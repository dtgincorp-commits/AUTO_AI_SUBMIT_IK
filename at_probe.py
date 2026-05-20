#!/usr/bin/env python3
"""
AT URL HTTP Probe — detects when AutoTrader drops a model filter.

All makes (including Mercedes-Benz) use query-based routing:
  ?makeCodeList=MB&modelCodeList=MBGLE450
  PASS = modelCodeList param still in AT's final response URL

Usage:
  .venv/bin/python at_probe.py                   # probe all makes
  .venv/bin/python at_probe.py ford f-150         # keyword filter (case-insensitive)
  .venv/bin/python at_probe.py mercedes           # only Mercedes
  .venv/bin/python at_probe.py --fail-only        # show only failures/errors

Rate-limited to ~1.5 s/request to avoid bot blocks. Full run ≈ 2–3 min.
"""

import sys, time, argparse
import requests
from urllib.parse import urlparse, parse_qs

from agents.url_helpers import (
    at_url, _at_model_code,
    normalize_make,
)

# ── All makes/models to probe (same list as generate_at_test_page.py) ─────────

ALL_MODELS = {
    "Acura":         ["MDX", "ADX", "TLX", "RDX", "Integra", "ZDX"],
    "Audi":          ["A4", "Q5", "A6", "e-tron", "A3", "A4 Allroad", "A5", "A8", "Q3",
                      "A7", "Q7", "Q8", "Q4 e-tron", "Q8 e-tron", "e-tron GT", "TT"],
    "BMW":           ["X5", "3 Series", "X3", "i4", "X7", "i7", "2 Series", "4 Series", "X1",
                      "5 Series", "7 Series", "8 Series", "X2", "X4", "X6",
                      "iX", "i5", "Z4", "M3", "M4", "M5"],
    "Buick":         ["Enclave", "Envision", "Encore GX", "Envista"],
    "Cadillac":      ["XT5", "Lyriq", "CT4", "CT5", "XT4", "XT6", "Escalade"],
    "Chevrolet":     ["Silverado 1500", "Tahoe", "Equinox", "Colorado", "Traverse",
                      "Silverado 2500HD", "Silverado 3500HD", "Suburban",
                      "Trailblazer", "Trax", "Blazer EV", "Equinox EV",
                      "Blazer", "Corvette", "Malibu"],
    "Chrysler":      ["Pacifica"],
    "Dodge":         ["Durango", "Charger", "Hornet"],
    "Ferrari":       ["SF90"],
    "Ford":          ["F-150", "Explorer", "Mustang", "Bronco", "Maverick", "Ranger",
                      "Escape", "Expedition", "Bronco Sport", "F-150 Lightning",
                      "F-250 Super Duty", "Mustang Mach-E", "Transit Cargo",
                      "F-350 Super Duty"],
    "Genesis":       ["GV70", "GV80", "G70", "G80", "G90", "GV60", "GV90", "Electrified GV70"],
    "GMC":           ["Sierra 1500", "Sierra 2500", "Terrain", "Acadia",
                      "Canyon", "Sierra 3500HD", "Yukon", "Yukon XL", "Hummer EV"],
    "Honda":         ["CR-V", "Accord", "Pilot", "Civic", "Ridgeline", "Odyssey",
                      "HR-V", "Passport", "CR-V Hybrid", "Accord Hybrid", "Prologue"],
    "Hyundai":       ["Tucson", "Santa Fe", "Ioniq 5", "Palisade",
                      "Elantra", "Kona", "Santa Cruz", "Sonata", "Ioniq 6", "Venue"],
    "Infiniti":      ["QX60", "QX50", "QX55", "QX80", "Q50", "Q60"],
    "Jeep":          ["Grand Cherokee", "Wrangler", "Gladiator", "Compass", "Grand Cherokee L"],
    "Kia":           ["Telluride", "Sportage", "Sorento", "Carnival",
                      "K5", "Niro", "Seltos", "Soul", "EV6", "EV9"],
    "Lexus":         ["GX", "ES", "IS", "TX", "LX", "NX", "NX Hybrid", "RX", "RX Hybrid",
                      "LS", "LC", "RZ", "UX"],
    "Lincoln":       ["Aviator", "Nautilus", "Corsair", "Navigator"],
    "Mazda":         ["CX-5", "CX-50", "CX-90", "CX-30", "Mazda3", "MX-5 Miata", "CX-70"],
    "Mercedes-Benz": ["C-Class", "E-Class", "S-Class", "G-Class", "CLA", "GLA",
                      "GLB", "GLC", "GLC Coupe", "GLE", "GLS", "AMG GT", "SL",
                      "EQS", "EQS SUV", "EQE", "EQE SUV", "EQB", "CLE", "CLS",
                      "Sprinter", "Maybach GLS 600", "Maybach S 680"],
    "Mitsubishi":    ["Outlander", "Eclipse Cross"],
    "Nissan":        ["Rogue", "Altima", "Pathfinder", "Frontier",
                      "Armada", "Kicks", "Murano", "Sentra", "Versa",
                      "Leaf", "Ariya", "Z", "Maxima"],
    "Porsche":       ["Cayenne", "Macan", "Taycan", "Panamera",
                      "911", "718 Boxster", "718 Cayman"],
    "RAM":           ["1500", "2500", "3500", "ProMaster"],
    "Subaru":        ["Outback", "Forester", "Crosstrek", "Ascent", "Legacy",
                      "Impreza", "WRX", "Solterra", "BRZ"],
    "Tesla":         ["Model Y", "Model 3", "Model X", "Model S", "Cybertruck"],
    "Toyota":        ["RAV4", "Camry", "Highlander", "Tacoma", "Tundra", "4Runner",
                      "Corolla", "Sienna", "RAV4 Hybrid",
                      "Venza", "Crown", "Sequoia", "Prius", "Land Cruiser", "bZ4X", "GR86"],
    "Volkswagen":    ["Tiguan", "Atlas", "Jetta", "Taos", "Atlas Cross Sport",
                      "ID.4", "Golf", "Arteon"],
    "Volvo":         ["XC90", "XC60", "XC40", "S60", "S90", "V60", "V90",
                      "EX30", "EX40", "EX90", "EC40"],
}

