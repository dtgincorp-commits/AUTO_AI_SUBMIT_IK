"""
AT / CarGurus / Cars.com code discovery via Rebrowser cloud browser.

Connects to Rebrowser's CDP endpoint (residential proxy, undetectable) instead
of a local headless browser that AT/CG/CM blocks. Discovers:

  1. (AT)  modelCodeList + trimCodeList values for every make/model we support
  2. (CG)  entityId numeric codes for CarGurus model URLs
  3. (CM)  slug correctness verification for Cars.com model URLs

Output: at_codes_full.json  — ready-to-paste code blocks printed to console.

Usage:
  1. Add REBROWSER_API_KEY=<your_key> to .env
  2. .venv/bin/python rebrowser_discover.py            # all three sites
     .venv/bin/python rebrowser_discover.py --at       # AutoTrader only
     .venv/bin/python rebrowser_discover.py --cg       # CarGurus only
     .venv/bin/python rebrowser_discover.py --cm       # Cars.com only
     .venv/bin/python rebrowser_discover.py --make "Mercedes-Benz" --trims

Updated: 2026-05-24
"""
import argparse
import json
import os
import time
import requests as _requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

REBROWSER_API_KEY = os.getenv("REBROWSER_API_KEY", "")
REBROWSER_API    = "https://rebrowser.net/api"

ZIP   = "92782"
DELAY = 3.0   # seconds between page navigations

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

