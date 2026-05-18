"""
NL Parser model coverage test.
Verifies that parse_query() correctly extracts make and model for every
make/model combination we support, plus known edge cases.

Run: .venv/bin/python -m pytest tests/test_nl_parser_models.py -v
"""
import pytest
from agents.nl_parser import parse_query

# ── Test cases ────────────────────────────────────────────────────────────────
# Format: (query, expected_make_fragment, expected_model_fragment)
# Checks are case-insensitive substring matches.
# expected_model_fragment can be a list — any one match passes.

CASES = [
    # ── Acura ──────────────────────────────────────────────────────────────────
    ("I want an Acura MDX near 92782",                    "acura",        "mdx"),
    ("Looking for Acura ADX under 50k",                   "acura",        "adx"),
    # ── Audi ───────────────────────────────────────────────────────────────────
    ("Find me an Audi A4 near Chicago",                   "audi",         "a4"),
    ("Audi Q5 under 60k in 90210",                        "audi",         "q5"),
    ("Audi A6 Prestige near Dallas",                      "audi",         "a6"),
    ("Audi Q5 quattro under 55k",                         "audi",         "q5"),   # quattro dropped
    ("Audi e-tron near 92782",                            "audi",         "e-tron"),
    # ── BMW ────────────────────────────────────────────────────────────────────
    ("BMW X5 xDrive40i near LA",                          "bmw",          "x5"),   # xDrive dropped
    ("BMW 3 Series near Boston under 45k",                "bmw",          "3 series"),
    ("BMW X3 near 10001",                                 "bmw",          "x3"),
    ("BMW i4 electric near 60601",                        "bmw",          "i4"),
    ("BMW X7 under 90k near Seattle",                     "bmw",          "x7"),
    # ── Buick ──────────────────────────────────────────────────────────────────
    ("Buick Enclave near 77001",                          "buick",        "enclave"),
    ("Buick Envision under 40k",                          "buick",        "envision"),
    # ── Cadillac ───────────────────────────────────────────────────────────────
    ("Cadillac XT5 near Phoenix",                         "cadillac",     "xt5"),
    ("Cadillac Lyriq EV near 92782",                      "cadillac",     "lyriq"),
    # ── Chevrolet ──────────────────────────────────────────────────────────────
    ("Chevy Silverado 1500 near Dallas",                  "chevrolet",    "silverado"),
    ("Chevrolet Tahoe under 60k near Houston",            "chevrolet",    "tahoe"),
    ("Chevy Equinox near 30301",                          "chevrolet",    "equinox"),
    ("Chevrolet Colorado near Denver",                    "chevrolet",    "colorado"),
    ("Chevy Traverse AWD under 50k",                      "chevrolet",    "traverse"),  # AWD dropped
    # ── Chrysler ───────────────────────────────────────────────────────────────
    ("Chrysler Pacifica near 33101",                      "chrysler",     "pacifica"),
    # ── Dodge ──────────────────────────────────────────────────────────────────
    ("Dodge Durango near 85001",                          "dodge",        "durango"),
    # ── Ferrari ────────────────────────────────────────────────────────────────
    ("Ferrari SF90 near Miami",                           "ferrari",      "sf90"),
    # ── Ford ───────────────────────────────────────────────────────────────────
    ("Ford F-150 Lariat near 75201",                      "ford",         "f-150"),
    ("Ford Explorer XLT near 92782",                      "ford",         "explorer"),
    ("Ford Mustang GT under 45k",                         "ford",         "mustang"),
    ("Ford Bronco near 78201",                            "ford",         "bronco"),
    ("Ford Maverick under 35k near 92782",                "ford",         "maverick"),
    ("Ford Mustang Mach-E near 94102",                    "ford",         ["mustang mach-e", "mustang mach e", "mach-e", "mach e"]),
    ("Ford F-150 Lightning near 48201",                   "ford",         ["f-150 lightning", "f-150", "lightning"]),
    ("Ford Ranger near 97201",                            "ford",         "ranger"),
    # ── Genesis ────────────────────────────────────────────────────────────────
    ("Genesis GV70 near 10001",                           "genesis",      "gv70"),
    # ── GMC ────────────────────────────────────────────────────────────────────
    ("GMC Sierra 1500 near 75201",                        "gmc",          "sierra"),
    ("GMC Sierra 2500 Denali HD near 92782 under 100k",   "gmc",          "sierra 2500"),  # HD dropped, Denali in trim
    ("GMC Terrain near 60601",                            "gmc",          "terrain"),
    ("GMC Acadia near 77001",                             "gmc",          "acadia"),
    # ── Honda ──────────────────────────────────────────────────────────────────
    ("Honda CR-V near 92782 under 40k",                   "honda",        ["cr-v", "crv"]),
    ("Honda Accord under 35k near LA",                    "honda",        "accord"),
    ("Honda Pilot near 92782",                            "honda",        "pilot"),
    ("Honda Civic near 10001",                            "honda",        "civic"),
    ("Honda Ridgeline near 96801",                        "honda",        "ridgeline"),
    ("Honda Odyssey near 33101",                          "honda",        "odyssey"),
    # ── Hyundai ────────────────────────────────────────────────────────────────
    ("Hyundai Tucson near 30301",                         "hyundai",      "tucson"),
    ("Hyundai Santa Fe near 77001",                       "hyundai",      "santa fe"),
    ("Hyundai Ioniq 5 near 94102",                        "hyundai",      "ioniq 5"),
    ("Hyundai Palisade near 85001",                       "hyundai",      "palisade"),
    # ── Infiniti ───────────────────────────────────────────────────────────────
    ("Infiniti QX60 near 92782",                          "infiniti",     "qx60"),
    # ── Jeep ───────────────────────────────────────────────────────────────────
    ("Jeep Grand Cherokee near 10001",                    "jeep",         "grand cherokee"),
    ("Jeep Wrangler near 85001",                          "jeep",         "wrangler"),
    ("Jeep Gladiator near 78201",                         "jeep",         "gladiator"),
    # ── Kia ────────────────────────────────────────────────────────────────────
    ("Kia Telluride near 30301",                          "kia",          "telluride"),
    ("Kia Sportage near 92782 under 35k",                 "kia",          "sportage"),
    ("Kia Sorento near 77001",                            "kia",          "sorento"),
    ("Kia Carnival near 33101",                           "kia",          "carnival"),
    # ── Lexus ──────────────────────────────────────────────────────────────────
    ("Lexus GX near 90210",                               "lexus",        "gx"),
    ("Lexus ES near 77001",                               "lexus",        "es"),
    ("Lexus IS near 92782",                               "lexus",        "is"),
    ("Lexus TX near 75201",                               "lexus",        "tx"),
    ("Lexus LX near 10001",                               "lexus",        "lx"),
    # ── Lincoln ────────────────────────────────────────────────────────────────
    ("Lincoln Navigator near 75201",                      "lincoln",      "navigator"),
    ("Lincoln Aviator near 77001",                        "lincoln",      "aviator"),
    ("Lincoln Nautilus near 60601",                       "lincoln",      "nautilus"),
    # ── Mazda ──────────────────────────────────────────────────────────────────
    ("Mazda CX-5 near 92782 under 35k",                   "mazda",        ["cx-5", "cx5", "cx 5"]),
    ("Mazda CX-50 near 94102",                            "mazda",        ["cx-50", "cx50"]),
    ("Mazda CX-90 near 10001",                            "mazda",        ["cx-90", "cx90"]),
    # ── Mercedes-Benz ──────────────────────────────────────────────────────────
    ("Mercedes GLE 450 near 92782",                       "mercedes",     "gle"),
    ("Mercedes GLE450e near 92782",                       "mercedes",     "gle 450e"),  # KEY edge case
    ("GLE450e 92782",                                     "mercedes",     "gle 450e"),  # no make typed
    ("Mercedes GLC 300 near 90210 under 60k",             "mercedes",     "glc"),
    ("Mercedes GLS 580 near 10001",                       "mercedes",     "gls"),
    ("Mercedes C300 near 77001",                          "mercedes",     ["c-class", "c 300", "c300"]),
    ("Mercedes E350 near 92782",                          "mercedes",     ["e-class", "e 350", "e350"]),
    ("Mercedes S580 near 90210",                          "mercedes",     ["s-class", "s 580", "s580"]),
    ("Mercedes AMG GT 63 near 33101",                     "mercedes",     ["amg gt", "amg gt 63"]),
    ("Mercedes G550 near 92782",                          "mercedes",     ["g-class", "g 550", "g550"]),
    ("Mercedes EQS 450 near 94102",                       "mercedes",     ["eqs", "eqs 450"]),
    ("Mercedes GLA 250 near 10001",                       "mercedes",     ["gla", "gla 250"]),
    ("Mercedes GLB 250 near 60601",                       "mercedes",     ["glb", "glb 250"]),
    ("Mercedes CLA 250 near 77001",                       "mercedes",     ["cla", "cla 250"]),
    ("Mercedes GLC300e near 85001",                       "mercedes",     "glc 300e"),  # PHEV variant
    ("Mercedes S580 near Beverly Hills",                  "mercedes",     ["s-class", "s 580", "s580"]),
    ("Mercedes S500 near 90210",                          "mercedes",     ["s-class", "s 500", "s500"]),
    ("Mercedes G550 near Miami",                          "mercedes",     ["g-class", "g 550", "g550"]),
    ("Mercedes AMG G63 near 33101",                       "mercedes",     ["g-class", "g 63", "amg g"]),
    ("Mercedes AMG GT 63 S near 90210",                   "mercedes",     ["amg gt", "amg gt 63"]),
    ("Mercedes AMG GT 43 near 92782",                     "mercedes",     ["amg gt", "amg gt 43"]),
    ("Mercedes EQS 450 near 94102",                       "mercedes",     ["eqs", "eqs 450"]),
    ("Mercedes EQS 580 near 10001",                       "mercedes",     ["eqs", "eqs 580"]),
    ("Mercedes GLA 250 near 90210",                       "mercedes",     ["gla", "gla 250"]),
    ("Mercedes GLB 250 near 60601",                       "mercedes",     ["glb", "glb 250"]),
    ("Mercedes SL 55 near Beverly Hills",                 "mercedes",     ["sl", "sl 55", "sl-class"]),
    ("Mercedes EQE 350 near 94102",                       "mercedes",     ["eqe", "eqe 350"]),
    ("Mercedes EQB 300 near 10001",                       "mercedes",     ["eqb", "eqb 300"]),
    ("Mercedes CLE 300 near 92782",                       "mercedes",     ["cle", "cle 300"]),
    # ── Mitsubishi ─────────────────────────────────────────────────────────────
    ("Mitsubishi Outlander near 92782",                   "mitsubishi",   "outlander"),
    # ── Nissan ─────────────────────────────────────────────────────────────────
    ("Nissan Rogue near 92782 under 35k",                 "nissan",       "rogue"),
    ("Nissan Altima near 30301",                          "nissan",       "altima"),
    ("Nissan Pathfinder near 77001",                      "nissan",       "pathfinder"),
    ("Nissan Frontier near 78201",                        "nissan",       "frontier"),
    # ── Porsche ────────────────────────────────────────────────────────────────
    ("Porsche Cayenne near 90210",                        "porsche",      "cayenne"),
    ("Porsche Macan near 92782",                          "porsche",      "macan"),
    ("Porsche Taycan near 94102",                         "porsche",      "taycan"),
    ("Porsche Panamera near 10001",                       "porsche",      "panamera"),
    # ── RAM ────────────────────────────────────────────────────────────────────
    ("RAM 1500 near 75201",                               "ram",          "1500"),
    ("Ram 2500 near 85001",                               "ram",          "2500"),
    # ── Subaru ─────────────────────────────────────────────────────────────────
    ("Subaru Outback near 97201",                         "subaru",       "outback"),
    ("Subaru Forester near 92782",                        "subaru",       "forester"),
    ("Subaru Crosstrek near 80201",                       "subaru",       "crosstrek"),
    # ── Tesla ──────────────────────────────────────────────────────────────────
    ("Tesla Model Y near 94102",                          "tesla",        "model y"),
    ("Tesla Model 3 near 92782 under 50k",                "tesla",        "model 3"),
    ("Tesla Model X near 10001",                          "tesla",        "model x"),
    # ── Toyota ─────────────────────────────────────────────────────────────────
    ("Toyota RAV4 near 92782 under 40k",                  "toyota",       "rav4"),
    ("Toyota Camry near 30301",                           "toyota",       "camry"),
    ("Toyota Highlander near 77001",                      "toyota",       "highlander"),
    ("Toyota Tacoma TRD Off-Road near 78201",             "toyota",       "tacoma"),
    ("Toyota Tundra near 75201",                          "toyota",       "tundra"),
    ("Toyota 4Runner near 85001",                         "toyota",       "4runner"),
    ("Toyota RAV4 AWD under 40k near 92782",              "toyota",       "rav4"),   # AWD dropped
    # ── Volkswagen ─────────────────────────────────────────────────────────────
    ("VW Tiguan near 10001",                              "volkswagen",   "tiguan"),
    ("Volkswagen Atlas near 60601",                       "volkswagen",   "atlas"),
    ("Volkswagen Jetta near 30301",                       "volkswagen",   "jetta"),
    # ── Volvo ──────────────────────────────────────────────────────────────────
    ("Volvo XC90 near 92782",                             "volvo",        "xc90"),
    ("Volvo XC60 near 94102",                             "volvo",        "xc60"),
    # ── Badge-stripping edge cases ──────────────────────────────────────────────
    ("Sierra 2500 Denali HD 92782 under 155k",            "gmc",          "sierra 2500"),
    ("BMW X5 xDrive45e near 92782",                       "bmw",          "x5"),
    ("Audi Q5 quattro Premium near 90210",                "audi",         "q5"),
    ("GLS 450 4MATIC near 10001",                         "mercedes",     "gls"),
]


def _make_matches(parsed_make: str, expected: str) -> bool:
    pm = parsed_make.lower()
    exp = expected.lower()
    return exp in pm or pm in exp


def _model_matches(parsed_model: str, expected) -> bool:
    pm = parsed_model.lower()
    if isinstance(expected, list):
        return any(e.lower() in pm or pm in e.lower() for e in expected)
    return expected.lower() in pm or pm in expected.lower()


@pytest.mark.parametrize("query,exp_make,exp_model", CASES)
def test_parse_query(query, exp_make, exp_model):
    result, err = parse_query(query)
    assert not err, f"Parser error: {err}"

    parsed_make  = result.get("make", "")
    parsed_model = result.get("model", "")

    assert parsed_make,  f"No make returned for: {query!r}"
    assert parsed_model, f"No model returned for: {query!r}"

    assert _make_matches(parsed_make, exp_make), (
        f"Make mismatch for {query!r}\n"
        f"  expected: {exp_make!r}\n"
        f"  got:      {parsed_make!r}"
    )
    assert _model_matches(parsed_model, exp_model), (
        f"Model mismatch for {query!r}\n"
        f"  expected: {exp_model!r}\n"
        f"  got:      {parsed_model!r}"
    )
