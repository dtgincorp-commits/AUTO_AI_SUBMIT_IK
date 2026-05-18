"""
End-to-end integration test: NL parser output → AutoTrader URL → HTTP check.

This is the missing link between test_nl_parser_models.py (parser only)
and test_link_validation.py (hand-written class names only).

It tests the REAL chain a user triggers:
  1. User types a natural language query with a variant number
  2. NL parser extracts make + model
  3. URL builder converts that to an AutoTrader slug
  4. AutoTrader must return 200 (not 404 / redirect away from the model page)

Run before deploy:
  .venv/bin/python -m pytest tests/test_parser_to_url.py -v --timeout=30
"""
import time
import pytest
import requests
from agents.nl_parser import parse_query
from agents.url_helpers import at_url, normalize_make

_ZIP   = "92782"
_DELAY = 1.5

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
})

# ── Test cases ────────────────────────────────────────────────────────────────
# Format: (user_query, expected_at_slug)
# expected_at_slug: the segment that should appear after make in the AT URL.
# This is what AutoTrader actually uses — NOT what the parser returns.

CASES = [
    # ── Mercedes variant queries (the original bug) ────────────────────────────
    ("Mercedes GLA 450 near 92782",           "gla"),
    ("GLA 450 92782",                         "gla"),
    ("Mercedes GLE450e near 92782",           "gle"),
    ("Mercedes GLE 450 near 92782",           "gle"),
    ("Mercedes GLC 300 near 92782",           "glc"),
    ("Mercedes GLC300e near 92782",           "glc"),
    ("Mercedes GLS 580 near 92782",           "gls"),
    ("Mercedes C300 near 92782",              "c-class"),
    ("Mercedes E350 near 92782",              "e-class"),
    ("Mercedes S580 near 92782",              "s-class"),
    ("Mercedes G550 near 92782",              "g-class"),
    ("Mercedes AMG GT 63 near 92782",         "amg-gt"),
    ("Mercedes EQS 450 near 92782",           "eqs"),
    ("Mercedes EQE 350 near 92782",           "eqe"),
    ("Mercedes EQB 300 near 92782",           "eqb"),
    ("Mercedes CLA 250 near 92782",           "cla"),
    ("Mercedes GLA 250 near 92782",           "gla"),
    ("Mercedes GLB 250 near 92782",           "glb"),
    ("Mercedes SL 55 near 92782",             "sl"),
    ("Mercedes CLE 300 near 92782",           "cle"),
    # ── Other brands with variant numbers ─────────────────────────────────────
    ("BMW X5 xDrive40i near 92782",           "x5"),
    ("Audi Q5 quattro near 92782",            "q5"),
    ("Toyota RAV4 AWD near 92782",            "rav4"),
    ("GMC Sierra 2500 Denali HD near 92782",  "sierra-2500"),
]


def _get(url: str):
    try:
        r = _SESSION.get(url, timeout=15, allow_redirects=True)
        return r.status_code, r.url
    except Exception as e:
        return 0, str(e)


@pytest.mark.parametrize("query,expected_slug", CASES)
def test_parser_to_autotrader_url(query, expected_slug):
    # Step 1: parse
    parsed, err = parse_query(query)
    assert not err, f"Parser error for {query!r}: {err}"
    assert parsed.get("make"),  f"No make parsed from: {query!r}"
    assert parsed.get("model"), f"No model parsed from: {query!r}"

    make  = normalize_make(parsed["make"])
    model = parsed["model"]
    cond  = parsed.get("condition", "Any")

    # Step 2: build URL
    url = at_url(make, model, cond, _ZIP)
    make_slug = make.lower().replace(" ", "-")
    assert make_slug in url, f"Make slug missing from URL: {url}"

    # Step 3: verify expected slug is in URL
    assert expected_slug in url.lower(), (
        f"Expected slug '{expected_slug}' not found in URL\n"
        f"  Query:  {query!r}\n"
        f"  Parsed: make={make!r}, model={model!r}\n"
        f"  URL:    {url}"
    )

    # Step 4: hit AutoTrader
    time.sleep(_DELAY)
    status, final_url = _get(url)

    if status == 0:
        pytest.fail(f"Connection error for {query!r}\n  URL: {url}")
    if status == 404:
        pytest.fail(
            f"AutoTrader 404 — slug '{expected_slug}' is wrong for {query!r}\n"
            f"  Parsed model: {model!r}\n"
            f"  URL: {url}"
        )
    if status == 403:
        pytest.skip(f"AutoTrader blocked bot (403) — URL format assumed valid: {url}")

    # Final check: make sure we didn't land on the wrong page
    assert make_slug in final_url.lower(), (
        f"AutoTrader redirected away from {make} page\n"
        f"  Built:  {url}\n"
        f"  Landed: {final_url}"
    )
