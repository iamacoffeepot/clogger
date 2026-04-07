"""Link actions to in-game interaction triggers via wiki Drop sources tables.

For each action output item, expands {{Drop sources|item}} to find source
entities (NPCs, objects) and their menu options. Batch-fetches source pages
to resolve game IDs, then writes action_triggers rows.

Requires: action scripts (fetch_fishing_actions.py, etc.) to have been run.
"""

import argparse
import re
from pathlib import Path

import requests

from ragger.db import create_tables, get_connection
from ragger.enums import TriggerType
from ragger.wiki import (
    WIKI_BATCH_SIZE,
    extract_template,
    fetch_pages_wikitext_batch,
    parse_int,
    parse_template_param,
    record_attributions_batch,
    throttle,
)

API_URL = "https://oldschool.runescape.wiki/api.php"
USER_AGENT = "ragger/1.0 (https://github.com/iamacoffeepot/ragger)"


def expand_drop_sources(item_name: str) -> str:
    """Expand {{Drop sources|item}} via the MediaWiki API."""
    resp = requests.get(API_URL, params={
        "action": "expandtemplates",
        "text": "{{Drop sources|" + item_name + "}}",
        "prop": "wikitext",
        "format": "json",
    }, headers={"User-Agent": USER_AGENT})
    return resp.json()["expandtemplates"]["wikitext"]


def parse_drop_sources(html: str) -> list[tuple[str, str | None]]:
    """Parse expanded Drop sources HTML for source page links.

    Returns list of (page_name, op_or_none) tuples. The op comes from the
    #anchor fragment when present (e.g. "Fishing spot (cage, harpoon)#Cage"
    yields op="Cage"). Plain links yield op=None.
    """
    sources: list[tuple[str, str | None]] = []
    rows = re.findall(r"<tr><td>(.*?)</td>", html, re.DOTALL)
    for row in rows:
        m = re.search(r"\[\[([^\]|]+)", row)
        if not m:
            continue
        link = m.group(1)
        if "#" in link:
            page, anchor = link.split("#", 1)
            sources.append((page.strip(), anchor.strip()))
        else:
            sources.append((link.strip(), None))
    return sources


def parse_page_ids_and_ops(wikitext: str) -> tuple[str | None, list[int], list[str]]:
    """Extract game IDs and menu options from a page's wikitext.

    Checks for Infobox NPC and Infobox Scenery. Returns (type, ids, ops)
    where type is "npc" or "object", or (None, [], []) if no relevant infobox.
    """
    for infobox_type, template_name in [("npc", "Infobox NPC"), ("object", "Infobox Scenery")]:
        block = extract_template(wikitext, template_name)
        if not block:
            continue

        # Parse IDs — may be versioned (id1, id2, ...) or plain (id)
        ids: list[int] = []
        plain_id = parse_template_param(block, "id")
        if plain_id:
            for part in plain_id.split(","):
                val = parse_int(part.strip())
                if val is not None:
                    ids.append(val)
        else:
            i = 1
            while True:
                vid = parse_template_param(block, f"id{i}")
                if vid is None:
                    break
                for part in vid.split(","):
                    val = parse_int(part.strip())
                    if val is not None:
                        ids.append(val)
                i += 1

        # Parse options — comma-separated, may have slash alternatives
        ops: list[str] = []
        options_raw = parse_template_param(block, "options")
        if options_raw:
            for opt in options_raw.split(","):
                opt = opt.strip().split("/")[0].strip()
                if opt:
                    ops.append(opt)

        return (infobox_type, ids, ops)

    return (None, [], [])


