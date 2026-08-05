import pandas as pd
import pytest

from ask_dashboard import (
    calculate_alliance_score_overview,
    calculate_dashboard_answer,
    render_dashboard_answer,
    route_dashboard_question,
)
from openai_intent import SUPPORTED_INTENT_DEFINITIONS


def overview_data():
    return pd.DataFrame(
        [
            {
                "alliance": "AAA",
                "player_name": "A1",
                "score_gained": 1000,
                "score_lost": 100,
                "net_score": 900,
                "net_status": "Positive",
            },
            {
                "alliance": "AAA",
                "player_name": "A2",
                "score_gained": 100,
                "score_lost": 400,
                "net_score": -300,
                "net_status": "Negative",
            },
            {
                "alliance": "BBB",
                "player_name": "B1",
                "score_gained": 1200,
                "score_lost": 0,
                "net_score": 1200,
                "net_status": "Positive",
            },
            {
                "alliance": "BBB",
                "player_name": "B2",
                "score_gained": 0,
                "score_lost": 800,
                "net_score": -800,
                "net_status": "Negative",
            },
            {
                "alliance": "CCC",
                "player_name": "C1",
                "score_gained": 500,
                "score_lost": 0,
                "net_score": 500,
                "net_status": "Positive",
            },
        ]
    )


@pytest.mark.parametrize(
    "question",
    [
        "Top alliance score",
        "Which alliance has the highest score?",
        "Show the best alliance score",
        "Who is the score-leading alliance?",
    ],
)
def test_generic_alliance_score_questions_route_to_overview(question):
    contract = route_dashboard_question(question, ["AAA", "BBB", "CCC"])

    assert contract["intent"] == "alliance_score_overview"
    assert contract["match_status"] == "matched"
    assert contract["source"] == "rule"


def test_explicit_metric_questions_keep_existing_precedence():
    assert route_dashboard_question(
        "Top net score alliance", ["AAA", "BBB"]
    )["intent"] == "net_score_leader_summary"
    assert route_dashboard_question(
        "Why is the top net-score alliance not first in positive contribution?",
        ["AAA", "BBB"],
    )["intent"] == "net_vs_positive_ranking"
    assert route_dashboard_question(
        "Which alliance has the highest positive contribution?", ["AAA", "BBB"]
    )["intent"] != "alliance_score_overview"


def test_action_question_does_not_silently_choose_a_top_metric():
    contract = route_dashboard_question(
        "Exclude the top alliance score", ["AAA", "BBB"]
    )

    assert contract["intent"] != "alliance_score_overview"


def test_overview_calculates_leaders_across_score_dimensions():
    answer = calculate_alliance_score_overview(overview_data(), "SVS Test")

    assert answer["status"] == "ok"
    assert answer["intent"] == "alliance_score_overview"
    assert answer["metrics"]["alliance_count"] == 3
    assert answer["metrics"]["net_score_leaders"] == [
        {
            "alliance": "AAA",
            "total_score_gained": 1100,
            "total_score_lost": 500,
            "total_net_score": 600,
            "positive_contribution": 900,
        }
    ]
    assert answer["metrics"]["score_gained_leaders"][0]["alliance"] == "BBB"
    assert answer["metrics"]["score_gained_leaders"][0]["total_score_gained"] == 1200
    assert answer["metrics"]["lowest_score_lost_leaders"][0]["alliance"] == "CCC"
    assert answer["metrics"]["lowest_score_lost_leaders"][0]["total_score_lost"] == 0
    assert answer["metrics"]["positive_contribution_leaders"][0]["alliance"] == "BBB"
    assert answer["metrics"]["positive_contribution_leaders"][0]["positive_contribution"] == 1200


def test_overview_wrapper_renders_soft_clarification_and_data_note():
    answer = calculate_dashboard_answer(
        "Top alliance score",
        overview_data(),
        "2026-W29",
    )
    rendered = render_dashboard_answer(answer)

    assert answer["intent"] == "alliance_score_overview"
    assert "Score can refer to several metrics" in rendered
    assert "Overall leader by net score" in rendered
    assert "Highest score gained" in rendered
    assert "Lowest score lost" in rendered
    assert "Highest positive contribution" in rendered
    assert "uses net score as the default" in rendered
    assert "Data note:" in rendered


def test_overview_reports_missing_columns_without_calculation():
    answer = calculate_alliance_score_overview(
        pd.DataFrame({"alliance": ["AAA"], "net_score": [100]}),
        "SVS Test",
    )

    assert answer["status"] == "error"
    assert answer["error_code"] == "missing_columns"
    assert set(answer["parameters"]["missing_columns"]) == {
        "score_gained",
        "score_lost",
    }


def test_openai_intent_catalog_includes_alliance_score_overview():
    definition = SUPPORTED_INTENT_DEFINITIONS["alliance_score_overview"]

    assert "multiple score metrics" in definition
