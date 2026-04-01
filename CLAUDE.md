# Clogger

OSRS Leagues knowledge base for route planning.

## Project Structure

- `src/clogger/` — Python package with data models and database module
- `scripts/` — Data ingestion scripts that pull from the OSRS wiki API
- `data/` — SQLite database (gitignored)

## Scripts

All scripts require the package to be installed: `uv pip install -e .`

### fetch_quests.py

Pulls all quests and their quest point values from the OSRS wiki.

```sh
uv run python scripts/fetch_quests.py [--db data/clogger.db]
```

### fetch_items.py

Pulls all item names from the OSRS wiki.

```sh
uv run python scripts/fetch_items.py [--db data/clogger.db]
```

### fetch_diary_tasks.py

Pulls all achievement diary tasks (492 across 12 regions, 4 tiers) from the OSRS wiki.

```sh
uv run python scripts/fetch_diary_tasks.py [--db data/clogger.db]
```

## Database

Default path: `data/clogger.db`. All scripts accept `--db` to override.

Tables are created automatically when any script runs.
