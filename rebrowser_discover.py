"""
AT model + trim code discovery via Rebrowser cloud browser.

Connects to Rebrowser's CDP endpoint (residential proxy, undetectable) instead
of a local headless browser that AT blocks. Discovers:

  1. modelCodeList values for every make/model we support
  2. trimCodeList strings for every model (especially Mercedes AMG variants)

Output: at_codes_full.json  — ready-to-paste code blocks printed to console.

Usage:
  1. Add REBROWSER_API_KEY=<your_key> to .env
  2. .venv/bin/python rebrowser_discover.py

To run a single make only (faster for testing):
  .venv/bin/python rebrowser_discover.py --make "Mercedes-Benz"

To discover trims for a specific model:
  .venv/bin/python rebrowser_discover.py --make "Mercedes-Benz" --trims
"""
import argparse
import json
import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

REBROWSER_API_KEY = os.getenv("REBROWSER_API_KEY", "")
# Rebrowser CDP WebSocket endpoint — paste the exact URL from your dashboard if different
REBROWSER_WS = f"wss://ws.rebrowser.net/?apiKey={REBROWSER_API_KEY}"

ZIP    = "92782"
DELAY  = 3.0   # seconds between page navigations (be polite)

MAKES = {
    "Acura":         "acura",
    "Audi":          "audi",
    "BMW":           "bmw",
    "Buick":         "buick",
    "Cadillac":      "cadillac",
    "Chevrolet":     "chevrolet",
    "Chrysler":      "chrysler",
    "Dodge":         "dodge",
    "Ferrari":       "ferrari",
    "Ford":          "ford",
    "Genesis":       "genesis",
    "GMC":           "gmc",
    "Honda":         "honda",
    "Hyundai":       "hyundai",
    "Infiniti":      "infiniti",
    "Jeep":          "jeep",
    "Kia":           "kia",
    "Lexus":         "lexus",
    "Lincoln":       "lincoln",
    "Mazda":         "mazda",
    "Mercedes-Benz": "mercedes-benz",
    "Mitsubishi":    "mitsubishi",
    "Nissan":        "nissan",
    "Porsche":       "porsche",
    "RAM":           "ram",
    "Subaru":        "subaru",
    "Tesla":         "tesla",
    "Toyota":        "toyota",
    "Volkswagen":    "volkswagen",
    "Volvo":         "volvo",
}

