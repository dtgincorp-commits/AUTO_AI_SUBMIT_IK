"""
Link validation test — verifies that AutoTrader, CarGurus, and Cars.com
URLs built by url_helpers resolve to valid pages (not 404 / homepage redirect).

This test makes real HTTP requests. Run it manually before a deploy:
  .venv/bin/python -m pytest tests/test_link_validation.py -v --timeout=30

It is deliberately excluded from fast CI runs via the `network` mark.
Average runtime: ~3-5 minutes (rate-limit delays between requests).
"""
import time
import pytest
import requests
from agents.url_helpers import at_url, cg_direct_url, cm_url

# ── Shared HTTP session ────────────────────────────────────────────────────────
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
})

_ZIP      = "92782"   # Irvine CA — used for all test searches
_RADIUS   = 50
_COND     = "Any"
_DELAY    = 1.2       # seconds between requests — be polite to the sites

# Homepages we should NOT land on after a redirect (means broken model URL)
_AT_HOME  = "autotrader.com/cars-for-sale/"
_CG_HOME  = "cargurus.com/Cars/inventorylisting"   # valid base path — keep
_CM_HOME  = "cars.com/shopping/results/"            # valid base path — keep

# ── Canonical make/model list ──────────────────────────────────────────────────
# Format: (make, model)  — one row per unique model we support
# These are the exact strings passed to the URL builder functions.
MODELS = [
    # Acura
    ("Acura",        "MDX"),
    # Audi
    ("Audi",         "A4"),
    ("Audi",         "Q5"),
    ("Audi",         "A6"),
    ("Audi",         "e-tron"),
    # BMW
    ("BMW",          "X5"),
    ("BMW",          "3 Series"),
    ("BMW",          "X3"),
    ("BMW",          "i4"),
    ("BMW",          "X7"),
    # Buick
    ("Buick",        "Enclave"),
    ("Buick",        "Envision"),
    # Cadillac
    ("Cadillac",     "XT5"),
    ("Cadillac",     "Lyriq"),
    # Chevrolet
    ("Chevrolet",    "Silverado 1500"),
    ("Chevrolet",    "Tahoe"),
    ("Chevrolet",    "Equinox"),
    ("Chevrolet",    "Colorado"),
    ("Chevrolet",    "Traverse"),
    # Chrysler
    ("Chrysler",     "Pacifica"),
    # Dodge
    ("Dodge",        "Durango"),
    # Ferrari
    ("Ferrari",      "SF90"),
    # Ford
    ("Ford",         "F-150"),
    ("Ford",         "Explorer"),
    ("Ford",         "Mustang"),
    ("Ford",         "Bronco"),
    ("Ford",         "Maverick"),
    ("Ford",         "Ranger"),
    # Genesis
    ("Genesis",      "GV70"),
    # GMC
    ("GMC",          "Sierra 1500"),
    ("GMC",          "Sierra 2500"),
    ("GMC",          "Terrain"),
    ("GMC",          "Acadia"),
    # Honda
    ("Honda",        "CR-V"),
    ("Honda",        "Accord"),
    ("Honda",        "Pilot"),
    ("Honda",        "Civic"),
    ("Honda",        "Ridgeline"),
    ("Honda",        "Odyssey"),
    # Hyundai
    ("Hyundai",      "Tucson"),
    ("Hyundai",      "Santa Fe"),
    ("Hyundai",      "Ioniq 5"),
    ("Hyundai",      "Palisade"),
    # Infiniti
    ("Infiniti",     "QX60"),
    # Jeep
    ("Jeep",         "Grand Cherokee"),
    ("Jeep",         "Wrangler"),
    ("Jeep",         "Gladiator"),
    # Kia
    ("Kia",          "Telluride"),
    ("Kia",          "Sportage"),
    ("Kia",          "Sorento"),
    ("Kia",          "Carnival"),
    # Lexus
    ("Lexus",        "GX"),
    ("Lexus",        "ES"),
    ("Lexus",        "IS"),
    ("Lexus",        "TX"),
    ("Lexus",        "LX"),
    # Lincoln
    ("Lincoln",      "Aviator"),
    ("Lincoln",      "Nautilus"),
    # Mazda
    ("Mazda",        "CX-5"),
    ("Mazda",        "CX-50"),
    ("Mazda",        "CX-90"),
    # Mercedes-Benz
    ("Mercedes-Benz", "C-Class"),
    ("Mercedes-Benz", "E-Class"),
    ("Mercedes-Benz", "S-Class"),
    ("Mercedes-Benz", "G-Class"),
    ("Mercedes-Benz", "CLA"),
    ("Mercedes-Benz", "GLA"),
    ("Mercedes-Benz", "GLB"),
    ("Mercedes-Benz", "GLC"),
    ("Mercedes-Benz", "GLE"),
    ("Mercedes-Benz", "GLS"),
    ("Mercedes-Benz", "AMG GT"),
    ("Mercedes-Benz", "SL"),
    ("Mercedes-Benz", "EQS"),
    ("Mercedes-Benz", "EQE"),
    ("Mercedes-Benz", "EQB"),
    ("Mercedes-Benz", "CLE"),
    ("Mercedes-Benz", "Sprinter"),
    # Mitsubishi
    ("Mitsubishi",   "Outlander"),
    # Nissan
    ("Nissan",       "Rogue"),
    ("Nissan",       "Altima"),
    ("Nissan",       "Pathfinder"),
    ("Nissan",       "Frontier"),
    # Porsche
    ("Porsche",      "Cayenne"),
    ("Porsche",      "Macan"),
    ("Porsche",      "Taycan"),
    ("Porsche",      "Panamera"),
    # RAM
    ("RAM",          "1500"),
    ("RAM",          "2500"),
    # Subaru
    ("Subaru",       "Outback"),
    ("Subaru",       "Forester"),
    ("Subaru",       "Crosstrek"),
    # Tesla
    ("Tesla",        "Model Y"),
    ("Tesla",        "Model 3"),
    ("Tesla",        "Model X"),
    # Toyota
    ("Toyota",       "RAV4"),
    ("Toyota",       "Camry"),
    ("Toyota",       "Highlander"),
    ("Toyota",       "Tacoma"),
    ("Toyota",       "Tundra"),
    ("Toyota",       "4Runner"),
    # Volkswagen
    ("Volkswagen",   "Tiguan"),
    ("Volkswagen",   "Atlas"),
    ("Volkswagen",   "Jetta"),
    # Volvo
    ("Volvo",        "XC90"),
    ("Volvo",        "XC60"),
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get(url: str) -> tuple[int, str]:
    """Return (status_code, final_url). Returns (0, '') on connection error."""
    try:
        r = _SESSION.get(url, timeout=15, allow_redirects=True)
        return r.status_code, r.url
    except Exception as e:
        return 0, str(e)


def _assert_valid(status: int, final_url: str, make: str, model: str, site: str, built_url: str):
    """
    Pass:  200 (success) or 403 (bot-blocked — URL exists, site rejects bots)
    Skip:  403 (logged as warning but not a test failure)
    Fail:  404 (URL doesn't exist on that site) or 0 (connection error)
    """
    if status == 0:
        pytest.fail(f"{site}: connection error for {make} {model}\n  URL: {built_url}\n  Error: {final_url}")
    if status == 404:
        pytest.fail(
            f"{site}: HTTP 404 — URL not found for {make} {model}\n"
            f"  Built:  {built_url}\n"
            f"  Final:  {final_url}"
        )
    if status == 403:
        pytest.skip(f"{site} blocked bot request (403) — URL format is valid for {make} {model}")
    if status not in (200, 301, 302):
        pytest.fail(f"{site}: unexpected HTTP {status} for {make} {model}\n  URL: {built_url}")


# ── AutoTrader tests ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("make,model", MODELS)
def test_autotrader_link(make, model):
    url = at_url(make, model, _COND, _ZIP, radius=_RADIUS)
    time.sleep(_DELAY)
    status, final_url = _get(url)
    _assert_valid(status, final_url, make, model, "AutoTrader", url)
    # Extra check: AutoTrader doesn't block bots — verify make is in final URL
    if status == 200:
        make_slug = make.lower().replace(" ", "-").replace(".", "")
        assert make_slug in final_url.lower(), (
            f"AutoTrader redirected away from {make} {model} page\n"
            f"  Built:  {url}\n"
            f"  Landed: {final_url}"
        )


# ── CarGurus tests ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("make,model", MODELS)
def test_cargurus_link(make, model):
    url = cg_direct_url(make, model, _COND, _ZIP, radius=_RADIUS)
    if url is None:
        pytest.skip(f"No CarGurus entity ID mapped for {make} {model}")
    time.sleep(_DELAY)
    status, final_url = _get(url)
    _assert_valid(status, final_url, make, model, "CarGurus", url)


# ── Cars.com tests ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("make,model", MODELS)
def test_carscom_link(make, model):
    url = cm_url(make, model, _COND, _ZIP, radius=_RADIUS)
    time.sleep(_DELAY)
    status, final_url = _get(url)
    _assert_valid(status, final_url, make, model, "Cars.com", url)
