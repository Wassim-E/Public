"""
Scrape Google Maps reviews for all residences in housing.json.

Strategy per residence:
  1. Navigate by coordinates (q=lat,lng) — more precise than name search
  2. Dismiss EU cookie consent if shown
  3. Click the compact rating span to open the full review panel
  4. Click "Plus d'avis" to load all reviews, then scroll until no new ones appear
  5. Save incrementally to debug/google_reviews.json

Usage:
  python google_reviews.py              # scrape all (headless)
  python google_reviews.py --limit 3    # test on first 3 (visible browser)
  python google_reviews.py --resume     # skip already-scraped IDs

Requirements:
  pip install playwright tqdm
  playwright install chromium
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import time

try:
    from playwright.sync_api import Page, sync_playwright, TimeoutError as PwTimeout
except ImportError:
    raise SystemExit(
        "Playwright not installed.\n"
        "Run:  pip install playwright && playwright install chromium"
    )

from tqdm import tqdm

# housing.json lives 3 levels up: ml/google_reviews/ -> ml/ -> StudAI/ -> App/src/data/
HOUSING_JSON = (
    Path(__file__).resolve().parents[2] / "App" / "src" / "data" / "housing.json"
)
OUT = Path(__file__).parent / "debug" / "google_reviews.json"


# -- Text helpers --------------------------------------------------------------

def _clean(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def _city_from_url_slug(url: str) -> str:
    m = re.search(r"/residence-etudiante/([^/]+)/", url or "")
    if not m:
        return ""
    slug = m.group(1).replace("-", " ").title()
    slug = re.sub(r"\b(Sur|De|Les|Du|En|La|Le)\b", lambda x: x.group().lower(), slug)
    return slug


def _search_query(r: dict) -> str:
    name = r["name"]
    addr = r.get("address") or ""
    parts = [p.strip() for p in addr.split(",") if p.strip()]
    city = next((p for p in reversed(parts) if not p[0].isdigit()), "")
    if not city:
        city = _city_from_url_slug(r.get("url") or "")
    return f"{name} {city}".strip() if city else name


# -- Page actions -------------------------------------------------------------

_consent_dismissed = False


def _dismiss_consent(page: Page) -> None:
    global _consent_dismissed
    if _consent_dismissed:
        return
    for sel in [
        "button[aria-label='Tout accepter']",
        "button[aria-label='Accept all']",
        "button[aria-label='Accepter tout']",
        "form:last-of-type button:last-of-type",
    ]:
        try:
            btn = page.wait_for_selector(sel, timeout=4_000)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(1.5)
                _consent_dismissed = True
                return
        except PwTimeout:
            pass


def _click_best_result(page: Page, residence: dict) -> bool:
    name_words = _clean(residence["name"]).split()
    best_el = None
    best_score = 0
    for card in page.query_selector_all("div[aria-label], a[aria-label]"):
        lbl = _clean(card.get_attribute("aria-label") or "")
        score = sum(1 for w in name_words if w in lbl)
        if score > best_score:
            best_score = score
            best_el = card
    if best_el and best_score >= 1:
        try:
            best_el.click()
            time.sleep(2.5)
            return True
        except Exception:
            pass
    for sel in ["a.hfpxzc", "a[href*='/maps/place/']"]:
        el = page.query_selector(sel)
        if el:
            el.click()
            time.sleep(2.5)
            return True
    return False


def _extract_rating(page: Page) -> tuple[float | None, int | None]:
    rating = None
    count = None
    for el in page.query_selector_all("*[aria-label]"):
        lbl = el.get_attribute("aria-label") or ""
        if rating is None:
            m = re.search(r"([\d][,\.][\d]|[1-5])\s*\xa0*[eE\xe9]toile", lbl)
            if m:
                try:
                    v = float(m.group(1).replace(",", "."))
                    if 1.0 <= v <= 5.0:
                        rating = v
                except ValueError:
                    pass
        if count is None:
            m = re.search(r"([\d][\d\s\xa0]*)\s*\xa0*avis", lbl)
            if m:
                try:
                    count = int(re.sub(r"\D", "", m.group(1)))
                except ValueError:
                    pass
        if rating and count:
            return rating, count
    if rating:
        return rating, count
    for span in page.query_selector_all("span[aria-hidden='true']"):
        txt = (span.text_content() or "").strip().replace(",", ".")
        try:
            v = float(txt)
            if 1.0 <= v <= 5.0 and len(txt) <= 4:
                return v, count
        except ValueError:
            pass
    return None, None


def _wait_for_place_or_settle(page: Page, extra: float = 2.5) -> None:
    deadline = time.time() + 6
    while time.time() < deadline and "/maps/place/" not in page.url:
        time.sleep(0.3)
    time.sleep(extra)


def _open_review_panel(page: Page) -> bool:
    for el in page.query_selector_all("span[aria-label], button[aria-label]"):
        lbl = el.get_attribute("aria-label") or ""
        if re.search(r"^[\d][,\.][\d][\s\xa0]{1,3}.{0,4}[eE\xe9]toile", lbl):
            try:
                el.click()
                _wait_for_place_or_settle(page)
                return True
            except Exception:
                pass
    for el in page.query_selector_all("*[aria-label]"):
        lbl = el.get_attribute("aria-label") or ""
        if re.search(r"[\d][,\.][\d].{0,5}[eE\xe9]toile.{0,15}\d+.{0,5}avis", lbl):
            tag = el.evaluate("el => el.tagName.toLowerCase()")
            if tag in ("span", "button", "a"):
                try:
                    el.click()
                    _wait_for_place_or_settle(page)
                    return True
                except Exception:
                    pass
    return False


def _load_more_reviews(page: Page) -> None:
    for btn in page.query_selector_all("button"):
        txt = (btn.text_content() or "").strip()
        if re.search(r"plus\s+d.avis|voir\s+(tous\s+les\s+)?avis|more\s+reviews", txt, re.I):
            try:
                btn.click()
                time.sleep(2.5)
            except Exception:
                pass
            return


def _scroll_panel(page: Page) -> None:
    page.evaluate("""
        Array.from(document.querySelectorAll('div')).forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.left < 100 && r.width > 200 && r.width < 650 && r.height > 200
                    && el.scrollHeight > el.clientHeight + 100) {
                el.scrollTop += 2000;
            }
        });
    """)


def _scrape_reviews(page: Page) -> list[dict]:
    try:
        page.wait_for_selector("div[data-review-id]", timeout=20_000)
    except PwTimeout:
        return []

    _load_more_reviews(page)
    time.sleep(1.5)

    # Scroll until no new reviews load — no artificial cap
    prev = 0
    stale_rounds = 0
    for _ in range(30):
        els = page.query_selector_all("div[data-review-id]")
        if len(els) == prev:
            stale_rounds += 1
            if stale_rounds >= 3:
                break
        else:
            stale_rounds = 0
        prev = len(els)
        _scroll_panel(page)
        if els:
            els[-1].scroll_into_view_if_needed()
        time.sleep(1.5)

    seen: set[tuple] = set()
    reviews: list[dict] = []

    for el in page.query_selector_all("div[data-review-id]"):
        for xbtn in el.query_selector_all("button, [role='button']"):
            t = (xbtn.text_content() or "").strip().lower()
            if t in ("plus", "more", "voir plus", "lire plus", "suite"):
                try:
                    xbtn.click()
                    time.sleep(0.3)
                except Exception:
                    pass
                break

        stars = None
        for star_el in el.query_selector_all("[aria-label]"):
            lbl = star_el.get_attribute("aria-label") or ""
            m = re.match(r"(\d)\s+[eE\xe9]toile", lbl)
            if m:
                stars = int(m.group(1))
                break

        author_el = (
            el.query_selector(".d4r55")
            or el.query_selector(".WNxzHc")
            or el.query_selector("[class*='reviewer']")
        )
        author = (author_el.text_content() if author_el else "").strip()

        date_el = el.query_selector(".rsqaWe") or el.query_selector(".dehysf")
        date_txt = (date_el.text_content() if date_el else "").strip()

        text_el = el.query_selector(".wiI7pd")
        text = (text_el.text_content() if text_el else "").strip()

        key = (author, text)
        if key in seen or (not text and not stars):
            continue
        seen.add(key)

        reviews.append({
            "author": author,
            "rating": stars,
            "date": date_txt,
            "text": text,
        })

    return reviews


# -- Core per-residence logic -------------------------------------------------

def _navigate_to_name_search(page: Page, residence: dict) -> bool:
    lat, lng = residence["lat"], residence["lng"]
    query = _search_query(residence)
    search_url = (
        f"https://www.google.com/maps/search/"
        f"{quote(query, safe=' ').replace(' ', '+')}/"
        f"@{lat},{lng},17z"
    )
    try:
        page.goto(search_url, timeout=20_000, wait_until="domcontentloaded")
    except PwTimeout:
        return False
    time.sleep(2.5)
    return True


def scrape_one(page: Page, residence: dict) -> dict | None:
    lat, lng = residence["lat"], residence["lng"]
    coord_url = f"https://www.google.com/maps?q={lat},{lng}"
    try:
        page.goto(coord_url, timeout=20_000, wait_until="domcontentloaded")
    except PwTimeout:
        return None

    _dismiss_consent(page)
    time.sleep(2.5)

    on_place_page = "/maps/place/" in page.url
    if not on_place_page:
        _navigate_to_name_search(page, residence)

    rating, count = _extract_rating(page)
    if rating is None:
        return None

    panel_opened = _open_review_panel(page)
    maps_url = page.url
    reviews = _scrape_reviews(page)

    return {
        "google_rating": rating,
        "google_review_count": count,
        "google_maps_url": maps_url,
        "reviews": reviews,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


# -- Entry point --------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Google Maps reviews for StudAI residences")
    parser.add_argument("--limit",    type=int, default=0,  help="Test: process only first N residences")
    parser.add_argument("--resume",   action="store_true",  help="Skip IDs already in output file")
    parser.add_argument("--headless", action="store_true",  help="Force headless (default when --limit is not set)")
    args = parser.parse_args()

    residences: list[dict] = json.loads(HOUSING_JSON.read_text(encoding="utf-8"))
    if args.limit:
        residences = residences[: args.limit]

    existing: dict = {}
    if args.resume and OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"[resume] {len(existing)} already scraped, skipping them")

    results = dict(existing)
    headless = args.headless or (args.limit == 0)
    global _consent_dismissed
    _consent_dismissed = False

    to_scrape = [r for r in residences if not (args.resume and r["id"] in results)]
    print(f"[google-reviews] {len(to_scrape)} residences to scrape (headless={headless})")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        ctx = browser.new_context(
            locale="fr-FR",
            timezone_id="Europe/Paris",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        for r in tqdm(to_scrape, desc="google-reviews", unit="residence"):
            rid = r["id"]
            result = scrape_one(page, r)
            if result:
                results[rid] = result

            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

            time.sleep(3.5)

        browser.close()

    found = sum(1 for v in results.values() if v.get("google_rating"))
    print(f"\n[done] {found} / {len(residences)} residences found on Google Maps")
    print(f"Output -> {OUT}")


if __name__ == "__main__":
    main()
