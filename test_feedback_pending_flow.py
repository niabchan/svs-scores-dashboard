from pathlib import Path

from ui_copy import ASK_UI_TEXT, SUPPORTED_UI_LOCALES


APP_SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_pending_answer_event_still_exposes_feedback_controls():
    assert "feedback_target_id = last_answer_event_id" in APP_SOURCE
    assert 'feedback_target_id = pending_answer_event.get("event_id")' in APP_SOURCE
    assert 'key=f"ask_dashboard_feedback_choice_{feedback_target_id}"' in APP_SOURCE
    assert 'key=f"ask_dashboard_feedback_submit_{feedback_target_id}"' in APP_SOURCE


def test_pending_analytics_plumbing_is_not_exposed_as_answer_ui():
    assert 'st.info(ask_t("feedback_pending"))' not in APP_SOURCE
    assert 'ask_t("retry_analytics")' not in APP_SOURCE
    assert 'ask_t("retry_failed")' not in APP_SOURCE

    for locale in SUPPORTED_UI_LOCALES:
        copy = ASK_UI_TEXT[locale]
        assert "feedback_pending" not in copy
        assert "retry_analytics" not in copy
        assert "retry_failed" not in copy


def test_feedback_submit_retries_pending_answer_before_feedback_event():
    submit_marker = 'if st.button(\n                    ask_t("submit_feedback")'
    submit_index = APP_SOURCE.index(submit_marker)
    retry_index = APP_SOURCE.index(
        "_persist_preview_analytics(\n                                pending_answer_event",
        submit_index,
    )
    build_index = APP_SOURCE.index(
        "build_feedback_event(\n                                confirmed_answer_event_id",
        submit_index,
    )
    assert retry_index < build_index
    assert 'st.warning(ask_t("feedback_delivery_failed"))' in APP_SOURCE[submit_index:]


def test_feedback_failure_copy_is_user_facing_not_analytics_facing():
    forbidden = {
        "en": ("analytics", "connection"),
        "es": ("analítica", "conexión"),
        "fr": ("analytique", "connexion"),
        "vi": ("phân tích", "kết nối"),
        "id": ("analitik", "koneksi"),
    }
    for locale in SUPPORTED_UI_LOCALES:
        text = ASK_UI_TEXT[locale]["feedback_delivery_failed"].lower()
        for term in forbidden[locale]:
            assert term not in text
