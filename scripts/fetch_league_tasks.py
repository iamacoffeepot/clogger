"""Fetch league tasks from the OSRS wiki and insert into the league_tasks table.

Currently targets Raging Echoes League as a prototype.
Requires: fetch_items.py and fetch_quests.py to have been run first.
"""

import argparse
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from clogger.db import create_tables, get_connection
from clogger.enums import DiaryLocation, DiaryTier, Region, Skill, TaskDifficulty

API_URL = "https://oldschool.runescape.wiki/api.php"
USER_AGENT = "clogger/0.1 - OSRS Leagues planner"
HEADERS = {"User-Agent": USER_AGENT}

def parse_template_fields(text: str) -> dict[str, str] | None:
    """Parse a RELTaskRow template handling nested [[ ]] and {{ }}."""
    if not text.startswith("{{RELTaskRow|"):
        return None

    # Strip outer {{ }}
    inner = text[2:-2]
    # Skip "RELTaskRow|"
    inner = inner[len("RELTaskRow|"):]

    fields: list[str] = []
    current: list[str] = []
    bracket_depth = 0
    brace_depth = 0

    for ch in inner:
        if ch == "[":
            bracket_depth += 1
            current.append(ch)
        elif ch == "]":
            bracket_depth -= 1
            current.append(ch)
        elif ch == "{":
            brace_depth += 1
            current.append(ch)
        elif ch == "}":
            brace_depth -= 1
            current.append(ch)
        elif ch == "|" and bracket_depth == 0 and brace_depth == 0:
            fields.append("".join(current))
            current = []
        else:
            current.append(ch)
    fields.append("".join(current))

    if len(fields) < 3:
        return None

    result = {"name": fields[0], "description": fields[1]}
    for f in fields[2:]:
        if "=" in f:
            key, _, value = f.partition("=")
            result[key.strip()] = value.strip()

    return result

SKILL_REQ_PATTERN = re.compile(r"\{\{SCP\|(\w+)\|(\d+)")
QUEST_REQ_PATTERN = re.compile(r"\[\[([^]|]+?)(?:\|[^]]+)?\]\]")
REGION_REQ_PATTERN = re.compile(r"\{\{RE\|(\w+)\}\}")

SKILL_NAME_MAP = {s.label.lower(): s for s in Skill}

DIFFICULTY_MAP = {
    "easy": TaskDifficulty.EASY,
    "medium": TaskDifficulty.MEDIUM,
    "hard": TaskDifficulty.HARD,
    "elite": TaskDifficulty.ELITE,
    "master": TaskDifficulty.MASTER,
}



DIARY_LOCATION_MAP = {
    "ardougne": DiaryLocation.ARDOUGNE,
    "desert": DiaryLocation.DESERT,
    "falador": DiaryLocation.FALADOR,
    "fremennik": DiaryLocation.FREMENNIK,
    "kandarin": DiaryLocation.KANDARIN,
    "karamja": DiaryLocation.KARAMJA,
    "kourend & kebos": DiaryLocation.KOUREND_KEBOS,
    "kourend and kebos": DiaryLocation.KOUREND_KEBOS,
    "lumbridge & draynor": DiaryLocation.LUMBRIDGE_DRAYNOR,
    "morytania": DiaryLocation.MORYTANIA,
    "varrock": DiaryLocation.VARROCK,
    "western provinces": DiaryLocation.WESTERN_PROVINCES,
    "wilderness": DiaryLocation.WILDERNESS,
}

DIARY_TIER_MAP = {
    "easy": DiaryTier.EASY,
    "medium": DiaryTier.MEDIUM,
    "hard": DiaryTier.HARD,
    "elite": DiaryTier.ELITE,
}

# Pattern: "Complete the Easy Falador Diary" or "Kourend and Kebos Easy Diary Tasks"
DIARY_TASK_PATTERN = re.compile(
    r"(?:Complete the (\w+) (.+?) Diary|(.+?) (\w+) Diary Tasks)",
    re.IGNORECASE,
)


@dataclass
class LeagueTaskData:
    id: int
    name: str
    description: str
    difficulty: TaskDifficulty
    region: Region
    skill_reqs: list[tuple[int, int]] = field(default_factory=list)
    quest_reqs: list[tuple[str, bool]] = field(default_factory=list)
    item_reqs: list[str] = field(default_factory=list)
    diary_reqs: list[tuple[DiaryLocation, DiaryTier]] = field(default_factory=list)
    region_reqs: list[tuple[int, bool]] = field(default_factory=list)  # (bitmask, any_region)


def strip_markup(text: str) -> str:
    text = re.sub(r"\[\[([^]|]*\|)?([^]]*)\]\]", r"\2", text)
    text = re.sub(r"\{\{[^}]*\}\}", "", text)
    text = re.sub(r"'{2,3}", "", text)
    return text.strip()


