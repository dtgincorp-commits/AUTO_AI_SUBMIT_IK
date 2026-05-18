"""
POC — Full VIN pipeline for a real NL query.

Steps:
  1. Parse NL query → CarPreferences
  2. Search → ranked listings with VINs
  3. For top 3 listings with VINs → run VIN agent:
       Step A: auto.dev  → dealer name, phone
       Step B: Claude    → find + verify dealer's own car page
       Step C: Python    → verify fallback if Claude finds nothing
       Step D: Phone only if all else fails

Run: .venv/bin/python poc_full_vin_pipeline.py
"""
import sys, os, time, requests
sys.path.insert(0, os.path.dirname(__file__))

import anthropic
from config import ANTHROPIC_API_KEY, AUTODEV_API_KEY
from agents.nl_parser import parse_query
from agents.search_agent import run_search_agent
from agents.ranking_agent import run_ranking_agent

claude  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
AUTODEV = "https://auto.dev/api"

NL_QUERY = "2017 gmc sierra 2500 denali HD less than 100k miles $55k or less"

SKIP_DOMAINS = {
    "autotrader.com","cars.com","cargurus.com","carmax.com","ebay.com",
    "craigslist.org","truecar.com","carfax.com","kbb.com","edmunds.com",
    "facebook.com","instagram.com","youtube.com","reddit.com","badvin.com",
    "vehiclehistory.com","vincheck.info","autocheck.com","ipacket.us",
    "carvana.com","vroom.com","shift.com","classic.com","motortrend.com",
}


# ─── Step A: dealer info ──────────────────────────────────────────────────────

def get_dealer_info(vin: str) -> dict:
    if not AUTODEV_API_KEY or not vin:
        return {}
    try:
        r = requests.get(
            f"{AUTODEV}/listings/{vin}",
            headers={"Authorization": f"Bearer {AUTODEV_API_KEY}"},
            timeout=15,
        )
        if r.status_code == 404:
            return {"error": "not_found"}
        r.raise_for_status()
        d = r.json()
        pt = str(d.get("phoneTel") or d.get("phoneTelRegional") or "")
        phone = d.get("phone") or (
            f"({pt[:3]}) {pt[3:6]}-{pt[6:]}" if len(pt) == 10 else pt
        )
        return {
            "dealer_name": d.get("dealerName") or "",
            "city":        d.get("city") or "",
            "state":       d.get("state") or "",
            "phone":       phone,
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Step B: Claude web_search ────────────────────────────────────────────────

def claude_find_vdp(vin: str, year: int, make: str, model: str, dealer: str) -> str:
    prompt = (
        f"Find the exact listing page for VIN {vin} "
        f"({year} {make} {model}) on the dealer's own website.\n"
        f"Known dealer: {dealer}\n"
        f"Skip: autotrader.com, cars.com, cargurus.com, carfax.com, "
        f"badvin.com, and all aggregator or VIN-history sites.\n"
        f"Confirm the VIN '{vin}' actually appears on the page.\n"
        f"Return ONLY the verified URL, or NONE."
    )
    try:
        resp = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if block.type == "text":
                url = block.text.strip()
                if url and url != "NONE" and url.startswith("http"):
                    return url
        return ""
    except anthropic.RateLimitError:
        return "RATE_LIMITED"
    except Exception as e:
        return f"ERROR:{e}"


# ─── Step C: verify fallback URL ─────────────────────────────────────────────

def verify_url(url: str, vin: str) -> bool:
    if not url:
        return False
    try:
        r = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0"
        })
        return vin.upper() in r.text.upper()
    except Exception:
        return False


# ─── Full VIN agent ───────────────────────────────────────────────────────────

