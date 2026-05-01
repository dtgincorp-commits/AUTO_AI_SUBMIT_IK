#!/usr/bin/env python3
"""
Build the AUTO_AI RAG knowledge base — no OpenAI API required.

Data sources:
  car_specs    — fueleconomy.gov (real trims/MPG) + structured templates
  dealer_data  — Marketcheck /dealers API (real), falls back to templates
  market_data  — Realistic pricing templates per model/region
  market_trends— Realistic trend templates per segment/region

Embeddings: ChromaDB DefaultEmbeddingFunction (local, no API key needed).

Run once to build, re-run to rebuild:
    .venv/bin/python knowledge_base/build_index.py
"""

import sys
import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from config import MARKETCHECK_API_KEY

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
FUELECONOMY_BASE = "https://www.fueleconomy.gov/ws/rest"
MARKETCHECK_BASE = "https://api.marketcheck.com/v2"

POPULAR_MODELS = [
    ("BMW", "X5"), ("BMW", "3 Series"), ("BMW", "X3"), ("BMW", "5 Series"),
    ("Toyota", "Camry"), ("Toyota", "RAV4"), ("Toyota", "Highlander"), ("Toyota", "Corolla"),
    ("Honda", "Accord"), ("Honda", "CR-V"), ("Honda", "Pilot"), ("Honda", "Civic"),
    ("Ford", "F-150"), ("Ford", "Explorer"), ("Ford", "Escape"), ("Ford", "Mustang"),
    ("Chevrolet", "Silverado"), ("Chevrolet", "Equinox"), ("Chevrolet", "Tahoe"),
    ("Tesla", "Model 3"), ("Tesla", "Model Y"),
    ("Mercedes-Benz", "GLE"), ("Mercedes-Benz", "C-Class"),
    ("Audi", "Q5"), ("Audi", "A4"),
    ("Hyundai", "Tucson"), ("Hyundai", "Santa Fe"),
    ("Kia", "Telluride"), ("Kia", "Sportage"),
    ("Subaru", "Outback"), ("Subaru", "Forester"),
    ("Nissan", "Altima"), ("Nissan", "Rogue"),
    ("Jeep", "Grand Cherokee"), ("Mazda", "CX-5"),
]