def parse_skill_reqs(s_field: str) -> list[tuple[int, int]]:
    reqs = []
    for match in SKILL_REQ_PATTERN.finditer(s_field):
        skill_name = match.group(1).lower()
        level = int(match.group(2))
        skill = SKILL_NAME_MAP.get(skill_name)
        if skill is not None and 1 <= level <= 99:
            reqs.append((skill.value, level))
    return reqs


def parse_other_reqs(
    other_field: str,
) -> tuple[list[tuple[str, bool]], list[str], list[tuple[int, bool]]]:
    quest_reqs: list[tuple[str, bool]] = []
    item_reqs: list[str] = []
    region_reqs: list[tuple[int, bool]] = []

    # Quest requirements
    if "Completion of" in other_field or "SCP|Quest" in other_field:
        for match in QUEST_REQ_PATTERN.finditer(other_field):
            quest_name = match.group(1)
            if quest_name.startswith("File:") or quest_name.startswith("Category:"):
                continue
            pos = match.start()
            context = other_field[max(0, pos - 80) : pos]
            if "Completion of" in context or "SCP|Quest" in context:
                quest_reqs.append((quest_name, False))

    if "Started" in other_field:
        for match in re.finditer(r"[Ss]tarted\s+\[\[([^]|]+?)(?:\|[^]]+)?\]\]", other_field):
            name = match.group(1)
            if not any(q == name for q, _ in quest_reqs):
                quest_reqs.append((name, True))

    # Item requirements — links in non-quest, non-region context
    quest_names = {q for q, _ in quest_reqs}
    for match in QUEST_REQ_PATTERN.finditer(other_field):
        name = match.group(1).strip()
        if name in quest_names:
            continue
        if name.startswith("File:") or name.startswith("Category:"):
            continue
        if "#" in name:
            continue
        # Skip region references {{RE|...}}
        pos = match.start()
        before = other_field[max(0, pos - 5) : pos]
        if "RE|" in before or "SCP|" in before:
            continue
        item_reqs.append(name)

    # Region requirements: {{RE|Region}}
    regions: list[Region] = []
    for match in REGION_REQ_PATTERN.finditer(other_field):
        try:
            region = Region.from_label(match.group(1))
            if region not in regions:
                regions.append(region)
        except KeyError:
            pass

    if regions:
        mask = 0
        for r in regions:
            mask |= r.mask
        is_any = "Either" in other_field or "either" in other_field or " or " in other_field or "one of" in other_field
        region_reqs.append((mask, is_any))

    return quest_reqs, item_reqs, region_reqs


def fetch_tasks_wikitext(page: str) -> str:
    resp = requests.get(
        API_URL,
        params={"action": "parse", "page": page, "prop": "wikitext", "format": "json"},
        headers=HEADERS,
    )
    resp.raise_for_status()
    return resp.json()["parse"]["wikitext"]["*"]


def extract_templates(wikitext: str) -> list[str]:
    """Extract all {{RELTaskRow|...}} templates from wikitext."""
    templates = []
    i = 0
    while i < len(wikitext):
        if wikitext[i : i + 12] == "{{RELTaskRow":
            depth = 0
            start = i
            while i < len(wikitext):
                if wikitext[i : i + 2] == "{{":
                    depth += 1
                    i += 2
                elif wikitext[i : i + 2] == "}}":
                    depth -= 1
                    i += 2
                    if depth == 0:
                        templates.append(wikitext[start:i])
                        break
                else:
                    i += 1
        else:
            i += 1
    return templates


def parse_league_tasks(wikitext: str) -> list[LeagueTaskData]:
    tasks = []
    for template in extract_templates(wikitext):
        fields = parse_template_fields(template)
        if fields is None or "id" not in fields or "tier" not in fields:
            continue

        name = fields["name"].strip()
        description = strip_markup(fields["description"].strip())
        s_field = fields.get("s", "")
        other_field = fields.get("other", "")
        tier = fields["tier"].lower()
        region_str = fields.get("region", "general").strip().lower()
        task_id = int(fields["id"])

        difficulty = DIFFICULTY_MAP.get(tier)
        if difficulty is None:
            continue
        try:
            region = Region.from_label(region_str)
        except KeyError:
            raise ValueError(f"Unknown region '{region_str}' for task '{name}' (id={task_id})")

        skill_reqs = parse_skill_reqs(s_field)
        quest_reqs, item_reqs, region_reqs = parse_other_reqs(other_field)

        # Detect diary requirements from task name
        diary_reqs: list[tuple[DiaryLocation, DiaryTier]] = []
        diary_match = DIARY_TASK_PATTERN.search(name)
        if diary_match:
            # "Complete the Easy Falador Diary" -> tier=Easy, location=Falador
            # "Kourend and Kebos Easy Diary Tasks" -> location=Kourend and Kebos, tier=Easy
            if diary_match.group(1):
                tier_str = diary_match.group(1).lower()
                loc_str = diary_match.group(2).lower()
            else:
                loc_str = diary_match.group(3).lower()
                tier_str = diary_match.group(4).lower()
            diary_loc = DIARY_LOCATION_MAP.get(loc_str)
            diary_tier = DIARY_TIER_MAP.get(tier_str)
            if diary_loc and diary_tier:
                diary_reqs.append((diary_loc, diary_tier))

        tasks.append(LeagueTaskData(
            id=task_id,
            name=name,
            description=description,
            difficulty=difficulty,
            region=region,
            skill_reqs=skill_reqs,
            quest_reqs=quest_reqs,
            item_reqs=item_reqs,
            diary_reqs=diary_reqs,
            region_reqs=region_reqs,
        ))

    return tasks


