"""Fetch NPC dialogue trees from Transcript: pages on the OSRS wiki.

Pulls from transcript subcategories (Quest transcript, NPC dialogue, etc.)
in namespace 120. Parses the *-indented wikitext into a tree stored as an
adjacency list in dialogue_pages + dialogue_nodes.
"""

import argparse
import re
from pathlib import Path

from ragger.db import create_tables, get_connection
from ragger.wiki import (
    extract_template,
    fetch_category_members,
    fetch_pages_wikitext_batch,
    record_attributions_batch,
    strip_wiki_links,
)

# Transcript subcategories → default page_type (overridden by {{Transcript|type}})
SUBCATEGORIES: list[str] = [
    "Quest transcript",
    "NPC dialogue",
    "Event transcript",
    "Miniquest transcript",
    "Item transcript",
    "Pet dialogue",
    "Scenery transcript",
    "Incomplete transcripts",
]

TRANSCRIPT_NS = 120

# '''Speaker:''' text
SPEAKER_RE = re.compile(r"^'''(.+?):'''\s*(.*)")

# {{template|...}} at the start of a line (after stripping *)
TEMPLATE_RE = re.compile(r"^\{\{(\w+)\|?(.*)\}\}$", re.DOTALL)

NODE_TYPE_MAP = {
    "topt": "option",
    "tcond": "condition",
    "tact": "action",
    "tbox": "box",
    "tselect": "select",
    "qact": "quest_action",
}


def parse_transcript_type(wikitext: str) -> str | None:
    """Extract page type from {{Transcript|type}} or {{transcript|type}}."""
    block = extract_template(wikitext, "Transcript")
    if not block:
        block = extract_template(wikitext, "transcript")
    if not block:
        return None
    # block is like "|Quest" or "|npc"
    parts = block.strip().lstrip("|").split("|")
    if parts and parts[0]:
        return parts[0].strip().lower()
    return None


def extract_template_text(template_name: str, params_str: str) -> str:
    """Extract human-readable text from a template's parameters."""
    if not params_str:
        return ""

    if template_name == "tbox":
        # tbox has pic=, pic2= named params; the text is the last positional
        parts = params_str.split("|")
        text_parts = [p.strip() for p in parts if "=" not in p]
        return strip_wiki_links(text_parts[-1]) if text_parts else strip_wiki_links(params_str)

    if template_name == "tact":
        return params_str.strip()

    # topt, tcond, tselect, qact — first positional param
    first = params_str.split("|")[0].strip()
    return strip_wiki_links(first)


def parse_line_content(content: str) -> dict:
    """Parse the content of a single * line into node_type, speaker, text."""
    content = content.strip()

    # Check for known templates
    m = TEMPLATE_RE.match(content)
    if m:
        tname = m.group(1).lower()
        if tname in NODE_TYPE_MAP:
            text = extract_template_text(tname, m.group(2))
            return {"node_type": NODE_TYPE_MAP[tname], "speaker": None, "text": text}

    # Speaker line: '''Name:''' text
    m = SPEAKER_RE.match(content)
    if m:
        speaker = strip_wiki_links(m.group(1).strip())
        text = strip_wiki_links(m.group(2).strip())
        return {"node_type": "line", "speaker": speaker, "text": text}

    # Fallback: plain text node
    return {"node_type": "line", "speaker": None, "text": strip_wiki_links(content)}


def parse_section_depth(line: str) -> tuple[int, str] | None:
    """Parse a section heading. Returns (heading_level, title) or None."""
    stripped = line.strip()
    if not stripped.startswith("=="):
        return None
    # Count leading = signs
    level = 0
    for ch in stripped:
        if ch == "=":
            level += 1
        else:
            break
    title = stripped.strip("= ")
    # == is level 2 in wikitext, normalize to 0-based
    return (level - 2, title)


