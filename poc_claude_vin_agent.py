"""
POC — Intelligent VIN Agent using LLM reasoning.

The gap with plain DuckDuckGo scraping: blind URL filtering returns false
positives (badvin.com, efaq.com) because there's no reasoning about WHAT
the page actually is.

This POC fixes that by:
1. Getting top 10 DuckDuckGo results for the VIN
2. Feeding titles + URLs to GPT-4o-mini
3. Letting the LLM reason: "which of these is the dealer's own car page?"

Same intelligence gap that Claude subagent fills natively — implemented here
via OpenAI reasoning over search results.

Run: .venv/bin/python poc_claude_vin_agent.py
"""
import sys, os, time, json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
from openai import OpenAI

sys.path.insert(0, os.path.dirname(__file__))
from config import OPENAI_API_KEY, AUTODEV_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
AUTODEV_BASE = "https://auto.dev/api"

ALWAYS_SKIP = {
    "autotrader.com", "cars.com", "cargurus.com", "carmax.com",
    "ebay.com", "craigslist.org", "truecar.com", "carfax.com",
    "kbb.com", "edmunds.com", "facebook.com", "instagram.com",
    "youtube.com", "reddit.com", "wikipedia.org", "yelp.com",
    "classic.com", "vehiclehistory.com", "vincheck.info",
    "autocheck.com", "ipacket.us", "dealertrend.com",
    "carvana.com", "vroom.com", "shift.com", "duckduckgo.com",
    "efaq.com", "google.com", "bing.com", "badvin.com",
    "carfax.com", "motortrend.com",
}

DDG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ── Step 1: Get dealer info from auto.dev ─────────────────────────────────────

