"""
URL builders for AutoTrader, CarGurus, and Cars.com.
Extracted here so they can be imported by both app.py and test_links.py.
"""
from urllib.parse import quote as _url_quote

# ── CarGurus entity IDs ──────────────────────────────────────────────────────
CG_ENTITY_IDS = {
    # Acura
    "acura adx": 3387, "acura mdx": 16,
    # Audi
    "audi a3": 24, "audi a4": 25, "audi a4 allroad": 2149,
    "audi a5": 2508, "audi a5 sportback": 2508,
    "audi a6": 27, "audi a8": 29, "audi q3": 2129, "audi q5": 1988,
    "audi e-tron": 2829, "audi etron": 2829,
    # BMW
    "bmw 2 series": 2262, "bmw 3 series": 2240, "bmw 4 series": 2244,
    "bmw i4": 3155,
    "bmw x1": 2160, "bmw x3": 392, "bmw x5": 393, "bmw x7": 2656,
    # Buick
    "buick enclave": 1029, "buick encore gx": 2901, "buick envision": 2398, "buick envista": 3333,
    # Cadillac
    "cadillac lyriq": 3157, "cadillac xt5": 2393,
    # Chevrolet
    "chevrolet blazer ev": 3351, "chevrolet colorado": 614, "chevrolet equinox": 616,
    "chevrolet equinox ev": 3267, "chevrolet express cargo": 618, "chevrolet silverado 1500": 630,
    "chevrolet silverado 2500hd": 634, "chevrolet silverado 3500hd": 1027,
    "chevrolet suburban": 638, "chevrolet tahoe": 639, "chevrolet trailblazer": 642,
    "chevrolet traverse": 1521, "chevrolet trax": 2272,
    # Chrysler
    "chrysler pacifica": 177,
    # Dodge
    "dodge durango": 651,
    # Ford
    "ford bronco": 320, "ford bronco sport": 3094, "ford escape": 330, "ford expedition": 333,
    "ford explorer": 334, "ford f-150": 337, "ford f 150": 337, "ford f150": 337,
    "ford f-150 lightning": 3147, "ford f-250 super duty": 341, "ford f-350 super duty": 343,
    "ford maverick": 1293, "ford mustang": 2, "ford mustang mach-e": 2990,
    "ford mustang mach e": 2990, "ford ranger": 354, "ford transit cargo": 1067,
    # Genesis
    "genesis gv70": 3163,
    # GMC
    "gmc acadia": 925, "gmc canyon": 103, "gmc sierra 1500": 116,
    "gmc sierra 2500hd": 119, "gmc sierra 3500hd": 973, "gmc terrain": 2042,
    # Honda
    "honda accord": 585, "honda accord hybrid": 2256, "honda cr-v": 589, "honda crv": 589,
    "honda cr-v hybrid": 3002, "honda civic": 586, "honda civic hatchback": 2441,
    "honda civic hybrid": 2923, "honda hr-v": 1271, "honda hrv": 1271,
    "honda odyssey": 592, "honda passport": 593, "honda pilot": 594, "honda ridgeline": 734,
    # Hyundai
    "hyundai elantra": 92, "hyundai elantra hybrid": 3139, "hyundai ioniq 5": 3120,
    "hyundai kona": 2663, "hyundai palisade": 2836, "hyundai santa cruz": 3128,
    "hyundai santa fe": 94, "hyundai santa fe hybrid": 3144,
    "hyundai sonata": 96, "hyundai tucson": 98, "hyundai tucson hybrid": 3141,
    # Infiniti
    "infiniti qx60": 2243,
    # Jeep
    "jeep compass": 905, "jeep gladiator": 2021, "jeep grand cherokee": 490,
    "jeep grand cherokee l": 3108, "jeep wrangler": 494,
    # Kia
    "kia carnival": 3117, "kia carnival hybrid": 3408, "kia k5": 3092, "kia niro": 2405,
    "kia seltos": 2991, "kia sorento": 162, "kia soul": 2020,
    "kia sportage": 164, "kia sportage hybrid": 3239, "kia telluride": 2830,
    # Lincoln
    "lincoln aviator": 524, "lincoln corsair": 2884, "lincoln nautilus": 2680,
    # Mazda
    "mazda cx-30": 2875, "mazda cx 30": 2875, "mazda cx-5": 2133, "mazda cx5": 2133,
    "mazda cx 5": 2133, "mazda cx-50": 3215, "mazda cx-90": 3315,
    # Mercedes-Benz
    "mercedes-benz c-class": 66, "mercedes benz c class": 66, "mercedes c-class": 66,
    "mercedes-benz glc": 2361, "mercedes glc": 2361,
    "mercedes-benz gle": 2317, "mercedes gle": 2317,
    "mercedes-benz gls": 2421, "mercedes gls": 2421,
    "mercedes-benz sprinter": 1830,
    # Mitsubishi
    "mitsubishi outlander": 429,
    # Nissan
    "nissan altima": 237, "nissan armada": 238, "nissan frontier": 240, "nissan kicks": 2660,
    "nissan murano": 243, "nissan pathfinder": 245, "nissan rogue": 1047,
    "nissan sentra": 249, "nissan versa": 937,
    # RAM
    "ram 1500": 2110, "ram1500": 2110, "ram 2500": 2102, "ram 3500": 2103,
    "ram promaster": 2229,
    # Subaru
    "subaru ascent": 2650, "subaru crosstrek": 2387, "subaru forester": 374,
    "subaru legacy": 378, "subaru outback": 380,
    # Lexus
    "lexus es": 2720, "lexus es hybrid": 2721, "lexus gs": 2822, "lexus gx": 2063,
    "lexus is": 2824, "lexus lc": 2400, "lexus lx": 3042, "lexus lx hybrid": 3438,
    "lexus nx hybrid": 2294, "lexus rc": 2827, "lexus ux hybrid": 2722,
    "lexus tx": 3343, "lexus tx 350": 3343,
    "lexus tx hybrid": 3345, "lexus tx 350h": 3345, "lexus tx 500h": 3345,
    # Porsche
    "porsche 718 boxster": 2416, "porsche 718 cayman": 2430,
    "porsche cayenne e-hybrid": 2723, "porsche macan": 2261,
    "porsche panamera e-hybrid": 2930, "porsche taycan": 2974,
    # Tesla
    "tesla model 3": 2475, "tesla model3": 2475,
    "tesla model x": 2132, "tesla modelx": 2132,
    "tesla model y": 3044, "tesla modely": 3044,
    # Toyota
    "toyota 4runner": 290, "toyota camry": 292, "toyota corolla": 295,
    "toyota rav4": 306, "toyota rav 4": 306, "toyota rav4 hybrid": 2318,
    "toyota sienna": 308,
    "toyota tacoma": 311, "toyota tundra": 313, "toyota tundra hybrid": 3414,
    # Volkswagen
    "volkswagen atlas": 2507, "vw atlas": 2507,
    "volkswagen atlas cross sport": 2995, "volkswagen jetta": 200, "vw jetta": 200,
    "volkswagen taos": 3131, "volkswagen tiguan": 1104, "vw tiguan": 1104,
    # Volvo
    "volvo xc60": 1629, "volvo xc90": 523,
}