def parse_dialogue_tree(wikitext: str) -> tuple[str | None, list[dict]]:
    """Parse transcript wikitext into (page_type, nodes).

    Each node dict has: parent_idx (index into the list or None),
    sort_order, depth, node_type, speaker, text, section.
    """
    page_type = parse_transcript_type(wikitext)
    nodes: list[dict] = []
    # depth → index of last node at that depth
    parent_at: dict[int, int] = {}
    sort_order = 0
    # Track current section heading path
    section_stack: list[str] = []

    for line in wikitext.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # Section headings
        heading = parse_section_depth(stripped)
        if heading is not None:
            level, title = heading
            # Trim section stack to this level and push
            section_stack = section_stack[:level]
            section_stack.append(title)
            # Reset parent tracking for * lines under new section
            parent_at.clear()
            continue

        # Dialogue lines (must start with *)
        if not stripped.startswith("*"):
            continue

        # Count * depth
        depth = 0
        for ch in stripped:
            if ch == "*":
                depth += 1
            else:
                break

        content = stripped[depth:].strip()
        if not content:
            continue

        node = parse_line_content(content)

        # Find parent: last node at depth - 1
        parent_idx = parent_at.get(depth - 1) if depth > 1 else None

        section = "/".join(section_stack) if section_stack else None

        nodes.append({
            "parent_idx": parent_idx,
            "sort_order": sort_order,
            "depth": depth,
            "node_type": node["node_type"],
            "speaker": node["speaker"],
            "text": node["text"],
            "section": section,
        })

        idx = len(nodes) - 1
        parent_at[depth] = idx
        # Clear deeper entries (new branch at this depth invalidates children)
        for d in [k for k in parent_at if k > depth]:
            del parent_at[d]

        sort_order += 1

    return page_type, nodes


def insert_dialogue(conn, page_title: str, page_type: str | None, nodes: list[dict]) -> int:
    """Insert a dialogue page and its nodes. Returns node count."""
    cur = conn.execute(
        "INSERT INTO dialogue_pages (title, page_type) VALUES (?, ?)",
        (page_title, page_type),
    )
    page_id = cur.lastrowid

    if not nodes:
        return 0

    # Insert nodes, tracking index → row ID for parent references
    idx_to_id: dict[int, int] = {}

    for i, node in enumerate(nodes):
        parent_id = idx_to_id.get(node["parent_idx"]) if node["parent_idx"] is not None else None
        cur = conn.execute(
            """INSERT INTO dialogue_nodes
               (page_id, parent_id, sort_order, depth, node_type, speaker, text, section)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                page_id,
                parent_id,
                node["sort_order"],
                node["depth"],
                node["node_type"],
                node["speaker"],
                node["text"],
                node["section"],
            ),
        )
        idx_to_id[i] = cur.lastrowid

    return len(nodes)


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    # Clear previous run in one shot
    conn.execute("DELETE FROM dialogue_nodes")
    conn.execute("DELETE FROM dialogue_pages")

    # Collect all transcript pages from subcategories
    all_pages: set[str] = set()
    for subcat in SUBCATEGORIES:
        pages = fetch_category_members(subcat, namespace=TRANSCRIPT_NS)
        print(f"  {subcat}: {len(pages)} pages", flush=True)
        all_pages.update(pages)

    pages_list = sorted(all_pages)
    print(f"Found {len(pages_list)} transcript pages total", flush=True)

    node_count = 0
    page_count = 0

    for i in range(0, len(pages_list), 50):
        batch = pages_list[i : i + 50]
        wikitext_batch = fetch_pages_wikitext_batch(batch)

        for page_title, wikitext in wikitext_batch.items():
            if not wikitext:
                continue

            page_type, nodes = parse_dialogue_tree(wikitext)

            # Derive display title (strip Transcript: prefix)
            display_title = page_title
            if display_title.startswith("Transcript:"):
                display_title = display_title[len("Transcript:"):]

            node_count += insert_dialogue(conn, display_title, page_type, nodes)
            page_count += 1

        print(f"  Fetched {i + len(batch)}/{len(pages_list)} pages, {node_count} nodes so far...", flush=True)

    print(f"Recording attributions for {len(pages_list)} pages...", flush=True)
    record_attributions_batch(conn, "dialogue_pages", pages_list)

    conn.commit()
    print(f"Inserted {node_count} dialogue nodes across {page_count} pages into {db_path}", flush=True)
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch OSRS dialogue trees")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    args = parser.parse_args()
    ingest(args.db)
