from pathlib import Path

from usage_analytics import build_answer_event, summarize_events


MODEL = "qwen3.8-27b-fp8"


def _answer(*, ai_attempted=False, ai_succeeded=False, source="rule"):
    return {
        "intent": "dashboard_help",
        "status": "ok",
        "period": "2026-W29",
        "guidance_code": None,
        "error_code": None,
        "parameters": {"question": "How do I use this?", "mentioned_alliances": []},
        "routing": {
            "source": source,
            "match_status": "matched",
            "confidence": 1.0 if source == "rule" else 0.9,
        },
        "routing_diagnostics": {
            "ai_attempted": ai_attempted,
            "ai_succeeded": ai_succeeded,
            "diagnostic_code": None,
        },
    }


def test_rule_answer_does_not_claim_configured_ai_model():
    event = build_answer_event(
        _answer(),
        "Rendered answer",
        question_kind="custom",
        ui_language="en",
        ai_routing_model=MODEL,
        event_id="rule-answer",
    )

    assert event["ai_attempted"] is False
    assert event["ai_routing_model"] is None


def test_ai_attempt_records_the_routing_model():
    event = build_answer_event(
        _answer(ai_attempted=True, ai_succeeded=True, source="api"),
        "Rendered answer",
        question_kind="custom",
        ui_language="en",
        ai_routing_model=MODEL,
        event_id="api-answer",
    )

    assert event["ai_attempted"] is True
    assert event["ai_succeeded"] is True
    assert event["ai_routing_model"] == MODEL


def test_ai_model_is_bounded_and_summary_counts_models():
    long_model = "m" * 400
    event = build_answer_event(
        _answer(ai_attempted=True, ai_succeeded=False),
        "Rendered answer",
        question_kind="custom",
        ui_language="en",
        ai_routing_model=long_model,
        event_id="api-fallback",
    )

    assert len(event["ai_routing_model"]) <= 200
    summary = summarize_events([event])
    assert summary["ai_routing_models"] == {event["ai_routing_model"]: 1}


def test_app_passes_runtime_intent_model_into_answer_analytics():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'ai_routing_model=_secret_or_env("OPENAI_INTENT_MODEL")' in source


def test_google_sheet_model_is_derived_without_changing_raw_headers():
    source = Path("analytics/google_apps_script/Code.gs").read_text(encoding="utf-8")
    raw_headers = source.split("const RAW_HEADERS = [", 1)[1].split("];", 1)[0]
    answer_headers = source.split("const ANSWER_FEEDBACK_HEADERS = [", 1)[1].split("];", 1)[0]

    assert '"ai_routing_model"' not in raw_headers
    assert '"ai_routing_model"' in answer_headers
    assert "answer.ai_routing_model" in source
    assert '["AI routing model", "Count"]' in source