MODELS_WE_USE = {
    "Acura":         ["MDX", "RDX", "TLX", "Integra", "ZDX", "ADX"],
    "Audi":          ["A3", "A4", "A4 Allroad", "A5", "A6", "A7", "A8",
                      "Q3", "Q5", "Q7", "Q8", "Q4 e-tron", "Q8 e-tron",
                      "e-tron GT", "TT"],
    "BMW":           ["2 Series", "3 Series", "4 Series", "5 Series",
                      "7 Series", "8 Series", "X1", "X2", "X3", "X4",
                      "X5", "X6", "X7", "i4", "i5", "iX", "Z4",
                      "M3", "M4", "M5"],
    "Buick":         ["Enclave", "Encore GX", "Envision", "Envista"],
    "Cadillac":      ["CT4", "CT5", "XT4", "XT5", "XT6", "Escalade", "Lyriq"],
    "Chevrolet":     ["Blazer", "Blazer EV", "Colorado", "Corvette",
                      "Equinox", "Equinox EV", "Malibu", "Silverado 1500",
                      "Silverado 2500HD", "Silverado 3500HD", "Suburban",
                      "Tahoe", "Trailblazer", "Traverse", "Trax"],
    "Chrysler":      ["Pacifica"],
    "Dodge":         ["Charger", "Durango", "Hornet"],
    "Ferrari":       ["SF90"],
    "Ford":          ["Bronco", "Bronco Sport", "Escape", "Expedition",
                      "Explorer", "F-150", "F-150 Lightning",
                      "F-250 Super Duty", "F-350 Super Duty",
                      "Maverick", "Mustang", "Mustang Mach-E",
                      "Ranger", "Transit Cargo"],
    "Genesis":       ["G70", "G80", "G90", "GV60", "GV70", "GV80",
                      "GV90", "Electrified GV70"],
    "GMC":           ["Acadia", "Canyon", "Hummer EV", "Sierra 1500",
                      "Sierra 2500", "Sierra 3500HD", "Terrain",
                      "Yukon", "Yukon XL"],
    "Honda":         ["Accord", "Accord Hybrid", "Civic", "CR-V",
                      "CR-V Hybrid", "HR-V", "Odyssey", "Passport",
                      "Pilot", "Prologue", "Ridgeline"],
    "Hyundai":       ["Elantra", "Ioniq 5", "Ioniq 6", "Kona",
                      "Palisade", "Santa Cruz", "Santa Fe",
                      "Sonata", "Tucson", "Venue"],
    "Infiniti":      ["Q50", "Q60", "QX50", "QX55", "QX60", "QX80"],
    "Jeep":          ["Compass", "Gladiator", "Grand Cherokee",
                      "Grand Cherokee L", "Wrangler"],
    "Kia":           ["Carnival", "EV6", "EV9", "K5", "Niro",
                      "Seltos", "Sorento", "Soul", "Sportage", "Telluride"],
    "Lexus":         ["ES", "GX", "IS", "LC", "LS", "LX", "NX",
                      "NX Hybrid", "RC", "RX", "RX Hybrid", "RZ",
                      "TX", "UX"],
    "Lincoln":       ["Aviator", "Corsair", "Nautilus", "Navigator"],
    "Mazda":         ["CX-30", "CX-5", "CX-50", "CX-70", "CX-90",
                      "Mazda3", "MX-5 Miata"],
    "Mercedes-Benz": ["C-Class", "C 43", "C 63",
                      "E-Class", "E 53", "E 63",
                      "S-Class", "S 63",
                      "G-Class", "G 63",
                      "CLA", "CLA 35", "CLA 45",
                      "CLE", "CLS", "CLS 53",
                      "GLA", "GLA 35", "GLA 45",
                      "GLB", "GLB 35",
                      "GLC", "GLC 43", "GLC 63",
                      "GLE", "GLE 53", "GLE 63",
                      "GLS", "GLS 63",
                      "AMG GT", "SL", "EQS", "EQE", "EQB",
                      "EQS SUV", "EQE SUV",
                      "Sprinter", "Maybach S", "Maybach GLS"],
    "Mitsubishi":    ["Eclipse Cross", "Outlander"],
    "Nissan":        ["Altima", "Armada", "Ariya", "Frontier", "Kicks",
                      "Leaf", "Maxima", "Murano", "Pathfinder",
                      "Rogue", "Sentra", "Versa", "Z"],
    "Porsche":       ["718 Boxster", "718 Cayman", "911", "Cayenne",
                      "Macan", "Panamera", "Taycan"],
    "RAM":           ["1500", "2500", "3500", "ProMaster"],
    "Subaru":        ["Ascent", "BRZ", "Crosstrek", "Forester",
                      "Impreza", "Legacy", "Outback", "Solterra", "WRX"],
    "Tesla":         ["Cybertruck", "Model 3", "Model S",
                      "Model X", "Model Y"],
    "Toyota":        ["4Runner", "bZ4X", "Camry", "Corolla", "Crown",
                      "GR86", "Highlander", "Land Cruiser", "Prius",
                      "RAV4", "RAV4 Hybrid", "Sequoia", "Sienna",
                      "Tacoma", "Tundra", "Venza"],
    "Volkswagen":    ["Arteon", "Atlas", "Atlas Cross Sport", "Golf",
                      "ID.4", "Jetta", "Taos", "Tiguan"],
    "Volvo":         ["EC40", "EX30", "EX40", "EX90", "S60", "S90",
                      "V60", "V90", "XC40", "XC60", "XC90"],
}


def _extract_code_list(data, depth=0):
    """Recursively find arrays of {label, code} items in any JSON structure."""
    if depth > 12:
        return []
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = set(data[0].keys())
        has_label = bool(keys & {"name", "label", "displayName", "title", "text"})
        has_code  = bool(keys & {"code", "value", "id", "key"})
        if has_label and has_code and len(data) >= 2:
            out = []
            for item in data:
                lk = next((k for k in ("name","label","displayName","title","text") if k in item), None)
                ck = next((k for k in ("code","value","id","key") if k in item), None)
                if lk and ck and item[lk] and item[ck]:
                    out.append({"label": str(item[lk]), "code": str(item[ck])})
            if out:
                return out
        for item in data:
            sub = _extract_code_list(item, depth + 1)
            if sub:
                return sub
    elif isinstance(data, dict):
        for priority in ("models", "modelFacets", "trims", "trimFacets", "modelList", "trimList"):
            if priority in data:
                sub = _extract_code_list(data[priority], depth + 1)
                if sub:
                    return sub
        for v in data.values():
            sub = _extract_code_list(v, depth + 1)
            if sub:
                return sub
    return []


def _best_match(target: str, options: list):
    t = target.lower().replace("-", " ").strip()
    for opt in options:
        if opt["label"].lower().replace("-", " ").strip() == t:
            return opt
    for opt in options:
        label = opt["label"].lower().replace("-", " ").strip()
        if t in label or label.startswith(t):
            return opt
    return None


