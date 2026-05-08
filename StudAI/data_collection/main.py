"""
StudAI data collection pipeline.

Stages
------
1. Scrape  — each source fetches all available data and writes to raw/<source>.json
2. Normalise — reads raw/ and writes the enriched App/src/data/housing.json
3. Infra (optional) — refreshes transit/stations data for the map

Usage
-----
  python main.py              # scrape housing sources + normalise (default)
  python main.py --normalise  # normalise only (re-read existing raw/ files)
  python main.py --all        # housing + normalise + infrastructure
  python main.py --infra      # infrastructure only
"""
from __future__ import annotations

import argparse
import sys

import studyrama
import nexity_studea
import normalize
import paris_stations
import paris_transit


def run_scrapers() -> None:
    try:
        studyrama.fetch()
    except Exception as exc:
        print(f"[main] WARNING: studyrama scraper failed: {exc}")

    try:
        nexity_studea.fetch()
    except Exception as exc:
        print(f"[main] WARNING: nexity-studea scraper failed: {exc}")


def run_housing() -> None:
    run_scrapers()
    normalize.run()


def run_infrastructure() -> None:
    paris_stations.main()
    paris_transit.main()


def main() -> int:
    parser = argparse.ArgumentParser(description="StudAI data collection pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--normalise", action="store_true", help="Normalise only (skip scraping)")
    group.add_argument("--all", action="store_true", help="Housing + infrastructure")
    group.add_argument("--infra", action="store_true", help="Infrastructure only")
    args = parser.parse_args()

    if args.infra:
        run_infrastructure()
    elif args.all:
        run_housing()
        run_infrastructure()
    elif args.normalise:
        normalize.run()
    else:
        run_housing()

    return 0


if __name__ == "__main__":
    sys.exit(main())
