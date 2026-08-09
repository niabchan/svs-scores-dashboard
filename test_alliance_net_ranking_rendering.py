import pandas as pd

from ask_dashboard import calculate_dashboard_answer, render_dashboard_answer


def _alliance_scores():
    return pd.DataFrame(
        [
            {
                "alliance": "NoM",
                "player_name": "N1",
                "score_gained": 3_500,
                "score_lost": 500,
                "net_score": 3_000,
            },
            {
                "alliance": "SnS",
                "player_name": "S1",
                "score_gained": 2_600,
                "score_lost": 600,
                "net_score": 2_000,
            },
            {
                "alliance": "TDA",
                "player_name": "T1",
                "score_gained": 300,
                "score_lost": 700,
                "net_score": -400,
            },
        ]
    )


def test_alliance_net_question_renders_full_ranking_for_selected_period():
    answer = calculate_dashboard_answer(
        "How are the alliance net scores this SVS?",
        _alliance_scores(),
        svs_period="2026-W27",
    )
    rendered = render_dashboard_answer(answer)

    assert answer["intent"] == "net_score_leader_summary"
    assert "Under the current sidebar filters in 2026-W27" in rendered
    assert "**Alliance net-score ranking — current filters**" in rendered
    assert "1. **NoM** — **+3,000**" in rendered
    assert "2. **SnS** — **+2,000**" in rendered
    assert "3. **TDA** — **-400**" in rendered
    assert "Leader breakdown" not in rendered
    assert "Positive contribution:" not in rendered
    assert "Negative impact:" not in rendered
    assert "Positive-contribution rank is a separate metric" in rendered
    assert "selected SVS period" in rendered
    assert "does not default to the latest SVS" in rendered
    assert "2026-W29" not in rendered


def test_alliance_net_ranking_contains_only_rows_left_by_current_filters():
    filtered = _alliance_scores()[_alliance_scores()["alliance"].isin(["SnS", "TDA"])]
    answer = calculate_dashboard_answer(
        "How are the alliance net scores this SVS?",
        filtered,
        svs_period="2026-W25",
    )
    rendered = render_dashboard_answer(answer)

    assert "1. **SnS** — **+2,000**" in rendered
    assert "2. **TDA** — **-400**" in rendered
    assert "NoM" not in rendered
    assert "current sidebar filters" in rendered


def test_leader_question_uses_the_same_deterministic_ranking_renderer():
    wrapper = calculate_dashboard_answer(
        "Which alliance leads net score, and why?",
        _alliance_scores(),
        svs_period="2026-W27",
    )
    rendered = render_dashboard_answer(wrapper)

    assert "1. **NoM** — **+3,000**" in rendered
    assert "Leader breakdown" not in rendered
    assert "Positive-contribution rank is a separate metric" in rendered
