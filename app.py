from dotenv import load_dotenv
load_dotenv(override=True)  # override=True ensures .env always wins over shell environment

import os
import streamlit as st

# Push LangSmith secrets into os.environ before any LangChain imports.
# On Streamlit Cloud secrets live in st.secrets, not os.environ — LangChain
# reads os.environ directly so we bridge them here first.
try:
    _ls_key = st.secrets.get("LANGSMITH_API_KEY") or st.secrets.get("LANGCHAIN_API_KEY")
    if _ls_key:
        os.environ["LANGSMITH_API_KEY"]    = _ls_key
        os.environ["LANGCHAIN_API_KEY"]    = _ls_key
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_TRACING"]    = "true"
        os.environ["LANGCHAIN_PROJECT"]    = st.secrets.get("LANGCHAIN_PROJECT", "AUTO_AI")
except Exception:
    pass
from agents.models import CarPreferences
from agents.orchestrator import run_pipeline
from agents.url_helpers import (
    CG_ENTITY_IDS as _CG_ENTITY_IDS, CG_COLOR_SPT as _CG_COLOR_SPT,
    CM_SLUG_MAP as _CM_SLUG_MAP, normalize_make as _normalize_make,
    cg_url as _cg_url_fn, at_url as _at_url_fn, cm_url as _cm_url_fn,
    zip_from_location as _zip_from_location,
    _at_model_code as _at_model_code_fn, AT_MAKE_CODE as _AT_MAKE_CODE,
)

def _reverse_geocode(lat: float, lon: float) -> str:
    """Convert lat/lon to 'City, ST ZIP' using BigDataCloud (free, no key)."""
    try:
        import requests as _req
        r = _req.get(
            "https://api.bigdatacloud.net/data/reverse-geocode-client",
            params={"latitude": lat, "longitude": lon, "localityLanguage": "en"},
            timeout=5,
        )
        d = r.json()
        city     = d.get("city") or d.get("locality", "")
        state    = d.get("principalSubdivisionCode", "").replace("US-", "")
        postcode = d.get("postcode", "")
        if city and state:
            return f"{city}, {state} {postcode}".strip()
    except Exception:
        pass
    return ""