# CarGurus exterior-color spt tag IDs
CG_COLOR_SPT = {
    "black": 335, "blue": 334, "gray": 410, "grey": 410,
    "red": 332, "silver": 408, "white": 333,
}

# Cars.com model slug overrides
CM_SLUG_MAP = {
    "lexus_tx_500h":   "lexus_tx",
    "lexus_tx_350h":   "lexus_tx",
    "lexus_tx_350":    "lexus_tx",
    "lexus_tx_hybrid": "lexus_tx",
    "lexus_nx_450h":   "lexus_nx",
    "lexus_nx_350h":   "lexus_nx",
    "lexus_nx_350":    "lexus_nx",
    "lexus_rx_500h":   "lexus_rx",
    "lexus_rx_450h":   "lexus_rx",
    "lexus_rx_350":    "lexus_rx",
    "lexus_rx_350h":   "lexus_rx",
    "lexus_es_300h":   "lexus_es",
    "lexus_gx_550":    "lexus_gx",
    "bmw_m3_competition": "bmw_m3",
    "bmw_m4_competition": "bmw_m4",
    "bmw_x5_m":           "bmw_x5",
    "bmw_x6_m":           "bmw_x6",
}

# Make name normalization
MAKE_NORMALIZE = {
    "mercedes":      "Mercedes-Benz",
    "mercedes benz": "Mercedes-Benz",
    "chevy":         "Chevrolet",
    "vw":            "Volkswagen",
    "volk":          "Volkswagen",
    "alfa":          "Alfa Romeo",
    "alfa romeo":    "Alfa Romeo",
    "land rover":    "Land Rover",
}


def normalize_make(make: str) -> str:
    return MAKE_NORMALIZE.get(make.strip().lower(), make.strip())


