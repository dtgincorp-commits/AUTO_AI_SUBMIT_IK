## AUTO AI — Copilot instructions (concise)

Purpose: Give an AI coding agent the exact, discoverable context needed to be productive in this repo.

1) Big picture (what runs where)
- Frontend/UI: `app.py` — Streamlit app that collects `CarPreferences` and calls `run_pipeline`.
- Orchestration: `agents/orchestrator.py` — coordinates the 3-step pipeline: Search → Ranking → Outreach.
- Agents: `agents/search_agent.py`, `agents/ranking_agent.py`, `agents/outreach_agent.py` — each is small and single-responsibility.
- Models: `agents/models.py` — Pydantic models (`CarPreferences`, `CarListing`) are the canonical data shapes.
- Config: `config.py` — environment-driven constants (LLM model, API keys, MAX_RESULTS).

2) Typical dataflow / why files look like they do
- UI => builds a `CarPreferences` and calls `run_pipeline(prefs, on_status=...)` in `app.py`.
- `run_pipeline` calls `run_search_agent` → `run_ranking_agent` → `run_outreach_agent` and returns a dict with
  `listings`, `delivery` (email/sms results), and `search_warning`.
- Search first tries Marketcheck (`agents/search_agent._search_marketcheck`) and falls back to an LLM-generated
  JSON list (`_search_gpt_fallback`) if Marketcheck is unavailable. This fallback is surfaced via `search_warning`.

3) How to run locally (developer workflow)
- Install deps: `pip install -r requirements.txt` (see `requirements.txt`).
- Provide secrets in `.env` (project expects `OPENAI_API_KEY`, `MARKETCHECK_API_KEY`, `SENDGRID_API_KEY`, `TWILIO_*`).
- Run the UI: `streamlit run app.py` (opens at http://localhost:8501).

4) Project-specific conventions & patterns (concrete)
- Pydantic models are used for inter-agent contracts. Always accept/return `CarListing` / `CarPreferences` instances
  (see `agents/models.py`). Agents call `.model_dump()` before serializing for prompts.
- LangChain pattern used consistently: define a `ChatPromptTemplate.from_messages([...])`, create a `ChatOpenAI` LLM,
  compose with `prompt | llm | StrOutputParser()`, then call `chain.invoke(dict)` to get a string result (see
  `agents/outreach_agent.py` and `agents/search_agent.py`). Preserve that structure when adding new LLM steps.
- Scoring constants are explicit numbers in `agents/ranking_agent.py` (Price: 40, Mileage: 30, Exterior: 15,
  Interior: 15). To adjust ranking behavior, edit these values and keep the same breakdown shape returned on
  each `CarListing.score_breakdown` so the UI can show the same why card.
- Fallback behavior: if `MARKETCHECK_API_KEY` is missing or an API error occurs, `run_search_agent` returns
  GPT-simulated listings and a `search_warning`. Code that consumes search results must handle both real
  and simulated `source` values — UI uses the `source` field to color badges.

5) Integration points (exact places to modify / inspect)
- Marketcheck calls: `agents/search_agent._search_marketcheck` — builds query params and parses `listings`.
  Note: HTTP requests use `requests.get(..., timeout=15)` and client-side checks for `condition` and `certified`.
- OpenAI usage: `agents/search_agent._normalize_make_model`, `agents/search_agent._search_gpt_fallback`, and
  `agents/outreach_agent.generate_email_content` / `generate_sms_content` — all use `ChatOpenAI(model=LLM_MODEL)`.
- SendGrid email: `agents/outreach_agent.send_email` — uses `sendgrid.SendGridAPIClient` and `Mail`.
- Twilio SMS: `agents/outreach_agent.send_sms` — uses `twilio.rest.Client` and `client.messages.create`.

6) Quick editing examples (where to change common behaviors)
- Change LLM model or temperature: edit `config.py` (`LLM_MODEL`) or set a different model in a single agent.
- Increase results returned by ranking: change `MAX_RESULTS` in `config.py` and `agents/ranking_agent.py` will
  automatically respect that when slicing the sorted list.
- Tune ranking weights: edit the constants and `breakdown` construction in `agents/ranking_agent.py`.
- Add a new external enrichment (VIN/specs): `agents/search_agent._search_autodev` is a placeholder — integrate
  additional calls and append enrichment fields to `CarListing`.

7) Debugging hints (common failure modes)
- Missing API keys → `search_agent` falls back to AI simulation. Look for `search_warning` in pipeline output.
- Marketcheck request errors raise exceptions; `run_search_agent` captures and returns GPT fallback with a
  message. Use `requests` exception text to identify 401/403 vs rate-limit vs timeout.
- Outreach errors are caught and returned as `delivery` entries with `error` fields — tests should assert on
  `delivery.get('email',{}).get('success')` rather than assuming delivery always succeeds.

8) Security & housekeeping
- Sensitive data should live only in local `.env` or CI secrets. This repository currently contains a `.env`
  in the workspace; rotate any exposed keys and add `.env` to `.gitignore` if not present.

9) Files to read first (priority)
- `app.py` — UI & caller of the pipeline
- `agents/orchestrator.py` — pipeline orchestration
- `agents/search_agent.py` — normalization, Marketcheck integration, GPT fallback
- `agents/ranking_agent.py` — scoring logic and constants
- `agents/outreach_agent.py` — templates, send logic (SendGrid/Twilio)
- `agents/models.py`, `config.py`, `AUTO_AI_BRD.md` (design notes & run instructions)

If anything in these instructions is unclear or missing (for example: desired test patterns, CI commands, or
preferred LLM temperature/response validation), tell me what to expand and I will iterate.
