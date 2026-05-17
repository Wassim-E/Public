"""
Action Logement — Step 1: Paginate the offers-overview search API.

Saves every listing stub (all fields returned by the search endpoint) to
raw/action_logement_search.json.  Run this before action_logement_details.py.

Usage:
    python action_logement_search.py
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

SEARCH_URL = "https://api.logement-actionlogement.fr/api/v1/demands/public/offers-overview"
RAW_PATH = Path(__file__).parent / "raw" / "action_logement_search.json"

PAGE_SIZE = 20
INTER_PAGE_DELAY = 1.0  # seconds between pages

SEARCH_BODY = {
    "municipalities": [{"code": "75056", "postcode": "75001"}],
    "searchRadiusInKm": 5,
    "typologyCodes": [],
    "productGuids": [],
}

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "fr-FR,fr;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "pragma": "no-cache",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
    "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}


def _fetch_page(session: requests.Session, page: int) -> dict:
    resp = session.post(
        SEARCH_URL,
        params={"size": PAGE_SIZE, "page": page},
        json=SEARCH_BODY,
        timeout=30,
    )
    resp.raise_for_status()
    # The API returns Latin-1 encoded strings despite claiming JSON/UTF-8.
    # Force correct decoding from raw bytes.
    try:
        return json.loads(resp.content.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(resp.content.decode("latin-1"))


def fetch() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    all_items: list[dict] = []
    page = 0

    while True:
        print(f"[action-logement] Fetching page {page}...")
        data = _fetch_page(session, page)

        # The API may wrap results in a 'content', 'items', 'data', or 'offers' key.
        # We try common patterns and fall back to the raw dict.
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (
                data.get("content")
                or data.get("items")
                or data.get("data")
                or data.get("offers")
                or data.get("results")
                or []
            )
            if not items and "totalElements" not in data and "total" not in data:
                # Might be a single-page response with nested structure — dump all keys
                print(f"  [warn] Unexpected response shape. Keys: {list(data.keys())}")
                print(f"  Full response saved to raw/action_logement_search_debug_p{page}.json")
                _debug_dump(data, page)
                break
        else:
            print(f"  [warn] Unexpected type: {type(data)}")
            break

        if not items:
            print(f"  No items on page {page}, stopping.")
            break

        print(f"  {len(items)} items on page {page}")
        all_items.extend(items)

        # Stop when the page returned fewer items than the page size
        if len(items) < PAGE_SIZE:
            break

        page += 1
        time.sleep(INTER_PAGE_DELAY)

    scraped_at = datetime.now(timezone.utc).isoformat()
    output = {"scraped_at": scraped_at, "total": len(all_items), "items": all_items}

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[action-logement] {len(all_items)} total items saved to {RAW_PATH}")
    return all_items


def _debug_dump(data: dict, page: int) -> None:
    path = RAW_PATH.parent / f"action_logement_search_debug_p{page}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    fetch()
