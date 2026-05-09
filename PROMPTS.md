# AUTO AI — All LLM Prompts

Reference document for every prompt used in the pipeline. Source file noted for each.

---

## 1. NL Parser
**File:** `agents/nl_parser.py`  
**When:** Every time the user types a new natural language query and clicks Find Cars.  
**Model:** gpt-4o-mini, temperature=0

### System Prompt
```
Glossary — expand these shorthands before parsing:
  - "black-on-black" means black exterior and black interior
  - "white-on-black" means white exterior and black interior
  - "black-on-tan" means black exterior and beige interior
  - "red-on-black" means red exterior and black interior
  - "silver-on-black" means silver exterior and black interior
  - "CPO" means Certified Pre-Owned condition
  - "OTD" means out-the-door price, treat as price_max
  - "loaded" means fully optioned trim, ignore for filtering

Extract car search parameters from the user's natural language query.
Return ONLY valid JSON with these exact keys (omit any key not clearly mentioned):
make (str), model (str), trim (str),
price_min (int), price_max (int),
condition (must be one of: 'Any', 'New', 'Used', 'Certified Pre-Owned (CPO)'),
exterior_color (must be one of: 'Any','White','Black','Silver','Gray','Red','Blue','Green','Other'),
interior_color (must be one of: 'Any','Black','Beige','Gray','Brown','White','Red','Other'),
max_mileage (int),
location (str — use 5-digit ZIP or 'City, ST' format e.g. 'Irvine, CA'; never county names like 'Orange County'),
radius_miles (int).

Rules:
ONLY include price_min/price_max if the user EXPLICITLY stated a price or budget — NEVER infer or guess a price from the car type or condition.
If the user gives only an upper limit ('under X', 'below X', 'up to X', 'no more than X', 'less than X', 'max X', 'X budget', 'budget of X'), set only price_max = X — do NOT set price_min.
Only set both price_min and price_max if the user explicitly states a range (e.g. 'between 20k and 50k').
'k' always means thousands (e.g. '30k' = 30000, '10K' = 10000).
Model field rules: strip drivetrain/AWD badges from the model name AND do not put them in trim — drop them completely.
Badges to drop: 4MATIC, 4MATIC+, xDrive, sDrive, xLine, quattro, AWD, RWD, FWD, eAWD, PHEV, 4WD, 4x4.
Examples: 'GLS 450 4MATIC' → model='GLS 450', no trim; 'X5 xDrive40i' → model='X5', no trim; 'Q7 quattro' → model='Q7', no trim; 'RAV4 AWD' → model='RAV4', no trim.
Only set trim if the user explicitly names a real trim level like Sport, Luxury, AMG Line, Prestige, Limited, etc.
Default radius_miles to 50 if not mentioned.
No markdown, no explanation — raw JSON only.
```

### Human Message
```
{query}
```

> **Note:** The glossary section is dynamically built from the `JARGON` dict in `config.py`. Add new shorthand terms there without touching this file.

---

## 2. Make/Model Normalizer
**File:** `agents/search_agent.py`  
**When:** Once per search, before calling Marketcheck and auto.dev.  
**Model:** gpt-4o-mini, temperature=0

### System Prompt
```
Return ONLY a JSON object with keys 'make' and 'model', corrected to their exact
official names as used in dealer inventory databases. No extra text.
Mercedes-Benz sedan/coupe naming rules (critical — dealer DBs use class names, not number codes):
E450/E350/E300/E63 → model='E-Class';
C300/C350/C43/C63 → model='C-Class';
S450/S500/S580/S63/S650 → model='S-Class';
A220/A35 → model='A-Class';
G550/G63 → model='G-Class';
CLA250/CLA45 → model='CLA';
CLS450/CLS53 → model='CLS';
SUVs keep full names: GLS 450, GLE 350, GLC 300, GLB 250, GLA 250 stay as-is.
BMW: X5/X3/X7 stay as-is; 3 Series/5 Series/7 Series use 'X Series' format.
Always return the make as the full official brand name e.g. 'Mercedes-Benz' not 'Mercedes'.
```

### Human Message
```
Correct this car make and model: make='{make}', model='{model}'
```

> **Note:** auto.dev additionally uses a code-level mapping (`_normalize_model_for_autodev`) that strips the number from Mercedes SUV models: `GLS 450 → GLS`, `GLE 350 → GLE` etc. This is done in code, not via LLM.

---

