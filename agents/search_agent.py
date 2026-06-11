import re
import json
import math
import requests
from urllib.parse import urlencode
from typing import Optional, Tuple
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.models import CarPreferences, CarListing
from config import LLM_MODEL, OPENAI_API_KEY, MARKETCHECK_API_KEY, MARKETCHECK_API_KEY2, AUTODEV_API_KEY, EBAY_APP_ID, SCRAPERAPI_KEY, get_langfuse_callbacks

MARKETCHECK_BASE = "https://api.marketcheck.com/v2"
EBAY_FINDING_URL = "https://svcs.ebay.com/services/search/FindingService/v1"
CARGURUS_BASE = "https://www.cargurus.com"
AUTODEV_BASE = "https://auto.dev/api"

_NORMALIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "Return ONLY a JSON object with keys 'make' and 'model', corrected to their exact "
        "official names as used in dealer inventory databases. No extra text. "
        "Mercedes-Benz sedan/coupe naming rules (critical — dealer DBs use class names, not number codes): "
        "E450/E350/E300/E63 → model='E-Class'; "
        "C300/C350/C43/C63 → model='C-Class'; "
        "S450/S500/S580/S63/S650 → model='S-Class'; "
        "A220/A35 → model='A-Class'; "
        "G550/G63 → model='G-Class'; "
        "CLA250/CLA45 → model='CLA'; "
        "CLS450/CLS53 → model='CLS'; "
        "SUVs keep full names: GLS 450, GLE 350, GLC 300, GLB 250, GLA 250 stay as-is. "
        "BMW: X5/X3/X7 stay as-is; 3 Series/5 Series/7 Series use 'X Series' format. "
        "Audi RS/SQ models: ALWAYS preserve the RS or SQ prefix as part of the model name. "
        "RS Q8 stays 'RS Q8'; RS Q3 stays 'RS Q3'; RS3 stays 'RS3'; RS5 stays 'RS5'; RS6 stays 'RS6'; RS7 stays 'RS7'; SQ5 stays 'SQ5'; SQ7 stays 'SQ7'; SQ8 stays 'SQ8'. "
        "Always return the make as the full official brand name e.g. 'Mercedes-Benz' not 'Mercedes'."
    )),
    ("human", "Correct this car make and model: make='{make}', model='{model}'"),
])

def _normalize_make_model(make: str, model: str) -> tuple:
    llm = ChatOpenAI(model=LLM_MODEL, openai_api_key=OPENAI_API_KEY, temperature=0)
    chain = _NORMALIZE_PROMPT | llm | StrOutputParser()
    try:
        _cb = get_langfuse_callbacks()
        raw = chain.invoke({"make": make, "model": model}, config={"callbacks": _cb} if _cb else {})
        data = json.loads(raw)
        norm_make  = data.get("make", make)
        norm_model = data.get("model", model)
    except Exception:
        norm_make, norm_model = make, model
    # Final pass: canonicalize against NHTSA to ensure exact official model name
    try:
        from agents.nhtsa import canonicalize_model
        norm_model = canonicalize_model(norm_make, norm_model)
    except Exception:
        pass
    return norm_make, norm_model


def _parse_location(location: str) -> dict:
    """Extract zip or city/state from a location string for API params."""
    zip_match = re.search(r"\b(\d{5})\b", location)
    if zip_match:
        return {"zip": zip_match.group(1)}
    parts = [p.strip() for p in location.split(",")]
    if len(parts) >= 2:
        return {"city": parts[0], "state": parts[1]}
    return {"city": location}


def _resolve_location(location: str) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    """Single Nominatim call → (zip, lat, lon).

    Extracts zip from the string if present, then geocodes once to get
    coordinates. Returns (None, None, None) on failure.
    """
    zip_match = re.search(r"\b(\d{5})\b", location)
    query = zip_match.group(1) if zip_match else location
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
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
                hit = hits[0]
                zip_code = (zip_match.group(1) if zip_match
                            else hit.get("address", {}).get("postcode", "")[:5] or None)
                lat = float(hit["lat"])
                lon = float(hit["lon"])
                return zip_code, lat, lon
    except Exception:
        pass
    # If Nominatim fails but we have a zip, return it with no coords
    return (zip_match.group(1) if zip_match else None), None, None


