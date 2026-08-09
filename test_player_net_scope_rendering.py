import pandas as pd

from ask_dashboard import calculate_dashboard_answer, render_dashboard_answer


def test_named_alliance_player_leader_shows_only_the_scoped_player_ranking():
    data = pd.DataFrame(
        [
            {
                "alliance": "SnS",
                "player_name": "PEQ",
                "score_gained": 5_000_000_000,
                "score_lost": 4_666_344_448,
                "net_score": 333_655_552,
            },
            {
                "alliance": "SnS",
                "player_name": "Second",
                "score_gained": 700_000_000,
                "score_lost": 500_000_000,
                "net_score": 200_000_000,
            },
            {
                "alliance": "SnS",
                "player_name": "Third",
                "score_gained": 600_000_000,
                "score_lost": 500_000_000,
                "net_score": 100_000_000,
            },
            {
                "alliance": "SnS",
                "player_name": "Negative",
                "score_gained": 100_000_000,
                "score_lost": 300_000_000,
                "net_score": -200_000_000,
            },
            {
                "alliance": "NoM",
                "player_name": "NoMLeader",
                "score_gained": 1_500_000_000,
                "score_lost": 0,
                "net_score": 1_500_000_000,
            },
        ]
    )

    answer = calculate_dashboard_answer(
        "Which SnS player had the best overall result?",
        data,
        svs_period="2026-W31",
        known_alliance_names=["SnS", "NoM"],
    )
    rendered = render_dashboard_answer(answer)

    assert answer["intent"] == "player_net_score_leader"
    assert answer["parameters"]["matched_alliances"] == ["SnS"]
    assert "**PEQ** has the highest player net score" in rendered
    assert "**Top players in SnS by net score**" in rendered
    assert "1. **PEQ** — **+333,655,552**" in rendered
    assert "2. **Second** — **+200,000,000**" in rendered
    assert "3. **Third** — **+100,000,000**" in rendered
    assert "NoMLeader" not in rendered
    assert "ranks players only within **SnS**" in rendered
    assert "does not compare SnS’s total alliance net score" in rendered


def test_unscoped_player_leader_labels_alliances_and_separates_alliance_totals():
    data = pd.DataFrame(
        [
            {
                "alliance": "SnS",
                "player_name": "Alpha",
                "score_gained": 1_000,
                "score_lost": 100,
                "net_score": 900,
            },
            {
                "alliance": "NoM",
                "player_name": "Beta",
                "score_gained": 900,
                "score_lost": 100,
                "net_score": 800,
            },
        ]
    )

    answer = calculate_dashboard_answer(
        "Who finished with the strongest overall balance among the players?",
        data,
        svs_period="2026-W31",
    )
    rendered = render_dashboard_answer(answer)

    assert "**Top players by net score under the current filters**" in rendered
    assert "1. **Alpha** (SnS) — **+900**" in rendered
    assert "2. **Beta** (NoM) — **+800**" in rendered
    assert "does not identify which alliance has the highest combined net score" in rendered
