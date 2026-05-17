"""
Action Logement — full pipeline in one script.

Stage 1: Paginate the offers-overview search API -> stubs saved to debug/action_logement_search.json
Stage 2: Enrich each stub with municipality coordinates + picture dimensions -> debug/action_logement.json

Usage:
    python action_logement.py           # full run (search + enrich)
    python action_logement.py --enrich  # enrich only (re-read existing search results)
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from tqdm import tqdm

SEARCH_URL = "https://api.logement-actionlogement.fr/api/v1/demands/public/offers-overview"
SEARCH_RAW = Path(__file__).parent / "debug" / "action_logement_search.json"
OUTPUT_PATH = Path(__file__).parent / "debug" / "action_logement.json"

PAGE_SIZE = 20
INTER_PAGE_DELAY = 1.0
INTER_ITEM_DELAY = 0.3

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

GEO_API = "https://geo.api.gouv.fr/communes/{code}?fields=nom,code,codesPostaux,centre,surface,population,codeDepartement,codeRegion,departement,region"
GEO_HEADERS = {
    "accept": "application/json",
    "user-agent": "StudAI-Scraper/1.0 (student housing data collection)",
}

PICTURE_DIMENSIONS = ["small", "medium", "large", "original"]


# ── Stage 1: Search ───────────────────────────────────────────────────────────

def _fetch_page(session: requests.Session, page: int) -> dict:
    resp = session.post(
        SEARCH_URL,
        params={"size": PAGE_SIZE, "page": page},
        json=SEARCH_BODY,
        timeout=30,
    )
    resp.raise_for_status()
    try:
        return json.loads(resp.content.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(resp.content.decode("latin-1"))


def _search() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    all_items: list[dict] = []
    page = 0

    print("[action-logement] Stage 1: paginating search API...")
    with tqdm(desc="action-logement pages", unit="page") as pbar:
        while True:
            data = _fetch_page(session, page)

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
                    print(f"  [warn] Unexpected response shape. Keys: {list(data.keys())}")
                    debug_path = SEARCH_RAW.parent / f"action_logement_search_debug_p{page}.json"
                    debug_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    break
            else:
                print(f"  [warn] Unexpected type: {type(data)}")
                break

            if not items:
                break

            all_items.extend(items)
            pbar.update(1)
            pbar.set_postfix(total=len(all_items))

            if len(items) < PAGE_SIZE:
                break

            page += 1
            time.sleep(INTER_PAGE_DELAY)

    scraped_at = datetime.now(timezone.utc).isoformat()
    output = {"scraped_at": scraped_at, "total": len(all_items), "items": all_items}
    SEARCH_RAW.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_RAW.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[action-logement] {len(all_items)} stubs saved -> {SEARCH_RAW}")
    return all_items


# ── Stage 2: Enrich ───────────────────────────────────────────────────────────

_commune_cache: dict[str, dict] = {}


def _fetch_commune(session: requests.Session, insee_code: str) -> dict:
    if insee_code in _commune_cache:
        return _commune_cache[insee_code]
    try:
        r = session.get(GEO_API.format(code=insee_code), headers=GEO_HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            _commune_cache[insee_code] = data
            return data
    except requests.RequestException:
        pass
    return {}


def _commune_centre(commune: dict) -> tuple[float | None, float | None]:
    centre = commune.get("centre", {})
    coords = centre.get("coordinates", [])
    if len(coords) >= 2:
        return coords[1], coords[0]  # GeoJSON is [lng, lat]
    return None, None


def _enrich_pictures(session: requests.Session, pictures: list[dict], lodging_guid: str) -> list[dict]:
    enriched: list[dict] = []
    prefix = lodging_guid[:2]
    for pic in pictures:
        entry: dict = {
            "ordering": pic.get("ordering"),
            "content_type": pic.get("urlContentType"),
            "urls": {},
        }
        original_url: str = pic.get("url", "")
        entry["urls"]["medium"] = original_url

        pic_guid = None
        if original_url:
            parts = original_url.split("?")[0].split("/")
            if len(parts) >= 2:
                pic_guid = parts[-1]

        if pic_guid and lodging_guid:
            base = f"https://assets.logement-actionlogement.fr/lodgings/{prefix}/{lodging_guid}"
            for dim in PICTURE_DIMENSIONS:
                if dim == "medium":
                    continue
                url = f"{base}/{dim}/{pic_guid}"
                try:
                    r = session.head(url, timeout=8, allow_redirects=True)
                    if r.status_code == 200:
                        entry["urls"][dim] = url
                except requests.RequestException:
                    pass

        enriched.append(entry)
    return enriched


def _flatten_item(item: dict, commune_data: dict) -> dict:
    lodging = item.get("lodging", {}) or {}
    residency = item.get("residency", {}) or {}
    municipality = lodging.get("municipality", {}) or {}
    lodging_type = residency.get("type", {}) or {}
    product = lodging_type.get("product", {}) or {}
    lodging_cat = lodging.get("lodgingCategory", {}) or {}
    lodging_typo = lodging.get("lodgingTypology", {}) or {}
    payment_type = item.get("paymentType", {}) or {}

    lat, lng = _commune_centre(commune_data)

    return {
        "id": item.get("id"),
        "guid": item.get("guid"),
        "reference": item.get("reference"),
        "available_at": item.get("availableAt"),
        "start_date_of_publication": item.get("startDateOfPublication"),
        "is_first_time_available": item.get("isLodgingFirstTimeAvailable"),
        "is_recent": item.get("isRecent"),
        "is_new_lodging": item.get("isNewLodging"),
        "rent_type": item.get("rentType"),
        "rent_total_cc": item.get("totalRentAmountBaseBound"),
        "rent_progressive": item.get("totalProgressiveRentAmount"),
        "payment_type_code": payment_type.get("code"),
        "payment_type_label": payment_type.get("label"),
        "agency_fees_requested": item.get("areAgencyFeesRequested"),
        "agency_fees_amount": item.get("agencyFeesAmount"),
        "estimated_external_charges": item.get("estimatedExternalCharges"),
        "description": item.get("description") or lodging.get("description"),
        "lodging_id": lodging.get("id"),
        "lodging_guid": lodging.get("guid"),
        "lodging_reference": lodging.get("reference"),
        "lodging_type": lodging.get("lodgingType"),
        "lodging_category_code": lodging_cat.get("code"),
        "lodging_category_label": lodging_cat.get("label"),
        "lodging_typology_code": lodging_typo.get("code"),
        "lodging_typology_label": lodging_typo.get("label"),
        "lodging_typology_commercial_label": lodging_typo.get("commercialLabel"),
        "area_m2": lodging.get("area"),
        "municipality_id": municipality.get("id"),
        "municipality_code": municipality.get("code"),
        "municipality_postcode": municipality.get("postcode"),
        "municipality_name": municipality.get("name"),
        "lat": lat,
        "lng": lng,
        "commune_surface_km2": commune_data.get("surface"),
        "commune_population": commune_data.get("population"),
        "commune_departement_code": commune_data.get("codeDepartement"),
        "commune_departement_name": (commune_data.get("departement") or {}).get("nom"),
        "commune_region_code": commune_data.get("codeRegion"),
        "commune_region_name": (commune_data.get("region") or {}).get("nom"),
        "residency_id": residency.get("id"),
        "residency_guid": residency.get("guid"),
        "residency_name": residency.get("name"),
        "residency_type_code": lodging_type.get("code"),
        "residency_type_label": lodging_type.get("label"),
        "product_code": product.get("code"),
        "product_label": product.get("label"),
        "pictures": item.get("pictures", []),
        "candidacy": item.get("candidacy"),
    }


def _enrich(items: list[dict]) -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    results: list[dict] = []
    scraped_at = datetime.now(timezone.utc).isoformat()

    print(f"[action-logement] Stage 2: enriching {len(items)} listings with geocodes...")
    for stub in tqdm(items, desc="action-logement enrich", unit="item"):
        lodging = stub.get("lodging", {}) or {}
        municipality = lodging.get("municipality", {}) or {}
        insee_code = municipality.get("code", "")
        lodging_guid = lodging.get("guid", "")

        commune = _fetch_commune(session, insee_code) if insee_code else {}
        flat = _flatten_item(stub, commune)

        pics = stub.get("pictures", [])
        if pics and lodging_guid:
            flat["pictures"] = _enrich_pictures(session, pics, lodging_guid)

        flat["_scraped_at"] = scraped_at
        results.append(flat)
        time.sleep(INTER_ITEM_DELAY)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[action-logement] {len(results)} records saved -> {OUTPUT_PATH}")
    return results


# ── Entry point ───────────────────────────────────────────────────────────────

def fetch() -> list[dict]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--enrich", action="store_true")
    args, _ = parser.parse_known_args()

    if args.enrich:
        if not SEARCH_RAW.exists():
            raise FileNotFoundError(f"{SEARCH_RAW} not found — run without --enrich first")
        raw = json.loads(SEARCH_RAW.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else raw.get("items", [])
        print(f"[action-logement] Loaded {len(items)} stubs from {SEARCH_RAW}")
    else:
        items = _search()

    return _enrich(items)


if __name__ == "__main__":
    fetch()
