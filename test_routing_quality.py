import pandas as pd

from ask_dashboard import (
    calculate_dashboard_answer,
    render_dashboard_answer,
    route_dashboard_question,
    route_dashboard_question_hybrid,
)


def _sample_scores():
    return pd.DataFrame(
        [
            {
                "alliance": "NoM",
                "player_name": "Alpha",
                "score_gained": 1_000,
                "score_lost": 200,
                "net_score": 800,
            },
            {
                "alliance": "SnS",
                "player_name": "Beta",
                "score_gained": 900,
                "score_lost": 300,
                "net_score": 600,
            },
        ]
    )


def _api_unsupported_contract():
    return {
        "schema_version": 1,
        "intent": "unsupported_question",
        "parameters": {},
        "source": "api",
        "confidence": 0.0,
        "match_status": "unsupported",
        "guidance_code": "unsupported_question",
    }


def test_metric_definition_is_rule_first_dashboard_help():
    calls = []

    def extractor(*args):
        calls.append(args)
        raise AssertionError("metric definition should not call AI")

    routed = route_dashboard_question_hybrid(
        "What is net score?",
        ["NoM", "SnS"],
        ai_enabled=True,
        ai_extractor=extractor,
    )

    assert routed["contract"]["intent"] == "dashboard_help"
    assert routed["contract"]["source"] == "rule"
    assert routed["ai_attempted"] is False
    assert calls == []


def test_metric_definition_renders_the_requested_metric_only():
    answer = calculate_dashboard_answer(
        "What is net score?",
        _sample_scores(),
        svs_period="2026-W29",
    )
    rendered = render_dashboard_answer(answer)

    assert answer["intent"] == "dashboard_help"
    assert "score gained − score lost" in rendered
    assert "How to use Ask Dashboard" not in rendered


def test_negative_share_definition_explains_the_formula():
    answer = calculate_dashboard_answer(
        "How is negative share calculated?",
        _sample_scores(),
    )
    rendered = render_dashboard_answer(answer)

    assert answer["intent"] == "dashboard_help"
    assert "negative impact ÷ (positive contribution + negative impact)" in rendered
    assert "not the percentage of players" in rendered


def test_strongest_overall_balance_routes_to_player_net_leader():
    contract = route_dashboard_question(
        "Who finished with the strongest overall balance among the players?",
        ["NoM", "SnS"],
    )

    assert contract["intent"] == "player_net_score_leader"
    assert contract["parameters"] == {"alliance_names": []}
    assert contract["source"] == "rule"

    answer = calculate_dashboard_answer(
        "Who finished with the strongest overall balance among the players?",
        _sample_scores(),
        svs_period="2026-W29",
    )
    rendered = render_dashboard_answer(answer)
    assert "Alpha" in rendered
    assert "highest net score" in rendered


def test_named_alliance_balance_wording_preserves_the_scope():
    contract = route_dashboard_question(
        "Which NoM player had the best overall result?",
        ["NoM", "SnS"],
    )

    assert contract["intent"] == "player_net_score_leader"
    assert contract["parameters"] == {"alliance_names": ["NoM"]}


def test_obvious_smalltalk_does_not_spend_an_ai_call():
    calls = []

    def extractor(*args):
        calls.append(args)
        return _api_unsupported_contract()

    routed = route_dashboard_question_hybrid(
        "Hello. How are you?",
        ["NoM", "SnS"],
        ai_enabled=True,
        ai_extractor=extractor,
    )

    assert routed["contract"]["intent"] == "unsupported_question"
    assert routed["ai_attempted"] is False
    assert calls == []

    answer = calculate_dashboard_answer(
        "Hello. How are you?",
        _sample_scores(),
        intent_router=lambda *_: routed,
    )
    rendered = render_dashboard_answer(answer)
    assert rendered.startswith("Hello!")
    assert "recorded SVS data" in rendered


def test_unfamiliar_dashboard_wording_can_still_reach_ai():
    calls = []

    def extractor(question, alliances):
        calls.append((question, alliances))
        return {
            "schema_version": 1,
            "intent": "alliance_score_overview",
            "parameters": {},
            "source": "api",
            "confidence": 0.9,
            "match_status": "matched",
            "guidance_code": None,
        }

    routed = route_dashboard_question_hybrid(
        "Which group carried the server result overall?",
        ["NoM", "SnS"],
        ai_enabled=True,
        ai_extractor=extractor,
    )

    assert routed["contract"]["intent"] == "alliance_score_overview"
    assert routed["contract"]["source"] == "api"
    assert routed["ai_attempted"] is True
    assert routed["ai_succeeded"] is True
    assert len(calls) == 1


def test_unsupported_guidance_no_longer_claims_the_dashboard_is_rule_only():
    routed = {
        "contract": _api_unsupported_contract(),
        "ai_attempted": True,
        "ai_succeeded": True,
        "diagnostic_code": None,
    }
    answer = calculate_dashboard_answer(
        "Tell me how many bananas are on Mars.",
        _sample_scores(),
        intent_router=lambda *_: routed,
    )
    rendered = render_dashboard_answer(answer)

    assert "rule-based matching" not in rendered
    assert "rather than an AI API" not in rendered
    assert "supported analyses" in rendered
    assert "What is net score?" in rendered


def test_prediction_question_gets_a_specific_limitation_message():
    routed = {
        "contract": _api_unsupported_contract(),
        "ai_attempted": True,
        "ai_succeeded": True,
        "diagnostic_code": None,
    }
    answer = calculate_dashboard_answer(
        "Predict who will win the next SVS.",
        _sample_scores(),
        intent_router=lambda *_: routed,
    )
    rendered = render_dashboard_answer(answer)

    assert "cannot predict a future winner" in rendered
    assert "recorded SVS scores" in rendered