def cg_direct_url(make: str, model: str, condition: str,
                  zip_code: str = "", price_max: int = 999999,
                  ext_color: str = "", int_color: str = "") -> str:
    """Return a direct CarGurus URL using entity ID, or None if not in lookup."""
    key = f"{make.strip()} {model.strip()}".lower()
    entity_id = CG_ENTITY_IDS.get(key)
    if entity_id is None:
        for k, eid in CG_ENTITY_IDS.items():
            if k.replace("-", " ").replace("  ", " ") == key.replace("-", " ").replace("  ", " "):
                entity_id = eid
                break
    if entity_id is None:
        return None

    make_slug  = make.strip().replace(" ", "-")
    model_slug = model.strip().replace(" ", "-")
    is_new     = (condition or "").lower() == "new"
    color_key  = (ext_color or "").strip().lower()
    color_spt  = CG_COLOR_SPT.get(color_key)
    int_key    = (int_color or "").strip().lower()

    qp = []
    if zip_code:
        qp.append(f"zip={zip_code}")
    if price_max and price_max < 999000:
        qp.append(f"maxPrice={price_max}")
    if int_key and int_key not in ("any", "other"):
        qp.append(f"interior_color={int_key.title()}")

    if is_new:
        if color_key and color_key not in ("any", "other"):
            qp.append(f"exteriorColorSimple={color_key.upper()}")
        qs = ("?" + "&".join(qp)) if qp else ""
        return f"https://www.cargurus.com/Cars/new/nl-New-{make_slug}-{model_slug}-d{entity_id}{qs}"
    else:
        qs = ("?" + "&".join(qp)) if qp else ""
        if color_spt and color_key not in ("any", "other"):
            color_slug = color_key.title()
            return f"https://www.cargurus.com/Cars/s-Used-{color_slug}-{make_slug}-{model_slug}-d{entity_id}_spt{color_spt}{qs}"
        return f"https://www.cargurus.com/Cars/l-Used-{make_slug}-{model_slug}-d{entity_id}{qs}"


def cg_url(make: str, model: str, zip_code: str, price_max: int,
           condition: str, ext_color: str = "", int_color: str = "") -> str:
    direct = cg_direct_url(make, model, condition, zip_code, price_max, ext_color, int_color)
    if direct:
        return direct
    parts = []
    if condition and condition != "Any":
        parts.append(condition)
    parts.append(f"{make} {model}".strip())
    parts.append("for sale")
    if zip_code:
        parts.append(f"near {zip_code}")
    if price_max < 999000:
        parts.append(f"under ${price_max:,}")
    return "https://www.google.com/search?q=" + _url_quote("site:cargurus.com " + " ".join(parts))


def at_url(make: str, model: str, condition: str,
           zip_code: str = "", price_max: int = 999999, price_min: int = 0,
           ext_color: str = "", int_color: str = "",
           radius: int = 50, mileage: int = None) -> str:
    """Build an AutoTrader search URL."""
    make = normalize_make(make)
    cond_seg  = "used-cars/" if condition == "Used" else "new-cars/" if condition == "New" else "cars-for-sale/"
    price_seg = f"cars-under-{price_max}/" if price_max and price_max < 999000 else ""
    color_seg = (ext_color.lower().replace(" ", "-") + "/") if ext_color and ext_color.lower() not in ("any", "other", "") else ""
    make_slug  = make.lower().replace(" ", "-")
    model_slug = model.lower().replace(" ", "-").replace("/", "-")
    qp = []
    if zip_code:    qp.append(f"zip={zip_code}")
    if radius < 500: qp.append(f"searchRadius={radius}")
    if price_min:   qp.append(f"startPrice={price_min}")
    if price_max and price_max < 999000: qp.append(f"endPrice={price_max}")
    if mileage:     qp.append(f"maxMileage={mileage}")
    if int_color and int_color.lower() not in ("any", "other", ""):
        qp.append(f"intColorSimple={int_color.upper()}")
    base = f"https://www.autotrader.com/cars-for-sale/{cond_seg}{price_seg}{color_seg}{make_slug}/{model_slug}/"
    return base + ("?" + "&".join(qp) if qp else "")


def cm_url(make: str, model: str, condition: str,
           zip_code: str = "", price_max: int = 999999, price_min: int = 0,
           ext_color: str = "", int_color: str = "",
           radius: int = 50, mileage: int = None) -> str:
    """Build a Cars.com search URL."""
    make = normalize_make(make)
    cm_make  = make.lower().replace(" ", "_").replace("-", "_")
    cm_model = (make + "_" + model).lower().replace(" ", "_").replace("-", "_").replace("/", "_").replace(".", "")
    cm_model = CM_SLUG_MAP.get(cm_model, cm_model)
    stock    = "used" if condition == "Used" else "new" if condition == "New" else "all"
    qp = [f"stock_type={stock}", f"makes[]={cm_make}", f"models[]={cm_model}"]
    if zip_code:    qp.append(f"zip={zip_code}")
    if radius < 500: qp.append(f"maximum_distance={radius}")
    if price_min:   qp.append(f"price_min={price_min}")
    if price_max and price_max < 999000: qp.append(f"price_max={price_max}")
    if mileage:     qp.append(f"mileage_max={mileage}")
    if ext_color and ext_color.lower() not in ("any", "other", ""):
        qp.append(f"exterior_color_slugs[]={ext_color.lower()}")
    if int_color and int_color.lower() not in ("any", "other", ""):
        qp.append(f"interior_color_slugs[]={int_color.lower()}")
    return "https://www.cars.com/shopping/results/?" + "&".join(qp)
