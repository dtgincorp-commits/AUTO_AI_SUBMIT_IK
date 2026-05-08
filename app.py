from dotenv import load_dotenv
load_dotenv(override=True)  # override=True ensures .env always wins over shell environment

import streamlit as st
from agents.models import CarPreferences
from agents.orchestrator import run_pipeline

st.set_page_config(
    page_title="AUTO AI - Car Discovery",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 AUTO AI — Car Discovery Agent")
st.caption("Powered by LangChain · Find your perfect car via AI agents")

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
    font-size: 17px !important;
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
div[data-testid="stForm"] { border: none !important; padding: 0 !important; }
</style>

<div class="nl-heading">🚀 &nbsp;What car are you hunting for?</div>
""", unsafe_allow_html=True)

with st.form("nl_form", clear_on_submit=False):
    _nl_col, _btn_col = st.columns([5, 1])
    with _nl_col:
        _nl_query = st.text_input(
            "nl",
            placeholder='e.g. "Used Honda CR-V under $30k near Irvine CA, max 60k miles"',
            label_visibility="collapsed",
            key="nl_query_input",
        )
    with _btn_col:
        _nl_btn = st.form_submit_button("🔍 Find Cars", use_container_width=True)

if "nl_parse_msg" in st.session_state:
    _msg_type, _msg_text = st.session_state.pop("nl_parse_msg")
    if _msg_type == "success":
        st.success(_msg_text)
    else:
        st.warning(_msg_text)

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
            st.session_state["p_price_min"]      = 1000
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
    location = st.text_input("Your ZIP or City", placeholder="e.g. Austin, TX or 78701", key="p_location")
    radius_miles = st.slider("Search Radius (miles)", min_value=10, max_value=200, key="p_radius_miles")

    st.subheader("Search Sources")
    from config import AUTODEV_API_KEY as _AUTODEV_KEY
    src_autodev     = st.checkbox("auto.dev", value=bool(_AUTODEV_KEY), disabled=not bool(_AUTODEV_KEY),
                                  help="Requires AUTODEV_API_KEY in .env — 1–4M listings, $0.002/call")
    src_marketcheck = st.checkbox("Marketcheck", value=True)
    src_ebay        = st.checkbox("eBay Motors (API key required)", value=False, disabled=True)
    src_cargurus    = st.checkbox("CarGurus (experimental)", value=False)
    src_craigslist  = st.checkbox("Craigslist",  value=True)

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
    if not make or not model or not location:
        st.error("Please fill in Make, Model, and Location.")
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
        trim=(trim if trim and trim.strip().lower() not in ("", "any") else None),
        price_min=int(price_min),
        price_max=int(price_max),
        exterior_color=None if exterior_color == "Any" else exterior_color,
        interior_color=None if interior_color == "Any" else interior_color,
        max_mileage=int(max_mileage) if max_mileage else None,
        location=location,
        radius_miles=radius_miles,
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
        "critic":           ("🎯 Critic Agent: Evaluating results...", 55),
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
    ] if on]

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
_last_result = st.session_state.get("_last_result")
_last_meta   = st.session_state.get("_last_meta", {})

if _last_result:
    listings         = _last_result["listings"]
    delivery         = _last_result.get("delivery", {})
    search_warning   = _last_result.get("search_warning")
    source_errors    = _last_result.get("source_errors", {})
    critic           = _last_result.get("critic")
    revision_count   = _last_result.get("revision_count", 0)
    outreach_retried = _last_result.get("outreach_retried", False)
    dealer_results   = _last_result.get("dealer_outreach", [])

    _make      = _last_meta.get("make", "")
    _model     = _last_meta.get("model", "")
    _condition = _last_meta.get("condition", "Any")
    _location  = _last_meta.get("location", "")
    _prefs     = _last_meta.get("prefs")
    _del_email = _last_meta.get("delivery_email", False)
    _del_sms   = _last_meta.get("delivery_sms", False)
    _user_email = _last_meta.get("user_email")
    _user_phone = _last_meta.get("user_phone")

    # ── No results ──────────────────────────────────────────────────────────
    if not listings:
        st.warning(f"No results found — {search_warning}" if search_warning else "No results found.")
        st.info("Try widening your price range, increasing the search radius, or removing color/mileage filters.")
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
        _badge_col, _vin_col = st.columns([1, 1])

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

        with _vin_col:
            with st.container(border=True):
                st.markdown("**📌 Pin a car by VIN**")
                st.caption("Paste a VIN from AutoTrader, Cars.com, or anywhere else")
                _vc1, _vc2 = st.columns([3, 1])
                with _vc1:
                    _vin_input = st.text_input(
                        "VIN", placeholder="e.g. 5UX13EU03T9384714",
                        label_visibility="collapsed", key="vin_lookup_input",
                    )
                with _vc2:
                    _vin_btn = st.button("Look Up", key="vin_lookup_btn", use_container_width=True)

                if _vin_btn and _vin_input:
                    with st.spinner("Decoding VIN..."):
                        from agents.search_agent import lookup_vin_listing
                        from agents.ranking_agent import run_ranking_agent as _rank
                        _vin_listing, _vin_err = lookup_vin_listing(_vin_input.strip(), _prefs)
                    if _vin_err:
                        st.error(_vin_err)
                    else:
                        _vin_scored = _rank(_prefs, [_vin_listing])
                        _vin_listing = _vin_scored[0] if _vin_scored else _vin_listing
                        _added = st.session_state.setdefault("vin_added_listings", [])
                        if not any(l.vin == _vin_listing.vin for l in _added):
                            _added.append(_vin_listing)
                            st.success(f"Added: **{_vin_listing.title}** — shown at the top of results.")
                            st.rerun()
                        else:
                            st.info("This VIN is already in your results.")

                _added_list = st.session_state.get("vin_added_listings", [])
                if _added_list:
                    st.markdown(f"**{len(_added_list)} car(s) added:**")
                    for _av in _added_list:
                        _av_col1, _av_col2 = st.columns([4, 1])
                        with _av_col1:
                            _price_str = f"${_av.asking_price:,}" if _av.asking_price else "Price not in auto.dev"
                            st.markdown(f"• **{_av.title}** &nbsp; {_price_str} &nbsp; `{_av.vin}`", unsafe_allow_html=True)
                        with _av_col2:
                            if st.button("✕", key=f"rm_vin_{_av.vin}", help="Remove"):
                                st.session_state["vin_added_listings"] = [l for l in _added_list if l.vin != _av.vin]
                                st.rerun()

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
        _SORT_OPTIONS = {
            "Match Score (Best First)":   lambda l: (-(l.match_score or 0)),
            "Distance: Closest First":    lambda l: (l.distance_miles if l.distance_miles is not None else 9999),
            "Price: Low → High":          lambda l: l.price,
            "Price: High → Low":          lambda l: -l.price,
            "Mileage: Low → High":        lambda l: l.mileage,
            "Year: Newest First":         lambda l: -(l.year or 0),
        }
        sort_col, _ = st.columns([2, 3])
        with sort_col:
            sort_choice = st.selectbox(
                "Sort by", list(_SORT_OPTIONS.keys()),
                key="results_sort",
                label_visibility="collapsed",
            )
        # Prepend any VIN-added listings (pinned at top, not sorted/paginated)
        _vin_added = st.session_state.get("vin_added_listings", [])
        sorted_listings = sorted(listings, key=_SORT_OPTIONS[sort_choice])

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

        # ── AutoTrader search URL (built once from search prefs) ────────────
        import re as _re
        _at_cond_seg = (
            "used-cars" if _condition == "Used" else
            "new-cars"  if _condition == "New"  else
            "all-cars"
        )
        _at_make_slug  = _make.lower().replace(" ", "-")
        _at_model_slug = _model.lower().replace(" ", "-").replace("/", "-")
        _zip_m = _re.search(r"\b(\d{5})\b", _location)
        _at_zip = _zip_m.group(1) if _zip_m else ""
        # Color slot goes between condition and make in AutoTrader path
        _ext_color = (_prefs.exterior_color or "") if _prefs else ""
        _at_color_seg = (_ext_color.lower().replace(" ", "-") + "/") if _ext_color and _ext_color.lower() not in ("any", "other", "") else ""
        _at_qp = []
        if _at_zip:
            _at_qp.append(f"zip={_at_zip}")
        if _prefs:
            if _prefs.price_min:    _at_qp.append(f"startPrice={_prefs.price_min}")
            if _prefs.price_max:    _at_qp.append(f"endPrice={_prefs.price_max}")
            if _prefs.max_mileage:  _at_qp.append(f"maxMileage={_prefs.max_mileage}")
        _autotrader_url = (
            f"https://www.autotrader.com/cars-for-sale/{_at_cond_seg}/{_at_color_seg}{_at_make_slug}/{_at_model_slug}"
            + ("?" + "&".join(_at_qp) if _at_qp else "")
        )
        # CarGurus new /search endpoint — make/model require internal entity IDs
        # (not public), so we pre-fill location/price/distance and open their
        # search page; user selects make+model in the CarGurus sidebar (one click).
        _cg_qp = ["sortType=PRICE", "sortDirection=ASC", "srpVariation=DEFAULT_SEARCH"]
        if _at_zip:
            _cg_qp.append(f"zip={_at_zip}")
        if _prefs:
            if _prefs.radius_miles: _cg_qp.append(f"distance={min(_prefs.radius_miles, 100)}")
            if _prefs.price_min:    _cg_qp.append(f"minPrice={_prefs.price_min}")
            if _prefs.price_max:    _cg_qp.append(f"maxPrice={_prefs.price_max}")
            if _prefs.max_mileage:  _cg_qp.append(f"maxMileage={_prefs.max_mileage}")
            if _condition == "New":   _cg_qp.append("listingTypes=NEW")
            elif _condition == "Used": _cg_qp.append("listingTypes=USED")
            if _ext_color and _ext_color.lower() not in ("any", "other", ""):
                _cg_qp.append(f"exteriorColor={_ext_color.lower()}")
        _cargurus_url = "https://www.cargurus.com/search?" + "&".join(_cg_qp)
        # Cars.com — supports plain-text make/model slugs like AutoTrader
        _cm_make  = _make.lower().replace(" ", "-")
        _cm_model = (_make + "-" + _model).lower().replace(" ", "-").replace("/", "-").replace(".", "")
        _cm_stock = "used" if _condition == "Used" else "new" if _condition == "New" else "all"
        _cm_qp = [f"stock_type={_cm_stock}", f"makes[]={_cm_make}", f"models[]={_cm_model}"]
        if _at_zip:          _cm_qp.append(f"zip={_at_zip}")
        if _prefs:
            if _prefs.radius_miles: _cm_qp.append(f"maximum_distance={_prefs.radius_miles}")
            if _prefs.price_min:    _cm_qp.append(f"price_min={_prefs.price_min}")
            if _prefs.price_max:    _cm_qp.append(f"price_max={_prefs.price_max}")
            if _prefs.max_mileage:  _cm_qp.append(f"mileage_max={_prefs.max_mileage}")
            if _ext_color and _ext_color.lower() not in ("any", "other", ""):
                _cm_qp.append(f"exterior_color_slugs[]={_ext_color.lower()}")
        _carsdotcom_url = "https://www.cars.com/shopping/results/?" + "&".join(_cm_qp)

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
                        <p style="margin:2px 0">🏢 {listing.dealer_name or "Private"}</p>
                        <p style="margin:2px 0">📍 {listing.location or _location}{f' &nbsp;<span style="color:#9ca3af;font-size:11px">({listing.distance_miles:.1f} mi away)</span>' if listing.distance_miles is not None else ''}</p>
                        <p style="margin:6px 0">Match score: <b style="color:{score_color}">{listing.match_score}/100</b></p>
                        {f'<p style="margin:2px 0;font-size:11px;color:#9ca3af">VIN: {listing.vin}</p>' if listing.vin else (f'<p style="margin:2px 0;font-size:11px;color:#9ca3af">Stock #: {listing.stock_number}</p>' if listing.stock_number else '')}
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
                _view_a = (
                    f'<a href="{_hurl(listing.listing_url)}" target="_blank" '
                    f'style="background:#2563eb;color:#fff;padding:2px 8px;border-radius:5px;'
                    f'font-size:11px;font-weight:700;text-decoration:none;white-space:nowrap">'
                    f'View Listing →</a>' if listing.listing_url else ""
                )
                _onclick = f'onclick="_cpv(`{_clip_js}`)" '
                _dsite_a = ""
                if listing.dealer_name:
                    _dsite_q = _url_quote(f"{listing.dealer_name} {listing.location or ''} official site".strip())
                    _dsite_a = (
                        f'<a href="https://www.google.com/search?q={_dsite_q}" target="_blank" '
                        f'{_onclick}'
                        f'style="color:#10b981;font-weight:600;text-decoration:none">🌐 Dealer site</a>'
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
