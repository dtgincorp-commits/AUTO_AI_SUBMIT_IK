# AUTO AI — Car Discovery & Outreach Agent
## Business Requirements Document v2.1

| | |
|---|---|
| **Document Type** | Business Requirements Document (BRD) |
| **Version** | 2.1 |
| **Date** | May 7, 2026 |
| **Author** | Neeraj Nagpal |
| **Status** | Live — In Active Professional Use |
| **Classification** | Confidential |

**Powered By:** LangChain · OpenAI GPT-4o-mini · auto.dev · Marketcheck · eBay Motors · CarGurus · Craigslist · Twilio · SendGrid · Streamlit · ChromaDB · LangSmith · DeepEval

---

## What's New in v2.1

This version documents production hardening and UI enhancements added after the app was deployed for professional office use:

- **Multi-source parallel search** — 5 live data sources (auto.dev, Marketcheck, eBay Motors, CarGurus, Craigslist) queried simultaneously; results merged, deduplicated, and relevance-filtered
- **AI simulation fallback fully removed** — app never returns fake listings; returns a clear error message when no real data is found
- **VIN + Stock Number on listing cards** — VIN displayed when available; Stock # shown as fallback; both extracted from structured API sources
- **Smart clipboard copy** — clicking any external link copies: VIN if available, otherwise `{title} {stock#} {dealer_name}` — optimized for Google/dealer-site search
- **One-click search links** — AutoTrader, Cars.com, and CarGurus pre-filtered search links on every card (make, model, color, price, mileage, condition, ZIP)
- **Dealer site link** — Google search link for the specific dealer on every card
- **Live Check** — on-demand VIN lookup via auto.dev for real-time price, phone, price history, and features
- **Distance calculation** — haversine distance from buyer location to each dealer; "Distance: Closest First" sort option added
- **Condition filter enforcement** — Craigslist excluded entirely for New car searches; mileage=0 from scraped sources treated as unknown (half credit) not perfect
- **New CarListing fields** — `vin`, `stock_number`, `distance_miles`, `asking_price`, `msrp`, `dealer_phone`, `dealer_email`
- **New env vars** — `AUTODEV_API_KEY`, `EBAY_APP_ID`, `SCRAPERAPI_KEY`

---

## What's New in v2.0

This version documents significant enhancements added as part of the AI Agent Capstone program:

- **Critic Agent** with Green/Amber/Red quality badge system
- **Critic/Revision Loop** — automated search retry with parameter adjustment
- **RAG Pipeline** — ChromaDB vector database with 4 knowledge collections
- **LangSmith Observability** — full pipeline tracing and monitoring
- **DeepEval Test Suite** — rule-based and LLM-as-Judge evaluation framework
- **Two new Pydantic models** — `DimensionResult`, `CriticResult`
- **Outreach enrichment** — email grounded in verified car spec facts from RAG

---

## Table of Contents

| # | Section |
|---|---|
| 1 | Executive Summary |
| 2 | Business Objectives |
| 3 | Scope |
| 4 | Functional Requirements |
| 5 | Non-Functional Requirements |
| 6 | System Architecture |
| 7 | Technology Stack |
| 8 | Data Models |
| 9 | External API Summary |
| 10 | Environment Configuration |
| 11 | Agent Pipeline Flow |
| 12 | Known Limitations |
| 13 | Future Enhancements |
| 14 | Setup & Run Instructions |
| 15 | PR / FAQ |
| 16 | Product Strategy |
| 17 | Design Architecture Diagram |
| 18 | Detailed Workflow |
| 19 | Agent Deep Dive |
| 20 | Evaluation Framework |
| 21 | Curriculum Concepts Applied |
| **22** | **Business Rules & Design Decisions** |

---

## SECTION 1 — Executive Summary

AUTO AI is an AI-powered car discovery and outreach platform that automates the end-to-end process of finding, ranking, and communicating personalized used car listings to buyers. The system leverages a multi-agent pipeline combining real-time marketplace inventory data, AI-based scoring, automated email/SMS delivery, and a self-correcting quality evaluation loop.

> **AUTO AI reduces the car buying research process from hours to seconds by combining real-time dealer inventory data, RAG-grounded AI personalization, and a Critic/Revision loop that guarantees result quality before delivery.**

Version 2.0 upgrades the original 3-agent pipeline into a full agentic system with quality evaluation, autonomous self-correction, retrieval-augmented generation, observability, and a formal evaluation framework — demonstrating production-grade multi-agent AI architecture.

---

## SECTION 2 — Business Objectives

| # | Objective | Priority |
|---|---|---|
| 1 | Automate used car discovery based on buyer preferences | High |
| 2 | Surface real, live inventory from dealer websites via Marketcheck API | High |
| 3 | Rank listings by relevance using a multi-factor scoring algorithm | High |
| 4 | Deliver personalized results to buyers via Email and/or SMS | Medium |
| 5 | Evaluate result quality before delivery using a Critic Agent | High *(new)* |
| 6 | Automatically revise search parameters when quality is insufficient | High *(new)* |
| 7 | Ground AI-generated content in verified car knowledge via RAG | Medium *(new)* |
| 8 | Provide full pipeline observability via LangSmith tracing | Medium *(new)* |
| 9 | Surface VIN, stock number, and dealer links on every listing card | High *(v2.1)* |
| 10 | Enable one-click search on AutoTrader, Cars.com, CarGurus from each card | High *(v2.1)* |
| 11 | Copy the best available car identifier to clipboard on every external link click | Medium *(v2.1)* |

---

## SECTION 3 — Scope

### In Scope
- Web-based user interface for entering car preferences (Streamlit)
- **Multi-source parallel inventory search: auto.dev, Marketcheck, eBay Motors, CarGurus (scraper), Craigslist**
- AI-powered make/model name normalization (handles user misspellings)
- Multi-factor listing ranking engine (price, mileage, color match)
- **Critic Agent with 4-dimension quality evaluation and Green/Amber/Red badge**
- **Automatic search revision loop (up to 2 cycles) when Critic flags quality issues**
- **RAG pipeline with ChromaDB — car specs, market data, dealer data, market trends**
- **LangSmith pipeline tracing and observability**
- **DeepEval test suite — rule-based + LLM-as-Judge metrics**
- Automated email delivery via SendGrid with GPT-generated content
- Automated SMS delivery via Twilio with GPT-generated content
- **VIN and Stock Number displayed on listing cards**
- **Live Check — on-demand VIN lookup for real-time price, phone, and price history (auto.dev)**
- **One-click search links to AutoTrader, Cars.com, CarGurus — pre-filtered by make/model/price/color/ZIP**
- **Dealer site Google search link on every card**
- **Smart clipboard copy — VIN if available, else title + stock# + dealer name**
- **Distance from buyer location calculated and displayed; "Distance: Closest First" sort option**
- **Condition enforcement — Craigslist excluded for New car searches**