FALLBACK_TRIMS = {
    ("BMW", "X5"): ["xDrive40i", "xDrive45e", "M50i"],
    ("BMW", "3 Series"): ["330i", "330i xDrive", "M340i"],
    ("BMW", "X3"): ["sDrive30i", "xDrive30i", "M40i"],
    ("BMW", "5 Series"): ["530i", "540i", "M550i"],
    ("Toyota", "Camry"): ["LE", "SE", "XLE", "XSE", "TRD"],
    ("Toyota", "RAV4"): ["LE", "XLE", "Adventure", "TRD Off-Road", "Limited"],
    ("Toyota", "Highlander"): ["L", "LE", "XLE", "Limited", "Platinum"],
    ("Toyota", "Corolla"): ["L", "LE", "SE", "XLE", "XSE"],
    ("Honda", "Accord"): ["LX", "Sport", "EX", "EX-L", "Touring"],
    ("Honda", "CR-V"): ["LX", "EX", "EX-L", "Touring", "Sport"],
    ("Honda", "Pilot"): ["LX", "Sport", "EX-L", "TrailSport", "Elite"],
    ("Honda", "Civic"): ["LX", "Sport", "EX", "Touring", "Si"],
    ("Ford", "F-150"): ["XL", "XLT", "Lariat", "King Ranch", "Platinum", "Raptor"],
    ("Ford", "Explorer"): ["Base", "XLT", "Limited", "ST", "Platinum"],
    ("Ford", "Escape"): ["S", "SE", "SEL", "Titanium", "ST-Line"],
    ("Ford", "Mustang"): ["EcoBoost", "EcoBoost Premium", "GT", "GT Premium", "Mach 1"],
    ("Chevrolet", "Silverado"): ["Work Truck", "Custom", "LT", "RST", "LTZ", "High Country"],
    ("Chevrolet", "Equinox"): ["LS", "LT", "RS", "Premier"],
    ("Chevrolet", "Tahoe"): ["LS", "LT", "RST", "Z71", "Premier", "High Country"],
    ("Tesla", "Model 3"): ["Standard Range", "Long Range", "Performance"],
    ("Tesla", "Model Y"): ["Standard Range", "Long Range", "Performance"],
    ("Mercedes-Benz", "GLE"): ["GLE 350", "GLE 450", "GLE 53 AMG", "GLE 63 S AMG"],
    ("Mercedes-Benz", "C-Class"): ["C 300", "C 300 4MATIC", "AMG C 43", "AMG C 63"],
    ("Audi", "Q5"): ["Premium", "Premium Plus", "Prestige", "SQ5"],
    ("Audi", "A4"): ["Premium", "Premium Plus", "Prestige", "S4"],
    ("Hyundai", "Tucson"): ["SE", "SEL", "N Line", "Limited", "XRT"],
    ("Hyundai", "Santa Fe"): ["SE", "SEL", "XRT", "Limited", "Calligraphy"],
    ("Kia", "Telluride"): ["LX", "S", "EX", "SX", "SX-Prestige"],
    ("Kia", "Sportage"): ["LX", "S", "EX", "SX", "X-Line"],
    ("Subaru", "Outback"): ["Base", "Premium", "Limited", "Wilderness", "Touring XT"],
    ("Subaru", "Forester"): ["Base", "Premium", "Sport", "Limited", "Touring"],
    ("Nissan", "Altima"): ["S", "SV", "SR", "SL", "Platinum"],
    ("Nissan", "Rogue"): ["S", "SV", "SL", "Platinum"],
    ("Jeep", "Grand Cherokee"): ["Laredo", "Altitude", "Limited", "Overland", "Summit"],
    ("Mazda", "CX-5"): ["Sport", "Select", "Preferred", "Carbon Edition", "Signature"],
}

REGIONS = [
    "Austin TX", "Los Angeles CA", "Chicago IL",
    "Houston TX", "Dallas TX", "Phoenix AZ",
    "New York NY", "Seattle WA", "Miami FL", "Denver CO",
]

SEGMENTS = ["luxury SUV", "midsize sedan", "compact SUV", "full-size truck", "electric vehicle"]

DEALER_CITIES = [
    ("Austin", "TX"), ("Los Angeles", "CA"), ("Chicago", "IL"),
    ("Houston", "TX"), ("Dallas", "TX"), ("Phoenix", "AZ"),
    ("New York", "NY"), ("Seattle", "WA"),
]

# ── Brand knowledge tables ─────────────────────────────────────────────────

PRICE_RANGES = {
    "BMW":           {"new": "$45,000–$90,000",  "used_2_3yr": "$28,000–$65,000"},
    "Mercedes-Benz": {"new": "$50,000–$95,000",  "used_2_3yr": "$32,000–$70,000"},
    "Audi":          {"new": "$42,000–$80,000",  "used_2_3yr": "$26,000–$60,000"},
    "Tesla":         {"new": "$42,000–$75,000",  "used_2_3yr": "$28,000–$55,000"},
    "Toyota":        {"new": "$25,000–$52,000",  "used_2_3yr": "$18,000–$38,000"},
    "Honda":         {"new": "$23,000–$48,000",  "used_2_3yr": "$16,000–$35,000"},
    "Ford":          {"new": "$28,000–$70,000",  "used_2_3yr": "$20,000–$52,000"},
    "Chevrolet":     {"new": "$27,000–$68,000",  "used_2_3yr": "$19,000–$50,000"},
    "Hyundai":       {"new": "$22,000–$45,000",  "used_2_3yr": "$15,000–$32,000"},
    "Kia":           {"new": "$22,000–$46,000",  "used_2_3yr": "$15,000–$33,000"},
    "Subaru":        {"new": "$23,000–$42,000",  "used_2_3yr": "$16,000–$30,000"},
    "Nissan":        {"new": "$22,000–$45,000",  "used_2_3yr": "$15,000–$32,000"},
    "Jeep":          {"new": "$32,000–$62,000",  "used_2_3yr": "$22,000–$45,000"},
    "Mazda":         {"new": "$24,000–$42,000",  "used_2_3yr": "$17,000–$31,000"},
}

