"""
VIN Agent — finds the dealer's own car listing page for a given VIN.

Approach:
  Step A: auto.dev        → dealer name, phone, city
  Step B: Claude web_search → intelligently finds + verifies dealer VDP
  Step C: Python verify   → confirm VIN in fallback listing_url
  Step D: phone only      → if all else fails, never show a broken link
"""
import requests
import anthropic

from agents.models import CarListing
from config import ANTHROPIC_API_KEY, AUTODEV_API_KEY

_claude  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
_AUTODEV = "https://auto.dev/api"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


# ── Step A: dealer info from auto.dev ─────────────────────────────────────────

def _get_dealer_info(vin: str) -> dict:
    if not AUTODEV_API_KEY or not vin:
        return {}
    try:
        r = requests.get(
            f"{_AUTODEV}/listings/{vin}",
            headers={"Authorization": f"Bearer {AUTODEV_API_KEY}"},
            timeout=12,
        )
        if r.status_code == 404:
            return {}
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
    except Exception:
        return {}


# ── Step B: Claude web_search ─────────────────────────────────────────────────

def _claude_find_vdp(vin: str, year: int, make: str, model: str,
                     dealer_name: str, city: str, state: str) -> str:
    """
    Claude searches the web, reads pages, confirms the VIN is on the dealer's
    own site. Returns a verified URL or empty string.
    """
    prompt = (
        f"Find the exact listing page for VIN {vin} "
        f"({year} {make} {model}) on the dealer's own website.\n"
        f"Dealer: {dealer_name}, {city}, {state}\n\n"
        f"Instructions:\n"
        f"1. Search for the VIN and the dealer name together\n"
        f"2. Also try searching site:[dealer-domain] for the VIN\n"
        f"3. Open the page and confirm the VIN '{vin}' actually appears on it\n"
        f"4. Only return the dealer's OWN website — not autotrader.com, "
        f"cars.com, cargurus.com, carfax.com, badvin.com, or any aggregator\n\n"
        f"Return ONLY the verified URL. If you cannot find a confirmed dealer "
        f"page with the VIN on it, return exactly: NONE"
    )
    try:
        resp = _claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if block.type == "text":
                url = block.text.strip()
                # Extract just the URL if Claude added explanation
                for word in url.split():
                    if word.startswith("http") and "NONE" not in word:
                        return word.rstrip(".,)")
                if url.startswith("http") and "NONE" not in url:
                    return url
        return ""
    except anthropic.RateLimitError:
        return ""
    except Exception:
        return ""


# ── Step C: verify fallback URL ───────────────────────────────────────────────

def _verify(url: str, vin: str) -> bool:
    if not url:
        return False
    try:
        r = requests.get(url, timeout=10, headers=_HEADERS, allow_redirects=True)
        return vin.upper() in r.text.upper()
    except Exception:
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def run_vin_agent(listing: CarListing) -> CarListing:
    """
    Enriches a CarListing with:
      - dealer_url  : verified dealer own VDP or verified fallback URL
      - dealer_phone: live phone from auto.dev
      - dealer_name : from auto.dev if not already set
    """
    vin = listing.vin or ""

    # Step A — dealer info
    info = _get_dealer_info(vin)
    if info:
        if not listing.dealer_name:
            listing.dealer_name = info.get("dealer_name", "")
        if not listing.dealer_phone:
            listing.dealer_phone = info.get("phone", "")
        if not listing.location:
            city  = info.get("city", "")
            state = info.get("state", "")
            listing.location = f"{city}, {state}".strip(", ")

    if not vin:
        return listing

    # Step B — Claude web_search
    # Claude web_search disabled — cost prohibitive. Pending better solution.
    # if ANTHROPIC_API_KEY: ...


    # Step C — verify existing listing_url as fallback
    if listing.listing_url and _verify(listing.listing_url, vin):
        listing.dealer_url = listing.listing_url

    # Step D — phone only if all else fails (dealer_url stays None)
    return listing
