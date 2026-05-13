"""
Level 1 — URL correctness tests (no network)
Level 2 — HTTP reachability tests (live HTTP GET, marked slow)

Run all:         python -m pytest test_links.py -v
Level 1 only:    python -m pytest test_links.py -v -m "not slow"
Level 2 only:    python -m pytest test_links.py -v -m slow
"""
import re
import pytest
import requests
from agents.url_helpers import (
    normalize_make, cg_url, cg_direct_url, at_url, cm_url,
    CM_SLUG_MAP, CG_ENTITY_IDS,
)

# ─── helpers ────────────────────────────────────────────────────────────────

def _qp(url: str) -> dict:
    """Return query-param dict from a URL (last ?-segment)."""
    qs = url.split("?", 1)[1] if "?" in url else ""
    out = {}
    for pair in qs.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            out[k] = v
    return out


# ═══════════════════════════════════════════════════════════════════════════
# LEVEL 1 — URL correctness (pure unit tests, no network)
# ═══════════════════════════════════════════════════════════════════════════

class TestMakeNormalization:
    def test_mercedes_short(self):
        assert normalize_make("mercedes") == "Mercedes-Benz"

    def test_mercedes_benz_passthrough(self):
        assert normalize_make("Mercedes-Benz") == "Mercedes-Benz"

    def test_chevy(self):
        assert normalize_make("Chevy") == "Chevrolet"

    def test_vw(self):
        assert normalize_make("VW") == "Volkswagen"

    def test_unknown_passthrough(self):
        assert normalize_make("Honda") == "Honda"


class TestCarGurusEntityIds:
    """Spot-check a handful of important entries that were previously wrong."""

    def test_lexus_tx_base_has_entity(self):
        assert CG_ENTITY_IDS.get("lexus tx") == 3343

    def test_lexus_tx_500h_points_to_hybrid_id(self):
        assert CG_ENTITY_IDS.get("lexus tx 500h") == 3345

    def test_lexus_tx_hybrid_points_to_hybrid_id(self):
        assert CG_ENTITY_IDS.get("lexus tx hybrid") == 3345

    def test_lexus_tx_base_and_hybrid_are_different(self):
        assert CG_ENTITY_IDS["lexus tx"] != CG_ENTITY_IDS["lexus tx hybrid"]


class TestCarGurusURL:
    """Level 1 — build CarGurus URLs and assert shape + params."""

    def test_used_honda_crv_has_entity_url(self):
        url = cg_url("Honda", "CR-V", "92782", 40000, "Used")
        assert "cargurus.com" in url
        assert "l-Used-Honda-CR-V-d" in url
        assert "google.com" not in url

    def test_used_with_zip_and_price(self):
        url = cg_url("Toyota", "RAV4", "90210", 35000, "Used")
        qp = _qp(url)
        assert qp.get("zip") == "90210"
        assert qp.get("maxPrice") == "35000"

    def test_used_with_exterior_color_slug(self):
        url = cg_url("BMW", "X5", "10001", 80000, "Used", ext_color="silver")
        assert "s-Used-Silver-BMW-X5-d" in url
        assert "_spt408" in url

    def test_new_car_uses_nl_prefix(self):
        url = cg_url("Toyota", "RAV4", "90001", 999999, "New")
        assert "nl-New-Toyota-RAV4-d" in url

    def test_new_car_with_ext_color_uses_query_param(self):
        url = cg_url("Honda", "CR-V", "90001", 999999, "New", ext_color="white")
        assert "nl-New-Honda-CR-V-d" in url
        qp = _qp(url)
        assert qp.get("exteriorColorSimple") == "WHITE"

    def test_interior_color_added_as_query_param(self):
        url = cg_url("Lexus", "TX 500H", "92782", 80000, "Used",
                     ext_color="silver", int_color="black")
        qp = _qp(url)
        assert qp.get("interior_color") == "Black"

    def test_lexus_tx_500h_resolves_to_hybrid_entity(self):
        url = cg_url("Lexus", "TX 500H", "92782", 80000, "Used")
        assert "d3345" in url
        assert "d3343" not in url

    def test_mercedes_benz_gle_used(self):
        url = cg_url("Mercedes-Benz", "GLE", "30301", 70000, "Used")
        assert "Mercedes-Benz-GLE-d2317" in url

    def test_unknown_model_falls_back_to_google(self):
        url = cg_url("Honda", "NonExistentXYZ", "10001", 50000, "Used")
        assert "google.com/search" in url
        assert "cargurus.com" in url  # inside the q= param

    def test_no_color_filter_for_any(self):
        url = cg_url("Ford", "F-150", "75001", 55000, "Used", ext_color="Any")
        assert "l-Used-Ford-F-150-d" in url
        assert "spt" not in url


class TestAutoTraderURL:
    """Level 1 — build AutoTrader URLs and assert shape + params."""

    def test_basic_used_honda_crv(self):
        url = at_url("Honda", "CR-V", "Used", zip_code="92782", price_max=40000)
        assert "autotrader.com" in url
        assert "used-cars" in url
        assert "honda/cr-v" in url

    def test_new_car_path_segment(self):
        url = at_url("Toyota", "RAV4", "New", zip_code="90210")
        assert "new-cars" in url

    def test_mercedes_normalized_in_slug(self):
        url = at_url("Mercedes", "GLE", "Used", zip_code="10001")
        assert "mercedes-benz" in url
        assert "/mercedes/" not in url

    def test_price_max_in_path_and_query(self):
        url = at_url("Ford", "F-150", "Used", zip_code="75001", price_max=55000)
        assert "cars-under-55000" in url
        qp = _qp(url)
        assert qp.get("endPrice") == "55000"

    def test_exterior_color_in_path(self):
        url = at_url("BMW", "X5", "Used", zip_code="10001", ext_color="Silver")
        assert "silver/" in url

    def test_interior_color_query_param(self):
        url = at_url("Honda", "CR-V", "Used", zip_code="92782",
                     int_color="Black")
        qp = _qp(url)
        assert qp.get("intColorSimple") == "BLACK"

    def test_mileage_query_param(self):
        url = at_url("Toyota", "Camry", "Used", zip_code="10001", mileage=50000)
        qp = _qp(url)
        assert qp.get("maxMileage") == "50000"

    def test_radius_query_param(self):
        url = at_url("Ford", "Explorer", "Used", zip_code="60601", radius=100)
        qp = _qp(url)
        assert qp.get("searchRadius") == "100"