### Out of Scope
- User account management / authentication / login
- Payment or financing integration
- Vehicle history reports (Carfax, AutoCheck)
- Direct dealer contact or lead form submission
- Mobile native app (iOS / Android)
- AutoTrader and CarGurus direct API (no public API available)
- Voice interface / ASR / TTS *(planned for v3.0)*
- MCP server interface *(planned for v3.0)*

---

## SECTION 4 — Functional Requirements

### 4.1 User Input — Search Preferences

| Field | Type | Required | Notes |
|---|---|---|---|
| Make | Text | Yes | Auto-corrected via GPT |
| Model | Text | Yes | Auto-corrected via GPT |
| Trim | Text | No | Optional trim filter |
| Min Price ($) | Number | Yes | USD — must be less than Max Price |
| Max Price ($) | Number | Yes | USD |
| Condition | Dropdown | No | Any, Used, New, Certified Pre-Owned (CPO) |
| Exterior Color | Dropdown | No | Any, White, Black, Silver, Gray, Red, Blue, Green, Other |
| Interior Color | Dropdown | No | Any, Black, Beige, Gray, Brown, White, Red, Other |
| Max Mileage | Number | No | Odometer cap in miles |
| Location | Text | Yes | ZIP code or City, State format |
| Search Radius | Slider | Yes | 10 – 200 miles |
| Email Delivery | Checkbox | No | Requires valid email address |
| SMS Delivery | Checkbox | No | Requires valid phone number (+1 format) |

### 4.2 Search Agent
- Accepts user preferences as structured Pydantic model (`CarPreferences`)
- Normalizes make/model spelling using GPT-4o-mini before API call
- Single Nominatim geocode call resolves buyer location to ZIP + lat/lon for all sources
- **Queries up to 5 sources in parallel (ThreadPoolExecutor, 55s wall-clock limit):**
  - **auto.dev** — structured dealer inventory API; provides VIN, stock number, colors, distance coords
  - **Marketcheck** — structured dealer inventory API; provides stock number, MSRP, listing URL
  - **eBay Motors** — Finding API; price and mileage when available
  - **CarGurus** — web scrape via ScraperAPI JS-render proxy (requires `SCRAPERAPI_KEY`)
  - **Craigslist** — direct web scrape; no API key required
- Results deduplicated by listing URL (preferred) or (title, price, dealer) tuple
- Relevance filter applied to scraped sources (CarGurus, Craigslist, eBay) — title must contain make or model
- **Condition enforcement:** when `condition = "New"`, Craigslist results are excluded entirely (private-seller platform — new dealer inventory never appears there; also reports `mileage=0` for all listings, which would inflate ranking scores)
- **Haversine distance** calculated from buyer coordinates to each auto.dev listing; stored on `CarListing.distance_miles`
- If all sources return 0 results → clear error message surfaced in UI; **no AI-simulated data is ever generated**

### 4.3 Ranking Agent — Scoring Formula

| Factor | Max Points | Scoring Logic |
|---|---|---|
| Price Proximity | 40 pts | Closer to midpoint of budget range = higher score |
| Mileage | 30 pts | Lower mileage relative to max = higher score; **mileage=0 from scraped sources = 15 pts (unknown), not 30 pts** |
| Exterior Color Match | 15 pts | Substring match between preference and listing |
| Interior Color Match | 15 pts | Substring match between preference and listing |
| **TOTAL** | **100 pts** | **Top listings returned sorted descending (up to MAX_RESULTS)** |

**Important mileage rule:** Craigslist, CarGurus, and eBay do not report mileage in search results — they return `mileage=0`. This `0` means *unknown*, not *zero miles driven*. Treating it as 0 miles would give full mileage points and artificially inflate scores (seen as 99% match for clearly-used cars). These listings receive 15/30 mileage points (neutral) instead.

- **If RAG knowledge base is available, market context for the make/model/region is attached to each listing's score breakdown**

### 4.4 Outreach Agent

| Channel | Generator | Delivery Service | Content |
|---|---|---|---|
| Email | GPT-4o-mini | SendGrid API | Personalized HTML email with listing cards, prices, links |
| SMS | GPT-4o-mini | Twilio API | Concise summary ≤300 chars — top 3 cars with price & mileage |

- **If RAG knowledge base is available, verified car spec facts (trims, MPG, price range) are injected into the email prompt**
- **If Critic flags low personalization score, email is regenerated with targeted feedback**

### 4.5 Critic Agent *(new in v2.0)*

The Critic Agent evaluates pipeline output quality across 4 dimensions using a 0–100 point system. It produces a **Green / Amber / Red badge** surfaced in the UI.

| Dimension | Max Score | Method | Pass Threshold |
|---|---|---|---|
| Result Relevance | 25 pts | Rule-based: price and mileage constraint compliance | 100% of listings pass |
| Result Quality | 25 pts | Rule-based: count of listings with match_score ≥ 60 | ≥ 3 listings |
| Data Source Trust | 25 pts | Rule-based: all AI Simulated → Amber (12 pts); any real → pass | At least 1 real listing |
| Outreach Personalization | 25 pts | LLM-as-Judge: GPT scores email 1–5 for personalization | Score ≥ 3 |

**Badge Logic:**
- **Green** — overall score ≥ 70 and no amber/fail dimensions
- **Amber** — overall score ≥ 40 or any amber-flagged dimension
- **Red** — overall score < 40 with failing dimensions

### 4.6 Critic/Revision Loop *(new in v2.0)*

- After ranking, the Critic evaluates results (search phase — no LLM call)
- If `revision_needed = True` and revision cycle < 2:
  - If fewer than 3 listings: radius expanded by +25 miles
  - If average match score < 50: price range relaxed by ±10%
  - Search and ranking re-run with adjusted parameters
- After outreach, Critic re-evaluates including personalization (LLM-as-Judge)
- If personalization score < 3 and no delivery error: outreach regenerated with critic feedback
- Maximum 2 search revision cycles + 1 outreach retry = 4 Critic calls worst case

### 4.7 RAG Knowledge Base *(new in v2.0)*

Four ChromaDB collections populated by `knowledge_base/build_index.py`:

| Collection | Documents | Data Source | Used By |
|---|---|---|---|
| `car_specs` | 35 (one per make/model) | fueleconomy.gov (real trims/MPG) + templates | Search Agent, Outreach Agent |
| `market_data` | 60 (15 models × 4 regions) | Realistic template data | Search Agent, Ranking Agent |
| `dealer_data` | ~40 (8 cities) | Marketcheck API (real) + templates | Available for future use |
| `market_trends` | 25 (5 segments × 5 regions) | Template data | Available for future use |

- Embeddings: `DefaultEmbeddingFunction` (local, no API key required)
- Similarity: cosine distance (ChromaDB HNSW index)
- Query interface: `agents/rag_agent.py` with lazy singleton client

---

