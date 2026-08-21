from ask_dashboard import (
    ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
    render_dashboard_answer,
)
from ask_dashboard._answer_i18n import (
    ANSWER_TEXT,
    LOCALIZED_RENDERED_INTENTS,
    SUPPORTED_LOCALIZED_ANSWER_LOCALES,
    validate_answer_copy_parity,
)
from ask_dashboard._routing import SUPPORTED_DASHBOARD_INTENTS
from ui_copy import ASK_UI_TEXT, SUPPORTED_UI_LOCALES


def _alliance_positive_answer(period="2026-W28"):
    leader = {
        "alliance": "SnS",
        "positive_contribution": 1200,
        "negative_impact": 300,
        "total_net_score": 900,
        "share_of_scope_positive": 60.0,
        "rank": 1,
    }
    second = {
        "alliance": "TDA",
        "positive_contribution": 800,
        "negative_impact": 500,
        "total_net_score": 300,
        "share_of_scope_positive": 40.0,
        "rank": 2,
    }
    return {
        "intent": ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
        "status": "ok",
        "period": period,
        "parameters": {},
        "metrics": {
            "scope": "current_filters",
            "leader_count": 1,
            "top_positive_contribution": 1200,
            "total_positive_contribution": 2000,
            "alliance_count": 2,
            "leaders": [leader],
        },
        "rankings": {"alliances": [leader, second]},
    }


def test_localized_answer_locales_match_non_english_ui_locales():
    assert set(SUPPORTED_LOCALIZED_ANSWER_LOCALES) == set(SUPPORTED_UI_LOCALES) - {"en"}


def test_localized_answer_copy_contract_is_valid():
    validate_answer_copy_parity()
    reference_keys = set(ANSWER_TEXT[SUPPORTED_LOCALIZED_ANSWER_LOCALES[0]])
    for locale in SUPPORTED_LOCALIZED_ANSWER_LOCALES:
        assert set(ANSWER_TEXT[locale]) == reference_keys


def test_localized_renderer_covers_all_supported_dashboard_intents():
    assert set(SUPPORTED_DASHBOARD_INTENTS).issubset(LOCALIZED_RENDERED_INTENTS)


def test_default_and_explicit_english_rendering_are_identical():
    answer = _alliance_positive_answer()
    assert render_dashboard_answer(answer) == render_dashboard_answer(answer, locale="en")


def test_unknown_locale_falls_back_to_established_english_renderer():
    answer = _alliance_positive_answer()
    assert render_dashboard_answer(answer, locale="th") == render_dashboard_answer(answer)


def test_dashboard_help_is_rendered_in_selected_locale():
    answer = {
        "intent": "dashboard_help",
        "status": "ok",
        "parameters": {"question": "What can I ask?"},
    }
    expected_markers = {
        "es": "## Cómo usar Ask Dashboard",
        "fr": "## Comment utiliser Ask Dashboard",
        "vi": "## Cách sử dụng Ask Dashboard",
        "id": "## Cara menggunakan Ask Dashboard",
    }
    for locale, marker in expected_markers.items():
        rendered = render_dashboard_answer(answer, locale=locale)
        assert marker in rendered
        assert "## How to use Ask Dashboard" not in rendered


def test_metric_definition_is_localized_without_changing_metric_value_semantics():
    answer = {
        "intent": "dashboard_help",
        "status": "ok",
        "parameters": {"question": "What is net score?"},
    }
    expected = {
        "es": "**Puntuación neta**",
        "fr": "**Score net**",
        "vi": "**Điểm ròng**",
        "id": "**Poin bersih**",
    }
    for locale, marker in expected.items():
        rendered = render_dashboard_answer(answer, locale=locale)
        assert marker in rendered
        assert "−" in rendered


def test_localized_dynamic_answer_preserves_names_and_numbers():
    answer = _alliance_positive_answer()
    expected = {
        "es": ("contribución positiva", "1.200"),
        "fr": ("contribution positive", "1\u202f200"),
        "vi": ("đóng góp tích cực", "1.200"),
        "id": ("kontribusi positif", "1.200"),
    }
    for locale, (marker, formatted_number) in expected.items():
        rendered = render_dashboard_answer(answer, locale=locale)
        assert "SnS" in rendered
        assert "TDA" in rendered
        assert formatted_number in rendered
        assert marker.casefold() in rendered.casefold()


