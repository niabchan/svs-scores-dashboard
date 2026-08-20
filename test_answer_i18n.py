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
from ui_copy import SUPPORTED_UI_LOCALES


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
    expected_language_markers = {
        "es": "contribución positiva",
        "fr": "contribution positive",
        "vi": "đóng góp tích cực",
        "id": "kontribusi positif",
    }
    for locale, marker in expected_language_markers.items():
        rendered = render_dashboard_answer(answer, locale=locale)
        assert "SnS" in rendered
        assert "TDA" in rendered
        assert "1,200" in rendered
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