def ingest(db_path: Path, source: str | None = None) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    # Clear existing triggers
    conn.execute("DELETE FROM action_triggers")
    conn.commit()

    # Get all distinct output items across all actions (optionally filtered by source)
    if source:
        output_items = conn.execute("""
            SELECT DISTINCT aoi.item_name
            FROM action_output_items aoi
            JOIN source_actions sa ON sa.action_id = aoi.action_id
            WHERE sa.source = ?
            ORDER BY aoi.item_name
        """, (source,)).fetchall()
    else:
        output_items = conn.execute("""
            SELECT DISTINCT item_name FROM action_output_items
            ORDER BY item_name
        """).fetchall()
    print(f"Found {len(output_items)} distinct output items" + (f" (source: {source})" if source else ""))

    # Build item name -> list of (action_id, trigger_types)
    item_actions: dict[str, list[tuple[int, int]]] = {}
    if source:
        rows = conn.execute("""
            SELECT aoi.item_name, aoi.action_id, a.trigger_types
            FROM action_output_items aoi
            JOIN source_actions sa ON sa.action_id = aoi.action_id
            JOIN actions a ON a.id = aoi.action_id
            WHERE sa.source = ?
        """, (source,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT aoi.item_name, aoi.action_id, a.trigger_types
            FROM action_output_items aoi
            JOIN actions a ON a.id = aoi.action_id
        """).fetchall()
    for item_name, action_id, trigger_types in rows:
        item_actions.setdefault(item_name, []).append((action_id, trigger_types))

    # Masks for matching infobox type to trigger_types
    npc_mask = TriggerType.CLICK_NPC.mask | TriggerType.USE_ITEM_ON_NPC.mask
    object_mask = TriggerType.CLICK_OBJECT.mask | TriggerType.USE_ITEM_ON_OBJECT.mask

    # --- Pass 1: Expand Drop sources for every output item, collect source pages ---
    print("Pass 1: Expanding Drop sources...")
    # item_name -> list of (page_name, op_or_none)
    item_sources: dict[str, list[tuple[str, str | None]]] = {}
    all_source_pages: set[str] = set()

    for i, (item_name,) in enumerate(output_items):
        if i % 50 == 0:
            print(f"  {i}/{len(output_items)}...")
        throttle()
        html = expand_drop_sources(item_name)
        sources = parse_drop_sources(html)
        if sources:
            item_sources[item_name] = sources
            for page_name, _ in sources:
                all_source_pages.add(page_name)

    print(f"  Found {len(all_source_pages)} unique source pages across {len(item_sources)} items")

    # --- Pass 2: Batch-fetch all source pages and parse infoboxes ---
    print("Pass 2: Fetching source pages...")
    page_data: dict[str, tuple[str | None, list[int], list[str]]] = {}
    source_page_list = sorted(all_source_pages)

    for i in range(0, len(source_page_list), WIKI_BATCH_SIZE):
        batch = source_page_list[i:i + WIKI_BATCH_SIZE]
        print(f"  Fetching pages {i + 1}-{i + len(batch)} of {len(source_page_list)}...")
        wikitext_batch = fetch_pages_wikitext_batch(batch)
        for page_name, wikitext in wikitext_batch.items():
            page_data[page_name] = parse_page_ids_and_ops(wikitext)

    # --- Pass 3: Write triggers ---
    print("Pass 3: Writing triggers...")
    trigger_count = 0
    matched_items = 0

    for item_name, sources in item_sources.items():
        actions = item_actions.get(item_name, [])
        if not actions:
            continue

        item_matched = False
        for page_name, op_from_anchor in sources:
            data = page_data.get(page_name)
            if not data:
                continue
            infobox_type, ids, ops = data
            if not ids:
                continue

            # Determine the op to use
            if op_from_anchor:
                op = op_from_anchor
            elif len(ops) == 1:
                op = ops[0]
            else:
                continue

            # Determine which trigger_types mask this source requires
            if infobox_type == "npc":
                required_mask = npc_mask
            elif infobox_type == "object":
                required_mask = object_mask
            else:
                continue

            for action_id, trigger_types in actions:
                if not (trigger_types & required_mask):
                    continue
                for target_id in ids:
                    conn.execute(
                        "INSERT INTO action_triggers (action_id, target_id, op) VALUES (?, ?, ?)",
                        (action_id, target_id, op),
                    )
                    trigger_count += 1
                item_matched = True

        if item_matched:
            matched_items += 1

    conn.commit()
    print(f"Linked {trigger_count} triggers for {matched_items}/{len(output_items)} items")

    # Record attributions for source pages fetched
    fetched_pages = [p for p in all_source_pages if p in page_data]
    if fetched_pages:
        record_attributions_batch(conn, "action_triggers", fetched_pages)
        conn.commit()

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Link actions to triggers via Drop sources")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/ragger.db"),
        help="Path to the SQLite database",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Only process output items from actions with this source (e.g. wiki-fishing)",
    )
    args = parser.parse_args()
    ingest(args.db, args.source)
