import json

import pandas as pd
import pytest

from ask_dashboard import (
    QUESTION_EXCLUSION_IMPACT,
    QUESTION_NEGATIVE_PERCENTAGE,
    QUESTION_NET_VS_POSITIVE,
    QUESTION_TOP_CONTRIBUTORS,
    calculate_dashboard_answer,
    calculate_player_net_score_leader,
    execute_dashboard_intent,
    render_dashboard_answer,
    route_dashboard_question,
    validate_intent_contract,
)


def sample_data():
    return pd.DataFrame(
        [
            {"alliance": "AAA", "player_name": "A1", "score_gained": 1000, "score_lost": 100, "net_score": 900, "net_status": "Positive"},
            {"alliance": "AAA", "player_name": "A2", "score_gained": 100, "score_lost": 400, "net_score": -300, "net_status": "Negative"},
            {"alliance": "BBB", "player_name": "B1", "score_gained": 1200, "score_lost": 0, "net_score": 1200, "net_status": "Positive"},
            {"alliance": "BBB", "player_name": "B2", "score_gained": 0, "score_lost": 800, "net_score": -800, "net_status": "Negative"},
            {"alliance": "CCC", "player_name": "C1", "score_gained": 500, "score_lost": 0, "net_score": 500, "net_status": "Positive"},
        ]
    )


def ask(question, data=None, selected=None, known=None):
    answer = calculate_dashboard_answer(
        question,
        sample_data() if data is None else data,
        "SVS Test",
        selected,
        known,
    )
    assert isinstance(answer, dict)
    assert answer["kind"] == "dashboard_answer"
    return answer


def assert_json_serializable(value):
    json.dumps(value)


def test_exact_suggested_questions_route_to_contracts():
    expected = {
        QUESTION_NET_VS_POSITIVE: ("net_vs_positive_ranking", {}),
        QUESTION_EXCLUSION_IMPACT: ("player_exclusion_impact", {}),
        QUESTION_NEGATIVE_PERCENTAGE: ("negative_share_change", {"requested_direction": "increase"}),
        QUESTION_TOP_CONTRIBUTORS: ("top_contributors", {"alliance_names": []}),
    }
    for question, (intent, parameters) in expected.items():
        contract = route_dashboard_question(question, known_alliance_names=["AAA", "BBB"])
        assert contract["intent"] == intent
        assert contract["parameters"] == parameters
        assert contract["source"] == "rule"
        assert contract["confidence"] == 1.0
        assert contract["match_status"] == "matched"
        assert_json_serializable(contract)


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("How did excluding selected players change the result?", "player_exclusion_impact"),
        ("Why is the net-score leader not first in positive contribution?", "net_vs_positive_ranking"),
        ("Which alliance leads net score, and why?", "net_score_leader_summary"),
        ("Show the best contributors in SnS.", "top_contributors"),
        ("What is the total net score without TDA?", "alliance_exclusion_total_net"),
    ],
)
def test_natural_language_variants_route_to_contract_intents(question, intent):
    contract = route_dashboard_question(question, known_alliance_names=["SnS", "TDA"])
    assert contract["intent"] == intent
    assert contract["match_status"] == "matched"


def test_route_extracts_named_alliances_and_negative_direction():
    contributors = route_dashboard_question("Who contributed most in SnS?", ["SnS", "TDA"])
    exclusion = route_dashboard_question("What is the total net score without TDA?", ["SnS", "TDA"])
    negative = route_dashboard_question("Why is the negative percentage lower now?", ["SnS"])
    assert contributors["parameters"]["alliance_names"] == ["SnS"]
    assert exclusion["parameters"]["excluded_alliances"] == ["TDA"]
    assert negative["parameters"]["requested_direction"] == "decrease"


def test_route_missing_alliance_and_unsupported_contracts():
    clarification = route_dashboard_question("What is the total net score without that alliance?", ["AAA"])
    unsupported = route_dashboard_question("Predict the next SVS result.", ["AAA"])
    assert clarification["match_status"] == "needs_clarification"
    assert clarification["guidance_code"] == "missing_alliance_name"
    assert unsupported["match_status"] == "unsupported"
    assert unsupported["confidence"] == 0.0
    assert unsupported["guidance_code"] == "unsupported_question"


def test_route_does_not_require_dataframe():
    contract = route_dashboard_question("Who contributed most in AAA?", ["AAA"])
    assert contract["intent"] == "top_contributors"
    assert_json_serializable(contract)


def test_validate_intent_contract_valid_contract_passes():
    contract = route_dashboard_question("Why did the negative share rise?", ["AAA"])
    assert validate_intent_contract(contract) == contract


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 999, "schema_version"),
        ("intent", "made_up", "unknown intent"),
        ("source", "bogus", "source"),
        ("confidence", 2, "confidence"),
        ("confidence", True, "confidence"),
        ("match_status", "maybe", "match_status"),
        ("parameters", [], "parameters"),
    ],
)
def test_validate_intent_contract_rejects_invalid_fields(field, value, message):
    contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    contract[field] = value
    with pytest.raises(ValueError, match=message):
        validate_intent_contract(contract)


def test_validate_intent_contract_rejects_incorrect_parameter_shapes():
    bad_top = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    bad_top["parameters"]["alliance_names"] = "AAA"
    with pytest.raises(ValueError, match="alliance_names"):
        validate_intent_contract(bad_top)
    bad_negative = route_dashboard_question(QUESTION_NEGATIVE_PERCENTAGE, ["AAA"])
    bad_negative["parameters"]["requested_direction"] = "sideways"
    with pytest.raises(ValueError, match="requested_direction"):
        validate_intent_contract(bad_negative)


@pytest.mark.parametrize(
    "question",
    [
        QUESTION_NET_VS_POSITIVE,
        QUESTION_EXCLUSION_IMPACT,
        QUESTION_NEGATIVE_PERCENTAGE,
        QUESTION_TOP_CONTRIBUTORS,
        "What is the total net score without BBB?",
        "Which alliance leads net score, and why?",
    ],
)
def test_execute_contract_matches_wrapper_visible_result(question):
    data = sample_data()
    selected = ["A1", "B1", "C1"]
    known = data["alliance"].dropna().unique().tolist()
    wrapper = calculate_dashboard_answer(question, data, "SVS Test", selected, known)
    contract = route_dashboard_question(question, known)
    executed = execute_dashboard_intent(contract, data, "SVS Test", selected, known)
    assert executed["intent"] == wrapper["intent"]
    assert render_dashboard_answer(executed) == render_dashboard_answer(wrapper)


def test_execute_clarification_and_unsupported_without_calculation():
    clarification = execute_dashboard_intent(
        route_dashboard_question("What is the total net score without that alliance?", ["AAA"]),
        pd.DataFrame(),
        "SVS Test",
        known_alliance_names=["AAA"],
    )
    unsupported = execute_dashboard_intent(
        route_dashboard_question("Predict the next SVS result.", ["AAA"]),
        pd.DataFrame(),
        "SVS Test",
    )
    assert clarification["status"] == "guidance"
    assert clarification["guidance_code"] == "missing_alliance_name"
    assert unsupported["guidance_code"] == "unsupported_question"
    assert "rule-based matching rather than an AI API" in render_dashboard_answer(unsupported)


def test_direct_api_execution_attaches_routing_source():
    contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    contract["source"] = "api"
    contract["confidence"] = 0.72
    answer = execute_dashboard_intent(contract, sample_data(), "SVS Test")
    assert answer["routing"]["source"] == "api"
    assert answer["routing"]["confidence"] == 0.72


