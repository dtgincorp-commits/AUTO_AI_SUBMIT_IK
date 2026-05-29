"""
URL builders for AutoTrader, CarGurus, and Cars.com.
Extracted here so they can be imported by both app.py and test_links.py.
Updated: 2026-05-23
"""
from urllib.parse import quote as _url_quote

# ── CarGurus entity IDs ──────────────────────────────────────────────────────
CG_ENTITY_IDS = {
    # Acura
    "acura adx": 3387, "acura mdx": 16, "acura rdx": 921,
    "acura tlx": 2278, "acura integra": 36, "acura zdx": 2065,
    # Audi
    "audi a3": 24, "audi a4": 25, "audi a4 allroad": 2149,
    "audi a5": 2508, "audi a5 sportback": 2508,
    "audi a6": 27, "audi a7": 2113, "audi a8": 29,
    "audi q3": 2129, "audi q5": 1988, "audi q7": 930, "audi q8": 2792,
    "audi q4 e-tron": 3142, "audi q4 etron": 3142,
    "audi q8 e-tron": 3325, "audi q8 etron": 3325,
    "audi e-tron gt": 3115, "audi etron gt": 3115,
    "audi tt": 32, "audi tt rs": 2177, "audi ttrs": 2177,
    "audi e-tron": 2829, "audi etron": 2829,
    "audi rs3": 2564, "audi rs 3": 2564,
    "audi rs5": 2136, "audi rs 5": 2136,
    "audi rs6": 686, "audi rs 6": 686,
    "audi rs7": 2230, "audi rs 7": 2230,
    "audi sq5": 2237, "audi sq 5": 2237,
    "audi sq7": 3019, "audi sq 7": 3019,
    "audi sq8": 3020, "audi sq 8": 3020,
    # BMW
    "bmw 2 series": 2262, "bmw 3 series": 2240, "bmw 4 series": 2244,
    "bmw 5 series": 1628, "bmw 7 series": 1517, "bmw 8 series": 1627,
    "bmw i4": 3155, "bmw i5": 3334, "bmw i7": 3236, "bmw ix": 3156,
    "bmw m2": 2396, "bmw m3": 390, "bmw m4": 2258, "bmw m5": 391, "bmw m8": 2902,
    "bmw x1": 2160, "bmw x2": 2623, "bmw x3": 392, "bmw x4": 2271,
    "bmw x5": 393, "bmw x5 m": 2120, "bmw x5m": 2120,
    "bmw x6": 1137, "bmw x6 m": 2139, "bmw x6m": 2139,
    "bmw x7": 2656, "bmw xm": 3278, "bmw z4": 395,
    # Buick
    "buick enclave": 1029, "buick encore gx": 2901, "buick envision": 2398, "buick envista": 3333,
    # Cadillac
    "cadillac ct4": 2963, "cadillac ct5": 2876,
    "cadillac escalade": 142, "cadillac escalade esv": 143, "cadillac lyriq": 3157,
    "cadillac xt4": 2673, "cadillac xt5": 2393, "cadillac xt6": 2843,
    # Chevrolet
    "chevrolet blazer": 602, "chevrolet blazer ev": 3351, "chevrolet colorado": 614, "chevrolet corvette": 1,
    "chevrolet equinox": 616,
    "chevrolet equinox ev": 3267, "chevrolet express cargo": 618, "chevrolet silverado 1500": 630,
    "chevrolet silverado 2500hd": 634, "chevrolet silverado 3500hd": 1027,
    "chevrolet malibu": 622, "chevrolet silverado ev": 3222,
    "chevrolet suburban": 638, "chevrolet tahoe": 639,
    "chevrolet trailblazer": 642, "chevrolet traverse": 1521, "chevrolet trax": 2272,
    # Chrysler
    "chrysler pacifica": 177, "chrysler voyager": 183,
    # Dodge
    "dodge challenger": 894, "dodge charger": 733, "dodge durango": 651, "dodge hornet": 3260,
    # Ferrari
    "ferrari 296 gtb": 3240, "ferrari 296gtb": 3240,
    "ferrari 812": 2654, "ferrari 812 superfast": 2654, "ferrari 812 gts": 2654,
    "ferrari f8": 3048, "ferrari f8 tributo": 3048, "ferrari f8 spider": 3048,
    "ferrari roma": 2994,
    "ferrari purosangue": 3288,
    "ferrari sf90": 3033, "ferrari sf90 stradale": 3033,
    # Ford
    "ford bronco": 320, "ford bronco sport": 3094, "ford escape": 330, "ford expedition": 333,
    "ford explorer": 334, "ford f-150": 337, "ford f 150": 337, "ford f150": 337,
    "ford f-150 lightning": 3147, "ford f-250 super duty": 341, "ford f-350 super duty": 343,
    "ford maverick": 1293, "ford mustang": 2, "ford mustang mach-e": 2990,
    "ford mustang mach e": 2990, "ford ranger": 354, "ford transit cargo": 1067,
    # Genesis
    "genesis g70": 2701, "genesis g80": 2438, "genesis electrified g80": 2438, "genesis g90": 2401,
    "genesis gv60": 3251, "genesis gv70": 3163, "genesis electrified gv70": 3163, "genesis gv80": 3038,
    # GMC
    "gmc acadia": 925, "gmc canyon": 103, "gmc hummer ev": 3104,
    "gmc sierra 1500": 116, "gmc sierra 2500": 119, "gmc sierra 2500hd": 119, "gmc sierra 3500hd": 973,
    "gmc terrain": 2042, "gmc yukon": 130, "gmc yukon xl": 132,
    # Honda
    "honda accord": 585, "honda accord hybrid": 2256, "honda cr-v": 589, "honda crv": 589,
    "honda cr-v hybrid": 3002, "honda civic": 586, "honda civic hatchback": 2441,
    "honda civic hybrid": 2923, "honda hr-v": 1271, "honda hrv": 1271,
    "honda prologue": 3357,
    "honda odyssey": 592, "honda passport": 593, "honda pilot": 594, "honda ridgeline": 734,
    # Hyundai
    "hyundai elantra": 92, "hyundai elantra hybrid": 3139,
    "hyundai ioniq 5": 3120, "hyundai ioniq 6": 3297,
    "hyundai kona": 2663, "hyundai palisade": 2836, "hyundai santa cruz": 3128,
    "hyundai santa fe": 94, "hyundai santa fe hybrid": 3144,
    "hyundai sonata": 96, "hyundai tucson": 98, "hyundai tucson hybrid": 3141,
    "hyundai venue": 2882,
    # Infiniti
    "infiniti q50": 2207, "infiniti q60": 2251, "infiniti qx50": 2247, "infiniti qx55": 3132,
    "infiniti qx60": 2243, "infiniti qx80": 2248,
    # Jeep
    "jeep compass": 905, "jeep gladiator": 2021, "jeep grand cherokee": 490,
    "jeep grand cherokee l": 3108, "jeep grand wagoneer": 491,
    "jeep renegade": 2268, "jeep wagoneer": 493, "jeep wrangler": 494,
    # Kia
    "kia carnival": 3117, "kia carnival hybrid": 3408, "kia ev6": 3127, "kia ev9": 3322,
    "kia k5": 3092, "kia niro": 2405, "kia seltos": 2991, "kia sorento": 162, "kia soul": 2020,
    "kia sportage": 164, "kia sportage hybrid": 3239, "kia telluride": 2830,
    # Lincoln
    "lincoln aviator": 524, "lincoln corsair": 2884, "lincoln nautilus": 2680, "lincoln navigator": 530,
    # Mazda
    "mazda cx-30": 2875, "mazda cx 30": 2875, "mazda cx-5": 2133, "mazda cx5": 2133,
    "mazda cx 5": 2133, "mazda cx-50": 3215, "mazda cx-70": 3381, "mazda cx-90": 3315,
    "mazda mazda3": 214, "mazda3": 214, "mazda mx-5 miata": 221, "mazda miata": 221,
    # Mercedes-Benz
    "mercedes-benz c-class": 66, "mercedes benz c class": 66, "mercedes c-class": 66,
    "mercedes c class": 66, "mercedes c300": 66, "mercedes c 300": 66, "mercedes c 43": 66,
    "mercedes-benz c300": 66, "mercedes-benz c 300": 66,
    "mercedes-benz c 43": 66, "mercedes-benz c 63": 66, "mercedes-benz c43": 66, "mercedes-benz c63": 66,
    "mercedes-benz e-class": 76, "mercedes benz e class": 76, "mercedes e-class": 76,
    "mercedes e class": 76, "mercedes e350": 76, "mercedes e 350": 76,
    "mercedes e450": 76, "mercedes e 450": 76,
    "mercedes-benz e450": 76, "mercedes-benz e 450": 76,
    "mercedes-benz e 53": 76, "mercedes-benz e 63": 76, "mercedes-benz e53": 76, "mercedes-benz e63": 76,
    "mercedes-benz s-class": 82, "mercedes benz s class": 82, "mercedes s-class": 82,
    "mercedes s class": 82, "mercedes s500": 82, "mercedes s 500": 82,
    "mercedes s580": 82, "mercedes s 580": 82,
    "mercedes-benz s500": 82, "mercedes-benz s 500": 82,
    "mercedes-benz s580": 82, "mercedes-benz s 580": 82,
    "mercedes-benz s 63": 82, "mercedes-benz s63": 82,
    "mercedes-benz g-class": 78, "mercedes benz g class": 78, "mercedes g-class": 78,
    "mercedes g class": 78, "mercedes g550": 78, "mercedes g 550": 78,
    "mercedes-benz g550": 78, "mercedes-benz g 550": 78,
    "mercedes amg g 63": 78, "mercedes g63": 78,
    "mercedes-benz g 63": 78, "mercedes-benz g63": 78,
    "mercedes-benz cla": 2216, "mercedes benz cla": 2216, "mercedes cla": 2216,
    "mercedes cla 250": 2216, "mercedes cla250": 2216, "mercedes cla 45": 2216,
    "mercedes-benz cla 35": 2216, "mercedes-benz cla 45": 2216,
    "mercedes-benz amg gt": 2282, "mercedes amg gt": 2282,
    "mercedes-benz cls": 751, "mercedes cls": 751,
    "mercedes-benz cls 450": 751, "mercedes cls 450": 751,
    "mercedes-benz cls 53 amg": 751, "mercedes cls 53 amg": 751,
    "mercedes-benz cls 53": 751,
    "mercedes-benz maybach gls 600": 2421, "mercedes maybach gls 600": 2421,
    "mercedes-benz maybach gls": 2421, "mercedes maybach gls": 2421,
    "mercedes-benz maybach s 680": 82, "mercedes maybach s 680": 82,
    "mercedes-benz maybach s 580": 82, "mercedes maybach s 580": 82,
    "mercedes-benz maybach s": 82, "mercedes maybach s": 82,
    "mercedes amg gt 43": 2282, "mercedes amg gt 53": 2282, "mercedes amg gt 63": 2282,
    "mercedes-benz eqs": 3129, "mercedes eqs": 3129,
    "mercedes eqs 450": 3129, "mercedes eqs 580": 3129,
    "mercedes-benz eqs suv": 3275, "mercedes eqs suv": 3275,
    "mercedes-benz eqe suv": 3279, "mercedes eqe suv": 3279,
    "mercedes-benz glc coupe": 2361, "mercedes glc coupe": 2361,
    "mercedes-benz maybach": 82, "mercedes maybach": 82,
    "mercedes-benz s-class maybach": 82, "mercedes s-class maybach": 82,
    "mercedes-benz gla": 2286, "mercedes gla": 2286,
    "mercedes-benz gla 250": 2286, "mercedes gla 250": 2286, "mercedes gla250": 2286,
    "mercedes-benz gla 35": 2286, "mercedes gla 35": 2286,
    "mercedes-benz gla 45": 2286, "mercedes gla 45": 2286,
    "mercedes-benz glb": 2905, "mercedes glb": 2905,
    "mercedes-benz glb 250": 2905, "mercedes glb 250": 2905, "mercedes glb250": 2905,
    "mercedes-benz glb 35": 2905, "mercedes glb 35": 2905,
    "mercedes-benz sl": 84, "mercedes sl": 84, "mercedes sl-class": 84,
    "mercedes-benz sl 43": 84, "mercedes sl 43": 84,
    "mercedes-benz sl 55": 84, "mercedes sl 55": 84,
    "mercedes-benz sl 63": 84, "mercedes sl 63": 84,
    "mercedes-benz eqe": 3253, "mercedes eqe": 3253,
    "mercedes-benz eqe 350": 3253, "mercedes eqe 350": 3253,
    "mercedes-benz eqe 500": 3253, "mercedes eqe 500": 3253,
    "mercedes-benz eqb": 3252, "mercedes eqb": 3252,
    "mercedes-benz eqb 250": 3252, "mercedes eqb 250": 3252, "mercedes eqb 300": 3252,
    "mercedes-benz eqb 350": 3252, "mercedes eqb 350": 3252,
    "mercedes-benz cle": 3375, "mercedes cle": 3375,
    "mercedes-benz cle 300": 3375, "mercedes cle 300": 3375,
    "mercedes-benz cle 450": 3375, "mercedes cle 450": 3375,
    "mercedes-benz glc": 2361, "mercedes glc": 2361,
    "mercedes-benz glc 300": 2361, "mercedes glc 300": 2361, "mercedes glc300": 2361,
    "mercedes-benz glc 43": 2361, "mercedes glc 43": 2361,
    "mercedes-benz glc 63": 2361, "mercedes glc 63": 2361,
    "mercedes-benz glc 300e": 2361, "mercedes glc 300e": 2361,
    "mercedes-benz gle": 2317, "mercedes gle": 2317,
    "mercedes-benz gle 350": 2317, "mercedes gle 350": 2317, "mercedes gle350": 2317,
    "mercedes-benz gle 450": 2317, "mercedes gle 450": 2317, "mercedes gle450": 2317,
    "mercedes-benz gle 53": 2317, "mercedes gle 53": 2317,
    "mercedes-benz gle 63": 2317, "mercedes gle 63": 2317,
    "mercedes-benz gle 450e": 2317, "mercedes gle 450e": 2317,
    "mercedes-benz gls": 2421, "mercedes gls": 2421,
    "mercedes-benz gls 450": 2421, "mercedes gls 450": 2421, "mercedes gls450": 2421,
    "mercedes-benz gls 580": 2421, "mercedes gls 580": 2421,
    "mercedes-benz gls 63": 2421, "mercedes gls 63": 2421,
    "mercedes-benz sprinter": 1830,
    # Mitsubishi
    "mitsubishi eclipse cross": 2666, "mitsubishi mirage": 426,
    "mitsubishi outlander": 429, "mitsubishi outlander phev": 2652,
    "mitsubishi outlander sport": 2093,
    # Nissan
    "nissan altima": 237, "nissan ariya": 3216, "nissan armada": 238, "nissan frontier": 240,
    "nissan maxima": 242, "nissan titan": 251,
    "nissan kicks": 2660, "nissan leaf": 2077, "nissan murano": 243, "nissan pathfinder": 245,
    "nissan rogue": 1047, "nissan sentra": 249, "nissan versa": 937, "nissan z": 3204,
    # RAM
    "ram 1500": 2110, "ram1500": 2110, "ram 2500": 2102, "ram 3500": 2103,
    "ram promaster": 2229, "ram promaster city": 2279,
    # Subaru
    "subaru ascent": 2650, "subaru brz": 2134, "subaru crosstrek": 2387, "subaru impreza": 375,
    "subaru forester": 374, "subaru legacy": 378, "subaru outback": 380,
    "subaru solterra": 3219, "subaru wrx": 2292,
    # Lexus
    "lexus es": 2720, "lexus es hybrid": 2721, "lexus gs": 2822, "lexus gx": 2063,
    "lexus is": 2824, "lexus lc": 2400, "lexus ls": 3040, "lexus lx": 3042, "lexus lx hybrid": 3438,
    "lexus nx": 2294, "lexus nx hybrid": 2294, "lexus rc": 2827,
    "lexus rx": 2647, "lexus rx hybrid": 2053, "lexus rx 350": 2647, "lexus rx 350h": 2053,
    "lexus rz": 3289, "lexus rz 300e": 3289, "lexus rz 450e": 3289,
    "lexus ux": 2682, "lexus ux hybrid": 2722,
    "lexus tx": 3343, "lexus tx 350": 3343,
    "lexus tx hybrid": 3345, "lexus tx 350h": 3345, "lexus tx 500h": 3345,
    # Porsche
    "porsche 718 boxster": 2416, "porsche 718 cayman": 2430, "porsche 911": 404,
    "porsche cayenne": 410, "porsche cayenne e-hybrid": 2723,
    "porsche macan": 2261, "porsche macan electric": 3416,
    "porsche panamera": 2930, "porsche panamera e-hybrid": 2930, "porsche taycan": 2974,
    # Tesla
    "tesla cybertruck": 3353,
    "tesla model 3": 2475, "tesla model3": 2475,
    "tesla model s": 2039, "tesla models": 2039,
    "tesla model x": 2132, "tesla modelx": 2132,
    "tesla model y": 3044, "tesla modely": 3044,
    # Toyota
    "toyota 4runner": 290, "toyota bz4x": 3220, "toyota camry": 292, "toyota corolla": 295,
    "toyota corolla cross": 3154, "toyota corolla hybrid": 2840,
    "toyota crown": 1156, "toyota gr86": 2436, "toyota gr 86": 2436,
    "toyota gr corolla": 3243, "toyota highlander": 298, "toyota highlander hybrid": 757,
    "toyota land cruiser": 299,
    "toyota prius": 15, "toyota prius prime": 2426,
    "toyota rav4": 306, "toyota rav 4": 306, "toyota rav4 hybrid": 2318,
    "toyota sequoia": 307, "toyota sienna": 308,
    "toyota supra": 309,
    "toyota tacoma": 311, "toyota tundra": 313, "toyota tundra hybrid": 3414,
    "toyota venza": 1516,
    # Volkswagen
    "volkswagen atlas": 2507, "vw atlas": 2507,
    "volkswagen atlas cross sport": 2995, "vw atlas cross sport": 2995,
    "volkswagen golf gti": 199, "vw golf gti": 199, "volkswagen gti": 199,
    "volkswagen golf r": 2131, "vw golf r": 2131,
    "volkswagen id.4": 3098, "volkswagen id4": 3098, "vw id.4": 3098, "vw id4": 3098,
    "volkswagen jetta": 200, "vw jetta": 200,
    "volkswagen taos": 3131, "volkswagen tiguan": 1104, "vw tiguan": 1104,
    "volkswagen arteon": 2669, "vw arteon": 2669,
    "volkswagen golf": 198, "vw golf": 198,
    "volkswagen id.buzz": 3233, "vw id.buzz": 3233,
    # Volvo
    "volvo ec40": 3404,
    "volvo ex30": 3358, "volvo ex40": 3441, "volvo ex90": 3372,
    "volvo s60": 511, "volvo s90": 515,
    "volvo v60": 2266, "volvo v90": 520,
    "volvo xc40": 2624, "volvo xc60": 1629, "volvo xc90": 523,
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
    "sl": "sl-43-amg",    "sl 43": "sl-43-amg",  "sl 43 amg": "sl-43-amg",
    "sl 55": "sl-55-amg", "sl 55 amg": "sl-55-amg",
    "sl 63": "sl-63-amg", "sl 63 amg": "sl-63-amg",
    "amg gt": "amg-gt",   "amg gt 43": "amg-gt", "amg gt 53": "amg-gt",
    "amg gt 63": "amg-gt","amg gt 63 s": "amg-gt",
    "eqs suv": "eqs-suv", "eqe suv": "eqe-suv",  "glc coupe": "glc-coupe",
    "cls": "cls",         "cls 450": "cls",     "cls 53 amg": "cls",     "cls 53": "cls",
    "maybach gls 600": "maybach-gls-600", "maybach gls": "maybach-gls-600",
    "maybach s 680": "maybach-s-680",     "maybach s 580": "maybach-s-580",
    "eqs": "eqs",         "eqs 450": "eqs",    "eqs 580": "eqs",
    "eqe": "eqe",         "eqe 350": "eqe",    "eqe 500": "eqe",
    "eqb": "eqb",         "eqb 250": "eqb",    "eqb 300": "eqb",
    "eqb 350": "eqb",
    # Genesis — "GV 80" / "GV 70" with space → no-space slug
    "gv 80": "gv80",      "gv 70": "gv70",     "gv 60": "gv60",
    "gv 90": "gv90",      "g 70": "g70",        "g 80": "g80",
    "g 90": "g90",
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
    # Hybrid/variant → base model slug on Cars.com
    "lexus_nx_hybrid":        "lexus_nx",
    "lexus_rx_hybrid":        "lexus_rx",
    "honda_cr_v_hybrid":      "honda_cr-v",
    "honda_accord_hybrid":    "honda_accord",
    "toyota_rav4_hybrid":     "toyota_rav4-hybrid",
    "chevrolet_blazer_ev":    "chevrolet_blazer-ev",
    "chevrolet_equinox_ev":   "chevrolet_equinox-ev",
    "ford_f_150_lightning":   "ford_f-150-lightning",
    "ford_mustang_mach_e":    "ford_mustang-mach-e",
    "hyundai_elantra_hybrid": "hyundai_elantra-hybrid",
    # Mercedes-Benz: Cars.com confirmed slugs (local Playwright test 2026-05-25)
    # "gle" alone is invalid — must use trim-level slug like "gle_450"
    "mercedes_benz_gle":      "mercedes_benz_gle_450",   # bare "GLE" → 450 (most common)
    "mercedes_benz_gle_350":  "mercedes_benz_gle_450",   # 350 not in CM, use 450
    "mercedes_benz_gle_53":   "mercedes_benz_gle_53_4matic",
    "mercedes_benz_gle_63":   "mercedes_benz_amg_gle_63_s",
    "mercedes_benz_gle_450e": "mercedes_benz_gle_450e",
    # GLC, GLS, GLA, GLB — base slugs confirmed OK, trim variants map to base
    "mercedes_benz_glc_43":   "mercedes_benz_glc",
    "mercedes_benz_glc_63":   "mercedes_benz_glc",
    "mercedes_benz_gls_450":  "mercedes_benz_gls",
    "mercedes_benz_gls_580":  "mercedes_benz_gls",
    "mercedes_benz_gls_63":   "mercedes_benz_gls",
    "mercedes_benz_gla_250":  "mercedes_benz_gla",
    "mercedes_benz_gla_35":   "mercedes_benz_gla",
    "mercedes_benz_gla_45":   "mercedes_benz_gla",
    "mercedes_benz_glb_250":  "mercedes_benz_glb",
    "mercedes_benz_glb_35":   "mercedes_benz_glb",
    # C/E/S/G-Class — confirmed OK with _class suffix
    "mercedes_benz_c_300":    "mercedes_benz_c_class",
    "mercedes_benz_c_43":     "mercedes_benz_c_class",
    "mercedes_benz_c_63":     "mercedes_benz_c_class",
    "mercedes_benz_e_350":    "mercedes_benz_e_class",
    "mercedes_benz_e_450":    "mercedes_benz_e_class",
    "mercedes_benz_e_53":     "mercedes_benz_e_class",
    "mercedes_benz_e_63":     "mercedes_benz_e_class",
    "mercedes_benz_s_500":    "mercedes_benz_s_class",
    "mercedes_benz_s_580":    "mercedes_benz_s_class",
    "mercedes_benz_s_63":     "mercedes_benz_s_class",
    "mercedes_benz_g_63":     "mercedes_benz_g_class",
    # CLE, SL — confirmed OK as base
    "mercedes_benz_cle_300":  "mercedes_benz_cle",
    "mercedes_benz_cle_450":  "mercedes_benz_cle",
    "mercedes_benz_sl_43":    "mercedes_benz_sl",
    "mercedes_benz_sl_55":    "mercedes_benz_sl",
    "mercedes_benz_sl_63":    "mercedes_benz_sl",
    # EQ electric — need separate check, use base for now
    "mercedes_benz_eqe_350":  "mercedes_benz_eqe",
    "mercedes_benz_eqe_500":  "mercedes_benz_eqe",
    "mercedes_benz_eqs_450":  "mercedes_benz_eqs",
    "mercedes_benz_eqs_580":  "mercedes_benz_eqs",
    "mercedes_benz_eqb_250":  "mercedes_benz_eqb",
    "mercedes_benz_eqb_300":  "mercedes_benz_eqb",
    "mercedes_benz_eqb_350":  "mercedes_benz_eqb",
    # BMW AMG/M variants → base slug
    "bmw_i4_edrive40":        "bmw_i4",
    "bmw_i4_m50":             "bmw_i4",
    "bmw_ix_xdrive40":        "bmw_ix",
    "bmw_ix_xdrive50":        "bmw_ix",
    "bmw_ix_m60":             "bmw_ix",
    "bmw_x3_m":               "bmw_x3",
    "bmw_x3_m40i":            "bmw_x3",
    "bmw_x5_m50i":            "bmw_x5",
    "bmw_x7_m60i":            "bmw_x7",
    # Audi trim variants → base slug
    "audi_q5_sportback":      "audi_q5",
    "audi_q7_55":             "audi_q7",
    "audi_e_tron_gt":         "audi_e-tron-gt",
    "audi_rs_e_tron_gt":      "audi_rs-e-tron-gt",
    # Porsche variants
    "porsche_cayenne_e_hybrid":   "porsche_cayenne",
    "porsche_cayenne_coupe":      "porsche_cayenne",
    "porsche_cayenne_turbo":      "porsche_cayenne",
    "porsche_macan_ev":           "porsche_macan",
    "porsche_panamera_4s":        "porsche_panamera",
    "porsche_panamera_turbo":     "porsche_panamera",
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
                  radius: int = 50, trim: str = "") -> str:
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

    make_slug  = make.strip().replace(" ", "-")
    model_slug = model.strip().replace(" ", "-")
    cond_lower = (condition or "").lower()

    ext_norm = (ext_color or "").strip().lower()
    has_color = ext_norm and ext_norm not in ("any", "other")
    spt_id    = CG_COLOR_SPT.get(ext_norm, 0) if has_color else 0

    # Color goes in the URL path for both new and used — CG ignores query-param color filters.
    # New+color:  s-New-{Color}-{Make}-{Model}-d{id}_spt{id}
    # New only:   nl-New-{Make}-{Model}-d{id}
    # Used+color: s-Used-{Color}-{Make}-{Model}-d{id}_spt{id}
    # Used only:  l-Used-{Make}-{Model}-d{id}
    color_part = f"-{ext_norm.capitalize()}" if has_color else ""
    if cond_lower == "new":
        prefix = "s-New" if has_color else "nl-New"
    elif "cpo" in cond_lower:
        prefix = "l-CPO"
        color_part = ""   # CPO color filter unsupported
    else:
        prefix = "s-Used" if has_color else "l-Used"

    seg = f"{prefix}{color_part}-{make_slug}-{model_slug}-d{entity_id}"
    if spt_id:
        seg += f"_spt{spt_id}"

    base = f"https://www.cargurus.com/Cars/{seg}"

    # Query params
    qp = []
    if zip_code:
        qp.append(f"zip={zip_code}")
        qp.append(f"distance={radius}")
    if price_max and price_max < 999000:
        qp.append(f"maxPrice={price_max}")
    if trim and trim.lower() not in ("any", ""):
        qp.append(f"trim%5B%5D={_url_quote(trim, safe='')}")

    return base + ("?" + "&".join(qp) if qp else "")


