"""Quick debug: inspect Google Maps DOM for ARPEJ SCIPION."""
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
import time, json, re
from pathlib import Path

housing = json.loads(Path("../App/src/data/housing.json").read_text(encoding="utf-8"))
r = housing[1]  # ARPEJ SCIPION - has 15 reviews

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    ctx = browser.new_context(
        locale="fr-FR", timezone_id="Europe/Paris",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    )
    page = ctx.new_page()

    url = f"https://www.google.com/maps/search/{r['name'].replace(' ','+')}/@{r['lat']},{r['lng']},15z"
    page.goto(url, timeout=20_000, wait_until="domcontentloaded")
    time.sleep(1)

    # Dismiss consent
    for sel in ["button[aria-label='Tout accepter']", "button[aria-label='Accept all']", "form:last-of-type button:last-of-type"]:
        try:
            btn = page.wait_for_selector(sel, timeout=4_000)
            if btn and btn.is_visible():
                btn.click()
                print(f"Consent dismissed ({sel})")
                time.sleep(2)
                break
        except PwTimeout:
            pass

    # Click first place result
    first = page.query_selector("a[href*='/maps/place/']")
    if first:
        first.click()
        print("Clicked first result")
        time.sleep(3)
    else:
        print("No first result link found")

    print(f"URL: {page.url[:80]}")
    page.screenshot(path="raw/dbg1_place.png")

    # Find rating element
    print("\n--- Elements with 'etoile' in aria-label ---")
    for el in page.query_selector_all("*[aria-label]"):
        lbl = el.get_attribute("aria-label") or ""
        if "toile" in lbl:
            tag = el.evaluate("el => el.tagName")
            clickable = el.evaluate("el => !el.disabled && window.getComputedStyle(el).cursor !== 'default'")
            print(f"  tag={tag}  clickable={clickable}  label={repr(lbl[:60])}")

    # Click the rating element (X,X etoiles N avis)
    print("\n--- Trying to click rating/review button ---")
    for el in page.query_selector_all("*[aria-label]"):
        lbl = el.get_attribute("aria-label") or ""
        if re.search(r"\d[,\.]\d.{0,3}toile.{0,10}\d+.{0,3}avis", lbl, re.I):
            tag = el.evaluate("el => el.tagName")
            print(f"Found: tag={tag} label={repr(lbl[:60])}")
            try:
                el.click()
                print("Clicked!")
                time.sleep(3)
                page.screenshot(path="raw/dbg2_after_rating_click.png")
                break
            except Exception as e:
                print(f"Click failed: {e}")

    # Check all review-related selectors
    print("\n--- Review element counts ---")
    for sel in [
        "div[data-review-id]",
        "[data-review-id]",
        ".jJc9Ad",
        "div[class*='section-review']",
        "[data-local-attribute*='d3fhz']",
        "[jsan*='review']",
        "div[aria-label*='avis']",
        "[data-index]",
        "li[aria-label]",
    ]:
        n = len(page.query_selector_all(sel))
        if n > 0:
            print(f"  {sel}: {n}")

    print("\n--- All aria-labels containing 'avis' ---")
    for el in page.query_selector_all("*[aria-label]"):
        lbl = el.get_attribute("aria-label") or ""
        if "avis" in lbl.lower():
            tag = el.evaluate("el => el.tagName")
            print(f"  [{tag}] {repr(lbl[:80])}")

    page.screenshot(path="raw/dbg3_final.png")
    input("Press Enter to close browser...")
    browser.close()
