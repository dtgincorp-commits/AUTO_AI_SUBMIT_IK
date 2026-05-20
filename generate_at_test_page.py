#!/usr/bin/env python3
"""
Generate AutoTrader URL test page with static + browser-based PASS/FAIL detection.

Static check  — runs immediately, no browser needed:
  PASS  = model has an explicit code entry in AT_MODEL_CODE
  WARN  = code was auto-derived from the model name (unconfirmed)
  FAIL  = code is missing, or a Mercedes model is missing the required MB prefix

Browser check — paste the URL from your address bar after clicking the link:
  PASS  = model slug appears in the URL path  (AutoTrader recognised the code)
  FAIL  = only the city appears in the path   (AutoTrader ignored the code)
  Reason is shown automatically.

Usage:
  .venv/bin/python generate_at_test_page.py
  Opens: at_test_page.html
"""
import sys, os, json, webbrowser
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.url_helpers import (
    at_url, AT_MODEL_CODE, AT_MODEL_SLUG_MAP,
    _at_model_code, _AT_MB_TRIM_CODE,
    _AT_PATH_ONLY_SLUGS, _AT_ZIP_CITY,
)

ZIP_CODE  = "92782"
RADIUS    = 50
CONDITION = "Any"

MODELS = {
    "Acura":         ["MDX"],
    "Audi":          ["A4", "Q5", "A6", "e-tron"],
    "BMW":           ["X5", "3 Series", "X3", "i4", "X7", "i7"],
    "Buick":         ["Enclave", "Envision"],
    "Cadillac":      ["XT5", "Lyriq"],
    "Chevrolet":     ["Silverado 1500", "Tahoe", "Equinox", "Colorado", "Traverse"],
    "Chrysler":      ["Pacifica"],
    "Dodge":         ["Durango"],
    "Ferrari":       ["SF90"],
    "Ford":          ["F-150", "Explorer", "Mustang", "Bronco", "Maverick", "Ranger"],
    "Genesis":       ["GV70", "GV80"],
    "GMC":           ["Sierra 1500", "Sierra 2500", "Terrain", "Acadia"],
    "Honda":         ["CR-V", "Accord", "Pilot", "Civic", "Ridgeline", "Odyssey"],
    "Hyundai":       ["Tucson", "Santa Fe", "Ioniq 5", "Palisade"],
    "Infiniti":      ["QX60"],
    "Jeep":          ["Grand Cherokee", "Wrangler", "Gladiator"],
    "Kia":           ["Telluride", "Sportage", "Sorento", "Carnival"],
    "Lexus":         ["GX", "ES", "IS", "TX", "LX"],
    "Lincoln":       ["Aviator", "Nautilus"],
    "Mazda":         ["CX-5", "CX-50", "CX-90"],
    "Mercedes-Benz": ["C-Class", "E-Class", "S-Class", "G-Class", "CLA", "GLA",
                      "GLB", "GLC", "GLC Coupe", "GLE", "GLS", "AMG GT", "SL",
                      "EQS", "EQS SUV", "EQE", "EQE SUV", "EQB", "CLE", "CLS",
                      "Sprinter", "Maybach GLS 600", "Maybach S 680"],
    "Mitsubishi":    ["Outlander"],
    "Nissan":        ["Rogue", "Altima", "Pathfinder", "Frontier"],
    "Porsche":       ["Cayenne", "Macan", "Taycan", "Panamera"],
    "RAM":           ["1500", "2500"],
    "Subaru":        ["Outback", "Forester", "Crosstrek"],
    "Tesla":         ["Model Y", "Model 3", "Model X"],
    "Toyota":        ["RAV4", "Camry", "Highlander", "Tacoma", "Tundra", "4Runner"],
    "Volkswagen":    ["Tiguan", "Atlas", "Jetta"],
    "Volvo":         ["XC90", "XC60"],
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _is_explicit(model: str) -> bool:
    m = model.lower().strip()
    if m in _AT_MB_TRIM_CODE:
        return True
    slug = AT_MODEL_SLUG_MAP.get(m, m.replace(" ", "-").replace("/", "-"))
    return slug in AT_MODEL_CODE


def static_check(make: str, model: str, url: str):
    """Returns dict with status, reason, code."""
    parsed_url = urlparse(url)
    params     = parse_qs(parsed_url.query)
    code       = params.get("modelCodeList", [""])[0]
    path       = parsed_url.path

    # Mercedes-Benz (and _AT_PATH_ONLY_SLUGS models) use path-based AT routing.
    # AT ignores modelCodeList and routes by model+city slug in the URL path.
    # If makeCodeList or modelCodeList appear in the QUERY string, AT overrides path
    # routing and drops the model filter — they must live in the hash fragment instead.
    m_lower = model.lower().strip()
    model_slug = AT_MODEL_SLUG_MAP.get(m_lower)
    is_path_routed = (make == "Mercedes-Benz" and model_slug is not None) \
                     or model_slug in _AT_PATH_ONLY_SLUGS
    if is_path_routed:
        codelist_in_query = bool(params.get("makeCodeList") or params.get("modelCodeList"))
        if codelist_in_query:
            return dict(status="FAIL",
                        reason=(f"Path-only model — makeCodeList/modelCodeList in query will "
                                f"cause AT to drop /{model_slug}/ filter (must be in hash fragment)"),
                        code=code or "—")
        if "/" + model_slug + "/" in path:
            city_in_path = path.rstrip("/").split("/")[-1]
            city_ok = city_in_path != model_slug
            if city_ok:
                return dict(status="PASS",
                            reason=f"Path-only model — AT routes via /{model_slug}/{city_in_path}/ (code-list in hash, invisible to AT)",
                            code=code or "—")
            return dict(status="WARN",
                        reason=f"Path-only model — /{model_slug}/ in path but no city slug; AT may still drop model filter",
                        code=code or "—")
        return dict(status="FAIL",
                    reason=f"Path-only model — AT ignores modelCodeList for {model}; model slug not in URL path",
                    code=code or "—")

    if not code:
        return dict(status="FAIL", reason="No model code in generated URL", code="—")

    _MB_NO_PREFIX = {"Sprinter"}
    if make == "Mercedes-Benz" and model not in _MB_NO_PREFIX and not code.startswith("MB"):
        return dict(status="FAIL",
                    reason=f"Bad MB code '{code}' — Mercedes requires MB prefix",
                    code=code)

    if not _is_explicit(model):
        return dict(status="WARN",
                    reason=f"Auto-derived code '{code}' — not explicitly mapped, needs browser test",
                    code=code)

    return dict(status="PASS",
                reason=f"Explicit code '{code}' in AT_MODEL_CODE",
                code=code)


def url_slug(model: str) -> str:
    """Slug AutoTrader puts in the URL path when the code is recognised."""
    return model.lower().replace(" ", "-").replace("/", "-").replace(".", "")


# ── build row data ───────────────────────────────────────────────────────────

rows = []
for make, models in MODELS.items():
    for model in models:
        url    = at_url(make, model, CONDITION, zip_code=ZIP_CODE, radius=RADIUS)
        check  = static_check(make, model, url)
        rows.append(dict(
            make=make, model=model,
            code=check["code"],
            url=url,
            static_status=check["status"],
            static_reason=check["reason"],
            expected_slug=url_slug(model),
        ))

total = len(rows)
static_pass = sum(1 for r in rows if r["static_status"] == "PASS")
static_warn = sum(1 for r in rows if r["static_status"] == "WARN")
static_fail = sum(1 for r in rows if r["static_status"] == "FAIL")

rows_json = json.dumps(rows, indent=2)


# ── HTML template ────────────────────────────────────────────────────────────

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AutoTrader URL Test — Static + Browser Check</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: Arial, sans-serif; margin: 0; padding: 0 20px 40px; background: #f7f7f7; }}
  h1 {{ font-size: 1.3em; margin: 16px 0 2px; }}
  p.sub {{ color: #555; font-size: 0.85em; margin: 0 0 12px; }}

  /* sticky summary bar */
  #bar {{ position: sticky; top: 0; z-index: 100; background: #fff; border-bottom: 2px solid #ddd;
          display: flex; align-items: center; gap: 18px; padding: 8px 0; font-size: 0.88em; }}
  #bar b {{ font-size: 1em; }}
  .tag {{ border-radius: 12px; padding: 2px 10px; font-weight: 700; font-size: 0.82em; }}
  .tag-pass {{ background: #d4edda; color: #155724; }}
  .tag-warn {{ background: #fff3cd; color: #856404; }}
  .tag-fail {{ background: #f8d7da; color: #721c24; }}
  .tag-bp   {{ background: #cce5ff; color: #004085; }}
  .tag-bf   {{ background: #f5c6cb; color: #721c24; }}

  /* section headers */
  h2 {{ font-size: 1em; margin: 22px 0 6px; padding-bottom: 4px; border-bottom: 1px solid #ccc; }}

  /* table */
  table {{ width: 100%; border-collapse: collapse; background: #fff; margin-bottom: 4px;
           box-shadow: 0 1px 3px rgba(0,0,0,.07); border-radius: 6px; overflow: hidden; }}
  th {{ text-align: left; background: #f0f0f0; padding: 7px 10px; font-size: 0.8em; color: #444; }}
  td {{ padding: 6px 10px; border-bottom: 1px solid #f0f0f0; font-size: 0.85em; vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  td.code {{ font-family: monospace; font-size: 0.8em; color: #333; }}
  td a {{ color: #1a73e8; text-decoration: none; }}
  td a:hover {{ text-decoration: underline; }}

  /* static status cell */
  .s-pass {{ color: #155724; font-weight: 700; }}
  .s-warn {{ color: #856404; font-weight: 700; }}
  .s-fail {{ color: #721c24; font-weight: 700; }}
  .reason {{ font-size: 0.78em; color: #666; display: block; margin-top: 2px; }}

  /* paste input */
  .paste-wrap {{ display: flex; gap: 4px; align-items: center; }}
  .paste-input {{ flex: 1; font-size: 0.78em; padding: 4px 7px; border: 1px solid #ccc;
                  border-radius: 4px; font-family: monospace; min-width: 0; }}
  .paste-input:focus {{ outline: 2px solid #1a73e8; border-color: #1a73e8; }}
  .btn-clear {{ font-size: 0.72em; padding: 3px 7px; border: 1px solid #ccc; border-radius: 4px;
                background: #fff; cursor: pointer; color: #555; }}
  .btn-clear:hover {{ background: #f0f0f0; }}

  /* browser check cell */
  .bc-empty {{ color: #aaa; font-size: 0.82em; font-style: italic; }}
  .bc-pass  {{ color: #155724; font-weight: 700; font-size: 0.85em; }}
  .bc-fail  {{ color: #721c24; font-weight: 700; font-size: 0.85em; }}
  .bc-reason {{ font-size: 0.75em; color: #555; display: block; margin-top: 2px; }}

  /* export panel */
  #export {{ margin-top: 32px; padding: 14px 18px; background: #fff;
             border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,.07); }}
  #export h3 {{ margin: 0 0 8px; font-size: 0.95em; }}
  #export-out {{ width: 100%; height: 180px; font-family: monospace; font-size: 0.8em;
                 border: 1px solid #ccc; border-radius: 4px; padding: 8px; resize: vertical; }}
  .btn-export {{ margin-top: 6px; padding: 5px 14px; font-size: 0.82em; background: #1a73e8;
                 color: #fff; border: none; border-radius: 4px; cursor: pointer; }}
  .btn-export:hover {{ background: #1558b0; }}
</style>
</head>
<body>

<h1>AutoTrader URL Test — Static + Browser Check</h1>
<p class="sub">
  ZIP: {ZIP_CODE} &nbsp;|&nbsp; Radius: {RADIUS} mi &nbsp;|&nbsp; Condition: {CONDITION} &nbsp;|&nbsp;
  Static: checks code mapping without a browser &nbsp;|&nbsp;
  Browser: click link → copy address-bar URL → paste below → PASS/FAIL auto-detected
</p>

<div id="bar">
  <b>Static analysis ({total} models):</b>
  <span class="tag tag-pass" id="b-spass">✅ PASS: {static_pass}</span>
  <span class="tag tag-warn" id="b-swarn">⚠️ WARN: {static_warn}</span>
  <span class="tag tag-fail" id="b-sfail">❌ FAIL: {static_fail}</span>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <b>Browser verified:</b>
  <span class="tag tag-bp" id="b-bpass">🟢 PASS: 0</span>
  <span class="tag tag-bf" id="b-bfail">🔴 FAIL: 0</span>
  <button class="btn-export" style="margin-left:auto" onclick="buildExport()">📋 Export Results</button>
</div>

<div id="sections"></div>

<div id="export">
  <h3>Export — paste into chat</h3>
  <textarea id="export-out" placeholder="Click 'Export Results' above to generate a summary..."></textarea>
</div>

<script>
const ROWS = {rows_json};

// group by make
const makes = {{}};
for (const r of ROWS) {{
  if (!makes[r.make]) makes[r.make] = [];
  makes[r.make].push(r);
}}

const sectionsEl = document.getElementById('sections');
let rowIndex = 0;

for (const [make, models] of Object.entries(makes)) {{
  const h2 = document.createElement('h2');
  h2.textContent = make;
  sectionsEl.appendChild(h2);

  const table = document.createElement('table');
  table.innerHTML = `<tr>
    <th style="width:110px">Model</th>
    <th style="width:90px">Code</th>
    <th>AutoTrader Link</th>
    <th style="width:130px">Static Check</th>
    <th style="width:280px">Paste URL → Browser Check</th>
  </tr>`;

  for (const r of models) {{
    const i = rowIndex++;
    const tr = document.createElement('tr');
    tr.dataset.idx = i;
    tr.dataset.slug = r.expected_slug;
    tr.dataset.make = make.toLowerCase().replace(/ /g, '-');

    // static badge
    const sClass = r.static_status === 'PASS' ? 's-pass' : r.static_status === 'WARN' ? 's-warn' : 's-fail';
    const sIcon  = r.static_status === 'PASS' ? '✅ PASS' : r.static_status === 'WARN' ? '⚠️ WARN' : '❌ FAIL';

    tr.innerHTML = `
      <td>${{r.model}}</td>
      <td class="code">${{r.code}}</td>
      <td><a href="${{r.url}}" target="_blank">Open AutoTrader ↗</a></td>
      <td class="${{sClass}}">${{sIcon}}<span class="reason">${{r.static_reason}}</span></td>
      <td>
        <div class="paste-wrap">
          <input class="paste-input" type="text" placeholder="Paste final URL from address bar…"
                 oninput="checkUrl(this, ${{i}})" />
          <button class="btn-clear" onclick="clearRow(${{i}})">✕</button>
        </div>
        <div class="bc-result bc-empty" id="bc-${{i}}">— not checked yet</div>
      </td>`;
    table.appendChild(tr);
  }}
  sectionsEl.appendChild(table);
}}

// ── browser check logic ───────────────────────────────────────────────────

function checkUrl(input, idx) {{
  const raw = input.value.trim();
  const el  = document.getElementById('bc-' + idx);
  if (!raw) {{
    el.className = 'bc-result bc-empty';
    el.innerHTML = '— not checked yet';
    updateBar();
    return;
  }}

  let parsed;
  try {{ parsed = new URL(raw); }} catch(e) {{
    el.className = 'bc-result bc-fail';
    el.innerHTML = '🔴 FAIL <span class="bc-reason">Could not parse URL — check the paste</span>';
    updateBar();
    return;
  }}

  const path  = parsed.pathname.toLowerCase();          // e.g. /cars-for-sale/new-cars/bmw/i7/tustin-ca
  const parts = path.split('/').filter(p => p);         // ['cars-for-sale','new-cars','bmw','i7','tustin-ca']

  // find the row to get expected slug
  const tr   = document.querySelector(`tr[data-idx="${{idx}}"]`);
  const slug = tr.dataset.slug;                         // e.g. 'i7'
  const make = tr.dataset.make;                         // e.g. 'bmw'

  // find make position in path
  const makeIdx = parts.indexOf(make);
  const afterMake = makeIdx >= 0 ? parts.slice(makeIdx + 1) : parts;

  // city-state pattern: word(s)-2letterabbr, e.g. 'tustin-ca', 'los-angeles-ca'
  const cityPat = /^[a-z0-9]+-[a-z]{{2}}$/;

  // check if slug appears before the city segment
  const nonCity = afterMake.filter(p => !cityPat.test(p));

  if (nonCity.includes(slug) || nonCity.some(p => p.startsWith(slug))) {{
    el.className = 'bc-result bc-pass';
    el.innerHTML = `🟢 PASS <span class="bc-reason">'${{slug}}' found in URL path — code recognised by AutoTrader</span>`;
  }} else if (afterMake.length === 1 && cityPat.test(afterMake[0])) {{
    el.className = 'bc-result bc-fail';
    el.innerHTML = `🔴 FAIL <span class="bc-reason">City-only URL — AutoTrader ignored the model code (bad code)</span>`;
  }} else if (afterMake.length === 0) {{
    el.className = 'bc-result bc-fail';
    el.innerHTML = `🔴 FAIL <span class="bc-reason">No model or city in path — URL unexpected</span>`;
  }} else {{
    // different model in path?
    const found = nonCity[0] || '?';
    el.className = 'bc-result bc-fail';
    el.innerHTML = `🔴 FAIL <span class="bc-reason">Expected '${{slug}}' but found '${{found}}' in path — wrong model code</span>`;
  }}

  updateBar();
}}

function clearRow(idx) {{
  const input = document.querySelector(`tr[data-idx="${{idx}}"] .paste-input`);
  input.value = '';
  checkUrl(input, idx);
}}

function updateBar() {{
  const bp = document.querySelectorAll('.bc-pass').length;
  const bf = document.querySelectorAll('.bc-fail').length;
  document.getElementById('b-bpass').textContent = '🟢 PASS: ' + bp;
  document.getElementById('b-bfail').textContent = '🔴 FAIL: ' + bf;
}}

// ── export ────────────────────────────────────────────────────────────────

function buildExport() {{
  const lines = ['AutoTrader URL Test Results', '='.repeat(50), ''];

  // static summary
  const sp = document.querySelectorAll('.s-pass').length;
  const sw = document.querySelectorAll('.s-warn').length;
  const sf = document.querySelectorAll('.s-fail').length;
  lines.push('STATIC CHECK');
  lines.push(`  PASS: ${{sp}}  WARN: ${{sw}}  FAIL: ${{sf}}`);
  lines.push('');

  // browser summary
  const bp = document.querySelectorAll('.bc-pass').length;
  const bf = document.querySelectorAll('.bc-fail').length;
  lines.push('BROWSER CHECK');
  lines.push(`  PASS: ${{bp}}  FAIL: ${{bf}}`);
  lines.push('');

  // failing rows
  const failRows = document.querySelectorAll('.bc-fail');
  if (failRows.length > 0) {{
    lines.push('FAILED (need fixing):');
    failRows.forEach(el => {{
      const tr  = el.closest('tr');
      const idx = tr.dataset.idx;
      const row = ROWS[idx];
      const reason = el.querySelector('.bc-reason')?.textContent || '';
      lines.push(`  - ${{row.make}} ${{row.model}} (code=${{row.code}}): ${{reason}}`);
    }});
    lines.push('');
  }}

  // static fails/warns
  const warnFail = document.querySelectorAll('.s-warn, .s-fail');
  const staticIssues = [];
  warnFail.forEach(el => {{
    const tr  = el.closest('tr');
    if (!tr) return;
    const idx = tr.dataset.idx;
    const row = ROWS[idx];
    const r   = el.querySelector('.reason')?.textContent || '';
    staticIssues.push(`  - ${{row.make}} ${{row.model}}: ${{r}}`);
  }});
  if (staticIssues.length > 0) {{
    lines.push('STATIC WARN/FAIL:');
    lines.push(...staticIssues);
  }}

  document.getElementById('export-out').value = lines.join('\\n');
}}
</script>
</body>
</html>"""

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "at_test_page.html")
with open(OUT, "w") as f:
    f.write(HTML)

print(f"Generated: {OUT}")
print(f"  {total} models  |  static PASS: {static_pass}  WARN: {static_warn}  FAIL: {static_fail}")
webbrowser.open(f"file://{OUT}")
