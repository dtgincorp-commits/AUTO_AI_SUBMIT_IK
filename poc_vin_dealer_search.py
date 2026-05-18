"""
POC: Given a VIN, find the dealer's exact inventory page URL via DuckDuckGo.
Run with: .venv/bin/python poc_vin_dealer_search.py
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote

SKIP_DOMAINS = {
    "autotrader.com", "cars.com", "cargurus.com", "carmax.com",
    "ebay.com", "craigslist.org", "truecar.com", "carfax.com",
    "kbb.com", "edmunds.com", "facebook.com", "instagram.com",
    "youtube.com", "reddit.com", "wikipedia.org", "yelp.com",
    "classic.com", "vehiclehistory.com", "vincheck.info",
    "autocheck.com", "ipacket.us", "dealertrend.com",
    "carvana.com", "vroom.com", "shift.com",
}

def _decode_ddg(href: str) -> str:
    """Decode DuckDuckGo redirect URL to the actual destination URL."""
    if "duckduckgo.com/l/" in href:
        qs = parse_qs(urlparse(href).query)
        return unquote(qs.get("uddg", [""])[0])
    return href

def find_dealer_url(vin: str) -> str:
    """Search DuckDuckGo for a VIN and return the first non-aggregator result URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": f'"{vin}"'},
        headers=headers,
        timeout=10,
    )
    soup = BeautifulSoup(resp.text, "html.parser")
    for a in soup.select("a.result__a"):
        raw_href = a.get("href", "")
        href = _decode_ddg(raw_href)
        if not href.startswith("http"):
            continue
        domain = urlparse(href).netloc.replace("www.", "")
        if not any(skip in domain for skip in SKIP_DOMAINS):
            print(f"  [found] {domain} → {href}")
            return href
    return ""


if __name__ == "__main__":
    test_vins = [
        ("2022 Ferrari SF90 - Fort Lauderdale", "ZFF95NLA8N0277529"),
        ("2023 Ferrari SF90 - Scottsdale AZ",   "ZFF95NLA0P0294022"),
    ]
    for label, vin in test_vins:
        print(f"\n{label}")
        print(f"VIN: {vin}")
        url = find_dealer_url(vin)
        print(f"Dealer URL: {url if url else 'NOT FOUND'}")
