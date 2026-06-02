# AUTO_AI Development Rules

## Before ANY code change

1. **Identify blast radius** — does this change touch `search_agent.py`, `ranking_agent.py`, `url_helpers.py`, or `app.py`? If yes, run sanity checks BEFORE and AFTER.
2. **Test the API before assuming it works** — if adding a new parameter to an API call, run a live test first to confirm the API accepts it.
3. **Never touch working code without a regression check** — if Honda CR-V is working, prove it still works after your change.

## Sanity checks — run before merging any change

```bash
.venv/bin/python test_at_trim_urls.py        # 33/33 must pass
.venv/bin/python scripts/regression_check.py  # live API checks
```

## Live API regression checks (scripts/regression_check.py)

These 3 searches must return >0 results from auto.dev after any change to search_agent.py or ranking_agent.py:

| Search | Expected |
|---|---|
| Honda CR-V, 92782 | >100 results |
| Toyota RAV4, 92782 | >100 results |
| BMW X5, 92782 | >100 results |

## Rules for search_agent.py

- **Do NOT pass `trim` to auto.dev** — returns HTTP 400 (confirmed 2026-06-01)
- **Do NOT pass `trim` to Marketcheck** — key unreliable, and trim naming differs from user input
- Trim filtering is handled by the **ranking agent** via title match, not by the search APIs

## Rules for ranking_agent.py

- Total score = 100pts: model+trim (50), price (20), mileage (15), ext color (10), int color (5)
- `make_pts` does not exist — was removed. Do not re-add it.
- `l_title` must be defined before model match block

## Rules for url_helpers.py

- AT path slug for Ford F-series: `f150`, `f250`, `f350` (no hyphens)
- AT trims for Lexus go in path slug: `tx-500h`, `rx-500h`
- AT trims for Porsche go as path segment: `/cayenne/s/`, `/macan/gts/`
- Do NOT add new makes to `_AT_PATH_ROUTED_STRIP_CODES` without testing the URL redirects

## Production warning

**main branch is live with real users. Never push breaking changes to main without testing locally first on port 8502.**

All feature work happens on `port_8502` branch. Merge to main only when confirmed working.
