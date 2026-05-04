import re
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.models import CarPreferences, CarListing
from config import LLM_MODEL, OPENAI_API_KEY, MARKETCHECK_API_KEY, AUTODEV_API_KEY, EBAY_APP_ID

MARKETCHECK_BASE = "https://api.marketcheck.com/v2"
EBAY_FINDING_URL = "https://svcs.ebay.com/services/search/FindingService/v1"
CARGURUS_BASE = "https://www.cargurus.com"

_NORMALIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Return ONLY a JSON object with keys 'make' and 'model', corrected to their exact official names. No extra text."),
    ("human", "Correct this car make and model: make='{make}', model='{model}'"),
])

def _normalize_make_model(make: str, model: str) -> tuple:
    llm = ChatOpenAI(model=LLM_MODEL, openai_api_key=OPENAI_API_KEY, temperature=0)
    chain = _NORMALIZE_PROMPT | llm | StrOutputParser()
    try:
        raw = chain.invoke({"make": make, "model": model})
        data = json.loads(raw)
        return data.get("make", make), data.get("model", model)
    except Exception:
        return make, model


def _parse_location(location: str) -> dict:
    """Extract zip or city/state from a location string for API params."""
    zip_match = re.search(r"\b(\d{5})\b", location)
    if zip_match:
        return {"zip": zip_match.group(1)}
    parts = [p.strip() for p in location.split(",")]
    if len(parts) >= 2:
        return {"city": parts[0], "state": parts[1]}
    return {"city": location}


# ---------------------------------------------------------------------------
# Craigslist helpers
# ---------------------------------------------------------------------------

_CL_SITE_MAP = {
    # California
    "irvine": "losangeles", "los angeles": "losangeles", "la": "losangeles",
    "anaheim": "losangeles", "santa ana": "losangeles", "long beach": "losangeles",
    "orange": "losangeles", "pasadena": "losangeles", "burbank": "losangeles",
    "san diego": "sandiego", "chula vista": "sandiego",
    "san francisco": "sfbay", "sf": "sfbay", "san jose": "sfbay",
    "oakland": "sfbay", "berkeley": "sfbay", "fremont": "sfbay",
    "sacramento": "sacramento", "fresno": "fresno",
    "riverside": "inlandempire", "ontario": "inlandempire", "san bernardino": "inlandempire",
    # New York
    "new york": "newyork", "nyc": "newyork", "manhattan": "newyork",
    "brooklyn": "newyork", "queens": "newyork", "bronx": "newyork",
    "buffalo": "buffalo",
    # Texas
    "houston": "houston", "dallas": "dallas", "austin": "austin",
    "san antonio": "sanantonio", "fort worth": "dallas",
    # Florida
    "miami": "miami", "orlando": "orlando", "tampa": "tampa",
    "jacksonville": "jacksonville", "fort lauderdale": "miami",
    # Illinois
    "chicago": "chicago",
    # Washington
    "seattle": "seattle", "tacoma": "seattle", "bellevue": "seattle",
    # Oregon
    "portland": "portland",
    # Colorado
    "denver": "denver",
    # Massachusetts
    "boston": "boston",
    # Georgia
    "atlanta": "atlanta",
    # Arizona
    "phoenix": "phoenix", "scottsdale": "phoenix", "tempe": "phoenix", "mesa": "phoenix",
    # Nevada
    "las vegas": "lasvegas",
    # Minnesota
    "minneapolis": "minneapolis",
    # Michigan
    "detroit": "detroit",
    # Pennsylvania
    "philadelphia": "philadelphia", "pittsburgh": "pittsburgh",
    # Ohio
    "columbus": "columbus", "cleveland": "cleveland", "cincinnati": "cincinnati",
    # North Carolina
    "charlotte": "charlotte", "raleigh": "raleigh",
    # Maryland/DC
    "baltimore": "baltimore", "washington": "washingtondc", "dc": "washingtondc",
    # Missouri
    "st louis": "stlouis", "kansas city": "kansascity",
    # Tennessee
    "nashville": "nashville", "memphis": "memphis",
}

_STATE_DEFAULT_SITE = {
    "ca": "losangeles", "ny": "newyork", "tx": "houston", "fl": "miami",
    "il": "chicago", "wa": "seattle", "or": "portland", "co": "denver",
    "ma": "boston", "ga": "atlanta", "az": "phoenix", "nv": "lasvegas",
    "pa": "philadelphia", "oh": "columbus", "nc": "charlotte", "mi": "detroit",
    "mn": "minneapolis", "mo": "stlouis", "tn": "nashville", "md": "baltimore",
    "va": "richmond", "in": "indianapolis", "wi": "milwaukee", "ut": "saltlakecity",
}

