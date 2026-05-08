"""
Fetch all student housing listings from Studyrama.

Stage 1 (fast)  — list API: 254 residences with coordinates, rent, surface.
Stage 2 (slow)  — detail HTML page per residence: services, description,
                  full image gallery, per-room table, precise address from JSON-LD.

Total run time: ~3–4 min (254 detail pages × 0.5 s delay).
Output: raw/studyrama.json
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

LIST_URL = (
    "https://logement.studyrama.com/api/annuaire"
    "?center=1&distance=30&surfacemin=9&loyermax=2000"
    "&typeslogement=&meuble=&type=&tri=prix"
    "&lat=48.8588897&lng=2.3200410217200766"
)
BASE_URL = "https://logement.studyrama.com"

LIST_HEADERS = {
    "accept": "*/*",
    "accept-language": "fr-FR,fr;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
}
DETAIL_HEADERS = {
    "accept": "text/html",
    "accept-language": "fr-FR,fr;q=0.9",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    ),
}

DETAIL_DELAY = 0.5   # seconds between detail page requests
RAW_PATH = Path(__file__).parent / "raw" / "studyrama.json"


# ── Detail page parsers ───────────────────────────────────────────────────────

def _parse_services(soup: BeautifulSoup) -> dict[str, list[str]]:
    """Return {"included": [...], "extra": [...]}"""
    def _names(container_class: str) -> list[str]:
        section = soup.find(class_=container_class)
        if not section:
            return []
        names = []
        for el in section.select(".views-field-name .field-content, .field-content"):
            text = el.get_text(strip=True)
            if text and text not in names:
                names.append(text)
        return names

    return {
        "included": _names("service_inclus_residence"),
        "extra": _names("service_supplement_residence"),
    }


def _parse_description(soup: BeautifulSoup) -> str | None:
    section = soup.find(class_="description_residence")
    if not section:
        return None
    parts = [p.get_text(" ", strip=True) for p in section.find_all("p")]
    text = " ".join(p for p in parts if p)
    return text if len(text) > 20 else None


def _parse_images(soup: BeautifulSoup) -> list[str]:
    """All photos from the image carousel."""
    urls: list[str] = []
    for el in soup.select(".cycle-slideshow img[src], .imagefield_slideshow-wrapper img[src]"):
        src = el.get("src", "").strip()
        if src and not src.endswith(".svg") and src not in urls:
            # Studyrama sometimes double-prepends the base URL — fix it
            src = re.sub(r"^https?://logement\.studyrama\.com(https?://)", r"\1", src)
            urls.append(src)
    return urls


def _parse_rooms(soup: BeautifulSoup) -> list[dict]:
    """Parse the per-room table: Type | Surface | Meublé | Loyer."""
    table = soup.select_one("table.table tbody")
    if not table:
        return []

    # Map column names from <th> in the <thead>
    thead = soup.select_one("table.table thead tr")
    if not thead:
        return []
    headers = [th.get_text(strip=True).lower() for th in thead.find_all("th")]

    def _col(*keywords: str) -> int | None:
        for kw in keywords:
            for i, h in enumerate(headers):
                if kw in h:
                    return i
        return None

    c_type = _col("type", "catég")
    c_surface = _col("surface")
    c_furnished = _col("meublé", "meuble")
    c_rent = _col("loyer", "prix")

    rooms = []
    for row in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if not cells:
            continue

        def _g(idx: int | None) -> str:
            return cells[idx].strip() if idx is not None and idx < len(cells) else ""

        rent_text = _g(c_rent)
        rent = None
        m = re.search(r"(\d[\d\s]*)", rent_text.replace("\xa0", ""))
        if m:
            try:
                rent = int(re.sub(r"\s", "", m.group(1)))
            except ValueError:
                pass

        surface_text = _g(c_surface)
        surface = None
        ms = re.search(r"(\d+)", surface_text)
        if ms:
            try:
                surface = int(ms.group(1))
            except ValueError:
                pass

        room_type = _g(c_type) or None
        furnished_text = _g(c_furnished).lower()
        furnished = True if "oui" in furnished_text else (False if "non" in furnished_text else None)

        rooms.append({
            "type": room_type,
            "surface_m2": surface,
            "furnished": furnished,
            "rent": rent,
        })
    return rooms


def _parse_jsonld(soup: BeautifulSoup) -> dict:
    """Extract structured data from JSON-LD script tag."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if not isinstance(data, dict):
                continue
            result: dict = {}

            # Address
            addr = data.get("address") or {}
            if addr:
                parts = [
                    addr.get("streetAddress", ""),
                    addr.get("postalCode", ""),
                    addr.get("addressLocality", ""),
                ]
                full = ", ".join(p for p in parts if p)
                if full:
                    result["address"] = full

            # Precise coordinates (may differ slightly from list API)
            geo = data.get("geo") or {}
            if geo.get("latitude") and geo.get("longitude"):
                result["geo_lat"] = float(geo["latitude"])
                result["geo_lng"] = float(geo["longitude"])

            # Rooms from containsPlace
            rooms = []
            for place in data.get("containsPlace") or []:
                floor_size = (place.get("floorSize") or {}).get("value")
                price = ((place.get("offers") or {}).get("priceSpecification") or {}).get("price")
                if floor_size or price:
                    rooms.append({
                        "name": place.get("name"),
                        "surface_m2": int(float(floor_size)) if floor_size else None,
                        "rent": int(float(price)) if price else None,
                    })
            if rooms:
                result["jsonld_rooms"] = rooms

            if result:
                return result
        except Exception:
            pass
    return {}


def _scrape_detail(session: requests.Session, url: str) -> dict:
    try:
        resp = session.get(url, headers=DETAIL_HEADERS, timeout=20)
        if resp.status_code != 200:
            return {"detail_http_status": resp.status_code}
        soup = BeautifulSoup(resp.text, "html.parser")
        services = _parse_services(soup)
        jsonld = _parse_jsonld(soup)
        return {
            "detail_http_status": 200,
            "services_included": services["included"],
            "services_extra": services["extra"],
            "description": _parse_description(soup),
            "detail_images": _parse_images(soup),
            "detail_rooms": _parse_rooms(soup),
            **jsonld,
        }
    except Exception as exc:
        return {"detail_http_status": None, "detail_error": str(exc)}


# ── Main entry ────────────────────────────────────────────────────────────────

def fetch() -> list[dict]:
    session = requests.Session()

    print("[studyrama] Fetching list API...")
    resp = session.get(LIST_URL, headers=LIST_HEADERS, allow_redirects=True, timeout=30)
    resp.raise_for_status()
    items: list[dict] = resp.json()
    print(f"[studyrama] {len(items)} residences from list API")

    scraped_at = datetime.now(timezone.utc).isoformat()
    enriched = []

    for i, item in enumerate(items):
        slug_url = item.get("url")
        full_url = BASE_URL + slug_url if slug_url else None
        print(f"  [{i+1}/{len(items)}] {item.get('titre', '?')}")

        detail: dict = {}
        if full_url:
            time.sleep(DETAIL_DELAY)
            detail = _scrape_detail(session, full_url)

        enriched.append({**item, **detail, "_scraped_at": scraped_at})

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[studyrama] Raw data saved to {RAW_PATH}")
    return enriched


if __name__ == "__main__":
    fetch()