def test_direct_execution_includes_routing_for_all_result_states():
    data = sample_data()
    matched = execute_dashboard_intent(route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"]), data, "SVS Test")
    clarification = execute_dashboard_intent(
        route_dashboard_question("What is the total net score without that alliance?", ["AAA"]),
        data,
        "SVS Test",
    )
    unsupported = execute_dashboard_intent(route_dashboard_question("Predict the next SVS result.", ["AAA"]), data, "SVS Test")
    calculator_guidance = execute_dashboard_intent(
        route_dashboard_question(QUESTION_EXCLUSION_IMPACT, ["AAA"]),
        pd.DataFrame(columns=["player_name", "score_gained", "score_lost", "net_score"]),
        "SVS Test",
    )
    calculator_error = execute_dashboard_intent(
        route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"]),
        pd.DataFrame(),
        "SVS Test",
    )
    for answer in [matched, clarification, unsupported, calculator_guidance, calculator_error]:
        assert "routing" in answer
        assert_json_serializable(answer["routing"])
    assert matched["status"] == "ok"
    assert clarification["status"] == "guidance"
    assert unsupported["guidance_code"] == "unsupported_question"
    assert calculator_guidance["guidance_code"] == "empty_player_scope"
    assert calculator_error["error_code"] == "missing_columns"


def test_wrapper_preserves_question_mentions_and_json_serializable_answer():
    data = sample_data().replace({"AAA": "SnS"})
    answer = calculate_dashboard_answer("Who contributed most in SnS?", data, "SVS Test")
    assert answer["parameters"]["question"] == "Who contributed most in SnS?"
    assert answer["parameters"]["mentioned_alliances"] == ["SnS"]
    assert_json_serializable(answer)


def test_question_log_source_from_direct_executor_answer():
    from ask_dashboard import build_question_log_record

    contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    contract["source"] = "api"
    contract["confidence"] = 0.5
    answer = execute_dashboard_intent(contract, sample_data(), "SVS Test")
    record = build_question_log_record(answer, timestamp_utc="2026-07-15T06:30:00Z")
    assert record["source"] == "api"


def test_malformed_contract_cannot_invoke_calculation():
    with pytest.raises(ValueError):
        execute_dashboard_intent({"intent": "top_contributors"}, sample_data())


def test_malformed_contract_cannot_invoke_calculation_function(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("calculation should not be invoked")

    monkeypatch.setattr("ask_dashboard.calculate_top_contributors", fail_if_called)
    contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    contract["confidence"] = 0.5
    with pytest.raises(ValueError, match="confidence"):
        execute_dashboard_intent(contract, sample_data())


@pytest.mark.parametrize(
    "updates",
    [
        {"intent": "unsupported_question", "match_status": "matched", "confidence": 1.0, "guidance_code": None},
        {"intent": "unsupported_question", "match_status": "needs_clarification", "confidence": 1.0, "guidance_code": "unsupported_question"},
        {"intent": "top_contributors", "match_status": "unsupported", "confidence": 0.0, "guidance_code": "unsupported_question"},
        {"intent": "unsupported_question", "match_status": "unsupported", "confidence": 0.0, "guidance_code": "other"},
        {"intent": "unsupported_question", "match_status": "unsupported", "confidence": 0.0, "guidance_code": "unsupported_question", "parameters": {"x": 1}},
    ],
)
def test_validate_rejects_unsupported_semantic_conflicts(updates):
    contract = route_dashboard_question("Predict the next SVS result.", ["AAA"])
    contract.update(updates)
    with pytest.raises(ValueError):
        validate_intent_contract(contract)


@pytest.mark.parametrize(
    "updates",
    [
        {"intent": "top_contributors", "parameters": {"alliance_names": []}},
        {"intent": "alliance_exclusion_total_net", "parameters": {"excluded_alliances": ["AAA"]}},
    ],
)
def test_validate_rejects_invalid_clarification_contracts(updates):
    contract = route_dashboard_question("What is the total net score without that alliance?", ["AAA"])
    contract.update(updates)
    with pytest.raises(ValueError):
        validate_intent_contract(contract)


def test_validate_rejects_matched_empty_alliance_exclusion():
    contract = route_dashboard_question("What is the total net score without AAA?", ["AAA"])
    contract["parameters"]["excluded_alliances"] = []
    with pytest.raises(ValueError, match="requires excluded_alliances"):
        validate_intent_contract(contract)


@pytest.mark.parametrize(
    "contract",
    [
        {
            "schema_version": 1,
            "intent": "alliance_exclusion_total_net",
            "parameters": {"excluded_alliances": [""]},
            "source": "rule",
            "confidence": 1.0,
            "match_status": "matched",
            "guidance_code": None,
        },
        {
            "schema_version": 1,
            "intent": "top_contributors",
            "parameters": {"alliance_names": ["   "]},
            "source": "rule",
            "confidence": 1.0,
            "match_status": "matched",
            "guidance_code": None,
        },
    ],
)
def test_validate_rejects_blank_alliance_names(contract):
    with pytest.raises(ValueError, match="nonblank"):
        validate_intent_contract(contract)


@pytest.mark.parametrize(
    "match_status, confidence, guidance_code",
    [
        ("matched", 0.9, None),
        ("needs_clarification", 0.9, "missing_alliance_name"),
        ("unsupported", 0.1, "unsupported_question"),
    ],
)
def test_validate_rejects_invalid_rule_confidence_values(match_status, confidence, guidance_code):
    intent = "unsupported_question" if match_status == "unsupported" else "alliance_exclusion_total_net"
    parameters = {} if match_status == "unsupported" else {"excluded_alliances": [] if match_status == "needs_clarification" else ["AAA"]}
    contract = {
        "schema_version": 1,
        "intent": intent,
        "parameters": parameters,
        "source": "rule",
        "confidence": confidence,
        "match_status": match_status,
        "guidance_code": guidance_code,
    }
    with pytest.raises(ValueError, match="confidence"):
        validate_intent_contract(contract)


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), float("-inf")])
def test_validate_rejects_nonfinite_confidence_values(confidence):
    contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    contract["confidence"] = confidence
    with pytest.raises(ValueError, match="finite"):
        validate_intent_contract(contract)


def test_validate_rejects_unknown_top_level_contract_field():
    contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    contract["unexpected"] = "payload"
    with pytest.raises(ValueError, match="unknown intent contract field"):
        validate_intent_contract(contract)


@pytest.mark.parametrize(
    "contract",
    [
        {
            "schema_version": 1,
            "intent": "top_contributors",
            "parameters": {"alliance_names": ["AAA"], "unexpected": "payload"},
            "source": "rule",
            "confidence": 1.0,
            "match_status": "matched",
            "guidance_code": None,
        },
        {
            "schema_version": 1,
            "intent": "negative_share_change",
            "parameters": {"requested_direction": "increase", "unexpected": "payload"},
            "source": "rule",
            "confidence": 1.0,
            "match_status": "matched",
            "guidance_code": None,
        },
        {
            "schema_version": 1,
            "intent": "alliance_exclusion_total_net",
            "parameters": {"excluded_alliances": ["AAA"], "unexpected": "payload"},
            "source": "rule",
            "confidence": 1.0,
            "match_status": "matched",
            "guidance_code": None,
        },
    ],
)
def test_validate_rejects_unknown_parameter_fields(contract):
    with pytest.raises(ValueError, match="unknown parameter field"):
        validate_intent_contract(contract)


def test_validate_rejects_parameters_for_intent_that_accepts_none():
    contract = route_dashboard_question(QUESTION_NET_VS_POSITIVE, ["AAA"])
    contract["parameters"] = {"unexpected": "payload"}
    with pytest.raises(ValueError, match="does not accept parameters"):
        validate_intent_contract(contract)


def test_validate_rejects_non_json_serializable_top_level_value():
    contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    contract["unexpected"] = object()
    with pytest.raises(ValueError, match="unknown intent contract field"):
        validate_intent_contract(contract)


def test_validate_rejects_non_json_serializable_nested_parameter_value():
    contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    contract["parameters"]["alliance_names"] = [object()]
    with pytest.raises(ValueError, match="nonblank strings"):
        validate_intent_contract(contract)


