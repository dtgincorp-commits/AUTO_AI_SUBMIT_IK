"""
Test AT URL generation for make/model/trim combinations.
Validates:
  1. Trim classification (LLM output)
  2. URL structure (model slug in path, trim encoding strategy)

Run: .venv/bin/python test_at_trim_urls.py
"""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from agents.url_helpers import at_url, classify_trim

ZIP = "92782"

# (make, model, trim, expected_type, must_contain, must_not_contain, notes)
TESTS = [
    # ── Honda ──────────────────────────────────────────────────────────────
    ("Honda", "CR-V",    "TrailSport",        "real_trim",    ["cr-v", "trimCodeList=TrailSport"],          [],                          "CR-V TrailSport"),
    ("Honda", "CR-V",    "Hybrid TrailSport",  "real_trim",    ["cr-v", "trimCodeList=TrailSport"],          ["Hybrid"],                  "Hybrid prefix stripped"),
    ("Honda", "Accord",  "Sport",              "real_trim",    ["accord", "trimCodeList=Sport"],             [],                          "Accord Sport"),
    # ── Toyota ─────────────────────────────────────────────────────────────
    ("Toyota", "RAV4",   "Prime",              "real_trim",    ["rav4", "trimCodeList=Prime"],               [],                          "RAV4 Prime"),
    ("Toyota", "RAV4",   "Hybrid XSE",         "real_trim",    ["rav4", "trimCodeList=XSE"],                 ["Hybrid"],                  "RAV4 Hybrid XSE — strip Hybrid"),
    ("Toyota", "Camry",  "XSE",                "real_trim",    ["camry", "trimCodeList=XSE"],                [],                          "Camry XSE"),
    ("Toyota", "Highlander", "Platinum",       "real_trim",    ["highlander", "trimCodeList=Platinum"],      [],                          "Highlander Platinum"),
    # ── Lexus ──────────────────────────────────────────────────────────────
    ("Lexus",  "TX",     "500h",               "real_trim",    ["tx-500h"],                                  ["trimCodeList"],             "Lexus TX 500h — path slug"),
    ("Lexus",  "RX",     "500h",               "real_trim",    ["rx-500h"],                                  ["trimCodeList"],             "Lexus RX 500h — path slug"),
    ("Lexus",  "NX",     "350",                "real_trim",    ["nx-350"],                                   ["trimCodeList"],             "Lexus NX 350 — path slug"),
    # ── Ford / GM ──────────────────────────────────────────────────────────
    ("Ford",   "F-150",  "Lariat",             "real_trim",    ["f-150", "trimCodeList=Lariat"],             [],                          "F-150 Lariat"),
    ("Ford",   "F-150",  "Raptor",             "real_trim",    ["f-150", "trimCodeList=Raptor"],             [],                          "F-150 Raptor"),
    ("Chevrolet", "Tahoe", "LT",               "real_trim",    ["tahoe", "trimCodeList=LT"],                 [],                          "Tahoe LT"),
    ("GMC",    "Sierra 1500", "Denali",        "real_trim",    ["sierra", "trimCodeList=Denali"],            [],                          "Sierra Denali"),
    # ── Jeep / Ram ─────────────────────────────────────────────────────────
    ("Jeep",   "Wrangler", "Rubicon",          "real_trim",    ["wrangler", "trimCodeList=Rubicon"],         [],                          "Wrangler Rubicon"),
    ("Ram",    "1500",   "Laramie",            "real_trim",    ["1500", "trimCodeList=Laramie"],             [],                          "Ram 1500 Laramie"),
    # ── BMW ────────────────────────────────────────────────────────────────
    ("BMW",    "X5",     "M Sport",            "package",      ["x5", "trimCodeList"],                       [],                          "BMW X5 M Sport — package, best-guess trimCodeList added"),
    ("BMW",    "X3",     "M Sport",            "package",      ["x3", "trimCodeList"],                       [],                          "BMW X3 M Sport — package, best-guess trimCodeList added"),
    # ── Audi ───────────────────────────────────────────────────────────────
    ("Audi",   "Q5",     "Prestige",           "real_trim",    ["q5", "trimCodeList=Prestige"],              [],                          "Audi Q5 Prestige"),
    ("Audi",   "Q7",     "S line",             "package",      ["q7", "trimCodeList"],                       [],                          "Audi Q7 S line — package, best-guess trimCodeList added"),
    ("Audi",   "Q5",     "Premium Plus",       "real_trim",    ["q5", "trimCodeList=Premium"],               [],                          "Audi Q5 Premium Plus"),
    # ── Porsche ────────────────────────────────────────────────────────────
    ("Porsche", "Cayenne", "S",                "path_segment", ["cayenne/s"],                                ["trimCodeList"],             "Porsche Cayenne S — path segment"),
    ("Porsche", "Cayenne", "GTS",              "path_segment", ["cayenne/gts"],                              ["trimCodeList"],             "Porsche Cayenne GTS — path segment"),
    ("Porsche", "Macan",   "GTS",              "path_segment", ["macan/gts"],                                ["trimCodeList"],             "Porsche Macan GTS — path segment"),
    ("Porsche", "911",     "Carrera S",        "path_segment", ["911/carrera"],                              ["trimCodeList"],             "Porsche 911 Carrera S — path segment"),
    # ── Genesis ────────────────────────────────────────────────────────────
    ("Genesis", "GV80",  "Prestige",           "real_trim",    ["gv80", "trimCodeList=Prestige"],            [],                          "Genesis GV80 Prestige"),
    ("Genesis", "GV70",  "Sport",              "real_trim",    ["gv70", "trimCodeList=Sport"],               [],                          "Genesis GV70 Sport"),
    # ── Cadillac ───────────────────────────────────────────────────────────
    ("Cadillac", "Escalade", "Premium Luxury", "real_trim",    ["escalade", "trimCodeList=Premium"],         [],                          "Escalade Premium Luxury"),
    # ── Hyundai / Kia ──────────────────────────────────────────────────────
    ("Hyundai", "Tucson", "SEL",               "real_trim",    ["tucson", "trimCodeList=SEL"],               [],                          "Tucson SEL"),
    ("Hyundai", "Tucson", "Hybrid SEL",        "real_trim",    ["tucson", "trimCodeList=SEL"],               ["Hybrid"],                  "Tucson Hybrid SEL — strip Hybrid"),
    ("Kia",    "Telluride", "SX Prestige",     "real_trim",    ["telluride", "trimCodeList=SX"],             [],                          "Telluride SX Prestige"),
    # ── Mercedes ───────────────────────────────────────────────────────────
    ("Mercedes-Benz", "GLE 450", "AMG Line",   "package",      ["gle"],                                      ["trimCodeList"],             "MB GLE 450 AMG Line — package"),
    ("Mercedes-Benz", "GLC 300", "AMG Line",   "package",      ["glc"],                                      ["trimCodeList"],             "MB GLC 300 AMG Line — package"),
]