MAKE_RELIABILITY = {
    "BMW":           "above-average performance focus; higher maintenance costs than average; reliability rated average by Consumer Reports",
    "Mercedes-Benz": "luxury-grade build quality; higher cost of ownership; reliability rated below average by Consumer Reports",
    "Audi":          "sporty and refined German engineering; above-average maintenance costs; reliability rated average",
    "Tesla":         "industry-leading acceleration and over-the-air updates; reliability improving but still below average overall; no dealer service required",
    "Toyota":        "top-ranked reliability by Consumer Reports and JD Power; very low maintenance costs; excellent long-term durability",
    "Honda":         "consistently high reliability ratings; low ownership costs; strong resale value across all models",
    "Ford":          "capable and versatile; reliability varies by model; F-150 is the best-selling vehicle in the US",
    "Chevrolet":     "broad lineup; reliability varies by model; trucks and full-size SUVs are segment leaders",
    "Hyundai":       "excellent value for money; reliability improved significantly; best-in-class 10yr/100k powertrain warranty",
    "Kia":           "top value segment; reliability improved significantly; Telluride rated highest in class by multiple agencies",
    "Subaru":        "symmetrical AWD standard on all models; strong IIHS safety ratings; reliability rated above average",
    "Nissan":        "competitive entry pricing; reliability rated average to below average in recent years",
    "Jeep":          "class-leading off-road capability; known reliability concerns for daily driving; loyal enthusiast following",
    "Mazda":         "sporty handling and premium interior feel; excellent build quality; reliability rated above average",
}

MAKE_BUYER_PROFILE = {
    "BMW":           "drivers who prioritize performance, technology, and prestige",
    "Mercedes-Benz": "buyers seeking ultimate luxury, comfort, and brand status",
    "Audi":          "buyers wanting European refinement with a sporty character",
    "Tesla":         "tech-forward buyers who want zero emissions and cutting-edge autonomous features",
    "Toyota":        "practical buyers who value long-term reliability and low total cost of ownership",
    "Honda":         "value-conscious buyers who refuse to sacrifice quality or reliability",
    "Ford":          "buyers needing a versatile work or family vehicle with proven capability",
    "Chevrolet":     "buyers wanting a broad selection of capable, value-oriented American vehicles",
    "Hyundai":       "budget-conscious buyers who want modern features backed by a strong warranty",
    "Kia":           "buyers seeking the best value-to-feature ratio on the market",
    "Subaru":        "outdoor-active buyers who need all-weather capability with strong safety ratings",
    "Nissan":        "practical buyers seeking comfortable transportation at an affordable price",
    "Jeep":          "adventure-oriented buyers who want genuine off-road credibility",
    "Mazda":         "driving enthusiasts who value quality, style, and handling at mainstream prices",
}

REGION_MARKET_INFO = {
    "Austin TX":      {"demand": "very high", "premium": "+8%",  "days": "18–28", "tip": "inventory is tight due to tech-sector population growth; act quickly on well-priced listings"},
    "Los Angeles CA": {"demand": "high",      "premium": "+5%",  "days": "22–35", "tip": "large dealer network near I-405 and I-710; CPO luxury deals available at volume franchises"},
    "Chicago IL":     {"demand": "moderate",  "premium": "0%",   "days": "30–45", "tip": "winter months (Dec–Feb) offer best negotiating leverage as showroom traffic drops"},
    "Houston TX":     {"demand": "high",      "premium": "+3%",  "days": "25–38", "tip": "one of the largest dealer networks in the US; use competing offers to negotiate"},
    "Dallas TX":      {"demand": "high",      "premium": "+4%",  "days": "22–35", "tip": "strong truck and SUV demand keeps prices elevated; sedan deals are better here"},
    "Phoenix AZ":     {"demand": "moderate",  "premium": "+2%",  "days": "28–40", "tip": "inspect rubber seals, AC systems, and paint for sun/heat deterioration on used vehicles"},
    "New York NY":    {"demand": "moderate",  "premium": "+6%",  "days": "35–50", "tip": "lower-mileage city cars available but premiums are high; check for parking-lot damage"},
    "Seattle WA":     {"demand": "high",      "premium": "+5%",  "days": "20–32", "tip": "AWD vehicles command a premium; EVs heavily incentivized by WA state rebates"},
    "Miami FL":       {"demand": "high",      "premium": "+4%",  "days": "24–36", "tip": "always request a flood/hurricane history check on any used vehicle in South Florida"},
    "Denver CO":      {"demand": "high",      "premium": "+5%",  "days": "21–34", "tip": "AWD/4WD commands premium in mountain markets; altitude affects some turbo engines"},
}