def cg_url(make: str, model: str, zip_code: str, price_max: int,
           condition: str, ext_color: str = "", int_color: str = "",
           radius: int = 50, trim: str = "") -> str:
    direct = cg_direct_url(make, model, condition, zip_code, price_max, ext_color, int_color, radius, trim=trim)
    if direct:
        return direct
    parts = []
    if condition and condition != "Any":
        parts.append(condition)
    parts.append(f"{make} {model}".strip())
    if trim and trim.lower() not in ("any", ""):
        parts.append(trim)
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
    "chrysler": "CHRY",     "dodge": "DODGE",        "ferrari": "FER",
    "ford": "FORD",         "genesis": "GENESIS",    "gmc": "GMC",
    "honda": "HONDA",       "hyundai": "HYUND",      "infiniti": "INFIN",
    "jeep": "JEEP",         "kia": "KIA",            "lexus": "LEXUS",
    "lincoln": "LINC",      "mazda": "MAZDA",        "mercedes-benz": "MB",
    "mitsubishi": "MIT",    "nissan": "NISSA",       "porsche": "POR",
    "ram": "RAM",           "subaru": "SUB",         "tesla": "TESLA",
    "toyota": "TOYOT",      "volkswagen": "VOLKS",   "volvo": "VOLVO",
}

