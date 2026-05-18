"""
End-to-end integration test: NL parser output → AutoTrader URL → HTTP check.

Tests the full chain:
  1. User types a natural language query
  2. NL parser extracts make + model
  3. URL builder converts that to an AutoTrader URL with modelCodeList param
  4. AutoTrader must return 200 (not 404)

Run before deploy:
  .venv/bin/python -m pytest tests/test_parser_to_url.py -v --timeout=30
"""
import time
import pytest
import requests
from agents.nl_parser import parse_query
from agents.url_helpers import at_url, normalize_make, _at_model_code

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
# Format: (user_query, expected_modelCodeList_value)
# expected_modelCodeList_value: what should appear as modelCodeList=X in the URL

CASES = [
    # ── Mercedes variant queries ───────────────────────────────────────────────
    ("Mercedes GLA 450 near 92782",           "GLA"),
    ("GLA 450 92782",                         "GLA"),
    ("Mercedes GLE450e near 92782",           "GLE"),
    ("Mercedes GLE 450 near 92782",           "GLE"),
    ("Mercedes GLC 300 near 92782",           "GLC"),
    ("Mercedes GLC300e near 92782",           "GLC"),
    ("Mercedes GLS 580 near 92782",           "GLS"),
    ("Mercedes C300 near 92782",              "C_CLASS"),
    ("Mercedes E350 near 92782",              "E_CLASS"),
    ("Mercedes S580 near 92782",              "S_CLASS"),
    ("Mercedes G550 near 92782",              "G_CLASS"),
    ("Mercedes AMG GT 63 near 92782",         "AMG_GT"),
    ("Mercedes EQS 450 near 92782",           "EQS"),
    ("Mercedes EQE 350 near 92782",           "EQE"),
    ("Mercedes EQB 300 near 92782",           "EQB"),
    ("Mercedes CLA 250 near 92782",           "CLA"),
    ("Mercedes GLA 250 near 92782",           "GLA"),
    ("Mercedes GLB 250 near 92782",           "GLB"),
    ("Mercedes SL 55 near 92782",             "SL"),
    ("Mercedes CLE 300 near 92782",           "CLE"),
    # ── Other brands ──────────────────────────────────────────────────────────
    ("BMW X5 xDrive40i near 92782",           "X5"),
    ("Audi Q5 quattro near 92782",            "Q5"),
    ("Toyota RAV4 AWD near 92782",            "RAV4"),
    ("GMC Sierra 2500 Denali HD near 92782",  "SIERRA_2500"),
]


def _get(url: str):
    try:
        r = _SESSION.get(url, timeout=15, allow_redirects=True)
        return r.status_code, r.url
    except Exception as e:
        return 0, str(e)


@pytest.mark.parametrize("query,expected_code", CASES)
def test_parser_to_autotrader_url(query, expected_code):
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

    # Step 3: verify modelCodeList param is in URL
    assert f"modelCodeList={expected_code}" in url, (
        f"Expected modelCodeList={expected_code} not found in URL\n"
        f"  Query:  {query!r}\n"
        f"  Parsed: make={make!r}, model={model!r}\n"
        f"  Code:   {_at_model_code(model)!r}\n"
        f"  URL:    {url}"
    )

    # Step 4: hit AutoTrader
    time.sleep(_DELAY)
    status, final_url = _get(url)

    if status == 0:
        pytest.fail(f"Connection error for {query!r}\n  URL: {url}")
    if status == 404:
        pytest.fail(
            f"AutoTrader 404 for {query!r}\n"
            f"  Parsed model: {model!r}\n"
            f"  URL: {url}"
        )
    if status == 403:
        pytest.skip(f"AutoTrader blocked bot (403) — URL format assumed valid: {url}")

    # Final check: make slug still in final URL
    assert make_slug in final_url.lower(), (
        f"AutoTrader redirected away from {make} page\n"
        f"  Built:  {url}\n"
        f"  Landed: {final_url}"
    )