def test_unsupported_smalltalk_guidance_is_localized():
    answer = {
        "intent": "unsupported_question",
        "status": "guidance",
        "guidance_code": "unsupported_question",
        "parameters": {"question": "hello"},
    }
    expected = {
        "es": "¡Hola!",
        "fr": "Bonjour !",
        "vi": "Xin chào!",
        "id": "Halo!",
    }
    for locale, marker in expected.items():
        assert marker in render_dashboard_answer(answer, locale=locale)


def test_rounded_score_notice_is_localized():
    answer = _alliance_positive_answer(period="2026-W29")
    expected = {
        "es": "Nota sobre los datos",
        "fr": "Note sur les données",
        "vi": "Lưu ý về dữ liệu",
        "id": "Catatan data",
    }
    for locale, marker in expected.items():
        rendered = render_dashboard_answer(answer, locale=locale)
        assert marker in rendered
        assert "Data note:" not in rendered


def test_app_passes_selected_ui_locale_to_answer_renderer():
    source = open("app.py", encoding="utf-8").read()
    assert "render_dashboard_answer(\n            answer,\n            locale=st.session_state.get(\"lang\", \"en\"),\n        )" in source


def test_app_does_not_show_a_stale_answer_after_ui_locale_changes():
    source = open("app.py", encoding="utf-8").read()
    assert 'st.session_state["ask_dashboard_last_answer_locale"] = st.session_state.get("lang", "en")' in source
    assert 'last_answer_locale = st.session_state.get("ask_dashboard_last_answer_locale")' in source
    assert 'and last_answer_locale == st.session_state.get("lang", "en")' in source


def test_localized_help_marks_english_examples_as_exact_input_language():
    answer = {
        "intent": "dashboard_help",
        "status": "ok",
        "parameters": {"question": "Hello. Can you help me?"},
    }
    markers = {
        "es": ("escríbelas en inglés", "comandos en inglés"),
        "fr": ("à saisir en anglais", "commandes en anglais"),
        "vi": ("nhập bằng tiếng Anh", "lệnh tiếng Anh"),
        "id": ("ketik dalam bahasa Inggris", "perintah bahasa Inggris"),
    }
    for locale, (example_marker, command_marker) in markers.items():
        rendered = render_dashboard_answer(answer, locale=locale)
        assert example_marker in rendered
        assert command_marker in rendered
        assert "Which alliance leads net score?" in rendered
        assert "`help filters`" in rendered


def test_indonesian_help_copy_is_polished_without_changing_capability_boundary():
    answer = {
        "intent": "dashboard_help",
        "status": "ok",
        "parameters": {"question": "Hello. Can you help me?"},
    }
    rendered = render_dashboard_answer(answer, locale="id")
    assert "Ask Dashboard dapat membantu menjelaskan" in rendered
    assert "kontribusi positif dan dampak negatif" in rendered
    assert "hasil skor yang tercatat, tetapi tidak dapat menentukan" in rendered
    assert "Ask Dashboard menjelaskan hasil poin yang tercatat. Ask Dashboard" not in rendered


def test_localized_answers_use_locale_number_punctuation():
    answer = _alliance_positive_answer()
    es = render_dashboard_answer(answer, locale="es")
    fr = render_dashboard_answer(answer, locale="fr")
    vi = render_dashboard_answer(answer, locale="vi")
    id_rendered = render_dashboard_answer(answer, locale="id")

    assert "1.200" in es
    assert "60,0\u202f%" in es
    assert "1\u202f200" in fr
    assert "60,0\u202f%" in fr
    assert "1.200" in vi
    assert "60,0%" in vi
    assert "1.200" in id_rendered
    assert "60,0%" in id_rendered
    for rendered in (es, fr, vi, id_rendered):
        assert "1,200" not in rendered


def test_french_cleanup_avoids_translation_calques():
    assert "magnitude" not in ANSWER_TEXT["fr"]["metric_lost"].casefold()
    assert "magnitude" not in ANSWER_TEXT["fr"]["metric_negative"].casefold()
    assert "gains utiles" not in ANSWER_TEXT["fr"]["outcome_improved"].casefold()
    assert ANSWER_TEXT["fr"]["negative_formula"].startswith("Part négative")


