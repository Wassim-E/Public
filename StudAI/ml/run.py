"""
StudAI data pipeline entry point.

Usage
-----
  python run.py                    # scrape all housing sources + aggregate
  python run.py --aggregate        # aggregate only (re-read existing debug/ files)
  python run.py --all              # housing + aggregate + infrastructure
  python run.py --infra            # infrastructure only (stations + transit)
  python run.py --reviews          # scrape Google reviews only
  python run.py --reviews --resume # resume Google reviews (skip already-done IDs)

All commands run synchronously and print explicit progress via tqdm.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure each sub-package is importable
sys.path.insert(0, str(Path(__file__).parent))

import studyrama.studyrama as _studyrama
import nexity_studea.nexity_studea as _nexity
import action_logement.action_logement as _action_logement
import aggregator as _aggregator
import infrastructure.paris_stations as _stations
import infrastructure.paris_transit as _transit


def run_scrapers() -> None:
    print("\n=== Studyrama ===")
    try:
        _studyrama.fetch()
    except Exception as exc:
        print(f"[main] WARNING: studyrama scraper failed: {exc}")

    print("\n=== Nexity Studéa ===")
    try:
        _nexity.fetch()
    except Exception as exc:
        print(f"[main] WARNING: nexity-studea scraper failed: {exc}")

    print("\n=== Action Logement ===")
    try:
        _action_logement.fetch()
    except Exception as exc:
        print(f"[main] WARNING: action-logement scraper failed: {exc}")


def run_housing() -> None:
    run_scrapers()
    print("\n=== Aggregator ===")
    _aggregator.run()


def run_infrastructure() -> None:
    print("\n=== Paris Stations ===")
    _stations.main()
    print("\n=== Paris Transit ===")
    _transit.main()


def main() -> int:
    parser = argparse.ArgumentParser(description="StudAI data pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--aggregate", action="store_true", help="Aggregate only (skip scraping)")
    group.add_argument("--all",       action="store_true", help="Housing + aggregate + infrastructure")
    group.add_argument("--infra",     action="store_true", help="Infrastructure only")
    group.add_argument("--reviews",   action="store_true", help="Google reviews only")
    parser.add_argument("--resume",   action="store_true", help="(--reviews) skip already-scraped IDs")
    args = parser.parse_args()

    if args.infra:
        run_infrastructure()
    elif args.all:
        run_housing()
        run_infrastructure()
    elif args.aggregate:
        print("\n=== Aggregator ===")
        _aggregator.run()
    elif args.reviews:
        import google_reviews.google_reviews as _reviews
        import sys as _sys
        _sys.argv = ["google_reviews.py"] + (["--resume"] if args.resume else [])
        _reviews.main()
    else:
        run_housing()

    return 0


if __name__ == "__main__":
    sys.exit(main())