_MODELS_FALLBACK = {
    "Acura":         ["MDX", "RDX", "TLX", "Integra", "ZDX", "ADX"],
    "Audi":          ["A3", "A4", "A4 Allroad", "A5", "A6", "A7", "A8",
                      "Q3", "Q5", "Q7", "Q8", "Q4 e-tron", "Q8 e-tron",
                      "e-tron GT", "TT",
                      "RS3", "RS5", "RS6", "RS7", "SQ5", "SQ7", "SQ8",
                      "TT RS"],
    "BMW":           ["2 Series", "3 Series", "4 Series", "5 Series",
                      "7 Series", "8 Series", "X1", "X2", "X3", "X4",
                      "X5", "X6", "X7", "i4", "i5", "i7", "iX", "Z4",
                      "M2", "M3", "M4", "M5", "M8", "X5 M", "X6 M", "XM"],
    "Buick":         ["Enclave", "Encore GX", "Envision", "Envista"],
    "Cadillac":      ["CT4", "CT5", "XT4", "XT5", "XT6", "Escalade", "Escalade ESV", "Lyriq"],
    "Chevrolet":     ["Blazer", "Blazer EV", "Colorado", "Corvette",
                      "Equinox", "Equinox EV", "Malibu", "Silverado 1500",
                      "Silverado 2500HD", "Silverado 3500HD", "Silverado EV",
                      "Suburban", "Tahoe", "Trailblazer", "Traverse", "Trax"],
    "Chrysler":      ["Pacifica", "Voyager"],
    "Dodge":         ["Challenger", "Charger", "Durango", "Hornet"],
    "Ferrari":       ["296 GTB", "812", "F8 Tributo", "F8 Spider", "Roma", "Purosangue", "SF90"],
    "Ford":          ["Bronco", "Bronco Sport", "Escape", "Expedition",
                      "Explorer", "F-150", "F-150 Lightning",
                      "F-250 Super Duty", "F-350 Super Duty",
                      "Maverick", "Mustang", "Mustang Mach-E",
                      "Ranger", "Transit Cargo"],
    "Genesis":       ["G70", "G80", "Electrified G80", "G90",
                      "GV60", "GV70", "GV80", "GV90", "Electrified GV70"],
    "GMC":           ["Acadia", "Canyon", "Hummer EV", "Sierra 1500",
                      "Sierra 2500", "Sierra 3500HD", "Terrain",
                      "Yukon", "Yukon XL"],
    "Honda":         ["Accord", "Accord Hybrid", "Civic", "Civic Hatchback",
                      "Civic Hybrid", "CR-V", "CR-V Hybrid", "HR-V",
                      "Odyssey", "Passport", "Pilot", "Prologue", "Ridgeline"],
    "Hyundai":       ["Elantra", "Elantra Hybrid", "Ioniq 5", "Ioniq 6", "Kona",
                      "Palisade", "Santa Cruz", "Santa Fe", "Santa Fe Hybrid",
                      "Sonata", "Tucson", "Tucson Hybrid", "Venue"],
    "Infiniti":      ["Q50", "Q60", "QX50", "QX55", "QX60", "QX80"],
    "Jeep":          ["Compass", "Gladiator", "Grand Cherokee",
                      "Grand Cherokee L", "Grand Wagoneer",
                      "Renegade", "Wagoneer", "Wrangler"],
    "Kia":           ["Carnival", "Carnival Hybrid", "EV6", "EV9", "K5", "Niro",
                      "Seltos", "Sorento", "Soul", "Sportage", "Telluride"],
    "Lexus":         ["ES", "ES Hybrid", "GX", "IS", "LC", "LS", "LX", "LX Hybrid",
                      "NX", "NX Hybrid", "RC", "RX", "RX Hybrid", "RZ",
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
    "Mitsubishi":    ["Eclipse Cross", "Mirage", "Outlander",
                      "Outlander PHEV", "Outlander Sport"],
    "Nissan":        ["Altima", "Armada", "Ariya", "Frontier", "Kicks",
                      "Leaf", "Maxima", "Murano", "Pathfinder",
                      "Rogue", "Sentra", "Titan", "Versa", "Z"],
    "Porsche":       ["718 Boxster", "718 Cayman", "911", "Cayenne",
                      "Cayenne E-Hybrid", "Macan", "Macan Electric",
                      "Panamera", "Taycan"],
    "RAM":           ["1500", "2500", "3500", "ProMaster", "ProMaster City"],
    "Subaru":        ["Ascent", "BRZ", "Crosstrek", "Forester",
                      "Impreza", "Legacy", "Outback", "Solterra", "WRX"],
    "Tesla":         ["Cybertruck", "Model 3", "Model S",
                      "Model X", "Model Y"],
    "Toyota":        ["4Runner", "bZ4X", "Camry", "Corolla", "Corolla Cross",
                      "Corolla Hybrid", "Crown", "GR86", "GR Corolla",
                      "Highlander", "Highlander Hybrid", "Land Cruiser", "Prius",
                      "RAV4", "RAV4 Hybrid", "Sequoia", "Sienna",
                      "Supra", "Tacoma", "Tundra", "Tundra Hybrid", "Venza"],
    "Volkswagen":    ["Arteon", "Atlas", "Atlas Cross Sport", "Golf",
                      "Golf GTI", "Golf R", "ID.4", "ID.Buzz",
                      "Jetta", "Taos", "Tiguan"],
    "Volvo":         ["EC40", "EX30", "EX40", "EX90", "S60", "S90",
                      "V60", "V90", "XC40", "XC60", "XC90"],
}

# Build MODELS_WE_USE dynamically from NHTSA, falling back to hardcoded list
def _build_models_we_use():
    try:
        from agents.nhtsa import get_all_models, SUPPORTED_MAKES
        nhtsa = get_all_models()
        result = {}
        for make in SUPPORTED_MAKES:
            models = nhtsa.get(make, [])
            if models:
                result[make] = models
            elif make in _MODELS_FALLBACK:
                result[make] = _MODELS_FALLBACK[make]
        # Add any makes in fallback not in NHTSA list
        for make, models in _MODELS_FALLBACK.items():
            if make not in result:
                result[make] = models
        return result
    except Exception:
        return _MODELS_FALLBACK

MODELS_WE_USE = _build_models_we_use()

# Known CG entity IDs already in url_helpers.py — used to seed/verify
CG_KNOWN = {
    "acura mdx": 36336,     "acura rdx": 36337,
    "bmw x3": 1441,         "bmw x5": 1443,
    "honda accord": 1265,   "honda civic": 1269,   "honda cr-v": 1271,
    "toyota camry": 1407,   "toyota rav4": 1411,   "toyota corolla": 1406,
    "ford f-150": 1344,     "ford mustang": 1347,  "ford explorer": 1340,
    "chevrolet silverado 1500": 1312, "chevrolet tahoe": 1315,
    "mercedes-benz c-class": 1422,   "mercedes-benz glc": 1426,
    "audi q5": 21909,
}


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _start_run():
    """Call Rebrowser startRun API and return (run_id, ws_endpoint)."""
    resp = _requests.get(f"{REBROWSER_API}/startRun",
                         params={"apiKey": REBROWSER_API_KEY}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    run  = data["run"]
    return run["id"], run["browserWSEndpoint"]


def _finish_run(run_id: int):
    try:
        _requests.get(f"{REBROWSER_API}/finishRun",
                      params={"apiKey": REBROWSER_API_KEY, "runId": run_id},
                      timeout=15)
    except Exception:
        pass


def _connect(p):
    """Start a Rebrowser run, connect via CDP, return (browser, context, page, run_id)."""
    if not REBROWSER_API_KEY:
        raise RuntimeError(
            "REBROWSER_API_KEY not set in .env\n"
            "Add:  REBROWSER_API_KEY=your_key_here"
        )
    print("Starting Rebrowser run...")
    run_id, ws_url = _start_run()
    print(f"  Run ID: {run_id}  |  Connecting...")
    browser = p.chromium.connect_over_cdp(ws_url)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 900},
    )
    page = context.new_page()
    return browser, context, page, run_id


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