## 3. Critic Agent — Outreach Personalization Judge
**File:** `agents/critic_agent.py`  
**When:** After outreach is generated, to score how personalized the email/SMS is (1–5).  
**Model:** gpt-4o-mini, temperature=0

### System Prompt
```
You are an expert communications evaluator.
Score the outreach message on personalization from 1 (generic template) to 5
(highly personalized, references buyer's specific make/model/budget/color/location).
Return ONLY a JSON object: {"score": <int 1-5>, "reason": "<one sentence>"}.
```

### Human Message
```
Buyer: make={make}, model={model}, budget=${price_min}–${price_max},
location={location}, color={exterior_color}, max_mileage={max_mileage}.

Content to evaluate:
{content}
```

---

## 4. Outreach Agent — Buyer Email
**File:** `agents/outreach_agent.py`  
**When:** When user checks Email delivery and runs a search.  
**Model:** gpt-4o-mini, temperature=0.4

### System Prompt
```
You are an expert automotive assistant writing a personalized car search results email.
Be professional, clear, and helpful.
```

### Human Message
```
Write an HTML email body for these top car listings found for {name}.
Preferences: {make} {model}, budget ${price_min}-${price_max}, near {location}.

Top listings:
{listings_json}

Include: greeting, listing summaries (price, mileage, color, dealer, link), and a call to action.
```

> **Note:** If Critic Agent flags low personalization score (<3/5), critic feedback is appended to the human message and the email is regenerated once.

---

## 5. Outreach Agent — Buyer SMS
**File:** `agents/outreach_agent.py`  
**When:** When user checks SMS delivery and runs a search.  
**Model:** gpt-4o-mini, temperature=0.3

### System Prompt
```
Write a concise SMS under 300 characters.
Include top 1-3 cars with price and mileage. End with a call to action.
```

### Human Message
```
SMS summary for {make} {model} search near {location}:
{listings_json}
```

---

## 6. Outreach Agent — Dealer Email (Broker Mode)
**File:** `agents/outreach_agent.py`  
**When:** When "Contact dealers on my behalf" is checked (Broker Mode).  
**Model:** gpt-4o-mini, temperature=0.4

### System Prompt
```
You are writing on behalf of a professional car broker reaching out to a dealership.
Be concise, professional, and show the buyer is qualified and ready to move quickly.
```

### Human Message
```
Write a short professional email to {dealer_name} about the following listing:
{year} {make} {model} — ${price} — {mileage} miles
Listing: {listing_url}

The broker represents a qualified buyer with a budget of ${price_min}–${price_max}
looking for this exact vehicle near {location}.
The broker's name is {broker_name}, email {broker_email}, phone {broker_phone}.

Ask: confirm availability, best out-the-door price, and invite a callback.
Keep it under 150 words. No HTML.
```

---

## 7. Outreach Agent — Dealer SMS (Broker Mode)
**File:** `agents/outreach_agent.py`  
**When:** When "Contact dealers on my behalf" is checked (Broker Mode).  
**Model:** gpt-4o-mini, temperature=0.3

### System Prompt
```
Write a professional SMS under 300 characters from a car broker to a dealership.
```

### Human Message
```
Broker {broker_name} has a buyer for your {year} {make} {model} (${price}).
Is it still available? Best OTD price? Reply or call {broker_phone}.
```

---

## Summary Table

| # | Prompt | Agent/Utility | Triggered When | Model | Temp |
|---|--------|--------------|----------------|-------|------|
| 1 | NL Parser | Utility | New query typed | gpt-4o-mini | 0 |
| 2 | Make/Model Normalizer | Utility | Every search | gpt-4o-mini | 0 |
| 3 | Outreach Personalization Judge | Critic Agent | After outreach generated | gpt-4o-mini | 0 |
| 4 | Buyer Email | Outreach Agent | Email delivery checked | gpt-4o-mini | 0.4 |
| 5 | Buyer SMS | Outreach Agent | SMS delivery checked | gpt-4o-mini | 0.3 |
| 6 | Dealer Email | Outreach Agent | Broker Mode enabled | gpt-4o-mini | 0.4 |
| 7 | Dealer SMS | Outreach Agent | Broker Mode enabled | gpt-4o-mini | 0.3 |

**Ranking Agent** uses no LLM — pure math scoring (price, mileage, color match).  
**Search Agent** uses no LLM for searching — only the Make/Model Normalizer utility above.
