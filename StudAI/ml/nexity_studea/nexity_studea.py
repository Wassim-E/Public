"""
Scrape Nexity Studéa student residences.

Stage 1 — Search: POST /search-query with a fresh CSRF token -> 50 HTML cards.
Stage 2 — Detail: GET each residence page and parse rooms, services, images, POI coords.
Output: debug/nexity_studea.json

Note: 3 s delay between detail requests is required to avoid CloudFront 403.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag
from tqdm import tqdm

SEARCH_PAGE = "https://www.nexity-studea.com/locations-etudiantes/paris"
SEARCH_ENDPOINT = "https://www.nexity-studea.com/search-query"
RAW_PATH = Path(__file__).parent / "debug" / "nexity_studea.json"

DETAIL_DELAY = 3.0


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        ),
        "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    return s


def _csrf_token(session: requests.Session) -> str:
    resp = session.get(SEARCH_PAGE, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    el = soup.find("input", {"name": "search[_token]"})
    if not el:
        raise RuntimeError("CSRF token not found on Nexity Studéa search page")
    return el["value"]  # type: ignore[index]


def _search_cards(session: requests.Session, token: str) -> list[dict]:
    resp = session.post(
        SEARCH_ENDPOINT,
        data={
            "search[autoCompleteCity]": "Paris, France",
            "search[autoCompleteEstablishment]": "",
            "search[city]": "Paris",
            "search[cityLat]": "48.8575475",
            "search[cityLng]": "2.3513765",
            "search[cityPostalCode]": "",
            "search[establishmentId]": "",
            "search[residencesId]": "",
            "search[residenceId]": "",
            "search[_token]": token,
        },
        headers={
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "referer": SEARCH_PAGE,
        },
        timeout=30,
    )
    resp.raise_for_status()
    html = resp.json()["content"]["residences"]
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    for div in soup.find_all("div", class_="block-residence"):
        link = div.find("a", href=lambda h: h and "/locations-etudiantes/" in h)
        img_url = None
        img_div = div.find("a", style=True)
        if img_div:
            m = re.search(r"url\((.+?)\)", img_div.get("style", ""))
            if m:
                img_url = m.group(1)
        cards.append({
            "reference": div.get("data-reference", ""),
            "name": div.get("data-name", ""),
            "search_price_min": _to_int(div.get("data-price")),
            "search_url": "https://www.nexity-studea.com" + link["href"] if link else None,
            "search_image_url": img_url,
        })
    return cards


# ── Detail page parsers ───────────────────────────────────────────────────────

def _parse_price(text: str) -> int | None:
    m = re.search(r"([\d\s ]+)", text.replace("\xa0", "").replace(" ", ""))
    if m:
        digits = re.sub(r"\s", "", m.group(1))
        try:
            return int(digits)
        except ValueError:
            pass
    return None


def _parse_surface(text: str) -> int | None:
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None


def _to_int(val: str | None) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _table_to_raw(table: Tag) -> dict:
    all_rows = table.find_all("tr")
    if not all_rows:
        return {"headers": [], "rows": []}
    first = all_rows[0]
    th_cells = first.find_all("th")
    if th_cells:
        headers = [c.get_text(" ", strip=True) for c in th_cells]
        data_rows = all_rows[1:]
    else:
        headers = [c.get_text(" ", strip=True) for c in first.find_all("td")]
        data_rows = all_rows[1:]
    rows = []
    for row in data_rows:
        cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
        if any(c.strip() for c in cells):
            rows.append(cells)
    return {"headers": headers, "rows": rows}


def _col(headers: list[str], *keywords: str) -> int | None:
    for kw in keywords:
        for i, h in enumerate(headers):
            if kw in h.lower():
                return i
    return None


def _parse_rooms(soup: BeautifulSoup) -> list[dict]:
    tables = soup.find_all("table")
    rooms: list[dict] = []
    for table in tables:
        raw = _table_to_raw(table)
        header_text = " ".join(raw["headers"]).lower()
        if not any(k in header_text for k in ["loyer", "superficie", "disponib"]):
            continue
        h = raw["headers"]
        c_type = _col(h, "type")
        c_surface = _col(h, "superficie", "surface")
        c_floor = _col(h, "tage")
        c_dispo = _col(h, "dispo")
        c_rent = _col(h, "loyer", "cc/mois")
        c_fee = _col(h, "frais")
        c_deposit = _col(h, "pot de garantie", "garantie")
        c_energy = _col(h, "nergi")
        for cells in raw["rows"]:
            if not cells:
                continue

            def _g(idx: int | None) -> str:
                return cells[idx].strip() if idx is not None and idx < len(cells) else ""

            energy_text = _g(c_energy)
            em = re.findall(r"([A-G])\s*:\s*(\d+)", energy_text)
            rooms.append({
                "type": _g(c_type) or None,
                "rent_cc": _parse_price(_g(c_rent)),
                "surface_m2": _parse_surface(_g(c_surface)),
                "available": ("disponible" in _g(c_dispo).lower()) if _g(c_dispo) else None,
                "floor": _to_int(_g(c_floor)),
                "application_fee": _parse_price(_g(c_fee)),
                "deposit": _parse_price(_g(c_deposit)),
                "energy_class": em[0][0] if len(em) >= 1 else None,
                "energy_value": int(em[0][1]) if len(em) >= 1 else None,
                "ghg_class": em[1][0] if len(em) >= 2 else None,
                "ghg_value": int(em[1][1]) if len(em) >= 2 else None,
            })
    return rooms


def _parse_services(soup: BeautifulSoup) -> list[str]:
    services: list[str] = []
    for section in soup.find_all(class_=re.compile(r"service", re.I)):
        for img in section.find_all("img", alt=True):
            alt = img["alt"].strip()
            if alt and len(alt) > 3 and alt not in services:
                services.append(alt)
        if services:
            return services
    for section in soup.find_all(class_=re.compile(r"service", re.I)):
        text = section.get_text("\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        seen: list[str] = []
        for line in lines:
            if line in seen and line not in services and 3 < len(line) < 80:
                services.append(line)
            seen.append(line)
        if services:
            return services
    return services


def _parse_description(soup: BeautifulSoup) -> str | None:
    for sel in [".cp-article-compact__entry", ".cp-article__entry", "[class*='article'] [class*='entry']"]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            if text and len(text) > 30:
                return text
    return None


def _parse_images(html_text: str) -> list[str]:
    urls = re.findall(r"url\((https://media\.nexity-studea\.com[^)]+)\)", html_text)
    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def _parse_phone(soup: BeautifulSoup) -> str | None:
    el = soup.find("a", href=re.compile(r"^tel:"))
    if el:
        return el["href"].replace("tel:", "").strip()  # type: ignore[index]
    return None


def _parse_poi_centroid(html_text: str) -> tuple[float | None, float | None]:
    m = re.search(r"const\s+poisJson\s*=\s*(\{.+?\});", html_text, re.DOTALL)
    if not m:
        return None, None
    lat_lngs = re.findall(r'"([\d.]+),([\d.-]+)"', m.group(1))
    if not lat_lngs:
        return None, None
    lats = [float(x[0]) for x in lat_lngs]
    lngs = [float(x[1]) for x in lat_lngs]
    return sum(lats) / len(lats), sum(lngs) / len(lngs)


def _parse_address(soup: BeautifulSoup) -> str | None:
    for sel in [
        ".cp-banner__address", ".cp-residence__address",
        "[class*='address']", "[class*='adresse']", "address",
    ]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            if text and len(text) > 5:
                return text
    return None


def _scrape_detail(session: requests.Session, url: str) -> dict:
    try:
        resp = session.get(url, timeout=25)
        status = resp.status_code
        if status != 200:
            return {"detail_http_status": status}
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        return {
            "detail_http_status": status,
            "description": _parse_description(soup),
            "services": _parse_services(soup),
            "rooms": _parse_rooms(soup),
            "images": _parse_images(html),
            "phone": _parse_phone(soup),
            "address": _parse_address(soup),
            "poi_lat": _parse_poi_centroid(html)[0],
            "poi_lng": _parse_poi_centroid(html)[1],
        }
    except Exception as exc:
        return {"detail_http_status": None, "detail_error": str(exc)}


# ── Main entry ────────────────────────────────────────────────────────────────

def fetch() -> list[dict]:
    session = _session()

    print("[nexity-studea] Stage 1: fetching CSRF token and search cards...")
    token = _csrf_token(session)
    cards = _search_cards(session, token)
    print(f"[nexity-studea] {len(cards)} residences found")

    scraped_at = datetime.now(timezone.utc).isoformat()
    results: list[dict] = []

    print("[nexity-studea] Stage 2: scraping detail pages (3 s delay each)...")
    for card in tqdm(cards, desc="nexity details", unit="page"):
        time.sleep(DETAIL_DELAY)
        detail = _scrape_detail(session, card["search_url"]) if card["search_url"] else {}
        results.append({**card, **detail, "_scraped_at": scraped_at})

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[nexity-studea] Saved {len(results)} records -> {RAW_PATH}")
    return results


if __name__ == "__main__":
    fetch()