def test_validate_wraps_json_serialization_failures(monkeypatch):
    def fail_json_dumps(_value):
        raise TypeError("not serializable")

    monkeypatch.setattr("ask_dashboard.json.dumps", fail_json_dumps)
    contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    with pytest.raises(ValueError, match="JSON serializable"):
        validate_intent_contract(contract)


def test_rule_and_api_contracts_remain_json_serializable():
    rule_contract = validate_intent_contract(route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"]))
    api_contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    api_contract["source"] = "api"
    api_contract["confidence"] = 0.42
    api_contract = validate_intent_contract(api_contract)
    json.dumps(rule_contract)
    json.dumps(api_contract)


def test_answer_includes_json_serializable_routing_metadata():
    answer = ask("Who contributed most in AAA?")
    assert answer["routing"]["intent"] == "top_contributors"
    encoded = json.dumps(answer["routing"])
    assert "DataFrame" not in encoded and "rankings" not in encoded
    assert_json_serializable(answer)


def test_question_log_source_comes_from_routing_metadata():
    from ask_dashboard import build_question_log_record

    answer = ask(QUESTION_TOP_CONTRIBUTORS)
    answer["routing"]["source"] = "api"
    record = build_question_log_record(answer, timestamp_utc="2026-07-15T06:30:00Z")
    assert record["source"] == "api"


def test_suggested_net_vs_positive_question():
    answer = ask(QUESTION_NET_VS_POSITIVE)
    assert answer["intent"] == "net_vs_positive_ranking"
    assert answer["status"] == "ok"
    assert answer["metrics"]["top_net_alliance"] == "AAA"
    assert answer["metrics"]["top_net_score"] == 600


def test_suggested_exclusion_impact_question():
    answer = ask(QUESTION_EXCLUSION_IMPACT, selected=["A1", "B1", "C1"])
    assert answer["intent"] == "player_exclusion_impact"
    assert answer["parameters"]["excluded_players"] == ["A2", "B2"]
    assert answer["metrics"]["before"]["net_score"] == 1500
    assert answer["metrics"]["after"]["net_score"] == 2600
    assert answer["metrics"]["changes"]["net_score"] == 1100


def test_suggested_negative_percentage_question():
    answer = ask(QUESTION_NEGATIVE_PERCENTAGE, selected=["A1", "B1", "C1"])
    assert answer["intent"] == "negative_share_change"
    assert answer["metrics"]["before"]["negative"] == 1100
    assert answer["metrics"]["after"]["negative"] == 0
    assert answer["metrics"]["excluded_player_count"] == 2


def test_suggested_top_contributors_question():
    answer = ask(QUESTION_TOP_CONTRIBUTORS)
    assert answer["intent"] == "top_contributors"
    assert answer["metrics"]["alliance_count"] == 3
    assert [group["alliance"] for group in answer["rankings"]["alliances"]] == ["AAA", "BBB", "CCC"]


def test_custom_total_net_without_named_alliance():
    answer = ask("What is the total net score without BBB?")
    assert answer["intent"] == "alliance_exclusion_total_net"
    assert answer["parameters"]["recognized_alliances"] == ["BBB"]
    assert answer["metrics"]["before_net_score"] == 1500
    assert answer["metrics"]["after_net_score"] == 1100
    assert answer["metrics"]["net_score_change"] == -400
    assert answer["metrics"]["excluded_score_gained"] == 1200
    assert answer["metrics"]["excluded_score_lost"] == 800
    assert answer["metrics"]["excluded_net_score"] == 400


def test_custom_top_contributors_for_named_alliance():
    answer = ask("Who contributed most in AAA?")
    assert answer["intent"] == "top_contributors"
    assert answer["parameters"]["alliance_names"] == ["AAA"]
    assert [group["alliance"] for group in answer["rankings"]["alliances"]] == ["AAA"]


def test_custom_selected_player_exclusion_pattern():
    answer = ask("How did excluding selected players change the result?", selected=["A1", "B1", "C1"])
    assert answer["intent"] == "player_exclusion_impact"
    assert answer["metrics"]["excluded_player_count"] == 2


def test_custom_negative_share_pattern():
    answer = ask("Why did the negative share rise?", selected=["A1", "A2", "B2", "C1"])
    assert answer["intent"] == "negative_share_change"
    assert answer["metrics"]["excluded_players"] == ["B1"]


def test_custom_ranking_pattern():
    answer = ask("Why is the net-score leader not first in positive contribution?")
    assert answer["intent"] == "net_vs_positive_ranking"
    assert answer["rankings"]["alliances"]


def test_named_alliance_contributors_without_who_or_player_terms():
    data = sample_data().replace({"AAA": "SnS"})
    answer = ask("Show the best contributors in SnS.", data=data)
    assert answer["intent"] == "top_contributors"
    assert answer["parameters"]["alliance_names"] == ["SnS"]
    assert [group["alliance"] for group in answer["rankings"]["alliances"]] == ["SnS"]


def test_named_alliance_contributor_nearby_variants():
    data = sample_data().replace({"AAA": "SnS"})
    questions = [
        "show TOP contribution in sns!",
        "Most contributors for SnS?",
        "Best contribution, SnS",
        "Who contributed most in SnS?",
    ]
    for question in questions:
        answer = ask(question, data=data)
        assert answer["intent"] == "top_contributors"
        assert answer["parameters"]["matched_alliances"] == ["SnS"]


def test_player_exclusion_noun_and_effect_terms_route():
    answer = ask("How did player exclusions affect the net score?", selected=["A1", "B1", "C1"])
    assert answer["intent"] == "player_exclusion_impact"
    assert answer["metrics"]["excluded_player_count"] == 2


def test_player_exclusion_nearby_effect_variants_route():
    questions = [
        "Did player exclusion effect the result?",
        "Player exclusions affected net score?",
        "How did selected exclusions change the result?",
    ]
    for question in questions:
        answer = ask(question, selected=["A1", "B1", "C1"])
        assert answer["intent"] == "player_exclusion_impact"


def test_player_exclusion_net_score_questions_precede_missing_alliance_guidance():
    questions = [
        "How did player exclusions affect the net score?",
        "Player exclusions affected net score?",
    ]
    for question in questions:
        answer = ask(question, selected=["A1", "B1", "C1"])
        assert answer["intent"] == "player_exclusion_impact"
        assert answer["guidance_code"] is None


def test_alliance_exclusion_missing_name_still_routes_to_guidance():
    answer = ask("What is the total net score without an alliance?")
    assert answer["intent"] == "alliance_exclusion_total_net"
    assert answer["guidance_code"] == "missing_alliance_name"


def test_named_alliance_exclusion_still_routes_to_total_net():
    data = sample_data().replace({"BBB": "TDA"})
    answer = ask("What is the total net score without TDA?", data=data)
    assert answer["intent"] == "alliance_exclusion_total_net"
    assert answer["parameters"]["recognized_alliances"] == ["TDA"]


def test_negative_share_lower_question_routes_and_reports_data_direction():
    answer = ask("Why is the negative percentage lower now?", selected=["A1", "A2", "B2", "C1"])
    assert answer["intent"] == "negative_share_change"
    assert answer["metrics"]["share_change"] > 0
    rendered = render_dashboard_answer(answer)
    assert "increased by" in rendered
    assert "lower" not in rendered.casefold()


def test_negative_share_downward_and_neutral_vocabulary_variants_route():
    questions = [
        "Why did the negative percent decrease?",
        "Why did the negative share declined?",
        "Why did the negative ratio fall?",
        "Why did negative percentage dropped?",
        "Why did negative percentage reduce?",
        "Why did the negative percentage change?",
    ]
    for question in questions:
        answer = ask(question, selected=["A1", "B1", "C1"])
        assert answer["intent"] == "negative_share_change"



def negative_share_direction_data():
    return pd.DataFrame(
        [
            {"alliance": "AAA", "player_name": "P1", "score_gained": 900, "score_lost": 0, "net_score": 900, "net_status": "Positive"},
            {"alliance": "AAA", "player_name": "P2", "score_gained": 600, "score_lost": 0, "net_score": 600, "net_status": "Positive"},
            {"alliance": "BBB", "player_name": "N1", "score_gained": 0, "score_lost": 1100, "net_score": -1100, "net_status": "Negative"},
            {"alliance": "BBB", "player_name": "N2", "score_gained": 0, "score_lost": 300, "net_score": -300, "net_status": "Negative"},
        ]
    )


def unchanged_negative_share_data():
    return pd.DataFrame(
        [
            {"alliance": "AAA", "player_name": "P1", "score_gained": 100, "score_lost": 0, "net_score": 100, "net_status": "Positive"},
            {"alliance": "AAA", "player_name": "P2", "score_gained": 100, "score_lost": 0, "net_score": 100, "net_status": "Positive"},
            {"alliance": "BBB", "player_name": "N1", "score_gained": 0, "score_lost": 100, "net_score": -100, "net_status": "Negative"},
            {"alliance": "BBB", "player_name": "N2", "score_gained": 0, "score_lost": 100, "net_score": -100, "net_status": "Negative"},
        ]
    )


def test_negative_share_downward_question_actual_decrease_no_premise_mismatch():
    answer = ask(
        "Why is the negative percentage lower now?",
        data=negative_share_direction_data(),
        selected=["P1", "P2", "N2"],
    )
    rendered = render_dashboard_answer(answer)
    assert answer["parameters"]["requested_direction"] == "decrease"
    assert answer["metrics"]["share_change"] < -0.05
    assert "decreased by" in rendered
    assert "premise does not match" not in rendered.casefold()


def test_negative_share_downward_question_actual_increase_premise_mismatch():
    answer = ask(
        "Why is the negative percentage lower now?",
        data=negative_share_direction_data(),
        selected=["P2", "N1", "N2"],
    )
    rendered = render_dashboard_answer(answer)
    assert answer["parameters"]["requested_direction"] == "decrease"
    assert answer["metrics"]["share_change"] > 0.05
    assert "premise does not match" in rendered.casefold()
    assert "increased by" in rendered


def test_negative_share_upward_question_actual_increase_no_premise_mismatch():
    answer = ask(
        "Why did the negative percentage increase?",
        data=negative_share_direction_data(),
        selected=["P2", "N1", "N2"],
    )
    rendered = render_dashboard_answer(answer)
    assert answer["parameters"]["requested_direction"] == "increase"
    assert answer["metrics"]["share_change"] > 0.05
    assert "increased by" in rendered
    assert "premise does not match" not in rendered.casefold()


def test_negative_share_upward_question_actual_decrease_premise_mismatch():
    answer = ask(
        "Why did the negative percentage increase?",
        data=negative_share_direction_data(),
        selected=["P1", "P2", "N2"],
    )
    rendered = render_dashboard_answer(answer)
    assert answer["parameters"]["requested_direction"] == "increase"
    assert answer["metrics"]["share_change"] < -0.05
    assert "premise does not match" in rendered.casefold()
    assert "decreased by" in rendered


def test_negative_share_neutral_change_question_actual_increase_no_premise_mismatch():
    answer = ask(
        "How did the negative percentage change?",
        data=negative_share_direction_data(),
        selected=["P2", "N1", "N2"],
    )
    rendered = render_dashboard_answer(answer)
    assert answer["parameters"]["requested_direction"] == "neutral"
    assert answer["metrics"]["share_change"] > 0.05
    assert "premise does not match" not in rendered.casefold()


def test_negative_share_neutral_change_question_actual_decrease_no_premise_mismatch():
    answer = ask(
        "How did the negative percentage change?",
        data=negative_share_direction_data(),
        selected=["P1", "P2", "N2"],
    )
    rendered = render_dashboard_answer(answer)
    assert answer["parameters"]["requested_direction"] == "neutral"
    assert answer["metrics"]["share_change"] < -0.05
    assert "premise does not match" not in rendered.casefold()


def test_negative_share_effectively_unchanged_asserted_direction_premise_mismatch():
    for question, expected_direction in [
        ("Why did the negative percentage increase?", "increase"),
        ("Why is the negative percentage lower now?", "decrease"),
    ]:
        answer = ask(question, data=unchanged_negative_share_data(), selected=["P1", "N1"])
        rendered = render_dashboard_answer(answer)
        assert answer["parameters"]["requested_direction"] == expected_direction
        assert abs(answer["metrics"]["share_change"]) <= 0.05
        assert "premise does not match" in rendered.casefold()
        assert "effectively unchanged" in rendered


def test_negative_share_requested_direction_is_json_serializable():
    answer = ask("Why is the negative percentage lower now?", selected=["A1", "B1", "C1"])
    encoded = json.dumps(answer)
    assert answer["parameters"]["requested_direction"] == "decrease"
    assert '"requested_direction": "decrease"' in encoded


def test_negative_share_matching_lower_now_regression_mentions_decrease_without_premise_mismatch():
    data = pd.DataFrame(
        [
            {"alliance": "AAA", "player_name": "P keep", "score_gained": 322.7, "score_lost": 0, "net_score": 322.7, "net_status": "Positive"},
            {"alliance": "AAA", "player_name": "P excluded", "score_gained": 90.3, "score_lost": 0, "net_score": 90.3, "net_status": "Positive"},
            {"alliance": "BBB", "player_name": "N keep", "score_gained": 0, "score_lost": 377.3, "net_score": -377.3, "net_status": "Negative"},
            {"alliance": "BBB", "player_name": "N excluded", "score_gained": 0, "score_lost": 209.7, "net_score": -209.7, "net_status": "Negative"},
        ]
    )
    answer = ask("Why is the negative percentage lower now?", data=data, selected=["P keep", "N keep"])
    rendered = render_dashboard_answer(answer)
    assert answer["parameters"]["requested_direction"] == "decrease"
    assert answer["metrics"]["before"]["negative_share"] == pytest.approx(58.7)
    assert answer["metrics"]["after"]["negative_share"] == pytest.approx(53.9)
    assert "decreased by" in rendered
    assert "premise does not match" not in rendered.casefold()


@pytest.mark.parametrize(
    "question",
    [
        "Top net score player",
        "Who has the highest net score?",
        "Which player leads in net score?",
        "Show the top net-score players",
        "Who is #1 by net score?",
        "WHO, exactly, has the BEST NET-SCORE?!",
    ],
)
def test_player_net_score_leader_variants_route_to_player_intent(question):
    contract = route_dashboard_question(question, known_alliance_names=["AAA", "BBB", "CCC"])
    assert contract["intent"] == "player_net_score_leader"
    assert contract["intent"] != "net_score_leader_summary"
    assert validate_intent_contract(contract) == contract


def test_smoke_regression_top_net_score_player_is_player_level():
    answer = ask("Top net score player")
    rendered = render_dashboard_answer(answer)
    assert answer["intent"] == "player_net_score_leader"
    assert answer["metrics"]["top_player"] == "B1"
    assert "**B1** has the highest net score" in rendered
    assert "leads total net score" not in rendered
    assert "positive contribution minus negative impact" not in rendered.casefold()


def test_player_net_score_named_alliance_uses_canonical_value():
    data = sample_data().replace({"AAA": "SnS"})
    answer = ask("Who has the highest net score in sns?", data=data)
    assert answer["intent"] == "player_net_score_leader"
    assert answer["parameters"]["alliance_names"] == ["SnS"]
    assert answer["parameters"]["matched_alliances"] == ["SnS"]
    assert answer["metrics"]["top_player"] == "A1"


def test_player_net_score_unknown_alliance_guidance():
    answer = ask("Who has the highest net score in ZZZ?", known=["AAA", "BBB", "CCC", "ZZZ"])
    assert answer["intent"] == "player_net_score_leader"
    assert answer["guidance_code"] == "alliance_outside_scope"
    assert answer["parameters"]["outside_scope_alliances"] == ["ZZZ"]


def test_calculate_player_net_score_leader_aggregates_and_ranks_stably():
    data = pd.DataFrame([
        {"alliance": "AAA", "player_name": "Zed", "score_gained": 10, "score_lost": 0, "net_score": 10},
        {"alliance": "AAA", "player_name": "Ann", "score_gained": 50, "score_lost": 10, "net_score": 40},
        {"alliance": "AAA", "player_name": "Ann", "score_gained": 10, "score_lost": 0, "net_score": 10},
        {"alliance": "BBB", "player_name": "Ann", "score_gained": 100, "score_lost": 60, "net_score": 40},
    ])
    answer = calculate_player_net_score_leader(data, "2026-W25")
    assert answer["metrics"]["top_player"] == "Ann"
    assert answer["metrics"]["top_alliance"] == "AAA"
    assert answer["metrics"]["top_net_score"] == 50
    assert [(r["player_name"], r["alliance"], r["rank"]) for r in answer["rankings"]["players"]] == [("Ann", "AAA", 1), ("Ann", "BBB", 2), ("Zed", "AAA", 3)]
    json.dumps(answer)


def test_calculate_player_net_score_leader_tie_negative_empty_and_missing_columns():
    tie = pd.DataFrame([
        {"alliance": "AAA", "player_name": "A", "score_gained": 0, "score_lost": 5, "net_score": -5},
        {"alliance": "BBB", "player_name": "B", "score_gained": 0, "score_lost": 5, "net_score": -5},
    ])
    answer = calculate_player_net_score_leader(tie)
    assert answer["metrics"]["leader_count"] == 2
    assert answer["metrics"]["top_net_score"] == -5
    rendered = render_dashboard_answer(answer)
    assert "tied for first" in rendered
    empty = calculate_player_net_score_leader(tie.iloc[0:0])
    assert empty["guidance_code"] == "empty_player_scope"
    missing = calculate_player_net_score_leader(tie.drop(columns=["score_lost"]))
    assert missing["error_code"] == "missing_columns"


def test_player_net_score_contract_and_hybrid_do_not_fallback():
    contract = route_dashboard_question("Who has the highest net score?", ["AAA"])
    assert validate_intent_contract(contract)["parameters"] == {"alliance_names": []}
    with pytest.raises(ValueError, match="unknown parameter field"):
        validate_intent_contract({**contract, "parameters": {"alliance_names": [], "extra": 1}})
    result = __import__("ask_dashboard").route_dashboard_question_hybrid(
        "Who has the highest net score?", ["AAA"], ai_enabled=True, ai_extractor=lambda *_: pytest.fail("AI fallback called")
    )
    assert result["contract"]["intent"] == "player_net_score_leader"
    assert result["ai_attempted"] is False


def test_general_net_score_leader_summary():
    answer = ask("Which alliance leads net score, and why?")
    assert answer["intent"] == "net_score_leader_summary"
    assert answer["metrics"]["top_net_alliance"] == "AAA"
    assert answer["metrics"]["top_net_score"] == 600
    assert answer["metrics"]["top_positive_contribution"] == 900
    assert answer["metrics"]["top_negative_impact"] == 300
    assert answer["metrics"]["top_positive_rank"] == 2
    rendered = render_dashboard_answer(answer)
    assert "premise does not match" not in rendered.casefold()
    assert "leads total net score" in rendered
    assert "Positive-contribution rank" in rendered


def test_multi_word_net_leader_terms_route_to_summary():
    questions = [
        "Which alliance has the highest net score?",
        "Top net-score alliance",
        "Which alliance has the highest total net score?",
    ]
    for question in questions:
        answer = ask(question)
        assert answer["intent"] == "net_score_leader_summary"


def test_ambiguous_alliance_score_questions_do_not_route_to_top_contributors():
    data = sample_data().replace({"AAA": "SnS"})
    questions = [
        "What is the best score in SnS?",
        "What is the top net score in SnS?",
    ]
    for question in questions:
        answer = ask(question, data=data)
        assert answer["intent"] != "top_contributors"


def test_general_net_score_leader_tie_is_explicit():
    data = pd.DataFrame(
        [
            {"alliance": "AAA", "player_name": "A1", "score_gained": 1000, "score_lost": 0, "net_score": 1000, "net_status": "Positive"},
            {"alliance": "BBB", "player_name": "B1", "score_gained": 1200, "score_lost": 0, "net_score": 1200, "net_status": "Positive"},
            {"alliance": "BBB", "player_name": "B2", "score_gained": 0, "score_lost": 200, "net_score": -200, "net_status": "Negative"},
        ]
    )
    answer = ask("Which alliance leads net score, and why?", data=data)
    assert answer["intent"] == "net_score_leader_summary"
    assert answer["metrics"]["leader_count"] == 2
    rendered = render_dashboard_answer(answer)
    assert "tied for first" in rendered


def test_case_and_punctuation_variations_route():
    answer = ask("WHICH ALLIANCE LEADS NET SCORE?!")
    assert answer["intent"] == "net_score_leader_summary"


def test_unsupported_question_still_guidance():
    answer = ask("Predict the next SVS result.")
    assert answer["intent"] == "unsupported_question"
    assert answer["guidance_code"] == "unsupported_question"


def test_empty_filters():
    answer = ask(QUESTION_TOP_CONTRIBUTORS, data=sample_data().iloc[0:0])
    assert answer["status"] == "guidance"
    assert answer["guidance_code"] == "empty_player_scope"


def test_one_alliance_scope():
    answer = ask(QUESTION_NET_VS_POSITIVE, data=sample_data()[sample_data()["alliance"] == "AAA"])
    assert answer["guidance_code"] == "requires_multiple_alliances"
    assert answer["metrics"]["alliance_count"] == 1


def test_missing_positive_status():
    data = sample_data()[sample_data()["net_status"] == "Negative"]
    answer = ask(QUESTION_NEGATIVE_PERCENTAGE, data=data)
    assert answer["guidance_code"] == "requires_positive_and_negative_status"


def test_missing_negative_status():
    data = sample_data()[sample_data()["net_status"] == "Positive"]
    answer = ask(QUESTION_NET_VS_POSITIVE, data=data)
    assert answer["guidance_code"] == "requires_positive_and_negative_status"


def test_unknown_alliance_name():
    answer = ask("What is the total net score without ZZZ?", known=["AAA", "BBB", "CCC", "ZZZ"])
    assert answer["guidance_code"] == "alliance_outside_scope"
    assert answer["parameters"]["outside_scope_alliances"] == ["ZZZ"]


def test_multiple_excluded_alliances():
    answer = ask("What is the total net score without AAA and BBB?")
    assert answer["parameters"]["recognized_alliances"] == ["AAA", "BBB"]
    assert answer["metrics"]["after_net_score"] == 500
    rendered = render_dashboard_answer(answer)
    assert "excluding **AAA**, **BBB**" in rendered


def test_no_excluded_players():
    players = sample_data()["player_name"].tolist()
    answer = ask(QUESTION_EXCLUSION_IMPACT, selected=players)
    assert answer["guidance_code"] == "no_excluded_players"
    assert answer["metrics"]["excluded_player_count"] == 0


def test_rendering_remains_available_for_user_answer():
    answer = ask(QUESTION_TOP_CONTRIBUTORS)
    rendered = render_dashboard_answer(answer)
    assert "Players are ranked by" in rendered
    assert "**AAA**" in rendered and "**BBB**" in rendered



def test_structured_answer_is_json_serializable():
    answer = ask("What is the total net score without BBB?")
    encoded = json.dumps(answer)
    assert '"intent": "alliance_exclusion_total_net"' in encoded


def test_new_structured_answers_are_json_serializable():
    data = sample_data().replace({"AAA": "SnS"})
    questions = [
        "Show the best contributors in SnS.",
        "How did player exclusions affect the net score?",
        "Why is the negative percentage lower now?",
        "Which alliance leads net score, and why?",
    ]
    for question in questions:
        answer = ask(question, data=data, selected=["A1", "B1", "C1"])
        json.dumps(answer)


def test_rendering_works_after_original_dataframe_is_discarded():
    data = sample_data()
    answer = calculate_dashboard_answer(QUESTION_TOP_CONTRIBUTORS, data, "SVS Test")
    del data
    rendered = render_dashboard_answer(answer)
    assert "Players are ranked by" in rendered
    assert "**AAA**" in rendered


def test_renderer_uses_structured_values_without_recalculation():
    answer = ask("What is the total net score without BBB?")
    answer["metrics"]["after_net_score"] = 999999
    answer["metrics"]["net_score_change"] = 998499
    rendered = render_dashboard_answer(answer)
    assert "**+999,999**" in rendered
    assert "**+998,499**" in rendered


def test_question_log_supported_question_context_and_json_serializable():
    from ask_dashboard import build_question_log_record

    answer = ask(
        "Why is the negative percentage lower now?",
        selected=["A1", "A2", "B2", "C1"],
    )
    record = build_question_log_record(
        answer,
        selected_alliances=["AAA", "BBB"],
        selected_net_status=["Positive", "Negative"],
        selected_player_count=4,
        total_player_count=5,
        timestamp_utc="2026-07-15T06:30:00Z",
    )

    assert record == {
        "schema_version": 1,
        "timestamp_utc": "2026-07-15T06:30:00Z",
        "question": "Why is the negative percentage lower now?",
        "normalized_question": "why is the negative percentage lower now",
        "intent": "negative_share_change",
        "status": "ok",
        "guidance_code": None,
        "error_code": None,
        "source": "rule",
        "period": "SVS Test",
        "mentioned_alliances": [],
        "requested_direction": "decrease",
        "selected_alliances": ["AAA", "BBB"],
        "selected_net_status": ["Positive", "Negative"],
        "selected_player_count": 4,
        "total_player_count": 5,
        "excluded_player_count": 1,
    }
    json.dumps(record)


def test_question_log_unsupported_question_guidance_code():
    from ask_dashboard import build_question_log_record

    record = build_question_log_record(
        ask("Predict the next SVS result."),
        timestamp_utc="2026-07-15T06:30:00Z",
    )
    assert record["intent"] == "unsupported_question"
    assert record["status"] == "guidance"
    assert record["guidance_code"] == "unsupported_question"


def test_question_log_preserves_mentioned_alliances_and_period():
    from ask_dashboard import build_question_log_record

    data = sample_data().replace({"AAA": "SnS"})
    answer = ask("Show the best contributors in SnS.", data=data)
    record = build_question_log_record(answer, timestamp_utc="2026-07-15T06:30:00Z")
    assert record["mentioned_alliances"] == ["SnS"]
    assert record["period"] == "SVS Test"


def test_question_log_auto_timestamp_is_utc_and_json_serializable():
    from datetime import datetime, timezone
    from ask_dashboard import build_question_log_record

    record = build_question_log_record(ask(QUESTION_NET_VS_POSITIVE))
    timestamp = record["timestamp_utc"]
    assert timestamp.endswith("Z")
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)
    json.dumps(record)


