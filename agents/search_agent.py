import re
import json
import requests
from typing import Optional
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.models import CarPreferences, CarListing
from config import LLM_MODEL, OPENAI_API_KEY, MARKETCHECK_API_KEY, AUTODEV_API_KEY, EBAY_APP_ID, SCRAPERAPI_KEY

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


def _resolve_zip(location: str) -> Optional[str]:
    """Return a US 5-digit zip for the location string.

    Returns immediately if the string already contains a zip.
    Otherwise geocodes via Nominatim (OpenStreetMap, free, no key required).
    """
    zip_match = re.search(r"\b(\d{5})\b", location)
    if zip_match:
        return zip_match.group(1)
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": location,
                "format": "json",
                "addressdetails": "1",
                "countrycodes": "us",
                "limit": "1",
            },
            headers={"User-Agent": "AUTO_AI_CarSearch/1.0"},
            timeout=5,
        )
        if resp.status_code == 200:
            hits = resp.json()
            if hits:
                postcode = hits[0].get("address", {}).get("postcode", "")
                if postcode:
                    return postcode[:5]
    except Exception:
        pass
    return None


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

def _search_marketcheck(prefs: CarPreferences, zip_code: Optional[str] = None) -> list[CarListing]:
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

    if zip_code:
        params["zip"] = zip_code
    else:
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
        heading = item.get("heading") or ""
        # Marketcheck headings are often just trim levels ("EX-L AWD") with no make/model.
        # Always prepend year+make+model so the title is human-readable and passes relevance filters.
        if heading and not any(w in heading.lower() for w in [make.lower(), model.lower()]):
            heading = f"{year} {make} {model} {heading}".strip()
        title = heading or f"{year} {make} {model}"
        listings.append(CarListing(
            title=title,
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

def _search_ebay(prefs: CarPreferences, zip_code: Optional[str] = None) -> list[CarListing]:
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
    if zip_code:
        params["buyerPostalCode"] = zip_code

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
# CarGurus — via ScraperAPI (handles Kasada/PerimeterX bot detection)
# ---------------------------------------------------------------------------

def _search_cargurus(prefs: CarPreferences, zip_code: Optional[str] = None) -> list[CarListing]:
    """CarGurus search via ScraperAPI JS-render proxy.
    Requires SCRAPERAPI_KEY in .env — free tier: 1,000 requests/month.
    Returns empty list silently if key or zip_code is not available.
    """
    if not SCRAPERAPI_KEY:
        return []
    if not zip_code:
        return []

    cargurus_url = (
        f"{CARGURUS_BASE}/Cars/inventorylisting/"
        f"viewDetailsFilterViewInventoryListing.action"
        f"?zip={zip_code}"
        f"&distance={min(prefs.radius_miles, 100)}"
        f"&minPrice={prefs.price_min}"
        f"&maxPrice={prefs.price_max}"
        f"&showNegotiable=true&sortDir=ASC&sortType=PRICE"
    )
    # Only add maxMileage if it's a real constraint (not a default placeholder like 999999)
    if prefs.max_mileage and prefs.max_mileage < 300000:
        cargurus_url += f"&maxMileage={prefs.max_mileage}"
    if prefs.condition and prefs.condition != "Any":
        if prefs.condition == "New":
            cargurus_url += "&listingTypes=NEW"
        elif prefs.condition == "Used":
            cargurus_url += "&listingTypes=USED"

    # ScraperAPI is intermittent on JS-rendered pages — retry once
    resp = None
    for _ in range(2):
        resp = requests.get(
            "https://api.scraperapi.com/",
            params={"api_key": SCRAPERAPI_KEY, "url": cargurus_url, "render": "true"},
            timeout=25,             # 25s per attempt; 2 attempts = 50s max
        )
        if len(resp.text) > 1000:   # real HTML is hundreds of KB; error blobs are tiny
            break
    if not resp or len(resp.text) < 1000:
        return []   # ScraperAPI couldn't render — fail silently

    # Verify we got an actual CarGurus page, not a CAPTCHA or error redirect
    if "cargurus" not in resp.text.lower():
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    listings = []

    # Selector: require both showNegotiable and listingId in href — search-result VDP links
    # always carry the full search context; "similar cars" / sponsored links do not.
    seen_ids: set = set()
    for link in soup.select('a[href*="showNegotiable"][href*="listingId"]'):
        href = link.get("href", "")
        lid_m = re.search(r"listingId=(\d+)", href)
        if not lid_m:
            continue
        lid = lid_m.group(1)
        if lid in seen_ids:
            continue
        seen_ids.add(lid)

        if not href.startswith("http"):
            href = f"{CARGURUS_BASE}{href}"

        # Find the smallest ancestor that contains a price AND fits within a single card.
        # Walking too far up lands on a multi-card container and every listing parses
        # to the same (first) car's data.
        text = ""
        node = link
        for _ in range(5):
            if not node.parent or node.parent.name in ("body", "html", "[document]"):
                break
            node = node.parent
            candidate = node.get_text(separator=" ", strip=True)
            if "$" in candidate and len(candidate) < 700:
                text = candidate
                break
        if not text:
            text = link.get_text(separator=" ", strip=True)

        try:
            year_m  = re.search(r"\b((?:19|20)\d{2})\b", text)
            price_m = re.search(r"\$([\d,]+)", text)
            # Require 4+ digits so "5 mi away" distance labels don't match as mileage
            mile_m  = re.search(r"\b([\d,]{4,})\s*mi\b", text)
            loc_m   = re.search(r"([A-Za-z][A-Za-z\s]+,\s*[A-Z]{2})\b", text)

            year    = int(year_m.group(1)) if year_m else 0
            price   = int(price_m.group(1).replace(",", "")) if price_m else 0
            mileage = int(mile_m.group(1).replace(",", "")) if mile_m else 0
            loc     = loc_m.group(1).strip() if loc_m else prefs.location

            # Title: look for YYYY Make Model in the card text; fallback to prefs
            make_pat = re.escape(prefs.make)
            model_pat = re.escape(prefs.model)
            title_m = re.search(
                rf"\b{year}\b\s+{make_pat}\s+{model_pat}[^\n$]{{0,40}}",
                text, re.IGNORECASE,
            ) if year else None
            if title_m:
                title = title_m.group(0).strip()
            elif year:
                title = f"{year} {prefs.make} {prefs.model}"
            else:
                title = f"{prefs.make} {prefs.model}"

            if not price:
                continue
            if prefs.max_mileage and mileage > 0 and mileage > prefs.max_mileage:
                continue

            listings.append(CarListing(
                title=title, price=price, asking_price=price,
                mileage=mileage, year=year,
                location=loc, listing_url=href,
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
    if prefs.condition and prefs.condition != "Any":
        if prefs.condition == "New":
            params["auto_newused"] = "1"
        elif prefs.condition == "Used":
            params["auto_newused"] = "10"

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

def run_search_agent(
    prefs: CarPreferences,
    selected_sources: list = [],
) -> tuple:
    """Query available sources in parallel and return (listings, warning, source_errors).

    selected_sources: if non-empty, only run the named sources.
    """
    # Resolve a zip code once — city/state inputs get geocoded via Nominatim so that
    # sources requiring a zip (CarGurus, eBay) work regardless of how location was entered.
    _zip = _resolve_zip(prefs.location)

    all_candidates = []

    if MARKETCHECK_API_KEY:
        all_candidates.append(("Marketcheck", lambda p=prefs, z=_zip: _search_marketcheck(p, z)))
    if EBAY_APP_ID:
        all_candidates.append(("eBay Motors", lambda p=prefs, z=_zip: _search_ebay(p, z)))
    all_candidates.append(("CarGurus",    lambda p=prefs, z=_zip: _search_cargurus(p, z)))
    all_candidates.append(("Craigslist",  lambda p=prefs: _search_craigslist(p)))

    # Filter to only selected sources when the caller specifies a subset
    if selected_sources:
        sources = [(n, fn) for n, fn in all_candidates if n in selected_sources]
    else:
        sources = all_candidates

    all_listings: list[CarListing] = []
    source_errors: dict = {}

    executor = ThreadPoolExecutor(max_workers=4)
    futures = {executor.submit(fn): name for name, fn in sources}
    try:
        # Hard 55s wall-clock limit across all sources
        for future in as_completed(futures, timeout=55):
            name = futures[future]
            try:
                results = future.result(timeout=25)
                all_listings.extend(results)
                source_errors[name] = f"OK ({len(results)} listings)"
            except Exception as exc:
                source_errors[name] = f"Error: {exc}"
    except TimeoutError:
        # Mark any source that didn't finish in time
        for future, name in futures.items():
            if not future.done():
                source_errors[name] = "Error: timed out"
    finally:
        executor.shutdown(wait=False)  # don't block waiting for slow threads

    if not all_listings:
        if not MARKETCHECK_API_KEY and not EBAY_APP_ID:
            return [], (
                "No API key configured. Add MARKETCHECK_API_KEY or EBAY_APP_ID to .env."
            ), source_errors
        return [], (
            "No listings found. Try widening your price range, increasing the radius, or relaxing filters."
        ), source_errors

    # Deduplicate by (normalised title prefix, price)
    seen: set = set()
    unique: list[CarListing] = []
    for listing in all_listings:
        key = (listing.title.lower()[:40], listing.price)
        if key not in seen:
            seen.add(key)
            unique.append(listing)

    # Relevance filter — only applied to scraped sources (CarGurus, Craigslist, eBay) which can
    # return wrong cars due to fragile HTML parsing. Marketcheck/API sources are already filtered
    # server-side by make/model, so we trust them and skip the check to avoid dropping listings
    # whose headings are trim-only ("EX-L AWD") rather than full vehicle names.
    _SCRAPED = {"CarGurus", "Craigslist", "eBay Motors"}
    make_lc  = prefs.make.lower()
    model_lc = prefs.model.lower()
    unique = [
        l for l in unique
        if l.source not in _SCRAPED
        or make_lc in l.title.lower()
        or model_lc in l.title.lower()
    ]

    # Client-side "New" condition filter — only applied to scraped sources whose server-side
    # condition filtering is unreliable. Marketcheck already sends inventory_type=new and its
    # results (source = "autotrader", "cars.com", "cargurus", etc.) are trusted as-is.
    # Craigslist never reports mileage in search results so it's also exempt.
    if prefs.condition == "New":
        _MILEAGE_FILTER_SOURCES = {"CarGurus", "eBay Motors"}
        unique = [
            l for l in unique
            if l.source not in _MILEAGE_FILTER_SOURCES or l.mileage <= 500
        ]

    # Update source_errors to reflect post-dedup / post-filter counts.
    # Marketcheck listings carry their upstream source name (e.g. "autotrader"), not "Marketcheck",
    # so we only recount sources whose l.source exactly matches the key recorded above.
    _EXACT_SRC = {"CarGurus", "Craigslist", "eBay Motors"}
    post_counts = Counter(l.source for l in unique if l.source in _EXACT_SRC)
    for src_name in _EXACT_SRC:
        if src_name not in source_errors or not source_errors[src_name].startswith("OK"):
            continue
        raw_m = re.search(r"\((\d+)", source_errors[src_name])
        raw = int(raw_m.group(1)) if raw_m else 0
        kept = post_counts.get(src_name, 0)
        if kept == raw:
            pass  # unchanged — label stays as-is
        elif kept == 0:
            source_errors[src_name] = f"OK (0 usable — {raw} returned but filtered out)"
        else:
            source_errors[src_name] = f"OK ({kept} usable; {raw - kept} filtered)"

    if not unique:
        return [], (
            "No listings matched your filters. "
            "Try widening your price range, increasing the radius, or changing the condition."
        ), source_errors

    return unique, None, source_errors
