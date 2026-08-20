from string import Formatter

from ask_dashboard import SUGGESTED_QUESTIONS
from ui_copy import (
    ASK_UI_TEXT,
    FEEDBACK_CHOICES,
    FEEDBACK_REASON_CODES,
    FEEDBACK_REASON_KEYS,
    SUGGESTED_QUESTION_KEYS,
    SUPPORTED_UI_LOCALES,
    feedback_choice_label,
    feedback_reason_label,
    suggested_question_label,
    ui_text,
)


def _format_fields(value):
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(value)
        if field_name
    }


def test_ask_ui_locales_are_exactly_supported_dashboard_locales():
    assert set(ASK_UI_TEXT) == set(SUPPORTED_UI_LOCALES)
    assert set(SUPPORTED_UI_LOCALES) == {"en", "es", "fr", "vi", "id"}


def test_every_ask_ui_locale_has_exactly_the_english_key_set():
    english_keys = set(ASK_UI_TEXT["en"])

    for locale, copy in ASK_UI_TEXT.items():
        assert set(copy) == english_keys, locale
        assert all(isinstance(value, str) and value.strip() for value in copy.values())


def test_format_fields_match_english_for_every_locale():
    for key, english_value in ASK_UI_TEXT["en"].items():
        english_fields = _format_fields(english_value)
        for locale, copy in ASK_UI_TEXT.items():
            assert _format_fields(copy[key]) == english_fields, f"{locale}.{key}"


def test_current_scope_formats_without_changing_runtime_values():
    rendered = ui_text(
        "es",
        "current_scope",
        svs="2026-W31",
        alliances="SnS, TDA",
        net_status="Positive, Negative",
        included=17,
        total=24,
    )

    assert "2026-W31" in rendered
    assert "SnS, TDA" in rendered
    assert "Positive, Negative" in rendered
    assert "17/24" in rendered


def test_suggested_question_display_labels_cover_canonical_questions():
    assert set(SUGGESTED_QUESTION_KEYS) == set(SUGGESTED_QUESTIONS)

    for question in SUGGESTED_QUESTIONS:
        assert suggested_question_label("en", question)
        assert suggested_question_label("fr", question)
        # Display localization must not mutate the canonical routing value.
        assert question in SUGGESTED_QUESTION_KEYS


def test_feedback_display_labels_keep_stable_internal_codes():
    assert FEEDBACK_CHOICES == ("choose", "helpful", "not_helpful")
    assert set(FEEDBACK_REASON_CODES) == set(FEEDBACK_REASON_KEYS)
    assert FEEDBACK_REASON_CODES["reason_misunderstood"] == "misunderstood_question"
    assert FEEDBACK_REASON_CODES["reason_incorrect"] == "wrong_answer"
    assert FEEDBACK_REASON_CODES["reason_unsupported"] == "unsupported_question"
    assert FEEDBACK_REASON_CODES["reason_unclear"] == "unclear_answer"
    assert FEEDBACK_REASON_CODES["reason_other"] == "other"

    for locale in SUPPORTED_UI_LOCALES:
        for choice in FEEDBACK_CHOICES:
            assert feedback_choice_label(locale, choice)
        for reason in FEEDBACK_REASON_KEYS:
            assert feedback_reason_label(locale, reason)


def test_unknown_locale_falls_back_to_english():
    assert ui_text("xx", "explain") == ui_text("en", "explain")
