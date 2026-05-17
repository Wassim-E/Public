"""
Action Logement — Step 2: Enrich each listing with municipality coordinates.

Reads raw/action_logement_search.json, enriches every item with:
  - Municipality lat/lng from the French government's commune API
  - All available picture dimensions (small / medium / large / original)
  - A clean, flat field layout

Writes raw/action_logement.json.

Usage:
    python action_logement_details.py
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

SEARCH_RAW = Path(__file__).parent / "raw" / "action_logement_search.json"
OUTPUT_PATH = Path(__file__).parent / "raw" / "action_logement.json"

# French government's commune API — fully public, no auth
GEO_API = "https://geo.api.gouv.fr/communes/{code}?fields=nom,code,codesPostaux,centre,surface,population,codeDepartement,codeRegion,departement,region"

PICTURE_DIMENSIONS = ["small", "medium", "large", "original"]
INTER_ITEM_DELAY = 0.3  # seconds

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "fr-FR,fr;q=0.9",
    "cache-control": "no-cache",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}

GEO_HEADERS = {
    "accept": "application/json",
    "user-agent": "StudAI-Scraper/1.0 (student housing data collection)",
}


# ── Commune geocoding ─────────────────────────────────────────────────────────

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


# ── Picture enrichment ────────────────────────────────────────────────────────

def _enrich_pictures(session: requests.Session, pictures: list[dict], lodging_guid: str) -> list[dict]:
    """
    The search only returns MEDIUM-dimension signed URLs.
    We try to get each picture in all dimensions by requesting fresh signed URLs
    from the assets host directly.  If that fails we keep the original medium URL.

    Signed S3 URLs are path-specific, so we cannot simply swap 'medium' → 'large'
    in the URL.  Instead we try an unsigned GET on the large/original path — if the
    bucket allows public access the image loads, otherwise we fall back to medium.
    """
    enriched: list[dict] = []
    prefix = lodging_guid[:2]

    for pic in pictures:
        entry: dict = {
            "ordering": pic.get("ordering"),
            "content_type": pic.get("urlContentType"),
            "urls": {},
        }

        original_url: str = pic.get("url", "")
        entry["urls"]["medium"] = original_url  # always available (signed, ~6h TTL)

        # Try to find picture guid from the signed URL path
        # URL pattern: .../lodgings/{prefix}/{lodging_guid}/{dimension}/{picture_guid}?...
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


# ── Item flattening ───────────────────────────────────────────────────────────

def _flatten_item(item: dict, commune_data: dict) -> dict:
    """Produce a clean, flat dict from one search stub + commune data."""
    lodging = item.get("lodging", {}) or {}
    residency = item.get("residency", {}) or {}
    municipality = lodging.get("municipality", {}) or {}
    lodging_type = residency.get("type", {}) or {}
    product = lodging_type.get("product", {}) or {}
    lodging_cat = lodging.get("lodgingCategory", {}) or {}
    lodging_typo = lodging.get("lodgingTypology", {}) or {}
    payment_type = item.get("paymentType", {}) or {}

    lat, lng = _commune_centre(commune_data)

    out: dict = {
        # Identifiers
        "id": item.get("id"),
        "guid": item.get("guid"),
        "reference": item.get("reference"),
        # Offer metadata
        "available_at": item.get("availableAt"),
        "start_date_of_publication": item.get("startDateOfPublication"),
        "is_first_time_available": item.get("isLodgingFirstTimeAvailable"),
        "is_recent": item.get("isRecent"),
        "is_new_lodging": item.get("isNewLodging"),
        "rent_type": item.get("rentType"),
        "orientation_code": item.get("orientationCode"),
        # Financials
        "rent_total_cc": item.get("totalRentAmountBaseBound"),
        "rent_progressive": item.get("totalProgressiveRentAmount"),
        "payment_type_code": payment_type.get("code"),
        "payment_type_label": payment_type.get("label"),
        "agency_fees_requested": item.get("areAgencyFeesRequested"),
        "agency_fees_amount": item.get("agencyFeesAmount"),
        "estimated_external_charges": item.get("estimatedExternalCharges"),
        # Description
        "description": item.get("description") or lodging.get("description"),
        # Lodging details
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
        # Municipality / Location
        "municipality_id": municipality.get("id"),
        "municipality_code": municipality.get("code"),  # INSEE code
        "municipality_postcode": municipality.get("postcode"),
        "municipality_name": municipality.get("name"),
        # Geocoordinates from geo.api.gouv.fr
        "lat": lat,
        "lng": lng,
        "commune_surface_km2": commune_data.get("surface"),
        "commune_population": commune_data.get("population"),
        "commune_departement_code": commune_data.get("codeDepartement"),
        "commune_departement_name": (commune_data.get("departement") or {}).get("nom"),
        "commune_region_code": commune_data.get("codeRegion"),
        "commune_region_name": (commune_data.get("region") or {}).get("nom"),
        # Residency
        "residency_id": residency.get("id"),
        "residency_guid": residency.get("guid"),
        "residency_name": residency.get("name"),
        "residency_type_code": lodging_type.get("code"),
        "residency_type_label": lodging_type.get("label"),
        "product_code": product.get("code"),
        "product_label": product.get("label"),
        # Pictures kept as-is (medium signed URLs, ~6h TTL)
        "pictures": item.get("pictures", []),
        # Candidacy (may be null for public view)
        "candidacy": item.get("candidacy"),
    }
    return out


# ── Main ─────────────────────────────────────────────────────────────────────

def fetch() -> list[dict]:
    if not SEARCH_RAW.exists():
        raise FileNotFoundError(
            f"{SEARCH_RAW} not found — run action_logement_search.py first."
        )

    raw = json.loads(SEARCH_RAW.read_text(encoding="utf-8"))
    items: list[dict] = raw if isinstance(raw, list) else raw.get("items", [])
    print(f"[action-logement-detail] Enriching {len(items)} listings...")

    session = requests.Session()
    session.headers.update(HEADERS)

    results: list[dict] = []
    scraped_at = datetime.now(timezone.utc).isoformat()

    for i, stub in enumerate(items):
        lodging = stub.get("lodging", {}) or {}
        municipality = lodging.get("municipality", {}) or {}
        insee_code = municipality.get("code", "")
        lodging_guid = lodging.get("guid", "")
        name = (stub.get("residency") or {}).get("name", f"item-{i}")

        print(f"  [{i+1}/{len(items)}] {name} — {municipality.get('name', '?')}")

        # Geocode the commune
        commune = _fetch_commune(session, insee_code) if insee_code else {}

        # Build flat record
        flat = _flatten_item(stub, commune)

        # Try picture dimension enrichment (best-effort)
        pics = stub.get("pictures", [])
        if pics and lodging_guid:
            flat["pictures"] = _enrich_pictures(session, pics, lodging_guid)

        flat["_scraped_at"] = scraped_at
        results.append(flat)
        time.sleep(INTER_ITEM_DELAY)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[action-logement-detail] {len(results)} records saved to {OUTPUT_PATH}")
    return results


if __name__ == "__main__":
    fetch()
