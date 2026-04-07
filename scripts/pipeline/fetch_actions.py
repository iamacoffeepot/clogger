"""Fetch actions for all skills from wiki Skill table templates.

Expands {{Skill table|skill=X|members=yes}} for each skill and parses the
uniform HTML table to produce actions with inputs, outputs, requirements,
and triggers. Replaces individual fetch_*_actions.py scripts with a single
universal step.

One API call per skill (23 total) vs hundreds of page fetches.

Requires: fetch_items.py to have been run first (for item_id cross-referencing).
"""

import argparse
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import requests

from ragger.action import Action
from ragger.db import create_tables, get_connection
from ragger.enums import Skill, ActionTriggerType
from ragger.wiki import (
    API_URL,
    HEADERS,
    SKILL_NAME_MAP,
    WIKI_BATCH_SIZE,
    extract_template,
    fetch_pages_wikitext_batch,
    parse_page_ids_and_ops,
    parse_template_param,
    record_attributions_batch,
    throttle,
)

# Type alias for parsed page data: (infobox_type, entity_ids, ops)
PageData = dict[str, tuple[str | None, list[int], list[str]]]


# --- Data model ---


@dataclass
class ParsedAction:
    name: str
    skill: Skill
    level: int
    xp: float
    members: bool
    materials: list[tuple[str, int]]  # (item_name, quantity)
    tools: list[str]  # tool item names
    facility_pages: list[str]  # wiki pages for facilities
    secondary_skills: list[tuple[Skill, int]]  # (skill, level)
    page: str  # wiki page for the output item/entity
    version: str | None


# --- Trigger type determination ---

_SKILL_TRIGGER_DEFAULTS: dict[Skill, ActionTriggerType] = {
    Skill.COOKING: ActionTriggerType.CLICK_OBJECT,
    Skill.SMITHING: ActionTriggerType.CLICK_OBJECT,
    Skill.CRAFTING: ActionTriggerType.CLICK_OBJECT,
    Skill.CONSTRUCTION: ActionTriggerType.CLICK_OBJECT,
    Skill.RUNECRAFT: ActionTriggerType.CLICK_OBJECT,
    Skill.FLETCHING: ActionTriggerType.USE_ITEM_ON_ITEM,
    Skill.HERBLORE: ActionTriggerType.USE_ITEM_ON_ITEM,
    Skill.MAGIC: ActionTriggerType.CLICK_WIDGET,
    Skill.FIREMAKING: ActionTriggerType.USE_ITEM_ON_ITEM,
    Skill.PRAYER: ActionTriggerType.CLICK_ITEM,
    Skill.AGILITY: ActionTriggerType.CLICK_OBJECT,
    Skill.THIEVING: ActionTriggerType.CLICK_OBJECT,
    Skill.MINING: ActionTriggerType.CLICK_OBJECT,
    Skill.WOODCUTTING: ActionTriggerType.CLICK_OBJECT,
    Skill.FISHING: ActionTriggerType.CLICK_NPC,
    Skill.HUNTER: ActionTriggerType.CLICK_OBJECT,
    Skill.FARMING: ActionTriggerType.CLICK_OBJECT,
}

_PREFERRED_OPS: dict[int, list[str]] = {
    ActionTriggerType.CLICK_NPC.mask: [
        "Pickpocket", "Attack",
        "Small Net", "Net", "Bait", "Lure", "Cage", "Harpoon", "Big Net",
        "Use-rod", "Fish",
    ],
    ActionTriggerType.CLICK_OBJECT.mask: [
        "Mine", "Chop down", "Steal-from", "Steal", "Search", "Smelt", "Smith",
        "Cook", "Craft", "Use", "Cross", "Walk-across", "Jump-across", "Climb",
        "Collect-from", "Dig", "Check", "Pick", "Catch", "Bait", "Net",
        "Lure", "Harpoon", "Cage",
    ],
}


def _determine_trigger_type(action: ParsedAction, page_data: PageData) -> ActionTriggerType | None:
    """Determine trigger type from tools, facilities, page data, and skill defaults."""
    if action.facility_pages:
        for fac_page in action.facility_pages:
            fac_data = page_data.get(fac_page)
            if fac_data and fac_data[0] == "spell":
                return ActionTriggerType.WIDGET_ON_ITEM
        if action.materials:
            return ActionTriggerType.USE_ITEM_ON_OBJECT
        return ActionTriggerType.CLICK_OBJECT
    if action.skill == Skill.MAGIC and action.materials:
        return ActionTriggerType.WIDGET_ON_ITEM
    if action.skill == Skill.CONSTRUCTION and action.materials:
        data = page_data.get(action.page)
        if data and data[0] == "object":
            return ActionTriggerType.USE_ITEM_ON_OBJECT
        return None
    if action.materials:
        return ActionTriggerType.USE_ITEM_ON_ITEM
    return _SKILL_TRIGGER_DEFAULTS.get(action.skill)


