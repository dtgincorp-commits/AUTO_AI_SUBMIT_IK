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
    # Ferrari
    "ferrari sf90": 3033, "ferrari sf90 stradale": 3033,
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
    "gmc sierra 2500": 119, "gmc sierra 2500hd": 119, "gmc sierra 3500hd": 973, "gmc terrain": 2042,
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
    "mercedes c class": 66, "mercedes c300": 66, "mercedes c 300": 66, "mercedes c 43": 66,
    "mercedes-benz e-class": 76, "mercedes benz e class": 76, "mercedes e-class": 76,
    "mercedes e class": 76, "mercedes e350": 76, "mercedes e 350": 76,
    "mercedes e450": 76, "mercedes e 450": 76,
    "mercedes-benz s-class": 82, "mercedes benz s class": 82, "mercedes s-class": 82,
    "mercedes s class": 82, "mercedes s500": 82, "mercedes s 500": 82,
    "mercedes s580": 82, "mercedes s 580": 82,
    "mercedes-benz g-class": 78, "mercedes benz g class": 78, "mercedes g-class": 78,
    "mercedes g class": 78, "mercedes g550": 78, "mercedes g 550": 78,
    "mercedes amg g 63": 78, "mercedes g63": 78,
    "mercedes-benz cla": 2216, "mercedes benz cla": 2216, "mercedes cla": 2216,
    "mercedes cla 250": 2216, "mercedes cla250": 2216, "mercedes cla 45": 2216,
    "mercedes-benz amg gt": 2282, "mercedes amg gt": 2282,
    "mercedes amg gt 43": 2282, "mercedes amg gt 53": 2282, "mercedes amg gt 63": 2282,
    "mercedes-benz eqs": 3129, "mercedes eqs": 3129,
    "mercedes eqs 450": 3129, "mercedes eqs 580": 3129,
    "mercedes-benz gla": 2286, "mercedes gla": 2286,
    "mercedes gla 250": 2286, "mercedes gla250": 2286, "mercedes gla 35": 2286,
    "mercedes-benz glb": 2905, "mercedes glb": 2905,
    "mercedes glb 250": 2905, "mercedes glb250": 2905,
    "mercedes-benz sl": 84, "mercedes sl": 84, "mercedes sl-class": 84,
    "mercedes sl 43": 84, "mercedes sl 55": 84, "mercedes sl 63": 84,
    "mercedes-benz eqe": 3253, "mercedes eqe": 3253,
    "mercedes eqe 350": 3253, "mercedes eqe 500": 3253,
    "mercedes-benz eqb": 3252, "mercedes eqb": 3252,
    "mercedes eqb 250": 3252, "mercedes eqb 300": 3252, "mercedes eqb 350": 3252,
    "mercedes-benz cle": 3375, "mercedes cle": 3375,
    "mercedes cle 300": 3375, "mercedes cle 450": 3375,
    "mercedes-benz glc": 2361, "mercedes glc": 2361,
    "mercedes-benz glc 300e": 2361, "mercedes glc 300e": 2361,
    "mercedes-benz gle": 2317, "mercedes gle": 2317,
    "mercedes-benz gle 450e": 2317, "mercedes gle 450e": 2317,
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