def test_question_log_excludes_dataframes_metrics_rankings_and_player_lists():
    from ask_dashboard import build_question_log_record

    answer = ask(QUESTION_TOP_CONTRIBUTORS)
    record = build_question_log_record(
        answer,
        selected_player_count=3,
        total_player_count=5,
        timestamp_utc="2026-07-15T06:30:00Z",
    )
    encoded = json.dumps(record)
    forbidden_keys = {"metrics", "rankings", "selected_players", "excluded_players", "players"}
    assert forbidden_keys.isdisjoint(record)
    assert "DataFrame" not in encoded
    assert "Series" not in encoded
    assert "A1" not in encoded and "B1" not in encoded and "C1" not in encoded


def test_append_question_log_record_keeps_newest_records():
    from ask_dashboard import append_question_log_record

    records = []
    for index in range(5):
        records = append_question_log_record(records, {"index": index}, max_entries=3)
    assert records == [{"index": 2}, {"index": 3}, {"index": 4}]


@pytest.mark.parametrize("max_entries", [0, -1, 1.5, True, "3"])
def test_append_question_log_record_rejects_invalid_limits(max_entries):
    from ask_dashboard import append_question_log_record

    with pytest.raises(ValueError, match="positive integer"):
        append_question_log_record([], {"index": 1}, max_entries=max_entries)


