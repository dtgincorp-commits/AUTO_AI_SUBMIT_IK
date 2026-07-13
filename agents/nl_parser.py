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
            "location (str — if the user mentions a 5-digit ZIP code (e.g. 'near 92782', 'in 90210'), return it exactly as-is (e.g. '92782'); if a city and state are given return 'City, ST' format (e.g. 'Irvine, CA'); if only a US state name or abbreviation is given (e.g. 'arizona', 'Texas', 'AZ'), return the largest city in that state with its 2-letter abbreviation (e.g. 'Phoenix, AZ', 'Houston, TX'); never county names like 'Orange County'; OMIT this key entirely if no location is mentioned — never use placeholders like 'City, ST' or 'Unknown'), "
            "radius_miles (int). "
            "Rules: "
            "ONLY include price_min/price_max if the user EXPLICITLY stated a price or budget — NEVER infer or guess a price from the car type or condition. "
            "If the user gives only an upper limit ('under X', 'below X', 'up to X', 'no more than X', 'less than X', 'max X', 'X budget', 'budget of X'), set only price_max = X — do NOT set price_min. "
            "Only set both price_min and price_max if the user explicitly states a range (e.g. 'between 20k and 50k'). "
            "'k' always means thousands (e.g. '30k' = 30000, '10K' = 10000). "
            "Model field rules: strip drivetrain/AWD badges from the model name AND do not put them in trim — drop them completely. "
            "Badges to drop: 4MATIC, 4MATIC+, xDrive, sDrive, xLine, quattro, AWD, RWD, FWD, eAWD, PHEV, 4WD, 4x4, HD, Hybrid (when it precedes a trim name — e.g. 'Hybrid TrailSport' → trim='TrailSport'; 'Hybrid' alone as a model descriptor is not a trim). "
            "Examples: 'GLS 450 4MATIC' → model='GLS 450', no trim; 'X5 xDrive40i' → model='X5', no trim; 'Q7 quattro' → model='Q7', no trim; 'RAV4 AWD' → model='RAV4', no trim; 'Sierra 2500 Denali HD' → model='Sierra 2500', trim='Denali'; 'CR-V Hybrid TrailSport' → model='CR-V', trim='TrailSport'; 'RAV4 Hybrid XSE' → model='RAV4', trim='XSE'; 'Accord Hybrid Sport' → model='Accord', trim='Sport'; 'Tucson Hybrid SEL' → model='Tucson', trim='SEL'; 'Highlander Hybrid Platinum' → model='Highlander', trim='Platinum'."
            "Mercedes-Benz model rules: always insert a space between the class letters and the number. "
            "The trailing 'e' on a Mercedes model number is a PHEV/hybrid variant designator — it is PART OF THE MODEL NAME, NOT a badge — always preserve it. "
            "Examples: 'GLE450e' → model='GLE 450e'; 'GLC300e' → model='GLC 300e'; 'GLE450' → model='GLE 450'; 'GLS580' → model='GLS 580'; 'GLE53 AMG' → model='GLE 53', trim='AMG Line'. "
            "Only set trim if the user explicitly names a real trim level like Sport, Luxury, AMG Line, Prestige, Limited, SR5, TRD, Denali, etc. "
            "Lexus/Toyota/Honda/Acura powertrain designators are valid trims — always preserve them: "
            "'TX 500h' → model='TX', trim='500h'; 'NX 350' → model='NX', trim='350'; 'RX 500h' → model='RX', trim='500h'; "
            "'NX 450h+' → model='NX', trim='450h+'; 'ES 350' → model='ES', trim='350'; 'GX 550' → model='GX', trim='550'; "
            "'Camry XSE' → model='Camry', trim='XSE'; 'RAV4 Prime' → model='RAV4', trim='Prime'. "
            "If the user mentions a model year of 2026 or later, set condition to 'New' (unless they explicitly say 'used'). "
            "Color rules: if the user mentions a single color with no qualifier, it means exterior_color. "
            "If two colors appear separated by 'or' (e.g. 'black or red', 'white or beige'), treat the FIRST as exterior_color and the SECOND as interior_color. "
            "If the user explicitly says 'exterior' or 'outside' before a color, set exterior_color; if they say 'interior', 'inside', or 'int' before a color, set interior_color. "
            "Default radius_miles to 50 if not mentioned. "
            "No markdown, no explanation — raw JSON only."
        )),
        ("human", "{query}"),
    ])


_JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are an automotive search expert. A first AI model tried to parse a car search query "
        "but the extracted make/model could not be validated. "
        "Correct the make and model based on your automotive knowledge. "
        "Return ONLY valid JSON with keys: make (str), model (str), trim (str or omit if unclear). "
        "Examples: "
        "'BMW M Sport' likely means make='BMW', model='X5' or another BMW — pick the most common model for M Sport. "
        "'Mercedes AMG' → make='Mercedes-Benz', model='GLE 53'. "
        "If you truly cannot determine the model, return the original values unchanged. "
        "No markdown, no explanation — raw JSON only."
    )),
    ("human", (
        "Original query: {query}\n"
        "First LLM extracted: make={make}, model={model}, trim={trim}\n"
        "NHTSA could not validate this make+model. Please correct it."
    )),
])


