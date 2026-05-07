from agents.models import CarPreferences, CarListing
from agents.search_agent import run_search_agent
from agents.ranking_agent import run_ranking_agent
from agents.outreach_agent import run_outreach_agent, run_dealer_outreach
from agents.critic_agent import run_critic_agent
from config import MAX_REVISION_CYCLES
from typing import Callable
try:
    from langsmith import traceable
except ImportError:
    def traceable(**_):
        return lambda f: f


@traceable(name="AUTO_AI Pipeline", run_type="chain")
def run_pipeline(
    prefs: CarPreferences,
    on_status: Callable[[str], None] = lambda s: None,
    selected_sources: list = [],
) -> dict:
    working_prefs = prefs
    revision_count = 0
    critic_scores_per_revision = []
    search_warning = None
    ranked = []
    pre_outreach_critic = None
    source_errors: dict = {}

    # Phase 1: Search + Rank + Critic revision loop (max MAX_REVISION_CYCLES)
    for cycle in range(MAX_REVISION_CYCLES + 1):
        on_status("search")
        listings, search_warning, src_errs = run_search_agent(working_prefs, selected_sources)
        if cycle == 0:
            source_errors = src_errs

        on_status("ranking")
        ranked = run_ranking_agent(working_prefs, listings)

        on_status("critic")
        critic = run_critic_agent(working_prefs, ranked, outreach_result=None)
        critic_scores_per_revision.append(critic.overall_score)

        # No point retrying if nothing came back — source-level issue, not a filter issue
        if not listings or not critic.revision_needed or cycle == MAX_REVISION_CYCLES:
            pre_outreach_critic = critic
            break

        # Determine what to adjust
        adjustment = {}
        avg_score = (
            sum(l.match_score or 0 for l in ranked) / len(ranked) if ranked else 0
        )

        if len(ranked) < 3 and working_prefs.radius_miles < 100:
            adjustment["radius_miles"] = min(working_prefs.radius_miles + 25, 100)
        if avg_score < 50:
            adjustment["price_max"] = int(working_prefs.price_max * 1.10)
            adjustment["price_min"] = int(working_prefs.price_min * 0.90)

        if not adjustment:
            pre_outreach_critic = critic
            break

        revision_count += 1
        on_status("revision")
        working_prefs = working_prefs.model_copy(update=adjustment)

    # Phase 2: Outreach (always use original prefs — personalize around buyer intent)
    on_status("outreach")
    try:
        delivery_results = run_outreach_agent(prefs, ranked)
    except Exception as e:
        delivery_results = {"error": str(e)}

    # Phase 3: Outreach personalization critic + one retry if needed
    outreach_retry = False
    on_status("critic_outreach")
    final_critic = run_critic_agent(prefs, ranked, outreach_result=delivery_results)

    outreach_dim = final_critic.dimensions.get("outreach_personalization")
    if (
        outreach_dim
        and not outreach_dim.passed
        and "error" not in delivery_results
    ):
        outreach_retry = True
        on_status("outreach")
        try:
            delivery_results = run_outreach_agent(
                prefs, ranked, critic_feedback=final_critic.revision_feedback
            )
        except Exception as e:
            delivery_results = {"error": str(e)}
        on_status("critic_outreach")
        final_critic = run_critic_agent(prefs, ranked, outreach_result=delivery_results)

    # Phase 4: Dealer outreach (optional — broker mode)
    dealer_outreach_results = []
    if prefs.dealer_outreach and ranked:
        on_status("dealer_outreach")
        try:
            dealer_outreach_results = run_dealer_outreach(prefs, ranked)
        except Exception as e:
            dealer_outreach_results = [{"error": str(e)}]

    on_status("done")
    return {
        "listings": ranked,
        "delivery": delivery_results,
        "dealer_outreach": dealer_outreach_results,
        "search_warning": search_warning,
        "critic": final_critic,
        "revision_count": revision_count,
        "critic_scores_per_revision": critic_scores_per_revision,
        "outreach_retried": outreach_retry,
        "source_errors": source_errors,
    }