SEGMENT_TREND_DATA = {
    "luxury SUV": {
        "demand": "strong and growing",
        "leaders": "BMW X5, Mercedes-Benz GLE, Audi Q5, Cadillac Escalade",
        "price_trend": "up 3–5% YoY as inventory normalizes post-pandemic",
        "inventory": "improving but still 15% below 2019 levels at most dealers",
        "tips": "Compare CPO programs — BMW, Mercedes, and Audi offer competitive rates. Buy in Q4 for year-end incentives.",
    },
    "midsize sedan": {
        "demand": "softening as buyers shift to SUVs",
        "leaders": "Toyota Camry, Honda Accord, Hyundai Sonata, Mazda6",
        "price_trend": "flat to down 2–3% as dealers incentivize to move inventory",
        "inventory": "plentiful — best buyer's market in the passenger car segment",
        "tips": "Sedans offer the best value right now. Negotiate aggressively — dealers need to move them. Hybrid trims hold value better.",
    },
    "compact SUV": {
        "demand": "highest of any segment — consistently the best-selling category",
        "leaders": "Toyota RAV4, Honda CR-V, Kia Sportage, Subaru Forester, Ford Escape",
        "price_trend": "up 2–4% YoY; used models holding value well",
        "inventory": "tighter than pre-pandemic; popular colors/trims sell within days",
        "tips": "Set price alerts and act quickly. RAV4 Hybrid and CR-V Hybrid command premiums but retain value better.",
    },
    "full-size truck": {
        "demand": "extremely high; trucks are the top-selling vehicles in the US",
        "leaders": "Ford F-150, Chevrolet Silverado, Ram 1500, GMC Sierra",
        "price_trend": "up 4–6% YoY; off-road and work trims most in demand",
        "inventory": "improving but specific configurations (Raptor, TRX) have long waits",
        "tips": "Work trim (XL/XLT) offers best value. Avoid paying ADM — shop 3+ dealers. Pre-owned fleet trucks often have low mileage and low prices.",
    },
    "electric vehicle": {
        "demand": "growing but slowing from 2022 peak as mainstream buyers hesitate",
        "leaders": "Tesla Model 3, Tesla Model Y, Chevrolet Equinox EV, Ford Mustang Mach-E, Hyundai Ioniq 5",
        "price_trend": "down 8–12% from 2022 highs; used EV prices dropped significantly",
        "inventory": "plentiful across most brands; Tesla still dominates market share",
        "tips": "Check federal $7,500 EV tax credit eligibility. Used EV market offers exceptional deals — 2021 Teslas selling at 40% off original MSRP. Verify battery health before purchasing.",
    },
}


# ── fueleconomy.gov helpers ─────────────────────────────────────────────────

