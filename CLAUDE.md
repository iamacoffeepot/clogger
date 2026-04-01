# Clogger

OSRS Leagues knowledge base for route planning.

## Project Structure

- `src/clogger/` — Python package with data models and database module
- `scripts/` — Data ingestion scripts that pull from the OSRS wiki API
- `data/` — SQLite database (gitignored)
- `tests/` — pytest tests

## Scripts

All scripts require the package to be installed: `uv pip install -e .`

### fetch_all.py (recommended)

Runs all ingestion scripts in the correct order. Items must be populated first since other scripts reference the items table.

```sh
uv run python scripts/fetch_all.py [--db data/clogger.db] [--league Raging_Echoes_League/Tasks]
```

### Individual scripts

Run order matters: items -> quests -> diary tasks -> diary items -> league tasks

- `fetch_items.py` — Pulls all item names from the OSRS wiki
- `fetch_quests.py` — Pulls quests with points, XP/item rewards, skill/quest/QP requirements
- `fetch_diary_tasks.py` — Pulls diary tasks with skill and quest requirements
- `fetch_diary_items.py` — Pulls diary task item requirements from the Achievement Diary overview page
- `fetch_league_tasks.py` — Pulls league tasks with skill, quest, item, and diary requirements. Accepts `--page` for the wiki page to fetch from

## Database

Default path: `data/clogger.db`. All scripts accept `--db` to override.

Tables are created automatically when any script runs. Only `fetch_items.py` writes to the items table — all other scripts reference it.

## Python API

All API methods accept a `sqlite3.Connection` so connections can be reused.

### Quest (`src/clogger/quest.py`)

```python
from clogger.quest import Quest

Quest.all(conn) -> list[Quest]
Quest.by_name(conn, name) -> Quest | None
quest.xp_rewards(conn) -> list[ExperienceReward]
quest.item_rewards(conn) -> list[ItemReward]
quest.skill_requirements(conn) -> list[SkillRequirement]
quest.quest_requirements(conn) -> list[QuestRequirement]
quest.quest_point_requirement(conn) -> QuestPointRequirement | None
quest.requirement_chain(conn) -> list[Quest]       # flat list, bottom-up order
quest.requirement_tree(conn) -> str                 # indented tree string
```

### Item (`src/clogger/item.py`)

```python
from clogger.item import Item

Item.all(conn) -> list[Item]
Item.by_name(conn, name) -> Item | None
```

### DiaryTask (`src/clogger/diary.py`)

```python
from clogger.diary import DiaryTask

DiaryTask.all(conn, location?, tier?) -> list[DiaryTask]
```

Diary XP rewards are on the enum: `DiaryLocation.xp_reward(tier)` and `DiaryLocation.min_level(tier)`.

### LeagueTask (`src/clogger/league.py`)

```python
from clogger.league import LeagueTask

LeagueTask.all(conn, difficulty?, region?) -> list[LeagueTask]
LeagueTask.by_name(conn, name) -> LeagueTask | None
task.points -> int                                    # derived from difficulty
task.skill_requirements(conn) -> list[SkillRequirement]
task.quest_requirements(conn) -> list[QuestRequirement]
task.item_requirements(conn) -> list[ItemRequirement]
task.diary_requirements(conn) -> list[DiaryRequirement]
```

## Enums (`src/clogger/enums.py`)

- `Skill(int, Enum)` — 23 OSRS skills, int-based with `label`, `mask` properties
- `Region(int, Enum)` — 11 regions, int-based with `label`, `mask` properties
- `TaskDifficulty(int, Enum)` — Easy/Medium/Hard/Elite/Master with `label`, `points` properties
- `DiaryLocation(str, Enum)` — 12 diary regions with `xp_reward(tier)`, `min_level(tier)` methods
- `DiaryTier(str, Enum)` — Easy/Medium/Hard/Elite
- `ALL_SKILLS_MASK`, `ALL_REGIONS_MASK` — bitmask constants for "all"

## Tests

```sh
uv run pytest
```
