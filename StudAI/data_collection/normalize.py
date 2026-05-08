"""
Read raw scraped data from raw/ and produce the enriched housing.json.

Input:  raw/studyrama.json, raw/nexity_studea.json
Output: App/src/data/housing.json

Merge strategy
--------------
When two records are within 150 m (same physical building from different
sources), they are MERGED rather than deduplicated:
  - scalar fields: prefer non-null, prefer studyrama for rent/surface baseline
  - lists (amenities, images, rooms): combine + deduplicate
  - description: prefer the longer one
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from math import cos, radians, sqrt
from pathlib import Path

RAW_DIR = Path(__file__).parent / "raw"
OUTPUT = Path(__file__).resolve().parents[1] / "App" / "src" / "data" / "housing.json"

PARIS_LAT, PARIS_LNG = 48.8566, 2.3522
DEDUP_KM = 0.15   # 150 m


# ── Geo ───────────────────────────────────────────────────────────────────────

def _km(lat1: float, lng1: float, lat2: float = PARIS_LAT, lng2: float = PARIS_LNG) -> float:
    R = 6371.0
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = (dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * (dlng / 2) ** 2
    return R * 2 * sqrt(a)


def _dist_str(lat: float, lng: float) -> str:
    return f"{_km(lat, lng):.2f} km".replace(".", ",")


# ── Amenity normalisation ─────────────────────────────────────────────────────

# Each entry: (regex pattern, canonical label)
_AMENITY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"wifi|wi-fi|internet|haut.?d.bit", re.I), "WiFi"),
    (re.compile(r"parking|garage|stationnement", re.I), "Parking"),
    (re.compile(r"laverie|laundry|lave-linge", re.I), "Laverie"),
    (re.compile(r"ascenseur|elevator|lift", re.I), "Ascenseur"),
    (re.compile(r"salle.de.sport|sport|gym|fitness", re.I), "Salle de sport"),
    (re.compile(r"v[eé]lo|deux.?roues|bicycl", re.I), "Local vélos"),
    (re.compile(r"vid[eé]o.?surv|surveillance|cam[eé]ra|cctv", re.I), "Vidéosurveillance"),
    (re.compile(r"m[eé]nage|nettoyage|cleaning|entretien.inclus", re.I), "Service ménage"),
    (re.compile(r"caf[eé]|cafet|salle.commune|polyvalente|lounge", re.I), "Espace commun"),
    (re.compile(r"salle.info|informatique|ordinateur|computer", re.I), "Salle informatique"),
    (re.compile(r"accueil|r[eé]ception|concierge|intendant", re.I), "Accueil"),
    (re.compile(r"interphone|digicode|visiophone", re.I), "Interphone"),
    (re.compile(r"piscine|pool", re.I), "Piscine"),
    (re.compile(r"jardin|green|espace.vert|terrasse", re.I), "Jardin / Terrasse"),
    (re.compile(r"meub[lé]|furnished|studio.meub", re.I), "Meublé"),
    (re.compile(r"kit.vaisselle|vaisselle", re.I), "Kit vaisselle"),
    (re.compile(r"pr[eê]t.de.mat[eé]riel|mat[eé]riel", re.I), "Prêt matériel"),
    (re.compile(r"distributeur", re.I), "Distributeur"),
    (re.compile(r"local.poubelle|d[eé]chets", re.I), "Local poubelles"),
]

_seen_unmapped: set[str] = set()


def _normalize_amenity(raw: str) -> str:
    """Map a raw service string to a canonical label."""
    for pattern, canonical in _AMENITY_PATTERNS:
        if pattern.search(raw):
            return canonical
    return raw  # keep as-is if no canonical match found


def _merge_amenities(a: list[str], b: list[str]) -> list[str]:
    """Combine two amenity lists, collapsing to canonical names and deduplicating."""
    canonical: dict[str, str] = {}  # canonical_label → first raw value
    for raw in [*a, *b]:
        canon = _normalize_amenity(raw)
        if canon not in canonical:
            canonical[canon] = canon
    return list(canonical.keys())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


def _clean(val) -> str | None:
    if not val:
        return None
    s = str(val).strip()
    return s or None


def _merge_images(a: list[str], b: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for url in [*a, *b]:
        if url and url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _merge_rooms(a: list[dict], b: list[dict]) -> list[dict]:
    """Prefer the list with more detail fields filled; combine if very different."""
    if not a:
        return b
    if not b:
        return a
    # Pick the set with more non-null fields on average
    def _score(rooms: list[dict]) -> float:
        if not rooms:
            return 0
        return sum(sum(1 for v in r.values() if v is not None) for r in rooms) / len(rooms)
    return a if _score(a) >= _score(b) else b


def _merge_records(base: dict, extra: dict) -> dict:
    """Merge `extra` into `base`. Lists are combined; scalars fill nulls."""
    result = dict(base)
    for key, bval in extra.items():
        if key.startswith("_") or key == "id":
            continue
        aval = result.get(key)

        if aval is None and bval is not None:
            result[key] = bval
        elif isinstance(aval, list) and isinstance(bval, list) and bval:
            if key == "amenities":
                result[key] = _merge_amenities(aval, bval)
            elif key == "images":
                result[key] = _merge_images(aval, bval)
            elif key == "rooms":
                result[key] = _merge_rooms(aval, bval)
        elif key == "description" and bval and (not aval or len(str(bval)) > len(str(aval))):
            result[key] = bval
        elif key == "imageUrl" and not aval and bval:
            result[key] = bval

    # Re-derive rent/surface from merged rooms if available
    rooms = result.get("rooms") or []
    rents = [r.get("rent") for r in rooms if r.get("rent")]
    surfs = [r.get("surface") for r in rooms if r.get("surface")]
    if rents:
        result["rent"] = result["rent"] or min(rents)
        result["rentMax"] = max(rents)
    if surfs:
        result["surface"] = result["surface"] or min(surfs)
        result["surfaceMax"] = max(surfs)

    # imageUrl from first image if missing
    if not result.get("imageUrl") and result.get("images"):
        result["imageUrl"] = result["images"][0]

    return result


# ── Per-source normalisers ────────────────────────────────────────────────────

def _norm_studyrama(item: dict) -> dict | None:
    # Use precise JSON-LD geo if available, else list API coords
    lat = item.get("geo_lat") or item.get("lat")
    lng = item.get("geo_lng") or item.get("lng")
    if not lat or not lng:
        return None

    raw_alt = ((item.get("logo_annonceur") or {}).get("alt") or "").strip()
    type_str = item.get("type") or ""
    is_crous = "crous" in raw_alt.lower() or "crous" in type_str.lower()
    if is_crous:
        provider, category = "CROUS", "crous"
    else:
        provider = raw_alt.replace("Logo ", "").strip() or None
        category = "private"

    url = (BASE_URL + item["url"]) if item.get("url") else None
    image_url = ((item.get("image") or {}).get("image")) or None

    # Images: prefer detail page carousel (19 photos) over single list image
    detail_images: list[str] = item.get("detail_images") or []
    all_images = _merge_images(detail_images, [image_url] if image_url else [])
    if not image_url and all_images:
        image_url = all_images[0]

    # Rooms: from detail page HTML table, supplemented by JSON-LD containsPlace
    html_rooms = item.get("detail_rooms") or []
    jsonld_rooms = item.get("jsonld_rooms") or []
    # Prefer HTML table (has furnished info); fall back to JSON-LD
    raw_rooms = html_rooms or jsonld_rooms

    norm_rooms = []
    for r in raw_rooms:
        norm_rooms.append({
            "type": _clean(r.get("type") or r.get("name")),
            "rent": _to_int(r.get("rent")),
            "surface": _to_int(r.get("surface_m2")),
            "furnished": r.get("furnished"),
            "available": None,
            "floor": None,
            "deposit": None,
            "applicationFee": None,
            "energyClass": None,
            "ghgClass": None,
        })

    # Rent / surface from rooms if richer, else list API
    rents = [r["rent"] for r in norm_rooms if r.get("rent")]
    surfs = [r["surface"] for r in norm_rooms if r.get("surface")]
    rent_min = min(rents) if rents else _to_int(item.get("loyer"))
    rent_max = max(rents) if len(rents) > 1 else None
    surf_min = min(surfs) if surfs else _to_int(item.get("surface"))
    surf_max = max(surfs) if len(surfs) > 1 else None

    # Amenities: included services are free, extra are paid (mark with "†")
    included = item.get("services_included") or []
    extra = [f"{s} (supplément)" for s in (item.get("services_extra") or [])]
    raw_amenities = included + extra
    amenities = [_normalize_amenity(a) for a in raw_amenities]
    # Deduplicate keeping order
    seen: set[str] = set()
    amenities = [a for a in amenities if not (a in seen or seen.add(a))]  # type: ignore

    # Mark as Meublé if any room is furnished
    if any(r.get("furnished") for r in norm_rooms) and "Meublé" not in amenities:
        amenities.append("Meublé")

    return {
        "id": f"studyrama-{item['id']}",
        "name": _clean(item.get("titre")) or "Unknown",
        "provider": provider,
        "category": category,
        "lat": lat,
        "lng": lng,
        "rent": rent_min,
        "rentMax": rent_max,
        "surface": surf_min,
        "surfaceMax": surf_max,
        "type": _clean(item.get("type")),
        "distance": item.get("distance") or _dist_str(lat, lng),
        "url": url,
        "imageUrl": image_url,
        "images": all_images,
        "description": _clean(item.get("description")),
        "amenities": amenities,
        "phone": None,
        "address": _clean(item.get("address")),
        "rooms": norm_rooms,
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


BASE_URL = "https://logement.studyrama.com"


def _norm_nexity(item: dict) -> dict | None:
    lat = item.get("poi_lat")
    lng = item.get("poi_lng")
    if not lat or not lng:
        return None

    rooms_raw = item.get("rooms") or []
    rents = [r["rent_cc"] for r in rooms_raw if r.get("rent_cc")]
    surfs = [r["surface_m2"] for r in rooms_raw if r.get("surface_m2")]
    rent_min = min(rents) if rents else item.get("search_price_min")
    rent_max = max(rents) if len(rents) > 1 else None
    surf_min = min(surfs) if surfs else None
    surf_max = max(surfs) if len(surfs) > 1 else None

    images = _merge_images(
        item.get("images") or [],
        [item.get("search_image_url")] if item.get("search_image_url") else [],
    )

    norm_rooms = [{
        "type": r.get("type"),
        "rent": r.get("rent_cc"),
        "surface": r.get("surface_m2"),
        "furnished": None,
        "available": r.get("available"),
        "floor": r.get("floor"),
        "deposit": r.get("deposit"),
        "applicationFee": r.get("application_fee"),
        "energyClass": r.get("energy_class"),
        "ghgClass": r.get("ghg_class"),
    } for r in rooms_raw]

    raw_amenities = item.get("services") or []
    amenities_seen: set[str] = set()
    amenities: list[str] = []
    for a in raw_amenities:
        canon = _normalize_amenity(a)
        if canon not in amenities_seen:
            amenities_seen.add(canon)
            amenities.append(canon)

    return {
        "id": f"nexity-studea-{item['reference']}",
        "name": item["name"].title(),
        "provider": "Nexity Studéa",
        "category": "private",
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "rent": _to_int(rent_min),
        "rentMax": _to_int(rent_max),
        "surface": _to_int(surf_min),
        "surfaceMax": _to_int(surf_max),
        "type": "Résidence étudiante",
        "distance": _dist_str(lat, lng),
        "url": item.get("search_url"),
        "imageUrl": images[0] if images else None,
        "images": images,
        "description": _clean(item.get("description")),
        "amenities": amenities,
        "phone": _clean(item.get("phone")),
        "address": _clean(item.get("address")),
        "rooms": norm_rooms,
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


# ── Dedup + merge ─────────────────────────────────────────────────────────────

def _richness(r: dict) -> int:
    score = 0
    for v in r.values():
        if v is None:
            continue
        if isinstance(v, (list, str)) and not v:
            continue
        score += 1
    return score


def _deduplicate_and_merge(residences: list[dict]) -> list[dict]:
    """
    Residences within 150 m are considered the same building.
    Instead of dropping one, MERGE them: the first found is the base,
    subsequent matches are merged into it.
    """
    kept: list[dict] = []
    for res in residences:
        lat, lng = res["lat"], res["lng"]
        dup_idx = next(
            (i for i, k in enumerate(kept) if _km(lat, lng, k["lat"], k["lng"]) < DEDUP_KM),
            None,
        )
        if dup_idx is None:
            kept.append(res)
        else:
            kept[dup_idx] = _merge_records(kept[dup_idx], res)
    return kept


# ── Entry point ───────────────────────────────────────────────────────────────

def run() -> list[dict]:
    all_residences: list[dict] = []

    sr_path = RAW_DIR / "studyrama.json"
    if sr_path.exists():
        raw = json.loads(sr_path.read_text(encoding="utf-8"))
        normed = [_norm_studyrama(r) for r in raw]
        valid = [r for r in normed if r]
        print(f"[normalize] studyrama: {len(raw)} raw -> {len(valid)} valid")
        all_residences.extend(valid)
    else:
        print("[normalize] WARN: raw/studyrama.json not found")

    nx_path = RAW_DIR / "nexity_studea.json"
    if nx_path.exists():
        raw = json.loads(nx_path.read_text(encoding="utf-8"))
        normed = [_norm_nexity(r) for r in raw]
        valid = [r for r in normed if r]
        print(f"[normalize] nexity-studea: {len(raw)} raw -> {len(valid)} valid")
        all_residences.extend(valid)
    else:
        print("[normalize] WARN: raw/nexity_studea.json not found")

    print(f"[normalize] Total before dedup+merge: {len(all_residences)}")
    merged = _deduplicate_and_merge(all_residences)
    print(f"[normalize] Total after dedup+merge:  {len(merged)}")

    providers: dict[str, int] = {}
    for r in merged:
        p = r.get("provider") or "Unknown"
        providers[p] = providers.get(p, 0) + 1
    print("[normalize] By provider:", dict(sorted(providers.items(), key=lambda x: -x[1])))

    # Count how many have amenities, rooms, description
    print(f"[normalize] With amenities: {sum(1 for r in merged if r.get('amenities'))}")
    print(f"[normalize] With rooms:     {sum(1 for r in merged if r.get('rooms'))}")
    print(f"[normalize] With desc:      {sum(1 for r in merged if r.get('description'))}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[normalize] Saved {len(merged)} residences to {OUTPUT}")
    return merged


if __name__ == "__main__":
    run()
