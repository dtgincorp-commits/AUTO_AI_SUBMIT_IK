import os
from pathlib import Path
from dotenv import load_dotenv

# Always load from THIS project's .env with override so stale env vars
# from other projects or previous processes never bleed in.
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "AUTO_AI"

def _get(key: str) -> str:
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, "")
    except Exception:
        return ""

OPENAI_API_KEY = _get("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = _get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = _get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = _get("TWILIO_PHONE_NUMBER")
SENDGRID_API_KEY = _get("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = _get("SENDGRID_FROM_EMAIL")
MARKETCHECK_API_KEY = _get("MARKETCHECK_API_KEY")
AUTODEV_API_KEY = _get("AUTODEV_API_KEY")
EBAY_APP_ID = _get("EBAY_APP_ID")
SCRAPERAPI_KEY = _get("SCRAPERAPI_KEY")

LLM_MODEL = "gpt-4o-mini"
MAX_RESULTS = 500
MAX_REVISION_CYCLES = 2

# ── Search jargon glossary ──────────────────────────────────────────────────
# Add shorthand terms here — the NL parser expands them before extracting
# search parameters. No code changes needed, just add a new entry below.
JARGON = {
    "black-on-black":  "black exterior and black interior",
    "white-on-black":  "white exterior and black interior",
    "black-on-tan":    "black exterior and beige interior",
    "red-on-black":    "red exterior and black interior",
    "silver-on-black": "silver exterior and black interior",
    "CPO":             "Certified Pre-Owned condition",
    "OTD":             "out-the-door price, treat as price_max",
    "loaded":          "fully optioned trim, ignore for filtering",
}