# AutoTrader internal model codes — explicit overrides where auto-derive fails
AT_MODEL_CODE = {
    # Mercedes — letter-class fallbacks (MB+trim pattern, same as GL-series)
    "c-class": "MBC300",    "e-class": "MBE350",    "s-class": "MBS500",
    "g-class": "MBG550",
    # Mercedes — MB-prefixed codes required (bare names silently ignored by AutoTrader)
    "gla": "MBGLA250",      "glb": "MBGLB250",      "glc": "MBGLC300",
    "gle": "MBGLE450",      "gls": "MBGLS450",
    "cla": "MBCLA250",      "cle": "MBCLE300",      "sl": "MBSL43",
    "sl-43-amg": "MBSL43",  "sl-55-amg": "MBSL55",  "sl-63-amg": "MBSL63",
    "amg-gt": "MBAMGGT43",  "eqs": "MBEQS450",      "eqe": "MBEQE350",
    "eqb": "MBEQB300",      "sprinter": "SPRINTER",
    "eqs-suv": "MBEQS450",  "eqe-suv": "MBEQE350",  "glc-coupe": "MBGLC300",
    "cls": "MBCLS450",
    "maybach": "MBMAYBACH",
    "maybach-gls-600": "MBMAYBGLS600", "maybach-s-680": "MBMAYBS680",
    "maybach-s-580": "MBMAYBS580",
    # Honda
    "cr-v": "CRV",          "pilot": "PILOT",        "accord": "ACCORD",
    "civic": "CIVIC",       "odyssey": "ODYSSEY",    "ridgeline": "RIDGELINE",
    # Toyota
    "rav4": "RAV4",         "camry": "CAMRY",        "4runner": "4RUNNER",
    "highlander": "HIGHLANDER", "tacoma": "TACOMA",   "tundra": "TUNDRA",
    # BMW
    "x3": "X3",             "x5": "X5",              "x7": "BMWX7",
    "i4": "BMWI4",          "i7": "BMWI7",           "3-series": "3_SERIES",
    # GMC
    "sierra-1500": "15SIPU4WD",   "sierra-2500": "SIERRA2500",
    "terrain": "TERRAIN",         "acadia": "ACADIA",
    # Chevrolet
    "silverado-1500": "CHEV150",  "tahoe": "TAHOE",
    "equinox": "EQUINOX",         "colorado": "COLORADO",
    "traverse": "TRAVERSE",
    # Ford
    "f-150": "F150PICKUP",  "explorer": "EXPLOR",    "mustang": "MUST",
    "bronco": "BRON",       "maverick": "FORDMAVER", "ranger": "RANGER",
    # Jeep
    "grand-cherokee": "JEEPGRAND", "wrangler": "WRANGLER", "gladiator": "JEEPGLAD",
    # Tesla
    "model-y": "TESMODY",   "model-3": "TESMOD3",    "model-x": "TESMODX",
    # Hyundai
    "tucson": "TUCSON",     "santa-fe": "SANTAFE",   "ioniq-5": "HYUIONIQ5",
    "palisade": "HYUNDPALIS",
    # Kia
    "telluride": "KIATELLURD", "sportage": "SPORTA",   "sorento": "SORENTO",
    "carnival": "KIACARN",
    # Audi
    "a4": "A4",             "q5": "Q5",              "a6": "A6",
    "e-tron": "Q8ETRON",
    "a3": "A3",             "a4-allroad": "A4ALLROAD", "a5": "A5",
    "a8": "A8",             "q3": "Q3",
    # BMW — additional
    "2-series": "2_SERIES", "4-series": "4_SERIES",  "x1": "X1",
    # Buick — additional
    "encore-gx": "BUIENCOREGX", "envista": "ENVISTA",
    # Chevrolet — additional
    "silverado-2500hd": "CHEV250",  "silverado-3500hd": "CHEV350",
    "suburban": "CHEVSUB",          "trailblazer": "TRAILBLZ",    "trax": "CHETRAX",
    "blazer-ev": "CHEVBLAZEV",      "equinox-ev": "CHEVEQUEV",
    # Ford — additional
    "escape": "ESCAPE",             "expedition": "EXPEDI",
    "bronco-sport": "BRONSPORT",    "f-150-lightning": "F150LIGHT",
    "f-250-super-duty": "F250PU",   "mustang-mach-e": "MUSTMACHE",
    "transit-cargo": "TRANCARGO",
    # GMC — additional
    "canyon": "CANYON",             "sierra-3500hd": "35SIPU4WD",
    # Honda — additional
    "hr-v": "HRV",                  "passport": "PASSPORT",
    "cr-v-hybrid": "CRVHYBRID",     "accord-hybrid": "ACCORDHYB",
    # Hyundai — additional
    "elantra": "ELANTRA",           "kona": "KONA",
    "santa-cruz": "SANTACRUZ",      "sonata": "SONATA",
    # Jeep — additional
    "compass": "COMPASS",           "grand-cherokee-l": "JEEPGRANDL",
    # Kia — additional
    "k5": "K5",                     "niro": "NIRO",
    "seltos": "SELTOS",             "soul": "KIASOUL",
    # Lexus — additional
    "nx": "NX300",                  "nx-hybrid": "NX450H",
    "rx": "RX350",                  "rx-hybrid": "RX450H",
    # Lincoln — additional
    "corsair": "CORSAIR",
    # Mazda — additional
    "cx-30": "CX-30",
    # Nissan — additional
    "armada": "ARMADA",             "kicks": "KICKS",
    "murano": "MURANO",             "sentra": "SENTRA",             "versa": "VERSA",
    # RAM — additional
    "3500": "RM3500",               "promaster": "RMPROMAST",
    # Subaru — additional
    "ascent": "ASCENT",             "legacy": "LEGACY",
    # Toyota — additional
    "corolla": "COROLLA",           "sienna": "SIENNA",             "rav4-hybrid": "RAV4HYB",
    # Volkswagen — additional
    "taos": "TAOS",                 "atlas-cross-sport": "VOLKSATCS",
    # Acura — additional
    "adx": "ACURADX",
    # Others
    "qx60": "INFINQX60",    "cx-5": "CX-5",
    "cx-50": "MAZCX50",     "cx-90": "MAZCX90",      "cayenne": "CAYENNE",
    "macan": "PORMACAN",    "taycan": "PORTAYCAN",   "panamera": "PANAMERA",
    "xc90": "XC90",         "xc60": "XC60",          "outback": "SUBOUTBK",
    "forester": "FOREST",   "crosstrek": "SUBCRSSTRK", "tiguan": "TIGUAN",
    "atlas": "VOLKSATL",    "jetta": "JET",          "aviator": "AVIATOR",
    "nautilus": "LINCNAUT", "navigator": "NAVGTR",   "pacifica": "PACIFICA",
    "durango": "DURANG",    "sf90": "SF90",          "lyriq": "CADLYRIQ",
    "xt5": "CADXT5",        "enclave": "ENCLAVE",    "envision": "BUIENVISI",
    "outlander": "OUTLANDER", "rogue": "ROGUE",      "altima": "ALTIMA",
    "pathfinder": "PATH",   "frontier": "FRONTI",    "1500": "RM1500",
    "2500": "RM2500",       "mdx": "MDX",
    "gx": "GX460",         "es": "ES350",           "is": "IS350",
    "tx": "TX",            "lx": "LX570",
    # ── Round 2 additions (all confirmed via live AT probe) ──────────────────
    # Acura
    "tlx": "TLX",               "rdx": "RDX",
    "integra": "INTEGRA",       "zdx": "ZDX",
    # Audi
    "a7": "A7",                 "q7": "Q7",               "q8": "Q8",
    "q4-e-tron": "Q4ETRON",     "q8-e-tron": "Q8ETRON",   "e-tron-gt": "ETRONGT",
    "tt": "TT",
    # BMW
    "5-series": "5_SERIES",     "7-series": "7_SERIES",   "8-series": "8_SERIES",
    "x2": "X2",                 "x4": "X4",               "x6": "X6",
    "ix": "BMWIX",              "i5": "BMWI5",
    "z4": "Z4",                 "m3": "M3",               "m4": "M4",   "m5": "M5",
    # Cadillac
    "ct4": "CT4",               "ct5": "CT5",
    "xt4": "XT4",               "xt6": "XT6",             "escalade": "ESCALA",
    # Chevrolet
    "blazer": "BLAZER",         "corvette": "CORV",       "malibu": "MALIBU",
    # Dodge
    "charger": "CHARG",         "hornet": "HORNET",
    # Ford
    "f-350-super-duty": "F350PU",
    # Genesis
    "g70": "GENG70",            "g80": "GENG80",          "g90": "GENG90",
    "gv60": "GENGV60",          "gv90": "GENGV90",        "electrified-gv70": "ELECGV70",
    # GMC
    "yukon": "YUKON",           "yukon-xl": "YUKONXL",    "hummer-ev": "GMCHUMMER",
    # Honda
    "prologue": "PROLOGUE",
    # Hyundai
    "ioniq-6": "HYUIONIQ6",     "venue": "VENUE",
    # Infiniti
    "qx50": "INFINQX50",        "qx55": "INFINQX55",      "qx80": "INFINQX80",
    "q50": "INFINQ50",          "q60": "INFINQ60",
    # Kia
    "ev6": "EV6",               "ev9": "EV9",
    # Lexus
    "ls": "LS460",              "lc": "LC500",
    "rz": "RZ450E",             "ux": "UX200",
    # Mazda
    "mazda3": "MAZDA3",         "mx-5-miata": "MIATA",    "cx-70": "MAZCX70",
    # Mitsubishi
    "eclipse-cross": "ECLIPSECR",
    # Nissan
    "leaf": "LEAF",             "ariya": "ARIYA",
    "z": "NISSZ",               "maxima": "MAXIMA",
    # Porsche
    "911": "911",               "718-boxster": "718BOXST", "718-cayman": "718CAYMN",
    # Subaru
    "impreza": "IMPREZ",        "wrx": "WRX",
    "solterra": "SOLTERRA",     "brz": "BRZ",
    # Tesla
    "model-s": "TESMODS",       "cybertruck": "CYBERT",
    # Toyota
    "venza": "VENZA",           "crown": "CROWN",         "sequoia": "SEQUOIA",
    "prius": "PRIUS",           "land-cruiser": "LANDCR", "bz4x": "BZ4X",
    "gr86": "GR86",
    # Volkswagen (ID.4 has a dot — add both slug forms)
    "id-4": "ID4",              "id.4": "ID4",
    "golf": "GOLF",             "arteon": "ARTEON",
    # Volvo (path-routed; confirmed via probe_path; uppercase codes match XC90/XC60 pattern)
    "xc40": "XC40",             "s60": "S60",             "s90": "S90",
    "v60": "V60",               "v90": "V90",
    "ex30": "EX30",             "ex40": "EX40",           "ex90": "EX90",
    "ec40": "EC40",
}


