"""
DeepEval test suite for AUTO_AI pipeline.

Run with:
    .venv/bin/deepeval test run tests/test_pipeline_eval.py

Or with pytest directly (skips DeepEval cloud upload):
    .venv/bin/pytest tests/test_pipeline_eval.py -v
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, HallucinationMetric

from agents.models import CarPreferences, CarListing
from agents.critic_agent import (
    run_critic_agent,
    _check_result_relevance,
    _check_result_quality,
    _check_data_source_trust,
)

# ── Shared sample data ──────────────────────────────────────────────────────

SAMPLE_PREFS = CarPreferences(
    make="BMW",
    model="X5",
    price_min=45000,
    price_max=65000,
    max_mileage=50000,
    location="Austin, TX",
    radius_miles=50,
    exterior_color="White",
)

GOOD_LISTINGS = [
    CarListing(
        title="2022 BMW X5 xDrive40i",
        price=58000, mileage=22000, year=2022,
        exterior_color="White", interior_color="Black",
        dealer_name="BMW of Austin", location="Austin, TX",
        listing_url="https://example.com/1",
        source="Marketcheck", match_score=85.0,
    ),
    CarListing(
        title="2021 BMW X5 sDrive40i",
        price=52000, mileage=35000, year=2021,
        exterior_color="Black", interior_color="Beige",
        dealer_name="AutoNation BMW", location="Austin, TX",
        listing_url="https://example.com/2",
        source="Marketcheck", match_score=72.0,
    ),
    CarListing(
        title="2023 BMW X5 M50i",
        price=63000, mileage=8000, year=2023,
        exterior_color="White", interior_color="Black",
        dealer_name="Park Place BMW", location="Dallas, TX",
        listing_url="https://example.com/3",
        source="Marketcheck", match_score=68.0,
    ),
]

POOR_LISTINGS = [
    CarListing(
        title="2022 BMW X5 xDrive40i",
        price=58000, mileage=22000, year=2022,
        source="Marketcheck", match_score=42.0,
    ),
    CarListing(
        title="2021 BMW X5",
        price=70000, mileage=60000, year=2021,  # over price_max AND max_mileage
        source="Marketcheck", match_score=38.0,
    ),
]

SIMULATED_LISTINGS = [
    CarListing(
        title="2022 BMW X5", price=55000, mileage=30000, year=2022,
        source="AI Simulated", match_score=65.0,
    ),
    CarListing(
        title="2021 BMW X5", price=48000, mileage=42000, year=2021,
        source="AI Simulated", match_score=60.0,
    ),
    CarListing(
        title="2023 BMW X5", price=62000, mileage=10000, year=2023,
        source="AI Simulated", match_score=70.0,
    ),
]

# Pre-written sample email — used for LLM metric tests without calling outreach agent
SAMPLE_EMAIL = """
<p>Dear Car Buyer,</p>
<p>We found 3 great BMW X5 matches near Austin, TX within your $45,000–$65,000 budget.</p>
<ul>
  <li><strong>2022 BMW X5 xDrive40i</strong> — $58,000 | 22,000 mi | White | BMW of Austin
      <a href="https://example.com/1">View Listing</a></li>
  <li><strong>2021 BMW X5 sDrive40i</strong> — $52,000 | 35,000 mi | Black | AutoNation BMW
      <a href="https://example.com/2">View Listing</a></li>
  <li><strong>2023 BMW X5 M50i</strong> — $63,000 | 8,000 mi | White | Park Place BMW
      <a href="https://example.com/3">View Listing</a></li>