def test_safe_question_log_helper_resets_malformed_existing_state():
    from ask_dashboard import safely_append_question_log_record

    records, logging_error = safely_append_question_log_record(
        {"unexpected": "state"},
        ask(QUESTION_NET_VS_POSITIVE),
        selected_alliances=["AAA"],
        selected_net_status=["Positive", "Negative"],
        selected_player_count=5,
        total_player_count=5,
        timestamp_utc="2026-07-15T06:30:00Z",
    )

    assert isinstance(records, list)
    assert len(records) == 1
    assert records[0]["intent"] == "net_vs_positive_ranking"
    assert logging_error == "question log state was reset"
    assert render_dashboard_answer(ask(QUESTION_NET_VS_POSITIVE))


def test_safe_question_log_helper_swallows_append_failure_for_rendering_path():
    from ask_dashboard import safely_append_question_log_record

    answer = ask(QUESTION_NET_VS_POSITIVE)

    def failing_appender(records, record, max_entries=100):
        raise RuntimeError("append failed")

    records, logging_error = safely_append_question_log_record(
        [],
        answer,
        record_appender=failing_appender,
        timestamp_utc="2026-07-15T06:30:00Z",
    )

    assert records == []
    assert logging_error == "question logging skipped: RuntimeError"
    assert "Under the current sidebar filters" in render_dashboard_answer(answer)