# AutoTrader model slug overrides
# AutoTrader uses class-level slugs, not variant numbers.
# "GLE 450e" → "gle", "C 300" → "c-class", etc.
# Keys are lowercase model strings as returned by the NL parser.
AT_MODEL_SLUG_MAP = {
    # Mercedes-Benz — strip variant numbers, use class slug
    "c-class": "c-class", "c 300": "c-class", "c300": "c-class",
    "c 43": "c-class",    "c 63": "c-class",
    "e-class": "e-class", "e 350": "e-class", "e350": "e-class",
    "e 450": "e-class",   "e 53": "e-class",
    "s-class": "s-class", "s 500": "s-class", "s500": "s-class",
    "s 580": "s-class",   "s580": "s-class",  "s 63": "s-class",
    "g-class": "g-class", "g 550": "g-class", "g550": "g-class",
    "g 63": "g-class",    "amg g 63": "g-class",
    "gla": "gla",         "gla 250": "gla",    "gla250": "gla",
    "gla 35": "gla",      "gla 45": "gla",     "gla 450": "gla",
    "glb": "glb",         "glb 250": "glb",    "glb250": "glb",
    "glc": "glc",         "glc 300": "glc",    "glc300": "glc",
    "glc 300e": "glc",    "glc300e": "glc",    "glc 43": "glc",
    "gle": "gle",         "gle 350": "gle",    "gle 450": "gle",
    "gle 450e": "gle",    "gle450e": "gle",    "gle 53": "gle",
    "gle 63": "gle",
    "gls": "gls",         "gls 450": "gls",    "gls 580": "gls",
    "gls 63": "gls",
    "cla": "cla",         "cla 250": "cla",    "cla250": "cla",
    "cla 35": "cla",      "cla 45": "cla",
    "cle": "cle",         "cle 300": "cle",    "cle 450": "cle",
    "sl": "sl",           "sl 43": "sl",       "sl 55": "sl",
    "sl 63": "sl",
    "amg gt": "amg-gt",   "amg gt 43": "amg-gt", "amg gt 53": "amg-gt",
    "amg gt 63": "amg-gt","amg gt 63 s": "amg-gt",
    "eqs": "eqs",         "eqs 450": "eqs",    "eqs 580": "eqs",
    "eqe": "eqe",         "eqe 350": "eqe",    "eqe 500": "eqe",
    "eqb": "eqb",         "eqb 250": "eqb",    "eqb 300": "eqb",
    "eqb 350": "eqb",
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


# Representative ZIP codes for each US state (largest city downtown ZIP)
_STATE_ZIP = {
    "al": "35203", "ak": "99501", "az": "85001", "ar": "72201", "ca": "90001",
    "co": "80201", "ct": "06601", "de": "19801", "fl": "32099", "ga": "30301",
    "hi": "96801", "id": "83701", "il": "60601", "in": "46201", "ia": "50301",
    "ks": "67201", "ky": "40201", "la": "70112", "me": "04101", "md": "21201",
    "ma": "02101", "mi": "48201", "mn": "55401", "ms": "39201", "mo": "64101",
    "mt": "59101", "ne": "68101", "nv": "89101", "nh": "03101", "nj": "07101",
    "nm": "87101", "ny": "10001", "nc": "28201", "nd": "58101", "oh": "43201",
    "ok": "73101", "or": "97201", "pa": "19101", "ri": "02901", "sc": "29201",
    "sd": "57101", "tn": "37201", "tx": "77001", "ut": "84101", "vt": "05401",
    "va": "23450", "wa": "98101", "wv": "25301", "wi": "53201", "wy": "82001",
    "dc": "20001",
}

# Full state names → abbreviation
_STATE_NAME_TO_ABBR = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar",
    "california": "ca", "colorado": "co", "connecticut": "ct", "delaware": "de",
    "florida": "fl", "georgia": "ga", "hawaii": "hi", "idaho": "id",
    "illinois": "il", "indiana": "in", "iowa": "ia", "kansas": "ks",
    "kentucky": "ky", "louisiana": "la", "maine": "me", "maryland": "md",
    "massachusetts": "ma", "michigan": "mi", "minnesota": "mn", "mississippi": "ms",
    "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv",
    "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm", "new york": "ny",
    "north carolina": "nc", "north dakota": "nd", "ohio": "oh", "oklahoma": "ok",
    "oregon": "or", "pennsylvania": "pa", "rhode island": "ri", "south carolina": "sc",
    "south dakota": "sd", "tennessee": "tn", "texas": "tx", "utah": "ut",
    "vermont": "vt", "virginia": "va", "washington": "wa", "west virginia": "wv",
    "wisconsin": "wi", "wyoming": "wy", "district of columbia": "dc",
}

import re as _re_loc


