import pandas as pd
import pytest

from ask_dashboard import (
    calculate_dashboard_answer,
    render_dashboard_answer,
    route_dashboard_question,
    route_dashboard_question_hybrid,
)


@pytest.mark.parametrize(
    "question",
    [
        "Who is the best player?",
        "¿Quién es el mejor jugador?",
        "Qui est le meilleur joueur ?",
        "Ai là người chơi tốt nhất?",
        "Siapa pemain terbaik?",
        "ใครเก่งที่สุด",
    ],
)
def test_multilingual_best_player_questions_route_to_player_net_leader(question):
    contract = route_dashboard_question(question, ["MBV", "NoM", "SnS", "TDA"])
    assert contract["intent"] == "player_net_score_leader"
    assert contract["parameters"] == {"alliance_names": []}
    assert contract["source"] == "rule"


@pytest.mark.parametrize(
    "question",
    [
        "Who is the best contributor?",
        "¿Quién es el mejor contribuyente?",
        "Qui est le meilleur contributeur ?",
        "Ai đóng góp nhiều nhất?",
        "Siapa kontributor terbaik?",
        "ใครมีส่วนร่วมมากที่สุด",
    ],
)
def test_multilingual_best_contributor_questions_route_to_single_player(question):
    contract = route_dashboard_question(question, ["MBV", "NoM", "SnS", "TDA"])
    assert contract["intent"] == "top_contributors"
    assert contract["parameters"] == {
        "alliance_names": [],
        "mode": "leader",
    }
    assert contract["source"] == "rule"


def test_spanish_grouped_contributor_request_stays_grouped():
    contract = route_dashboard_question(
        "Mostrar los principales contribuyentes de cada alianza seleccionada.",
        ["MBV", "NoM", "SnS", "TDA"],
    )
    assert contract["intent"] == "top_contributors"
    assert contract["parameters"] == {"alliance_names": []}


def test_reported_spanish_questions_do_not_need_ai_routing():
    calls = []

    def extractor(*args):
        calls.append(args)
        raise AssertionError("supported multilingual question should not call AI")

    for question, expected_intent in [
        ("¿Quién es el mejor jugador?", "player_net_score_leader"),
        ("¿Quién es el mejor contribuyente?", "top_contributors"),
    ]:
        routed = route_dashboard_question_hybrid(
            question,
            ["MBV", "NoM", "SnS", "TDA"],
            ai_enabled=True,
            ai_extractor=extractor,
        )
        assert routed["contract"]["intent"] == expected_intent
        assert routed["contract"]["source"] == "rule"
        assert routed["ai_attempted"] is False
    assert calls == []


def test_reported_spanish_best_contributor_renders_one_global_player():
    data = pd.DataFrame(
        [
            {
                "alliance": "MBV",
                "player_name": "Alpha",
                "score_gained": 1_000,
                "score_lost": 200,
                "net_score": 800,
                "net_status": "Positive",
            },
            {
                "alliance": "NoM",
                "player_name": "Beta",
                "score_gained": 1_500,
                "score_lost": 100,
                "net_score": 1_400,
                "net_status": "Positive",
            },
            {
                "alliance": "SnS",
                "player_name": "Gamma",
                "score_gained": 500,
                "score_lost": 900,
                "net_score": -400,
                "net_status": "Negative",
            },
        ]
    )
    answer = calculate_dashboard_answer(
        "¿Quién es el mejor contribuyente?",
        data,
        "2026-W31",
        known_alliance_names=["MBV", "NoM", "SnS"],
    )
    assert answer["intent"] == "top_contributors"
    assert answer["metrics"]["mode"] == "leader"
    assert answer["metrics"]["leaders"][0]["player_name"] == "Beta"

    rendered = render_dashboard_answer(answer, locale="es")
    assert "**Beta**" in rendered
    assert "mayor contribución positiva" in rendered
    assert "**MBV** —" not in rendered
    assert "**NoM** —" not in rendered


def test_reported_thai_best_question_resolves_player_not_alliance():
    data = pd.DataFrame(
        [
            {
                "alliance": "AAA",
                "player_name": "Player A",
                "score_gained": 1_000,
                "score_lost": 100,
                "net_score": 900,
            },
            {
                "alliance": "BBB",
                "player_name": "Player B",
                "score_gained": 2_000,
                "score_lost": 1_500,
                "net_score": 500,
            },
        ]
    )
    answer = calculate_dashboard_answer(
        "ใครเก่งที่สุด",
        data,
        "2026-W31",
        known_alliance_names=["AAA", "BBB"],
    )
    assert answer["intent"] == "player_net_score_leader"
    assert answer["metrics"]["leaders"][0]["player_name"] == "Player A"


@pytest.mark.parametrize(
    "question",
    [
        "ใครเก่งที่สุด",
        "รอบนี้ใครเก่งที่สุด",
        "ถ้าดูจากคะแนนใครเก่งที่สุด",
        "ถ้าดูจากคะแนนแล้ว ใครเก่งที่สุด?",
        "ใครทำคะแนนสุทธิสูงที่สุด",
    ],
)
def test_thai_best_player_natural_variants_route_to_player_net_leader(question):
    contract = route_dashboard_question(question, ["MBV", "NoM", "SnS", "TDA"])
    assert contract["intent"] == "player_net_score_leader"
    assert contract["parameters"] == {"alliance_names": []}
    assert contract["source"] == "rule"


@pytest.mark.parametrize(
    "question",
    [
        "ใครมีส่วนร่วมมากที่สุด",
        "รอบนี้ใครมีส่วนร่วมมากที่สุด",
        "ถ้าดูจากผลงาน ใครมีส่วนร่วมมากที่สุด?",
    ],
)
def test_thai_best_contributor_natural_variants_route_to_single_player(question):
    contract = route_dashboard_question(question, ["MBV", "NoM", "SnS", "TDA"])
    assert contract["intent"] == "top_contributors"
    assert contract["parameters"] == {
        "alliance_names": [],
        "mode": "leader",
    }
    assert contract["source"] == "rule"


def test_thai_named_alliance_best_player_routes_with_alliance_scope():
    contract = route_dashboard_question(
        "TDA มีใครทำคะแนนดีที่สุด",
        ["MBV", "NoM", "SnS", "TDA"],
    )
    assert contract["intent"] == "player_net_score_leader"
    assert contract["parameters"] == {"alliance_names": ["TDA"]}
    assert contract["source"] == "rule"


def test_thai_named_alliance_best_contributor_preserves_named_scope():
    contract = route_dashboard_question(
        "ใน TDA ใครมีส่วนร่วมมากที่สุด",
        ["MBV", "NoM", "SnS", "TDA"],
    )
    assert contract["intent"] == "top_contributors"
    assert contract["parameters"] == {"alliance_names": ["TDA"]}
    assert contract["source"] == "rule"