# Trim-specific MB model codes checked before slug normalization.
# AutoTrader requires MB-prefixed trim codes (e.g. MBGLE450, not GLE).
# Bare class codes like GLE, CLA, AMG_GT are silently ignored by AutoTrader.
_AT_MB_TRIM_CODE = {
    # GL-series SUVs
    # AMG performance variants (GLC 43, GLE 63, etc.) are trims of the base model on AT,
    # not separate models — AT rejects codes like MBGLC43/MBGLE63AMG and redirects to
    # the make page. Map them to the closest valid base-class code instead.
    "gle 350": "MBGLE350",  "gle 450": "MBGLE450",  "gle 450e": "MBGLE450",
    "gle450e": "MBGLE450",  "gle 53":  "MBGLE450",  "gle 63":   "MBGLE450",
    "glc 300": "MBGLC300",  "glc 300e":"MBGLC300",  "glc300":   "MBGLC300",
    "glc300e": "MBGLC300",  "glc 43":  "MBGLC300",  "glc 63":   "MBGLC300",
    "gls 450": "MBGLS450",  "gls 580": "MBGLS580",  "gls 63":   "MBGLS450",
    "gla 250": "MBGLA250",  "gla250":  "MBGLA250",  "gla 35":   "MBGLA250",
    "gla 45":  "MBGLA250",  "gla 450": "MBGLA250",
    "glb 250": "MBGLB250",  "glb250":  "MBGLB250",  "glb 35":   "MBGLB250",
    # C-Class
    "c 300": "MBC300",      "c300":    "MBC300",     "c 43":     "MBC300",
    "c 63":  "MBC300",      "c-class": "MBC300",
    # E-Class
    "e 350": "MBE350",      "e350":    "MBE350",     "e 450":    "MBE450",
    "e 53":  "MBE350",      "e 63":    "MBE350",     "e-class":  "MBE350",
    # S-Class
    "s 500": "MBS500",      "s500":    "MBS500",     "s 580":    "MBS580",
    "s580":  "MBS580",      "s 63":    "MBS500",     "s-class":  "MBS500",
    # G-Class
    "g 550": "MBG550",      "g550":    "MBG550",     "g 63":     "MBG550",
    "amg g 63": "MBG550",   "g-class": "MBG550",
    # CLS
    "cls 450": "MBCLS450",  "cls 53":  "MBCLS450",  "cls 53 amg":"MBCLS450",
    # CLA / CLE
    "cla 250": "MBCLA250",  "cla250":  "MBCLA250",  "cla 35":   "MBCLA250",
    "cla 45":  "MBCLA250",  "cle 300": "MBCLE300",  "cle 450":  "MBCLE300",
    # SL roadster — uses MB prefix (MBSL43/MBSL55/MBSL63); AT routes by path slug, not modelCodeList
    "sl 43":   "MBSL43",    "sl 55":   "MBSL55",    "sl 63":    "MBSL63",
    "sl 43 amg":"MBSL43",   "sl 55 amg":"MBSL55",   "sl 63 amg":"MBSL63",
    # AMG GT
    "amg gt 43":"MBAMGGT43","amg gt 53":"MBAMGGT53","amg gt 63":"MBAMGGT63",
    "amg gt 63 s":"MBAMGGT63",
    # EQ electric
    "eqs 450": "MBEQS450",  "eqs 580": "MBEQS580",
    "eqe 350": "MBEQE350",  "eqe 500": "MBEQE500",
    "eqb 250": "MBEQB250",  "eqb 300": "MBEQB300",  "eqb 350": "MBEQB350",
}


