import pandas as pd

from ask_dashboard import calculate_dashboard_answer, render_dashboard_answer


def test_alliance_net_score_question_stays_focused_on_filtered_ranking():
    filtered_data = pd.DataFrame(
        [
            {
                "alliance": "NoM",
                "player_name": "N1",
                "score_gained": 500,
                "score_lost": 100,
                "net_score": 400,
            },
            {
                "alliance": "SnS",
                "player_name": "S1",
                "score_gained": 300,
                "score_lost": 200,
                "net_score": 100,
            },
        ]
    )

    answer = calculate_dashboard_answer(
        "How are the alliance net scores this SVS?",
        filtered_data,
        svs_period="2026-W25",
        known_alliance_names=["NoM", "SnS", "TDA"],
    )
    rendered = render_dashboard_answer(answer)

    assert answer["intent"] == "net_score_leader_summary"
    assert "Under the current sidebar filters in 2026-W25" in rendered
    assert "**Alliance net-score ranking — current filters**" in rendered
    assert "1. **NoM** — **+400**" in rendered
    assert "2. **SnS** — **+100**" in rendered
    assert "TDA" not in rendered
    assert "Leader breakdown" not in rendered
    assert "Positive contribution" not in rendered
    assert "Negative impact" not in rendered
    assert "selected SVS period" in rendered
    assert "does not default to the latest SVS" in rendered