def _print_unmatched(makes_to_run: dict, found_map: dict, site: str):
    unmatched = []
    for make_name, our_models in MODELS_WE_USE.items():
        if make_name not in makes_to_run:
            continue
        found = set(found_map.get(make_name, {}).keys())
        for m in our_models:
            if m not in found:
                unmatched.append(f"  {make_name} — {m}")
    if unmatched:
        print(f"\n# ── [{site}] Still unmatched ──────────────────────────────")
        for u in unmatched:
            print(u)


# ── AutoTrader ─────────────────────────────────────────────────────────────────

def _extract_code_list(data, depth=0):
    """Recursively find [{label, code}] arrays in AT JSON responses."""
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


def _at_capture_options(page, url: str) -> list:
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

    seen, unique = set(), []
    for opt in captured:
        if opt["code"] not in seen:
            seen.add(opt["code"])
            unique.append(opt)
    return unique


def _at_discover_make(page, make_name: str, make_slug: str) -> tuple:
    url = (f"https://www.autotrader.com/cars-for-sale/all-cars/{make_slug}/"
           f"?zip={ZIP}&searchRadius=50")
    print(f"\n  {make_name}... ", end="", flush=True)
    options = _at_capture_options(page, url)
    print(f"{len(options)} model options", end="")

    result = {}
    for model in MODELS_WE_USE.get(make_name, []):
        m = _best_match(model, options)
        if m:
            result[model] = m["code"]
    print(f"  ({len(result)}/{len(MODELS_WE_USE.get(make_name,[]))} matched)")
    return result, options


def _at_discover_trims(page, make_slug: str, model_name: str) -> list:
    model_slug = model_name.lower().replace(" ", "-").replace("/", "-")
    url = (f"https://www.autotrader.com/cars-for-sale/all-cars/{make_slug}/{model_slug}/"
           f"?zip={ZIP}&searchRadius=50")
    return _at_capture_options(page, url)