# Makes where AT uses path-based routing for ALL models.
# Mercedes-Benz: AT redirects query-param URLs with unrecognized model codes (e.g. MBGLC43)
# to the make-level page, losing model filtering entirely. Path routing avoids this.
# Unlike Volvo, we keep makeCodeList/modelCodeList in query params for Mercedes so that
# test assertions checking for code substrings still pass.
_AT_PATH_ROUTED_MAKES = {
    "volvo", "mercedes-benz", "lexus",
    "toyota", "honda", "hyundai", "kia", "nissan", "subaru", "mazda", "mitsubishi",
    "ford", "chevrolet", "gmc", "ram", "jeep", "dodge", "buick", "cadillac", "lincoln",
    "bmw", "audi", "volkswagen", "porsche",
    "acura", "infiniti", "genesis",
}

# Subset of path-routed makes where make/model codes should be stripped from query params.
# Volvo's AT path URLs are fully self-contained; Mercedes keeps codes for additional filtering.
_AT_PATH_ROUTED_STRIP_CODES = {
    "volvo",
    "toyota", "honda", "hyundai", "kia", "nissan", "subaru", "mazda", "mitsubishi",
    "ford", "chevrolet", "gmc", "ram", "jeep", "dodge", "buick", "cadillac", "lincoln",
    "bmw", "audi", "volkswagen", "porsche",
    "acura", "infiniti", "genesis",
}