def _pick_op(ops: list[str], trigger_mask: int) -> str | None:
    """Pick the best op from an entity's ops list."""
    if len(ops) == 1:
        return ops[0]
    for tt_mask, preferred in _PREFERRED_OPS.items():
        if not (trigger_mask & tt_mask):
            continue
        for pref in preferred:
            if pref in ops:
                return pref
    return None


def _resolve_tool_ids(conn: sqlite3.Connection, tool_name: str) -> list[int]:
    """Resolve a tool name to item IDs.

    Tries exact match, then case-insensitive, then expands equipment
    combat_style categories (e.g. "Bow" -> all bow items).
    """
    # Item lookup (exact then case-insensitive)
    row = conn.execute("SELECT id FROM items WHERE name = ?", (tool_name,)).fetchone()
    if row:
        return [row[0]]
    row = conn.execute("SELECT id FROM items WHERE name = ? COLLATE NOCASE", (tool_name,)).fetchone()
    if row:
        return [row[0]]
    # Equipment combat_style expansion (exact then case-insensitive)
    for collation in ("", " COLLATE NOCASE"):
        rows = conn.execute(
            f"SELECT DISTINCT item_id FROM equipment WHERE combat_style = ?{collation} AND item_id IS NOT NULL",
            (tool_name,),
        ).fetchall()
        if rows:
            return [r[0] for r in rows]
    return []


# --- Parsing ---

_WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")


def _extract_wiki_links(cell: str) -> list[str]:
    """Extract wiki page names from a cell, ignoring File: links."""
    return [m.group(1).strip() for m in _WIKI_LINK_RE.finditer(cell) if not m.group(1).startswith("File:")]


def _parse_items(cell: str) -> list[tuple[str, int]]:
    """Parse materials column: '2 x [[Item]]<br/>1 x [[Item2]]'."""
    items: list[tuple[str, int]] = []
    for part in cell.split("<br/>"):
        part = part.strip()
        if not part:
            continue
        qty_match = re.match(r"(\d+)\s*×\s*", part)
        qty = int(qty_match.group(1)) if qty_match else 1
        links = _extract_wiki_links(part)
        if links:
            items.append((links[-1], qty))
    return items


def _parse_skill_reqs(cell: str) -> list[tuple[Skill, int]]:
    """Parse secondary skill requirements from data attributes."""
    reqs: list[tuple[Skill, int]] = []
    for m in re.finditer(r'data-skill="(\w+)"\s+data-level="(\d+)"', cell):
        skill = SKILL_NAME_MAP.get(m.group(1).lower())
        if skill:
            reqs.append((skill, int(m.group(2))))
    return reqs


def _parse_skill_table(skill: Skill, html: str) -> list[ParsedAction]:
    """Parse expanded Skill table HTML into ParsedAction objects."""
    actions: list[ParsedAction] = []
    for row_match in re.finditer(r"<tr>(.*?)</tr>", html, re.DOTALL):
        row = row_match.group(1)
        cells = re.findall(r"<td>(.*?)</td>", row, re.DOTALL)
        # Columns: 0=image, 1=name, 2=members, 3=level, 4=xp, 5=materials, 6=tools, 7=facilities, 8=skills
        if len(cells) < 5:
            continue

        # Name (cell 1) — [[Page#anchor|Display]] or [[Page]]
        name_cell = cells[1]
        m = re.search(r"\[\[([^\]|]+?)(?:#[^\]|]*)?\|([^\]]+)\]\]", name_cell)
        if not m:
            m = re.search(r"\[\[([^\]|#]+?)(?:#[^\]|]*)?\]\]", name_cell)
            if not m:
                continue
            page, display = m.group(1).strip(), m.group(1).strip()
        else:
            page, display = m.group(1).strip(), m.group(2).strip()

        version_match = re.search(r"<small>\(([^)]+)\)</small>", name_cell)
        version = version_match.group(1).strip() if version_match else None

        members = "Member icon" in cells[2]

        level_match = re.search(r'data-level="(\d+)"', cells[3])
        if not level_match:
            continue
        level = int(level_match.group(1))

        try:
            xp = float(cells[4].strip().replace(",", ""))
        except ValueError:
            continue
        if xp <= 0:
            continue

        materials = _parse_items(cells[5]) if len(cells) > 5 else []
        tools = [name for name, _ in _parse_items(cells[6])] if len(cells) > 6 else []
        facility_pages = _extract_wiki_links(cells[7]) if len(cells) > 7 else []
        secondary_skills = _parse_skill_reqs(cells[8]) if len(cells) > 8 else []

        action_name = f"{display} ({version})" if version else display

        actions.append(ParsedAction(
            name=action_name, skill=skill, level=level, xp=xp,
            members=members, materials=materials, tools=tools,
            facility_pages=facility_pages, secondary_skills=secondary_skills,
            page=page, version=version,
        ))

    return actions