PASS = "✅"; FAIL = "❌"; WARN = "⚠️"

results = []
print(f"\n{'Make/Model/Trim':<40} {'Type':<14} {'URL Check':<10} {'Notes'}")
print("─" * 110)

for make, model, trim, exp_type, must_have, must_not, notes in TESTS:
    # 1. Classify trim
    trim_for_url = trim
    for pfx in ("hybrid ", "plug-in hybrid ", "phev ", "electric "):
        if trim_for_url.lower().startswith(pfx):
            trim_for_url = trim_for_url[len(pfx):].strip()
            break
    actual_type, at_name = classify_trim(make, model, trim_for_url) if trim_for_url and trim_for_url.lower() not in ("any","") else ("none","")

    # 2. Build URL (passes original trim — at_url strips prefix internally)
    url = at_url(make, model, "Any", ZIP, trim=trim)
    url_lower = url.lower()

    # 3. Validate
    type_ok  = (actual_type == exp_type)
    have_ok  = all(s.lower() in url_lower for s in must_have)
    not_ok   = all(s.lower() not in url_lower for s in must_not)
    all_ok   = type_ok and have_ok and not_ok

    label = f"{make} {model} / {trim}"
    type_icon = PASS if type_ok else FAIL
    url_icon  = PASS if (have_ok and not_ok) else FAIL
    print(f"{label:<40} {type_icon}{actual_type:<13} {url_icon}         {notes}")
    if not all_ok:
        if not type_ok:
            print(f"  {'':4}type: expected={exp_type} got={actual_type}")
        if not have_ok:
            missing = [s for s in must_have if s.lower() not in url_lower]
            print(f"  {'':4}URL missing: {missing}")
        if not not_ok:
            present = [s for s in must_not if s.lower() in url_lower]
            print(f"  {'':4}URL should NOT contain: {present}")
        print(f"  {'':4}URL: {url}")
    results.append(all_ok)

total = len(results)
passed = sum(results)
print("─" * 110)
print(f"\n{PASS if passed == total else FAIL} {passed}/{total} passed\n")
sys.exit(0 if passed == total else 1)
