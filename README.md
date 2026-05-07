# AUTO AI — Car Discovery & Outreach Agent

An AI-powered multi-agent pipeline that searches live dealer inventory across 5 sources, ranks listings by relevance, evaluates result quality, and delivers personalized results via email and SMS.

**Version:** 2.1 | **Status:** Live — In Active Professional Use | **Author:** Neeraj Nagpal

---

## What It Does

1. User enters car preferences (make, model, budget, location, condition, color, mileage)
2. **Search Agent** queries 5 sources in parallel — auto.dev, Marketcheck, eBay Motors, CarGurus, Craigslist
3. **Ranking Agent** scores every listing on price, mileage, and color match (0–100)
4. **Critic Agent** evaluates result quality (Green / Amber / Red badge) and triggers automatic revision if needed
5. **Outreach Agent** generates a personalized email and SMS and delivers via SendGrid / Twilio
6. UI displays ranked listing cards with VIN, stock number, distance, one-click search links, and a Live Check button

---

## Quick Start

```bash
git clone <repo>
cd AUTO_AI_1.1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your API keys
.venv/bin/python -m streamlit run app.py
```

App opens at `http://localhost:8501`

---

## API Keys

| Key | Required | Source |
|---|---|---|
| `OPENAI_API_KEY` | Yes | platform.openai.com |
| `AUTODEV_API_KEY` | Recommended | auto.dev — primary inventory + Live Check |
| `MARKETCHECK_API_KEY` | Recommended | marketcheck.com — secondary inventory |
| `EBAY_APP_ID` | Optional | developer.ebay.com |
| `SCRAPERAPI_KEY` | Optional | scraperapi.com — enables CarGurus results |
| `SENDGRID_API_KEY` + `SENDGRID_FROM_EMAIL` | If email | sendgrid.com |
| `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` + `TWILIO_PHONE_NUMBER` | If SMS | twilio.com |

---

## Data Sources

| Source | Type | Provides |
|---|---|---|
| auto.dev | Structured API | VIN, stock number, distance, Live Check |
| Marketcheck | Structured API | Stock number, MSRP, listing URL |
| eBay Motors | Structured API | Auction and private sales |
| CarGurus | Web scrape (ScraperAPI) | Price, location |
| Craigslist | Web scrape | Private listings — excluded for New condition searches |

**No AI-simulated data is ever generated.** If no real listings are found, the app shows a clear error message.

---

## Key Business Rules

### VIN vs. Stock Number
- **VIN** — 17-character globally unique ID, assigned at factory, follows the car forever. Use for CarFax, any marketplace search, insurance, recall checks.
- **Stock Number** — Dealer-internal reference. Only meaningful at the specific dealer that issued it. **Do not search stock numbers on AutoTrader/Cars.com/CarGurus** — they will return completely unrelated cars.

### Clipboard Copy (on link click)
1. VIN available → copies VIN
2. No VIN → copies `{title} {stock#} {dealer_name}` — optimized for Google to find the exact car's VDP page
3. Nothing else → copies car title

### Craigslist and New Cars
Craigslist is excluded when `condition = "New"`. It is a private-seller platform with no new dealer inventory. It also reports `mileage=0` for all listings (mileage is unknown, not actually 0), which would inflate ranking scores.

### Mileage = 0 from Scraped Sources
CarGurus, Craigslist, and eBay don't show mileage in search results — the app stores 0 (unknown). The ranker gives these 15/30 mileage points (neutral) instead of 30/30 (perfect), preventing artificially inflated match scores.

### New Cars on Marketplaces
Franchise dealers list their full new inventory on AutoTrader, Cars.com, and CarGurus — 95%+ coverage for mainstream brands in major metro areas. The search links on each card are pre-filtered and fully usable for new car searches.

---

## Architecture

```
User → Streamlit UI (app.py)
         │
         ▼
    Orchestrator (orchestrator.py)
         │
         ├─ Search Agent ──► auto.dev + Marketcheck + eBay + CarGurus + Craigslist
         ├─ Ranking Agent ──► score 0–100 per listing
         ├─ Critic Agent ──► Green/Amber/Red badge + revision trigger
         ├─ [Revision loop up to 2×]
         ├─ Outreach Agent ──► SendGrid email + Twilio SMS
         └─ Critic Agent ──► outreach personalization check + 1 retry
```

Full architecture and all business rules: see [AUTO_AI_BRD_v2.md](AUTO_AI_BRD_v2.md)

---

## Listing Card Features

Each result card shows:
- Price (asking + MSRP delta if available)
- Year, mileage, exterior/interior color, dealer, location, distance
- Match score with per-factor breakdown
- VIN (if available) or Stock # (if available)
- **View Listing →** — direct link to the listing page
- **🌐 Dealer site** — Google search for dealer's website
- **🔎 AutoTrader · 🚙 Cars.com · 🚗 CarGurus** — pre-filtered search links
- **Live Check** button (auto.dev listings with VIN) — real-time price, phone, price history

---

*See [AUTO_AI_BRD_v2.md](AUTO_AI_BRD_v2.md) for full Business Requirements Document*
