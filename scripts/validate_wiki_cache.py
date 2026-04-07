"""Bulk-validate the wiki cache against current revision IDs.

Bumps fetched_at on entries that are still current, evicts stale ones.
Run this before ingestion to avoid per-page revid checks during fetches.
"""

import argparse
from pathlib import Path

from ragger.wiki import WikiCache


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate wiki cache revision IDs")
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path("data/wiki-cache.db"),
        help="Path to the wiki cache database",
    )
    args = parser.parse_args()

    cache = WikiCache(args.cache)
    cache.validate()
    cache.close()


if __name__ == "__main__":
    main()