def _capture_page_options(page, url: str) -> list:
    """Navigate to url, wait for AT's API calls to settle, return all code options found."""
    captured = []

    def on_response(response):
        try:
            if "json" in response.headers.get("content-type", "") and response.status == 200:
                found = _extract_code_list(response.json())
                if found and len(found) >= 2:
                    captured.extend(found)
        except Exception:
            pass

    page.on("response", on_response)
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        print(f"    nav error: {e}")
    finally:
        page.remove_listener("response", on_response)

    # Deduplicate by code
    seen, unique = set(), []
    for opt in captured:
        if opt["code"] not in seen:
            seen.add(opt["code"])
            unique.append(opt)
    return unique


def discover_model_codes(page, make_name: str, make_slug: str) -> dict:
    """Return {model_name: model_code} for all MODELS_WE_USE entries for this make."""
    url = f"https://www.autotrader.com/cars-for-sale/all-cars/{make_slug}/?zip={ZIP}&searchRadius=50"
    print(f"\n{make_name}... ", end="", flush=True)
    options = _capture_page_options(page, url)
    print(f"{len(options)} model options", end="")

    result = {}
    for model in MODELS_WE_USE.get(make_name, []):
        m = _best_match(model, options)
        if m:
            result[model] = m["code"]
        # unmatched → skip silently, printed in summary
    print(f"  ({len(result)}/{len(MODELS_WE_USE.get(make_name,[]))} matched)")
    return result, options


def discover_trim_codes(page, make_slug: str, model_slug: str, model_code: str) -> list:
    """Navigate to a model page and return all trim options AT exposes."""
    url = (f"https://www.autotrader.com/cars-for-sale/all-cars/{make_slug}/{model_slug}/"
           f"?zip={ZIP}&searchRadius=50")
    options = _capture_page_options(page, url)
    return options


def run(filter_make=None, discover_trims=False):
    if not REBROWSER_API_KEY:
        print("ERROR: REBROWSER_API_KEY not set in .env")
        print("Add:  REBROWSER_API_KEY=your_key_here")
        return

    makes_to_run = {k: v for k, v in MAKES.items()
                    if filter_make is None or k.lower() == filter_make.lower()}

    model_codes = {}   # make → {model: code}
    trim_codes  = {}   # make/model → [{"label":..., "code":...}]
    all_options = {}   # make → full options list (for debugging)

    print(f"Connecting to Rebrowser...")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(REBROWSER_WS)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # Warm up — let AT set cookies and recognize the session
        print("Warming up session on autotrader.com...")
        page.goto("https://www.autotrader.com/", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        print(f"  Page title: {page.title()}\n")

        for make_name, make_slug in makes_to_run.items():
            codes, options = discover_model_codes(page, make_name, make_slug)
            model_codes[make_name] = codes
            all_options[make_name] = options
            time.sleep(DELAY)

            if discover_trims and codes:
                trim_codes[make_name] = {}
                for model_name, model_code in codes.items():
                    model_slug = model_name.lower().replace(" ", "-").replace("/", "-")
                    trims = discover_trim_codes(page, make_slug, model_slug, model_code)
                    if trims:
                        trim_codes[make_name][model_name] = trims
                        print(f"    {model_name} trims: {[t['label'] for t in trims[:6]]}")
                    time.sleep(DELAY)

        browser.close()

    # Save full results
    output = {"model_codes": model_codes, "trim_codes": trim_codes, "all_options": all_options}
    with open("at_codes_full.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\n\nSaved → at_codes_full.json")

    # Print ready-to-paste model code block
    print("\n" + "="*65)
    print("# ── Paste into AT_MODEL_CODE in agents/url_helpers.py ───────")
    for make_name, models in model_codes.items():
        if models:
            print(f"\n    # {make_name}")
            for model, code in models.items():
                slug = model.lower().replace(" ", "-").replace("/", "-")
                print(f'    "{slug}": "{code}",')

    # Print unmatched
    unmatched = []
    for make_name, our_models in MODELS_WE_USE.items():
        if make_name not in makes_to_run:
            continue
        found = set(model_codes.get(make_name, {}).keys())
        for m in our_models:
            if m not in found:
                unmatched.append(f"  {make_name} — {m}")
    if unmatched:
        print("\n# ── Still unmatched (check AT_MODEL_SLUG_MAP manually) ──")
        for u in unmatched:
            print(u)

    # Print trim codes for Mercedes AMG variants
    if discover_trims and trim_codes.get("Mercedes-Benz"):
        print("\n# ── Mercedes trim codes (for _AT_MB_TRIM_CODE) ─────────")
        for model, trims in trim_codes["Mercedes-Benz"].items():
            print(f"\n    # {model}")
            for t in trims:
                print(f'    # "{model.lower()} ...": "{t["code"]}",  # {t["label"]}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", help="Run for a single make only (e.g. 'Mercedes-Benz')")
    parser.add_argument("--trims", action="store_true", help="Also discover trim codes per model")
    args = parser.parse_args()
    run(filter_make=args.make, discover_trims=args.trims)