def test_safe_question_log_helper_swallows_build_failure_for_rendering_path():
    from ask_dashboard import safely_append_question_log_record

    answer = ask(QUESTION_NET_VS_POSITIVE)

    def failing_builder(answer, **kwargs):
        raise RuntimeError("build failed")

    records, logging_error = safely_append_question_log_record(
        [],
        answer,
        record_builder=failing_builder,
        timestamp_utc="2026-07-15T06:30:00Z",
    )

    assert records == []
    assert logging_error == "question logging skipped: RuntimeError"
    assert "Under the current sidebar filters" in render_dashboard_answer(answer)


def test_hybrid_matched_rule_never_calls_ai():
    from ask_dashboard import route_dashboard_question_hybrid

    def fail_ai(*_args):
        raise AssertionError("AI should not be called")

    result = route_dashboard_question_hybrid(
        QUESTION_TOP_CONTRIBUTORS,
        ["AAA"],
        ai_enabled=True,
        ai_extractor=fail_ai,
    )
    assert result["contract"]["source"] == "rule"
    assert result["contract"]["match_status"] == "matched"
    assert result["ai_attempted"] is False
    assert_json_serializable(result)


def test_hybrid_clarification_rule_never_calls_ai():
    from ask_dashboard import route_dashboard_question_hybrid

    def fail_ai(*_args):
        raise AssertionError("AI should not be called")

    result = route_dashboard_question_hybrid(
        "What is the total net score without that alliance?",
        ["AAA"],
        ai_enabled=True,
        ai_extractor=fail_ai,
    )
    assert result["contract"]["match_status"] == "needs_clarification"
    assert result["ai_attempted"] is False