def zip_from_location(location: str) -> str:
    """
    Extract a usable 5-digit ZIP from a location string.
    1. Returns an explicit ZIP if present (e.g. "Irvine, CA 92782" → "92782").
    2. Falls back to a state-name or state-abbr lookup
       (e.g. "arizona" → "85001", "AZ" → "85001").
    Returns "" if nothing can be resolved.
    """
    if not location:
        return ""
    # 1) Explicit 5-digit ZIP in the string
    m = _re_loc.search(r"\b(\d{5})\b", location)
    if m:
        return m.group(1)
    loc_lower = location.strip().lower()
    # 2) Full state name (may appear as whole string or after a comma, e.g. "arizona usa")
    for name, abbr in _STATE_NAME_TO_ABBR.items():
        if _re_loc.search(r"\b" + _re_loc.escape(name) + r"\b", loc_lower):
            return _STATE_ZIP[abbr]
    # 3) 2-letter state abbreviation (e.g. "AZ", "CA")
    abbr_m = _re_loc.search(r"\b([a-z]{2})\b", loc_lower)
    if abbr_m and abbr_m.group(1) in _STATE_ZIP:
        return _STATE_ZIP[abbr_m.group(1)]
    return ""


def normalize_make(make: str) -> str:
    return MAKE_NORMALIZE.get(make.strip().lower(), make.strip())


def cg_direct_url(make: str, model: str, condition: str,
                  zip_code: str = "", price_max: int = 999999,
                  ext_color: str = "", int_color: str = "",
                  radius: int = 50) -> str:
    """Return a CarGurus inventory listing URL using entity ID, or None if not in lookup."""
    key = f"{make.strip()} {model.strip()}".lower()
    entity_id = CG_ENTITY_IDS.get(key)
    if entity_id is None:
        for k, eid in CG_ENTITY_IDS.items():
            if k.replace("-", " ").replace("  ", " ") == key.replace("-", " ").replace("  ", " "):
                entity_id = eid
                break
    if entity_id is None:
        return None

    qp = [f"entityId=d{entity_id}"]
    if zip_code:
        qp.append(f"zip={zip_code}")
        qp.append(f"distance={radius}")
    if price_max and price_max < 999000:
        qp.append(f"max_price={price_max}")
    cond_lower = (condition or "").lower()
    if cond_lower == "new":
        qp.append("searchType=NEW")
    elif cond_lower == "used":
        qp.append("searchType=USED")
    elif "cpo" in cond_lower:
        qp.append("searchType=CPO")
    return "https://www.cargurus.com/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action?" + "&".join(qp)


def cg_url(make: str, model: str, zip_code: str, price_max: int,
           condition: str, ext_color: str = "", int_color: str = "",
           radius: int = 50) -> str:
    direct = cg_direct_url(make, model, condition, zip_code, price_max, ext_color, int_color, radius)
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


# AutoTrader internal make codes (used in makeCodeList query param)
AT_MAKE_CODE = {
    "acura": "ACURA",       "audi": "AUDI",         "bmw": "BMW",
    "buick": "BUICK",       "cadillac": "CAD",       "chevrolet": "CHEV",
    "chrysler": "CHRY",     "dodge": "DODGE",        "ferrari": "FERRA",
    "ford": "FORD",         "genesis": "GENES",      "gmc": "GMC",
    "honda": "HONDA",       "hyundai": "HYUND",      "infiniti": "INFIN",
    "jeep": "JEEP",         "kia": "KIA",            "lexus": "LEXUS",
    "lincoln": "LINCO",     "mazda": "MAZDA",        "mercedes-benz": "MB",
    "mitsubishi": "MITSU",  "nissan": "NISSA",       "porsche": "PORSC",
    "ram": "RAM",           "subaru": "SUBAR",       "tesla": "TESLA",
    "toyota": "TOYOT",      "volkswagen": "VW",      "volvo": "VOLVO",
}

