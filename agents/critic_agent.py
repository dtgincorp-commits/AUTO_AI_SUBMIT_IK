import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.models import CarPreferences, CarListing, DimensionResult, CriticResult
from config import LLM_MODEL, OPENAI_API_KEY, get_langfuse_callbacks

_PERSONALIZATION_JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are an expert communications evaluator. "
        "Score the outreach message on personalization from 1 (generic template) to 5 (highly personalized, "
        "references buyer's specific make/model/budget/color/location). "
        'Return ONLY a JSON object: {"score": <int 1-5>, "reason": "<one sentence>"}.'
    )),
    ("human", (
        "Buyer: make={make}, model={model}, budget=${price_min}–${price_max}, "
        "location={location}, color={exterior_color}, max_mileage={max_mileage}.\n\n"
        "Content to evaluate:\n{content}"
    )),
])


def _check_result_relevance(prefs: CarPreferences, listings: list) -> DimensionResult:
    if not listings:
        return DimensionResult(
            name="result_relevance", passed=False, score=0.0, flag="fail",
            reason="No listings returned to evaluate.",
        )
    violations = 0
    for l in listings:
        if not (prefs.price_min <= l.price <= prefs.price_max):
            violations += 1
        elif prefs.max_mileage and l.mileage > prefs.max_mileage:
            violations += 1
    passed = violations == 0
    score = round(25 * (1 - violations / len(listings)), 1)
    if passed:
        reason = f"All {len(listings)} listings satisfy price and mileage constraints."
    else:
        reason = f"{violations} of {len(listings)} listings violate price or mileage constraints."
    return DimensionResult(
        name="result_relevance", passed=passed, score=score,
        flag="pass" if passed else "fail", reason=reason,
    )


def _check_result_quality(listings: list) -> DimensionResult:
    if not listings:
        return DimensionResult(
            name="result_quality", passed=False, score=0.0, flag="fail",
            reason="No listings returned to evaluate.",
        )
    count = sum(1 for l in listings if (l.match_score or 0) >= 60)
    passed = count >= 3
    score = round(min(25.0, (count / 3) * 25), 1)
    reason = f"{count} of {len(listings)} listings score ≥ 60/100."
    return DimensionResult(
        name="result_quality", passed=passed, score=score,
        flag="pass" if passed else "fail", reason=reason,
    )


def _check_data_source_trust(listings: list) -> DimensionResult:
    if not listings:
        return DimensionResult(
            name="data_source_trust", passed=False, score=0.0, flag="fail",
            reason="No listings returned.",
        )
    sources = list({l.source for l in listings if l.source})
    return DimensionResult(
        name="data_source_trust", passed=True, score=25.0, flag="pass",
        reason=f"Real inventory data from: {', '.join(sources) or 'Marketcheck'}.",
    )


def _check_outreach_personalization(prefs: CarPreferences, outreach_result: dict) -> DimensionResult:
    neutral = DimensionResult(
        name="outreach_personalization", passed=True, score=25.0, flag="pass",
        reason="Outreach not evaluated (no content or delivery failed).",
    )
    if not outreach_result or "error" in outreach_result:
        return neutral
    content = (outreach_result.get("email_content", "") or "") + "\n" + (outreach_result.get("sms_content", "") or "")
    if not content.strip():
        return neutral
    try:
        llm = ChatOpenAI(model=LLM_MODEL, openai_api_key=OPENAI_API_KEY, temperature=0)
        chain = _PERSONALIZATION_JUDGE_PROMPT | llm | StrOutputParser()
        _cb = get_langfuse_callbacks()
        raw = chain.invoke(
            {
                "make": prefs.make,
                "model": prefs.model,
                "price_min": f"{prefs.price_min:,}",
                "price_max": f"{prefs.price_max:,}",
                "location": prefs.location,
                "exterior_color": prefs.exterior_color or "Any",
                "max_mileage": prefs.max_mileage or "Any",
                "content": content[:3000],
            },
            config={"callbacks": _cb} if _cb else {},
        )
        data = json.loads(raw)
        llm_score = int(data.get("score", 3))
        llm_score = max(1, min(5, llm_score))
        llm_reason = data.get("reason", "")
    except Exception:
        llm_score = 3
        llm_reason = "Personalization check unavailable — defaulting to threshold."
    passed = llm_score >= 3
    score = round((llm_score / 5) * 25, 1)
    reason = f"Personalization score {llm_score}/5. {llm_reason}"
    return DimensionResult(
        name="outreach_personalization", passed=passed, score=score,
        flag="pass" if passed else "fail", reason=reason,
    )


def _compute_badge(overall_score: float, dimensions: dict) -> str:
    has_amber = any(d.flag == "amber" for d in dimensions.values())
    has_fail = any(d.flag == "fail" for d in dimensions.values())
    if overall_score >= 70 and not has_amber and not has_fail:
        return "green"
    if overall_score >= 40 or (has_amber and not has_fail):
        return "amber"
    return "red"


def _build_revision_feedback(dimensions: dict, prefs: CarPreferences) -> tuple:
    failing = [d for d in dimensions.values() if d.flag == "fail"]
    if not failing:
        return False, ""
    parts = []
    for d in failing:
        if d.name == "result_relevance":
            parts.append("Some listings violated hard constraints. Widen the search radius or relax filters.")
        elif d.name == "result_quality":
            parts.append(f"Fewer than 3 listings scored ≥60. Relax price range or increase search radius.")
        elif d.name == "outreach_personalization":
            parts.append(
                f"The outreach scored low on personalization. Reference the buyer's specific "
                f"{prefs.make} {prefs.model}, ${prefs.price_min:,}–${prefs.price_max:,} budget, "
                f"{prefs.exterior_color or 'any'} color, and {prefs.location} location explicitly."
            )
    return True, " ".join(parts)


def run_critic_agent(
    prefs: CarPreferences,
    listings: list,
    outreach_result: dict = None,
) -> CriticResult:
    relevance = _check_result_relevance(prefs, listings)
    quality = _check_result_quality(listings)
    trust = _check_data_source_trust(listings)

    if outreach_result is not None:
        personalization = _check_outreach_personalization(prefs, outreach_result)
    else:
        personalization = DimensionResult(
            name="outreach_personalization", passed=True, score=25.0, flag="pass",
            reason="Not yet evaluated (outreach not run).",
        )

    dims = {
        "result_relevance": relevance,
        "result_quality": quality,
        "data_source_trust": trust,
        "outreach_personalization": personalization,
    }
    overall_score = round(sum(d.score for d in dims.values()), 1)
    badge = _compute_badge(overall_score, dims)
    revision_needed, revision_feedback = _build_revision_feedback(dims, prefs)

    return CriticResult(
        overall_score=overall_score,
        badge=badge,
        dimensions=dims,
        revision_needed=revision_needed,
        revision_feedback=revision_feedback,
    )