ZIP_CODE  = "92782"
RADIUS    = 50
CONDITION = "Any"
DELAY     = 1.5

# ── HTTP session ──────────────────────────────────────────────────────────────

_session = requests.Session()
_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
})


# ── probe logic ───────────────────────────────────────────────────────────────

def probe_one(make: str, model: str) -> dict:
    make_norm = normalize_make(make)
    url       = at_url(make_norm, model, CONDITION, ZIP_CODE, radius=RADIUS)

    try:
        r = _session.get(url, timeout=15, allow_redirects=True)
        final_url   = r.url
        status_code = r.status_code
    except Exception as exc:
        return _result(make, model, "error", str(exc), url, "")

    if status_code == 403:
        return _result(make, model, "blocked",
                       "AT returned 403 — bot block (treat as inconclusive)",
                       url, final_url)

    final_params = parse_qs(urlparse(final_url).query)

    expected_code = _at_model_code(model)
    if not expected_code:
        return _result(make, model, "warn",
                       "no modelCodeList generated — no model code mapped for this model",
                       url, final_url)
    kept = final_params.get("modelCodeList", [""])[0] == expected_code
    if kept:
        return _result(make, model, "pass",
                       f"modelCodeList={expected_code} kept by AT", url, final_url)
    found = final_params.get("modelCodeList", ["—"])[0]
    return _result(make, model, "fail",
                   f"modelCodeList={expected_code} dropped (AT has: {found!r})",
                   url, final_url)


def _result(make, model, status, reason, sent, final):
    return dict(make=make, model=model, status=status, reason=reason,
                sent_url=sent, final_url=final)


# ── CLI ───────────────────────────────────────────────────────────────────────

_ICONS = {"pass": "✅ PASS", "fail": "❌ FAIL",
          "warn": "⚠️ WARN", "error": "💥 ERROR", "blocked": "🚫 BLOCKED"}


def main():
    parser = argparse.ArgumentParser(description="Probe AT URLs for dropped model filters")
    parser.add_argument("keywords", nargs="*",
                        help="Optional filter: make and/or model keywords (case-insensitive)")
    parser.add_argument("--fail-only", action="store_true",
                        help="Print only failures, warnings, and errors")
    args = parser.parse_args()

    filters = [k.lower() for k in args.keywords]
    results = []

    for make, models in ALL_MODELS.items():
        for model in models:
            if filters:
                combined = (make + " " + model).lower()
                if not any(f in combined for f in filters):
                    continue

            print(f"  Probing {make} {model} ...", end="", flush=True)
            res = probe_one(make, model)
            results.append(res)

            label = f"  {_ICONS[res['status']]}  {make} {model}"
            print(f"\r{label:<72}")

            if res["status"] not in ("pass", "blocked") or not args.fail_only:
                if res["status"] in ("fail", "warn", "error"):
                    print(f"       Sent:   {res['sent_url']}")
                    print(f"       Got:    {res['final_url']}")
                    print(f"       Reason: {res['reason']}")

            time.sleep(DELAY)

    # ── summary ──────────────────────────────────────────────────────────────
    counts = {s: sum(1 for r in results if r["status"] == s)
              for s in ("pass", "fail", "warn", "blocked", "error")}
    total  = len(results)

    print()
    print("=" * 65)
    print(f"  Probed: {total}  |  "
          f"✅ PASS: {counts['pass']}  "
          f"❌ FAIL: {counts['fail']}  "
          f"⚠️ WARN: {counts['warn']}  "
          f"🚫 BLOCKED: {counts['blocked']}  "
          f"💥 ERROR: {counts['error']}")

    if counts["fail"] or counts["warn"]:
        print()
        print("Issues found:")
        for r in results:
            if r["status"] in ("fail", "warn"):
                print(f"  • {r['make']} {r['model']}: {r['reason']}")
                print(f"    URL: {r['final_url']}")
    print()


if __name__ == "__main__":
    main()