def _location_to_craigslist_site(location: str) -> str:
    loc = location.lower()
    for city, site in _CL_SITE_MAP.items():
        if city in loc:
            return site
    parts = [p.strip().lower() for p in location.split(",")]
    if len(parts) >= 2:
        state = parts[-1][:2]
        if state in _STATE_DEFAULT_SITE:
            return _STATE_DEFAULT_SITE[state]
    return "losangeles"


# ---------------------------------------------------------------------------
# Marketcheck
# ---------------------------------------------------------------------------

def _search_marketcheck(prefs: CarPreferences) -> list[CarListing]:
    make, model = _normalize_make_model(prefs.make, prefs.model)
    params = {
        "api_key": MARKETCHECK_API_KEY,
        "make": make,
        "model": model,
        "price_min": prefs.price_min,
        "price_max": prefs.price_max,
        "radius": min(prefs.radius_miles, 100),
        "rows": 30,
        "sort_by": "price",
        "sort_order": "asc",
    }
    if prefs.trim and prefs.trim.lower() != "any":
        params["trim"] = prefs.trim
    if prefs.max_mileage:
        params["mileage_max"] = prefs.max_mileage
    if prefs.exterior_color and prefs.exterior_color.lower() != "any":
        params["exterior_color"] = prefs.exterior_color.lower()
    if prefs.certified_only:
        params["inventory_type"] = "certified"
    elif prefs.condition and prefs.condition != "Any":
        params["inventory_type"] = prefs.condition.lower()

    params.update(_parse_location(prefs.location))

    resp = requests.get(f"{MARKETCHECK_BASE}/search/car/active", params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    import datetime
    current_year = datetime.date.today().year

    listings = []
    for item in data.get("listings", []):
        build = item.get("build", {})
        dealer = item.get("dealer", {})
        city = dealer.get("city", "")
        state = dealer.get("state", "")
        loc = ", ".join(filter(None, [city, state]))
        try:
            price = int(float(item.get("price") or 0))
            msrp_raw = int(float(item.get("msrp") or 0)) or None
            miles = int(float(item.get("miles", 0)))
            year = int(build.get("year", 0))
        except (ValueError, TypeError):
            continue

        effective_price = price if price > 0 else (msrp_raw or int((prefs.price_min + prefs.price_max) / 2))

        if prefs.condition == "Used" and miles == 0:
            continue

        raw_source = item.get("source", "")
        display_source = raw_source if raw_source else "Marketcheck"
        listings.append(CarListing(
            title=item.get("heading") or f"{year} {prefs.make} {prefs.model}",
            price=effective_price,
            asking_price=price,
            mileage=miles,
            year=year,
            msrp=msrp_raw,
            exterior_color=item.get("exterior_color"),
            interior_color=item.get("interior_color"),
            dealer_name=dealer.get("name"),
            location=loc or prefs.location,
            listing_url=item.get("vdp_url"),
            source=display_source,
        ))
    return listings


# ---------------------------------------------------------------------------
# eBay Motors — Finding API (free, requires EBAY_APP_ID)
# ---------------------------------------------------------------------------

def _search_ebay(prefs: CarPreferences) -> list[CarListing]:
    if not EBAY_APP_ID:
        return []

    keywords = f"{prefs.make} {prefs.model}"
    if prefs.trim and prefs.trim.lower() not in ("", "any"):
        keywords += f" {prefs.trim}"

    params = {
        "OPERATION-NAME": "findItemsAdvanced",
        "SERVICE-VERSION": "1.0.0",
        "SECURITY-APPNAME": EBAY_APP_ID,
        "RESPONSE-DATA-FORMAT": "JSON",
        "categoryId": "6001",          # eBay Motors → Cars & Trucks
        "keywords": keywords,
        "itemFilter(0).name": "MinPrice",
        "itemFilter(0).value": str(prefs.price_min),
        "itemFilter(0).paramName": "Currency",
        "itemFilter(0).paramValue": "USD",
        "itemFilter(1).name": "MaxPrice",
        "itemFilter(1).value": str(prefs.price_max),
        "itemFilter(1).paramName": "Currency",
        "itemFilter(1).paramValue": "USD",
        "outputSelector(0)": "ItemSpecifics",
        "paginationInput.entriesPerPage": "15",
        "sortOrder": "PricePlusShippingLowest",
    }
    loc = _parse_location(prefs.location)
    if "zip" in loc:
        params["buyerPostalCode"] = loc["zip"]

    resp = requests.get(EBAY_FINDING_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    search_result = (data.get("findItemsAdvancedResponse") or [{}])[0]
    items = (search_result.get("searchResult") or [{}])[0].get("item") or []

    listings = []
    for item in items:
        try:
            title = (item.get("title") or [""])[0]
            price_block = (item.get("sellingStatus") or [{}])[0]
            price = int(float((price_block.get("currentPrice") or [{}])[0].get("__value__", 0)))
            if price <= 0:
                continue

            location_raw = (item.get("location") or [""])[0]
            url = (item.get("viewItemURL") or [""])[0]

            year_m = re.search(r"\b(19|20)\d{2}\b", title)
            year = int(year_m.group()) if year_m else 0

            mileage = 0
            for spec_wrapper in (item.get("itemSpecifics") or []):
                for nv in (spec_wrapper.get("nameValueList") or []):
                    name = (nv.get("name") or [""])[0].lower()
                    if "mileage" in name or "miles" in name:
                        val_raw = (nv.get("value") or ["0"])[0].replace(",", "").split()[0]
                        try:
                            mileage = int(float(val_raw))
                        except Exception:
                            pass

            if prefs.max_mileage and mileage > 0 and mileage > prefs.max_mileage:
                continue

            listings.append(CarListing(
                title=title,
                price=price,
                asking_price=price,
                mileage=mileage,
                year=year,
                location=location_raw or prefs.location,
                listing_url=url,
                source="eBay Motors",
            ))
        except Exception:
            continue

    return listings


# ---------------------------------------------------------------------------
# CarGurus — web scrape (JSON-LD structured data)
# ---------------------------------------------------------------------------

def _search_cargurus(prefs: CarPreferences) -> list[CarListing]:
    loc = _parse_location(prefs.location)
    zip_code = loc.get("zip")
    if not zip_code:
        return []   # CarGurus requires a 5-digit zip

    params = {
        "zip": zip_code,
        "distance": min(prefs.radius_miles, 100),
        "minPrice": prefs.price_min,
        "maxPrice": prefs.price_max,
        "showNegotiable": "true",
        "sortDir": "ASC",
        "sortType": "PRICE",
        "keywords": f"{prefs.make} {prefs.model}",
    }
    if prefs.max_mileage:
        params["maxMileage"] = prefs.max_mileage

    url = f"{CARGURUS_BASE}/Cars/new/nl/Cars/d_Cars"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    resp = requests.get(url, params=params, headers=headers, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    listings = []

    # Primary: JSON-LD structured data (Car / Vehicle schema)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            ld = json.loads(script.string or "")
            items = ld if isinstance(ld, list) else [ld]
            for item in items:
                if item.get("@type") not in ("Car", "Vehicle"):
                    continue
                title = item.get("name", "")
                offers = item.get("offers") or {}
                price = int(float(str(offers.get("price", 0)).replace(",", "")))
                mileage_info = item.get("mileageFromOdometer") or {}
                mileage = int(float(str(mileage_info.get("value", 0)).replace(",", "")))
                year_m = re.search(r"\b(19|20)\d{2}\b", title)
                year = int(year_m.group()) if year_m else int(item.get("modelYear") or 0)
                listing_url = item.get("url") or offers.get("url", "")
                color = item.get("color", "")

                if not title or not price:
                    continue
                if prefs.max_mileage and mileage > 0 and mileage > prefs.max_mileage:
                    continue

                listings.append(CarListing(
                    title=title,
                    price=price,
                    asking_price=price,
                    mileage=mileage,
                    year=year,
                    exterior_color=color or None,
                    location=prefs.location,
                    listing_url=listing_url,
                    source="CarGurus",
                ))
        except Exception:
            continue

    # Fallback: parse listing card elements from HTML
    if not listings:
        for card in soup.select(
            "a[data-cg-ft='car-blade-link'], article.listing-item, div.listingCard"
        ):
            try:
                title_el = card.select_one("h4, [class*='title'], [class*='heading']")
                price_el = card.select_one("[class*='price'], [data-testid*='price']")
                link_el = card if card.name == "a" else card.select_one("a[href]")

                if not title_el or not price_el:
                    continue

                title = title_el.get_text(strip=True)
                price_text = re.sub(r"[^\d]", "", price_el.get_text(strip=True))
                price = int(price_text) if price_text else 0
                href = (link_el.get("href") or "") if link_el else ""
                if href and not href.startswith("http"):
                    href = f"{CARGURUS_BASE}{href}"

                year_m = re.search(r"\b(19|20)\d{2}\b", title)
                year = int(year_m.group()) if year_m else 0

                if price and prefs.price_min <= price <= prefs.price_max:
                    listings.append(CarListing(
                        title=title,
                        price=price,
                        asking_price=price,
                        mileage=0,
                        year=year,
                        location=prefs.location,
                        listing_url=href,
                        source="CarGurus",
                    ))
            except Exception:
                continue

    return listings[:15]


# ---------------------------------------------------------------------------
# Craigslist — web scrape (no API key needed)
# ---------------------------------------------------------------------------

def _search_craigslist(prefs: CarPreferences) -> list[CarListing]:
    site = _location_to_craigslist_site(prefs.location)

    query = f"{prefs.make} {prefs.model}"
    if prefs.trim and prefs.trim.lower() not in ("", "any"):
        query += f" {prefs.trim}"

    params = {
        "query": query,
        "min_price": prefs.price_min,
        "max_price": prefs.price_max,
        "srchType": "T",   # title-only search — more relevant results
        "hasPic": "1",
    }
    if prefs.max_mileage:
        params["max_auto_miles"] = prefs.max_mileage

    url = f"https://{site}.craigslist.org/search/cta"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;"
            "q=0.8,application/signed-exchange;v=b3;q=0.7"
        ),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

    session = requests.Session()
    # First hit the homepage so Akamai sees a normal browsing pattern
    try:
        session.get(f"https://{site}.craigslist.org", headers=headers, timeout=10)
    except Exception:
        pass
    resp = session.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    listings = []

    # Craigslist static search result design
    for result in soup.select("li.cl-static-search-result, li.cl-search-result, li.result-row"):
        try:
            title_el = (
                result.select_one("div.title")
                or result.select_one("span[data-testid='listing-title']")
                or result.select_one("a.result-title")
            )
            price_el = (
                result.select_one("div.price")
                or result.select_one("span.priceinfo")
                or result.select_one("span.result-price")
            )
            link_el = (
                result.select_one("a[href]")
            )
            location_el = (
                result.select_one("div.location")
                or result.select_one("div.meta span:last-child")
                or result.select_one("span.result-hood")
            )

            if not title_el or not link_el:
                continue

            title = title_el.get_text(strip=True)
            price_text = re.sub(r"[^\d]", "", (price_el.get_text(strip=True) if price_el else ""))
            price = int(price_text) if price_text else 0
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://{site}.craigslist.org{href}"
            loc_text = location_el.get_text(strip=True).strip("() ") if location_el else ""

            year_m = re.search(r"\b(19|20)\d{2}\b", title)
            year = int(year_m.group()) if year_m else 0

            if not price or not (prefs.price_min <= price <= prefs.price_max):
                continue

            listings.append(CarListing(
                title=title,
                price=price,
                asking_price=price,
                mileage=0,   # not shown in CL search results; visible on listing page
                year=year,
                location=loc_text or prefs.location,
                listing_url=href,
                source="Craigslist",
            ))
        except Exception:
            continue

    return listings[:15]


# ---------------------------------------------------------------------------
# GPT fallback (unused in production — kept for reference)
# ---------------------------------------------------------------------------

_SEARCH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a car marketplace search agent. Return a JSON array of exactly 5 realistic "
        "car listings matching the criteria. Each listing must have: title (string), price (int), "
        "mileage (int), year (int), exterior_color, interior_color, dealer_name, location, "
        "listing_url (use a real Cars.com or CarGurus search URL format)."
    )),
    ("human", (
        "Find cars matching these preferences:\n"
        "Make: {make}, Model: {model}\n"
        "Price range: ${price_min:,} - ${price_max:,}\n"
        "Max mileage: {max_mileage} miles\n"
        "Exterior color: {exterior_color}\n"
        "Interior color: {interior_color}\n"
        "Location: {location} (within {radius_miles} miles)\n\n"
        "Return ONLY a valid JSON array, no markdown, no code fences."
    )),
])


