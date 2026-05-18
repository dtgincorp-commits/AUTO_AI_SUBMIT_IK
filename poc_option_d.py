"""
POC — Option D: Two-tier dealer link + phone number.

For each VIN:
  PRIMARY  → dealer's own VDP page (site-targeted DDG search)
  FALLBACK → aggregator listing URL (AutoTrader VIN search, always works)
  ALWAYS   → dealer name + phone from auto.dev

Run: .venv/bin/python poc_option_d.py
"""
import sys, os, time, re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote, quote

# Load config so we get AUTODEV_API_KEY from .env
sys.path.insert(0, os.path.dirname(__file__))
from config import AUTODEV_API_KEY

AUTODEV_BASE = "https://auto.dev/api"

SKIP_DOMAINS = {
    "autotrader.com", "cars.com", "cargurus.com", "carmax.com",
    "ebay.com", "craigslist.org", "truecar.com", "carfax.com",
    "kbb.com", "edmunds.com", "facebook.com", "instagram.com",
    "youtube.com", "reddit.com", "wikipedia.org", "yelp.com",
    "classic.com", "vehiclehistory.com", "vincheck.info",
    "autocheck.com", "ipacket.us", "dealertrend.com",
    "carvana.com", "vroom.com", "shift.com", "duckduckgo.com",
    "efaq.com", "google.com", "bing.com",
}

DDG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ── Step 1: auto.dev live lookup ─────────────────────────────────────────────

