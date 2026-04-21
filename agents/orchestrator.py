from agents.models import CarPreferences, CarListing
from agents.search_agent import run_search_agent
from agents.ranking_agent import run_ranking_agent
from agents.outreach_agent import run_outreach_agent
from typing import Callable


def run_pipeline(
    prefs: CarPreferences,
    on_status: Callable[[str], None] = lambda s: None,
) -> dict:
    on_status("search")
    listings, search_warning = run_search_agent(prefs)

    on_status("ranking")
    ranked = run_ranking_agent(prefs, listings)

    on_status("outreach")
    delivery_results = run_outreach_agent(prefs, ranked)

    on_status("done")
    return {
        "listings": ranked,
        "delivery": delivery_results,
        "search_warning": search_warning,
    }