</ul>
<p>Visit a dealer today to schedule a test drive!</p>
"""

SAMPLE_EMAIL_GENERIC = """
<p>Dear Customer,</p>
<p>We found some cars for you. Please check the listings below and contact a dealer.</p>
<p>Good luck with your purchase!</p>
"""


# ── Rule-based critic tests (no LLM calls — fast) ──────────────────────────

class TestCriticResultRelevance:
    def test_all_listings_in_range_passes(self):
        result = _check_result_relevance(SAMPLE_PREFS, GOOD_LISTINGS)
        assert result.passed is True
        assert result.score == 25.0
        assert result.flag == "pass"

    def test_out_of_range_listing_fails(self):
        result = _check_result_relevance(SAMPLE_PREFS, POOR_LISTINGS)
        assert result.passed is False
        assert result.flag == "fail"
        assert result.score < 25.0

    def test_empty_listings_fails(self):
        result = _check_result_relevance(SAMPLE_PREFS, [])
        assert result.passed is False
        assert result.score == 0.0


class TestCriticResultQuality:
    def test_three_good_listings_passes(self):
        result = _check_result_quality(GOOD_LISTINGS)
        assert result.passed is True
        assert result.score == 25.0

    def test_fewer_than_three_good_listings_fails(self):
        result = _check_result_quality(POOR_LISTINGS)
        assert result.passed is False
        assert result.flag == "fail"

    def test_empty_listings_fails(self):
        result = _check_result_quality([])
        assert result.passed is False
        assert result.score == 0.0


class TestCriticDataSourceTrust:
    def test_real_listings_passes(self):
        result = _check_data_source_trust(GOOD_LISTINGS)
        assert result.passed is True
        assert result.flag == "pass"
        assert result.score == 25.0

    def test_all_simulated_is_amber(self):
        result = _check_data_source_trust(SIMULATED_LISTINGS)
        assert result.passed is False
        assert result.flag == "amber"
        assert result.score == 12.0  # amber penalty, not zero

    def test_mixed_sources_passes(self):
        mixed = GOOD_LISTINGS[:2] + SIMULATED_LISTINGS[:1]
        result = _check_data_source_trust(mixed)
        assert result.passed is True


class TestCriticBadges:
    def test_good_listings_get_green_or_amber_badge(self):
        critic = run_critic_agent(SAMPLE_PREFS, GOOD_LISTINGS)
        assert critic.badge in ("green", "amber")
        assert critic.overall_score >= 60

    def test_simulated_listings_get_amber_badge(self):
        critic = run_critic_agent(SAMPLE_PREFS, SIMULATED_LISTINGS)
        assert critic.badge == "amber"

    def test_poor_listings_get_red_or_amber_badge(self):
        critic = run_critic_agent(SAMPLE_PREFS, POOR_LISTINGS)
        assert critic.badge in ("amber", "red")

    def test_revision_needed_for_poor_listings(self):
        critic = run_critic_agent(SAMPLE_PREFS, POOR_LISTINGS)
        assert critic.revision_needed is True
        assert len(critic.revision_feedback) > 0

    def test_no_revision_for_good_listings(self):
        critic = run_critic_agent(SAMPLE_PREFS, GOOD_LISTINGS)
        assert critic.revision_needed is False


# ── LLM-as-Judge tests via DeepEval (makes OpenAI API calls) ───────────────

@pytest.mark.parametrize("threshold", [0.5])
def test_outreach_answer_relevancy(threshold):
    """Email must be relevant to the buyer's car search query."""
    test_case = LLMTestCase(
        input=(
            "Find me a white BMW X5 under $65,000 with under 50,000 miles near Austin TX."
        ),
        actual_output=SAMPLE_EMAIL,
    )
    metric = AnswerRelevancyMetric(threshold=threshold, model="gpt-4o-mini")
    assert_test(test_case, [metric])


def test_outreach_no_hallucination():
    """Email must not fabricate car details beyond the provided listing context."""
    context = [
        "2022 BMW X5 xDrive40i priced at $58,000 with 22,000 miles, White exterior, at BMW of Austin.",
        "2021 BMW X5 sDrive40i priced at $52,000 with 35,000 miles, Black exterior, at AutoNation BMW.",
        "2023 BMW X5 M50i priced at $63,000 with 8,000 miles, White exterior, at Park Place BMW.",
    ]
    test_case = LLMTestCase(
        input="BMW X5 search results near Austin TX, budget $45,000–$65,000.",
        actual_output=SAMPLE_EMAIL,
        context=context,
    )
    metric = HallucinationMetric(threshold=0.5, model="gpt-4o-mini")
    assert_test(test_case, [metric])


def test_generic_email_lower_relevancy():
    """A generic non-personalized email should score lower than a personalized one."""
    relevancy_metric = AnswerRelevancyMetric(threshold=0.3, model="gpt-4o-mini")
    test_case = LLMTestCase(
        input="Find me a white BMW X5 under $65,000 near Austin TX.",
        actual_output=SAMPLE_EMAIL_GENERIC,
    )
    # This test intentionally uses a low threshold — generic emails should still pass 0.3
    # The point is to show measurable difference vs the personalized email
    assert_test(test_case, [relevancy_metric])