def run_at(p, filter_make=None, discover_trims=False):
    makes_to_run = {k: v for k, v in MAKES.items()
                    if filter_make is None or k.lower() == filter_make.lower()}

    model_codes = {}
    trim_codes  = {}
    all_options = {}

    browser, _, page, run_id = _connect(p)
    try:
        print("\nWarming up on autotrader.com...")
        page.goto("https://www.autotrader.com/", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        print(f"  Title: {page.title()}\n")

        print("[AT] Discovering model codes...")
        for make_name, make_slug in makes_to_run.items():
            codes, options = _at_discover_make(page, make_name, make_slug)
            model_codes[make_name] = codes
            all_options[make_name] = options
            time.sleep(DELAY)

            if discover_trims and codes:
                trim_codes[make_name] = {}
                for model_name in codes:
                    trims = _at_discover_trims(page, make_slug, model_name)
                    if trims:
                        trim_codes[make_name][model_name] = trims
                        print(f"    {model_name} trims: {[t['label'] for t in trims[:6]]}")
                    time.sleep(DELAY)
    finally:
        browser.close()
        _finish_run(run_id)

    output = {"model_codes": model_codes, "trim_codes": trim_codes, "all_options": all_options}
    with open("at_codes_full.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved → at_codes_full.json")

    print("\n" + "="*65)
    print("# ── [AT] Paste into AT_MODEL_CODE in url_helpers.py ─────────")
    for make_name, models in model_codes.items():
        if models:
            print(f"\n    # {make_name}")
            for model, code in models.items():
                slug = model.lower().replace(" ", "-").replace("/", "-")
                print(f'    "{slug}": "{code}",')

    if discover_trims and trim_codes.get("Mercedes-Benz"):
        print("\n# ── [AT] Mercedes trim codes (for _AT_MB_TRIM_CODE) ────────")
        for model, trims in trim_codes["Mercedes-Benz"].items():
            print(f"\n    # {model}")
            for t in trims:
                print(f'    # "{model.lower()} ...": "{t["code"]}",  # {t["label"]}')

    _print_unmatched(makes_to_run, model_codes, "AT")
    return model_codes


# ── CarGurus ───────────────────────────────────────────────────────────────────

import re as _re

def _cg_parse_links(html: str) -> list:
    """Extract {label, entityId} from CG page HTML by scanning href patterns.

    CG encodes entity IDs directly in anchor hrefs:
      /Cars/new/nl-New-Honda-Accord-d167
    This is more reliable than XHR interception.
    """
    # Match both model links and make links
    pattern = _re.compile(
        r'href=["\'](?:/Cars/[^"\']*?nl-New-[^"\']*?-d(\d+)[^"\']*)["\'][^>]*>([^<]+)<',
        _re.IGNORECASE,
    )
    seen, results = set(), []
    for eid, label in pattern.findall(html):
        label = label.strip()
        if eid not in seen and label:
            seen.add(eid)
            results.append({"label": label, "entityId": eid})
    return results


def run_cg(p, filter_make=None):
    makes_to_run = {k: v for k, v in MAKES.items()
                    if filter_make is None or k.lower() == filter_make.lower()}

    entity_ids = {}

    browser, _, page, run_id = _connect(p)
    try:
        # Load CG's "Browse All New Cars" index — every make/model link is here
        print("\nLoading CarGurus browse page...")
        page.goto("https://www.cargurus.com/Cars/new/nl-New-Cars.html",
                  timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        print(f"  Title: {page.title()}\n")

        # Parse the full HTML once — contains all make/model links
        html = page.content()
        all_links = _cg_parse_links(html)
        print(f"  Found {len(all_links)} entity links on browse page")

        print("[CG] Matching entity IDs...")
        for make_name in makes_to_run:
            print(f"\n  {make_name}... ", end="", flush=True)
            result = {}
            for model in MODELS_WE_USE.get(make_name, []):
                m = _best_match(model, [{"label": o["label"], "code": o["entityId"]}
                                        for o in all_links])
                if m:
                    result[model] = m["code"]

            # If no matches from browse page, try make-specific page
            if not result:
                cg_slug = make_name.lower().replace(" ", "-").replace(".", "")
                url = (f"https://www.cargurus.com/Cars/new/nl-New-{cg_slug}"
                       f"?zip={ZIP}&distance=50")
                try:
                    page.goto(url, timeout=35000, wait_until="domcontentloaded")
                    page.wait_for_timeout(4000)
                    make_html = page.content()
                    make_links = _cg_parse_links(make_html)
                    for model in MODELS_WE_USE.get(make_name, []):
                        m = _best_match(model, [{"label": o["label"], "code": o["entityId"]}
                                                for o in make_links])
                        if m:
                            result[model] = m["code"]
                    time.sleep(DELAY)
                except Exception as e:
                    print(f"(fallback nav error: {e})", end="")

            entity_ids[make_name] = result
            print(f"({len(result)}/{len(MODELS_WE_USE.get(make_name,[]))} matched)")
    finally:
        browser.close()
        _finish_run(run_id)

    print("\n" + "="*65)
    print("# ── [CG] Paste into CG_ENTITY_IDS in url_helpers.py ────────")
    for make_name, models in entity_ids.items():
        if models:
            print(f"\n    # {make_name}")
            for model, eid in models.items():
                slug = model.lower().replace(" ", "-").replace("/", "-")
                known = CG_KNOWN.get(f"{make_name.lower()} {model.lower()}")
                note = f"  # was {known}" if known and str(known) != str(eid) else ""
                print(f'    "{slug}": {eid},{note}')

    _print_unmatched(makes_to_run, entity_ids, "CG")
    return entity_ids


# ── Cars.com ───────────────────────────────────────────────────────────────────

def _cm_make_slug(make_name: str) -> str:
    return make_name.lower().replace(" ", "_").replace("-", "_").replace(".", "")


def _cm_model_slug(model_name: str) -> str:
    return (model_name.lower()
            .replace(" ", "_").replace("-", "_")
            .replace(".", "").replace("/", "_"))


def _cm_check_slug(page, make_name: str, model_name: str) -> dict:
    make_slug  = _cm_make_slug(make_name)
    model_slug = _cm_model_slug(model_name)
    full_slug  = f"{make_slug}-{model_slug}"

    url = (f"https://www.cars.com/shopping/results/"
           f"?makes[]={make_slug}&models[]={full_slug}"
           f"&zip={ZIP}&maximum_distance=50&stock_type=all")

    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        final_url = page.url

        # Redirected to make-level page means model slug was wrong
        redirected = (model_slug not in final_url.lower()
                      and make_slug in final_url.lower())

        try:
            count_el = page.query_selector(
                "[data-test='total-listings-count'], .total-listings, "
                "[data-qa='listing-count']"
            )
            count_text = count_el.inner_text().strip() if count_el else ""
        except Exception:
            count_text = ""

        return {
            "make": make_name, "model": model_name, "slug": full_slug,
            "url": url, "final_url": final_url,
            "redirected": redirected, "count_text": count_text,
            "ok": not redirected,
        }
    except Exception as e:
        return {
            "make": make_name, "model": model_name, "slug": full_slug,
            "url": url, "final_url": "", "redirected": False,
            "count_text": "", "ok": False, "error": str(e),
        }


def run_cm(p, filter_make=None):
    makes_to_run = {k: v for k, v in MAKES.items()
                    if filter_make is None or k.lower() == filter_make.lower()}

    results = {}
    bad     = []

    browser, _, page, run_id = _connect(p)
    try:
        print("\nWarming up on cars.com...")
        page.goto("https://www.cars.com/", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        print(f"  Title: {page.title()}\n")

        print("[CM] Verifying Cars.com slugs...")
        for make_name in makes_to_run:
            results[make_name] = {}
            models = MODELS_WE_USE.get(make_name, [])
            print(f"\n  {make_name} ({len(models)} models)...")
            for model_name in models:
                info = _cm_check_slug(page, make_name, model_name)
                results[make_name][model_name] = info
                status = "OK " if info["ok"] else "BAD"
                redirect_note = (f"  !! → {info['final_url'][:70]}"
                                 if info["redirected"] else "")
                print(f"    [{status}] {model_name}  →  {info['slug']}"
                      + (f"  ({info['count_text']})" if info["count_text"] else "")
                      + redirect_note)
                if not info["ok"]:
                    bad.append(info)
                time.sleep(DELAY)
    finally:
        browser.close()
        _finish_run(run_id)

    print("\n" + "="*65)
    if bad:
        print("# ── [CM] BAD slugs — fix in CM_SLUG_MAP in url_helpers.py ──")
        for info in bad:
            make_slug  = _cm_make_slug(info["make"])
            model_slug = _cm_model_slug(info["model"])
            print(f'\n    # {info["make"]} {info["model"]}')
            print(f'    # Current slug: "{make_slug}-{model_slug}"')
            print(f'    # Redirected to: {info.get("final_url","")[:80]}')
            print(f'    # "{model_slug}": "CORRECT_SLUG_HERE",')
    else:
        print("# ── [CM] All slugs verified OK! ──────────────────────────────")

    return results


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Discover AT model codes, CG entity IDs, and verify CM slugs "
            "via Rebrowser undetectable cloud browser."
        )
    )
    parser.add_argument("--at",    action="store_true", help="Run AutoTrader discovery only")
    parser.add_argument("--cg",    action="store_true", help="Run CarGurus entity ID discovery only")
    parser.add_argument("--cm",    action="store_true", help="Run Cars.com slug verification only")
    parser.add_argument("--make",  help="Limit to one make (e.g. 'Mercedes-Benz')")
    parser.add_argument("--trims", action="store_true",
                        help="(AT only) Also discover trim codes per model")
    args = parser.parse_args()

    run_all = not (args.at or args.cg or args.cm)

    if not REBROWSER_API_KEY:
        print("ERROR: REBROWSER_API_KEY not set in .env")
        print("Add:  REBROWSER_API_KEY=your_key_here")
        return

    with sync_playwright() as p:
        if run_all or args.at:
            run_at(p, filter_make=args.make, discover_trims=args.trims)

        if run_all or args.cg:
            run_cg(p, filter_make=args.make)

        if run_all or args.cm:
            run_cm(p, filter_make=args.make)


if __name__ == "__main__":
    main()
