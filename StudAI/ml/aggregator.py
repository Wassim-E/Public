"""
Aggregate per-source debug JSON files into a single housing.json for the frontend.

Inputs (all optional — missing sources are skipped with a warning):
  studyrama/debug/studyrama.json
  nexity_studea/debug/nexity_studea.json
  action_logement/debug/action_logement.json
  google_reviews/debug/google_reviews.json

Output:
  App/src/data/housing.json
  App/public/data/housing.json

Data model
----------
Each merged record contains:
  - Canonical scalar fields (name, lat, lng, address, description, …)
  - amenities: union from all sources, normalized to canonical labels
  - prices[]: one PriceSource object per contributing scraper
  - sources[]: list of source keys that contributed
  - rent / rentMax / surface / surfaceMax: aggregated min/max across prices[]
  - googleRating / googleRatingCount / googleReviews / googleMapsUrl: from google_reviews
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from math import cos, radians, sqrt
from pathlib import Path

ML_DIR = Path(__file__).parent
APP_DATA = ML_DIR.parent / "App" / "src" / "data"
APP_PUBLIC_DATA = ML_DIR.parent / "App" / "public" / "data"
OUTPUT = APP_DATA / "housing.json"

PARIS_LAT, PARIS_LNG = 48.8566, 2.3522
DEDUP_KM = 0.05   # 50 m same-source; cross-source uses name only


# ── Geo ───────────────────────────────────────────────────────────────────────

def _km(lat1: float, lng1: float, lat2: float = PARIS_LAT, lng2: float = PARIS_LNG) -> float:
    R = 6371.0
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = (dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * (dlng / 2) ** 2
    return R * 2 * sqrt(a)


def _dist_str(lat: float, lng: float) -> str:
    return f"{_km(lat, lng):.2f} km".replace(".", ",")


# ── Name normalisation ────────────────────────────────────────────────────────

def _norm_name(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ── Amenity normalisation ─────────────────────────────────────────────────────

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


def _normalize_amenity(raw: str) -> str:
    for pattern, canonical in _AMENITY_PATTERNS:
        if pattern.search(raw):
            return canonical
    return raw


def _merge_amenities(a: list[str], b: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for raw in [*a, *b]:
        canon = _normalize_amenity(raw)
        if canon not in seen:
            seen[canon] = canon
    return list(seen.keys())


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


# ── Per-source normalisers ────────────────────────────────────────────────────

BASE_STUDYRAMA = "https://logement.studyrama.com"


def _norm_studyrama(item: dict) -> dict | None:
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

    url = (BASE_STUDYRAMA + item["url"]) if item.get("url") else None
    image_url = ((item.get("image") or {}).get("image")) or None

    detail_images: list[str] = item.get("detail_images") or []
    all_images = _merge_images(detail_images, [image_url] if image_url else [])
    if not image_url and all_images:
        image_url = all_images[0]

    html_rooms = item.get("detail_rooms") or []
    jsonld_rooms = item.get("jsonld_rooms") or []
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

    rents = [r["rent"] for r in norm_rooms if r.get("rent")]
    surfs = [r["surface"] for r in norm_rooms if r.get("surface")]
    rent_min = min(rents) if rents else _to_int(item.get("loyer"))
    rent_max = max(rents) if len(rents) > 1 else None
    surf_min = min(surfs) if surfs else _to_int(item.get("surface"))
    surf_max = max(surfs) if len(surfs) > 1 else None

    included = item.get("services_included") or []
    extra = [f"{s} (supplément)" for s in (item.get("services_extra") or [])]
    raw_amenities = included + extra
    amenities = [_normalize_amenity(a) for a in raw_amenities]
    seen_set: set[str] = set()
    amenities = [a for a in amenities if not (a in seen_set or seen_set.add(a))]  # type: ignore

    if any(r.get("furnished") for r in norm_rooms) and "Meublé" not in amenities:
        amenities.append("Meublé")

    price_entry = {
        "source": "studyrama",
        "sourceLabel": "Studyrama",
        "url": url,
        "rent": rent_min,
        "rentMax": rent_max,
        "surface": surf_min,
        "surfaceMax": surf_max,
        "rooms": norm_rooms,
    }

    return {
        "id": f"studyrama-{item['id']}",
        "name": _clean(item.get("titre")) or "Unknown",
        "provider": provider,
        "category": category,
        "lat": lat,
        "lng": lng,
        "type": _clean(item.get("type")),
        "distance": item.get("distance") or _dist_str(lat, lng),
        "imageUrl": image_url,
        "images": all_images,
        "description": _clean(item.get("description")),
        "amenities": amenities,
        "phone": None,
        "address": _clean(item.get("address")),
        "_source_key": "studyrama",
        "_price_entry": price_entry,
    }


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

    price_entry = {
        "source": "nexity",
        "sourceLabel": "Nexity Studéa",
        "url": item.get("search_url"),
        "rent": _to_int(rent_min),
        "rentMax": _to_int(rent_max),
        "surface": _to_int(surf_min),
        "surfaceMax": _to_int(surf_max),
        "rooms": norm_rooms,
    }

    return {
        "id": f"nexity-studea-{item['reference']}",
        "name": item["name"].title(),
        "provider": "Nexity Studéa",
        "category": "private",
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "type": "Résidence étudiante",
        "distance": _dist_str(lat, lng),
        "imageUrl": images[0] if images else None,
        "images": images,
        "description": _clean(item.get("description")),
        "amenities": amenities,
        "phone": _clean(item.get("phone")),
        "address": _clean(item.get("address")),
        "_source_key": "nexity",
        "_price_entry": price_entry,
    }


def _norm_action_logement(item: dict) -> dict | None:
    name = item.get("residency_name")
    lat = item.get("lat")
    lng = item.get("lng")
    if not name or not lat or not lng:
        return None

    rent = _to_int(item.get("rent_total_cc"))
    surface = _to_int(item.get("area_m2"))

    pictures = item.get("pictures") or []
    images: list[str] = []
    for p in pictures:
        urls = p.get("urls") or {}
        url = urls.get("large") or urls.get("medium") or p.get("url")
        if url:
            images.append(url)

    room_label = (
        item.get("lodging_typology_commercial_label")
        or item.get("lodging_typology_label")
        or item.get("lodging_category_label")
    )

    price_entry = {
        "source": "action_logement",
        "sourceLabel": "Action Logement",
        "url": None,
        "rent": rent,
        "rentMax": None,
        "surface": surface,
        "surfaceMax": None,
        "rooms": [{
            "type": room_label,
            "rent": rent,
            "surface": surface,
            "furnished": None,
            "available": None,
            "floor": None,
            "deposit": None,
            "applicationFee": item.get("agency_fees_amount"),
            "energyClass": None,
            "ghgClass": None,
        }] if (rent or surface) else [],
    }

    return {
        "id": f"action-logement-{item.get('id') or item.get('guid', '')}",
        "name": name,
        "provider": "Action Logement",
        "category": "private",
        "lat": lat,
        "lng": lng,
        "type": item.get("residency_type_label") or "Résidence étudiante",
        "distance": _dist_str(lat, lng),
        "imageUrl": images[0] if images else None,
        "images": images,
        "description": _clean(item.get("description")),
        "amenities": [],
        "phone": None,
        "address": item.get("municipality_name"),
        "_source_key": "action_logement",
        "_price_entry": price_entry,
    }


# ── Dedup + merge ─────────────────────────────────────────────────────────────

def _source_key(rec: dict) -> str:
    return rec.get("_source_key", rec.get("id", "").rsplit("-", 1)[0])


def _merge_into(base: dict, extra: dict) -> None:
    """Merge `extra` into `base` in-place. Prices and amenities are accumulated."""
    for key, bval in extra.items():
        if key.startswith("_") or key == "id":
            continue
        aval = base.get(key)
        if aval is None and bval is not None:
            base[key] = bval
        elif key == "amenities" and isinstance(aval, list) and isinstance(bval, list):
            base[key] = _merge_amenities(aval, bval)
        elif key == "images" and isinstance(aval, list) and isinstance(bval, list):
            base[key] = _merge_images(aval, bval)
        elif key == "description" and bval and (not aval or len(str(bval)) > len(str(aval))):
            base[key] = bval

    if not base.get("imageUrl") and base.get("images"):
        base["imageUrl"] = base["images"][0]


def _deduplicate_and_merge(candidates: list[dict]) -> list[dict]:
    """
    Cluster candidates into merged records.

    Same source:  within 50 m AND same normalized name -> merge
    Cross source: same normalized name -> merge (coords unreliable across sources)
    """
    groups: list[dict] = []       # merged records
    group_names: list[str] = []   # normalized names per group
    group_prices: list[list] = [] # accumulated price entries per group

    for cand in candidates:
        lat, lng = cand["lat"], cand["lng"]
        name = _norm_name(cand.get("name", ""))
        src = _source_key(cand)

        match_idx = next(
            (
                i for i, g in enumerate(groups)
                if name and group_names[i] == name and (
                    _source_key(g) == src and _km(lat, lng, g["lat"], g["lng"]) < DEDUP_KM
                    or _source_key(g) != src
                )
            ),
            None,
        )

        price_entry = cand.pop("_price_entry", None)
        cand.pop("_source_key", None)

        if match_idx is None:
            groups.append(dict(cand))
            group_names.append(name)
            group_prices.append([price_entry] if price_entry else [])
        else:
            _merge_into(groups[match_idx], cand)
            if price_entry:
                existing_sources = {p["source"] for p in group_prices[match_idx]}
                if price_entry["source"] not in existing_sources:
                    group_prices[match_idx].append(price_entry)

    results: list[dict] = []
    for g, prices in zip(groups, group_prices):
        g["prices"] = prices
        g["sources"] = [p["source"] for p in prices]

        # Aggregate rent/surface across all price sources
        all_rents = [p["rent"] for p in prices if p.get("rent")]
        all_rents_max = [p["rentMax"] for p in prices if p.get("rentMax")]
        all_surfs = [p["surface"] for p in prices if p.get("surface")]
        all_surfs_max = [p["surfaceMax"] for p in prices if p.get("surfaceMax")]

        g["rent"] = min(all_rents) if all_rents else None
        g["rentMax"] = max(all_rents_max + all_rents) if (all_rents_max or all_rents) else None
        g["surface"] = min(all_surfs) if all_surfs else None
        g["surfaceMax"] = max(all_surfs_max + all_surfs) if (all_surfs_max or all_surfs) else None

        g["lastUpdated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        results.append(g)

    return results


# ── Attach Google reviews ─────────────────────────────────────────────────────

def _attach_reviews(records: list[dict], reviews_data: dict) -> None:
    """Match google_reviews entries to merged records by id or normalized name."""
    name_index: dict[str, dict] = {_norm_name(r["name"]): r for r in records}

    for rid, rev in reviews_data.items():
        if not rev or not rev.get("google_rating"):
            continue
        target = None
        if rid in {r["id"] for r in records}:
            target = next((r for r in records if r["id"] == rid), None)
        if target is None:
            # Fallback: match by normalized name embedded in the ID
            norm = _norm_name(rid.replace("studyrama-", "").replace("nexity-studea-", "").replace("-", " "))
            target = name_index.get(norm)

        if target:
            target["googleRating"] = rev["google_rating"]
            target["googleRatingCount"] = rev.get("google_review_count")
            target["googleReviews"] = rev.get("reviews") or []
            target["googleMapsUrl"] = rev.get("google_maps_url")


# ── Entry point ───────────────────────────────────────────────────────────────

def run() -> list[dict]:
    all_candidates: list[dict] = []

    def _load(path: Path, label: str, norm_fn):
        if not path.exists():
            print(f"[aggregator] WARN: {path.name} not found — skipping {label}")
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "items" in raw:
            raw = raw["items"]
        normed = [norm_fn(r) for r in raw]
        valid = [r for r in normed if r]
        print(f"[aggregator] {label}: {len(raw)} raw -> {len(valid)} valid")
        all_candidates.extend(valid)

    _load(ML_DIR / "studyrama" / "debug" / "studyrama.json", "studyrama", _norm_studyrama)
    _load(ML_DIR / "nexity_studea" / "debug" / "nexity_studea.json", "nexity", _norm_nexity)
    _load(ML_DIR / "action_logement" / "debug" / "action_logement.json", "action_logement", _norm_action_logement)

    print(f"[aggregator] Total candidates: {len(all_candidates)}")
    merged = _deduplicate_and_merge(all_candidates)
    print(f"[aggregator] After dedup+merge: {len(merged)}")

    reviews_path = ML_DIR / "google_reviews" / "debug" / "google_reviews.json"
    if reviews_path.exists():
        reviews_data = json.loads(reviews_path.read_text(encoding="utf-8"))
        _attach_reviews(merged, reviews_data)
        rated = sum(1 for r in merged if r.get("googleRating"))
        print(f"[aggregator] Google reviews attached: {rated} / {len(merged)} residences")
    else:
        print(f"[aggregator] WARN: {reviews_path.name} not found — no reviews attached")

    sources_count: dict[str, int] = {}
    for r in merged:
        for s in r.get("sources", []):
            sources_count[s] = sources_count.get(s, 0) + 1
    print(f"[aggregator] Sources: {sources_count}")
    multi = sum(1 for r in merged if len(r.get("sources", [])) > 1)
    print(f"[aggregator] Multi-source records: {multi}")

    APP_DATA.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[aggregator] Saved {len(merged)} residences -> {OUTPUT}")

    pub = APP_PUBLIC_DATA / "housing.json"
    APP_PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    pub.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[aggregator] Also saved -> {pub}")

    return merged


if __name__ == "__main__":
    run()