def test_vietnamese_cleanup_uses_consistent_negative_share_terminology():
    assert "độ lớn" not in ANSWER_TEXT["vi"]["negative_no_magnitude"].casefold()
    assert "độ lớn" not in ANSWER_TEXT["vi"]["negative_after_none"].casefold()
    assert ANSWER_TEXT["vi"]["negative_formula"].startswith("Tỷ trọng tiêu cực")
    assert "người có đóng góp tích cực lớn nhất" in ANSWER_TEXT["vi"]["player_positive_single"]


def test_french_ranking_selector_has_no_top_bottom_english_leakage():
    source = open("app.py", encoding="utf-8").read()
    assert '"top_10_net_score": "Top 10 score net"' not in source
    assert '"bottom_10_net_score": "Bottom 10 score net"' not in source
    assert '"top_10_net_score": "10 scores nets les plus élevés"' in source
    assert '"bottom_10_net_score": "10 scores nets les plus faibles"' in source


def test_spanish_cleanup_avoids_translation_calques():
    assert "magnitud" not in ANSWER_TEXT["es"]["metric_lost"].casefold()
    assert "magnitud" not in ANSWER_TEXT["es"]["metric_negative"].casefold()
    assert "aporte útil" not in ANSWER_TEXT["es"]["outcome_decreased"].casefold()
    assert ANSWER_TEXT["es"]["negative_formula"].startswith("Participación negativa")
    assert "mayor contribución positiva" in ANSWER_TEXT["es"]["player_positive_single"]


def test_indonesian_cleanup_avoids_translation_calques():
    assert "besaran" not in ANSWER_TEXT["id"]["metric_lost"].casefold()
    assert "besaran" not in ANSWER_TEXT["id"]["negative_no_magnitude"].casefold()
    assert "kontribusi bermanfaat" not in ANSWER_TEXT["id"]["outcome_decreased"].casefold()
    assert "dampak negatif mentah" not in ANSWER_TEXT["id"]["negative_reason_increase_down"].casefold()
    assert ANSWER_TEXT["id"]["negative_formula"].startswith("Persentase dampak negatif")
    assert "kontribusi positif terbesar" in ANSWER_TEXT["id"]["player_positive_single"]


def test_custom_question_guidance_is_consolidated_into_placeholder():
    for locale in SUPPORTED_UI_LOCALES:
        assert "custom_question_help" not in ASK_UI_TEXT[locale]
        placeholder = ASK_UI_TEXT[locale]["question_placeholder"]
        assert "help" in placeholder.casefold()
        assert len(placeholder) > 60

    source = open("app.py", encoding="utf-8").read()
    assert 'st.caption(ask_t("custom_question_help"))' not in source
    assert ASK_UI_TEXT["en"]["analytics_privacy"] == "Usage analytics & privacy"


def test_spanish_top_contributor_copy_and_group_summary_spacing():
    answer = {
        "intent": "top_contributors",
        "status": "ok",
        "period": None,
        "parameters": {},
        "metrics": {"mode": "ranking", "top_n": 2},
        "rankings": {
            "alliances": [
                {
                    "alliance": "MBV",
                    "positive_total": 2000,
                    "net_total": -300,
                    "players": [
                        {
                            "player_name": "Alpha",
                            "net_score": 1200,
                            "score_gained": 1500,
                            "score_lost": 300,
                            "share_of_positive": 60.0,
                        },
                        {
                            "player_name": "Beta",
                            "net_score": 800,
                            "score_gained": 1000,
                            "score_lost": 200,
                            "share_of_positive": 40.0,
                        },
                    ],
                },
                {
                    "alliance": "NoM",
                    "positive_total": 500,
                    "net_total": 400,
                    "players": [
                        {
                            "player_name": "Gamma",
                            "net_score": 500,
                            "score_gained": 600,
                            "score_lost": 100,
                            "share_of_positive": 100.0,
                        }
                    ],
                },
            ]
        },
    }
    rendered = render_dashboard_answer(answer, locale="es")
    assert "Con **2 alianzas** seleccionadas" in rendered
    assert "según su **puntuación neta**" in rendered
    assert "**MBV** — contribuyentes con puntuación neta positiva:" in rendered
    assert "puntuación neta **+1.200**" in rendered
    assert "\n\nLos jugadores mostrados representan el **100,0\u202f%**" in rendered
    assert "\n\nPuntuación neta total de la alianza" in rendered