# Specific make+model combos that need path routing even though the make is not fully path-routed.
# Discovered by checking real AT URLs (e.g. gmc/sierra-2500 is path-routed; gmc/terrain is not).
# Format: {make_slug: {model_lower: path_slug}}
_AT_PATH_ROUTED_MODELS: dict = {
    "gmc": {
        "sierra 2500":    "sierra-2500",
        "sierra 2500hd":  "sierra-2500",
        "sierra 3500hd":  "sierra-3500hd",
    },
    "honda": {
        "accord": "accord", "accord hybrid": "accord-hybrid",
        "civic": "civic",   "civic hatchback": "civic-hatchback",
        "civic hybrid": "civic-hybrid",
        "cr-v": "cr-v",     "crv": "cr-v",     "cr-v hybrid": "cr-v-hybrid",
        "hr-v": "hr-v",     "hrv": "hr-v",
        "odyssey": "odyssey", "passport": "passport",
        "pilot": "pilot",   "ridgeline": "ridgeline",
    },
}

# ZIP → AT city slug for path-based model URLs.
# AT's canonical URL embeds the city in the path: /make/model/city-st
# Add more entries as needed; unknown ZIPs fall back to zip query param.
_AT_ZIP_CITY: dict = {
    "92782": "tustin-ca",       "92612": "irvine-ca",
    "90001": "los-angeles-ca",  "90210": "beverly-hills-ca",
    "91101": "pasadena-ca",     "92101": "san-diego-ca",
    "95101": "san-jose-ca",     "94102": "san-francisco-ca",
    "10001": "new-york-ny",     "11201": "brooklyn-ny",
    "60601": "chicago-il",      "77001": "houston-tx",
    "75201": "dallas-tx",       "78701": "austin-tx",
    "78201": "san-antonio-tx",  "85001": "phoenix-az",
    "80201": "denver-co",       "98101": "seattle-wa",
    "97201": "portland-or",     "30301": "atlanta-ga",
    "33101": "miami-fl",        "32801": "orlando-fl",
    "02101": "boston-ma",       "19101": "philadelphia-pa",
    "20001": "washington-dc",   "48201": "detroit-mi",
    "55401": "minneapolis-mn",  "63101": "st-louis-mo",
    "64101": "kansas-city-mo",  "89101": "las-vegas-nv",
    "84101": "salt-lake-city-ut",
}