# --- Cache definitions ---


def _load_cache_ops(data_dir: Path) -> tuple[dict[int, list[str]], dict[int, list[str]]]:
    """Load NPC and object ops from cache dump definitions."""
    result: list[dict[int, list[str]]] = []
    for filename in ("npc-definitions.json", "object-definitions.json"):
        ops_map: dict[int, list[str]] = {}
        path = data_dir / "cache-dump" / filename
        if path.exists():
            with open(path) as f:
                for entry in json.load(f):
                    ops = [op["text"] for op in entry.get("ops", []) if op.get("text")]
                    if ops:
                        ops_map[entry["id"]] = ops
        result.append(ops_map)
    return result[0], result[1]


# --- Page data resolution ---


def _fetch_page_data(pages: set[str]) -> tuple[PageData, dict[str, str]]:
    """Batch-fetch pages and parse infobox data. Returns (page_data, all_wikitext)."""
    page_data: PageData = {}
    all_wikitext: dict[str, str] = {}
    for i in range(0, len(pages), WIKI_BATCH_SIZE):
        batch = sorted(pages)[i:i + WIKI_BATCH_SIZE]
        wikitext_batch = fetch_pages_wikitext_batch(batch)
        all_wikitext.update(wikitext_batch)
        for page_name, wikitext in wikitext_batch.items():
            page_data[page_name] = parse_page_ids_and_ops(wikitext)
    return page_data, all_wikitext


def _follow_redirects(page_data: PageData, all_wikitext: dict[str, str]) -> None:
    """Follow #REDIRECT pages and copy target data back to the source."""
    redirects: dict[str, str] = {}
    for page_name, (itype, _, _) in page_data.items():
        if itype is not None:
            continue
        wikitext = all_wikitext.get(page_name, "")
        m = re.match(r"#REDIRECT\s*\[\[([^\]]+)\]\]", wikitext, re.IGNORECASE)
        if m:
            redirects[page_name] = m.group(1).strip()
    if not redirects:
        return
    targets_to_fetch = sorted(set(redirects.values()) - set(page_data.keys()))
    for i in range(0, len(targets_to_fetch), WIKI_BATCH_SIZE):
        batch = targets_to_fetch[i:i + WIKI_BATCH_SIZE]
        for rpage, rwikitext in fetch_pages_wikitext_batch(batch).items():
            page_data[rpage] = parse_page_ids_and_ops(rwikitext)
    for orig, target in redirects.items():
        if target in page_data:
            page_data[orig] = page_data[target]


def _follow_construction_hotspots(page_data: PageData, all_wikitext: dict[str, str]) -> None:
    """Follow Infobox Construction hotspot params to resolve hotspot object IDs."""
    hotspot_map: dict[str, str] = {}  # page_name -> hotspot_page
    for page_name, (itype, _, _) in page_data.items():
        if itype is not None:
            continue
        wikitext = all_wikitext.get(page_name, "")
        block = extract_template(wikitext, "Infobox Construction")
        if not block:
            continue
        hotspot_raw = parse_template_param(block, "hotspot")
        if not hotspot_raw:
            continue
        m = re.search(r"\[\[([^\]|]+)", hotspot_raw)
        if m:
            hotspot_map[page_name] = m.group(1).strip()
    if not hotspot_map:
        return
    # Fetch hotspot pages we don't already have
    to_fetch = sorted(set(hotspot_map.values()) - set(page_data.keys()))
    for i in range(0, len(to_fetch), WIKI_BATCH_SIZE):
        batch = to_fetch[i:i + WIKI_BATCH_SIZE]
        for hpage, hwikitext in fetch_pages_wikitext_batch(batch).items():
            page_data[hpage] = parse_page_ids_and_ops(hwikitext)
    # Copy hotspot data back to original pages
    for page_name, hotspot_page in hotspot_map.items():
        hs_data = page_data.get(hotspot_page)
        if hs_data and hs_data[0] is not None:
            page_data[page_name] = hs_data


