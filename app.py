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

RESULTS_PER_PAGE = 50

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
div[data-testid="stColumn"]:last-child button,
div[data-testid="stColumn"]:last-child button:focus {
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
div[data-testid="stColumn"]:last-child button:hover {
    transform: scale(1.04) !important;
    box-shadow: 0 6px 28px rgba(220, 38, 38, 0.8) !important;
}
div[data-testid="stColumn"]:last-child button:active {
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
        with st.spinner("Understanding your request..."):
            from agents.nl_parser import parse_query as _parse_query
            _parsed, _parse_err = _parse_query(_nl_query.strip())
        if _parse_err:
            st.error(f"Could not parse your request: {_parse_err}")
            st.stop()
        _COLOR_EXT = ["Any", "White", "Black", "Silver", "Gray", "Red", "Blue", "Green", "Other"]
        _COLOR_INT = ["Any", "Black", "Beige", "Gray", "Brown", "White", "Red", "Other"]
        _COND = ["Any", "Used", "New", "Certified Pre-Owned (CPO)"]
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
            st.session_state["p_radius_miles"]  = max(10, min(100, int(_parsed["radius_miles"])))

        _has_required = _parsed.get("make") and _parsed.get("model") and _parsed.get("location")
        if _has_required:
            st.session_state["_nl_auto_run"] = True
        else:
            _missing = [f for f, v in [("make", _parsed.get("make")), ("model", _parsed.get("model")), ("location", _parsed.get("location"))] if not v]
            st.session_state["nl_parse_msg"] = (
                "warning",
                f"Please also specify **{', '.join(_missing)}** — filled what I could, check the sidebar.",
            )
            st.rerun()
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

        # ── Critic badge ────────────────────────────────────────────────────
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

        # ── Pagination setup ─────────────────────────────────────────────────
        total       = len(listings)
        total_pages = max(1, (total + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
        page        = min(st.session_state.get("results_page", 0), total_pages - 1)
        start       = page * RESULTS_PER_PAGE
        end         = min(start + RESULTS_PER_PAGE, total)
        page_listings = listings[start:end]

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
        st.subheader(f"Top Matches — Page {page + 1}")
        cols = st.columns(3)

        for i, listing in enumerate(page_listings):
            col = cols[i % 3]
            with col:
                score_color = "green" if (listing.match_score or 0) >= 70 else "orange"
                source = listing.source or "Unknown"
                source_color = "#e67e22" if source in ("AI Simulated", "Unknown") else "#2ecc71"
                source_badge = f'<span style="background:{source_color};color:#fff;border-radius:4px;padding:2px 7px;font-size:11px;font-weight:bold">{source}</span>'
                view_link = f'<a href="{listing.listing_url}" target="_blank">View Listing →</a>' if listing.listing_url else ""

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
                    <div style="border:1px solid #ddd; border-radius:10px; padding:16px; margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start">
                            <h4 style="margin:0">{listing.title}</h4>
                            {source_badge}
                        </div>
                        {price_block}
                        <p style="margin:2px 0">📅 Year: <b>{listing.year}</b></p>
                        <p style="margin:2px 0">🛣 Mileage: <b>{listing.mileage:,} mi</b></p>
                        <p style="margin:2px 0">🎨 Ext: {listing.exterior_color or "N/A"} &nbsp;|&nbsp; Int: {listing.interior_color or "N/A"}</p>
                        <p style="margin:2px 0">🏢 {listing.dealer_name or "Private"}</p>
                        <p style="margin:2px 0">📍 {listing.location or _location}</p>
                        <p style="margin:6px 0">Match score: <b style="color:{score_color}">{listing.match_score}/100</b></p>
                        {view_link}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
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