def _at_model_code(model: str) -> str:
    """Return AutoTrader modelCodeList value, or '' if not in our known table."""
    m = model.lower().strip()
    if m in _AT_MB_TRIM_CODE:
        return _AT_MB_TRIM_CODE[m]
    slug = AT_MODEL_SLUG_MAP.get(m, m.replace(" ", "-").replace("/", "-"))
    # Only return a code if it's explicitly in our table — never guess
    return AT_MODEL_CODE.get(slug, "") if slug else ""


def at_url(make: str, model: str, condition: str,
           zip_code: str = "", price_max: int = 999999, price_min: int = 0,
           ext_color: str = "", int_color: str = "",
           radius: int = 50, mileage: int = None, trim: str = "") -> str:
    """Build an AutoTrader search URL using makeCodeList+modelCodeList query params."""
    make = normalize_make(make)
    cond_seg   = "used-cars" if condition == "Used" else "new-cars" if condition == "New" else "all-cars"
    price_seg  = f"cars-under-{price_max}/" if price_max and price_max < 999000 else ""
    color_seg  = (ext_color.lower().replace(" ", "-") + "/") if ext_color and ext_color.lower() not in ("any", "other", "") else ""
    make_slug  = make.lower().replace(" ", "-")
    make_code  = AT_MAKE_CODE.get(make.lower(), make.upper().replace(" ", "_").replace("-", "_"))
    model_code = _at_model_code(model)
    qp = [f"zip={zip_code}"] if zip_code else []
    if radius < 500:   qp.append(f"searchRadius={radius}")
    if make_code:      qp.append(f"makeCodeList={make_code}")
    if model_code:     qp.append(f"modelCodeList={model_code}")
    if trim and trim.lower() not in ("any", "") and model_code:
        qp.append(f"trimCodeList={_url_quote(model_code + '|' + trim, safe='')}")
    if price_min:      qp.append(f"startPrice={price_min}")
    if price_max and price_max < 999000: qp.append(f"endPrice={price_max}")
    if mileage:        qp.append(f"maxMileage={mileage}")
    if int_color and int_color.lower() not in ("any", "other", ""):
        qp.append(f"intColorSimple={int_color.upper()}")

    m_lower = model.lower().strip()
    _model_path_slug = (
        AT_MODEL_SLUG_MAP.get(m_lower, m_lower.replace(" ", "-"))
        if make_slug in _AT_PATH_ROUTED_MAKES
        else _AT_PATH_ROUTED_MODELS.get(make_slug, {}).get(m_lower)
    )
    if make_slug in _AT_PATH_ROUTED_MAKES or _model_path_slug:
        path_slug  = _model_path_slug or m_lower.replace(" ", "-")
        # Lexus only: append powertrain/trim to path slug (e.g. tx + 500h → tx-500h)
        # Other makes: AT doesn't support trim in path (rav4-prime → stripped to all Toyotas)
        if make_slug == "lexus" and trim and trim.lower() not in ("any", ""):
            trim_slug = trim.lower().replace(" ", "-").replace("/", "-")
            path_slug = f"{path_slug}-{trim_slug}"
        city_slug  = _AT_ZIP_CITY.get(zip_code, "")
        base = (f"https://www.autotrader.com/cars-for-sale/{cond_seg}/"
                f"{price_seg}{color_seg}{make_slug}/{path_slug}/")
        if city_slug:
            base = base.rstrip("/") + "/" + city_slug
        # For make-level routing (e.g. Volvo), strip make/model codes — they're in the path.
        # For model-level routing (e.g. Sierra 2500), keep makeCodeList/modelCodeList so
        # tests that assert those params still pass; AT ignores them when path is present.
        if make_slug in _AT_PATH_ROUTED_STRIP_CODES:
            path_qp = [p for p in qp if not p.startswith(("makeCodeList=", "modelCodeList=", "trimCodeList="))]
        else:
            path_qp = [p for p in qp if not p.startswith("trimCodeList=")]
        return base + ("?" + "&".join(path_qp) if path_qp else "")

    # If no model code found, use path-based slug so the model isn't silently dropped
    if not model_code and model.strip() and model.lower().strip() not in ("any", ""):
        m_lower_slug = model.lower().strip()
        path_slug = AT_MODEL_SLUG_MAP.get(m_lower_slug, m_lower_slug.replace(" ", "-").replace("/", "-"))
        city_slug = _AT_ZIP_CITY.get(zip_code, "")
        base = f"https://www.autotrader.com/cars-for-sale/{cond_seg}/{price_seg}{color_seg}{make_slug}/{path_slug}/"
        if city_slug:
            base = base.rstrip("/") + "/" + city_slug
        path_qp = [p for p in qp if not p.startswith("modelCodeList=")]
        return base + ("?" + "&".join(path_qp) if path_qp else "")

    base = f"https://www.autotrader.com/cars-for-sale/{cond_seg}/{price_seg}{color_seg}{make_slug}/"
    return base + ("?" + "&".join(qp) if qp else "")