st.set_page_config(
    page_title="AUTO AI - Car Discovery",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 AUTO AI — Car Discovery Agent")
st.caption("Powered by LangChain · Find your perfect car via AI agents · build ce3d331")

RESULTS_PER_PAGE = 18   # 3 columns × 6 rows per page

# ── Session state defaults ──────────────────────────────────────────────────
_SS_DEFAULTS = {
    "p_make": "", "p_model": "", "p_trim": "",
    "p_price_min": 20000, "p_price_max": 50000,
    "p_condition": "Any", "p_exterior_color": "Any", "p_interior_color": "Any",
    "p_max_mileage": 50000, "p_location": "", "p_radius_miles": 50,
    "results_page": 0,
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Natural Language Search ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@700;900&display=swap');
.nl-heading {
    font-family: 'Exo 2', sans-serif;
    font-size: 2.1rem;
    font-weight: 900;
    background: linear-gradient(90deg, #f97316, #facc15, #22d3ee, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 0.5px;
    margin-bottom: 14px;
    text-shadow: none;
}
div[data-testid="stTextInput"]:has(input[aria-label="nl"]) input {
    background-color: #ffffff !important;
    color: #111111 !important;
    caret-color: #111111 !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    border: 3px solid #2563eb !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
    box-shadow: 0 0 14px rgba(37,99,235,0.5) !important;
}
div[data-testid="stTextInput"]:has(input[aria-label="nl"]) input::placeholder {
    color: #9ca3af !important;
    font-weight: 400 !important;
}
div[data-testid="stTextInput"]:has(input[aria-label="nl"]) input:focus {
    border-color: #1d4ed8 !important;
    box-shadow: 0 0 22px rgba(37,99,235,0.75) !important;
}
div[data-testid="stForm"] div[data-testid="stColumn"]:last-child button,
div[data-testid="stForm"] div[data-testid="stColumn"]:last-child button:focus {
    background: linear-gradient(135deg, #f97316 0%, #dc2626 100%) !important;
    color: #ffffff !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    border: none !important;
    border-radius: 10px !important;
    min-height: 52px !important;
    box-shadow: 0 4px 18px rgba(220, 38, 38, 0.6) !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
div[data-testid="stForm"] div[data-testid="stColumn"]:last-child button:hover {
    transform: scale(1.04) !important;
    box-shadow: 0 6px 28px rgba(220, 38, 38, 0.8) !important;
}
div[data-testid="stForm"] div[data-testid="stColumn"]:last-child button:active {
    transform: scale(0.97) !important;
}
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-last-child(2) button,
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-last-child(2) button:focus {
    background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%) !important;
    color: #ffffff !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    border: none !important;
    border-radius: 10px !important;
    min-height: 52px !important;
    box-shadow: 0 4px 18px rgba(99, 102, 241, 0.55) !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-last-child(2) button:hover {
    transform: scale(1.04) !important;
    box-shadow: 0 6px 28px rgba(99, 102, 241, 0.8) !important;
}
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-last-child(2) button:active {
    transform: scale(0.97) !important;
}
div[data-testid="stForm"] { border: none !important; padding: 0 !important; }
</style>

<div class="nl-heading">🚀 &nbsp;What car are you hunting for?</div>
""", unsafe_allow_html=True)

with st.expander("💡 Search tips — make, model, trim & powertrain", expanded=False):
    st.markdown("""
**Always include make + model.** Don't just say "BMW M Sport" — include the model: "BMW X5 M Sport".

| What you want | What to type |
|---|---|
| Specific trim | "Honda CR-V **TrailSport**", "Ford F-150 **Lariat**", "Jeep Wrangler **Rubicon**" |
| Option package | "BMW X5 **M Sport**", "Audi Q7 **S line**" — we try it, but the car site may show all trims for that model |
| Hybrid + trim | "Toyota RAV4 **Hybrid XSE**", "Honda CR-V **Hybrid TrailSport**" — just say it naturally |
| Lexus powertrain | "Lexus TX **500h**", "Lexus RX **500h**" — powertrain is part of the model on Lexus |
| Porsche variant | "Porsche Cayenne **S**", "Porsche Macan **GTS**" — variant goes in the URL path |

**The green/red AT URL check** under Your Search tells you instantly whether make, model, and trim made it into the link.
""")

with st.form("nl_form", clear_on_submit=False):
    _nl_col, _build_col, _btn_col = st.columns([4, 1.6, 1.6])
    with _nl_col:
        _nl_query = st.text_input(
            "nl",
            placeholder='e.g. "Used Honda CR-V under $30k near Irvine CA, max 60k miles"',
            label_visibility="collapsed",
            key="nl_query_input",
        )
    with _build_col:
        _build_btn = st.form_submit_button("🗺️ Build Search", use_container_width=True)
    with _btn_col:
        _nl_btn = st.form_submit_button("🔍 Find Cars", use_container_width=True)

if "nl_parse_msg" in st.session_state:
    _msg_type, _msg_text = st.session_state.pop("nl_parse_msg")
    if _msg_type == "success":
        st.success(_msg_text)
    else:
        st.warning(_msg_text)

_RADIUS_SNAP = [10, 25, 50, 75, 100, 200, 300, 400, 500]
def _snap_radius(r: int) -> int:
    return min(_RADIUS_SNAP, key=lambda v: abs(v - r))

if _build_btn:
    if _nl_query.strip():
        with st.spinner("Understanding your request..."):
            from agents.nl_parser import parse_query as _parse_query
            _parsed, _parse_err = _parse_query(_nl_query.strip())
        if _parse_err:
            st.error(f"Could not parse your request: {_parse_err}")
        else:
            _COLOR_EXT = ["Any", "White", "Black", "Silver", "Gray", "Red", "Blue", "Green", "Other"]
            _COLOR_INT = ["Any", "Black", "Beige", "Gray", "Brown", "White", "Red", "Other"]
            _COND      = ["Any", "Used", "New", "Certified Pre-Owned (CPO)"]
            # Sync sidebar fields — same logic as Find Cars
            st.session_state["p_price_min"]      = 0
            st.session_state["p_price_max"]      = 999000
            st.session_state["p_condition"]      = "Any"
            st.session_state["p_exterior_color"] = "Any"
            st.session_state["p_interior_color"] = "Any"
            st.session_state["p_max_mileage"]    = 500000
            st.session_state["p_trim"]           = ""
            st.session_state["p_radius_miles"]   = 50
            if _parsed.get("make"):      st.session_state["p_make"]          = _parsed["make"]
            if _parsed.get("model"):     st.session_state["p_model"]         = _parsed["model"]
            if _parsed.get("trim"):      st.session_state["p_trim"]          = _parsed["trim"]
            if _parsed.get("price_min"): st.session_state["p_price_min"]     = int(_parsed["price_min"])
            if _parsed.get("price_max"): st.session_state["p_price_max"]     = int(_parsed["price_max"])
            if _parsed.get("condition") and _parsed["condition"] in _COND:
                st.session_state["p_condition"] = _parsed["condition"]
            if _parsed.get("exterior_color") and _parsed["exterior_color"] in _COLOR_EXT:
                st.session_state["p_exterior_color"] = _parsed["exterior_color"]
            if _parsed.get("interior_color") and _parsed["interior_color"] in _COLOR_INT:
                st.session_state["p_interior_color"] = _parsed["interior_color"]
            if _parsed.get("max_mileage"):
                st.session_state["p_max_mileage"] = int(_parsed["max_mileage"])
            if _parsed.get("location"):
                st.session_state["p_location"]    = _parsed["location"]
            if _parsed.get("radius_miles"):
                st.session_state["p_radius_miles"] = _snap_radius(int(_parsed["radius_miles"]))
            st.session_state["_search_builder"] = True
            st.rerun()
    else:
        # No NL query — just show the card using current sidebar values
        st.session_state["_search_builder"] = True
        st.rerun()

if _nl_btn:
    if _nl_query.strip():
        _query_changed = _nl_query.strip() != st.session_state.get("_last_parsed_query", "")
        if _query_changed:
            with st.spinner("Understanding your request..."):
                from agents.nl_parser import parse_query as _parse_query
                _parsed, _parse_err = _parse_query(_nl_query.strip())
            if _parse_err:
                st.error(f"Could not parse your request: {_parse_err}")
                st.stop()
            _COLOR_EXT = ["Any", "White", "Black", "Silver", "Gray", "Red", "Blue", "Green", "Other"]
            _COLOR_INT = ["Any", "Black", "Beige", "Gray", "Brown", "White", "Red", "Other"]
            _COND = ["Any", "Used", "New", "Certified Pre-Owned (CPO)"]
            # Reset all optional fields to clean defaults before applying parsed values.
            # Prevents stale values from a previous search bleeding into this one.
            st.session_state["p_price_min"]      = 0
            st.session_state["p_price_max"]      = 999000
            st.session_state["p_condition"]      = "Any"
            st.session_state["p_exterior_color"] = "Any"
            st.session_state["p_interior_color"] = "Any"
            st.session_state["p_max_mileage"]    = 500000
            st.session_state["p_trim"]           = ""
            st.session_state["p_radius_miles"]   = 50
            if _parsed.get("make"):         st.session_state["p_make"]          = _parsed["make"]
            if _parsed.get("model"):        st.session_state["p_model"]         = _parsed["model"]
            if _parsed.get("trim"):         st.session_state["p_trim"]          = _parsed["trim"]
            if _parsed.get("price_min"):    st.session_state["p_price_min"]     = int(_parsed["price_min"])
            if _parsed.get("price_max"):    st.session_state["p_price_max"]     = int(_parsed["price_max"])
            if _parsed.get("condition") and _parsed["condition"] in _COND:
                st.session_state["p_condition"] = _parsed["condition"]
            if _parsed.get("exterior_color") and _parsed["exterior_color"] in _COLOR_EXT:
                st.session_state["p_exterior_color"] = _parsed["exterior_color"]
            if _parsed.get("interior_color") and _parsed["interior_color"] in _COLOR_INT:
                st.session_state["p_interior_color"] = _parsed["interior_color"]
            if _parsed.get("max_mileage"):
                st.session_state["p_max_mileage"]   = int(_parsed["max_mileage"])
            if _parsed.get("location"):
                st.session_state["p_location"]      = _parsed["location"]
            if _parsed.get("radius_miles"):
                st.session_state["p_radius_miles"]  = max(10, min(200, int(_parsed["radius_miles"])))
            st.session_state["_last_parsed_query"] = _nl_query.strip()
            # Log query to local CSV
            try:
                import csv, datetime as _dt
                _log_path = os.path.join(os.path.dirname(__file__), "query_log.csv")
                _log_exists = os.path.exists(_log_path)
                with open(_log_path, "a", newline="", encoding="utf-8") as _lf:
                    _lw = csv.writer(_lf)
                    if not _log_exists:
                        _lw.writerow(["timestamp", "raw_query", "make", "model", "trim", "condition", "location", "price_min", "price_max", "exterior_color", "interior_color", "max_mileage", "radius_miles"])
                    _lw.writerow([
                        _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        _nl_query.strip(),
                        _parsed.get("make", ""), _parsed.get("model", ""), _parsed.get("trim", ""),
                        _parsed.get("condition", ""), _parsed.get("location", ""),
                        _parsed.get("price_min", ""), _parsed.get("price_max", ""),
                        _parsed.get("exterior_color", ""), _parsed.get("interior_color", ""),
                        _parsed.get("max_mileage", ""), _parsed.get("radius_miles", ""),
                    ])
            except Exception:
                pass
            # If parser found no location, check if sidebar already has one (from GPS detect)
            if not _parsed.get("location") and st.session_state.get("p_location"):
                _parsed["location"] = st.session_state["p_location"]
            _has_required = _parsed.get("make") and _parsed.get("model") and _parsed.get("location")
            if not _has_required:
                _missing = [f for f, v in [("make", _parsed.get("make")), ("model", _parsed.get("model")), ("location", _parsed.get("location"))] if not v]
                st.session_state["nl_parse_msg"] = (
                    "warning",
                    f"Please also specify **{', '.join(_missing)}** — filled what I could, check the sidebar.",
                )
                st.rerun()

        # Query unchanged — sidebar already has valid fields from the previous parse; run directly
        st.session_state["_nl_auto_run"] = True
    else:
        st.warning("Please type something first.")

st.divider()

# Read results/meta early so Build Search card can access them
_last_result = st.session_state.get("_last_result")
_last_meta   = st.session_state.get("_last_meta", {})

def _render_vin_widget(prefs, key_prefix=""):
    with st.container(border=True):
        st.markdown("**📌 Pin a car by VIN**")
        st.caption("Paste a VIN from AutoTrader, Cars.com, or anywhere else")
        _fc, _lc = st.columns(2)
        with _fc:
            st.text_input("First Name", placeholder="First", key=f"{key_prefix}vin_first_name")
        with _lc:
            st.text_input("Last Name", placeholder="Last", key=f"{key_prefix}vin_last_name")
        _vin_input = st.text_input(
            "VIN", placeholder="e.g. 5UX13EU03T9384714",
            label_visibility="collapsed", key=f"{key_prefix}vin_lookup_input",
        )
        _vin_btn = st.button("Look Up", key=f"{key_prefix}vin_lookup_btn", use_container_width=True)
        if _vin_btn and _vin_input:
            if not prefs:
                st.warning("Run a search first so VIN results can be scored.")
            else:
                with st.spinner("Decoding VIN..."):
                    from agents.search_agent import lookup_vin_listing
                    from agents.ranking_agent import run_ranking_agent as _rank
                    _vin_listing, _vin_err = lookup_vin_listing(_vin_input.strip(), prefs)
                if _vin_err:
                    st.error(_vin_err)
                else:
                    _vin_scored = _rank(prefs, [_vin_listing])
                    _vin_listing = _vin_scored[0] if _vin_scored else _vin_listing
                    _added = st.session_state.setdefault("vin_added_listings", [])
                    if not any(l.vin == _vin_listing.vin for l in _added):
                        _added.append(_vin_listing)
                        from agents.search_agent import fetch_vin_details as _fvd2
                        st.session_state.setdefault("vin_details", {})[_vin_input.strip().upper()] = _fvd2(_vin_input.strip())
                        st.success(f"Added: **{_vin_listing.title}** — shown at the top of results.")
                        st.rerun()
                    else:
                        st.info("This VIN is already in your results.")
        _added_list = st.session_state.get("vin_added_listings", [])
        if _added_list:
            st.markdown(f"**{len(_added_list)} pinned:**")
            for _av in _added_list:
                _price_str = f"${_av.asking_price:,}" if _av.asking_price else "N/A"
                _det2 = st.session_state.get("vin_details", {}).get(_av.vin, {})
                with st.expander(f"📌 {_av.title}  —  {_price_str}", expanded=True):
                    if _det2.get("photo_url"):
                        st.image(_det2["photo_url"], use_container_width=True)
                    else:
                        _gi2 = _det2.get("google_images_url", "")
                        _bi2 = _det2.get("bing_images_url", "")
                        if _gi2:
                            st.markdown(
                                f"📸 **Photos:** &nbsp;[Google Images]({_gi2}) &nbsp;|&nbsp; [Bing Images]({_bi2})",
                                unsafe_allow_html=True,
                            )
                    _rc1, _rc2 = st.columns(2)
                    with _rc1:
                        if _det2.get("year"):      st.markdown(f"**Year:** {_det2['year']}")
                        if _det2.get("make"):      st.markdown(f"**Make:** {_det2['make']}")
                        if _det2.get("model"):     st.markdown(f"**Model:** {_det2['model']}")
                        if _det2.get("trim"):      st.markdown(f"**Trim:** {_det2['trim']}")
                        if _det2.get("body_type"): st.markdown(f"**Body:** {_det2['body_type']}")
                    with _rc2:
                        if _det2.get("engine"):    st.markdown(f"**Engine:** {_det2['engine']}")
                        if _det2.get("fuel_type"): st.markdown(f"**Fuel:** {_det2['fuel_type']}")
                        if _det2.get("doors"):     st.markdown(f"**Doors:** {_det2['doors']}")
                        if _det2.get("mileage"):   st.markdown(f"**Mileage:** {_det2['mileage']:,} mi")
                        if _det2.get("price"):     st.markdown(f"**Price:** ${_det2['price']:,}")
                    if _det2.get("features"):
                        st.markdown("**Features:** " + " · ".join(_det2["features"][:12]))
                    if _det2.get("listing_url"):
                        st.markdown(f"[🔗 Search on AutoTrader by VIN]({_det2['listing_url']})")
                    st.divider()
                    _render_vin_actions(_det2, _av, f"{key_prefix}rs_{_av.vin}")
                if st.button("✕ Remove", key=f"{key_prefix}rm_vin_{_av.vin}"):
                    st.session_state["vin_added_listings"] = [l for l in _added_list if l.vin != _av.vin]
                    st.session_state.get("vin_details", {}).pop(_av.vin, None)
                    st.rerun()

def _render_vin_actions(det: dict, av, key_suffix: str) -> None:
    """Render crop toggle, download, and text-to-client actions for a pinned VIN."""
    from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
    from agents.search_agent import crop_dealer_overlay
    has_photo = bool(det.get("photo_url"))
    has_bytes = bool(det.get("photo_bytes"))

    # Crop toggle — only shown when we have bytes to process
    _crop_key = f"crop_{key_suffix}"
    do_crop = False
    if has_bytes:
        do_crop = st.checkbox("✂️ Crop dealer banner before download/send", key=_crop_key)
        _img_bytes = crop_dealer_overlay(det["photo_bytes"]) if do_crop else det["photo_bytes"]

        # Preview cropped image
        if do_crop:
            st.image(_img_bytes, caption="Preview (cropped)", use_container_width=True)

        st.download_button(
            "⬇️ Download" + (" (cropped)" if do_crop else " Photo"),
            data=_img_bytes,
            file_name=f"{av.vin}{'_cropped' if do_crop else ''}.jpg",
            mime="image/jpeg",
            key=f"dl_{key_suffix}",
            use_container_width=True,
        )
    else:
        _img_bytes = None

    st.markdown("**📲 Text to client:**")
    _ph_key  = f"txt_ph_{key_suffix}"
    _btn_key = f"txt_btn_{key_suffix}"
    _ph = st.text_input(
        "Client phone", placeholder="+1 949-555-0123",
        label_visibility="collapsed", key=_ph_key,
    )
    if st.button("Send " + ("📸 Photo + Info" if has_photo else "📋 Info") + " via SMS",
                 key=_btn_key, use_container_width=True):
        if not _ph.strip():
            st.warning("Enter a phone number.")
        elif not TWILIO_ACCOUNT_SID:
            st.warning("Twilio not configured — add TWILIO_* keys to .env")
        else:
            _title = av.title or f"VIN {av.vin}"
            _lines = [f"🚗 {_title}"]
            if det.get("mileage"): _lines.append(f"Mileage: {det['mileage']:,} mi")
            if det.get("price"):   _lines.append(f"Price: ${det['price']:,}")
            if det.get("dealer_name"): _lines.append(f"Dealer: {det['dealer_name']}")
            _lines.append(f"Search listing: {det.get('listing_url','')}")
            _body = "\n".join(_lines)
            try:
                from twilio.rest import Client as _TC
                _tc = _TC(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                _kwargs = dict(body=_body, from_=TWILIO_PHONE_NUMBER, to=_ph.strip())
                if has_photo:
                    if do_crop and _img_bytes:
                        # Upload cropped bytes to a temp public URL via Twilio's own media
                        # hosting isn't available — fall back to original photo_url for MMS
                        # but warn user the crop applies to download only
                        _kwargs["media_url"] = [det["photo_url"]]
                        _tc.messages.create(**_kwargs)
                        st.success("Sent! Note: MMS uses original photo (cropped version available via download).")
                    else:
                        _kwargs["media_url"] = [det["photo_url"]]
                        _tc.messages.create(**_kwargs)
                        st.success("Sent! (photo + info)")
                else:
                    _tc.messages.create(**_kwargs)
                    st.success("Sent! (info only — no photo available)")
            except Exception as _e:
                st.error(f"Send failed: {_e}")


# ── Build Search card (shown when user clicks "Build Search") ───────────────
# Always reads live from sidebar session state so any sidebar change
# immediately reflects in the card without re-clicking Build Search.
if st.session_state.get("_search_builder"):
    import re as _re2
    _sb_make      = _normalize_make(st.session_state.get("p_make", ""))
    _sb_model     = st.session_state.get("p_model", "")
    _sb_trim      = (st.session_state.get("p_trim") or "").strip()
    _sb_condition = st.session_state.get("p_condition", "Any")
    _sb_location  = st.session_state.get("p_location", "")
    _sb_price_min = st.session_state.get("p_price_min", 0)
    _sb_price_max = st.session_state.get("p_price_max", 999000)
    _sb_mileage   = st.session_state.get("p_max_mileage")
    if _sb_mileage and _sb_mileage >= 500000: _sb_mileage = None
    _sb_color     = st.session_state.get("p_exterior_color") or ""
    _sb_int_color = st.session_state.get("p_interior_color") or ""
    _sb_radius    = st.session_state.get("p_radius_miles", 50)

    _sb_zip    = _zip_from_location(_sb_location)
    _sb_at_url = _at_url_fn(
        _sb_make, _sb_model, _sb_condition, _sb_zip,
        price_max=_sb_price_max, price_min=_sb_price_min,
        ext_color=_sb_color, int_color=_sb_int_color,
        radius=_sb_radius, mileage=_sb_mileage, trim=_sb_trim,
    )
    from urllib.parse import quote_plus as _sb_qp, quote as _sb_quote
    _sb_cg_url = _cg_url_fn(_sb_make, _sb_model, _sb_zip, _sb_price_max, _sb_condition, _sb_color, _sb_int_color, _sb_radius, trim=_sb_trim)
    _sb_cm_make  = _sb_make.lower().replace(" ", "_").replace("-", "_")
    _sb_cm_model = (_sb_make + "_" + _sb_model).lower().replace(" ", "_").replace("-", "_").replace("/", "_").replace(".", "")
    _sb_cm_model = _CM_SLUG_MAP.get(_sb_cm_model, _sb_cm_model)
    _sb_cm_qp = [f"stock_type={'used' if _sb_condition=='Used' else 'new' if _sb_condition=='New' else 'all'}",
                 f"makes[]={_sb_cm_make}", f"models[]={_sb_cm_model}"]
    if _sb_zip:    _sb_cm_qp.append(f"zip={_sb_zip}")
    if _sb_radius and _sb_radius < 500: _sb_cm_qp.append(f"maximum_distance={_sb_radius}")
    if _sb_price_min:     _sb_cm_qp.append(f"price_min={_sb_price_min}")
    if _sb_price_max < 999000: _sb_cm_qp.append(f"price_max={_sb_price_max}")
    if _sb_mileage:       _sb_cm_qp.append(f"mileage_max={_sb_mileage}")
    if _sb_color and _sb_color.lower() not in ("any", "other", ""):
        _sb_cm_qp.append(f"exterior_color_slugs[]={_sb_color.lower()}")
    if _sb_int_color and _sb_int_color.lower() not in ("any", "other", ""):
        _sb_cm_qp.append(f"interior_color_slugs[]={_sb_int_color.lower()}")
    if _sb_trim and _sb_trim.lower() not in ("any", ""):
        from urllib.parse import quote as _sb_q2
        _sb_cm_qp.append(f"trims[]={_sb_q2(_sb_trim, safe='')}")
    _sb_cm_url = "https://www.cars.com/shopping/results/?" + "&".join(_sb_cm_qp)
    _sb_google_url = f"https://www.google.com/search?q={_sb_quote(f'{_sb_condition} {_sb_make} {_sb_model} for sale near {_sb_location}')}"

    def _hurl_sb(u): return u.replace("&", "&amp;")

    # Porsche Finder button — official dealer inventory, Porsche searches only
    _sb_pf_btn = ""
    if _sb_make.strip().lower() == "porsche":
        from agents.search_agent import _porsche_model_slug as _pf_slug_fn
        _pf_qp = []
        _pf_slug = _pf_slug_fn(_sb_model)
        if _pf_slug: _pf_qp.append(f"model={_pf_slug}")
        if _sb_condition in ("New", "Used"): _pf_qp.append(f"condition={_sb_condition.lower()}")
        _sb_pf_url = "https://finder.porsche.com/us/en-US/search" + (("?" + "&".join(_pf_qp)) if _pf_qp else "")
        _sb_pf_btn = f'''
    <a href="{_hurl_sb(_sb_pf_url)}" target="_blank" title="Official Porsche dealer inventory"
       style="background:#0891b2;color:#fff;padding:5px 10px;border-radius:6px;
              font-size:11px;font-weight:700;text-decoration:none;text-align:center">🏁 Porsche Finder</a>'''

    _sb_pill = f"{_sb_make} {_sb_model}".strip() or "Any"
    if _sb_trim: _sb_pill += f" {_sb_trim}"
    _sb_pill += f" &nbsp;·&nbsp; {_sb_condition}"
    if _sb_location:  _sb_pill += f" &nbsp;·&nbsp; near {_sb_location}"
    if _sb_radius != 50: _sb_pill += f" &nbsp;·&nbsp; {_sb_radius} mi radius"
    if _sb_price_min and _sb_price_min > 0 and _sb_price_max < 999000:
        _sb_pill += f" &nbsp;·&nbsp; ${_sb_price_min:,}–${_sb_price_max:,}"
    elif _sb_price_max < 999000:
        _sb_pill += f" &nbsp;·&nbsp; up to ${_sb_price_max:,}"
    elif _sb_price_min and _sb_price_min > 0:
        _sb_pill += f" &nbsp;·&nbsp; from ${_sb_price_min:,}"
    if _sb_mileage and _sb_mileage < 500000: _sb_pill += f" &nbsp;·&nbsp; max {_sb_mileage:,} mi"
    if _sb_color and _sb_color.lower() not in ("any", "other", ""):
        _sb_pill += f" &nbsp;·&nbsp; {_sb_color} ext"
    if _sb_int_color and _sb_int_color.lower() not in ("any", "other", ""):
        _sb_pill += f" &nbsp;·&nbsp; {_sb_int_color} int"

    # Two-column layout: card left, VIN pin right
    _sb_left, _sb_right = st.columns(2)

    with _sb_left:
        st.markdown(f"""
<div style="font-family:sans-serif;background:linear-gradient(135deg,#1e3a5f,#1a2e4a);
            border:1px solid #2563eb;border-radius:12px;padding:12px 16px;margin:4px 0 8px;
            display:table">
  <div style="font-size:13px;font-weight:700;color:#f0f4ff;margin-bottom:4px;white-space:nowrap">
    🗺️ &nbsp;Your search — ready to go on any platform
  </div>
  <div style="font-size:10px;color:#94a3b8;margin-bottom:8px">
    👤 Human in the loop required.
  </div>
  <div style="display:inline-block;font-size:11px;color:#e0f0ff;font-weight:600;
              border:1px solid #3b82f6;border-radius:6px;
              padding:3px 8px;margin-bottom:10px;background:rgba(59,130,246,0.15);white-space:nowrap">
    {_sb_pill}
  </div>
  <div style="display:grid;grid-template-columns:auto auto;gap:6px">
    <a href="{_hurl_sb(_sb_at_url)}" target="_blank"
       style="background:#2563eb;color:#fff;padding:5px 10px;border-radius:6px;
              font-size:11px;font-weight:700;text-decoration:none;text-align:center">🔎 AutoTrader</a>
    <a href="{_hurl_sb(_sb_cm_url)}" target="_blank"
       style="background:#16a34a;color:#fff;padding:5px 10px;border-radius:6px;
              font-size:11px;font-weight:700;text-decoration:none;text-align:center">🚙 Cars.com</a>
    <a href="{_hurl_sb(_sb_cg_url)}" target="_blank" title="Open CarGurus listings"
       style="background:#dc2626;color:#fff;padding:5px 10px;border-radius:6px;
              font-size:11px;font-weight:700;text-decoration:none;text-align:center">🚗 CarGurus</a>
    <a href="{_hurl_sb(_sb_google_url)}" target="_blank"
       style="background:#d97706;color:#fff;padding:5px 10px;border-radius:6px;
              font-size:11px;font-weight:700;text-decoration:none;text-align:center">🌐 Google</a>{_sb_pf_btn}
  </div>
</div>""", unsafe_allow_html=True)
        if st.button("✕ Clear", key="clear_search_builder"):
            del st.session_state["_search_builder"]
            st.rerun()


    with _sb_right:
        st.markdown("**📌 Pin a car by VIN**")
        st.caption("Paste a VIN from AutoTrader, Cars.com, or anywhere else")
        _sb_fc, _sb_lc = st.columns(2)
        with _sb_fc:
            st.text_input("First Name", placeholder="First", key="sb_vin_first_name")
        with _sb_lc:
            st.text_input("Last Name", placeholder="Last", key="sb_vin_last_name")
        st.text_input("Client Phone", placeholder="+1 949-555-0123", key="sb_vin_phone")
        _sb_vin_val = st.text_input(
            "VIN", placeholder="e.g. 5UX13EU03T9384714",
            label_visibility="collapsed", key="sb_vin_lookup_input",
        )
        _sb_vin_btn = st.button("Look Up VIN", key="sb_vin_lookup_btn", use_container_width=True)
        if _sb_vin_btn and _sb_vin_val:
            # Use prefs from prior search if available; otherwise build from sidebar values
            _sb_prefs = _last_meta.get("prefs")
            if not _sb_prefs:
                from agents.models import CarPreferences as _CP
                try:
                    _sb_prefs = _CP(
                        make=st.session_state.get("p_make", "Any") or "Any",
                        model=st.session_state.get("p_model", "Any") or "Any",
                        price_min=int(st.session_state.get("p_price_min", 0) or 0),
                        price_max=int(st.session_state.get("p_price_max", 999000) or 999000),
                        location=st.session_state.get("p_location", "") or "",
                        radius_miles=int(st.session_state.get("p_radius_miles", 50) or 50),
                    )
                except Exception:
                    _sb_prefs = None
            if not _sb_prefs:
                st.warning("Fill in Make, Model, and Location in the sidebar first.")
            else:
                with st.spinner("Decoding VIN..."):
                    from agents.search_agent import lookup_vin_listing
                    from agents.ranking_agent import run_ranking_agent as _rank_sb
                    _sb_listing, _sb_err = lookup_vin_listing(_sb_vin_val.strip(), _sb_prefs)
                if _sb_err:
                    st.error(_sb_err)
                else:
                    _sb_scored = _rank_sb(_sb_prefs, [_sb_listing])
                    _sb_listing = _sb_scored[0] if _sb_scored else _sb_listing
                    _sb_added = st.session_state.setdefault("vin_added_listings", [])
                    if not any(l.vin == _sb_listing.vin for l in _sb_added):
                        _sb_added.append(_sb_listing)
                        from agents.search_agent import fetch_vin_details as _fvd
                        st.session_state.setdefault("vin_details", {})[_sb_vin_val.strip().upper()] = _fvd(_sb_vin_val.strip())
                        # Save to MySQL nn.vin_lookups
                        try:
                            import mysql.connector as _mc
                            _det_save = st.session_state.get("vin_details", {}).get(_sb_vin_val.strip().upper(), {})
                            _cn = _mc.connect(host="localhost", port=3306, user="root", password="fruitL00p", database="nn")
                            _cu = _cn.cursor()
                            _cu.execute(
                                "INSERT INTO vin_lookups (first_name, last_name, phone, vin, year, make, model, trim_level, price, mileage, dealer_name, image_url) "
                                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (
                                    (st.session_state.get("sb_vin_first_name") or "").strip(),
                                    (st.session_state.get("sb_vin_last_name") or "").strip(),
                                    (st.session_state.get("sb_vin_phone") or "").strip(),
                                    _sb_listing.vin,
                                    _det_save.get("year") or _sb_listing.year,
                                    _det_save.get("make", ""),
                                    _det_save.get("model", ""),
                                    _det_save.get("trim", ""),
                                    _sb_listing.asking_price or _sb_listing.price,
                                    _sb_listing.mileage,
                                    _sb_listing.dealer_name or _det_save.get("dealer_name", ""),
                                    _det_save.get("photo_url", ""),
                                )
                            )
                            _cn.commit()
                            _cn.close()
                        except Exception as _dbe:
                            import traceback; traceback.print_exc()
                            st.session_state["_vin_db_err"] = str(_dbe)
                        st.success(f"Added: **{_sb_listing.title}**")
                        st.rerun()
                    else:
                        st.info("This VIN is already pinned.")
        if "_vin_db_err" in st.session_state:
            st.warning(f"DB save failed: {st.session_state.pop('_vin_db_err')}")
        _sb_pinned = st.session_state.get("vin_added_listings", [])
        if _sb_pinned:
            st.markdown(f"**{len(_sb_pinned)} pinned:**")
            for _av in _sb_pinned:
                _pstr = f"${_av.asking_price:,}" if _av.asking_price else "N/A"
                _det = st.session_state.get("vin_details", {}).get(_av.vin, {})
                with st.expander(f"📌 {_av.title}  —  {_pstr}", expanded=True):
                    if _det.get("photo_url"):
                        st.image(_det["photo_url"], use_container_width=True)
                    else:
                        _gi = _det.get("google_images_url", "")
                        _bi = _det.get("bing_images_url", "")
                        if _gi:
                            st.markdown(
                                f"📸 **Photos:** &nbsp;[Google Images]({_gi}) &nbsp;|&nbsp; [Bing Images]({_bi})",
                                unsafe_allow_html=True,
                            )
                    _dc1, _dc2 = st.columns(2)
                    with _dc1:
                        if _det.get("year"):      st.markdown(f"**Year:** {_det['year']}")
                        if _det.get("make"):      st.markdown(f"**Make:** {_det['make']}")
                        if _det.get("model"):     st.markdown(f"**Model:** {_det['model']}")
                        if _det.get("trim"):      st.markdown(f"**Trim:** {_det['trim']}")
                        if _det.get("body_type"): st.markdown(f"**Body:** {_det['body_type']}")
                    with _dc2:
                        if _det.get("engine"):    st.markdown(f"**Engine:** {_det['engine']}")
                        if _det.get("fuel_type"): st.markdown(f"**Fuel:** {_det['fuel_type']}")
                        if _det.get("doors"):     st.markdown(f"**Doors:** {_det['doors']}")
                        if _det.get("mileage"):   st.markdown(f"**Mileage:** {_det['mileage']:,} mi")
                        if _det.get("price"):     st.markdown(f"**Price:** ${_det['price']:,}")
                    if _det.get("features"):
                        st.markdown("**Features:** " + " · ".join(_det["features"][:12]))
                    if _det.get("listing_url"):
                        st.markdown(f"[🔗 Search on AutoTrader by VIN]({_det['listing_url']})")
                    st.divider()
                    _render_vin_actions(_det, _av, f"sb_{_av.vin}")
                if st.button("✕ Remove", key=f"sb_rm_{_av.vin}"):
                    st.session_state["vin_added_listings"] = [l for l in _sb_pinned if l.vin != _av.vin]
                    st.session_state.get("vin_details", {}).pop(_av.vin, None)
                    st.rerun()

# ── Sidebar: User Preferences ──────────────────────────────────────────────
with st.sidebar:
    st.header("Your Car Preferences")

    make = st.text_input("Make", placeholder="e.g. BMW, Toyota", key="p_make")
    model = st.text_input("Model", placeholder="e.g. X5, Camry", key="p_model")
    trim = st.text_input("Trim (optional)", placeholder="e.g. Sport, Luxury, Prestige", key="p_trim")

    st.subheader("Budget")
    col1, col2 = st.columns(2)
    with col1:
        price_min = st.number_input("Min ($)", min_value=0, step=1000, key="p_price_min")
    with col2:
        price_max = st.number_input("Max ($)", min_value=0, step=1000, key="p_price_max")

    st.subheader("Vehicle Details")
    condition = st.selectbox("Condition", ["Any", "Used", "New", "Certified Pre-Owned (CPO)"], key="p_condition")
    certified_only = condition == "Certified Pre-Owned (CPO)"
    exterior_color = st.selectbox(
        "Exterior Color",
        ["Any", "White", "Black", "Silver", "Gray", "Red", "Blue", "Green", "Other"],
        key="p_exterior_color",
    )
    interior_color = st.selectbox(
        "Interior Color",
        ["Any", "Black", "Beige", "Gray", "Brown", "White", "Red", "Other"],
        key="p_interior_color",
    )
    max_mileage = st.number_input("Max Mileage", min_value=0, step=5000, key="p_max_mileage")

    st.subheader("Location")
    # Apply pending auto-detected location BEFORE the widget is rendered
    if st.session_state.get("_pending_location"):
        st.session_state["p_location"] = st.session_state.pop("_pending_location")
    location = st.text_input("Your ZIP or City", placeholder="e.g. 92782 or Irvine, CA", key="p_location")
    st.markdown("""
<style>
div[data-testid="stSidebar"] div[data-testid="stButton"]:has(button[title*="GPS"]) button {
    background: linear-gradient(135deg,#0ea5e9,#6366f1) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px !important;
    padding: 5px 10px !important;
    margin-top: -8px !important;
}
</style>""", unsafe_allow_html=True)
    if st.button("📍 Use My Location", use_container_width=True,
                 help="Uses your browser's GPS — you'll be asked to allow location access"):
        st.session_state["_geo_requested"] = True
        st.rerun()

    # Browser geolocation — renders a JS component that asks for GPS permission
    if st.session_state.get("_geo_requested"):
        try:
            from streamlit_js_eval import get_geolocation
            _geo = get_geolocation()
            if _geo and _geo.get("coords"):
                _lat = _geo["coords"]["latitude"]
                _lon = _geo["coords"]["longitude"]
                _loc = _reverse_geocode(_lat, _lon)
                if _loc:
                    st.session_state["_pending_location"] = _loc
                    st.session_state.pop("_geo_requested", None)
                    st.rerun()
        except Exception:
            st.warning("Browser geolocation unavailable — please type your location.")
    _RADIUS_OPTS = [10, 25, 50, 75, 100, 200, 300, 400, 500, 0]
    radius_miles = st.selectbox(
        "Search Radius",
        _RADIUS_OPTS,
        format_func=lambda x: "Nationwide" if x == 0 else f"{x} Miles",
        key="p_radius_miles",
    )

    st.subheader("Search Sources")
    from config import AUTODEV_API_KEY as _AUTODEV_KEY
    src_autodev     = st.checkbox("auto.dev", value=bool(_AUTODEV_KEY), disabled=not bool(_AUTODEV_KEY),
                                  help="Requires AUTODEV_API_KEY in .env — 1–4M listings, $0.002/call")
    src_marketcheck = st.checkbox("Marketcheck", value=True)
    src_ebay        = st.checkbox("eBay Motors (API key required)", value=False, disabled=True)
    src_cargurus    = st.checkbox("CarGurus (experimental)", value=False)
    src_craigslist  = st.checkbox("Craigslist",  value=True)
    src_porsche     = st.checkbox("Porsche Finder (Porsche searches only)", value=True,
                                  help="Official dealer inventory from finder.porsche.com — only runs when the search make is Porsche")

    st.subheader("Delivery Preference")
    delivery_email = st.checkbox("Email", value=False)
    delivery_sms = st.checkbox("SMS")

    user_email = None
    user_phone = None
    if delivery_email:
        user_email = st.text_input("Your Email", placeholder="you@example.com")
    if delivery_sms:
        user_phone = st.text_input("Your Phone", placeholder="+1 555 000 0000")

    st.subheader("Dealer Outreach (Broker Mode)")
    dealer_outreach = st.checkbox("Contact dealers on my behalf", value=False)
    broker_name = broker_email = broker_phone = None
    if dealer_outreach:
        broker_name = st.text_input("Broker / Your Name", placeholder="e.g. John Smith")
        broker_email = st.text_input("Broker Email", placeholder="broker@example.com")
        broker_phone = st.text_input("Broker Phone", placeholder="+1 555 000 0000")

    find_btn = st.button("Find Cars", type="primary", use_container_width=True)

# ── Run pipeline ────────────────────────────────────────────────────────────
_nl_auto_run = st.session_state.pop("_nl_auto_run", False)
if find_btn or _nl_auto_run:
    if not make or not model:
        st.error("Please fill in Make and Model.")
        st.stop()
    if not location:
        st.error("Please fill in your location, or click **📍 Detect** in the sidebar to use your GPS.")
        st.stop()
    if dealer_outreach and not broker_name:
        st.error("Please enter your broker name for dealer outreach.")
        st.stop()
    if price_min >= price_max:
        st.error("Min price must be less than Max price.")
        st.stop()

    prefs = CarPreferences(
        make=make,
        model=model,
        trim=(_t.strip() if (_t := " ".join(w for w in (trim or "").split() if w.upper() not in ("HD","AWD","4WD","RWD","FWD","4X4"))) and _t.lower() not in ("", "any") else None),
        price_min=int(price_min),
        price_max=int(price_max),
        exterior_color=None if exterior_color == "Any" else exterior_color,
        interior_color=None if interior_color == "Any" else interior_color,
        max_mileage=int(max_mileage) if max_mileage else None,
        location=location,
        radius_miles=500 if radius_miles == 0 else radius_miles,  # 0 = Nationwide
        certified_only=certified_only,
        condition=None if condition in ("Any", "Certified Pre-Owned (CPO)") else condition,
        delivery_email=delivery_email,
        delivery_sms=delivery_sms,
        user_email=user_email,
        user_phone=user_phone,
        dealer_outreach=dealer_outreach,
        broker_name=broker_name or None,
        broker_email=broker_email or None,
        broker_phone=broker_phone or None,
    )

    status_box  = st.empty()
    progress_bar = st.progress(0)

    agent_steps = {
        "search":           ("🔍 Search Agent: Scanning marketplaces...", 20),
        "ranking":          ("📊 Ranking Agent: Scoring matches...", 40),
        "critic":           ("🎯 Critic Agent: Evaluating results...", 50),
        "revision":         ("🔄 Revising search parameters and retrying...", 25),
        "outreach":         ("📨 Outreach Agent: Generating messages...", 75),
        "critic_outreach":  ("🎯 Critic Agent: Evaluating outreach quality...", 88),
        "dealer_outreach":  ("📞 Dealer Outreach: Drafting dealer messages...", 93),
        "done":             ("✅ Complete!", 100),
    }

    def on_status(step: str):
        label, pct = agent_steps.get(step, ("Working...", 50))
        status_box.info(label)
        progress_bar.progress(pct)

    selected_sources = [n for n, on in [
        ("auto.dev",    src_autodev),
        ("Marketcheck", src_marketcheck),
        ("eBay Motors", src_ebay),
        ("CarGurus",    src_cargurus),
        ("Craigslist",  src_craigslist),
        ("Porsche Finder", src_porsche),
    ] if on]
    if not selected_sources:
        st.error("Please enable at least one search source in the sidebar.")
        st.stop()

    try:
        result = run_pipeline(prefs, on_status=on_status, selected_sources=selected_sources)
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        st.stop()

    status_box.empty()
    progress_bar.empty()

    # Store results in session state and reset to page 1
    st.session_state["_last_result"] = result
    st.session_state["vin_added_listings"] = []   # clear on new search
    st.session_state["_last_meta"] = {
        "make": make, "model": model, "condition": condition, "location": location,
        "prefs": prefs, "delivery_email": delivery_email, "delivery_sms": delivery_sms,
        "user_email": user_email, "user_phone": user_phone,
    }
    st.session_state["results_page"] = 0
    st.rerun()

# ── Results display ─────────────────────────────────────────────────────────
if _last_result:
    listings         = _last_result["listings"]
    delivery         = _last_result.get("delivery", {})
    search_warning   = _last_result.get("search_warning")
    source_errors    = _last_result.get("source_errors", {})
    critic           = _last_result.get("critic")
    revision_count   = _last_result.get("revision_count", 0)
    outreach_retried = _last_result.get("outreach_retried", False)
    dealer_results   = _last_result.get("dealer_outreach", [])

    _make      = _normalize_make(_last_meta.get("make", ""))
    _model     = _last_meta.get("model", "")
    _condition = _last_meta.get("condition", "Any")
    _location  = _last_meta.get("location", "")
    _prefs     = _last_meta.get("prefs")
    _del_email = _last_meta.get("delivery_email", False)
    _del_sms   = _last_meta.get("delivery_sms", False)
    _user_email = _last_meta.get("user_email")
    _user_phone = _last_meta.get("user_phone")

    # ── External search URLs (built once, used in both 0-result and card views) ──
    import re as _re
    _at_zip    = _zip_from_location(_location)
    _ext_color = (_prefs.exterior_color or "") if _prefs else ""
    _int_color = (_prefs.interior_color or "") if _prefs else ""
    _trim = (_prefs.trim or "") if _prefs else ""
    _autotrader_url = _at_url_fn(
        _make, _model, _condition, _at_zip,
        price_max=_prefs.price_max if _prefs else 999999,
        price_min=_prefs.price_min if _prefs else 0,
        ext_color=_ext_color, int_color=_int_color,
        radius=_prefs.radius_miles if _prefs else 50,
        mileage=_prefs.max_mileage if _prefs else None,
        trim=_trim,
    )
    from urllib.parse import quote_plus as _qp
    _cargurus_url = _cg_url_fn(
        _make, _model, _at_zip,
        _prefs.price_max if _prefs else 999999,
        _condition,
        ext_color=_ext_color,
        int_color=_int_color,
        radius=_prefs.radius_miles if _prefs else 50,
        trim=_trim,
    )
    # Cars.com slugs use underscores; model slug is make_model combined
    _cm_make  = _make.lower().replace(" ", "_").replace("-", "_")
    _cm_model = (_make + "_" + _model).lower().replace(" ", "_").replace("-", "_").replace("/", "_").replace(".", "")
    _cm_model = _CM_SLUG_MAP.get(_cm_model, _cm_model)
    _cm_stock = "used" if _condition == "Used" else "new" if _condition == "New" else "all"
    from urllib.parse import quote as _url_quote
    _cm_qp = [f"stock_type={_cm_stock}", f"makes[]={_cm_make}", f"models[]={_cm_model}"]
    if _at_zip:          _cm_qp.append(f"zip={_at_zip}")
    if _prefs:
        if _prefs.radius_miles < 500: _cm_qp.append(f"maximum_distance={_prefs.radius_miles}")
        if _prefs.price_min:    _cm_qp.append(f"price_min={_prefs.price_min}")
        if _prefs.price_max < 999000: _cm_qp.append(f"price_max={_prefs.price_max}")
        if _prefs.max_mileage:  _cm_qp.append(f"mileage_max={_prefs.max_mileage}")
        if _ext_color and _ext_color.lower() not in ("any", "other", ""):
            _cm_qp.append(f"exterior_color_slugs[]={_ext_color.lower()}")
        if _int_color and _int_color.lower() not in ("any", "other", ""):
            _cm_qp.append(f"interior_color_slugs[]={_int_color.lower()}")
        if _trim and _trim.lower() not in ("any", ""):
            _cm_qp.append(f"trims[]={_url_quote(_trim, safe='')}")
    _carsdotcom_url = "https://www.cars.com/shopping/results/?" + "&".join(_cm_qp)
    _google_url = f"https://www.google.com/search?q={_url_quote(f'{_condition} {_make} {_model} for sale near {_location}')}"

    # ── No results ──────────────────────────────────────────────────────────
    if not listings:
        st.warning(f"No results found — {search_warning}" if search_warning else "No results found.")
        st.info("Try widening your price range, increasing the search radius, or removing color/mileage filters.")

        import streamlit.components.v1 as _stc_z
        def _hurl_z(u): return u.replace("&", "&amp;")

        # Porsche Finder button — official dealer inventory, Porsche searches only
        _pf_btn_z = ""
        if _make.strip().lower() == "porsche":
            from agents.search_agent import _porsche_model_slug as _pf_slug_fn_z
            _pf_qp_z = []
            _pf_slug_z = _pf_slug_fn_z(_model)
            if _pf_slug_z: _pf_qp_z.append(f"model={_pf_slug_z}")
            if _condition in ("New", "Used"): _pf_qp_z.append(f"condition={_condition.lower()}")
            _pf_url_z = "https://finder.porsche.com/us/en-US/search" + (("?" + "&".join(_pf_qp_z)) if _pf_qp_z else "")
            _pf_btn_z = f'''
    <a href="{_hurl_z(_pf_url_z)}" target="_blank" title="Official Porsche dealer inventory"
       style="background:#0891b2;color:#fff;padding:9px 20px;border-radius:8px;
              font-size:14px;font-weight:700;text-decoration:none;letter-spacing:0.3px">
      🏁 &nbsp;Porsche Finder
    </a>'''

        _stc_z.html(f"""
<div style="font-family:sans-serif;background:linear-gradient(135deg,#1e3a5f,#1a2e4a);
            border:1px solid #2563eb;border-radius:12px;padding:20px 24px;margin:4px 0">
  <div style="font-size:16px;font-weight:700;color:#f0f4ff;margin-bottom:6px">
    🔍 &nbsp;Continue your search — filters already applied
  </div>
  <div style="display:inline-block;font-size:12px;color:#e0f0ff;font-weight:600;
              border:1px solid #3b82f6;border-radius:6px;
              padding:5px 12px;margin-bottom:16px;background:rgba(59,130,246,0.15)">
    {_make} {_model} &nbsp;·&nbsp; {_condition} &nbsp;·&nbsp; near {_location}
    {"&nbsp;·&nbsp; " + str(_prefs.radius_miles) + " mi radius" if _prefs and _prefs.radius_miles != 50 else ""}
    {"&nbsp;·&nbsp; up to $" + f"{_prefs.price_max:,}" if _prefs and _prefs.price_max < 999000 else ""}
    {"&nbsp;·&nbsp; max " + f"{_prefs.max_mileage:,} mi" if _prefs and _prefs.max_mileage and _prefs.max_mileage < 500000 else ""}
    {"&nbsp;·&nbsp; " + _prefs.exterior_color + " ext" if _prefs and _prefs.exterior_color and _prefs.exterior_color.lower() not in ("any","other") else ""}
    {"&nbsp;·&nbsp; " + _prefs.interior_color + " int" if _prefs and _prefs.interior_color and _prefs.interior_color.lower() not in ("any","other") else ""}
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px">
    <a href="{_hurl_z(_autotrader_url)}" target="_blank"
       style="background:#2563eb;color:#fff;padding:9px 20px;border-radius:8px;
              font-size:14px;font-weight:700;text-decoration:none;letter-spacing:0.3px">
      🔎 &nbsp;AutoTrader
    </a>
    <a href="{_hurl_z(_carsdotcom_url)}" target="_blank"
       style="background:#16a34a;color:#fff;padding:9px 20px;border-radius:8px;
              font-size:14px;font-weight:700;text-decoration:none;letter-spacing:0.3px">
      🚙 &nbsp;Cars.com
    </a>
    <a href="{_hurl_z(_cargurus_url)}" target="_blank" title="Open CarGurus listings"
       style="background:#dc2626;color:#fff;padding:9px 20px;border-radius:8px;
              font-size:14px;font-weight:700;text-decoration:none;letter-spacing:0.3px">
      🚗 &nbsp;CarGurus
    </a>
    <a href="{_hurl_z(_google_url)}" target="_blank"
       style="background:#d97706;color:#fff;padding:9px 20px;border-radius:8px;
              font-size:14px;font-weight:700;text-decoration:none;letter-spacing:0.3px">
      🌐 &nbsp;Google
    </a>{_pf_btn_z}
  </div>
</div>""", height=185)

        if source_errors:
            with st.expander("Source Status — click to see why"):
                for src_name, src_status in source_errors.items():
                    ok = src_status.startswith("OK")
                    icon = "✅" if ok else "❌"
                    color = "#27ae60" if ok else "#e74c3c"
                    st.markdown(
                        f"<span style='color:{color}'>{icon} <b>{src_name}</b></span> — {src_status}",
                        unsafe_allow_html=True,
                    )
        with st.expander("Debug — Search parameters sent to API"):
            if _prefs:
                st.json(_prefs.model_dump())

    else:
        if search_warning:
            st.warning(f"⚠️ {search_warning}")

        # ── Critic badge + inline VIN lookup ────────────────────────────────
        _show_sb = st.session_state.get("_search_builder")

        # When Build Search is active the compact card + VIN are already rendered
        # above (in the early section), so here we only show the critic badge.
        # When Build Search is off, show [critic badge | VIN] side by side.
        if not _show_sb:
            _badge_col, _vin_col = st.columns([1, 1])

        if not _show_sb:
            with _badge_col:
                if critic:
                    badge_colors = {"green": "#27ae60", "amber": "#f39c12", "red": "#e74c3c"}
                    badge_labels = {
                        "green": "Green — High quality results",
                        "amber": "Amber — Partial quality, review carefully",
                        "red":   "Red — Low quality, consider revising preferences",
                    }
                    badge = critic.badge
                    color = badge_colors.get(badge, "#95a5a6")
                    label = badge_labels.get(badge, badge)
                    st.markdown(
                        f"""
                        <div style="background:{color};color:#fff;border-radius:8px;
                                    padding:12px 20px;font-size:18px;font-weight:bold;
                                    display:inline-block;margin-bottom:12px">
                            {label} &nbsp;·&nbsp; {critic.overall_score:.0f}/100
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if revision_count > 0:
                        st.info(f"Search improved after {revision_count} revision(s).")
                    with st.expander("Critic Agent — Quality Breakdown"):
                        for dim_key, dim in critic.dimensions.items():
                            icon = "✅" if dim.passed else ("⚠️" if dim.flag == "amber" else "❌")
                            dim_label = dim_key.replace("_", " ").title()
                            bar = int((dim.score / 25) * 100)
                            st.markdown(
                                f"**{icon} {dim_label}** — {dim.score:.0f}/25 pts  \n"
                                f"<div style='background:#e5e7eb;border-radius:4px;height:6px;margin:2px 0 4px'>"
                                f"<div style='background:{color};width:{bar}%;height:6px;border-radius:4px'></div></div>"
                                f"<small style='color:#6b7280'>{dim.reason}</small>",
                                unsafe_allow_html=True,
                            )

        # When Build Search is active, show critic badge below the two-column row
        if _show_sb and critic:
            badge_colors = {"green": "#27ae60", "amber": "#f39c12", "red": "#e74c3c"}
            badge_labels = {
                "green": "Green — High quality results",
                "amber": "Amber — Partial quality, review carefully",
                "red":   "Red — Low quality, consider revising preferences",
            }
            badge = critic.badge
            color = badge_colors.get(badge, "#95a5a6")
            label = badge_labels.get(badge, badge)
            st.markdown(
                f"""<div style="background:{color};color:#fff;border-radius:8px;
                            padding:12px 20px;font-size:18px;font-weight:bold;
                            display:inline-block;margin-bottom:12px">
                    {label} &nbsp;·&nbsp; {critic.overall_score:.0f}/100
                </div>""",
                unsafe_allow_html=True,
            )
            if revision_count > 0:
                st.info(f"Search improved after {revision_count} revision(s).")
            with st.expander("Critic Agent — Quality Breakdown"):
                for dim_key, dim in critic.dimensions.items():
                    icon = "✅" if dim.passed else ("⚠️" if dim.flag == "amber" else "❌")
                    dim_label = dim_key.replace("_", " ").title()
                    bar = int((dim.score / 25) * 100)
                    st.markdown(
                        f"**{icon} {dim_label}** — {dim.score:.0f}/25 pts  \n"
                        f"<div style='background:#e5e7eb;border-radius:4px;height:6px;margin:2px 0 4px'>"
                        f"<div style='background:{color};width:{bar}%;height:6px;border-radius:4px'></div></div>"
                        f"<small style='color:#6b7280'>{dim.reason}</small>",
                        unsafe_allow_html=True,
                    )

        if not _show_sb:
            with _vin_col:
                _render_vin_widget(_prefs)

        # ── Source status ────────────────────────────────────────────────────
        if source_errors:
            with st.expander("Source Status"):
                for src_name, src_status in source_errors.items():
                    ok = src_status.startswith("OK")
                    icon = "✅" if ok else "❌"
                    color = "#27ae60" if ok else "#e74c3c"
                    st.markdown(
                        f"<span style='color:{color}'>{icon} <b>{src_name}</b></span> — {src_status}",
                        unsafe_allow_html=True,
                    )

        # ── Sort control ─────────────────────────────────────────────────────
        # Each entry: (key_fn, reverse). reverse=True for Z→A / High→Low string sorts.
        _SORT_OPTIONS = {
            "Match Score (Best First)":   (lambda l: (-(l.match_score or 0)),                                    False),
            "Distance: Closest First":    (lambda l: (l.distance_miles if l.distance_miles is not None else 9999), False),
            "Price: Low → High":          (lambda l: l.price,                                                     False),
            "Price: High → Low":          (lambda l: -l.price,                                                    False),
            "Mileage: Low → High":        (lambda l: l.mileage,                                                   False),
            "Mileage: High → Low":        (lambda l: l.mileage,                                                   True),
            "Year: Newest First":         (lambda l: -(l.year or 0),                                              False),
            "Year: Oldest First":         (lambda l: (l.year or 9999),                                            False),
            "Color (A→Z)":               (lambda l: (l.exterior_color or "zzz").lower(),                         False),
            "Color (Z→A)":               (lambda l: (l.exterior_color or "").lower(),                            True),
            "Model (A→Z)":               (lambda l: " ".join((l.title or "").lower().split()[1:3]),               False),
            "Model (Z→A)":               (lambda l: " ".join((l.title or "").lower().split()[1:3]),               True),
            "Trim (A→Z)":                (lambda l: " ".join((l.title or "").lower().split()[3:]),                False),
            "Trim (Z→A)":                (lambda l: " ".join((l.title or "").lower().split()[3:]),                True),
        }
        sort_col, _ = st.columns([2, 3])
        with sort_col:
            st.markdown(
                '<div style="background:linear-gradient(90deg,#1e3a5f,#1a2e4a);'
                'border:1px solid #3b82f6;border-radius:10px;padding:8px 14px;margin-bottom:4px">'
                '<span style="color:#93c5fd;font-size:12px;font-weight:700;letter-spacing:0.5px">'
                '⇅ &nbsp;SORT RESULTS</span></div>',
                unsafe_allow_html=True,
            )
            sort_choice = st.selectbox(
                "Sort results", list(_SORT_OPTIONS.keys()),
                key="results_sort",
                label_visibility="collapsed",
            )
        # Prepend any VIN-added listings (pinned at top, not sorted/paginated)
        _vin_added = st.session_state.get("vin_added_listings", [])
        _sort_key, _sort_rev = _SORT_OPTIONS[sort_choice]
        sorted_listings = sorted(listings, key=_sort_key, reverse=_sort_rev)

        # ── Pagination setup ─────────────────────────────────────────────────
        total       = len(sorted_listings)
        total_pages = max(1, (total + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
        page        = min(st.session_state.get("results_page", 0), total_pages - 1)
        start       = page * RESULTS_PER_PAGE
        end         = min(start + RESULTS_PER_PAGE, total)
        page_listings = sorted_listings[start:end]

        cond_label = f" — {_condition}" if _condition != "Any" else ""
        st.success(
            f"Found **{total}** matches for your {_make} {_model}{cond_label} "
            f"— showing **{start + 1}–{end}**"
        )

        def _pagination_controls(key_suffix: str):
            if total_pages <= 1:
                return
            pc1, pc2, pc3 = st.columns([1, 2, 1])
            with pc1:
                if st.button("← Previous", disabled=(page == 0), key=f"prev_{key_suffix}"):
                    st.session_state["results_page"] = page - 1
                    st.rerun()
            with pc2:
                st.markdown(
                    f"<div style='text-align:center;padding-top:6px;font-size:15px'>"
                    f"Page <b>{page + 1}</b> of <b>{total_pages}</b></div>",
                    unsafe_allow_html=True,
                )
            with pc3:
                if st.button("Next →", disabled=(page >= total_pages - 1), key=f"next_{key_suffix}"):
                    st.session_state["results_page"] = page + 1
                    st.rerun()

        _pagination_controls("top")

        # ── Car listing cards ────────────────────────────────────────────────
        # ── VIN-pinned cards (shown above regular results, page 1 only) ────────
        if _vin_added and page == 0:
            st.markdown("#### 📌 Added by VIN")
            _vin_cols = st.columns(3)
            for _vi, _vl in enumerate(_vin_added):
                with _vin_cols[_vi % 3]:
                    _vsc = "green" if (_vl.match_score or 0) >= 70 else "orange"
                    _vprice_str = (f"${_vl.asking_price:,} asking price" if _vl.asking_price
                                   else "Price not in auto.dev — check AutoTrader link")
                    st.markdown(
                        f"""<div style="border:2px solid #2563eb;border-radius:10px;padding:16px;margin-bottom:4px;">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start">
                            <h4 style="margin:0">{_vl.title}</h4>
                            <span style="background:#2563eb;color:#fff;border-radius:4px;padding:2px 7px;font-size:11px;font-weight:bold">VIN Lookup</span>
                        </div>
                        <p style="margin:4px 0;color:#f97316;font-weight:bold">{_vprice_str}</p>
                        <p style="margin:2px 0">📅 Year: <b>{_vl.year or "—"}</b></p>
                        <p style="margin:2px 0">🛣 Mileage: <b>{f"{_vl.mileage:,} mi" if _vl.mileage else "—"}</b></p>
                        <p style="margin:2px 0">🏢 {_vl.dealer_name or "Dealer not in auto.dev"}</p>
                        <p style="margin:6px 0">Match score: <b style="color:{_vsc}">{_vl.match_score}/100</b></p>
                        <p style="margin:2px 0;font-size:11px;color:#9ca3af">VIN: {_vl.vin}</p>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    import streamlit.components.v1 as _stc2
                    _vlcj = (_vl.vin or "").replace("`", "\\`")
                    _at_vin = f"https://www.autotrader.com/cars-for-sale/all-cars?vin={_vl.vin}&searchRadius=500"
                    _cm_vin = f"https://www.cars.com/vehicledetail/{_vl.vin}/"
                    _gg_vin = f"https://www.google.com/search?q={_vl.vin}"
                    _stc2.html(
                        f"""<script>
function _cpv2(t){{var e=document.createElement('textarea');e.value=t;e.style.cssText='position:fixed;opacity:0;top:-9999px';document.body.appendChild(e);e.focus();e.select();try{{document.execCommand('copy')}}catch(x){{}}document.body.removeChild(e);}}
</script>
<div style="font-family:sans-serif;font-size:11px;padding:2px 0;display:flex;gap:4px;flex-wrap:nowrap;align-items:center">
<a href="{_at_vin}" target="_blank" onclick="_cpv2(`{_vlcj}`)" style="background:#2563eb;color:#fff;padding:2px 8px;border-radius:5px;font-size:11px;font-weight:700;text-decoration:none">View on AutoTrader →</a>
<a href="{_cm_vin}" target="_blank" onclick="_cpv2(`{_vlcj}`)" style="color:#60a5fa;text-decoration:none">🚙 Cars.com</a>
<a href="{_gg_vin}" target="_blank" onclick="_cpv2(`{_vlcj}`)" style="color:#60a5fa;text-decoration:none">🔎 Google VIN</a>
</div>""",
                        height=30,
                    )
            st.divider()

        st.subheader(f"Top Matches — Page {page + 1}")
        cols = st.columns(3)

        for i, listing in enumerate(page_listings):
            col = cols[i % 3]
            with col:
                score_color = "green" if (listing.match_score or 0) >= 70 else "orange"
                source = listing.source or "Unknown"
                source_color = "#2ecc71"
                badge_text = listing.dealer_name if listing.dealer_name else source
                source_badge = f'<span style="background:{source_color};color:#fff;border-radius:4px;padding:2px 7px;font-size:11px;font-weight:bold">{badge_text}</span>'
                _live_key = f"live_{listing.vin or i}"

                ask  = listing.asking_price if listing.asking_price is not None else 0
                msrp = listing.msrp

                if ask > 0 and msrp and msrp != ask:
                    savings = msrp - ask
                    savings_color = "#27ae60" if savings > 0 else "#e74c3c"
                    savings_label = f"${savings:,} below MSRP" if savings > 0 else f"${abs(savings):,} above MSRP"
                    price_block = (
                        f'<p style="font-size:22px;font-weight:bold;color:#1f77b4;margin:4px 0">'
                        f'${ask:,}'
                        f'<span style="font-size:13px;font-weight:normal;color:#6b7280"> asking</span></p>'
                        f'<p style="margin:2px 0;font-size:13px">MSRP: <b>${msrp:,}</b> &nbsp;'
                        f'<span style="color:{savings_color};font-weight:bold">{savings_label}</span></p>'
                    )
                elif ask > 0:
                    price_block = (
                        f'<p style="font-size:22px;font-weight:bold;color:#1f77b4;margin:4px 0">'
                        f'${ask:,}'
                        f'<span style="font-size:13px;font-weight:normal;color:#6b7280"> asking price</span></p>'
                        + (f'<p style="margin:2px 0;font-size:13px">MSRP: <b>${msrp:,}</b></p>' if msrp else '')
                    )
                elif msrp:
                    price_block = (
                        f'<p style="font-size:22px;font-weight:bold;color:#1f77b4;margin:4px 0">'
                        f'${msrp:,}'
                        f'<span style="font-size:13px;font-weight:normal;color:#6b7280"> MSRP</span></p>'
                        f'<p style="margin:2px 0;font-size:13px;color:#e67e22">Asking price not published — contact dealer</p>'
                    )
                else:
                    price_block = (
                        f'<p style="font-size:22px;font-weight:bold;color:#e67e22;margin:4px 0">'
                        f'Contact dealer for price</p>'
                    )

                st.markdown(
                    f"""
                    <div style="border:1px solid #ddd; border-radius:10px; padding:16px; margin-bottom:4px;">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start">
                            <h4 style="margin:0">{listing.title}</h4>
                            {source_badge}
                        </div>
                        {price_block}
                        <p style="margin:2px 0">📅 Year: <b>{listing.year}</b></p>
                        <p style="margin:2px 0">🛣 Mileage: <b>{listing.mileage:,} mi</b></p>
                        <p style="margin:2px 0">🎨 Ext: {listing.exterior_color or "N/A"} &nbsp;|&nbsp; Int: {listing.interior_color or "N/A"}</p>
                        <p style="margin:2px 0">🏢 {listing.dealer_name or "Private"}{f' &nbsp;<span style="color:#6ee7b7;font-size:11px">📞 {listing.dealer_phone}</span>' if listing.dealer_phone else ''}</p>
                        <p style="margin:2px 0">📍 {listing.location or _location}{f' &nbsp;<span style="color:#9ca3af;font-size:11px">({listing.distance_miles:.1f} mi away)</span>' if listing.distance_miles is not None else ''}</p>
                        <p style="margin:6px 0">Match score: <b style="color:{score_color}">{listing.match_score}/100</b>{f' &nbsp;<span style="color:#9ca3af;font-size:11px">· VIN: {listing.vin}</span>' if listing.vin else (f' &nbsp;<span style="color:#9ca3af;font-size:11px">· Stock #: {listing.stock_number}</span>' if listing.stock_number else '')}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                # Link row — rendered via components.html() so onclick JS works natively
                import streamlit.components.v1 as _stc
                from urllib.parse import quote as _url_quote
                # VIN if available; otherwise combine title + stock# + dealer for a strong Google query
                if listing.vin:
                    _clip_text = listing.vin
                else:
                    _clip_parts = [listing.title]
                    if listing.stock_number:
                        _clip_parts.append(listing.stock_number)
                    if listing.dealer_name:
                        _clip_parts.append(listing.dealer_name)
                    _clip_text = " ".join(_clip_parts)
                _clip_js = _clip_text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
                _ask = listing.asking_price or listing.price
                # Encode & as &amp; for HTML href attributes
                def _hurl(u): return u.replace("&", "&amp;")
                if listing.listing_url:
                    from urllib.parse import urlparse as _urlparse
                    _view_domain = _urlparse(listing.listing_url).netloc.replace("www.", "")
                    _view_a = (
                        f'<a href="{_hurl(listing.listing_url)}" target="_blank" '
                        f'style="background:#2563eb;color:#fff;padding:2px 8px;border-radius:5px;'
                        f'font-size:11px;font-weight:700;text-decoration:none;white-space:nowrap">'
                        f'View Listing →</a>'
                        f'<span style="font-size:10px;color:#9ca3af;margin-left:4px">{_view_domain}</span>'
                    )
                else:
                    _view_a = ""
                _onclick = f'onclick="_cpv(`{_clip_js}`)" '
                _dsite_a = ""
                if listing.dealer_url:
                    from urllib.parse import urlparse as _urlparse2
                    _dsite_domain = _urlparse2(listing.dealer_url).netloc.replace("www.", "")
                    _dsite_a = (
                        f'<a href="{_hurl(listing.dealer_url)}" target="_blank" '
                        f'{_onclick}'
                        f'style="color:#10b981;font-weight:600;text-decoration:none">🌐 Dealer Website</a>'
                        f'<span style="font-size:10px;color:#6ee7b7;margin-left:2px">✓</span>'
                    )
                elif listing.dealer_name:
                    _dsite_q = _url_quote(f"{listing.dealer_name} {listing.location or ''} official site".strip())
                    _dsite_a = (
                        f'<a href="https://www.google.com/search?q={_dsite_q}" target="_blank" '
                        f'{_onclick}'
                        f'style="color:#9ca3af;font-weight:600;text-decoration:none">🌐 Dealer site</a>'
                    )
                _links_html = '<span style="color:#555;margin:0 1px">·</span>'.join(filter(None, [
                    _view_a, _dsite_a,
                    f'<a href="{_hurl(_autotrader_url)}" target="_blank" {_onclick}style="color:#60a5fa;text-decoration:none">🔎 AutoTrader</a>',
                    f'<a href="{_hurl(_carsdotcom_url)}" target="_blank" {_onclick}style="color:#60a5fa;text-decoration:none">🚙 Cars.com</a>',
                    f'<a href="{_hurl(_cargurus_url)}" target="_blank" {_onclick}style="color:#60a5fa;text-decoration:none">🚗 CarGurus</a>',
                ]))
                _stc.html(
                    f"""<script>
function _cpv(t){{var e=document.createElement('textarea');e.value=t;e.style.cssText='position:fixed;opacity:0;top:-9999px';document.body.appendChild(e);e.focus();e.select();try{{document.execCommand('copy')}}catch(x){{}}document.body.removeChild(e);}}
</script>
<div style="font-family:sans-serif;font-size:11px;padding:2px 0;display:flex;gap:2px;flex-wrap:nowrap;align-items:center;overflow:hidden;white-space:nowrap">{_links_html}</div>""",
                    height=30,
                )

                # Live Check button for auto.dev listings
                if listing.source == "auto.dev" and listing.vin:
                    _live_data = st.session_state.get(_live_key)
                    if _live_data:
                        if "error" in _live_data:
                            st.error(_live_data["error"])
                        else:
                            _tc = _live_data["total_price_change"]
                            _tc_color = "#27ae60" if _tc < 0 else "#e74c3c"
                            _tc_label = f"${abs(_tc):,} price drop" if _tc < 0 else f"${abs(_tc):,} price increase"
                            # Fall back to card-level data when VIN endpoint returns empty fields
                            _dn = _live_data["dealer_name"] or listing.dealer_name or ""
                            _ph = _live_data["phone"]
                            _dloc = listing.location or ""
                            from urllib.parse import quote as _url_quote
                            _dw = _live_data.get("dealer_website") or ""
                            _link = _live_data["listing_url"] or (
                                f"https://www.google.com/search?q={_url_quote((_dn + ' ' + _dloc + ' inventory').strip())}" if _dn else ""
                            )
                            _phone_html = (
                                f'<a href="tel:{_ph}" style="font-size:16px;font-weight:bold;color:#60a5fa">{_ph}</a>'
                                if _ph else
                                (f'<a href="{_dw}" target="_blank" style="color:#60a5fa">Visit dealer website →</a>' if _dw else "No phone available")
                            )
                            st.markdown(
                                f"""
                                <div style="border:1px solid #2563eb;border-radius:8px;padding:12px;margin-bottom:12px;background:#1e3a5f;color:#ffffff">
                                    <b style="color:#ffffff">🔴 Live Data — {_dn}</b><br>
                                    💰 <b style="color:#facc15">Live Price: {_live_data['price_formatted']}</b>
                                    {"&nbsp;&nbsp;<span style='color:" + _tc_color + ";font-weight:bold'>" + _tc_label + "</span>" if _tc else ""}<br>
                                    📞 {_phone_html}<br>
                                    🛣 <span style="color:#d1d5db">Mileage: <b>{_live_data['mileage']:,} mi</b></span><br>
                                    {"<a href='" + _dw + "' target='_blank' style='color:#a78bfa'>🌐 Dealer website →</a><br>" if _dw else ""}
                                    {"<a href='" + _link + "' target='_blank' style='color:#34d399'>🔍 Find dealer inventory →</a>" if _link else ""}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            # ── Clipboard: car detail sheet ─────────────────
                            _clip_price = _live_data['price_formatted'] if _live_data.get('price') else f"${listing.asking_price or listing.price:,}"
                            _clip_miles = _live_data['mileage'] or listing.mileage
                            _clip_text = "\n".join(filter(None, [
                                listing.title,
                                f"Year:     {listing.year}",
                                f"Price:    {_clip_price}",
                                f"Mileage:  {_clip_miles:,} mi",
                                f"Exterior: {listing.exterior_color or 'N/A'}  |  Interior: {listing.interior_color or 'N/A'}",
                                f"Dealer:   {_dn}" if _dn else None,
                                f"Location: {listing.location or _location}",
                                f"Phone:    {_ph}" if _ph else None,
                                f"VIN:      {listing.vin}" if listing.vin else None,
                                f"AutoTrader search: {_autotrader_url}",
                            ]))
                            with st.expander("📋 Copy car details"):
                                st.code(_clip_text, language=None)

                            if _live_data.get("price_history"):
                                with st.expander("Price History"):
                                    for ph in _live_data["price_history"]:
                                        delta = ph["delta"]
                                        delta_str = (f" &nbsp;<span style='color:#27ae60'>▼ ${abs(delta):,}</span>" if delta and delta < 0
                                                     else f" &nbsp;<span style='color:#e74c3c'>▲ ${delta:,}</span>" if delta and delta > 0 else "")
                                        st.markdown(f"{ph['date']} — **${ph['price']:,}**{delta_str}", unsafe_allow_html=True)
                            if _live_data.get("features"):
                                with st.expander("Features"):
                                    st.markdown("  \n".join(f"• {f}" for f in _live_data["features"]))
                    else:
                        if st.button("🔴 Live Check", key=f"btn_{_live_key}", use_container_width=True):
                            from agents.search_agent import fetch_autodev_live
                            with st.spinner("Fetching live data..."):
                                st.session_state[_live_key] = fetch_autodev_live(listing.vin)
                            st.rerun()
                # VIN Agent — on-demand dealer page finder
                if listing.vin:
                    _vin_key = f"vin_result_{listing.vin}"
                    _vin_result = st.session_state.get(_vin_key)
                    if _vin_result:
                        if _vin_result.get("dealer_url"):
                            from urllib.parse import urlparse as _up2
                            _vd = _vin_result["dealer_url"]
                            _vdom = _up2(_vd).netloc.replace("www.","")
                            st.markdown(
                                f'✅ **[Dealer Page Found → {_vdom}]({_vd})**',
                                unsafe_allow_html=False
                            )
                        else:
                            _vph = _vin_result.get("dealer_phone","")
                            st.info(f"No dealer page found online.{f'  Call: **{_vph}**' if _vph else ''}")
                    else:
                        if st.button("🔍 Find Dealer Page", key=f"vin_btn_{listing.vin}", use_container_width=True):
                            from agents.vin_agent import run_vin_agent as _run_vin
                            with st.spinner("Claude searching for dealer page..."):
                                _tmp = listing.model_copy()
                                _run_vin(_tmp)
                                st.session_state[_vin_key] = {
                                    "dealer_url":   _tmp.dealer_url,
                                    "dealer_phone": _tmp.dealer_phone or listing.dealer_phone,
                                }
                            st.rerun()

                if listing.score_breakdown:
                    with st.expander("Why this score?"):
                        bd = listing.score_breakdown
                        for factor, label in [
                            ("price",          "Price"),
                            ("mileage",        "Mileage"),
                            ("exterior_color", "Exterior Color"),
                            ("interior_color", "Interior Color"),
                        ]:
                            f = bd.get(factor, {})
                            pts = f.get("points", 0)
                            mx  = f.get("max", 0)
                            bar = int((pts / mx * 100) if mx else 0)
                            st.markdown(
                                f"**{label}** — {pts}/{mx} pts  \n"
                                f"<div style='background:#e5e7eb;border-radius:4px;height:6px;margin:2px 0 4px'>"
                                f"<div style='background:#2563eb;width:{bar}%;height:6px;border-radius:4px'></div></div>"
                                f"<small style='color:#6b7280'>{f.get('reason','')}</small>",
                                unsafe_allow_html=True,
                            )

        _pagination_controls("bottom")

        # ── Delivery status ──────────────────────────────────────────────────
        st.subheader("Delivery Status")
        if outreach_retried:
            st.info("Outreach was regenerated after Critic feedback to improve personalization.")
        dcol1, dcol2 = st.columns(2)

        with dcol1:
            if _del_email and "email" in delivery:
                if delivery["email"].get("success"):
                    st.success(f"Email sent to {_user_email}")
                else:
                    st.error(f"Email failed: {delivery['email'].get('error')}")
                with st.expander("Preview Email Content"):
                    st.markdown(delivery.get("email_content", ""), unsafe_allow_html=True)

        with dcol2:
            if _del_sms and "sms" in delivery:
                if delivery["sms"].get("success"):
                    st.success(f"SMS sent to {_user_phone}")
                else:
                    st.error(f"SMS failed: {delivery['sms'].get('error')}")
                with st.expander("Preview SMS Content"):
                    st.code(delivery.get("sms_content", ""), language=None)

        # ── Dealer Outreach Results ──────────────────────────────────────────
        if dealer_results:
            st.subheader("Dealer Outreach")
            st.caption("Messages drafted to contact selling dealers on your behalf.")
            for dr in dealer_results:
                if "error" in dr:
                    st.error(f"{dr.get('dealer_name','Dealer')}: {dr['error']}")
                    continue
                with st.expander(f"📞 {dr['dealer_name']} — {dr.get('listing_title','')}"):
                    contact_parts = []
                    if dr.get("dealer_phone"):
                        contact_parts.append(f"📱 {dr['dealer_phone']}")
                    if dr.get("dealer_email"):
                        contact_parts.append(f"✉️ {dr['dealer_email']}")
                    if contact_parts:
                        st.markdown("**Contact:** " + " &nbsp;|&nbsp; ".join(contact_parts))
                    if dr.get("listing_url"):
                        st.markdown(f"**Listing:** [{dr['listing_url']}]({dr['listing_url']})")

                    sent_email = dr.get("email_sent")
                    sent_sms   = dr.get("sms_sent")
                    if sent_email:
                        if sent_email.get("success"):
                            st.success("Email sent to dealer automatically")
                        else:
                            st.warning(f"Email not sent: {sent_email.get('error')}")
                    if sent_sms:
                        if sent_sms.get("success"):
                            st.success("SMS sent to dealer automatically")
                        else:
                            st.warning(f"SMS not sent: {sent_sms.get('error')}")
                    if not sent_email and not sent_sms:
                        st.info("No dealer contact info available — copy message below to send manually.")

                    st.markdown("**Email Draft:**")
                    st.code(dr.get("email_content", ""), language=None)
                    st.markdown("**SMS Draft:**")
                    st.code(dr.get("sms_content", ""), language=None)

else:
    st.info("Fill in your preferences in the sidebar and click **Find Cars** to start the agent pipeline.")
    st.markdown("""
    ### How it works
    1. **Search Agent** — discovers listings from marketplaces
    2. **Ranking Agent** — scores each listing against your preferences
    3. **Outreach Agent** — generates and delivers personalized Email + SMS
    """)