# Keep _resolve_zip as a thin wrapper for callers that only need the zip
def _resolve_zip(location: str) -> Optional[str]:
    zip_code, _, _ = _resolve_location(location)
    return zip_code


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles between two lat/lon points."""
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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

def _marketcheck_cache_available() -> bool:
    try:
        import streamlit as st
        return True
    except Exception:
        return False

def _fetch_marketcheck_raw(make, model, price_min, price_max, radius, condition,
                            certified_only, trim, max_mileage, exterior_color,
                            zip_code, location_str):
    """Raw Marketcheck API call — wrapped in cache below."""
    params = {
        "api_key": MARKETCHECK_API_KEY,
        "make": make,
        "model": model,
        "radius": min(radius, 200),
        # Plan caps rows at 50; values above the cap are silently ignored and the
        # API reverts to its default of 10 (confirmed live 2026-06-10)
        "rows": 50,
        "sort_by": "price",
        "sort_order": "asc",
    }
    # Only pass price when user explicitly set a budget — listings with no price get excluded otherwise
    if price_max and price_max < 999000:
        params["price_min"] = price_min
        params["price_max"] = price_max
    # trim not passed — auto.dev returns 400, Marketcheck is unreliable; ranking agent scores by title
    if max_mileage and condition != "New":
        params["mileage_max"] = max_mileage
    if exterior_color and exterior_color.lower() != "any":
        params["exterior_color"] = exterior_color.lower()
    if certified_only:
        params["inventory_type"] = "certified"
    elif condition and condition != "Any":
        params["inventory_type"] = condition.lower()
    if zip_code:
        params["zip"] = zip_code
    elif location_str:
        params.update(_parse_location(location_str))
    resp = requests.get(f"{MARKETCHECK_BASE}/search/car/active", params=params, timeout=15)
    if resp.status_code in (401, 403, 429) and MARKETCHECK_API_KEY2:
        params["api_key"] = MARKETCHECK_API_KEY2
        resp = requests.get(f"{MARKETCHECK_BASE}/search/car/active", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()

# Wrap with st.cache_data (2-hour TTL) when running inside Streamlit.
# Falls back to direct call when running outside Streamlit (e.g. unit tests).
try:
    import streamlit as st
    _fetch_marketcheck_cached = st.cache_data(ttl=7200, show_spinner=False)(_fetch_marketcheck_raw)
except Exception:
    _fetch_marketcheck_cached = _fetch_marketcheck_raw


def _search_marketcheck(prefs: CarPreferences, zip_code: Optional[str] = None) -> list[CarListing]:
    make, model = _normalize_make_model(prefs.make, prefs.model)
    model = _normalize_model_for_autodev(make, model)  # same MB normalization: GLE 450 → GLE
    data = _fetch_marketcheck_cached(
        make, model,
        prefs.price_min, prefs.price_max,
        prefs.radius_miles,
        prefs.condition or "Any",
        prefs.certified_only,
        prefs.trim or "",
        prefs.max_mileage or 0,
        prefs.exterior_color or "Any",
        zip_code or "",
        prefs.location,
    )

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

        # miles == 0 on a Used search means the dealer didn't report mileage, not a 0-mile
        # car — keep the listing; ranking agent treats it as unknown (half credit)

        display_source = "Marketcheck"
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
            stock_number=item.get("stock_no") or None,
        ))
    return listings


# ---------------------------------------------------------------------------
# Porsche Finder — official dealer inventory (finder.porsche.com)
# Porsche searches only. Fetched via ScraperAPI plain proxy (no JS render
# needed): the Next.js RSC stream embeds full schema.org Car objects even
# though the visible HTML shell says "0 vehicles" (confirmed 2026-06-10).
# ---------------------------------------------------------------------------

_PORSCHE_FINDER_BASE = "https://finder.porsche.com/us/en-US/search"

# finder.porsche.com model filter slugs (from the site's own footer links)
_PORSCHE_MODEL_SLUGS = [
    ("cayenne",  "cayenne"),
    ("macan",    "macan"),
    ("taycan",   "taycan"),
    ("panamera", "panamera"),
    ("911",      "911"),
    ("carrera",  "911"),
    ("gt3",      "911"),
    ("718",      "718"),
    ("boxster",  "718"),
    ("cayman",   "718"),
    ("gt4",      "718"),
]


def _porsche_model_slug(model: str) -> Optional[str]:
    m = (model or "").lower()
    for token, slug in _PORSCHE_MODEL_SLUGS:
        if token in m:
            return slug
    return None


def _parse_porsche_rsc(html: str) -> list[dict]:
    """Extract schema.org Car objects from the RSC stream (escaped JSON)."""
    cars = []
    raw = html.replace('\\"', '"')
    for m in re.finditer(r'\{"@type":\["Product","Car"\]', raw):
        s = m.start()
        depth = 0
        for i in range(s, min(s + 20000, len(raw))):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        cars.append(json.loads(raw[s:i + 1]))
                    except Exception:
                        pass
                    break
    return cars


def _fetch_porsche_finder_raw(model_slug, condition, zip_code, lat, lon, radius):
    """Fetch up to 2 pages (15 cars each) from finder.porsche.com via ScraperAPI."""
    base_params = {}
    if zip_code and lat and lon:
        base_params["position"] = f"{zip_code},{lat},{lon},{min(radius, 500)}"
    if model_slug:
        base_params["model"] = model_slug
    if condition in ("New", "Used"):
        base_params["condition"] = condition.lower()

    cars: list[dict] = []
    for page in (1, 2):
        params = dict(base_params)
        if page > 1:
            params["page"] = page
        target = f"{_PORSCHE_FINDER_BASE}?{urlencode(params)}"
        resp = None
        # ScraperAPI is intermittent — retry once, same pattern as CarGurus
        for _ in range(2):
            try:
                resp = requests.get(
                    "https://api.scraperapi.com/",
                    params={"api_key": SCRAPERAPI_KEY, "country_code": "us", "url": target},
                    timeout=20,
                )
            except Exception:
                continue
            if resp.status_code == 200 and len(resp.text) > 10000:
                break
        if not resp or resp.status_code != 200 or len(resp.text) < 10000:
            break
        page_cars = _parse_porsche_rsc(resp.text)
        cars.extend(page_cars)
        if len(page_cars) < 15:   # short page = no more results
            break
    return cars

# Same 2-hour Streamlit cache pattern as Marketcheck
try:
    import streamlit as _st_pf
    _fetch_porsche_finder_cached = _st_pf.cache_data(ttl=7200, show_spinner=False)(_fetch_porsche_finder_raw)
except Exception:
    _fetch_porsche_finder_cached = _fetch_porsche_finder_raw


def _search_porsche_finder(prefs: CarPreferences, zip_code: Optional[str] = None,
                           coords: Optional[Tuple[float, float]] = None) -> list[CarListing]:
    if not SCRAPERAPI_KEY:
        return []

    lat, lon = coords if coords else (None, None)
    cars = _fetch_porsche_finder_cached(
        _porsche_model_slug(prefs.model),
        prefs.condition or "Any",
        zip_code or "",
        lat, lon,
        prefs.radius_miles,
    )

    has_budget = prefs.price_max and prefs.price_max < 999000
    listings = []
    for c in cars:
        offer = c.get("offers") or {}
        seller = offer.get("seller") or {}
        addr = seller.get("address") or {}
        try:
            price = int(float(offer.get("price") or 0))
            year = int((c.get("modelDate") or "0")[:4])
            miles = int(float((c.get("mileageFromOdometer") or {}).get("value") or 0))
        except (ValueError, TypeError):
            continue
        if has_budget and price > 0 and not (prefs.price_min <= price <= prefs.price_max):
            continue
        effective_price = price if price > 0 else int((prefs.price_min + prefs.price_max) / 2)
        name = c.get("name") or "Porsche"
        title = f"{year} Porsche {name}".strip() if "porsche" not in name.lower() else f"{year} {name}".strip()
        listings.append(CarListing(
            title=title,
            price=effective_price,
            asking_price=price,
            mileage=miles,
            year=year,
            exterior_color=c.get("color"),
            interior_color=c.get("vehicleInteriorColor"),
            dealer_name=seller.get("name"),
            location=", ".join(filter(None, [addr.get("addressLocality"), addr.get("postalCode")])) or prefs.location,
            listing_url=offer.get("url"),
            source="Porsche Finder",
        ))
    return listings


# ---------------------------------------------------------------------------
# MBUSA — official Mercedes-Benz dealer inventory (nafta-service.mbusa.com)
# Public unauthenticated JSON API; new + used endpoints. Mercedes searches only.
# Params confirmed live 2026-06-11: zip + distance + class filter correctly;
# pagination via start= (12 records/page).
# ---------------------------------------------------------------------------

_MBUSA_API = "https://nafta-service.mbusa.com/api/inv/v1/en_us/{cond}/vehicles/search"
_MBUSA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Origin": "https://www.mbusa.com",
    "Referer": "https://www.mbusa.com/",
}
_MB_CLASS_CODES = {"A", "B", "C", "E", "S", "G", "CLA", "CLE", "CLS", "GLA", "GLB",
                   "GLC", "GLE", "GLS", "SL", "SLC", "SLK", "EQB", "EQE", "EQS", "GT"}


def _mb_class_from_model(model: str) -> Optional[str]:
    m = re.match(r"[A-Za-z]+", (model or "").replace(" ", ""))
    if m and m.group(0).upper() in _MB_CLASS_CODES:
        return m.group(0).upper()
    return None


def _fetch_mbusa_raw(cls, condition, zip_code, radius):
    """Fetch up to 4 pages per endpoint (12 records each) from MBUSA."""
    endpoints = {"New": ["new"], "Used": ["used"]}.get(condition, ["new", "used"])
    records = []
    for cond in endpoints:
        for page in range(2 if len(endpoints) == 2 else 4):
            params = {"zip": zip_code, "distance": min(radius, 200), "start": page * 12}
            if cls:
                params["class"] = cls
            resp = requests.get(_MBUSA_API.format(cond=cond), params=params,
                                headers=_MBUSA_HEADERS, timeout=15)
            if resp.status_code != 200:
                break
            pv = (resp.json().get("result") or {}).get("pagedVehicles") or {}
            recs = pv.get("records") or []
            for r in recs:
                r["_mb_used"] = (cond == "used")
            records.extend(recs)
            if len(recs) < 12:
                break
    return records

try:
    import streamlit as _st_mb
    _fetch_mbusa_cached = _st_mb.cache_data(ttl=7200, show_spinner=False)(_fetch_mbusa_raw)
except Exception:
    _fetch_mbusa_cached = _fetch_mbusa_raw


def _search_mbusa(prefs: CarPreferences, zip_code: Optional[str] = None) -> list[CarListing]:
    if not zip_code:
        return []
    records = _fetch_mbusa_cached(
        _mb_class_from_model(prefs.model),
        prefs.condition or "Any",
        zip_code,
        prefs.radius_miles,
    )

    has_budget = prefs.price_max and prefs.price_max < 999000
    listings = []
    for r in records:
        try:
            year = int(r.get("year") or 0)
            price = int(float(r.get("inventoryPrice") or 0)) or int(float(r.get("msrp") or 0))
        except (ValueError, TypeError):
            continue
        if has_budget and price > 0 and not (prefs.price_min <= price <= prefs.price_max):
            continue
        effective_price = price if price > 0 else int((prefs.price_min + prefs.price_max) / 2)
        dealer = r.get("dealer") or {}
        addr = (dealer.get("address") or [{}])[0]
        model_name = str(r.get("modelName") or "").strip()
        title = f"{year} Mercedes-Benz {model_name}".strip()
        listings.append(CarListing(
            title=title,
            price=effective_price,
            asking_price=price,
            mileage=0,   # API omits mileage; ranking treats 0 as unknown on Used
            year=year,
            msrp=int(float(r.get("msrp") or 0)) or None,
            exterior_color=(r.get("paint") or {}).get("name"),
            interior_color=(r.get("upholstery") or {}).get("name"),
            dealer_name=dealer.get("name"),
            location=", ".join(filter(None, [addr.get("city"), addr.get("state")])) or prefs.location,
            listing_url=None,
            source="MBUSA",
            vin=r.get("vin") or None,
        ))
    return listings


# ---------------------------------------------------------------------------
# HyundaiUSA — official dealer inventory (papp-bsi-api.hyundaiusa.com)
# Public unauthenticated JSON API; new inventory only. Hyundai searches only.
# Model filter takes facet codes (e.g. TUCSON = 8001) resolved from the
# response's own filters block; results are distance-sorted, totals are
# national, so radius is enforced client-side via distanceFromOrigin.
# Confirmed live 2026-06-11; pageSize caps at 30.
# ---------------------------------------------------------------------------

_HYUNDAI_API = "https://papp-bsi-api.hyundaiusa.com/inventory/item/v2/search"
_HYUNDAI_HEADERS = {
    "User-Agent": _MBUSA_HEADERS["User-Agent"],
    "Origin": "https://www.hyundaiusa.com",
    "Referer": "https://www.hyundaiusa.com/",
    "Content-Type": "application/json",
}


def _fetch_hyundai_raw(model, zip_code, radius):
    """Resolve model → facet code(s), then fetch up to 2 pages (30 each)."""
    def post(body):
        resp = requests.post(_HYUNDAI_API, json=body, headers=_HYUNDAI_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()

    base = {"zipCode": zip_code, "distance": min(radius, 250)}
    first = post({**base, "page": 1, "pageSize": 1})

    # Model facet: exact displayName match first, then prefix match so
    # "Tucson" also covers TUCSON Hybrid / Plug-in Hybrid
    codes = []
    m_up = (model or "").upper().strip()
    if m_up and m_up != "ANY":
        for f in (first.get("filters") or {}).get("filters") or []:
            if f.get("filterTitle") == "Model":
                opts = f.get("options") or []
                exact = [o for o in opts if o.get("displayName", "").upper() == m_up]
                prefix = [o for o in opts if o.get("displayName", "").upper().startswith(m_up)]
                codes = [o["code"] for o in (exact or prefix)]
                break

    body = {**base, "pageSize": 30}
    if codes:
        body["modelName"] = [{"code": c} for c in codes]
    items = []
    for page in (1, 2):
        d = post({**body, "page": page})
        page_items = (d.get("data") or {}).get("items") or []
        items.extend(page_items)
        if len(page_items) < 30:
            break
    return items

try:
    import streamlit as _st_hy
    _fetch_hyundai_cached = _st_hy.cache_data(ttl=7200, show_spinner=False)(_fetch_hyundai_raw)
except Exception:
    _fetch_hyundai_cached = _fetch_hyundai_raw


def _search_hyundai(prefs: CarPreferences, zip_code: Optional[str] = None) -> list[CarListing]:
    if not zip_code:
        return []
    if prefs.condition == "Used":
        return []   # API serves new dealer inventory only
    items = _fetch_hyundai_cached(prefs.model or "", zip_code, prefs.radius_miles)

    has_budget = prefs.price_max and prefs.price_max < 999000
    listings = []
    for it in items:
        try:
            year = int(it.get("modelYear") or 0)
            msrp = int(float(it.get("msrp") or 0))
            price = int(float(it.get("dealerInternetPrice") or 0)) or msrp
            dist = float(it.get("distanceFromOrigin") or 0)
        except (ValueError, TypeError):
            continue
        # Totals are national — enforce the radius ourselves
        if dist and dist > prefs.radius_miles:
            continue
        if has_budget and price > 0 and not (prefs.price_min <= price <= prefs.price_max):
            continue
        effective_price = price if price > 0 else int((prefs.price_min + prefs.price_max) / 2)
        model_disp = str(it.get("modelDisplayName") or "").title()
        trim_disp = str(it.get("trimDisplayName") or "")
        title = " ".join(filter(None, [str(year), "Hyundai", model_disp, trim_disp]))
        listings.append(CarListing(
            title=title,
            price=effective_price,
            asking_price=price,
            mileage=0,   # new inventory
            year=year,
            msrp=msrp or None,
            exterior_color=str(it.get("exteriorColor") or "").title() or None,
            interior_color=str(it.get("interiorColor") or "").title() or None,
            dealer_name=it.get("dealerName"),
            location=prefs.location,
            listing_url=it.get("dealerVDPURL") or None,
            source="HyundaiUSA",
            vin=it.get("vin") or None,
            distance_miles=round(dist, 1) if dist else None,
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
# auto.dev — structured listings API (1-4M inventory, $0.002/call)
# ---------------------------------------------------------------------------

# auto.dev stores Mercedes-Benz SUVs as 3-letter class only (GLS, GLE, GLC…)
# with the number in the trim field. Sedans use E-Class/C-Class/S-Class.
# This differs from Marketcheck which uses full names like "GLS 450".
_AUTODEV_MB_SUV_PREFIXES = {"GLS", "GLE", "GLC", "GLB", "GLA", "EQS", "EQE", "EQB", "EQC"}

def _normalize_model_for_autodev(make: str, model: str) -> str:
    if "mercedes" in make.lower():
        base = model.strip().split()[0].upper()
        if base in _AUTODEV_MB_SUV_PREFIXES:
            return base
    return model


def _search_autodev(
    prefs: CarPreferences,
    zip_code: Optional[str] = None,
    search_coords: Optional[Tuple[float, float]] = None,
) -> list[CarListing]:
    if not AUTODEV_API_KEY:
        return []

    make, model = _normalize_make_model(prefs.make, prefs.model)
    model = _normalize_model_for_autodev(make, model)
    headers = {"Authorization": f"Bearer {AUTODEV_API_KEY}"}

    base_params: dict = {
        "vehicle.make": make,
        "vehicle.model": model,
        "distance": min(prefs.radius_miles, 200),
        "limit": 100,
    }
    # Only pass price range if user explicitly set one — listings with "accepting_offers"
    # price get excluded by auto.dev's price filter even when no budget was specified
    if prefs.price_max and prefs.price_max < 999000:
        base_params["retailListing.price"] = f"{prefs.price_min}-{prefs.price_max}"
    if zip_code:
        base_params["zip"] = zip_code
    # trim not passed — auto.dev returns 400 on vehicle.trim; ranking agent scores by title

    # Smart pagination: always fetch 5 pages (500 listings), then keep going if
    # fewer than 5 listings match the requested trim in their title.
    # Caps at 10 pages (1000 listings) to limit cost.
    _trim_kw   = (prefs.trim or "").lower().strip()
    _trim_has  = bool(_trim_kw and _trim_kw not in ("any", ""))
    _TRIM_MIN  = 5    # keep pulling pages until we have at least this many trim matches
    _MAX_PAGES = 10   # hard cap to control cost

    listings = []
    _trim_match_count = 0
    for page in range(1, _MAX_PAGES + 1):
        # After page 5, only continue if trim specified and we have fewer than 5 matches
        if page > 5 and (not _trim_has or _trim_match_count >= _TRIM_MIN):
            break
        params = {**base_params, "page": page}
        for _attempt in range(2):   # retry once on timeout
            try:
                resp = requests.get(f"{AUTODEV_BASE}/listings", params=params, headers=headers, timeout=20)
                break
            except requests.exceptions.Timeout:
                if _attempt == 0:
                    import time; time.sleep(3)
                else:
                    raise
        resp.raise_for_status()
        data = resp.json()

        raw_items = data.get("data") or []
        if not raw_items:
            break

        for item in raw_items:
            try:
                vehicle = item.get("vehicle") or {}
                retail  = item.get("retailListing") or {}

                year   = int(vehicle.get("year") or 0)
                # str() coercion required: auto.dev returns numeric model names
                # (Porsche 911, 718) as JSON numbers, which crash " ".join()
                vmake  = str(vehicle.get("make") or make)
                vmodel = str(vehicle.get("model") or model)
                trim   = str(vehicle.get("trim") or "")

                price = int(float(retail.get("price") or 0))
                if price > 0 and not (prefs.price_min <= price <= prefs.price_max):
                    continue
                # price 0 = "accepting offers" / unpublished — keep the listing rather than
                # drop it (same effective-price pattern as Marketcheck; UI shows asking_price 0 as N/A)
                effective_price = price if price > 0 else int((prefs.price_min + prefs.price_max) / 2)

                mileage = int(float(retail.get("miles") or 0))
                if prefs.max_mileage and mileage > 0 and mileage > prefs.max_mileage:
                    continue

                # Client-side condition filter using retailListing.used boolean
                if prefs.condition == "New" and retail.get("used") is True:
                    continue
                if prefs.condition == "Used" and retail.get("used") is False:
                    continue

                ext_color = vehicle.get("exteriorColor") or ""
                int_color = vehicle.get("interiorColor") or ""

                dealer_name  = retail.get("dealer") or ""
                dealer_city  = retail.get("city") or ""
                dealer_state = retail.get("state") or ""
                location     = ", ".join(filter(None, [dealer_city, dealer_state])) or prefs.location

                # Client-side distance filter using coordinates auto.dev provides
                # location field is [longitude, latitude]
                coords = item.get("location")
                dist_miles = None
                if search_coords and coords and isinstance(coords, list) and len(coords) == 2:
                    dist_miles = round(_haversine_miles(search_coords[0], search_coords[1], coords[1], coords[0]), 1)
                    if dist_miles > prefs.radius_miles:
                        continue

                vin = item.get("vin") or vehicle.get("vin") or ""
                stock_no = retail.get("stockNumber") or retail.get("stock_no") or item.get("stockNumber") or ""
                vdp_url = ""  # resolved live via VIN endpoint on user request

                title_parts = [str(year), vmake, vmodel]
                if trim:
                    title_parts.append(trim)
                title = " ".join(filter(None, title_parts))

                listing = CarListing(
                    title=title,
                    price=effective_price,
                    asking_price=price,
                    mileage=mileage,
                    year=year,
                    exterior_color=ext_color or None,
                    interior_color=int_color or None,
                    dealer_name=dealer_name or None,
                    location=location,
                    listing_url=vdp_url or None,
                    source="auto.dev",
                    vin=vin or None,
                    stock_number=stock_no or None,
                    distance_miles=dist_miles,
                )
                listings.append(listing)
                if _trim_has and _trim_kw in title.lower():
                    _trim_match_count += 1
            except Exception:
                continue

        # Stop if no next page
        links = data.get("links", {})
        if not links.get("next") or links["next"] == links.get("self"):
            break

    return listings


# ---------------------------------------------------------------------------
# auto.dev live VIN lookup — called on demand from the UI
# ---------------------------------------------------------------------------

def fetch_autodev_live(vin: str) -> dict:
    """Fetch real-time listing data for a VIN from auto.dev.
    Returns a dict with phone, live price, price history, features, listing URL.
    """
    if not AUTODEV_API_KEY or not vin:
        return {"error": "No API key or VIN"}
    headers = {"Authorization": f"Bearer {AUTODEV_API_KEY}"}
    try:
        resp = requests.get(
            f"{AUTODEV_BASE}/listings/{vin}",
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 404:
            return {"error": "Listing no longer available — car may be sold"}
        resp.raise_for_status()
        d = resp.json()

        # auto.dev vdpUrl is a broken internal path — build a dealer Google search instead
        dealer = d.get("dealerName") or ""
        city   = d.get("city") or ""
        state  = d.get("state") or ""
        listing_url = (
            f"https://www.google.com/search?q={requests.utils.quote(dealer + ' ' + city + ' ' + state + ' inventory')}"
            if dealer else ""
        )
        # Try several field names auto.dev uses for dealer website
        dealer_website = (
            d.get("dealerUrl") or d.get("dealerWebsite") or d.get("website") or
            d.get("websiteUrl") or (d.get("dealer") or {}).get("url") or
            (d.get("dealer") or {}).get("website") or ""
        )
        # Fallback: Google search for dealer's homepage
        if not dealer_website and dealer:
            dealer_website = f"https://www.google.com/search?q={requests.utils.quote(dealer + ' ' + city + ' ' + state + ' official site')}"

        price_history = []
        for ch in (d.get("realTimePriceChanges") or []):
            price_history.append({
                "date": ch.get("dateFormatted", ""),
                "price": ch.get("price", 0),
                "delta": ch.get("delta"),
            })

        if d.get("clickOff"):
            return {"error": "This dealer has opted out of direct contact — visit the dealership in person or call their main line."}

        phone_raw = d.get("phone") or ""
        phone_tel = d.get("phoneTel") or d.get("phoneTelRegional") or ""
        phone = phone_raw or (f"({str(phone_tel)[:3]}) {str(phone_tel)[3:6]}-{str(phone_tel)[6:]}" if len(str(phone_tel)) == 10 else str(phone_tel))

        price = d.get("price") or d.get("basePrice") or d.get("priceWithListimate") or 0
        price_fmt = d.get("priceFormatted") or (f"${price:,}" if price else "Not published")

        return {
            "phone": phone,
            "dealer_name": d.get("dealerName") or "",
            "price": price,
            "price_formatted": price_fmt,
            "mileage": d.get("mileage") or 0,
            "total_price_change": d.get("totalPriceChange") or 0,
            "recent_price_drop": d.get("recentPriceDrop", False),
            "original_price": d.get("originalPrice") or 0,
            "listing_url": listing_url,
            "dealer_website": dealer_website,
            "features": (d.get("features") or [])[:15],
            "price_history": price_history,
            "photo_url": d.get("thumbnailUrlLarge") or d.get("thumbnailUrl") or "",
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Photo crop — remove solid-color dealer banners from listing photos
# ---------------------------------------------------------------------------

def crop_dealer_overlay(img_bytes: bytes) -> bytes:
    """Remove dealer overlay banners from car listing photos.

    Two-pass strategy:
    1. Always crop the bottom 13% (dealer contact banners live here in virtually
       every listing photo regardless of color or content).
    2. Then scan outward from each edge for additional dark or solid-color rows
       (brightness < 110 OR per-channel stddev < 30) and remove those too,
       capped at 25% total from either edge.
    """
    import io
    from PIL import Image

    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    gray = img.convert("L")

    DARK_THRESH   = 110   # rows with mean brightness below this = dark overlay
    SOLID_THRESH  = 30    # rows with stddev below this = solid-color overlay
    MIN_BOT_FRAC  = 0.13  # always remove at least the bottom 13%
    MAX_FRAC      = 0.25  # never remove more than 25% from either edge

    def _row_stats(y: int):
        px = list(gray.crop((0, y, w, y + 1)).getdata())
        mean = sum(px) / len(px)
        std  = (sum((p - mean) ** 2 for p in px) / len(px)) ** 0.5
        return mean, std

    # ── Bottom: start from guaranteed minimum, scan further if overlay continues ──
    bottom = h - int(h * MIN_BOT_FRAC)
    limit  = h - int(h * MAX_FRAC)
    for y in range(bottom - 1, limit - 1, -1):
        mean, std = _row_stats(y)
        if mean < DARK_THRESH or std < SOLID_THRESH:
            bottom = y
        else:
            break

    # ── Top: scan down from edge for dark/solid rows ──────────────────────────
    top   = 0
    limit = int(h * MAX_FRAC)
    for y in range(0, limit):
        mean, std = _row_stats(y)
        if mean < DARK_THRESH or std < SOLID_THRESH:
            top = y + 1
        else:
            break

    img = img.crop((0, top, w, bottom))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# VIN details — rich decode for client presentation (photos, specs, links)
# ---------------------------------------------------------------------------

def fetch_vin_details(vin: str) -> dict:
    """Full VIN decode for client-facing display: specs + photo + image search links."""
    from urllib.parse import quote as _q
    vin = vin.strip().upper()
    out = {
        "vin": vin, "year": 0, "make": "", "model": "", "trim": "",
        "body_type": "", "engine": "", "fuel_type": "", "doors": "",
        "photo_url": "", "features": [],
        "price": 0, "mileage": 0, "dealer_name": "",
        "listing_url": f"https://www.autotrader.com/cars-for-sale/all-cars?vin={vin}&searchRadius=500",
        "google_images_url": "", "bing_images_url": "",
    }

    # NHTSA decode for full specs
    try:
        resp = requests.get(
            f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json",
            timeout=10,
        )
        resp.raise_for_status()
        _na = {"", "0", "Not Applicable", "null", "None"}
        flds = {r["Variable"]: (r["Value"] or "").strip() for r in resp.json().get("Results", [])}
        yr = flds.get("Model Year", "")
        out["year"]      = int(yr) if yr.isdigit() else 0
        out["make"]      = flds.get("Make", "")  if flds.get("Make", "")  not in _na else ""
        out["model"]     = flds.get("Model", "") if flds.get("Model", "") not in _na else ""
        out["trim"]      = flds.get("Trim", "")  if flds.get("Trim", "")  not in _na else ""
        out["body_type"] = flds.get("Body Class", "") if flds.get("Body Class", "") not in _na else ""
        displ = flds.get("Displacement (L)", "")
        cyl   = flds.get("Engine Number of Cylinders", "")
        if displ and displ not in _na:
            out["engine"] = f"{displ}L" + (f" {cyl}-cyl" if cyl and cyl not in _na else "")
        out["fuel_type"] = flds.get("Fuel Type - Primary", "") if flds.get("Fuel Type - Primary", "") not in _na else ""
        out["doors"]     = flds.get("Doors", "") if flds.get("Doors", "") not in _na else ""
    except Exception:
        pass

    # auto.dev enrichment for live price, mileage, photo
    if AUTODEV_API_KEY:
        live = fetch_autodev_live(vin)
        if "error" not in live:
            out["photo_url"]   = live.get("photo_url", "")
            out["features"]    = live.get("features", [])
            out["price"]       = live.get("price", 0)
            out["mileage"]     = live.get("mileage", 0)
            out["dealer_name"] = live.get("dealer_name", "")

    # Image search fallback URLs (always generated)
    q_parts = [str(out["year"]) if out["year"] else "", out["make"], out["model"], out["trim"]]
    q = _q(" ".join(p for p in q_parts if p) + " car")
    out["google_images_url"] = f"https://www.google.com/search?q={q}&tbm=isch"
    out["bing_images_url"]   = f"https://www.bing.com/images/search?q={q}"

    # Pre-fetch image bytes for Streamlit download button
    out["photo_bytes"] = None
    if out["photo_url"]:
        try:
            img_r = requests.get(out["photo_url"], timeout=8)
            if img_r.status_code == 200:
                out["photo_bytes"] = img_r.content
        except Exception:
            pass

    return out


# ---------------------------------------------------------------------------
# VIN lookup — NHTSA decode + auto.dev live data
# ---------------------------------------------------------------------------

def lookup_vin_listing(vin: str, prefs: "CarPreferences") -> tuple:
    """Decode a VIN via NHTSA (free, no key) and enrich with auto.dev live data.

    Returns (CarListing, error_message). On success error_message is empty.
    Used when the user pastes a VIN they found on AutoTrader or another site.
    """
    vin = vin.strip().upper()
    if len(vin) != 17:
        return None, "VIN must be exactly 17 characters."

    # Step 1 — NHTSA free VIN decode (year / make / model / trim)
    try:
        resp = requests.get(
            f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json",
            timeout=10,
        )
        resp.raise_for_status()
        fields = {r["Variable"]: (r["Value"] or "").strip()
                  for r in resp.json().get("Results", [])}

        _na = {"", "0", "Not Applicable", "null", "None"}
        year_raw = fields.get("Model Year", "")
        make     = fields.get("Make", "")  if fields.get("Make",  "") not in _na else ""
        model    = fields.get("Model", "") if fields.get("Model", "") not in _na else ""
        trim     = fields.get("Trim",  "") if fields.get("Trim",  "") not in _na else ""
        year     = int(year_raw) if year_raw.isdigit() else 0

        if not make or not model:
            return None, "Could not decode this VIN — NHTSA returned no make/model. Check the VIN and try again."
    except Exception as e:
        return None, f"NHTSA decode failed: {e}"

    # Step 2 — auto.dev live lookup for price / mileage / dealer
    price       = 0
    mileage     = 0
    dealer_name = None
    location    = None
    listing_url = None

    if AUTODEV_API_KEY:
        live = fetch_autodev_live(vin)
        if "error" not in live:
            price       = live.get("price") or 0
            mileage     = live.get("mileage") or 0
            dealer_name = live.get("dealer_name") or None

    # Build title
    title_parts = [str(year) if year else "", make, model, trim]
    title = " ".join(p for p in title_parts if p)

    # Direct VIN search links (set as listing_url → "View Listing →" button)
    at_url = f"https://www.autotrader.com/cars-for-sale/all-cars?vin={vin}&searchRadius=500"

    # Use budget midpoint as price placeholder when live price unavailable
    placeholder_price = price if price > 0 else int((prefs.price_min + prefs.price_max) / 2)

    from agents.models import CarListing
    listing = CarListing(
        title=title,
        price=placeholder_price,
        asking_price=price if price > 0 else None,
        mileage=mileage,
        year=year,
        dealer_name=dealer_name,
        location=location,
        listing_url=at_url,
        source="VIN Lookup",
        vin=vin,
    )
    return listing, ""


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
    # Single Nominatim call → zip + coordinates for the whole pipeline.
    # Passing coordinates into _search_autodev avoids a second Nominatim hit
    # and ensures the client-side distance filter always has data to work with.
    _zip, _lat, _lon = _resolve_location(prefs.location)
    _coords = (_lat, _lon) if _lat and _lon else None

    all_candidates = []

    if AUTODEV_API_KEY:
        all_candidates.append(("auto.dev", lambda p=prefs, z=_zip, c=_coords: _search_autodev(p, z, c)))
    if MARKETCHECK_API_KEY:
        all_candidates.append(("Marketcheck", lambda p=prefs, z=_zip: _search_marketcheck(p, z)))
    if EBAY_APP_ID:
        all_candidates.append(("eBay Motors", lambda p=prefs, z=_zip: _search_ebay(p, z)))
    all_candidates.append(("CarGurus",    lambda p=prefs, z=_zip: _search_cargurus(p, z)))
    all_candidates.append(("Craigslist",  lambda p=prefs: _search_craigslist(p)))
    # Official-manufacturer inventory sources — gated to the matching make
    _mk = (prefs.make or "").strip().lower()
    if SCRAPERAPI_KEY and _mk == "porsche":
        all_candidates.append(("Porsche Finder", lambda p=prefs, z=_zip, c=_coords: _search_porsche_finder(p, z, c)))
    if _mk == "mercedes-benz":
        all_candidates.append(("MBUSA", lambda p=prefs, z=_zip: _search_mbusa(p, z)))
    if _mk == "hyundai":
        all_candidates.append(("HyundaiUSA", lambda p=prefs, z=_zip: _search_hyundai(p, z)))

    # Filter to only selected sources when the caller specifies a subset
    sources = [(n, fn) for n, fn in all_candidates if n in selected_sources] if selected_sources else all_candidates

    all_listings: list[CarListing] = []
    source_errors: dict = {}

    executor = ThreadPoolExecutor(max_workers=6)
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
        if not MARKETCHECK_API_KEY and not EBAY_APP_ID and not AUTODEV_API_KEY:
            return [], (
                "No API key configured. Add AUTODEV_API_KEY or MARKETCHECK_API_KEY to .env."
            ), source_errors
        return [], (
            "No listings found. Try widening your price range, increasing the radius, or relaxing filters."
        ), source_errors

    # Deduplicate by (normalised title prefix, price)
    seen: set = set()
    unique: list[CarListing] = []
    for listing in all_listings:
        # Prefer listing URL as dedup key — Marketcheck VDP URLs contain the VIN so they're
        # globally unique per vehicle. Fall back to (title, price, dealer) for scraped sources
        # that may not have a URL.
        key = listing.listing_url or (
            listing.title.lower()[:40],
            listing.price,
            (listing.dealer_name or listing.location or "").lower()[:30],
        )
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

    # Client-side "New" condition filter — applied to ALL sources.
    # Craigslist excluded entirely: private-seller platform with no new dealer inventory.
    # All other sources filtered to mileage ≤ 500: Marketcheck and auto.dev can return
    # demo/loaner cars tagged "new" in their systems despite having 10,000–25,000+ miles.
    # 500 mi threshold allows legitimate delivery mileage (port → dealer transport).
    if prefs.condition == "New":
        unique = [l for l in unique if l.source != "Craigslist"]
        unique = [l for l in unique if l.mileage <= 500]

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
        # Auto-retry with wider radius before giving up (100mi → 200mi)
        for _wider in [100, 200]:
            if _wider <= prefs.radius_miles:
                continue
            _wider_prefs = prefs.model_copy(update={"radius_miles": _wider})
            _w_zip, _w_lat, _w_lon = _resolve_location(_wider_prefs.location)
            _w_coords = (_w_lat, _w_lon) if _w_lat and _w_lon else None
            _w_listings: list = []
            if AUTODEV_API_KEY:
                try:
                    _w_listings += _search_autodev(_wider_prefs, _w_zip, _w_coords)
                except Exception:
                    pass
            if MARKETCHECK_API_KEY:
                try:
                    _w_listings += _search_marketcheck(_wider_prefs, _w_zip)
                except Exception:
                    pass
            _w_unique = list({l.vin or l.listing_url: l for l in _w_listings if l.vin or l.listing_url}.values())
            if prefs.condition == "New":
                _w_unique = [l for l in _w_unique if l.source != "Craigslist"]
                _w_unique = [l for l in _w_unique if l.mileage <= 500]
            if _w_unique:
                return _w_unique, (
                    f"No results within {prefs.radius_miles} mi — widened to {_wider} mi and found {len(_w_unique)} listing(s)."
                ), source_errors

        return [], (
            "No listings matched your filters. "
            "Try widening your price range, increasing the radius, or changing the condition."
        ), source_errors

    return unique, None, source_errors