def get_dealer_info(vin: str) -> dict:
    if not AUTODEV_API_KEY:
        return {}
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
        phone_raw = d.get("phone") or ""
        phone_tel = str(d.get("phoneTel") or d.get("phoneTelRegional") or "")
        phone = phone_raw or (
            f"({phone_tel[:3]}) {phone_tel[3:6]}-{phone_tel[6:]}"
            if len(phone_tel) == 10 else phone_tel
        )
        return {
            "dealer_name": d.get("dealerName") or "",
            "city":        d.get("city") or "",
            "state":       d.get("state") or "",
            "phone":       phone,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Step 2: Fetch top DDG results with titles ─────────────────────────────────

def _decode_ddg(href: str) -> str:
    if "duckduckgo.com/l/" in href:
        qs = parse_qs(urlparse(href).query)
        return unquote(qs.get("uddg", [""])[0])
    return href


def get_search_candidates(vin: str) -> list[dict]:
    """Return up to 10 {title, url, domain} results from DuckDuckGo."""
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": f'"{vin}"'},
            headers=DDG_HEADERS,
            timeout=12,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        candidates = []
        for a in soup.select("a.result__a"):
            href = _decode_ddg(a.get("href", ""))
            if not href.startswith("http"):
                continue
            domain = urlparse(href).netloc.replace("www.", "")
            if any(skip in domain for skip in ALWAYS_SKIP):
                continue
            if href.startswith("https://duckduckgo.com/y.js"):
                continue
            title = a.get_text(strip=True)
            candidates.append({"title": title, "url": href, "domain": domain})
            if len(candidates) >= 10:
                break
        return candidates
    except Exception:
        return []


# ── Step 3: LLM reasons about which result is the dealer's own VDP ────────────

def llm_pick_dealer_vdp(vin: str, make: str, model: str, candidates: list[dict]) -> str:
    """Ask GPT-4o-mini to identify the dealer's own listing page from candidates."""
    if not candidates:
        return ""

    candidate_text = "\n".join(
        f"{i+1}. [{c['domain']}] {c['title']}\n   URL: {c['url']}"
        for i, c in enumerate(candidates)
    )

    prompt = f"""You are helping find the exact listing page for a specific car on the dealer's own website.

VIN: {vin}
Car: {make} {model}

Search results (already filtered to remove major aggregators):
{candidate_text}

Task: Identify which result (if any) is the dealer's own inventory/listing page for this exact VIN.

Rules:
- A dealer's own page will be on a dealership domain (e.g. ferrarifl.com, normreeveshonda.com, carluxlax.com)
- Reject: VIN history sites (badvin.com, vincheck.info, autocheck.com), auction sites, press/review articles, forum posts, ipacket.us dealer documents
- The page should be the car's listing/detail/inventory page, not just the dealer's homepage
- If none of the results are clearly a dealer's own listing page, return "none"

Return ONLY a JSON object: {{"url": "<the url>" }} or {{"url": "none"}}
No explanation, no markdown."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(raw)
        url = data.get("url", "none")
        return "" if url == "none" else url
    except Exception:
        return ""


# ── Aggregator fallback (always works) ────────────────────────────────────────

def aggregator_url(vin: str) -> str:
    return f"https://www.autotrader.com/cars-for-sale/all-cars?vin={vin}&searchRadius=500"


# ── Option D: full lookup + display ───────────────────────────────────────────

def option_d(vin: str, price: str, info: str, delay: float = 3.0):
    print(f"\n  VIN : {vin}  |  {price}  |  {info}")

    # Dealer info from auto.dev
    dealer_info = get_dealer_info(vin)
    if "error" in dealer_info:
        err = dealer_info["error"]
        print(f"  auto.dev : {'listing not found (sold?)' if err == 'not_found' else err}")
        print(f"  [FALLBACK] {aggregator_url(vin)}")
        return

    dealer = dealer_info.get("dealer_name", "")
    phone  = dealer_info.get("phone", "")
    city   = dealer_info.get("city", "")
    state  = dealer_info.get("state", "")
    print(f"  Dealer   : {dealer or 'N/A'}  |  {city}, {state}")
    print(f"  Phone    : {phone or 'N/A'}")

    time.sleep(delay)

    # Get DDG candidates
    candidates = get_search_candidates(vin)
    print(f"  DDG hits : {len(candidates)} non-aggregator results found")

    # LLM picks the right one
    dealer_vdp = llm_pick_dealer_vdp(vin, "", "", candidates) if candidates else ""

    if dealer_vdp:
        domain = urlparse(dealer_vdp).netloc.replace("www.", "")
        print(f"  [PRIMARY]  Dealer VDP : {dealer_vdp}")
        print(f"             (on {domain})")
    else:
        print(f"  [FALLBACK] Aggregator  : {aggregator_url(vin)}")
        if candidates:
            print(f"             (LLM found no clean dealer VDP in {len(candidates)} results)")
        else:
            print(f"             (no search results found)")


# ── Test VINs ─────────────────────────────────────────────────────────────────

searches = {
    "2017 GMC Sierra 2500 Denali HD": [
        ("1GT12UEY1HF151328", "$47,499", "Tustin Buick GMC"),
        ("1GT12UEY5HF151297", "$48,991", "Car Lux Inglewood"),
    ],
    "Ferrari SF90 near 92782": [
        ("ZFF95NLA8N0277529", "$489,900", "Ferrari Fort Lauderdale"),
        ("ZFF95NLA0P0294022", "$447,900", "Scottsdale Ferrari"),
        ("ZFF95NLA7P0295135", "$449,000", "Ferrari Beverly Hills"),
    ],
    "Honda CR-V near 92782": [
        ("2HKRS4H78RH426819", "$31,988",  "2024 — Cerritos area"),
        ("2HKRW2H97JH687891", "$21,998",  "2018 — Orange County"),
        ("5J6RS3H46PL003272", "$28,998",  "Norm Reeves Honda Cerritos"),
    ],
}

primary = fallback = total = 0

for label, vins in searches.items():
    print(f"\n{'='*70}")
    print(f"SEARCH: {label}")
    print(f"{'='*70}")
    for vin, price, info in vins:
        total += 1
        option_d(vin, price, info, delay=3.0)

print(f"\n{'='*70}")
print("LEGEND")
print("  [PRIMARY]  = dealer's own exact car page — no middleman")
print("  [FALLBACK] = AutoTrader VIN search — always shows the exact car")
print("  Phone      = sourced from auto.dev live data")
print(f"{'='*70}")
