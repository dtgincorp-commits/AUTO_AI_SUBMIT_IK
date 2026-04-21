# Business Requirements Document (BRD)
## AUTO AI — Car Discovery & Outreach Agent

**Version:** 1.0  
**Date:** April 19, 2026  
**Author:** Neeraj Nagpal  
**Status:** Active Development

---

## 1. Executive Summary

AUTO AI is an AI-powered car discovery and outreach platform built to automate the end-to-end process of finding, ranking, and communicating personalized used car listings to buyers. The system leverages a multi-agent pipeline — combining real-time marketplace inventory data, AI-based scoring, and automated email/SMS delivery — to eliminate the manual effort of browsing multiple car listing sites.

---

## 2. Business Objectives

| # | Objective |
|---|-----------|
| 1 | Automate used car discovery based on buyer preferences (make, model, budget, mileage, color, location) |
| 2 | Surface real, live inventory from dealer websites via Marketcheck API |
| 3 | Rank listings by relevance using a multi-factor scoring algorithm |
| 4 | Deliver personalized results to buyers via Email and/or SMS |
| 5 | Provide a graceful fallback to AI-simulated listings when live data is unavailable |

---

## 3. Scope

### In Scope
- Web-based user interface for entering car preferences
- Real-time car inventory search via Marketcheck API
- AI-powered make/model name normalization (handles misspellings)
- Multi-factor listing ranking engine
- Automated email delivery via SendGrid
- Automated SMS delivery via Twilio
- AI-generated personalized email and SMS content via OpenAI GPT-4o-mini
- Graceful fallback to GPT-simulated listings if API is unavailable

### Out of Scope
- User account management / login
- Payment or financing integration
- Vehicle history reports (Carfax, AutoCheck)
- Direct dealer contact / lead submission
- Mobile native app (iOS/Android)

---

## 4. Stakeholders

| Role | Name |
|------|------|
| Product Owner | Neeraj Nagpal |
| Developer | Neeraj Nagpal |

---

## 5. Functional Requirements

### 5.1 User Input (Search Preferences)
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Make | Text | Yes | Auto-corrected via GPT (handles misspellings) |
| Model | Text | Yes | Auto-corrected via GPT |
| Min Price ($) | Number | Yes | USD |
| Max Price ($) | Number | Yes | USD, must be > Min |
| Exterior Color | Dropdown | No | Any, White, Black, Silver, Gray, Red, Blue, Green, Other |
| Interior Color | Dropdown | No | Any, Black, Beige, Gray, Brown, White, Red, Other |
| Max Mileage | Number | No | Miles |
| Location | Text | Yes | ZIP code or City, State |
| Search Radius | Slider | Yes | 10–200 miles |
| Delivery: Email | Checkbox | No | Requires valid email address |
| Delivery: SMS | Checkbox | No | Requires valid phone number |

### 5.2 Search Agent
- Accepts user preferences as structured input
- Normalizes make/model spelling using GPT-4o-mini before API call
- Queries Marketcheck API (`GET /v2/search/car/active`) with:
  - Make, model, price range, mileage cap, exterior color
  - Location (ZIP or city/state), search radius
  - Sorted by price ascending, up to 10 results
- Parses response: title, price, mileage, year, colors, dealer name, location, listing URL, source domain
- Falls back to GPT-simulated listings if Marketcheck key is absent or API fails
- Surfaces a warning banner in the UI when fallback is used

### 5.3 Ranking Agent
Scores each listing (0–100) using:

| Factor | Max Points | Logic |
|--------|-----------|-------|
| Price Proximity | 40 | Closer to midpoint of budget range = higher score |
| Mileage | 30 | Lower mileage relative to max = higher score |
| Exterior Color Match | 15 | Exact substring match |
| Interior Color Match | 15 | Exact substring match |

- Listings sorted by score descending
- Top 5 returned to UI and outreach

### 5.4 Outreach Agent
**Email:**
- GPT-4o-mini generates a personalized HTML email body
- Includes listing summaries: price, mileage, color, dealer, link
- Delivered via SendGrid API

**SMS:**
- GPT-4o-mini generates a concise SMS (≤300 characters)
- Includes top 1–3 cars with price and mileage
- Delivered via Twilio API