def get_dealer_info(vin: str) -> dict:
    """Call auto.dev VIN endpoint → dealer name, phone, website domain."""
    if not AUTODEV_API_KEY:
        return {"error": "No AUTODEV_API_KEY"}
    try:
        resp = requests.get(
            f"{AUTODEV_BASE}/listings/{vin}",
            headers={"Authorization": f"Bearer {AUTODEV_API_KEY}"},
            timeout=15,
        )
        if resp.status_code == 404:
            return {"error": "not_found"}
        resp.raise_for_status()
        d = resp.json()

        dealer = d.get("dealerName") or ""
        city   = d.get("city") or ""
        state  = d.get("state") or ""
        phone_raw = d.get("phone") or ""
        phone_tel = d.get("phoneTel") or d.get("phoneTelRegional") or ""
        phone = phone_raw or (
            f"({str(phone_tel)[:3]}) {str(phone_tel)[3:6]}-{str(phone_tel)[6:]}"
            if len(str(phone_tel)) == 10 else str(phone_tel)
        )

        # Try all field names auto.dev uses for dealer website
        raw_site = (
            d.get("dealerUrl") or d.get("dealerWebsite") or d.get("website") or
            d.get("websiteUrl") or (d.get("dealer") or {}).get("url") or
            (d.get("dealer") or {}).get("website") or ""
        )
        # Only keep if it's a real domain (not a Google/Bing search fallback)
        dealer_domain = ""
        if raw_site and "google.com" not in raw_site and "bing.com" not in raw_site:
            parsed = urlparse(raw_site if raw_site.startswith("http") else f"https://{raw_site}")
            dealer_domain = parsed.netloc.replace("www.", "").strip("/")

        return {
            "dealer_name": dealer,
            "city": city,
            "state": state,
            "phone": phone,
            "dealer_domain": dealer_domain,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Step 2: site-targeted DuckDuckGo search ──────────────────────────────────

def _decode_ddg(href: str) -> str:
    if "duckduckgo.com/l/" in href:
        qs = parse_qs(urlparse(href).query)
        return unquote(qs.get("uddg", [""])[0])
    return href


def find_dealer_vdp(vin: str, dealer_domain: str) -> str:
    """Search DuckDuckGo with site: operator for exact VIN on dealer's domain."""
    query = f'site:{dealer_domain} "{vin}"'
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=DDG_HEADERS,
            timeout=12,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a.result__a"):
            href = _decode_ddg(a.get("href", ""))
            if not href.startswith("http"):
                continue
            domain = urlparse(href).netloc.replace("www.", "")
            if any(skip in domain for skip in SKIP_DOMAINS):
                continue
            # Confirm it's actually on the dealer's domain
            if dealer_domain.split(".")[0] in domain:
                return href
    except Exception:
        pass
    return ""


def find_any_dealer_page(vin: str) -> str:
    """Fallback: general VIN search on DDG, skip all aggregators."""
    query = f'"{vin}"'
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=DDG_HEADERS,
            timeout=12,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a.result__a"):
            href = _decode_ddg(a.get("href", ""))
            if not href.startswith("http"):
                continue
            domain = urlparse(href).netloc.replace("www.", "")
            if not any(skip in domain for skip in SKIP_DOMAINS):
                return href
    except Exception:
        pass
    return ""


# ── Step 3: aggregator fallback (always works) ───────────────────────────────

def aggregator_url(vin: str) -> str:
    return f"https://www.autotrader.com/cars-for-sale/all-cars?vin={vin}&searchRadius=500"


# ── Option D display ─────────────────────────────────────────────────────────

def option_d(vin: str, price: str, info: str, delay: float = 4.0):
    print(f"\n  VIN : {vin}  |  {price}  |  {info}")

    # Step 1 — dealer info from auto.dev
    info_d = get_dealer_info(vin)
    if "error" in info_d:
        err = info_d["error"]
        if err == "not_found":
            print(f"  auto.dev: listing not found (car may be sold)")
        else:
            print(f"  auto.dev error: {err}")
        # Still show aggregator fallback
        print(f"  [FALLBACK] Aggregator : {aggregator_url(vin)}")
        return

    dealer  = info_d["dealer_name"]
    phone   = info_d["phone"]
    domain  = info_d["dealer_domain"]
    city    = info_d["city"]
    state   = info_d["state"]

    print(f"  Dealer   : {dealer}  |  {city}, {state}")
    print(f"  Phone    : {phone or 'N/A'}")
    print(f"  Domain   : {domain or 'not returned by auto.dev'}")

    time.sleep(delay)  # polite pause before DDG search

    dealer_vdp = ""
    if domain:
        # Step 2a — site-targeted search on dealer's own domain
        dealer_vdp = find_dealer_vdp(vin, domain)
        time.sleep(delay)

    if not dealer_vdp:
        # Step 2b — general VIN search (skip aggregators)
        dealer_vdp = find_any_dealer_page(vin)
        time.sleep(delay)

    if dealer_vdp:
        print(f"  [PRIMARY]  Dealer VDP : {dealer_vdp}")
    else:
        print(f"  [FALLBACK] Aggregator : {aggregator_url(vin)}")
        if domain:
            print(f"             (dealer site: https://{domain} — VDP not indexed)")


# ── Test VINs ────────────────────────────────────────────────────────────────
# Smaller subset per search to avoid DDG rate limits while demonstrating all 3 tiers.

searches = {
    "2017 GMC Sierra 2500 Denali HD": [
        ("1GT12UEY1HF151328", "$47,499", "52,573 mi"),
        ("1GT12UEY5HF151297", "$48,991", "82,132 mi"),
    ],
    "Ferrari SF90 near 92782": [
        ("ZFF95NLA8N0277529", "$489,900", "Ferrari Fort Lauderdale"),
        ("ZFF95NLA0P0294022", "$447,900", "Scottsdale Ferrari"),
        ("ZFF95NLA7P0295135", "$449,000", "Ferrari Beverly Hills"),
    ],
    "Honda CR-V near 92782": [
        ("2HKRS4H78RH426819", "$31,988", "2024 / 16,127 mi"),
        ("2HKRW2H97JH687891", "$21,998", "2018 / 63,780 mi"),
        ("5J6RS3H46PL003272", "$28,998", "2023 / 25,107 mi"),
    ],
}

for search_label, vins in searches.items():
    print(f"\n{'='*70}")
    print(f"SEARCH: {search_label}")
    print(f"{'='*70}")
    for vin, price, info in vins:
        option_d(vin, price, info, delay=4.0)

print(f"\n{'='*70}")
print("LEGEND:")
print("  [PRIMARY]  = dealer's own VDP page (exact car on dealer website)")
print("  [FALLBACK] = aggregator listing (AutoTrader VIN search, always works)")
print("  Phone      = sourced from auto.dev live data")
print(f"{'='*70}")
