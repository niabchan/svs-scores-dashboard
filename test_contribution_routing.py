import json

import pandas as pd
import pytest

from ask_dashboard import (
    ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
    QUESTION_TOP_CONTRIBUTOR,
    QUESTION_TOP_CONTRIBUTORS,
    calculate_alliance_positive_contribution_leader,
    calculate_dashboard_answer,
    calculate_player_positive_contribution_leader,
    render_dashboard_answer,
    route_dashboard_question,
    validate_intent_contract,
)


def contribution_data():
    return pd.DataFrame(
        [
            {
                "alliance": "AAA",
                "player_name": "A1",
                "score_gained": 1_000,
                "score_lost": 100,
                "net_score": 900,
                "net_status": "Positive",
            },
            {
                "alliance": "AAA",
                "player_name": "A2",
                "score_gained": 600,
                "score_lost": 100,
                "net_score": 500,
                "net_status": "Positive",
            },
            {
                "alliance": "BBB",
                "player_name": "B1",
                "score_gained": 1_400,
                "score_lost": 200,
                "net_score": 1_200,
                "net_status": "Positive",
            },
            {
                "alliance": "BBB",
                "player_name": "B2",
                "score_gained": 100,
                "score_lost": 400,
                "net_score": -300,
                "net_status": "Negative",
            },
        ]
    )


def test_who_contributed_most_routes_to_single_player_mode():
    contract = route_dashboard_question(
        "Who contributed the most?",
        ["AAA", "BBB"],
    )
    assert contract["intent"] == "top_contributors"
    assert contract["parameters"] == {
        "alliance_names": [],
        "mode": "leader",
    }
    assert validate_intent_contract(contract) == contract


def test_named_alliance_who_question_keeps_player_subject():
    contract = route_dashboard_question(
        "Who contributed most in AAA?",
        ["AAA", "BBB"],
    )
    assert contract["intent"] == "top_contributors"
    assert contract["parameters"] == {
        "alliance_names": ["AAA"],
        "mode": "leader",
    }


def test_alliance_positive_score_question_routes_to_alliance_level():
    contract = route_dashboard_question(
        "The alliance that contributed the most to server positive score",
        ["AAA", "BBB"],
    )
    assert contract["intent"] == ALLIANCE_POSITIVE_CONTRIBUTION_INTENT
    assert contract["parameters"] == {"scope": "server"}
    assert validate_intent_contract(contract) == contract


@pytest.mark.parametrize(
    "question",
    [
        "Which alliance contributed the most?",
        "Which alliance has the highest positive contribution?",
        "The top alliance by positive score",
    ],
)
def test_alliance_subject_variants_route_to_alliance_leader(question):
    contract = route_dashboard_question(question, ["AAA", "BBB"])
    assert contract["intent"] == ALLIANCE_POSITIVE_CONTRIBUTION_INTENT


def test_grouped_contributor_wording_preserves_existing_list_output():
    for question in [
        QUESTION_TOP_CONTRIBUTORS,
        "Show the best contributors in AAA.",
        "List the top contributors within each alliance.",
    ]:
        contract = route_dashboard_question(question, ["AAA", "BBB"])
        assert contract["intent"] == "top_contributors"
        assert contract["parameters"].get("mode", "grouped") == "grouped"


def test_new_singular_suggested_question_routes_to_leader():
    contract = route_dashboard_question(
        QUESTION_TOP_CONTRIBUTOR,
        ["AAA", "BBB"],
    )
    assert contract["parameters"]["mode"] == "leader"


def test_player_positive_leader_calculation_uses_positive_net_score():
    answer = calculate_player_positive_contribution_leader(
        contribution_data(),
        "2026-W29",
    )
    leader = answer["metrics"]["leaders"][0]
    assert leader["player_name"] == "B1"
    assert leader["positive_contribution"] == 1_200
    assert leader["share_of_scope_positive"] == pytest.approx(46.1538, rel=1e-4)
    assert answer["metrics"]["mode"] == "leader"
    json.dumps(answer)