# AutoTrader internal model codes — explicit overrides where auto-derive fails
AT_MODEL_CODE = {
    # Mercedes — letter-class codes (confirmed working with _CLASS suffix)
    "c-class": "C_CLASS",   "e-class": "E_CLASS",   "s-class": "S_CLASS",
    "g-class": "G_CLASS",
    # Mercedes — MB-prefixed codes required (bare names silently ignored by AutoTrader)
    "gla": "MBGLA250",      "glb": "MBGLB250",      "glc": "MBGLC300",
    "gle": "MBGLE450",      "gls": "MBGLS450",
    "cla": "MBCLA250",      "cle": "MBCLE300",      "sl": "MBSL43",
    "amg-gt": "MBAMGGT43",  "eqs": "MBEQS450",      "eqe": "MBEQE350",
    "eqb": "MBEQB300",
    # Honda
    "cr-v": "CRV",          "pilot": "PILOT",        "accord": "ACCORD",
    "civic": "CIVIC",       "odyssey": "ODYSSEY",    "ridgeline": "RDGLN",
    # Toyota
    "rav4": "RAV4",         "camry": "CAMRY",        "4runner": "4RUNNER",
    "highlander": "HIGHLD", "tacoma": "TACOMA",      "tundra": "TUNDRA",
    # BMW
    "x3": "X3",             "x5": "X5",              "x7": "X7",
    "i4": "I4",             "3-series": "3SERIES",
    # GMC
    "sierra-1500": "SIERRA1500",  "sierra-2500": "SIERRA2500",
    "terrain": "TERRAIN",         "acadia": "ACADIA",
    # Chevrolet
    "silverado-1500": "SILVER1500", "tahoe": "TAHOE",
    "equinox": "EQUINOX",           "colorado": "COLORADO",
    "traverse": "TRAVERSE",
    # Ford
    "f-150": "F150",        "explorer": "EXPLOR",    "mustang": "MUSTNG",
    "bronco": "BRONCO",     "maverick": "MAVCK",     "ranger": "RANGER",
    # Jeep
    "grand-cherokee": "GRNDCH",  "wrangler": "WRANGL",  "gladiator": "GLADTR",
    # Tesla
    "model-y": "MODEL_Y",   "model-3": "MODEL_3",    "model-x": "MODEL_X",
    # Hyundai
    "tucson": "TUCSON",     "santa-fe": "SANTFE",    "ioniq-5": "IONIQ5",
    "palisade": "PALSD",
    # Kia
    "telluride": "TELRD",   "sportage": "SPTGE",     "sorento": "SRNTO",
    "carnival": "CRNVL",
    # Audi
    "a4": "A4",             "q5": "Q5",              "a6": "A6",
    "e-tron": "ETRON",
    # Others
    "qx60": "QX60",         "gv70": "GV70",          "cx-5": "CX5",
    "cx-50": "CX50",        "cx-90": "CX90",         "cayenne": "CAYNE",
    "macan": "MACAN",       "taycan": "TAYCAN",      "panamera": "PANAM",
    "xc90": "XC90",         "xc60": "XC60",          "outback": "OUTBCK",
    "forester": "FORSTR",   "crosstrek": "CRSTRK",   "tiguan": "TIGUAN",
    "atlas": "ATLAS",       "jetta": "JETTA",        "aviator": "AVIATR",
    "nautilus": "NAUTLS",   "navigator": "NAVGTR",   "pacifica": "PACFCA",
    "durango": "DURAGO",    "sf90": "SF90",          "lyriq": "LYRIQ",
    "xt5": "XT5",           "enclave": "ENCLVE",     "envision": "ENVSON",
    "outlander": "OUTLD",   "rogue": "ROGUE",        "altima": "ALTIMA",
    "pathfinder": "PATHFDR","frontier": "FRONTR",    "1500": "RAM1500",
    "2500": "RAM2500",      "mdx": "MDX",            "gx": "GX",
    "es": "ES",             "is": "IS",              "tx": "TX",
    "lx": "LX",
}


