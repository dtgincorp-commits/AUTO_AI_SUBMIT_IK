"""
Quick feasibility test for AutoTrader scraping via ScraperAPI.
Run: .venv/bin/python test_autotrader.py
"""
import json
import re
import requests
from bs4 import BeautifulSoup

SCRAPERAPI_KEY = "f18e594351546ddcd9836175ab226ac9"

# ── Same search your broker friend used ─────────────────────────────────────
MAKE      = "honda"
MODEL     = "cr-v"
ZIP       = "92782"       # Irvine, CA
RADIUS    = 50
MIN_PRICE = 20000
MAX_PRICE = 50000
CONDITION = "used-cars"   # or "new-cars"

url = (
    f"https://www.autotrader.com/cars-for-sale/{CONDITION}/{MAKE}/{MODEL}/"
    f"irvine_ca-{ZIP}"
    f"?zip={ZIP}&searchRadius={RADIUS}"
    f"&minPrice={MIN_PRICE}&maxPrice={MAX_PRICE}"
    f"&sortBy=relevance"
)
print(f"Fetching: {url}\n")

# Try without JS rendering first — AutoTrader partially server-renders
resp = requests.get(
    "https://api.scraperapi.com/",
    params={"api_key": SCRAPERAPI_KEY, "url": url, "render": "false", "ultra_premium": "true"},
    timeout=90,
)

print(f"HTTP status  : {resp.status_code}")
print(f"Response size: {len(resp.text):,} bytes")

if len(resp.text) < 2000:
    print("\n❌ Response too small — likely blocked or error page")
    print(resp.text[:500])
    exit()

if "autotrader" not in resp.text.lower():
    print("\n❌ AutoTrader content not found — redirected or blocked")
    exit()

print("✅ Got AutoTrader HTML\n")

soup = BeautifulSoup(resp.text, "lxml")

# ── Method 1: JSON-LD structured data ───────────────────────────────────────
json_ld_count = 0
for script in soup.find_all("script", type="application/ld+json"):
    try:
        data = json.loads(script.string or "")
        if isinstance(data, dict) and data.get("@type") == "ItemList":
            items = data.get("itemListElement", [])
            json_ld_count = len(items)
            print(f"✅ JSON-LD ItemList found: {json_ld_count} listings")
            if items:
                sample = items[0]
                print(f"   Sample: {json.dumps(sample, indent=2)[:400]}")
            break
    except Exception:
        continue

if json_ld_count == 0:
    print("⚠️  No JSON-LD ItemList found")

# ── Method 2: data-cmp listing cards ────────────────────────────────────────
cards = soup.select('[data-cmp="itemCard"]')
print(f"\n{'✅' if cards else '⚠️ '} data-cmp=itemCard cards: {len(cards)}")

# ── Method 3: any link with /cars-for-sale/ in href (listing links) ─────────
listing_links = soup.select('a[href*="/cars-for-sale/"]')
unique_listings = {a["href"].split("?")[0] for a in listing_links if "/cars-for-sale/" in a.get("href","")}
print(f"{'✅' if unique_listings else '⚠️ '} Unique listing URLs found: {len(unique_listings)}")

# ── Method 4: window.__PRELOADED_STATE__ embedded JSON ──────────────────────
preloaded = re.search(r"window\.__PRELOADED_STATE__\s*=\s*({.+?});\s*</script>", resp.text, re.DOTALL)
if preloaded:
    try:
        state = json.loads(preloaded.group(1))
        listing_count = len(state.get("listings", {}).get("listings", []))
        print(f"✅ window.__PRELOADED_STATE__ found — {listing_count} listings in state")
    except Exception:
        print("⚠️  __PRELOADED_STATE__ found but couldn't parse")
else:
    print("⚠️  No window.__PRELOADED_STATE__ found")

# ── Summary ──────────────────────────────────────────────────────────────────
best = max(json_ld_count, len(cards), len(unique_listings))
print(f"\n{'='*50}")
print(f"Best listing count found: {best}")
if best >= 15:
    print("✅ FEASIBLE — scraping will work, proceed with integration")
elif best >= 5:
    print("⚠️  PARTIAL — some data accessible, may need tuning")
else:
    print("❌ BLOCKED — ScraperAPI not getting through AutoTrader's bot detection")
print(f"{'='*50}")