def test_player_leader_answer_starts_with_the_direct_result():
    answer = calculate_dashboard_answer(
        "Who contributed the most?",
        contribution_data(),
        "2026-W29",
        known_alliance_names=["AAA", "BBB"],
    )
    rendered = render_dashboard_answer(answer)
    assert rendered.startswith(
        "Under the current sidebar filters in 2026-W29, **B1** contributed the most"
    )
    assert "Share of positive contribution in this scope" in rendered


def test_alliance_positive_leader_calculation_ranks_alliances():
    answer = calculate_alliance_positive_contribution_leader(
        contribution_data(),
        "2026-W29",
    )
    leader = answer["metrics"]["leaders"][0]
    assert leader["alliance"] == "AAA"
    assert leader["positive_contribution"] == 1_400
    assert leader["share_of_scope_positive"] == pytest.approx(53.8461, rel=1e-4)
    assert [row["alliance"] for row in answer["rankings"]["alliances"]] == [
        "AAA",
        "BBB",
    ]


def test_server_wording_uses_full_period_data_not_sidebar_subset():
    current_filter = contribution_data().query("alliance == 'AAA'").copy()
    full_server = contribution_data()
    full_server.loc[
        full_server["player_name"] == "B1",
        ["score_gained", "score_lost", "net_score"],
    ] = [2_500, 100, 2_400]

    answer = calculate_dashboard_answer(
        "The alliance that contributed the most to server positive score",
        current_filter,
        "2026-W29",
        known_alliance_names=["AAA", "BBB"],
        server_data=full_server,
    )
    rendered = render_dashboard_answer(answer)
    assert answer["metrics"]["scope"] == "server"
    assert answer["metrics"]["leaders"][0]["alliance"] == "BBB"
    assert rendered.startswith("Across the full server in 2026-W29, **BBB**")


def test_same_question_without_server_respects_current_filter_scope():
    current_filter = contribution_data().query("alliance == 'AAA'").copy()
    answer = calculate_dashboard_answer(
        "Which alliance contributed the most?",
        current_filter,
        "2026-W29",
        known_alliance_names=["AAA", "BBB"],
        server_data=contribution_data(),
    )
    assert answer["metrics"]["scope"] == "current_filters"
    assert answer["metrics"]["leaders"][0]["alliance"] == "AAA"
    assert render_dashboard_answer(answer).startswith(
        "Under the current sidebar filters in 2026-W29, **AAA**"
    )


def test_invalid_contribution_mode_and_scope_are_rejected():
    contract = route_dashboard_question("Who contributed the most?", ["AAA"])
    contract["parameters"]["mode"] = "everyone"
    with pytest.raises(ValueError, match="mode"):
        validate_intent_contract(contract)

    alliance_contract = route_dashboard_question(
        "Which alliance contributed the most?",
        ["AAA"],
    )
    alliance_contract["parameters"]["scope"] = "galaxy"
    with pytest.raises(ValueError, match="scope"):
        validate_intent_contract(alliance_contract)


def test_reported_w29_questions_return_direct_leaders_from_repository_data():
    from pathlib import Path

    from data_loading import coerce_numeric_columns

    source = pd.read_csv(Path(__file__).with_name("svs_scores_utf8.csv"))
    source = coerce_numeric_columns(source)
    period = source[source["svs_date"] == "2026-W29"].copy()
    selected = period[period["alliance"].isin(["MBV", "NoM", "SnS", "TDA"])]

    player_answer = calculate_dashboard_answer(
        "Who contributed the most?",
        selected,
        "2026-W29",
        known_alliance_names=period["alliance"].dropna().unique().tolist(),
    )
    player_leader = player_answer["metrics"]["leaders"][0]
    assert player_leader["player_name"] == "K_NO_OZ"
    assert player_leader["positive_contribution"] == 4_641_673_280

    alliance_answer = calculate_dashboard_answer(
        "The alliance that contributed the most to server positive score",
        selected,
        "2026-W29",
        known_alliance_names=period["alliance"].dropna().unique().tolist(),
        server_data=period,
    )
    alliance_leader = alliance_answer["metrics"]["leaders"][0]
    assert alliance_leader["alliance"] == "NoM"
    assert alliance_leader["positive_contribution"] == 6_812_178_997

    rendered = render_dashboard_answer(alliance_answer)
    assert rendered.startswith("Across the full server in 2026-W29, **NoM**")
    assert "Positive-contribution ranking" in rendered