class TestCarsDotComURL:
    """Level 1 — build Cars.com URLs and assert shape + params."""

    def test_basic_used_honda_crv(self):
        url = cm_url("Honda", "CR-V", "Used", zip_code="92782", price_max=40000)
        assert "cars.com" in url
        assert "makes[]=honda" in url
        assert "models[]=honda_cr_v" in url
        assert "stock_type=used" in url

    def test_lexus_tx_500h_slug_remapped(self):
        url = cm_url("Lexus", "TX 500H", "Used", zip_code="92782")
        assert "models[]=lexus_tx" in url
        assert "lexus_tx_500h" not in url

    def test_lexus_tx_hybrid_slug_remapped(self):
        url = cm_url("Lexus", "TX Hybrid", "Used", zip_code="92782")
        assert "models[]=lexus_tx" in url

    def test_mercedes_normalized(self):
        url = cm_url("Mercedes", "GLE", "Used", zip_code="10001")
        assert "makes[]=mercedes_benz" in url

    def test_new_stock_type(self):
        url = cm_url("Toyota", "RAV4", "New", zip_code="90210")
        assert "stock_type=new" in url

    def test_exterior_color_slug(self):
        url = cm_url("BMW", "X5", "Used", zip_code="10001", ext_color="Silver")
        assert "exterior_color_slugs[]=silver" in url

    def test_interior_color_slug(self):
        url = cm_url("Honda", "CR-V", "Used", zip_code="92782", int_color="Black")
        assert "interior_color_slugs[]=black" in url

    def test_price_range(self):
        url = cm_url("Ford", "F-150", "Used", zip_code="75001",
                     price_min=30000, price_max=55000)
        assert "price_min=30000" in url
        assert "price_max=55000" in url

    def test_bmw_slug_map_m3(self):
        assert CM_SLUG_MAP.get("bmw_m3_competition") == "bmw_m3"


# ═══════════════════════════════════════════════════════════════════════════
# LEVEL 2 — HTTP reachability (live network, slow marker)
# ═══════════════════════════════════════════════════════════════════════════

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

_LEVEL2_CASES = [
    # (label, make, model, condition, zip)
    ("honda_crv_used",        "Honda",        "CR-V",        "Used", "92782"),
    ("toyota_rav4_hybrid",    "Toyota",       "RAV4 Hybrid", "Used", "90210"),
    ("lexus_tx_500h",         "Lexus",        "TX 500H",     "Used", "92782"),
    ("bmw_x5_used",           "BMW",          "X5",          "Used", "10001"),
    ("ford_f150_used",        "Ford",         "F-150",       "Used", "75001"),
    ("chevrolet_equinox_new", "Chevrolet",    "Equinox",     "New",  "60601"),
    ("mercedes_gle_used",     "Mercedes-Benz","GLE",         "Used", "30301"),
    ("tesla_model_y_used",    "Tesla",        "Model Y",     "Used", "94016"),
    ("porsche_cayenne",       "Porsche",      "Cayenne E-Hybrid", "Used", "10001"),
]


def _level2_id(val):
    if isinstance(val, tuple):
        return val[0]
    return str(val)


@pytest.mark.slow
@pytest.mark.parametrize("label,make,model,cond,zip_code", _LEVEL2_CASES, ids=_level2_id)
class TestLevel2Reachability:
    """
    Verify that generated URLs return HTTP 200 and mention the make/model
    somewhere in the response.  These tests hit live sites so they are
    marked @slow and skipped by default unless you pass -m slow.
    """

    def _get(self, url: str):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
            return r
        except requests.RequestException as exc:
            pytest.skip(f"Network error: {exc}")

    def test_cargurus_reachable(self, label, make, model, cond, zip_code):
        url = cg_url(make, model, zip_code, 999999, cond)
        if "google.com" in url:
            pytest.skip(f"No entity ID for {make} {model} — falls back to Google")
        r = self._get(url)
        assert r.status_code == 200, f"CarGurus {url!r} → {r.status_code}"
        body = r.text.lower()
        assert make.lower().split()[0] in body or model.lower().split()[0] in body, \
            f"Make/model not found in CarGurus page for {url!r}"

    def test_autotrader_reachable(self, label, make, model, cond, zip_code):
        url = at_url(make, model, cond, zip_code=zip_code)
        r = self._get(url)
        assert r.status_code == 200, f"AutoTrader {url!r} → {r.status_code}"
        body = r.text.lower()
        assert make.lower().split()[0] in body or model.lower().split()[0] in body, \
            f"Make/model not found in AutoTrader page for {url!r}"

    def test_carsdotcom_reachable(self, label, make, model, cond, zip_code):
        url = cm_url(make, model, cond, zip_code=zip_code)
        r = self._get(url)
        assert r.status_code == 200, f"Cars.com {url!r} → {r.status_code}"
        body = r.text.lower()
        assert make.lower().split()[0] in body or model.lower().split()[0] in body, \
            f"Make/model not found in Cars.com page for {url!r}"