def run_vin_agent(listing, delay: float = 35.0):
    vin          = listing.vin or ""
    year         = listing.year
    make_model   = listing.title  # e.g. "2017 GMC Sierra 2500HD Denali"
    price        = f"${listing.price:,}"
    mileage      = f"{listing.mileage:,} mi"
    fallback_url = listing.listing_url or ""

    print(f"\n  {'─'*66}")
    print(f"  {listing.title}  |  {price}  |  {mileage}")
    print(f"  VIN     : {vin or 'NOT AVAILABLE'}")
    print(f"  Source  : {listing.source}")

    if not vin:
        print(f"  ⚠️  No VIN — skipping VIN agent")
        if fallback_url:
            print(f"  [FALLBACK] {fallback_url}")
        return

    # Step A — dealer info
    info = get_dealer_info(vin)
    if "error" not in info:
        print(f"  Dealer  : {info.get('dealer_name','N/A')}  |  {info.get('city','')}, {info.get('state','')}")
        print(f"  Phone   : {info.get('phone') or 'N/A'}")
    else:
        print(f"  Dealer  : (auto.dev: {info.get('error')})")

    # Step B — Claude
    print(f"  Claude  : searching (waiting {int(delay)}s rate-limit gap)...")
    time.sleep(delay)

    parts      = make_model.split()
    yr         = year
    make       = parts[1] if len(parts) > 1 else ""
    model      = " ".join(parts[2:]) if len(parts) > 2 else ""
    dealer_name= info.get("dealer_name","") if "error" not in info else ""

    vdp = claude_find_vdp(vin, yr, make, model, dealer_name)

    if vdp == "RATE_LIMITED":
        print(f"  Claude  : rate limited — skipping to fallback")
    elif vdp.startswith("ERROR"):
        print(f"  Claude  : {vdp}")
    elif vdp:
        print(f"  [PRIMARY]  Dealer VDP : {vdp}")
        return

    # Step C — verify fallback
    if fallback_url:
        print(f"  Fallback: verifying {fallback_url[:60]}...")
        if verify_url(fallback_url, vin):
            print(f"  [FALLBACK ✅] {fallback_url}")
        else:
            print(f"  [FALLBACK ❌] URL did not contain VIN — link may be stale")
    else:
        print(f"  [PHONE ONLY] Call dealer directly: {info.get('phone','N/A')}")


# ─── Main ─────────────────────────────────────────────────────────────────────

print(f"\n{'='*70}")
print(f"QUERY: \"{NL_QUERY}\"")
print(f"{'='*70}")

# Step 1 — parse
print("\n[1] Parsing query...")
prefs, err = parse_query(NL_QUERY)
if err:
    print(f"Parse error: {err}")
    sys.exit(1)
from agents.models import CarPreferences
cp = CarPreferences(**{
    "make":        prefs.get("make","GMC"),
    "model":       prefs.get("model","Sierra 2500HD"),
    "trim":        prefs.get("trim"),
    "price_min":   prefs.get("price_min", 0),
    "price_max":   prefs.get("price_max", 55000),
    "max_mileage": prefs.get("max_mileage", 100000),
    "location":    prefs.get("location","Los Angeles, CA"),
    "radius_miles":prefs.get("radius_miles", 50),
    "condition":   prefs.get("condition","Used"),
})
print(f"    make={cp.make}  model={cp.model}  trim={cp.trim}")
print(f"    price_max=${cp.price_max:,}  max_mileage={cp.max_mileage:,}")
print(f"    location={cp.location}  radius={cp.radius_miles}mi")

# Step 2 — search
print("\n[2] Searching marketplaces...")
result = run_search_agent(cp)
listings, warning = result[0], result[1]
if warning:
    print(f"    ⚠️  {warning}")
print(f"    Found {len(listings)} listings")

# Step 3 — rank
print("\n[3] Ranking...")
ranked = run_ranking_agent(cp, listings)
print(f"    Top results:")
for i, l in enumerate(ranked[:5], 1):
    print(f"    {i}. {l.title}  ${l.price:,}  {l.mileage:,}mi  VIN:{l.vin or 'N/A'}  score:{l.match_score}")

# Step 4 — VIN agent on top 3 that have VINs
print(f"\n[4] VIN Agent (Claude) — top listings with VINs")
print(f"    Note: 35s delay between each call (Tier 1 rate limit)")

with_vins = [l for l in ranked if l.vin][:3]
without   = [l for l in ranked if not l.vin]

if not with_vins:
    print("    No VINs found in results — check search sources")

for listing in with_vins:
    run_vin_agent(listing, delay=35.0)

print(f"\n{'='*70}")
print("DONE")
print(f"{'='*70}")