### 5.5 Results Display
- Top 5 listings shown as cards in a 3-column grid
- Each card shows: title, price, year, mileage, colors, dealer, location, match score, source badge, "View Listing" link
- Source badge color: green = real data, orange = AI simulated
- Warning banner shown if fallback to AI simulation was triggered

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | Marketcheck API call must complete within 15 seconds |
| Availability | App runs locally via Streamlit; no uptime SLA |
| Security | API keys stored in `.env` file, never committed to version control |
| Scalability | Stateless pipeline; each search is independent |
| Resilience | Full GPT fallback if Marketcheck API fails |
| Compatibility | Python 3.9+, macOS/Linux |

---

## 7. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│                  Streamlit (app.py)                          │
│         Sidebar: Preferences  │  Main: Results Cards        │
└────────────────────┬─────────────────────────────────────────┘
                     │ CarPreferences (Pydantic model)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR                             │
│                 agents/orchestrator.py                       │
│        Coordinates pipeline: Search → Rank → Outreach       │
└──────┬────────────────────┬──────────────────────┬──────────┘
       │                    │                      │
       ▼                    ▼                      ▼
┌─────────────┐   ┌──────────────────┐   ┌─────────────────┐
│   SEARCH    │   │    RANKING       │   │    OUTREACH     │
│    AGENT    │   │     AGENT        │   │     AGENT       │
│             │   │                  │   │                 │
│ 1. Normalize│   │ Score by:        │   │ Generate email  │
│    make/    │   │ • Price (40pts)  │   │ via GPT-4o-mini │
│    model    │   │ • Mileage (30pts)│   │                 │
│    via GPT  │   │ • Ext Color(15pt)│   │ Generate SMS    │
│             │   │ • Int Color(15pt)│   │ via GPT-4o-mini │
│ 2. Query    │   │                  │   │                 │
│ Marketcheck │   │ Return top 5     │   │ Send via:       │
│    API      │   │ sorted by score  │   │ • SendGrid      │
│             │   │                  │   │ • Twilio        │
│ 3. Fallback │   └──────────────────┘   └─────────────────┘
│    to GPT   │
│    if needed│
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL APIS                             │
│                                                             │
│  Marketcheck API          OpenAI API (GPT-4o-mini)         │
│  api.marketcheck.com      • Make/model normalization        │
│  • Real inventory         • Email content generation        │
│  • Dealer data            • SMS content generation          │
│  • Source domain          • Listing fallback simulation     │
│                                                             │
│  SendGrid API             Twilio API                        │
│  • Email delivery         • SMS delivery                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | Streamlit | ≥1.32.0 | Web UI |
| Agent Framework | LangChain | ≥0.2.0 | LLM chain orchestration |
| LLM | OpenAI GPT-4o-mini | — | Normalization, content generation, fallback |
| LLM Client | langchain-openai | ≥0.1.0 | OpenAI integration |
| Data Validation | Pydantic | ≥2.0.0 | CarPreferences, CarListing models |
| Car Inventory API | Marketcheck | v2 | Real-time used car listings |
| Email Delivery | SendGrid | ≥6.10.0 | Transactional email |
| SMS Delivery | Twilio | ≥9.0.0 | SMS messaging |
| HTTP Client | Requests | ≥2.31.0 | Marketcheck API calls |
| Config | python-dotenv | ≥1.0.0 | Environment variable management |
| Language | Python | 3.9+ | Runtime |

---

## 9. Data Models

### CarPreferences
```
make            str       Required   Vehicle make (e.g. Porsche)
model           str       Required   Vehicle model (e.g. 911)
price_min       int       Required   Minimum budget in USD
price_max       int       Required   Maximum budget in USD
exterior_color  str?      Optional   Preferred exterior color
interior_color  str?      Optional   Preferred interior color
max_mileage     int?      Optional   Maximum odometer reading
location        str       Required   ZIP code or city/state
radius_miles    int       Required   Search radius in miles
delivery_email  bool      Default T  Send results via email
delivery_sms    bool      Default F  Send results via SMS
user_email      str?      Optional   Recipient email address
user_phone      str?      Optional   Recipient phone number
```

### CarListing
```
title           str       Listing headline
price           int       Listed price in USD
mileage         int       Odometer reading in miles
year            int       Model year
exterior_color  str?      Exterior color
interior_color  str?      Interior color
dealer_name     str?      Selling dealer name
location        str?      Dealer city, state
listing_url     str?      Direct link to listing page
match_score     float?    Computed relevance score (0–100)
source          str?      Origin domain (e.g. dealer website)
```