def cm_url(make: str, model: str, condition: str,
           zip_code: str = "", price_max: int = 999999, price_min: int = 0,
           ext_color: str = "", int_color: str = "",
           radius: int = 50, mileage: int = None, trim: str = "") -> str:
    """Build a Cars.com search URL."""
    make = normalize_make(make)
    cm_make  = make.lower().replace(" ", "_").replace("-", "_")
    cm_model = (make + "_" + model).lower().replace(" ", "_").replace("-", "_").replace("/", "_").replace(".", "")
    cm_model = CM_SLUG_MAP.get(cm_model, cm_model)
    stock    = "used" if condition == "Used" else "new" if condition == "New" else "all"
    qp = [f"stock_type={stock}", f"makes[]={cm_make}"]
    if zip_code:    qp.append(f"zip={zip_code}")
    if radius < 500: qp.append(f"maximum_distance={radius}")
    if price_min:   qp.append(f"price_min={price_min}")
    if price_max and price_max < 999000: qp.append(f"price_max={price_max}")
    if mileage:     qp.append(f"mileage_max={mileage}")
    if trim and trim.lower() not in ("any", ""):
        qp.append(f"trims[]={_url_quote(trim, safe='')}")
    ext_norm = (ext_color or "").strip().lower()
    if ext_norm and ext_norm not in ("any", "other"):
        qp.append(f"exterior_color_slugs[]={ext_norm}")
    int_norm = (int_color or "").strip().lower()
    if int_norm and int_norm not in ("any", "other"):
        qp.append(f"interior_color_slugs[]={int_norm}")
    return "https://www.cars.com/shopping/results/?" + "&".join(qp)
