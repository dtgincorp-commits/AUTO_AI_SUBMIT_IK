import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import LLM_MODEL, OPENAI_API_KEY

_PARSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "Extract car search parameters from the user's natural language query. "
        "Return ONLY valid JSON with these exact keys (omit any key not clearly mentioned): "
        "make (str), model (str), trim (str), "
        "price_min (int), price_max (int), "
        "condition (must be one of: 'Any', 'New', 'Used', 'Certified Pre-Owned (CPO)'), "
        "exterior_color (must be one of: 'Any','White','Black','Silver','Gray','Red','Blue','Green','Other'), "
        "interior_color (must be one of: 'Any','Black','Beige','Gray','Brown','White','Red','Other'), "
        "max_mileage (int), "
        "location (str — use 5-digit ZIP or 'City, ST' format e.g. 'Irvine, CA'; never county names like 'Orange County'), "
        "radius_miles (int). "
        "Rules: "
        "ONLY include price_min/price_max if the user EXPLICITLY stated a price or budget — NEVER infer or guess a price from the car type or condition. "
        "If only one price is explicitly mentioned, treat it as price_max and set price_min = round(price_max * 0.7, -3). "
        "Default radius_miles to 50 if not mentioned. "
        "No markdown, no explanation — raw JSON only."
    )),
    ("human", "{query}"),
])


def parse_query(query: str) -> tuple[dict, str]:
    """Returns (parsed_dict, error_message). On success error_message is empty."""
    llm = ChatOpenAI(model=LLM_MODEL, openai_api_key=OPENAI_API_KEY, temperature=0)
    chain = _PARSE_PROMPT | llm | StrOutputParser()
    try:
        raw = chain.invoke({"query": query}).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw.strip()), ""
    except Exception as e:
        return {}, str(e)