---

## 10. External API Summary

### Marketcheck API
- **Base URL:** `https://api.marketcheck.com/v2`
- **Endpoint:** `GET /search/car/active`
- **Auth:** `api_key` query parameter
- **Key Params:** `make`, `model`, `price_min`, `price_max`, `mileage_max`, `zip`, `city`, `state`, `radius`, `exterior_color`, `rows`, `sort_by`, `sort_order`
- **Data Source:** Aggregates listings from individual dealer websites; does not include AutoTrader or CarGurus (those platforms block scraping)
- **Signup:** `https://www.marketcheck.com/automotive`

### OpenAI API
- **Model:** `gpt-4o-mini`
- **Uses:** Make/model normalization, email body generation, SMS generation, listing fallback simulation
- **Auth:** `OPENAI_API_KEY` environment variable

### SendGrid API
- **Use:** HTML email delivery
- **Auth:** `SENDGRID_API_KEY` environment variable
- **Requires:** Verified sender email (`SENDGRID_FROM_EMAIL`)

### Twilio API
- **Use:** SMS delivery
- **Auth:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`
- **Requires:** Twilio phone number (`TWILIO_PHONE_NUMBER`)

---

## 11. Environment Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `MARKETCHECK_API_KEY` | Recommended | Marketcheck API key (enables real listings) |
| `AUTODEV_API_KEY` | No | AutoDev key (reserved for future VIN enrichment) |
| `TWILIO_ACCOUNT_SID` | If SMS enabled | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | If SMS enabled | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | If SMS enabled | Twilio outbound number |
| `SENDGRID_API_KEY` | If Email enabled | SendGrid API key |
| `SENDGRID_FROM_EMAIL` | If Email enabled | Verified sender email |

---

## 12. Agent Pipeline Flow

```
User clicks "Find Cars"
        │
        ▼
[Input Validation]
  • Make, Model, Location required
  • price_min < price_max
  • Email/phone required if delivery selected
        │
        ▼
[Search Agent]
  1. GPT normalizes make/model spelling
  2. Marketcheck API called with all filters
  3. If 0 results or API error → GPT fallback
  4. Returns list of CarListing objects + warning flag
        │
        ▼
[Ranking Agent]
  • Scores each listing 0–100
  • Sorts by score descending
  • Returns top 5
        │
        ▼
[Outreach Agent]
  • If email enabled: GPT writes HTML email → SendGrid sends
  • If SMS enabled: GPT writes SMS → Twilio sends
        │
        ▼
[Display Results]
  • 5 listing cards with source badge + match score
  • Warning banner if fallback used
  • Delivery status confirmation
```

---

## 13. Known Limitations

| Limitation | Detail |
|------------|--------|
| AutoTrader / CarGurus data | Not available — both block third-party scraping; no public APIs exist |
| Marketcheck price filter | API may return listings slightly outside price range; ranking agent re-prioritizes by budget fit |
| Free tier API limits | Marketcheck free tier has monthly call limits |
| Location input | Works best with ZIP code; city/state parsing may be less precise |
| No persistent storage | Search results are not saved between sessions |
| Python 3.9 only | `str | None` union type syntax not supported; uses `Optional` instead |

---

## 14. Future Enhancements

| Priority | Enhancement |
|----------|-------------|
| High | Add VIN-based vehicle history enrichment via AutoDev API |
| High | Save search history and results to a local database (SQLite) |
| Medium | Add photo thumbnails from Marketcheck `media.photo_links` |
| Medium | User accounts with saved preferences and alerts |
| Medium | Price trend analysis (is listing price above/below market?) |
| Low | Deploy to cloud (Streamlit Cloud, AWS, GCP) |
| Low | Mobile-responsive UI improvements |
| Low | Support for new/CPO inventory in addition to used |

---

## 15. Setup & Run Instructions

### Prerequisites
- Python 3.9+
- API keys for OpenAI and Marketcheck (minimum)

### Installation
```bash
git clone <repo>
cd AUTO_AI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API keys
```

### Running
```bash
streamlit run app.py
# Opens at http://localhost:8501
```

---

*Document maintained by Neeraj Nagpal — AUTO AI Project*