def fetch_trims_from_fueleconomy(make: str, model: str, year: int = 2022) -> list:
    try:
        r = requests.get(
            f"{FUELECONOMY_BASE}/vehicle/menu/trim",
            params={"year": year, "make": make, "model": model},
            headers={"Accept": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("menuItem", [])
        if isinstance(items, dict):
            items = [items]
        trims = [item.get("text", "") for item in items if item.get("text")]
        return trims if trims else FALLBACK_TRIMS.get((make, model), [])
    except Exception:
        return FALLBACK_TRIMS.get((make, model), [])


def fetch_mpg_from_fueleconomy(make: str, model: str, year: int = 2022) -> str:
    try:
        r = requests.get(
            f"{FUELECONOMY_BASE}/vin/vehicles",
            params={"year": year, "make": make, "model": model, "count": 1},
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if r.status_code != 200:
            return ""
        data = r.json()
        vehicles = data.get("vehicle", [])
        if isinstance(vehicles, dict):
            vehicles = [vehicles]
        if not vehicles:
            return ""
        v = vehicles[0]
        city = v.get("city08", "")
        hwy = v.get("highway08", "")
        return f"{city} city / {hwy} highway MPG" if city and hwy else ""
    except Exception:
        return ""


# ── Template-based content generators ─────────────────────────────────────

def generate_car_spec(make: str, model: str, trims: list, mpg: str) -> str:
    trims_str = ", ".join(trims[:5]) if trims else "Standard, Premium, Sport"
    mpg_line = f"Fuel economy: {mpg}." if mpg else "Fuel economy varies by trim and powertrain."
    prices = PRICE_RANGES.get(make, {"new": "$25,000–$50,000", "used_2_3yr": "$18,000–$38,000"})
    reliability = MAKE_RELIABILITY.get(make, "reliability rated above average by consumer surveys")
    buyer = MAKE_BUYER_PROFILE.get(make, "practical buyers seeking a balance of value and features")

    return (
        f"The {make} {model} is available in multiple trim configurations: {trims_str}. "
        f"{mpg_line} "
        f"New vehicle MSRP range: {prices['new']}. "
        f"Used 2020–2023 models typically list for {prices['used_2_3yr']}. "
        f"Reliability and ownership notes: {reliability}. "
        f"Standard features across most trims include: touchscreen infotainment with Apple CarPlay "
        f"and Android Auto, backup camera, automatic emergency braking, lane-departure warning, "
        f"and multiple USB/charging ports. "
        f"Higher trims typically add: heated and ventilated seats, panoramic sunroof, "
        f"premium audio system, adaptive cruise control, wireless charging, and enhanced safety packages. "
        f"Ideal buyer profile: {buyer}. "
        f"The {make} {model} has strong dealer availability nationwide and competitive certified "
        f"pre-owned (CPO) programs at franchise dealerships."
    )


def generate_market_data(make: str, model: str, region: str) -> str:
    prices = PRICE_RANGES.get(make, {"new": "$25,000–$50,000", "used_2_3yr": "$18,000–$38,000"})
    info = REGION_MARKET_INFO.get(region, {
        "demand": "moderate", "premium": "+2%", "days": "28–42",
        "tip": "shop multiple dealers for best price",
    })
    return (
        f"2024 market data for {make} {model} in {region}:\n"
        f"Typical used listing price (2020–2023 models): {prices['used_2_3yr']}.\n"
        f"New MSRP range: {prices['new']}.\n"
        f"Local demand: {info['demand']}. Regional price premium vs national average: {info['premium']}.\n"
        f"Average days on market: {info['days']} days.\n"
        f"Price trend: Used car prices are moderating after the 2021–2022 surge, "
        f"down approximately 4–7% year-over-year in most segments.\n"
        f"CPO availability: Certified pre-owned {model} units available at franchise dealerships "
        f"with manufacturer-backed warranty extending to 6 years/100,000 miles on most programs.\n"
        f"Buying tip for {region}: {info['tip']}."
    )


def generate_market_trends(segment: str, region: str) -> str:
    data = SEGMENT_TREND_DATA.get(segment, {
        "demand": "steady",
        "leaders": "various models",
        "price_trend": "flat year-over-year",
        "inventory": "normalizing",
        "tips": "Compare multiple dealers and negotiate on out-of-door price.",
    })
    info = REGION_MARKET_INFO.get(region, {"demand": "moderate", "premium": "+2%", "tip": "shop multiple dealers"})
    return (
        f"2024 {segment} market trends in {region}:\n"
        f"Segment demand: {data['demand']}. Local market demand: {info['demand']}.\n"
        f"Top models in segment: {data['leaders']}.\n"
        f"Pricing dynamics: {data['price_trend']}. "
        f"Regional price vs national: {info['premium']}.\n"
        f"Inventory status: {data['inventory']}.\n"
        f"Buyer tips: {data['tips']} {info['tip'].capitalize()}."
    )


# ── Marketcheck dealer fetch ────────────────────────────────────────────────

def fetch_marketcheck_dealers(city: str, state: str) -> list:
    if not MARKETCHECK_API_KEY:
        return []
    try:
        r = requests.get(
            f"{MARKETCHECK_BASE}/dealers/car",
            params={"api_key": MARKETCHECK_API_KEY, "city": city, "state": state, "rows": 5},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("dealers", [])
    except Exception:
        return []


def generate_template_dealers(cities: list) -> list:
    dealers = []
    brand_pairs = [
        ("AutoNation", ["Toyota", "Honda"]),
        ("Hendrick Automotive", ["Chevrolet", "BMW"]),
        ("Penske Automotive", ["Mercedes-Benz", "Audi"]),
        ("Lithia Motors", ["Ford", "Subaru"]),
        ("Group 1 Automotive", ["BMW", "Toyota"]),
        ("Sonic Automotive", ["Honda", "Ford"]),
        ("Asbury Automotive", ["Mercedes-Benz", "Toyota"]),
        ("Ken Garff Automotive", ["Ford", "Chevrolet"]),
    ]
    for i, (city, state) in enumerate(cities):
        for j in range(2):
            brand_idx = (i * 2 + j) % len(brand_pairs)
            group, makes = brand_pairs[brand_idx]
            dealers.append({
                "name": f"{group} {city}",
                "city": city,
                "state": state,
                "address": f"{1000 + i * 100 + j * 50} Auto Mall Drive",
                "makes": makes,
                "rating": round(4.1 + (i + j) % 8 * 0.1, 1),
                "inventory_focus": f"New, used, and CPO {' and '.join(makes)} vehicles",
            })
    return dealers


# ── Build ChromaDB collections ─────────────────────────────────────────────

def build_car_specs_collection(client, ef):
    print("\n[1/4] Building car_specs collection...")
    try:
        client.delete_collection("car_specs")
    except Exception:
        pass
    col = client.create_collection("car_specs", embedding_function=ef,
                                   metadata={"hnsw:space": "cosine"})
    docs, metas, ids = [], [], []
    for i, (make, model) in enumerate(POPULAR_MODELS):
        print(f"  Fetching specs: {make} {model} ({i+1}/{len(POPULAR_MODELS)})")
        trims = fetch_trims_from_fueleconomy(make, model)
        mpg = fetch_mpg_from_fueleconomy(make, model)
        time.sleep(0.2)
        spec_text = generate_car_spec(make, model, trims, mpg)
        docs.append(f"{make} {model} specs and overview:\n{spec_text}")
        metas.append({"make": make, "model": model,
                      "trims": ", ".join(trims[:5]),
                      "source": "fueleconomy.gov + template"})
        ids.append(f"spec_{make}_{model}".replace(" ", "_").replace("-", "_"))
    col.add(documents=docs, metadatas=metas, ids=ids)
    print(f"  ✓ Added {len(docs)} car spec documents")


def build_market_data_collection(client, ef):
    print("\n[2/4] Building market_data collection...")
    try:
        client.delete_collection("market_data")
    except Exception:
        pass
    col = client.create_collection("market_data", embedding_function=ef,
                                   metadata={"hnsw:space": "cosine"})
    docs, metas, ids = [], [], []
    sample_models = POPULAR_MODELS[:15]
    sample_regions = REGIONS[:4]
    total = len(sample_models) * len(sample_regions)
    count = 0
    for make, model in sample_models:
        for region in sample_regions:
            count += 1
            print(f"  Generating market data: {make} {model} in {region} ({count}/{total})")
            text = generate_market_data(make, model, region)
            docs.append(f"{make} {model} market data in {region} (2024):\n{text}")
            metas.append({"make": make, "model": model, "region": region, "source": "template"})
            ids.append(f"market_{make}_{model}_{region}".replace(" ", "_").replace("-", "_"))
    col.add(documents=docs, metadatas=metas, ids=ids)
    print(f"  ✓ Added {len(docs)} market data documents")


def build_dealer_data_collection(client, ef):
    print("\n[3/4] Building dealer_data collection...")
    try:
        client.delete_collection("dealer_data")
    except Exception:
        pass
    col = client.create_collection("dealer_data", embedding_function=ef,
                                   metadata={"hnsw:space": "cosine"})
    docs, metas, ids = [], [], []

    real_count = 0
    for city, state in DEALER_CITIES:
        dealers = fetch_marketcheck_dealers(city, state)
        for d in dealers:
            name = d.get("name", "Unknown Dealer")
            city_d = d.get("city", city)
            state_d = d.get("state", state)
            doc = (
                f"Dealer: {name}\n"
                f"Location: {city_d}, {state_d}\n"
                f"Address: {d.get('street', 'N/A')} {d.get('zip', '')}\n"
                f"Phone: {d.get('phone', 'N/A')}\n"
                f"Source: Marketcheck live inventory"
            )
            docs.append(doc)
            metas.append({"city": city, "state": state, "source": "Marketcheck"})
            ids.append(f"dealer_mc_{len(ids)}")
            real_count += 1

    if real_count > 0:
        print(f"  ✓ Fetched {real_count} real dealers from Marketcheck")
    else:
        print("  Marketcheck dealers unavailable — using template dealers")

    print("  Adding template dealers to supplement...")
    template_dealers = generate_template_dealers(DEALER_CITIES)
    for d in template_dealers:
        makes = ", ".join(d["makes"]) if isinstance(d["makes"], list) else str(d["makes"])
        doc = (
            f"Dealer: {d['name']}\n"
            f"Location: {d['city']}, {d['state']}\n"
            f"Address: {d['address']}\n"
            f"Specializes in: {makes}\n"
            f"Rating: {d['rating']}/5\n"
            f"Inventory focus: {d['inventory_focus']}"
        )
        docs.append(doc)
        metas.append({"city": d["city"], "state": d["state"], "source": "template"})
        ids.append(f"dealer_tpl_{len(ids)}")

    col.add(documents=docs, metadatas=metas, ids=ids)
    print(f"  ✓ Added {len(docs)} dealer documents total")


def build_market_trends_collection(client, ef):
    print("\n[4/4] Building market_trends collection...")
    try:
        client.delete_collection("market_trends")
    except Exception:
        pass
    col = client.create_collection("market_trends", embedding_function=ef,
                                   metadata={"hnsw:space": "cosine"})
    docs, metas, ids = [], [], []
    total = len(SEGMENTS) * len(REGIONS[:5])
    count = 0
    for segment in SEGMENTS:
        for region in REGIONS[:5]:
            count += 1
            print(f"  Generating trend: {segment} in {region} ({count}/{total})")
            text = generate_market_trends(segment, region)
            docs.append(f"{segment} market trends in {region} (2024):\n{text}")
            metas.append({"segment": segment, "region": region, "source": "template"})
            ids.append(f"trend_{segment}_{region}".replace(" ", "_"))
    col.add(documents=docs, metadatas=metas, ids=ids)
    print(f"  ✓ Added {len(docs)} market trend documents")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("AUTO_AI Knowledge Base Builder")
    print("  Embeddings: local (no OpenAI key required)")
    print("=" * 60)
    print(f"ChromaDB path: {CHROMA_PATH}")

    ef = DefaultEmbeddingFunction()

    client = chromadb.PersistentClient(path=CHROMA_PATH)

    build_car_specs_collection(client, ef)
    build_market_data_collection(client, ef)
    build_dealer_data_collection(client, ef)
    build_market_trends_collection(client, ef)

    print("\n" + "=" * 60)
    print("Knowledge base built successfully!")
    for name in ["car_specs", "market_data", "dealer_data", "market_trends"]:
        col = client.get_collection(name, embedding_function=ef)
        print(f"  {name}: {col.count()} documents")
    print("=" * 60)
    print("\nRun your AUTO_AI app — RAG is now active.")


if __name__ == "__main__":
    main()