def _judge_parse(query: str, parsed: dict) -> dict:
    """LLM #2 — fires only when NHTSA cannot validate the parsed make+model."""
    try:
        llm = ChatOpenAI(model=LLM_MODEL, openai_api_key=OPENAI_API_KEY, temperature=0)
        chain = _JUDGE_PROMPT | llm | StrOutputParser()
        raw = chain.invoke({
            "query": query,
            "make":  parsed.get("make", ""),
            "model": parsed.get("model", ""),
            "trim":  parsed.get("trim", ""),
        }).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        corrected = json.loads(raw.strip())
        # Merge corrections back — only override make/model/trim
        for key in ("make", "model", "trim"):
            if corrected.get(key):
                parsed[key] = corrected[key]
    except Exception:
        pass
    return parsed


# Trace of the most recent parse_query call — raw LLM output, the NHTSA
# grounding steps, and the final parsed dict. Read by the app's debug view via
# get_last_parse_trace() to show "what the LLM chopped → how it was grounded".
_LAST_PARSE_TRACE: dict = {}


def get_last_parse_trace() -> dict:
    """Return a copy of the trace recorded by the most recent parse_query call."""
    return dict(_LAST_PARSE_TRACE)


def parse_query(query: str) -> tuple[dict, str]:
    """Returns (parsed_dict, error_message). On success error_message is empty."""
    global _LAST_PARSE_TRACE
    _trace: dict = {"raw_query": query, "llm_raw": None, "steps": [], "final": None}
    llm = ChatOpenAI(model=LLM_MODEL, openai_api_key=OPENAI_API_KEY, temperature=0)
    chain = _build_prompt() | llm | StrOutputParser()
    try:
        _cb = get_langfuse_callbacks()
        raw = chain.invoke({"query": query}, config={"callbacks": _cb} if _cb else {}).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(raw.strip())
        _trace["llm_raw"] = dict(parsed)   # exactly what the LLM extracted, pre-grounding

        # Canonicalize make+model against NHTSA (keep the user's granularity —
        # do NOT peel a trailing number here: "GX 550" is a real Lexus model,
        # while "AMG GT 63" is model+trim. They're structurally identical, so the
        # split can't be decided at parse time — the sources handle it via a
        # fallback-on-zero query instead).
        if parsed.get("make") and parsed.get("model"):
            try:
                from agents.nhtsa import canonicalize_model, model_exists
                _pre = parsed["model"]
                canonical = canonicalize_model(parsed["make"], parsed["model"])
                parsed["model"] = canonical
                _trace["steps"].append(
                    f"NHTSA canonicalize: {parsed['make']} {_pre!r} → {canonical!r}"
                    + ("" if _pre == canonical else " (rewritten to catalog name)"))
                # If NHTSA still can't validate → fire LLM #2 judge
                if not model_exists(parsed["make"], canonical):
                    _trace["steps"].append(
                        f"NHTSA could NOT validate {parsed['make']} {canonical!r} → firing LLM judge (#2)")
                    parsed = _judge_parse(query, parsed)
                    _pre2 = parsed.get("model", "")
                    parsed["model"] = canonicalize_model(parsed["make"], parsed.get("model", ""))
                    _trace["steps"].append(
                        f"LLM judge returned: {parsed.get('make')} {_pre2!r} → canonical {parsed['model']!r}")
                else:
                    _trace["steps"].append(f"NHTSA validated {parsed['make']} {canonical!r} — no judge needed")
            except Exception as _e:
                _trace["steps"].append(f"grounding error: {_e}")

        # Final pass: strip a duplicated make prefix from the model. Brands whose
        # models are named after the brand (Polestar 2/3/4) end up as model
        # "Polestar 2" — via the LLM or the judge — but listing APIs store just
        # "2", so leaving it duplicated returns 0 results. Done last so it also
        # catches judge output.
        _mk = (parsed.get("make") or "").strip()
        _md = (parsed.get("model") or "").strip()
        if _mk and _md and _md.lower().startswith(_mk.lower() + " "):
            parsed["model"] = _md[len(_mk):].strip()
            _trace["steps"].append(f"stripped duplicated make prefix: {_md!r} → {parsed['model']!r}")

        _trace["final"] = dict(parsed)
        _LAST_PARSE_TRACE = _trace
        return parsed, ""
    except Exception as e:
        _trace["steps"].append(f"parse error: {e}")
        _LAST_PARSE_TRACE = _trace
        return {}, str(e)