def ingest(db_path: Path, page: str = "Raging_Echoes_League/Tasks") -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    # Lookup maps
    quest_ids = dict(conn.execute("SELECT name, id FROM quests").fetchall())
    item_ids = dict(conn.execute("SELECT name, id FROM items").fetchall())

    print(f"Fetching tasks from {page}...")
    wikitext = fetch_tasks_wikitext(page)
    tasks = parse_league_tasks(wikitext)

    skill_req_count = 0
    quest_req_count = 0
    item_req_count = 0
    diary_req_count = 0
    region_req_count = 0

    for task in tasks:
        conn.execute(
            "INSERT INTO league_tasks (name, description, difficulty, region) VALUES (?, ?, ?, ?)",
            (task.name, task.description, task.difficulty.value, task.region.value),
        )
        league_task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Skill requirements
        for skill_id, level in task.skill_reqs:
            conn.execute(
                "INSERT OR IGNORE INTO skill_requirements (skill, level) VALUES (?, ?)",
                (skill_id, level),
            )
            req_id = conn.execute(
                "SELECT id FROM skill_requirements WHERE skill = ? AND level = ?",
                (skill_id, level),
            ).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO league_task_skill_requirements (league_task_id, skill_requirement_id) VALUES (?, ?)",
                (league_task_id, req_id),
            )
            skill_req_count += 1

        # Quest requirements
        for quest_name, partial in task.quest_reqs:
            req_quest_id = quest_ids.get(quest_name)
            if req_quest_id is None:
                continue
            partial_int = 1 if partial else 0
            conn.execute(
                "INSERT OR IGNORE INTO quest_requirements (required_quest_id, partial) VALUES (?, ?)",
                (req_quest_id, partial_int),
            )
            req_id = conn.execute(
                "SELECT id FROM quest_requirements WHERE required_quest_id = ? AND partial = ?",
                (req_quest_id, partial_int),
            ).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO league_task_quest_requirements (league_task_id, quest_requirement_id) VALUES (?, ?)",
                (league_task_id, req_id),
            )
            quest_req_count += 1

        # Item requirements
        for item_name in task.item_reqs:
            item_id = item_ids.get(item_name)
            if item_id is None:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO item_requirements (item_id, quantity) VALUES (?, ?)",
                (item_id, 1),
            )
            req_id = conn.execute(
                "SELECT id FROM item_requirements WHERE item_id = ? AND quantity = 1",
                (item_id,),
            ).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO league_task_item_requirements (league_task_id, item_requirement_id) VALUES (?, ?)",
                (league_task_id, req_id),
            )
            item_req_count += 1

        # Diary requirements
        for diary_loc, diary_tier in task.diary_reqs:
            conn.execute(
                "INSERT OR IGNORE INTO diary_requirements (location, tier) VALUES (?, ?)",
                (diary_loc.value, diary_tier.value),
            )
            req_id = conn.execute(
                "SELECT id FROM diary_requirements WHERE location = ? AND tier = ?",
                (diary_loc.value, diary_tier.value),
            ).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO league_task_diary_requirements (league_task_id, diary_requirement_id) VALUES (?, ?)",
                (league_task_id, req_id),
            )
            diary_req_count += 1

        # Region requirements
        for mask, is_any in task.region_reqs:
            any_int = 1 if is_any else 0
            conn.execute(
                "INSERT OR IGNORE INTO region_requirements (regions, any_region) VALUES (?, ?)",
                (mask, any_int),
            )
            req_id = conn.execute(
                "SELECT id FROM region_requirements WHERE regions = ? AND any_region = ?",
                (mask, any_int),
            ).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO league_task_region_requirements (league_task_id, region_requirement_id) VALUES (?, ?)",
                (league_task_id, req_id),
            )
            region_req_count += 1

    conn.commit()
    print(
        f"Inserted {len(tasks)} tasks, {skill_req_count} skill requirements, "
        f"{quest_req_count} quest requirements, {item_req_count} item requirements, "
        f"{diary_req_count} diary requirements, {region_req_count} region requirements into {db_path}"
    )
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch league tasks into the database")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/clogger.db"),
        help="Path to the SQLite database",
    )
    parser.add_argument(
        "--page",
        default="Raging_Echoes_League/Tasks",
        help="Wiki page to fetch tasks from",
    )
    args = parser.parse_args()
    ingest(args.db, args.page)
