import json

import pandas as pd

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