# --- Entity resolution ---


def _resolve_entity(
    action: ParsedAction,
    page_data: PageData,
) -> tuple[str | None, list[int], list[str]] | None:
    """Find the best entity data for an action (page first, then facility pages)."""
    data = page_data.get(action.page)
    if data and data[0] not in (None, "spell") and data[1]:
        return data
    for fac_page in action.facility_pages:
        fac_data = page_data.get(fac_page)
        if fac_data and fac_data[0] not in (None, "spell") and fac_data[1]:
            return fac_data
    return None


# --- Database writing ---


def _insert_trigger(
    conn: sqlite3.Connection,
    action_id: int,
    trigger_type: ActionTriggerType,
    source_id: int | None,
    target_id: int,
    op: str,
) -> None:
    conn.execute(
        "INSERT INTO action_triggers (action_id, trigger_type, source_id, target_id, op) VALUES (?, ?, ?, ?, ?)",
        (action_id, trigger_type.value, source_id, target_id, op),
    )


def _lookup_item_id(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute("SELECT id FROM items WHERE name = ?", (name,)).fetchone()
    return row[0] if row else None


def _write_actions(
    conn: sqlite3.Connection,
    actions: list[ParsedAction],
    page_data: PageData,
    npc_ops: dict[int, list[str]],
    obj_ops: dict[int, list[str]],
    source: str,
) -> tuple[int, int]:
    """Write parsed actions to the database. Returns (action_count, trigger_count)."""
    action_count = 0
    trigger_count = 0

    for action in actions:
        trigger_type = _determine_trigger_type(action, page_data)

        cur = conn.execute(
            "INSERT INTO actions (name, members, ticks, notes) VALUES (?, ?, ?, ?)",
            (action.name, int(action.members), None, None),
        )
        action_id = cur.lastrowid

        conn.execute(
            "INSERT INTO source_actions (source, action_id) VALUES (?, ?)",
            (source, action_id),
        )

        # Output experience
        conn.execute(
            "INSERT INTO action_output_experience (action_id, skill, xp) VALUES (?, ?, ?)",
            (action_id, action.skill.value, action.xp),
        )

        # Requirement group
        group_id = conn.execute("INSERT INTO requirement_groups DEFAULT VALUES").lastrowid
        conn.execute(
            "INSERT INTO action_requirement_groups (action_id, group_id) VALUES (?, ?)",
            (action_id, group_id),
        )
        for skill, level in [(action.skill, action.level)] + action.secondary_skills:
            conn.execute(
                "INSERT INTO group_skill_requirements (group_id, skill, level, boostable) VALUES (?, ?, ?, ?)",
                (group_id, skill.value, max(1, level), True),
            )

        # Input items
        for item_name, qty in action.materials:
            conn.execute(
                "INSERT INTO action_input_items (action_id, item_id, item_name, quantity) VALUES (?, ?, ?, ?)",
                (action_id, _lookup_item_id(conn, item_name), item_name, qty),
            )

        # Output item or object
        out_item_id = _lookup_item_id(conn, action.page)
        if out_item_id:
            conn.execute(
                "INSERT INTO action_output_items (action_id, item_id, item_name, quantity) VALUES (?, ?, ?, ?)",
                (action_id, out_item_id, action.page, 1),
            )
        else:
            conn.execute(
                "INSERT INTO action_output_objects (action_id, object_name) VALUES (?, ?)",
                (action_id, action.page),
            )

        # --- Triggers ---
        if trigger_type == ActionTriggerType.USE_ITEM_ON_ITEM:
            material_ids = [_lookup_item_id(conn, name) for name, _ in action.materials]
            material_ids = [mid for mid in material_ids if mid is not None]
            tool_ids = _resolve_tool_ids(conn, action.tools[0]) if action.tools else []

            if len(material_ids) >= 2:
                _insert_trigger(conn, action_id, trigger_type, material_ids[0], material_ids[1], "Use")
                trigger_count += 1
            elif len(material_ids) == 1 and tool_ids:
                for tid in tool_ids:
                    _insert_trigger(conn, action_id, trigger_type, tid, material_ids[0], "Use")
                    trigger_count += 1
            elif len(material_ids) == 1:
                _insert_trigger(conn, action_id, trigger_type, None, material_ids[0], "Use")
                trigger_count += 1
            elif tool_ids:
                page_item_id = _lookup_item_id(conn, action.page)
                if page_item_id:
                    for tid in tool_ids:
                        _insert_trigger(conn, action_id, trigger_type, tid, page_item_id, "Use")
                        trigger_count += 1

        elif trigger_type in (ActionTriggerType.WIDGET_ON_ITEM, ActionTriggerType.CLICK_ITEM):
            page_item_id = _lookup_item_id(conn, action.page)
            if page_item_id:
                op = "Cast" if trigger_type == ActionTriggerType.WIDGET_ON_ITEM else "Use"
                _insert_trigger(conn, action_id, trigger_type, None, page_item_id, op)
                trigger_count += 1

        elif trigger_type in (
            ActionTriggerType.USE_ITEM_ON_OBJECT, ActionTriggerType.USE_ITEM_ON_NPC,
            ActionTriggerType.CLICK_OBJECT, ActionTriggerType.CLICK_NPC,
        ):
            entity = _resolve_entity(action, page_data)
            if not entity:
                action_count += 1
                continue
            infobox_type, ids, wiki_ops = entity

            # Override trigger type from entity type when clicking
            if trigger_type in (ActionTriggerType.CLICK_OBJECT, ActionTriggerType.CLICK_NPC):
                if infobox_type == "npc":
                    trigger_type = ActionTriggerType.CLICK_NPC
                elif infobox_type == "object":
                    trigger_type = ActionTriggerType.CLICK_OBJECT

            source_item_id = None
            if trigger_type in (ActionTriggerType.USE_ITEM_ON_OBJECT, ActionTriggerType.USE_ITEM_ON_NPC):
                if action.materials:
                    source_item_id = _lookup_item_id(conn, action.materials[0][0])

            cache_lookup = npc_ops if infobox_type == "npc" else obj_ops
            for target_id in ids:
                target_ops = cache_lookup.get(target_id, wiki_ops)
                op = _pick_op(target_ops, trigger_type.mask)
                if not op and target_ops:
                    op = target_ops[0]
                if op:
                    _insert_trigger(conn, action_id, trigger_type, source_item_id, target_id, op)
                    trigger_count += 1

        action_count += 1

    return action_count, trigger_count


# --- Main ---


def ingest(db_path: Path, skills: list[Skill] | None = None) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    data_dir = db_path.parent
    npc_ops, obj_ops = _load_cache_ops(data_dir)
    print(f"Loaded {len(npc_ops)} NPC and {len(obj_ops)} object definitions from cache")

    if skills is None:
        skills = list(Skill)

    total_actions = 0
    total_triggers = 0

    for skill in skills:
        source = f"wiki-skill-table-{skill.label.lower()}"

        old_ids = Action.delete_by_source(conn, source)
        if old_ids:
            conn.commit()

        print(f"\n--- {skill.label} ---")
        throttle()
        resp = requests.get(API_URL, params={
            "action": "expandtemplates",
            "text": "{{Skill table|skill=" + skill.label + "|members=yes}}",
            "prop": "wikitext",
            "format": "json",
        }, headers=HEADERS)
        resp.raise_for_status()
        html = resp.json()["expandtemplates"]["wikitext"]

        actions = _parse_skill_table(skill, html)
        if not actions:
            print(f"  No actions found")
            continue
        print(f"  Parsed {len(actions)} actions")

        # Batch-fetch all entity + facility pages
        pages_to_fetch: set[str] = set()
        for action in actions:
            pages_to_fetch.add(action.page)
            pages_to_fetch.update(action.facility_pages)

        page_data, all_wikitext = _fetch_page_data(pages_to_fetch)
        _follow_redirects(page_data, all_wikitext)
        _follow_construction_hotspots(page_data, all_wikitext)

        # Write to database
        action_count, trigger_count = _write_actions(
            conn, actions, page_data, npc_ops, obj_ops, source,
        )
        conn.commit()

        print(f"  Wrote {action_count} actions, {trigger_count} triggers")
        total_actions += action_count
        total_triggers += trigger_count

        # Record attributions
        fetched_pages = list(page_data.keys())
        if fetched_pages:
            record_attributions_batch(conn, "actions", fetched_pages)
            conn.commit()

    print(f"\nTotal: {total_actions} actions, {total_triggers} triggers")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch actions from Skill table templates")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/ragger.db"),
        help="Path to the SQLite database",
    )
    parser.add_argument(
        "--skill",
        type=str,
        default=None,
        help="Only fetch for a specific skill (e.g. Smithing)",
    )
    args = parser.parse_args()

    skills = None
    if args.skill:
        skill = SKILL_NAME_MAP.get(args.skill.lower())
        if not skill:
            parser.error(f"Unknown skill: {args.skill}")
        skills = [skill]

    ingest(args.db, skills)
