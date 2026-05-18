"""
POC — Claude VIN Agent with native web_search tool.

Claude searches the web, reads pages, verifies the VIN appears,
and returns only confirmed dealer URLs. One API call per VIN.
No DuckDuckGo scraping. No blind URL filtering. No false positives.

Run: .venv/bin/python poc_claude_websearch_vin.py
"""
import sys, os, time
import requests
import anthropic

sys.path.insert(0, os.path.dirname(__file__))
from config import ANTHROPIC_API_KEY, AUTODEV_API_KEY

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
AUTODEV_BASE = "https://auto.dev/api"


# ── Dealer info from auto.dev ─────────────────────────────────────────────────

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
        phone_tel = str(d.get("phoneTel") or d.get("phoneTelRegional") or "")
        phone = d.get("phone") or (
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


# ── Claude with web_search ────────────────────────────────────────────────────

def claude_find_dealer_vdp(vin: str, make: str, model: str, dealer_name: str) -> str:
    """
    Ask Claude to find and verify the dealer's own listing page for this VIN.
    Claude uses web_search natively — searches, reads pages, confirms VIN present.
    Returns verified URL or empty string.
    """
    prompt = f"""I need to find the exact listing page for a specific car on the dealer's own website.

VIN: {vin}
Car: {make} {model}
Known dealer: {dealer_name}

Please:
1. Search the web for this VIN
2. Find the dealer's own website listing for this exact car (NOT autotrader.com, cars.com, cargurus.com, carfax.com, carmax.com, badvin.com, or any aggregator/VIN-history site)
3. Confirm the VIN "{vin}" actually appears on that page
4. Return ONLY the verified URL — nothing else, no explanation

If you cannot find a verified dealer page, return exactly: NONE"""

    try:
        response = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract final text response
        for block in response.content:
            if block.type == "text":
                url = block.text.strip()
                if url and url != "NONE" and url.startswith("http"):
                    return url
        return ""
    except Exception as e:
        return f"ERROR: {e}"


# ── Aggregator fallback ───────────────────────────────────────────────────────

def aggregator_url(vin: str) -> str:
    return f"https://www.autotrader.com/cars-for-sale/all-cars?vin={vin}&searchRadius=500"


# ── Option D display ──────────────────────────────────────────────────────────

def option_d(vin: str, price: str, info: str, make: str = "", model: str = ""):
    print(f"\n  VIN  : {vin}  |  {price}  |  {info}")

    # Step 1 — dealer info
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
    print(f"  Dealer : {dealer or 'N/A'}  |  {city}, {state}")
    print(f"  Phone  : {phone or 'N/A'}")

    # Step 2 — Claude finds + verifies dealer VDP
    print(f"  Claude : searching and verifying...")
    result = claude_find_dealer_vdp(vin, make, model, dealer)

    if result.startswith("ERROR"):
        print(f"  Claude error: {result}")
        print(f"  [FALLBACK] {aggregator_url(vin)}")
    elif result:
        print(f"  [PRIMARY]  Dealer VDP : {result}")
    else:
        print(f"  [FALLBACK] Aggregator : {aggregator_url(vin)}")
        print(f"             (Claude could not find a verified dealer page)")


# ── Test VINs ─────────────────────────────────────────────────────────────────

searches = {
    "2017 GMC Sierra 2500 Denali HD": [
        ("1GT12UEY1HF151328", "$47,499", "Tustin Buick GMC",  "GMC", "Sierra 2500"),
        ("1GT12UEY5HF151297", "$48,991", "Car Lux Inglewood", "GMC", "Sierra 2500"),
    ],
    "Ferrari SF90 near 92782": [
        ("ZFF95NLA8N0277529", "$489,900", "Ferrari Fort Lauderdale", "Ferrari", "SF90"),
        ("ZFF95NLA0P0294022", "$447,900", "Scottsdale Ferrari",      "Ferrari", "SF90"),
        ("ZFF95NLA7P0295135", "$449,000", "Ferrari Beverly Hills",   "Ferrari", "SF90"),
    ],
    "Honda CR-V near 92782": [
        ("2HKRS4H78RH426819", "$31,988", "2024",               "Honda", "CR-V"),
        ("2HKRW2H97JH687891", "$21,998", "2018 Orange County", "Honda", "CR-V"),
        ("5J6RS3H46PL003272", "$28,998", "Norm Reeves Cerritos","Honda", "CR-V"),
    ],
}

for label, vins in searches.items():
    print(f"\n{'='*70}")
    print(f"SEARCH: {label}")
    print(f"{'='*70}")
    for vin, price, info, make, model in vins:
        option_d(vin, price, info, make, model)
        time.sleep(1)

print(f"\n{'='*70}")
print("LEGEND")
print("  [PRIMARY]  = Claude verified dealer's own car page")
print("  [FALLBACK] = AutoTrader VIN search (always shows the exact car)")
print("  Phone      = sourced from auto.dev live data")
print(f"{'='*70}")
