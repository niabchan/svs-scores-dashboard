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
    rendered = render_dashboard_answer(answer)
    assert isinstance(rendered, str)
    assert rendered
    return rendered


def test_suggested_net_vs_positive_question():
    text = ask(QUESTION_NET_VS_POSITIVE)
    assert "ranks first in total net score" in text
    assert "positive contribution" in text


def test_suggested_exclusion_impact_question():
    text = ask(QUESTION_EXCLUSION_IMPACT, selected=["A1", "B1", "C1"])
    assert "Excluded:" in text
    assert "A2" in text and "B2" in text


def test_suggested_negative_percentage_question():
    text = ask(QUESTION_NEGATIVE_PERCENTAGE, selected=["A1", "B1", "C1"])
    assert "negative share" in text.casefold()
    assert "Negative percentage" in text


def test_suggested_top_contributors_question():
    text = ask(QUESTION_TOP_CONTRIBUTORS)
    assert "Players are ranked by" in text
    assert "**AAA**" in text and "**BBB**" in text


def test_custom_total_net_without_named_alliance():
    text = ask("What is the total net score without BBB?")
    assert "excluding **BBB** changes total net score" in text
    assert "Score gained" in text


def test_custom_top_contributors_for_named_alliance():
    text = ask("Who contributed most in AAA?")
    assert "**AAA**" in text
    assert "**BBB**" not in text


def test_custom_selected_player_exclusion_pattern():
    text = ask("How did excluding selected players change the result?", selected=["A1", "B1", "C1"])
    assert "After the current exclusions" in text


def test_custom_negative_share_pattern():
    text = ask("Why did the negative share rise?", selected=["A1", "A2", "B2", "C1"])
    assert "Negative percentage" in text


def test_custom_ranking_pattern():
    text = ask("Why is the net-score leader not first in positive contribution?")
    assert "total net score" in text


def test_empty_filters():
    text = ask(QUESTION_TOP_CONTRIBUTORS, data=sample_data().iloc[0:0])
    assert "There is no player score data" in text


def test_one_alliance_scope():
    text = ask(QUESTION_NET_VS_POSITIVE, data=sample_data()[sample_data()["alliance"] == "AAA"])
    assert "needs at least two alliances" in text


def test_missing_positive_status():
    data = sample_data()[sample_data()["net_status"] == "Negative"]
    text = ask(QUESTION_NEGATIVE_PERCENTAGE, data=data)
    assert "does not include both Positive and Negative" in text


def test_missing_negative_status():
    data = sample_data()[sample_data()["net_status"] == "Positive"]
    text = ask(QUESTION_NET_VS_POSITIVE, data=data)
    assert "does not include both Positive and Negative" in text


def test_unknown_alliance_name():
    text = ask("What is the total net score without ZZZ?", known=["AAA", "BBB", "CCC", "ZZZ"])
    assert "**ZZZ** is not included" in text


def test_multiple_excluded_alliances():
    text = ask("What is the total net score without AAA and BBB?")
    assert "excluding **AAA**, **BBB**" in text
    assert "Players remaining" in text


def test_no_excluded_players():
    players = sample_data()["player_name"].tolist()
    text = ask(QUESTION_EXCLUSION_IMPACT, selected=players)
    assert "No players are currently excluded" in text
