import re
import json
import requests
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from agents.models import CarPreferences, CarListing
from config import LLM_MODEL, MARKETCHECK_API_KEY, AUTODEV_API_KEY

MARKETCHECK_BASE = "https://api.marketcheck.com/v2"
AUTODEV_BASE = "https://auto.dev/api"

_NORMALIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Return ONLY a JSON object with keys 'make' and 'model', corrected to their exact official names. No extra text."),
    ("human", "Correct this car make and model: make='{make}', model='{model}'"),
])

def _normalize_make_model(make: str, model: str) -> tuple:
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
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


def _search_marketcheck(prefs: CarPreferences) -> list[CarListing]:
    make, model = _normalize_make_model(prefs.make, prefs.model)
    params = {
        "api_key": MARKETCHECK_API_KEY,
        "make": make,
        "model": model,
        "price_min": prefs.price_min,
        "price_max": prefs.price_max,
        "radius": min(prefs.radius_miles, 100),  # free tier hard cap
        "rows": 10,
        "sort_by": "price",
        "sort_order": "asc",
    }
    if prefs.trim:
        params["trim"] = prefs.trim
    if prefs.max_mileage:
        params["mileage_max"] = prefs.max_mileage
    if prefs.exterior_color and prefs.exterior_color.lower() != "any":
        params["exterior_color"] = prefs.exterior_color.lower()
    if prefs.certified_only:
        params["inventory_type"] = "certified"
    elif prefs.condition and prefs.condition != "Any":
        params["inventory_type"] = prefs.condition.lower()

    # Fetch more rows so client-side filtering still returns enough results
    params["rows"] = 30

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

        # Ranking proxy when dealer hasn't published price — never stored as display price
        effective_price = price if price > 0 else (msrp_raw or int((prefs.price_min + prefs.price_max) / 2))

        # Client-side condition enforcement
        if prefs.certified_only and (miles == 0 or year >= current_year):
            continue  # CPO must be a used car with actual mileage
        if prefs.condition == "Used" and (miles == 0 or year >= current_year):
            continue
        if prefs.condition == "New" and miles > 0:
            continue

        raw_source = item.get("source", "")
        display_source = raw_source if raw_source else "Marketcheck"
        listings.append(CarListing(
            title=item.get("heading") or f"{year} {prefs.make} {prefs.model}",
            price=effective_price,       # used for ranking only
            asking_price=price,          # raw dealer price, 0 = not published
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


def _search_autodev(prefs: CarPreferences) -> list[CarListing]:
    """
    AutoDev is a VIN/specs API, not an inventory search API.
    It does not support searching by make/model/price/location.
    Included here for future VIN-based enrichment only.
    """
    return []


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


def _search_gpt_fallback(prefs: CarPreferences) -> list[CarListing]:
    from agents.rag_agent import is_rag_available, query_car_specs, query_market_data

    rag_context = ""
    if is_rag_available():
        specs = query_car_specs(prefs.make, prefs.model, n_results=2)
        market = query_market_data(prefs.make, prefs.model, prefs.location, n_results=2)
        parts = []
        if specs:
            parts.append("Car spec context:\n" + "\n".join(specs))
        if market:
            parts.append("Market data context:\n" + "\n".join(market))
        rag_context = "\n\n".join(parts)

    if rag_context:
        human_msg = (
            "Find cars matching these preferences:\n"
            "Make: {make}, Model: {model}\n"
            "Price range: ${price_min:,} - ${price_max:,}\n"
            "Max mileage: {max_mileage} miles\n"
            "Exterior color: {exterior_color}\n"
            "Interior color: {interior_color}\n"
            "Location: {location} (within {radius_miles} miles)\n\n"
            f"Use this factual context to generate realistic listings:\n{rag_context}\n\n"
            "Return ONLY a valid JSON array, no markdown, no code fences."
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are a car marketplace search agent. Return a JSON array of exactly 5 realistic "
                "car listings matching the criteria. Each listing must have: title (string), price (int), "
                "mileage (int), year (int), exterior_color, interior_color, dealer_name, location, "
                "listing_url (use a real Cars.com or CarGurus search URL format)."
            )),
            ("human", human_msg),
        ])
    else:
        prompt = _SEARCH_PROMPT

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.3)
    chain = prompt | llm | StrOutputParser()
    raw = chain.invoke({
        "make": prefs.make,
        "model": prefs.model,
        "price_min": prefs.price_min,
        "price_max": prefs.price_max,
        "max_mileage": prefs.max_mileage or "Any",
        "exterior_color": prefs.exterior_color or "Any",
        "interior_color": prefs.interior_color or "Any",
        "location": prefs.location,
        "radius_miles": prefs.radius_miles,
    })
    listings_data = json.loads(raw)
    return [CarListing(**{**item, "source": "AI Simulated"}) for item in listings_data]


def run_search_agent(prefs: CarPreferences) -> tuple:
    if MARKETCHECK_API_KEY:
        try:
            listings = _search_marketcheck(prefs)
            if listings:
                return listings, None
            return [], "No listings found matching your criteria. Try widening your price range, increasing the search radius, or relaxing other filters."
        except Exception as e:
            return [], f"Marketcheck error: {e}"

    return [], "No API key configured — cannot search live inventory."
