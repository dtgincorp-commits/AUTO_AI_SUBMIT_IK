import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import LLM_MODEL, OPENAI_API_KEY, JARGON, get_langfuse_callbacks

def _build_prompt() -> ChatPromptTemplate:
    glossary_section = ""
    if JARGON:
        lines = "\n".join(f'  - "{k}" means {v}' for k, v in JARGON.items())
        glossary_section = (
            "Glossary — expand these shorthands before parsing:\n"
            + lines + "\n"
        )
    return ChatPromptTemplate.from_messages([
        ("system", (
            glossary_section +
            "Extract car search parameters from the user's natural language query. "
            "Return ONLY valid JSON with these exact keys (omit any key not clearly mentioned): "
            "make (str), model (str), trim (str), "
            "price_min (int), price_max (int), "
            "condition (must be one of: 'Any', 'New', 'Used', 'Certified Pre-Owned (CPO)'), "
            "exterior_color (must be one of: 'Any','White','Black','Silver','Gray','Red','Blue','Green','Other'), "
            "interior_color (must be one of: 'Any','Black','Beige','Gray','Brown','White','Red','Other'), "
            "max_mileage (int), "
            "location (str — use 5-digit ZIP or 'City, ST' format e.g. 'Irvine, CA'; if only a US state name is given (e.g. 'arizona', 'Texas', 'AZ'), return the largest city in that state with its 2-letter abbreviation (e.g. 'Phoenix, AZ', 'Houston, TX'); never county names like 'Orange County'; OMIT this key entirely if no location is mentioned — never use placeholders like 'City, ST' or 'Unknown'), "
            "radius_miles (int). "
            "Rules: "
            "ONLY include price_min/price_max if the user EXPLICITLY stated a price or budget — NEVER infer or guess a price from the car type or condition. "
            "If the user gives only an upper limit ('under X', 'below X', 'up to X', 'no more than X', 'less than X', 'max X', 'X budget', 'budget of X'), set only price_max = X — do NOT set price_min. "
            "Only set both price_min and price_max if the user explicitly states a range (e.g. 'between 20k and 50k'). "
            "'k' always means thousands (e.g. '30k' = 30000, '10K' = 10000). "
            "Model field rules: strip drivetrain/AWD badges from the model name AND do not put them in trim — drop them completely. "
            "Badges to drop: 4MATIC, 4MATIC+, xDrive, sDrive, xLine, quattro, AWD, RWD, FWD, eAWD, PHEV, 4WD, 4x4. "
            "Examples: 'GLS 450 4MATIC' → model='GLS 450', no trim; 'X5 xDrive40i' → model='X5', no trim; 'Q7 quattro' → model='Q7', no trim; 'RAV4 AWD' → model='RAV4', no trim. "
            "Only set trim if the user explicitly names a real trim level like Sport, Luxury, AMG Line, Prestige, Limited, SR5, TRD, etc. "
            "If the user mentions a model year of 2026 or later, set condition to 'New' (unless they explicitly say 'used'). "
            "Default radius_miles to 50 if not mentioned. "
            "No markdown, no explanation — raw JSON only."
        )),
        ("human", "{query}"),
    ])


def parse_query(query: str) -> tuple[dict, str]:
    """Returns (parsed_dict, error_message). On success error_message is empty."""
    llm = ChatOpenAI(model=LLM_MODEL, openai_api_key=OPENAI_API_KEY, temperature=0)
    chain = _build_prompt() | llm | StrOutputParser()
    try:
        _cb = get_langfuse_callbacks()
        raw = chain.invoke({"query": query}, config={"callbacks": _cb} if _cb else {}).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw.strip()), ""
    except Exception as e:
        return {}, str(e)