# ---------------------------------------------------------------------------
# Main entry point — parallel multi-source search
# ---------------------------------------------------------------------------

def run_search_agent(prefs: CarPreferences) -> tuple:
    """Query all available sources in parallel and return merged, deduplicated listings."""
    sources = []

    if MARKETCHECK_API_KEY:
        sources.append(("Marketcheck", lambda p=prefs: _search_marketcheck(p)))

    if EBAY_APP_ID:
        sources.append(("eBay Motors", lambda p=prefs: _search_ebay(p)))

    sources.append(("CarGurus", lambda p=prefs: _search_cargurus(p)))
    sources.append(("Craigslist", lambda p=prefs: _search_craigslist(p)))

    all_listings: list[CarListing] = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): name for name, fn in sources}
        for future in as_completed(futures):
            try:
                all_listings.extend(future.result(timeout=25))
            except Exception:
                pass  # source failed silently; others still contribute

    if not all_listings:
        if not MARKETCHECK_API_KEY and not EBAY_APP_ID:
            return [], (
                "No API key configured. Add MARKETCHECK_API_KEY or EBAY_APP_ID to .env, "
                "or results will come from CarGurus/Craigslist scraping only."
            )
        return [], (
            "No listings found matching your criteria. "
            "Try widening your price range, increasing the search radius, or relaxing other filters."
        )

    # Deduplicate by (normalised title prefix, price)
    seen: set = set()
    unique: list[CarListing] = []
    for listing in all_listings:
        key = (listing.title.lower()[:40], listing.price)
        if key not in seen:
            seen.add(key)
            unique.append(listing)

    return unique, None