def test_hybrid_unsupported_does_not_call_ai_when_disabled():
    from ask_dashboard import route_dashboard_question_hybrid

    calls = []
    result = route_dashboard_question_hybrid(
        "Predict the next SVS result.",
        ["AAA"],
        ai_enabled=False,
        ai_extractor=lambda *_args: calls.append(True),
    )
    assert calls == []
    assert result["contract"]["match_status"] == "unsupported"
    assert result["ai_attempted"] is False


def test_build_api_intent_contract_maps_only_allowed_parameters():
    from openai_intent import build_api_intent_contract

    contract = build_api_intent_contract(
        {
            "intent": "negative_share_change",
            "requested_direction": "decrease",
            "alliance_names": ["AAA"],
            "excluded_alliances": ["BBB"],
            "match_status": "matched",
            "guidance_code": None,
            "confidence": 0.7,
        }
    )
    assert contract["source"] == "api"
    assert contract["parameters"] == {"requested_direction": "decrease"}
    assert validate_intent_contract(contract) == contract
    assert_json_serializable(contract)

    player_contract = build_api_intent_contract(
        {
            "intent": "player_net_score_leader",
            "requested_direction": "increase",
            "alliance_names": ["AAA"],
            "excluded_alliances": ["BBB"],
            "match_status": "matched",
            "guidance_code": None,
            "confidence": 0.7,
        }
    )
    assert player_contract["parameters"] == {"alliance_names": ["AAA"]}
    assert validate_intent_contract(player_contract) == player_contract
    assert_json_serializable(player_contract)


@pytest.mark.parametrize(
    "candidate",
    [
        "not a dict",
        {
            "intent": "alliance_exclusion_total_net",
            "requested_direction": "unspecified",
            "alliance_names": [],
            "excluded_alliances": [],
            "match_status": "matched",
            "guidance_code": None,
            "confidence": 0.8,
        },
        {
            "intent": "unsupported_question",
            "requested_direction": "unspecified",
            "alliance_names": [],
            "excluded_alliances": [],
            "match_status": "matched",
            "guidance_code": None,
            "confidence": 0.8,
        },
    ],
)
def test_build_api_intent_contract_rejects_invalid_output(candidate):
    from openai_intent import build_api_intent_contract

    with pytest.raises(ValueError):
        build_api_intent_contract(candidate)


def test_successful_ai_fallback_executes_existing_contract_and_logs_api():
    from openai_intent import build_api_intent_contract

    def ai_extractor(_question, _known):
        return build_api_intent_contract(
            {
                "intent": "top_contributors",
                "requested_direction": "unspecified",
                "alliance_names": ["AAA"],
                "excluded_alliances": [],
                "match_status": "matched",
                "guidance_code": None,
                "confidence": 0.66,
            }
        )

    answer = calculate_dashboard_answer(
        "List star performers for AAA",
        sample_data(),
        "SVS Test",
        known_alliance_names=["AAA", "BBB"],
        intent_router=lambda question, known: __import__("ask_dashboard").route_dashboard_question_hybrid(
            question,
            known,
            ai_enabled=True,
            ai_extractor=ai_extractor,
        ),
    )
    assert answer["intent"] == "top_contributors"
    assert answer["routing"]["source"] == "api"
    assert answer["routing_diagnostics"]["ai_attempted"] is True
    record = __import__("ask_dashboard").build_question_log_record(answer, timestamp_utc="2026-07-15T06:30:00Z")
    assert record["source"] == "api"


@pytest.mark.parametrize("exc", [Exception("secret raw provider error"), TimeoutError("slow")])
def test_hybrid_ai_failure_returns_safe_rule_fallback(exc):
    from ask_dashboard import route_dashboard_question_hybrid

    def ai_extractor(*_args):
        raise exc

    result = route_dashboard_question_hybrid(
        "Predict the next SVS result.",
        ["AAA"],
        ai_enabled=True,
        ai_extractor=ai_extractor,
    )
    assert result["contract"]["source"] == "rule"
    assert result["contract"]["match_status"] == "unsupported"
    assert result["ai_attempted"] is True
    assert result["ai_succeeded"] is False
    assert result["diagnostic_code"] == "api_invalid_output"
    assert "secret raw provider error" not in json.dumps(result)


@pytest.mark.parametrize("diagnostic", ["api_unavailable", "api_refusal", "api_incomplete", "api_invalid_output"])
def test_hybrid_preserves_safe_ai_diagnostics(diagnostic):
    from ask_dashboard import route_dashboard_question_hybrid
    from openai_intent import OpenAIIntentError

    def ai_extractor(*_args):
        raise OpenAIIntentError(diagnostic)

    result = route_dashboard_question_hybrid(
        "Predict the next SVS result.",
        ["AAA"],
        ai_enabled=True,
        ai_extractor=ai_extractor,
    )
    assert result["contract"]["source"] == "rule"
    assert result["diagnostic_code"] == diagnostic


def test_invalid_ai_contract_does_not_invoke_calculator(monkeypatch):
    from ask_dashboard import route_dashboard_question_hybrid

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("calculator should not be invoked")

    monkeypatch.setattr("ask_dashboard.calculate_top_contributors", fail_if_called)
    bad_contract = route_dashboard_question(QUESTION_TOP_CONTRIBUTORS, ["AAA"])
    bad_contract["source"] = "api"
    bad_contract["confidence"] = 0.5
    bad_contract["parameters"]["alliance_names"] = [""]
    result = route_dashboard_question_hybrid(
        "Predict the next SVS result.",
        ["AAA"],
        ai_enabled=True,
        ai_extractor=lambda *_args: bad_contract,
    )
    answer = execute_dashboard_intent(result["contract"], sample_data())
    assert answer["intent"] == "unsupported_question"


def test_routing_contract_remains_strict_for_rule_ai_success_failure_and_clarification():
    from ask_dashboard import route_dashboard_question_hybrid
    from openai_intent import OpenAIIntentError, build_api_intent_contract

    def successful_ai(*_args):
        return build_api_intent_contract(
            {
                "intent": "top_contributors",
                "requested_direction": "unspecified",
                "alliance_names": ["AAA"],
                "excluded_alliances": [],
                "match_status": "matched",
                "guidance_code": None,
                "confidence": 0.5,
            }
        )

    scenarios = [
        calculate_dashboard_answer(QUESTION_TOP_CONTRIBUTORS, sample_data(), known_alliance_names=["AAA"]),
        calculate_dashboard_answer(
            "List star performers for AAA",
            sample_data(),
            known_alliance_names=["AAA"],
            intent_router=lambda question, known: route_dashboard_question_hybrid(
                question, known, ai_enabled=True, ai_extractor=successful_ai
            ),
        ),
        calculate_dashboard_answer(
            "Predict the next SVS result.",
            sample_data(),
            known_alliance_names=["AAA"],
            intent_router=lambda question, known: route_dashboard_question_hybrid(
                question,
                known,
                ai_enabled=True,
                ai_extractor=lambda *_args: (_ for _ in ()).throw(OpenAIIntentError("api_unavailable")),
            ),
        ),
        calculate_dashboard_answer(
            "What is the total net score without that alliance?",
            sample_data(),
            known_alliance_names=["AAA"],
            intent_router=lambda question, known: route_dashboard_question_hybrid(
                question, known, ai_enabled=True, ai_extractor=successful_ai
            ),
        ),
    ]
    for answer in scenarios:
        assert validate_intent_contract(answer["routing"]) == answer["routing"]
        assert_json_serializable(answer)


class FakeResponse:
    status = "completed"
    incomplete_details = None

    def __init__(self, output_text):
        self.output_text = output_text


