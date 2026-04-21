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

# ── Sidebar: User Preferences ──────────────────────────────────────────────
with st.sidebar:
    st.header("Your Car Preferences")

    make = st.text_input("Make", placeholder="e.g. BMW, Toyota")
    model = st.text_input("Model", placeholder="e.g. X5, Camry")
    trim = st.text_input("Trim (optional)", placeholder="e.g. Sport, Luxury, Prestige")

    st.subheader("Budget")
    col1, col2 = st.columns(2)
    with col1:
        price_min = st.number_input("Min ($)", min_value=0, value=20000, step=1000)
    with col2:
        price_max = st.number_input("Max ($)", min_value=0, value=50000, step=1000)

    st.subheader("Vehicle Details")
    condition = st.selectbox("Condition", ["Any", "Used", "New", "Certified Pre-Owned (CPO)"])
    certified_only = condition == "Certified Pre-Owned (CPO)"
    exterior_color = st.selectbox(
        "Exterior Color",
        ["Any", "White", "Black", "Silver", "Gray", "Red", "Blue", "Green", "Other"],
    )
    interior_color = st.selectbox(
        "Interior Color",
        ["Any", "Black", "Beige", "Gray", "Brown", "White", "Red", "Other"],
    )
    max_mileage = st.number_input("Max Mileage", min_value=0, value=50000, step=5000)

    st.subheader("Location")
    location = st.text_input("Your ZIP or City", placeholder="e.g. Austin, TX or 78701")
    radius_miles = st.slider("Search Radius (miles)", 10, 200, 50)

    st.subheader("Delivery Preference")
    delivery_email = st.checkbox("Email", value=True)
    delivery_sms = st.checkbox("SMS")

    user_email = None
    user_phone = None
    if delivery_email:
        user_email = st.text_input("Your Email", placeholder="you@example.com")
    if delivery_sms:
        user_phone = st.text_input("Your Phone", placeholder="+1 555 000 0000")

    find_btn = st.button("Find Cars", type="primary", use_container_width=True)

# ── Main: Results ───────────────────────────────────────────────────────────
if find_btn:
    if not make or not model or not location:
        st.error("Please fill in Make, Model, and Location.")
        st.stop()
    if delivery_email and not user_email:
        st.error("Please enter your email address.")
        st.stop()
    if delivery_sms and not user_phone:
        st.error("Please enter your phone number.")
        st.stop()
    if price_min >= price_max:
        st.error("Min price must be less than Max price.")
        st.stop()

    prefs = CarPreferences(
        make=make,
        model=model,
        trim=trim or None,
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
    )

    # Progress display
    status_box = st.empty()
    progress_bar = st.progress(0)

    agent_steps = {
        "search": ("🔍 Search Agent: Scanning marketplaces...", 33),
        "ranking": ("📊 Ranking Agent: Scoring matches...", 66),
        "outreach": ("📨 Outreach Agent: Generating messages...", 90),
        "done": ("✅ Complete!", 100),
    }

    def on_status(step: str):
        label, pct = agent_steps.get(step, ("Working...", 50))
        status_box.info(label)
        progress_bar.progress(pct)

    try:
        result = run_pipeline(prefs, on_status=on_status)
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        st.stop()

    status_box.empty()
    progress_bar.empty()

    listings = result["listings"]
    delivery = result.get("delivery", {})
    search_warning = result.get("search_warning")

    if search_warning:
        st.warning(f"⚠️ Fell back to AI simulation — {search_warning}")

    cond_label = f" — {condition}" if condition != "Any" else ""
    st.success(f"Found {len(listings)} top matches for your {make} {model}{cond_label}!")

    st.markdown(f"<p style='color:gray'>{len(listings)} results</p>", unsafe_allow_html=True)
    sorted_listings = listings

    # ── Car listing cards ───────────────────────────────────────────────────
    st.subheader("Top Matches")
    cols = st.columns(3)

    for i, listing in enumerate(sorted_listings):
        col = cols[i % 3]
        with col:
            score_color = "green" if (listing.match_score or 0) >= 70 else "orange"
            source = listing.source or "Unknown"
            source_color = "#e67e22" if source in ("AI Simulated", "Unknown") else "#2ecc71"
            source_badge = f'<span style="background:{source_color};color:#fff;border-radius:4px;padding:2px 7px;font-size:11px;font-weight:bold">{source}</span>'
            view_link = f'<a href="{listing.listing_url}" target="_blank">View Listing →</a>' if listing.listing_url else ""
            st.markdown(
                f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:16px; margin-bottom:12px;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start">
                        <h4 style="margin:0">{listing.title}</h4>
                        {source_badge}
                    </div>
                    <p style="font-size:22px; font-weight:bold; color:#1f77b4; margin:4px 0">
                        ${listing.price:,}
                    </p>
                    <p style="margin:2px 0">📅 Year: <b>{listing.year}</b></p>
                    <p style="margin:2px 0">🛣 Mileage: <b>{listing.mileage:,} mi</b></p>
                    <p style="margin:2px 0">🎨 Ext: {listing.exterior_color or "N/A"} &nbsp;|&nbsp; Int: {listing.interior_color or "N/A"}</p>
                    <p style="margin:2px 0">🏢 {listing.dealer_name or "Private"}</p>
                    <p style="margin:2px 0">📍 {listing.location or location}</p>
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

    # ── Delivery status ─────────────────────────────────────────────────────
    st.subheader("Delivery Status")
    dcol1, dcol2 = st.columns(2)

    with dcol1:
        if delivery_email and "email" in delivery:
            if delivery["email"].get("success"):
                st.success(f"Email sent to {user_email}")
            else:
                st.error(f"Email failed: {delivery['email'].get('error')}")
            with st.expander("Preview Email Content"):
                st.markdown(delivery.get("email_content", ""), unsafe_allow_html=True)

    with dcol2:
        if delivery_sms and "sms" in delivery:
            if delivery["sms"].get("success"):
                st.success(f"SMS sent to {user_phone}")
            else:
                st.error(f"SMS failed: {delivery['sms'].get('error')}")
            with st.expander("Preview SMS Content"):
                st.code(delivery.get("sms_content", ""), language=None)

else:
    st.info("Fill in your preferences in the sidebar and click **Find Cars** to start the agent pipeline.")
    st.markdown("""
    ### How it works
    1. **Search Agent** — discovers listings from marketplaces
    2. **Ranking Agent** — scores each listing against your preferences
    3. **Outreach Agent** — generates and delivers personalized Email + SMS
    """)
