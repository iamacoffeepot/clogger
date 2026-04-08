"""Compute entity tags on dialogue nodes via Aho-Corasick matching.

Builds dictionaries from items, NPCs, monsters, quests, locations, shops,
equipment, and activities tables. Runs a single-pass Aho-Corasick automaton
over each dialogue node's text to find probable entity references.

Tags are stored in dialogue_tags as (node_id, entity_type, entity_name,
entity_id) — probable links, not hard foreign keys.
"""

import argparse
from pathlib import Path

import ahocorasick

from ragger.db import create_tables, get_connection

# Minimum entity name length to avoid false positives (e.g. "Ash", "Ice", "Ring")
MIN_NAME_LENGTH = 4

# Entity names that are common English words — skip these
STOPLIST: set[str] = {
    # Common English words that collide with entity names
    "ashes", "coins", "coal", "gold", "iron", "steel", "milk",
    "fire", "water", "earth", "mind", "body", "death", "soul",
    "door", "gate", "bank", "shop", "tree", "rock", "bush",
    "king", "queen", "lord", "lady", "chef", "cook", "duke",
    "guard", "knight", "monk", "priest", "hunter", "farmer",
    "thief", "hero", "boss", "pest", "frog", "bear", "wolf",
    "this", "that", "them", "they", "with", "from", "your",
    "have", "will", "what", "been", "were", "said", "each",
    "make", "like", "just", "over", "such", "take", "than",
    "some", "well", "also", "back", "then", "good", "look",
    "come", "could", "made", "find", "here", "know", "want",
    "give", "most", "only", "tell", "very", "when", "much",
    "need", "long", "time", "help", "hand", "left", "right",
    "home", "keep", "last", "name", "head", "turn", "move",
    "live", "work", "read", "lost", "part", "talk", "sure",
    "down", "gone", "done", "rest", "bone", "staff", "cape",
    "ring", "seed", "logs", "hide", "bolt", "dart", "rope",
    "lamp", "vial", "cake", "wine", "beer", "fish", "meat",
    # Titles / common nouns that are also entity names
    "love", "captain", "camel", "list", "present", "watch",
    "mother", "father", "brother", "sister", "uncle", "bunny",
    "ghost", "pirate", "wizard", "witch", "giant", "demon",
    "temple", "castle", "manor", "tower", "palace", "island",
    "hammer", "bucket", "knife", "spade", "chisel", "needle",
    "bones", "casket", "chest", "crate", "sack", "basket",
    "scroll", "note", "book", "page", "letter", "diary",
    "potion", "stew", "bread", "potato", "onion", "cabbage",
    "chicken", "shrimp", "lobster", "salmon", "trout", "tuna",
    "adventurer", "stranger", "messenger", "warrior", "archer",
    "spirit", "shade", "spawn", "zombie", "skeleton", "vampire",
    "mouse", "snake", "spider", "scorpion",
}


def build_automaton(conn) -> ahocorasick.Automaton:
    """Build an Aho-Corasick automaton from all entity names in the DB."""
    auto = ahocorasick.Automaton()

    # (query, entity_type)
    sources = [
        ("SELECT id, name FROM items", "item"),
        ("SELECT id, name FROM npcs", "npc"),
        ("SELECT id, name FROM monsters", "monster"),
        ("SELECT id, name FROM quests", "quest"),
        ("SELECT id, name FROM locations", "location"),
        ("SELECT id, name FROM shops", "shop"),
        ("SELECT id, name FROM equipment", "equipment"),
        ("SELECT id, name FROM activities", "activity"),
    ]

    seen: set[str] = set()

    for query, entity_type in sources:
        for row in conn.execute(query).fetchall():
            entity_id, name = row[0], row[1]
            if not name:
                continue

            lower = name.lower().strip()

            if len(lower) < MIN_NAME_LENGTH:
                continue
            if lower in STOPLIST:
                continue
            # Skip purely numeric names
            if lower.replace(" ", "").isdigit():
                continue

            # Use (lower, entity_type) as dedup key so the same name
            # can exist in multiple entity types
            key = (lower, entity_type)
            if key in seen:
                continue
            seen.add(key)

            # Aho-Corasick stores values at each pattern endpoint
            # If multiple entity types share a name, store them all
            existing = auto.get(lower, [])
            existing.append((entity_type, name, entity_id))
            auto.add_word(lower, existing)

    auto.make_automaton()
    print(f"Built automaton with {len(seen)} patterns from {len(sources)} entity types", flush=True)
    return auto


def is_word_boundary(text: str, start: int, end: int) -> bool:
    """Check that the match is bounded by non-alphanumeric chars."""
    if start > 0 and text[start - 1].isalnum():
        return False
    if end < len(text) and text[end].isalnum():
        return False
    return True


def tag_nodes(conn, auto: ahocorasick.Automaton) -> int:
    """Run the automaton over all dialogue node text. Returns tag count."""
    rows = conn.execute(
        "SELECT id, text FROM dialogue_nodes WHERE text IS NOT NULL AND text != ''"
    ).fetchall()

    tag_count = 0
    batch: list[tuple] = []

    for node_id, text in rows:
        lower = text.lower()
        # Track matches for this node to deduplicate
        seen_for_node: set[tuple[str, str]] = set()

        for end_idx, entries in auto.iter(lower):
            for entity_type, entity_name, entity_id in entries:
                match_len = len(entity_name)
                start_idx = end_idx - match_len + 1

                if not is_word_boundary(lower, start_idx, end_idx + 1):
                    continue

                dedup_key = (entity_type, entity_name)
                if dedup_key in seen_for_node:
                    continue
                seen_for_node.add(dedup_key)

                batch.append((node_id, entity_type, entity_name, entity_id))
                tag_count += 1

        if len(batch) >= 5000:
            conn.executemany(
                "INSERT INTO dialogue_tags (node_id, entity_type, entity_name, entity_id) VALUES (?, ?, ?, ?)",
                batch,
            )
            batch.clear()

    if batch:
        conn.executemany(
            "INSERT INTO dialogue_tags (node_id, entity_type, entity_name, entity_id) VALUES (?, ?, ?, ?)",
            batch,
        )

    return tag_count


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    # Clear previous tags
    conn.execute("DELETE FROM dialogue_tags")

    auto = build_automaton(conn)

    node_count = conn.execute(
        "SELECT COUNT(*) FROM dialogue_nodes WHERE text IS NOT NULL AND text != ''"
    ).fetchone()[0]
    print(f"Tagging {node_count} dialogue nodes...", flush=True)

    tag_count = tag_nodes(conn, auto)

    conn.commit()

    # Stats
    print(f"Created {tag_count} tags", flush=True)
    print("\nTags by entity type:", flush=True)
    for row in conn.execute(
        "SELECT entity_type, COUNT(*) FROM dialogue_tags GROUP BY entity_type ORDER BY 2 DESC"
    ):
        print(f"  {row[0]:20s} {row[1]}", flush=True)

    tagged_nodes = conn.execute(
        "SELECT COUNT(DISTINCT node_id) FROM dialogue_tags"
    ).fetchone()[0]
    print(f"\n{tagged_nodes}/{node_count} nodes have at least one tag", flush=True)

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute entity tags on dialogue nodes")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    args = parser.parse_args()
    ingest(args.db)
