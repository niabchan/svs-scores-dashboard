import json

import pandas as pd
import pytest

from ask_dashboard import (
    QUESTION_EXCLUSION_IMPACT,
    QUESTION_NEGATIVE_PERCENTAGE,
    QUESTION_NET_VS_POSITIVE,
    QUESTION_TOP_CONTRIBUTORS,
    calculate_dashboard_answer,
    render_dashboard_answer,
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
        "Who has the top net score?",
        "Which alliance has the highest net score?",
        "Who is the net score winner?",
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
