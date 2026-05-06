import os
from pathlib import Path
from dotenv import load_dotenv

# Always load from THIS project's .env with override so stale env vars
# from other projects or previous processes never bleed in.
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# Disable LangSmith tracing to prevent 403 noise
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

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