## SECTION 5 — Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | Marketcheck API call must complete within 15 seconds |
| Availability | Runs locally via Streamlit; no uptime SLA currently |
| Security | API keys stored in .env file — never committed to version control |
| Scalability | Stateless pipeline; each search is fully independent |
| Resilience | Full GPT fallback if Marketcheck API fails or returns 0 results |
| Compatibility | Python 3.9+ on macOS / Linux |
| **Observability** | **Full pipeline traced to LangSmith on every run** |
| **Evaluation** | **DeepEval test suite must pass rule-based tests on every code change** |
| **Quality Gate** | **Critic badge must be computed and displayed for every search result** |

---

## SECTION 6 — System Architecture

| Layer | Component | Technology | Role |
|---|---|---|---|
| Frontend | app.py | Streamlit | User interface — preferences sidebar, results grid, Critic badge |
| Orchestration | orchestrator.py | Python + LangSmith | Coordinates Search → Rank → Critic Loop → Outreach → Outreach Critic |
| Agent | search_agent.py | LangChain + Requests | Make/model normalization, Marketcheck query, RAG-grounded GPT fallback |
| Agent | ranking_agent.py | Python | Multi-factor scoring, RAG market context attachment |
| Agent | outreach_agent.py | LangChain + APIs | RAG-enriched email/SMS generation and delivery |
| **Agent** | **critic_agent.py** | **Python + LangChain** | **4-dimension quality evaluation, LLM-as-Judge, badge computation** |
| **RAG** | **rag_agent.py** | **ChromaDB** | **Semantic retrieval from 4 knowledge collections** |
| **Knowledge Base** | **knowledge_base/** | **ChromaDB + fueleconomy.gov** | **Persistent vector store — car specs, market data, dealer data, trends** |
| Data Models | models.py | Pydantic v2 | CarPreferences, CarListing, DimensionResult, CriticResult |
| Config | config.py | python-dotenv | Environment variable management |
| **Observability** | **LangSmith** | **@traceable decorator** | **Full pipeline tracing and monitoring** |
| **Evaluation** | **tests/test_pipeline_eval.py** | **DeepEval + pytest** | **Rule-based + LLM-as-Judge test suite** |
| External API | Marketcheck | REST API v2 | Real-time used car inventory |
| External API | OpenAI GPT-4o-mini | OpenAI SDK | Normalization, email, SMS, LLM-as-Judge |
| External API | fueleconomy.gov | REST API (free) | Real trim and MPG data for knowledge base |
| External API | SendGrid | SendGrid SDK | Transactional HTML email |
| External API | Twilio | Twilio SDK | SMS delivery |

---

## SECTION 7 — Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Frontend | Streamlit | ≥1.32.0 | Web UI |
| Agent Framework | LangChain | ≥0.2.0 | LLM chain orchestration |
| LLM | OpenAI GPT-4o-mini | Latest | Normalization, content generation, fallback, LLM-as-Judge |
| LLM Client | langchain-openai | ≥0.1.0 | OpenAI API integration |
| Data Validation | Pydantic | ≥2.0.0 | All agent input/output models |
| **Vector DB** | **ChromaDB** | **≥1.5.0** | **Persistent semantic search knowledge base** |
| **Observability** | **LangSmith** | **≥0.4.0** | **Pipeline tracing, run monitoring** |
| **Evaluation** | **DeepEval** | **0.21.78** | **Rule-based + LLM metric test suite** |
| Car Inventory | Marketcheck API | v2 | Real-time used car listings |
| **Car Specs** | **fueleconomy.gov API** | **Free** | **Real trim and MPG data — no key required** |
| Email Delivery | SendGrid | ≥6.10.0 | Transactional email |
| SMS Delivery | Twilio | ≥9.0.0 | SMS messaging |
| HTTP Client | Requests | ≥2.31.0 | External API calls |
| Config | python-dotenv | ≥1.0.0 | Environment variable management |
| Language | Python | 3.9+ | Runtime |

---

## SECTION 8 — Data Models

### CarPreferences
| Field | Type | Required | Description |
|---|---|---|---|
| make | str | Yes | Vehicle make — auto-corrected via GPT |
| model | str | Yes | Vehicle model — auto-corrected via GPT |
| trim | str? | No | Optional trim filter |
| price_min | int | Yes | Minimum budget in USD |
| price_max | int | Yes | Maximum budget in USD |
| exterior_color | str? | No | Preferred exterior color |
| interior_color | str? | No | Preferred interior color |
| max_mileage | int? | No | Maximum odometer reading in miles |
| location | str | Yes | ZIP code or City, State |
| radius_miles | int | Yes | Search radius in miles |
| condition | str? | No | Any, Used, New, or Certified Pre-Owned |
| certified_only | bool | Default F | CPO listings only |
| delivery_email | bool | Default T | Send results via email |
| delivery_sms | bool | Default F | Send results via SMS |
| user_email | str? | No | Recipient email address |
| user_phone | str? | No | Recipient phone number |

### CarListing
| Field | Type | Description |
|---|---|---|
| title | str | Listing headline (Year Make Model Trim) |
| price | int | Effective price used for ranking |
| asking_price | int? | Raw dealer asking price (0 = not published) |
| msrp | int? | Manufacturer suggested retail price |
| mileage | int | Odometer reading in miles (0 = unknown for scraped sources) |
| year | int | Model year |
| exterior_color | str? | Exterior color |
| interior_color | str? | Interior color |
| dealer_name | str? | Selling dealer name |
| dealer_phone | str? | Dealer phone number |
| dealer_email | str? | Dealer email address |
| location | str? | Dealer city and state |
| listing_url | str? | Direct link to listing page |
| match_score | float? | Computed relevance score (0–100) |
| score_breakdown | dict? | Per-factor points and reasons |
| source | str? | Origin: auto.dev / Marketcheck / eBay Motors / CarGurus / Craigslist |
| vin | str? | 17-character Vehicle Identification Number — globally unique, follows car for life |
| stock_number | str? | Dealer-internal stock reference — meaningful only at that specific dealership |
| distance_miles | float? | Haversine distance from buyer location to dealer (auto.dev only) |

### DimensionResult *(new in v2.0)*
| Field | Type | Description |
|---|---|---|
| name | str | Dimension identifier |
| passed | bool | Whether this dimension met its threshold |
| score | float | Points earned (0–25) |
| reason | str | Human-readable explanation |
| flag | str | "pass" / "amber" / "fail" |

### CriticResult *(new in v2.0)*
| Field | Type | Description |
|---|---|---|
| overall_score | float | Total score 0–100 (sum of 4 dimensions) |
| badge | str | "green" / "amber" / "red" |
| dimensions | Dict[str, DimensionResult] | Per-dimension breakdown |
| revision_needed | bool | Whether search should be retried |
| revision_feedback | str | Targeted feedback for revision or outreach retry |

---

## SECTION 9 — External API Summary

| API | Status | Base URL | Auth Method | Primary Use |
|---|---|---|---|---|
| **auto.dev** | **Active** | **auto.dev/api** | **Bearer token** | **Primary inventory source — VIN, stock#, distance, live VIN lookup** |
| Marketcheck | Active | api.marketcheck.com/v2 | api_key param | Secondary inventory source — structured dealer listings |
| eBay Motors | Active | svcs.ebay.com/services/search/FindingService/v1 | EBAY_APP_ID param | Tertiary source — auction and private sales |
| CarGurus | Active (scrape) | cargurus.com | ScraperAPI proxy | Web-scraped inventory — requires SCRAPERAPI_KEY |
| Craigslist | Active (scrape) | {city}.craigslist.org | None | Web-scraped private listings — excluded for New condition searches |
| Nominatim (OSM) | Active | nominatim.openstreetmap.org | None (free) | Single geocode call to resolve buyer location to ZIP + lat/lon |
| OpenAI | Active | api.openai.com/v1 | Bearer token | Normalization, email/SMS generation, LLM-as-Judge |
| SendGrid | Active | api.sendgrid.com/v3 | API key header | Email delivery |
| Twilio | Active | api.twilio.com | AccountSID + Token | SMS delivery |
| **fueleconomy.gov** | **Active** | **fueleconomy.gov/ws/rest** | **None (free)** | **Real trim and MPG data for RAG knowledge base** |
| **LangSmith** | **Active** | **api.smith.langchain.com** | **API key** | **Pipeline tracing and run monitoring** |
| AutoTrader | N/A | No public API | Enterprise only | Not integrated — search links generated client-side |
| Cars.com | N/A | No public API | N/A | Not integrated — search links generated client-side |

---

## SECTION 10 — Environment Configuration

| Variable | Required | Description |
|---|---|---|
| OPENAI_API_KEY | Yes | OpenAI API key for GPT-4o-mini |
| AUTODEV_API_KEY | Recommended | auto.dev key — primary inventory source; also enables Live Check VIN lookup |
| MARKETCHECK_API_KEY | Recommended | Marketcheck key — secondary structured inventory source |
| EBAY_APP_ID | Optional | eBay Finding API app ID — tertiary inventory source |
| SCRAPERAPI_KEY | Optional | ScraperAPI key — enables CarGurus web-scraped results |
| TWILIO_ACCOUNT_SID | If SMS | Twilio account SID |
| TWILIO_AUTH_TOKEN | If SMS | Twilio auth token |
| TWILIO_PHONE_NUMBER | If SMS | Twilio outbound phone number |
| SENDGRID_API_KEY | If Email | SendGrid API key |
| SENDGRID_FROM_EMAIL | If Email | Verified SendGrid sender email |
| **LANGCHAIN_TRACING_V2** | **For tracing** | **Set to "true" to enable LangSmith** |
| **LANGSMITH_TRACING** | **For tracing** | **Set to "true" (new LangSmith SDK)** |
| **LANGCHAIN_API_KEY** | **For tracing** | **LangSmith API key** |
| **LANGSMITH_API_KEY** | **For tracing** | **LangSmith API key (new SDK alias)** |
| **LANGCHAIN_PROJECT** | **For tracing** | **Set to "AUTO_AI"** |
| **LANGSMITH_PROJECT** | **For tracing** | **Set to "AUTO_AI" (new SDK alias)** |

---

## SECTION 11 — Agent Pipeline Flow

| Step | Agent / Component | Input | Output | Fallback |
|---|---|---|---|---|
| 1 | Input Validation | User form data | CarPreferences model | Validation error shown in UI |
| 2 | Search Agent | CarPreferences | List of CarListing objects | GPT-simulated listings |
| 3 | Ranking Agent | List[CarListing] | Top 5 scored listings | None needed |
| **4** | **Critic Agent (Search)** | **CarPreferences + ranked listings** | **CriticResult — badge + revision_needed** | **None** |
| **5** | **Revision Loop** | **CriticResult + CarPreferences** | **Adjusted CarPreferences (if needed)** | **Break after 2 cycles** |
| 6 | Outreach Agent | Top 5 + user contacts | Email/SMS delivery result | Error shown in UI |
| **7** | **Critic Agent (Outreach)** | **CriticResult + outreach content** | **Final CriticResult with personalization score** | **None** |
| **8** | **Outreach Retry** | **Critic feedback** | **Regenerated email/SMS (if needed)** | **Skip if delivery failed** |
| 9 | Display | Ranked listings + Critic badge | Result cards + Green/Amber/Red badge | Warning banner |

---

## SECTION 12 — Known Limitations

| Limitation | Detail |
|---|---|
| AutoTrader / Cars.com direct data | No public inventory API — search links are generated client-side (pre-filtered by make/model/price/color/ZIP) |
| CarGurus scraping reliability | ScraperAPI JS-render is intermittent; retried once automatically; returns 0 silently if unavailable |
| Craigslist mileage | Craigslist never reports mileage in search results — stored as 0 (unknown); scored at 15/30 pts |
| Stock number availability | Stock numbers are only available from structured API sources (auto.dev, Marketcheck); scraped sources (Craigslist, CarGurus, eBay) never provide them |
| VIN availability | VINs only come from auto.dev listings; Marketcheck, eBay, CarGurus, and Craigslist do not include VINs in search results |
| Stock number portability | A stock number is dealer-internal only — searching it on any external marketplace (AutoTrader, Cars.com, etc.) will return unrelated results. It is only useful when communicating directly with that specific dealer |
| Marketcheck price filter | API may return listings slightly outside price range; ranking agent re-prioritizes |
| Free tier API limits | auto.dev and Marketcheck free tiers have monthly call volume limits |
| Location input | Works best with ZIP code; city/state parsing uses Nominatim geocoding which may be less precise |
| No persistent storage | Search results are not saved between sessions |
| Python 3.9 compatibility | `str \| None` union syntax not supported — uses `Optional[]` instead |
| **OpenAI key required** | **Email/SMS generation, make/model normalization, and LLM-as-Judge all need a valid key** |
| **RAG content quality** | **market_data and market_trends are template-based, not live market data** |
| **PII in LangSmith traces** | **User email/phone appear in trace payloads — acceptable for development, must be masked in production** |
| **DeepEval LLM tests** | **AnswerRelevancy and Hallucination tests require a valid OpenAI key to run** |

---

## SECTION 13 — Future Enhancements

| Priority | Enhancement | Benefit |
|---|---|---|
| High | VIN-based vehicle history enrichment via AutoDev API | Reliability data per listing |
| High | Save search history and results to SQLite database | Persistent user sessions |
| High | Mask PII (email/phone) before LangSmith trace payload | Production-grade privacy |
| High | Structured output parsing with `PydanticOutputParser` | Safe JSON parsing with automatic retry |
| Medium | Voice interface — Whisper ASR + TTS for hands-free search | Accessibility and mobile-first UX |
| Medium | MCP Server — expose agents as MCP tools for Claude Desktop | Multi-client interoperability |
| Medium | Display photo thumbnails from Marketcheck media links | Richer listing cards |
| Medium | User accounts with saved preferences and price alerts | Repeat engagement |
| Medium | Live market data source for `market_data` collection | Higher RAG accuracy |
| Low | Deploy to cloud (Streamlit Cloud / AWS / GCP) | Public accessibility |
| Low | Mobile-responsive UI improvements | Better mobile experience |

---

## SECTION 14 — Setup & Run Instructions

### Prerequisites
- Python 3.9+
- OpenAI API key (required)
- Marketcheck API key (recommended for real listings)
- LangSmith API key (optional — for tracing)

### Installation
```bash
git clone <repo>
cd AUTO_AI_1.1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API keys
```

### Build the Knowledge Base (one-time)
```bash
.venv/bin/python knowledge_base/build_index.py
# Builds 4 ChromaDB collections (~2 minutes, no OpenAI key needed)
```

### Running the App
```bash
.venv/bin/python -m streamlit run app.py
# Opens at http://localhost:8501
```

### Running the Evaluation Suite
```bash
# Rule-based tests (no OpenAI key needed)
.venv/bin/pytest tests/test_pipeline_eval.py -v -k "Critic"

# Full suite including LLM-as-Judge (requires OpenAI key)
.venv/bin/pytest tests/test_pipeline_eval.py -v
```

---

## SECTION 15 — PR / FAQ

### Press Release

**FOR IMMEDIATE RELEASE**

### AUTO AI v2.0 — AI Agent Now Self-Evaluates and Self-Corrects Car Search Results

*Anaheim, CA — April 22, 2026* — AUTO AI v2.0 introduces a Critic Agent that evaluates every car search result before it reaches the buyer. If result quality is insufficient, the pipeline automatically revises its search parameters and retries — up to twice — without any user intervention. A Green/Amber/Red quality badge is displayed alongside every result set, giving buyers full transparency into result confidence.

Additionally, v2.0 introduces a RAG pipeline backed by ChromaDB that grounds AI-generated content in a verified knowledge base of 35 car models, real MPG data from fueleconomy.gov, and regional market data — reducing hallucinated car details in outreach emails.

**FAQ**

**Q: What is the Green/Amber/Red badge?**
A: The Critic Agent evaluates results on 4 dimensions: constraint compliance, match quality, data source trust, and outreach personalization. Green = all dimensions pass (score ≥70). Amber = partial quality (score ≥40 or one amber dimension). Red = significant quality issues (score <40).

**Q: What triggers a revision cycle?**
A: If the Critic finds fewer than 3 valid listings or average match scores below 50, it triggers a retry with expanded radius (+25 miles) or relaxed price range (±10%). Maximum 2 retries.

**Q: What is RAG and what does it do here?**
A: RAG (Retrieval-Augmented Generation) retrieves relevant text from a ChromaDB vector database before asking GPT to generate content. In AUTO AI, it grounds the GPT fallback search and outreach emails in real car spec facts — trims, MPG, and typical prices — instead of letting GPT hallucinate details.

**Q: Is the car data real or simulated?**
A: When a Marketcheck API key is configured, all listings are real and sourced directly from dealer websites. Without a key, the system falls back to GPT-simulated listings marked with an orange "AI Simulated" badge. The Critic Agent will assign an Amber badge to all-simulated result sets.

**Q: Is my data stored anywhere?**
A: Search results are not persisted between sessions. Pipeline runs are traced to LangSmith (if configured), which may include preference data. User email and phone appear in trace payloads in development — a known limitation to be addressed before production deployment.

---

## SECTION 16 — Product Strategy

### Vision
To become the go-to AI-powered car discovery layer — making personalized, real-time inventory search available to any buyer, dealer, or platform through a simple, intelligent, self-correcting agent pipeline.

### Strategic Pillars

| Pillar | Description |
|---|---|
| **Real Data First** | Connect to live dealer inventory via Marketcheck. AI simulation is a fallback, never the default goal. |
| **Quality-Gated Delivery** | The Critic Agent ensures results meet defined quality thresholds before reaching the buyer. |
| **Transparency** | Every match score is explainable. Every Critic badge shows per-dimension reasoning. |
| **RAG-Grounded Content** | Outreach content is grounded in verified facts, not GPT imagination. |
| **Omnichannel Delivery** | Results reach buyers via browser, email, or SMS without requiring an account. |
| **Extensible by Design** | New agents (VIN enrichment, voice, MCP) can plug in without rearchitecting. |

### Competitive Positioning

| Capability | AUTO AI | AutoTrader | CarGurus | Manual Search |
|---|---|---|---|---|
| Real inventory data | Yes | Yes | Yes | Yes |
| Public API access | Yes | No | No | N/A |
| AI-based ranking | Yes | No | Partial | No |
| **Self-correcting quality loop** | **Yes** | **No** | **No** | **No** |
| **Quality badge / transparency** | **Yes** | **No** | **No** | **No** |
| **RAG-grounded content** | **Yes** | **No** | **No** | **No** |
| Automated email/SMS | Yes | No | No | No |
| Make/model autocorrect | Yes | No | No | No |
| Free to use | Yes | No | No | Yes |
| Customizable pipeline | Yes | No | No | No |

### Go-to-Market Phases

| Phase | Name | Focus | Target |
|---|---|---|---|
| 1 | MVP | Local Streamlit app, Marketcheck integration | Developer / personal use |
| **2** | **Enhanced** | **Critic loop, RAG, LangSmith, DeepEval** | **Capstone demonstration** |
| 3 | Beta | Cloud deploy, user accounts, saved searches | Early adopters / dealerships |
| 4 | Growth | Voice interface, MCP server, VIN history | Consumer car buyers |
| 5 | Scale | White-label API for dealers, CRM integrations | Enterprise / dealer networks |

---

## SECTION 17 — Design Architecture Diagram

```
╔═════════════════════════════════════════════════════════════════╗
║                     PRESENTATION LAYER                          ║
╠═════════════════════════════════════════════════════════════════╣
║                                                                 ║
║   User (Browser)                                                ║
║        │                                                        ║
║   Streamlit Frontend  (app.py)                                  ║
║   ├── Preferences sidebar  (make · model · budget · location)   ║
║   ├── Green / Amber / Red  Critic quality badge                 ║
║   ├── Listing cards with match score breakdown                  ║
║   ├── Dealer outreach message drafts                            ║
║   └── Email / SMS delivery status                               ║
║                                                                 ║
╚══════════════════════════╤══════════════════════════════════════╝
                           │
╔══════════════════════════▼══════════════════════════════════════╗
║                    ORCHESTRATION LAYER                          ║
╠═════════════════════════════════════════════════════════════════╣
║                                                                 ║
║   Orchestrator  (orchestrator.py)   @traceable ──► LangSmith   ║
║                                                                 ║
║   Phase 1 ──  Search ──► Rank ──► Critic ──► Revise? ──┐       ║
║                   ▲                          (max 2×)   │       ║
║                   └─────────────────────────────────────┘       ║
║                                                                 ║
║   Phase 2 ──  Outreach (buyer) ──► Critic ──► Retry?           ║
║                                                                 ║
║   Phase 3 ──  Dealer Outreach  (broker mode · optional)        ║
║                                                                 ║
╚══════════════════════════╤══════════════════════════════════════╝
                           │
╔══════════════════════════▼══════════════════════════════════════╗
║                       AGENT LAYER                               ║
╠══════════════════════════════════╦══════════════════════════════╣
║                                  ║                              ║
║   Search Agent                   ║   Outreach Agent             ║
║   ├── Marketcheck API (primary)  ║   ├── Buyer  email / SMS     ║
║   └── GPT fallback + RAG context ║   └── Dealer email / SMS     ║
║                                  ║                              ║
║   Ranking Agent                  ║   RAG Agent                  ║
║   ├── Price       (40 pts)       ║   ├── query_car_specs()      ║
║   ├── Mileage     (30 pts)       ║   ├── query_market_data()    ║
║   ├── Ext color   (15 pts)       ║   ├── query_dealer_data()    ║
║   └── Int color   (15 pts)       ║   └── query_market_trends()  ║
║                                  ║                              ║
╠══════════════════════════════════╩══════════════════════════════╣
║                                                                 ║
║   Critic Agent                                                  ║
║   ├── Result Relevance          (rule-based · 25 pts)          ║
║   ├── Result Quality            (rule-based · 25 pts)          ║
║   ├── Data Source Trust         (rule-based · 25 pts)          ║
║   └── Outreach Personalization  (LLM Judge  · 25 pts)          ║
║                                                                 ║
╚══════════════════════════╤══════════════════════════════════════╝
                           │
╔══════════════════════════▼══════════════════════════════════════╗
║                      KNOWLEDGE BASE                             ║
╠═════════════════════════════════════════════════════════════════╣
║                                                                 ║
║   ChromaDB  (local · persistent · DefaultEmbeddingFunction)     ║
║                                                                 ║
║   ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐  ║
║   │  car_specs    │  │  market_data  │  │   dealer_data     │  ║
║   │  35 docs      │  │  60 docs      │  │   ~40 docs        │  ║
║   │  fueleconomy  │  │  price ranges │  │   Marketcheck     │  ║
║   └───────────────┘  └───────────────┘  └───────────────────┘  ║
║                      ┌───────────────┐                          ║
║                      │ market_trends │                          ║
║                      │  25 docs      │                          ║
║                      └───────────────┘                          ║
║                                                                 ║
╚══════════════════════════╤══════════════════════════════════════╝
                           │
╔══════════════════════════▼══════════════════════════════════════╗
║                    EXTERNAL SERVICES                            ║
╠══════════════════════════╦══════════════════════════════════════╣
║                          ║                                      ║
║   Marketcheck API        ║   OpenAI  GPT-4o-mini                ║
║   Live car inventory     ║   Search fallback · Email/SMS gen    ║
║   40,000+ US dealers     ║   Critic LLM Judge (1–5 score)       ║
║                          ║                                      ║
╠══════════════════════════╬══════════════════════════════════════╣
║                          ║                                      ║
║   SendGrid               ║   Twilio                             ║
║   Email delivery         ║   SMS delivery                       ║
║                          ║                                      ║
╠══════════════════════════╬══════════════════════════════════════╣
║                          ║                                      ║
║   fueleconomy.gov        ║   LangSmith                          ║
║   Trims + MPG data       ║   Pipeline observability & tracing   ║
║                          ║                                      ║
╚══════════════════════════╩══════════════════════════════════════╝
```

---

## SECTION 18 — Detailed Workflow

```
Input → Orchestrate → Normalize → Search ──→ Rank → Critic ──→ [Revise?] ──→ Outreach → Critic → [Retry?] → Display
                                              ↑__________________________|
                                                    (up to 2 cycles)
```

### Step-by-Step Breakdown

**Step 1 — User Input & Validation**
User fills the Streamlit sidebar. App validates all required fields and checks `price_min < price_max` before proceeding. A `CarPreferences` Pydantic model is constructed.

**Step 2 — Orchestrator Kicks Off Pipeline**
`run_pipeline()` is called, decorated with `@traceable` for LangSmith. Every agent call within is automatically captured in the trace.

**Step 3 — Search Agent: Normalize**
GPT-4o-mini corrects make/model spelling. Example: `'porche'` → `'Porsche'`.

**Step 4 — Search Agent: Query Marketcheck + RAG**
Calls `GET /v2/search/car/active`. If RAG knowledge base is available, car spec and market context is retrieved from ChromaDB and injected into the GPT fallback prompt. Each listing parsed into a `CarListing` Pydantic object.

**Step 5 — Ranking Agent**
Scores each listing on 4 factors (100 pts total). Attaches market context from RAG to `score_breakdown` if available. Returns top 5.

**Step 6 — Critic Agent (Search Phase)**
Evaluates result relevance, quality, and data source trust using rule-based checks. If `revision_needed = True` and cycle < 2, adjusts `radius_miles` or `price_min/max` and loops back to Step 4.

**Step 7 — Outreach Agent**
If email enabled: GPT writes personalized HTML email enriched with RAG car spec facts. If SMS enabled: GPT writes ≤300 char summary. Both delivered via SendGrid/Twilio.

**Step 8 — Critic Agent (Outreach Phase)**
LLM-as-Judge evaluates email personalization on a 1–5 scale. If score < 3, regenerates email with targeted critic feedback and re-evaluates once.

**Step 9 — Display Results**
Streamlit renders 5 listing cards in a 3-column grid. Green/Amber/Red badge displayed at top with per-dimension breakdown in an expander. Revision count and outreach retry notice shown if applicable.

---

## SECTION 19 — Agent Deep Dive

### Search Agent — `agents/search_agent.py`
| | |
|---|---|
| **Role** | Discover real car listings from live inventory APIs and normalize user input |
| **Input** | `CarPreferences` |
| **Output** | `list[CarListing]` + optional warning string |
| **Tools** | GPT-4o-mini (normalization), Marketcheck REST API v2, ChromaDB RAG (car_specs + market_data), GPT-4o-mini (fallback) |
| **Steps** | 1. GPT corrects make/model spelling · 2. Parse location · 3. Call Marketcheck · 4. Parse into CarListing objects · 5. If 0 results → retrieve RAG context → call GPT fallback |
| **Fallback** | GPT-4o-mini generates 5 simulated listings grounded in RAG context, marked "AI Simulated" |

### Ranking Agent — `agents/ranking_agent.py`
| | |
|---|---|
| **Role** | Score and prioritize listings by relevance to buyer preferences |
| **Input** | `CarPreferences` + `list[CarListing]` |
| **Output** | `list[CarListing]` — top 5, sorted by `match_score` descending |
| **Tools** | Pure Python (no LLM) + ChromaDB RAG (market_data) |
| **Steps** | 1. Retrieve market context from RAG · 2. Score price (40pts) + mileage (30pts) + ext color (15pts) + int color (15pts) · 3. Attach market_context to score_breakdown · 4. Sort and return top 5 |
| **Fallback** | No fallback needed — pure deterministic algorithm |

### Outreach Agent — `agents/outreach_agent.py`
| | |
|---|---|
| **Role** | Generate personalized content and deliver results via email and SMS |
| **Input** | `CarPreferences` + top 5 `CarListing` objects + optional `critic_feedback` |
| **Output** | Dict with email/SMS success status and generated content |
| **Tools** | ChromaDB RAG (car_specs), GPT-4o-mini, SendGrid API, Twilio API |
| **Steps** | 1. Retrieve car spec facts from RAG · 2. GPT writes HTML email enriched with facts (+ critic feedback if retry) · 3. Send via SendGrid · 4. GPT writes SMS · 5. Send via Twilio |
| **Fallback** | Delivery failure caught, shown as error in UI — pipeline continues |

### Critic Agent — `agents/critic_agent.py` *(new in v2.0)*
| | |
|---|---|
| **Role** | Evaluate pipeline output quality and determine if revision or retry is needed |
| **Input** | `CarPreferences` + `list[CarListing]` + optional `outreach_result` dict |
| **Output** | `CriticResult` — overall_score, badge, 4 DimensionResults, revision_needed, revision_feedback |
| **Tools** | Pure Python (3 dimensions) + GPT-4o-mini as LLM-as-Judge (1 dimension) |
| **Steps** | 1. `_check_result_relevance` — price/mileage constraint compliance · 2. `_check_result_quality` — match score threshold · 3. `_check_data_source_trust` — real vs simulated · 4. `_check_outreach_personalization` — LLM scores 1–5 · 5. Compute badge and revision feedback |
| **Called** | Up to 4 times per pipeline run: after ranking (×1–3 with revisions) + after outreach (×1–2 with retry) |

### RAG Agent — `agents/rag_agent.py` *(new in v2.0)*
| | |
|---|---|
| **Role** | Semantic retrieval interface for the ChromaDB knowledge base |
| **Input** | Query string + collection name + optional filters |
| **Output** | `list[str]` — retrieved document text |
| **Tools** | ChromaDB PersistentClient + DefaultEmbeddingFunction (local) |
| **Functions** | `query_car_specs(make, model)` · `query_market_data(make, model, location)` · `query_dealer_data(city, state)` · `query_market_trends(make, location)` |
| **Design** | Lazy singleton client — one ChromaDB connection shared across all agents per session |

---

## SECTION 20 — Evaluation Framework *(new in v2.0)*

### Evaluation Methods Applied

| Method | Implementation | Where |
|---|---|---|
| **Rule-based** | Critic dimension checks: price/mileage compliance, match score counts, source trust | `critic_agent.py` + `test_pipeline_eval.py` |
| **LLM-as-Judge** | GPT-4o-mini scores outreach personalization 1–5; DeepEval AnswerRelevancy + Hallucination metrics | `critic_agent.py` + `test_pipeline_eval.py` |
| **Execution-based** | Marketcheck success/fallback tracking; email/SMS delivery success dict; revision count | `orchestrator.py` + `app.py` |
| Reference-based | Not implemented (no golden dataset) | — |
| Human / HITL | Not implemented (planned) | — |

### DeepEval Test Suite — `tests/test_pipeline_eval.py`

**Rule-based tests (no LLM — runs instantly):**
- `TestCriticResultRelevance` — listings must satisfy price_min/max and max_mileage
- `TestCriticResultQuality` — at least 3 listings must score ≥60
- `TestCriticDataSourceTrust` — all-simulated → Amber flag (score=12, not 0)
- `TestCriticBadges` — end-to-end badge and revision logic

**LLM-as-Judge tests (requires OpenAI key):**
- `test_outreach_answer_relevancy` — email relevance to search query (threshold 0.5)
- `test_outreach_no_hallucination` — email must not fabricate listing details (threshold 0.5)
- `test_generic_email_lower_relevancy` — generic email scores above floor threshold of 0.3

### Guardrails & Safety

| Guardrail | Status |
|---|---|
| Input validation | ✅ app.py validates required fields; Pydantic rejects wrong types |
| Schema compliance | ✅ Pydantic at every agent handoff; partial gap on raw GPT JSON parse |
| Hallucination detection | ✅ DeepEval HallucinationMetric in test suite; RAG grounding in production |
| Scope creep | N/A (no BRD source document in this pipeline) |
| Confidentiality / PII | ⚠️ User email/phone appear in LangSmith traces — known gap, planned fix |
| Cross-agent consistency | ✅ Critic enforces listing-to-preference consistency across agents |

---

## SECTION 21 — Curriculum Concepts Applied *(new in v2.0)*

This section maps capstone AI curriculum concepts to their implementation in AUTO AI.

| Concept | Status | Implementation |
|---|---|---|
| Multi-agent orchestration | ✅ | Sequential pipeline: Search → Rank → Critic → Outreach → Critic |
| LLM-as-Judge | ✅ | `_check_outreach_personalization` in critic_agent.py; DeepEval metrics |
| Critic / Revision Loop | ✅ | orchestrator.py — up to 2 search cycles + 1 outreach retry |
| Quality badges (Green/Amber/Red) | ✅ | app.py — colored banner with per-dimension expander |
| Tool use | ✅ | Each agent is a discrete callable with typed inputs/outputs |
| RAG pipeline | ✅ | rag_agent.py querying ChromaDB; grounding search + outreach |
| Chunking & Embeddings | ✅ | build_index.py — 4 collections, one doc per model/region/dealer |
| Vector DB | ✅ | ChromaDB PersistentClient with cosine similarity |
| Pydantic structured output | ✅ | CarPreferences, CarListing, CriticResult, DimensionResult |
| Prompt engineering | ✅ | Module-level ChatPromptTemplate; dynamic prompts with critic feedback |
| Observability / Tracing | ✅ | LangSmith @traceable on run_pipeline |
| Evaluation framework | ✅ | DeepEval 0.21.78 — rule-based + LLM metric tests |
| Execution-based evaluation | ✅ Partial | Tool success tracking; fallback/revision count surfaced in UI |
| Reference-based evaluation | ❌ | Not implemented — no golden dataset |
| Human-in-the-loop (HITL) | ❌ | Not implemented — planned |
| MCP architecture | ❌ | Not implemented — planned for v3.0 |
| Voice interface (ASR/TTS) | ❌ | Not implemented — planned for v3.0 |
| Structured output parsing | ⚠️ Partial | Pydantic at handoffs; raw json.loads() on GPT output (planned upgrade) |

---

---

## SECTION 22 — Business Rules & Design Decisions

This section documents the non-obvious business logic decisions that govern how the app behaves in production. These rules exist because of real-world data quality issues discovered during professional use.

---

### 22.1 — VIN vs. Stock Number: What They Are and When to Use Each

| | VIN | Stock Number |
|---|---|---|
| **Full name** | Vehicle Identification Number | Dealer stock / inventory number |
| **Length** | Always 17 characters | Variable (e.g. P12345, U8823) |
| **Assigned by** | Manufacturer, at factory | Individual dealership, on arrival |
| **Unique scope** | Globally unique — one car, ever | Only unique within one dealership |
| **Changes?** | Never | Yes — if car moves to another dealer |
| **Useful for** | CarFax, recall checks, any marketplace search, title/registration, insurance | Calling or emailing that specific dealer |
| **Searchable on AutoTrader/Cars.com/CarGurus?** | Yes — returns exact car | No — returns random unrelated results |

**Key rule:** Never use a stock number to search on external marketplace sites. It will find the wrong car. Stock numbers are only meaningful in a conversation with the specific dealer that issued them.

---

### 22.2 — Clipboard Copy Strategy

When a user clicks any external link (AutoTrader, Cars.com, CarGurus, Dealer Site) on a listing card, the app automatically copies the best available identifier to the clipboard. The user can then paste it into any search box or share it.

**Priority order:**

| Priority | Condition | What is copied | Best used for |
|---|---|---|---|
| 1 | VIN available | VIN only (e.g. `1HGBH41JXMN109186`) | Any marketplace, Google, CarFax |
| 2 | No VIN, stock# and/or dealer available | `{title} {stock#} {dealer_name}` (e.g. `2024 BMW X5 sDrive40i P12345 BMW of Culver City`) | Google search → finds exact VDP on dealer site or aggregator |
| 3 | No VIN, no stock#, no dealer | Title only (e.g. `2024 BMW X5 sDrive40i`) | General marketplace search |

**Why not copy stock number alone?** Pasting a bare stock number (e.g. `P12345`) into Google or any marketplace returns random unrelated results. It only makes sense in the context of the dealer's name — hence the combined string.

**Why not copy stock number to clipboard for external search?** Confirmed in production testing: stock numbers match completely different vehicles on external sites. The combination of title + stock# + dealer is optimized for Google to surface that dealer's own VDP page.

---

### 22.3 — New Car Search: Craigslist Excluded

When a user searches with `condition = "New"`, Craigslist results are excluded entirely from the pipeline.

**Reason:** Craigslist is a private-seller classifieds platform. New cars from authorized dealers are not listed there. Including Craigslist results in a "New" search would surface used private-party listings that are not remotely relevant.

**Secondary reason:** Craigslist never reports mileage in search results (stored as `mileage=0`). A used car with unknown mileage stored as 0 would be scored at 30/30 mileage points, giving it an artificially inflated match score (observed as 99% match for a clearly used car in production).

---

### 22.4 — Mileage = 0 from Scraped Sources Means "Unknown"

Craigslist, CarGurus, and eBay Motors do not include mileage in their search result pages (it appears only on the individual listing detail page, which the app does not load during search).

The app stores `mileage=0` for these listings. In the ranking agent, `mileage=0` from a scraped source is treated as **unknown** and receives **15/30 mileage points** (neutral, half credit). It is not treated as "0 miles driven" (which would give full 30/30 points).

**Sources affected:** CarGurus, Craigslist, eBay Motors  
**Sources not affected:** auto.dev, Marketcheck — both return actual mileage from structured APIs

---

### 22.5 — No AI-Simulated Data in Production

The app never generates fake car listings. There is no GPT fallback that invents listings when real data is unavailable. This was removed in v2.1 before the app was deployed for professional office use.

**What happens when no listings are found:**
- No valid API keys configured → error: *"No API key configured. Add AUTODEV_API_KEY or MARKETCHECK_API_KEY to .env."*
- API keys valid but no matching inventory found → warning: *"No listings found. Try widening your price range, increasing the radius, or relaxing filters."*

**No orange "AI Simulated" badge will ever appear.** All results shown are real dealer listings from live inventory.

---

### 22.6 — New Cars Are Listed on AutoTrader, Cars.com, and CarGurus

Franchise dealers (BMW, Toyota, Honda, etc.) pay to list their full new inventory on AutoTrader, Cars.com, and CarGurus as a core part of their marketing. New car inventory is often *more* complete on these platforms than used.

**Coverage:** 95%+ of new dealer inventory for mainstream brands in any major metro area is listed on at least one of these three platforms.

**Lag:** A car that just arrived on the lot may take 24–48 hours to appear on aggregators; it will appear on the dealer's own website first.

**Implication for this app:** The AutoTrader/Cars.com/CarGurus search links generated on each card (pre-filtered by make, model, condition, color, price, ZIP) are valid and useful for new car searches. The auto.dev and Marketcheck API sources also include new dealer inventory directly.

---

### 22.7 — External Search Link Generation

Each listing card includes three pre-filtered search links that open in a new browser tab. These are not links to specific listings — they are marketplace search pages pre-filtered to show cars matching the buyer's criteria.

**AutoTrader URL format:**
```
https://www.autotrader.com/cars-for-sale/{condition}/{color}/{make}/{model}?zip=...&startPrice=...&endPrice=...&maxMileage=...
```

**Cars.com URL format:**
```
https://www.cars.com/shopping/results/?stock_type={condition}&makes[]={make}&models[]={make}-{model}&exterior_color_slugs[]={color}&zip=...&maximum_distance=...&list_price_max=...&maximum_mileage=...
```

**CarGurus URL format:**
```
https://www.cargurus.com/search?zip=...&distance=...&minPrice=...&maxPrice=...&maxMileage=...&listingTypes=...&exteriorColor=...&sortType=PRICE&sortDirection=ASC
```

CarGurus does not support make/model as URL parameters in their public search endpoint — results are filtered by the buyer's location and price/mileage/condition/color parameters only.

---

### 22.8 — Live Check (auto.dev VIN Lookup)

For auto.dev listings that have a VIN, a "Live Check" button appears on the card. Clicking it makes a real-time API call to `auto.dev/api/listings/{vin}` and surfaces:

- Current asking price and price history
- Dealer phone number
- Dealer website link (or Google search fallback)
- Recent price drops
- Vehicle features (up to 15)

**ClickOff dealers:** Some dealers have opted out of direct contact through auto.dev's platform. For these, the Live Check will display: *"This dealer has opted out of direct contact — visit the dealership in person or call their main line."*

---

*AUTO AI BRD v2.1 — Confidential — Neeraj Nagpal — May 7, 2026*
