"""
POC batch test: find dealer URLs for real VINs from 3 searches.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
import time

SKIP_DOMAINS = {
    "autotrader.com", "cars.com", "cargurus.com", "carmax.com",
    "ebay.com", "craigslist.org", "truecar.com", "carfax.com",
    "kbb.com", "edmunds.com", "facebook.com", "instagram.com",
    "youtube.com", "reddit.com", "wikipedia.org", "yelp.com",
    "classic.com", "vehiclehistory.com", "vincheck.info",
    "autocheck.com", "ipacket.us", "dealertrend.com",
    "carvana.com", "vroom.com", "shift.com",
}

def _decode_ddg(href):
    if "duckduckgo.com/l/" in href:
        qs = parse_qs(urlparse(href).query)
        return unquote(qs.get("uddg", [""])[0])
    return href

def find_dealer_url(vin):
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        resp = requests.get("https://html.duckduckgo.com/html/",
                            params={"q": f'"{vin}"'}, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a.result__a"):
            href = _decode_ddg(a.get("href", ""))
            if not href.startswith("http"):
                continue
            domain = urlparse(href).netloc.replace("www.", "")
            if not any(skip in domain for skip in SKIP_DOMAINS):
                return href, domain
    except Exception as e:
        return "", f"ERROR: {e}"
    return "", "NOT FOUND"

searches = {
    "2017 GMC Sierra 2500 Denali HD — under $55k, under 100k miles": [
        ("1GT12UEY1HF151328", "$47,499", "52,573 mi"),
        ("1GT12UEY5HF151297", "$48,991", "82,132 mi"),
        ("1GT12UEY0HF232787", "$45,590", "91,710 mi"),
        ("1GT12UEY0HF173241", "$44,741", "58,066 mi"),
    ],
    "Ferrari SF90 near 92782": [
        ("ZFF95NLA0P0295851", "$445,990", "1,275 mi — Ferrari of Newport Beach"),
        ("ZFF95NLA4N0280198", "$455,999", "1,729 mi — Eurocar"),
        ("ZFF95NLA7R0300398", "$499,000", "4,066 mi — Ilusso"),
        ("ZFF95NLAXP0288714", "$459,990", "1,894 mi — Ferrari of Newport Beach"),
        ("ZFF95NLA5N0271087", "$424,999", "4,674 mi — Eurocar"),
        ("ZFF95NLA8N0277529", "$489,900", "2,593 mi — Ferrari Fort Lauderdale"),
        ("ZFF95NLA0P0294022", "$447,900", "— Scottsdale Ferrari"),
        ("ZFF95NLA7P0295135", "$449,000", "1,065 mi — Ferrari Beverly Hills"),
    ],
    "Honda CR-V near 92782 — under $70k, under 80k miles": [
        ("2HKRS4H78RH426819", "$31,988", "2024 / 16,127 mi"),
        ("2HKRW2H97JH687891", "$21,998", "2018 / 63,780 mi"),
        ("2HKRW1H94LH419295", "$27,342", "2020 / 33,467 mi"),
        ("5J6RW1H58NA009441", "$24,382", "2022 / 54,091 mi"),
        ("5J6RS3H46PL003272", "$28,998", "2023 / 25,107 mi"),
        ("2HKRW1H95HH506954", "$20,258", "2017 / 65,155 mi"),
        ("7FARS3H48PE008468", "$27,000", "2023 / 47,060 mi"),
        ("5J6RW1H52KA007065", "$22,985", "2019 / 41,636 mi"),
        ("2HKRS4H21PH422161", "$26,497", "2023 / 33,218 mi"),
        ("2HKRS3H75RH322038", "$30,969", "2024 / 17,098 mi"),
    ],
}

total = found = 0
for search, vins in searches.items():
    print(f"\n{'='*70}")
    print(f"SEARCH: {search}")
    print(f"{'='*70}")
    for vin, price, info in vins:
        total += 1
        url, domain = find_dealer_url(vin)
        status = "✅" if url else "❌"
        print(f"\n  {status} VIN: {vin}  |  {price}  |  {info}")
        if url:
            found += 1
            print(f"     Dealer: {domain}")
            print(f"     URL:    {url}")
        else:
            print(f"     Result: {domain}")
        time.sleep(0.5)  # be polite to DuckDuckGo

print(f"\n{'='*70}")
print(f"SUMMARY: {found}/{total} VINs resolved to a dealer page")
print(f"{'='*70}")