# Trim-specific MB model codes checked before slug normalization.
# AutoTrader requires MB-prefixed trim codes (e.g. MBGLE450, not GLE).
# Bare class codes like GLE, CLA, AMG_GT are silently ignored by AutoTrader.
_AT_MB_TRIM_CODE = {
    # GL-series SUVs
    "gle 350": "MBGLE350",  "gle 450": "MBGLE450",  "gle 450e": "MBGLE450",
    "gle450e": "MBGLE450",  "gle 53":  "MBGLE53",   "gle 63":   "MBGLE63AMG",
    "glc 300": "MBGLC300",  "glc 300e":"MBGLC300",  "glc300":   "MBGLC300",
    "glc300e": "MBGLC300",  "glc 43":  "MBGLC43",   "glc 63":   "MBGLC63AMG",
    "gls 450": "MBGLS450",  "gls 580": "MBGLS580",  "gls 63":   "MBGLS63AMG",
    "gla 250": "MBGLA250",  "gla250":  "MBGLA250",  "gla 35":   "MBGLA35AMG",
    "gla 45":  "MBGLA45AMG","gla 450": "MBGLA250",
    "glb 250": "MBGLB250",  "glb250":  "MBGLB250",  "glb 35":   "MBGLB35AMG",
    # CLA / CLE
    "cla 250": "MBCLA250",  "cla250":  "MBCLA250",  "cla 35":   "MBCLA35AMG",
    "cla 45":  "MBCLA45AMG","cle 300": "MBCLE300",  "cle 450":  "MBCLE450",
    # SL roadster
    "sl 43":   "MBSL43",    "sl 55":   "MBSL55",    "sl 63":    "MBSL63",
    # AMG GT
    "amg gt 43":"MBAMGGT43","amg gt 53":"MBAMGGT53","amg gt 63":"MBAMGGT63",
    "amg gt 63 s":"MBAMGGT63",
    # EQ electric
    "eqs 450": "MBEQS450",  "eqs 580": "MBEQS580",
    "eqe 350": "MBEQE350",  "eqe 500": "MBEQE500",
    "eqb 250": "MBEQB250",  "eqb 300": "MBEQB300",  "eqb 350": "MBEQB350",
}


def _at_model_code(model: str) -> str:
    """Return AutoTrader modelCodeList value for a given model string."""
    m = model.lower().strip()
    if m in _AT_MB_TRIM_CODE:
        return _AT_MB_TRIM_CODE[m]
    slug = AT_MODEL_SLUG_MAP.get(m, m.replace(" ", "-").replace("/", "-"))
    return AT_MODEL_CODE.get(slug, slug.upper().replace("-", "")) if slug else ""


def at_url(make: str, model: str, condition: str,
           zip_code: str = "", price_max: int = 999999, price_min: int = 0,
           ext_color: str = "", int_color: str = "",
           radius: int = 50, mileage: int = None) -> str:
    """Build an AutoTrader search URL using makeCodeList+modelCodeList query params."""
    make = normalize_make(make)
    cond_seg   = "used-cars" if condition == "Used" else "new-cars" if condition == "New" else "all-cars"
    price_seg  = f"cars-under-{price_max}/" if price_max and price_max < 999000 else ""
    color_seg  = (ext_color.lower().replace(" ", "-") + "/") if ext_color and ext_color.lower() not in ("any", "other", "") else ""
    make_code  = AT_MAKE_CODE.get(make.lower(), make.upper().replace(" ", "_").replace("-", "_"))
    model_code = _at_model_code(model)
    qp = [f"zip={zip_code}"] if zip_code else []
    if radius < 500:   qp.append(f"searchRadius={radius}")
    if make_code:      qp.append(f"makeCodeList={make_code}")
    if model_code:     qp.append(f"modelCodeList={model_code}")
    if price_min:      qp.append(f"startPrice={price_min}")
    if price_max and price_max < 999000: qp.append(f"endPrice={price_max}")
    if mileage:        qp.append(f"maxMileage={mileage}")
    if int_color and int_color.lower() not in ("any", "other", ""):
        qp.append(f"intColorSimple={int_color.upper()}")
    base = f"https://www.autotrader.com/cars-for-sale/{cond_seg}/{price_seg}{color_seg}"
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
    # Cars.com color slug params silently drop models[] when invalid — omit entirely
    return "https://www.cars.com/shopping/results/?" + "&".join(qp)
