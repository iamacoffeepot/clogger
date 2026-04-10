"""Crawl the OSRS wiki category graph and populate wiki_categories/wiki_category_parents.

Bulk-enumerates all wiki categories via allcategories (500/request), then
batch-fetches parent categories via prop=categories (50/request).  Filters
to the subgraph reachable from the root categories (default: Content).
"""

import argparse
from collections import deque
from pathlib import Path

import requests

from ragger.db import create_tables, get_connection
from ragger.wiki import API_URL, HEADERS, throttle

ROOT_CATEGORIES = ["Content"]


def fetch_all_categories() -> dict[str, dict]:
    """Enumerate every category on the wiki with page/subcat counts.

    Returns {name: {"page_count": int, "subcat_count": int}}.
    """
    cats: dict[str, dict] = {}
    params = {
        "action": "query",
        "list": "allcategories",
        "aclimit": "500",
        "acprop": "size",
        "format": "json",
    }

    while True:
        throttle()
        resp = requests.get(API_URL, params=params, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()

        for cat in data["query"]["allcategories"]:
            name = cat["*"]
            pages = cat.get("pages", 0)
            subcats = cat.get("subcats", 0)
            cats[name] = {
                "page_count": max(0, pages - subcats),
                "subcat_count": subcats,
            }

        if "continue" in data:
            params["accontinue"] = data["continue"]["accontinue"]
        else:
            break

    return cats


def fetch_parent_categories_batch(names: list[str]) -> dict[str, list[str]]:
    """Batch-fetch parent categories for up to 50 Category: pages.

    Returns {name: [parent_name, ...]}.
    """
    result: dict[str, list[str]] = {n: [] for n in names}
    titles = "|".join(f"Category:{n}" for n in names)
    params = {
        "action": "query",
        "prop": "categories",
        "titles": titles,
        "cllimit": "500",
        "format": "json",
    }

    while True:
        throttle()
        resp = requests.get(API_URL, params=params, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()

        for page in data["query"]["pages"].values():
            name = page.get("title", "").removeprefix("Category:")
            for cat in page.get("categories", []):
                parent = cat["title"].removeprefix("Category:")
                result.setdefault(name, []).append(parent)

        if "continue" in data:
            params["clcontinue"] = data["continue"]["clcontinue"]
        else:
            break

    return result


def ingest(db_path: Path, roots: list[str]) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    conn.execute("DELETE FROM wiki_category_parents")
    conn.execute("DELETE FROM wiki_categories")
    conn.commit()

    # Step 1: Bulk enumerate all categories with sizes
    print("Enumerating all wiki categories...")
    all_cats = fetch_all_categories()
    print(f"  Found {len(all_cats)} categories")

    # Step 2: Batch-fetch parent categories for every category
    print("Fetching parent categories...")
    names = list(all_cats.keys())
    # child -> [parents]
    parent_map: dict[str, list[str]] = {}
    for i in range(0, len(names), 50):
        batch = names[i : i + 50]
        parent_map.update(fetch_parent_categories_batch(batch))
        if (i // 50) % 10 == 0:
            print(f"  {i + len(batch)}/{len(names)}")

    # Step 3: Filter to the subtree reachable from roots
    # Build child -> parents adjacency from parent_map, then BFS down
    # from roots using the inverse (parent -> children)
    children_of: dict[str, list[str]] = {}
    for child, parents in parent_map.items():
        for parent in parents:
            children_of.setdefault(parent, []).append(child)

    reachable: set[str] = set()
    queue: deque[str] = deque()
    for root in roots:
        if root in all_cats:
            queue.append(root)
            reachable.add(root)

    while queue:
        name = queue.popleft()
        for child in children_of.get(name, []):
            if child not in reachable and child in all_cats:
                reachable.add(child)
                queue.append(child)

    print(f"  {len(reachable)} categories reachable from {roots}")

    # Step 4: Insert reachable categories
    for name in reachable:
        info = all_cats[name]
        conn.execute(
            """INSERT OR IGNORE INTO wiki_categories (name, page_count, subcat_count)
               VALUES (?, ?, ?)""",
            (name, info["page_count"], info["subcat_count"]),
        )
    conn.commit()

    # Build name -> id map
    rows = conn.execute("SELECT id, name FROM wiki_categories").fetchall()
    name_to_id = {r[1]: r[0] for r in rows}

    # Step 5: Insert parent edges (only between reachable categories)
    inserted = 0
    for child, parents in parent_map.items():
        child_id = name_to_id.get(child)
        if not child_id:
            continue
        for parent in parents:
            parent_id = name_to_id.get(parent)
            if parent_id:
                conn.execute(
                    """INSERT OR IGNORE INTO wiki_category_parents
                       (category_id, parent_id) VALUES (?, ?)""",
                    (child_id, parent_id),
                )
                inserted += 1
    conn.commit()

    print(f"Inserted {len(reachable)} categories, {inserted} parent edges into {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl wiki category graph")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/ragger.db"),
        help="Path to the SQLite database",
    )
    parser.add_argument(
        "--root",
        nargs="+",
        default=ROOT_CATEGORIES,
        help="Root categories to crawl from (default: Content)",
    )
    args = parser.parse_args()
    ingest(args.db, args.root)