class FakeResponses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeResponse(
            json.dumps(
                {
                    "intent": "top_contributors",
                    "requested_direction": "unspecified",
                    "alliance_names": ["AAA"],
                    "excluded_alliances": [],
                    "match_status": "matched",
                    "guidance_code": None,
                    "confidence": 0.5,
                }
            )
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_openai_extractor_data_minimization_and_strict_schema():
    from openai_intent import extract_intent_contract_with_openai

    client = FakeClient()
    contract = extract_intent_contract_with_openai(
        "Who are AAA stars?",
        ["AAA", "BBB"],
        client=client,
        model="intent-test-model",
    )
    kwargs = client.responses.kwargs
    encoded_input = json.dumps(kwargs["input"])
    assert contract["source"] == "api"
    assert kwargs["store"] is False
    assert kwargs["text"]["format"]["strict"] is True
    assert kwargs["text"]["format"]["schema"]["additionalProperties"] is False
    assert "Who are AAA stars?" in encoded_input
    assert "AAA" in encoded_input and "BBB" in encoded_input
    user_message = next(message for message in kwargs["input"] if message["role"] == "user")
    user_payload = json.loads(user_message["content"])
    assert set(user_payload) == {
        "question",
        "supported_intent_definitions",
        "parameter_rules",
        "known_alliance_names",
    }
    assert user_payload["question"] == "Who are AAA stars?"
    assert user_payload["known_alliance_names"] == ["AAA", "BBB"]

    def all_keys(value):
        if isinstance(value, dict):
            keys = set(value)
            for item in value.values():
                keys.update(all_keys(item))
            return keys
        if isinstance(value, list):
            keys = set()
            for item in value:
                keys.update(all_keys(item))
            return keys
        return set()

    forbidden_data_keys = {
        "score_gained",
        "score_lost",
        "net_score",
        "metrics",
        "rankings",
        "player_name",
        "selected_players",
        "excluded_players",
        "logs",
        "DataFrame",
    }
    assert all_keys(user_payload).isdisjoint(forbidden_data_keys)


def test_openai_extractor_malformed_json_raises_safe_code():
    from openai_intent import AI_DIAGNOSTIC_API_INVALID_OUTPUT, OpenAIIntentError, extract_intent_contract_with_openai

    class BadResponses:
        def create(self, **_kwargs):
            return FakeResponse("not-json")

    class BadClient:
        responses = BadResponses()

    with pytest.raises(OpenAIIntentError) as error:
        extract_intent_contract_with_openai("Question", ["AAA"], client=BadClient(), model="m")
    assert error.value.diagnostic_code == AI_DIAGNOSTIC_API_INVALID_OUTPUT


def test_openai_client_options_are_bounded_and_testable():
    from openai_intent import build_openai_client_options

    assert build_openai_client_options("test-key") == {
        "api_key": "test-key",
        "timeout": 10.0,
        "max_retries": 0,
    }


def test_openai_import_smoke_no_network():
    from openai import OpenAI

    assert OpenAI is not None


def test_extractor_accepts_valid_known_alliance():
    client = FakeClient()
    contract = __import__("openai_intent").extract_intent_contract_with_openai(
        "Who are AAA stars?",
        ["AAA"],
        client=client,
        model="intent-test-model",
    )
    assert contract["parameters"]["alliance_names"] == ["AAA"]


def test_extractor_canonicalizes_known_alliance_case():
    class LowercaseResponses:
        def create(self, **_kwargs):
            return FakeResponse(json.dumps({
                "intent": "top_contributors",
                "requested_direction": "unspecified",
                "alliance_names": ["aaa"],
                "excluded_alliances": [],
                "match_status": "matched",
                "guidance_code": None,
                "confidence": 0.5,
            }))

    class LowercaseClient:
        responses = LowercaseResponses()

    contract = __import__("openai_intent").extract_intent_contract_with_openai(
        "Who are aaa stars?",
        ["AAA"],
        client=LowercaseClient(),
        model="intent-test-model",
    )
    assert contract["parameters"]["alliance_names"] == ["AAA"]


def test_extractor_allows_empty_alliance_arrays_with_empty_known_alliance_list():
    class NoAllianceResponses:
        def create(self, **_kwargs):
            return FakeResponse(json.dumps({
                "intent": "net_score_leader_summary",
                "requested_direction": "unspecified",
                "alliance_names": [],
                "excluded_alliances": [],
                "match_status": "matched",
                "guidance_code": None,
                "confidence": 0.5,
            }))

    class NoAllianceClient:
        responses = NoAllianceResponses()

    contract = __import__("openai_intent").extract_intent_contract_with_openai(
        "Who leads net score?",
        [],
        client=NoAllianceClient(),
        model="intent-test-model",
    )
    assert contract["intent"] == "net_score_leader_summary"


def test_extractor_rejects_invented_alliance_with_safe_code():
    from openai_intent import AI_DIAGNOSTIC_API_INVALID_OUTPUT, OpenAIIntentError, extract_intent_contract_with_openai

    client = FakeClient()
    with pytest.raises(OpenAIIntentError) as error:
        extract_intent_contract_with_openai("Who are AAA stars?", [], client=client, model="intent-test-model")
    assert error.value.diagnostic_code == AI_DIAGNOSTIC_API_INVALID_OUTPUT


def test_extractor_rejects_mixed_valid_and_invented_alliances():
    from openai_intent import AI_DIAGNOSTIC_API_INVALID_OUTPUT, OpenAIIntentError, extract_intent_contract_with_openai

    class MixedResponses:
        def create(self, **_kwargs):
            return FakeResponse(json.dumps({
                "intent": "alliance_exclusion_total_net",
                "requested_direction": "unspecified",
                "alliance_names": [],
                "excluded_alliances": ["AAA", "INVENTED"],
                "match_status": "matched",
                "guidance_code": None,
                "confidence": 0.5,
            }))

    class MixedClient:
        responses = MixedResponses()

    with pytest.raises(OpenAIIntentError) as error:
        extract_intent_contract_with_openai("Net without AAA and INVENTED", ["AAA"], client=MixedClient(), model="m")
    assert error.value.diagnostic_code == AI_DIAGNOSTIC_API_INVALID_OUTPUT


def test_allowlist_failure_falls_back_without_calculator_or_leaking_name(monkeypatch):
    from ask_dashboard import route_dashboard_question_hybrid
    from openai_intent import AI_DIAGNOSTIC_API_INVALID_OUTPUT, OpenAIIntentError

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("calculator should not be invoked")

    monkeypatch.setattr("ask_dashboard.calculate_total_net_excluding_alliances", fail_if_called)

    def extractor(*_args):
        raise OpenAIIntentError(AI_DIAGNOSTIC_API_INVALID_OUTPUT)

    result = route_dashboard_question_hybrid(
        "Net without INVENTED", ["AAA"], ai_enabled=True, ai_extractor=extractor
    )
    answer = execute_dashboard_intent(result["contract"], sample_data())
    assert answer["intent"] == "unsupported_question"
    assert result["diagnostic_code"] == AI_DIAGNOSTIC_API_INVALID_OUTPUT
    assert "INVENTED" not in json.dumps(result)


@pytest.mark.parametrize(
    "candidate",
    [
        {
            "requested_direction": "unspecified",
            "alliance_names": [],
            "excluded_alliances": [],
            "match_status": "matched",
            "guidance_code": None,
            "confidence": 0.5,
        },
        {
            "intent": "top_contributors",
            "requested_direction": "unspecified",
            "alliance_names": [],
            "excluded_alliances": [],
            "match_status": "matched",
            "guidance_code": None,
            "confidence": 0.5,
            "unexpected": "x",
        },
        {
            "intent": "top_contributors",
            "requested_direction": "unspecified",
            "alliance_names": "AAA",
            "excluded_alliances": [],
            "match_status": "matched",
            "guidance_code": None,
            "confidence": 0.5,
        },
    ],
)
def test_build_api_intent_contract_enforces_exact_candidate_schema(candidate):
    from openai_intent import build_api_intent_contract

    with pytest.raises(ValueError):
        build_api_intent_contract(candidate)
