from datetime import datetime, timezone
import json

import pytest

import usage_analytics
from usage_analytics import (
    MAX_ANSWER_CHARS,
    MAX_COMMENT_CHARS,
    MAX_QUESTION_CHARS,
    append_local_event,
    build_answer_event,
    build_feedback_event,
    load_local_events,
    safely_persist_event,
    summarize_events,
)


def sample_answer(question="Why did the negative percentage increase?"):
    return {
        "intent": "negative_share_change",
        "status": "ok",
        "period": "2026-W29",
        "guidance_code": None,
        "error_code": None,
        "parameters": {
            "question": question,
            "mentioned_alliances": ["TDA"],
        },
        "routing": {
            "source": "rule",
            "match_status": "matched",
            "confidence": 1.0,
        },
        "routing_diagnostics": {
            "ai_attempted": False,
            "ai_succeeded": False,
            "diagnostic_code": None,
        },
    }


def test_answer_event_excludes_custom_full_text_without_consent():
    event = build_answer_event(
        sample_answer("Was TDA careless?"),
        "The dashboard cannot establish carelessness.",
        question_kind="custom",
        ui_language="en",
        include_full_text=False,
        selected_alliance_count=3,
        selected_net_status_count=2,
        selected_player_count=90,
        total_player_count=100,
        timestamp_utc=datetime(2026, 8, 5, 3, 0, tzinfo=timezone.utc),
        event_id="answer-1",
    )

    assert event["event_type"] == "answer_generated"
    assert event["event_id"] == "answer-1"
    assert event["timestamp_utc"] == "2026-08-05T03:00:00Z"
    assert event["question_text"] is None
    assert event["answer_text"] is None
    assert event["full_text_consent"] is False
    assert event["question_character_count"] == len("Was TDA careless?")
    assert event["mentioned_alliance_count"] == 1
    assert event["selected_alliance_count"] == 3
    assert event["selected_player_count"] == 90
    assert event["total_player_count"] == 100


def test_answer_event_includes_and_bounds_opted_in_custom_text():
    question = "Q" * (MAX_QUESTION_CHARS + 20)
    answer_text = "A" * (MAX_ANSWER_CHARS + 20)
    event = build_answer_event(
        sample_answer(question),
        answer_text,
        question_kind="custom",
        ui_language="vi",
        include_full_text=True,
        event_id="answer-2",
        app_version="preview-pr13",
    )

    assert event["app_version"] == "preview-pr13"
    assert event["full_text_consent"] is True
    assert len(event["question_text"]) == MAX_QUESTION_CHARS
    assert event["question_text"].endswith("…")
    assert len(event["answer_text"]) == MAX_ANSWER_CHARS
    assert event["answer_text"].endswith("…")
    assert event["ui_language"] == "vi"


def test_suggested_question_uses_system_label_without_full_answer_text():
    label = "Which players contributed most to the selected alliance?"
    event = build_answer_event(
        sample_answer(label),
        "Rendered answer",
        question_kind="suggested",
        suggested_question=label,
        ui_language="en",
        include_full_text=True,
        event_id="answer-3",
    )

    assert event["suggested_question"] == label
    assert event["full_text_consent"] is False
    assert event["question_text"] is None
    assert event["answer_text"] is None


def test_feedback_event_links_answer_and_bounds_comment():
    event = build_feedback_event(
        "answer-1",
        helpful=False,
        reason="misunderstood_question",
        comment="C" * (MAX_COMMENT_CHARS + 10),
        timestamp_utc=datetime(2026, 8, 5, 3, 5, tzinfo=timezone.utc),
        event_id="feedback-1",
        app_version="preview-pr13",
    )

    assert event["app_version"] == "preview-pr13"
    assert event["event_type"] == "feedback_submitted"
    assert event["answer_event_id"] == "answer-1"
    assert event["helpful"] is False
    assert event["reason"] == "misunderstood_question"
    assert len(event["comment"]) == MAX_COMMENT_CHARS
    assert event["comment"].endswith("…")


def test_feedback_requires_a_persisted_answer_event_id():
    with pytest.raises(ValueError, match="answer_event_id"):
        build_feedback_event("", helpful=True)


def test_local_jsonl_round_trip_and_malformed_count(tmp_path):
    path = tmp_path / "analytics" / "events.jsonl"
    answer = build_answer_event(
        sample_answer(),
        "Rendered answer",
        question_kind="suggested",
        suggested_question="Suggested",
        ui_language="en",
        event_id="answer-1",
    )
    feedback = build_feedback_event(
        "answer-1",
        helpful=True,
        reason="correct_and_clear",
        event_id="feedback-1",
    )

    append_local_event(str(path), answer)
    append_local_event(str(path), feedback)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")

    events, malformed = load_local_events(str(path))

    assert [event["event_id"] for event in events] == ["answer-1", "feedback-1"]
    assert malformed == 1
    assert all(json.dumps(event, ensure_ascii=False) for event in events)


def test_safe_persistence_never_raises(tmp_path):
    answer = build_answer_event(
        sample_answer(),
        "Rendered answer",
        question_kind="suggested",
        suggested_question="Suggested",
        ui_language="en",
        event_id="answer-1",
    )

    result = safely_persist_event(
        answer,
        mode="local",
        local_path=str(tmp_path / "events.jsonl"),
    )
    invalid_mode = safely_persist_event(answer, mode="unknown")
    missing_endpoint = safely_persist_event(answer, mode="webhook", endpoint=None)
    missing_secret = safely_persist_event(
        answer,
        mode="webhook",
        endpoint="https://example.test/events",
    )
    insecure_endpoint = safely_persist_event(
        answer,
        mode="webhook",
        endpoint="http://example.test/events",
        shared_secret="shared-secret",
    )

    assert result == {"ok": True, "mode": "local", "diagnostic": None}
    assert invalid_mode["diagnostic"] == "invalid_mode"
    assert missing_endpoint["diagnostic"] == "missing_endpoint"
    assert missing_secret["diagnostic"] == "missing_shared_secret"
    assert insecure_endpoint["diagnostic"] == "ValueError"


def test_webhook_mode_posts_validated_json(monkeypatch):
    answer = build_answer_event(
        sample_answer(),
        "Rendered answer",
        question_kind="suggested",
        suggested_question="Suggested",
        ui_language="en",
        event_id="answer-1",
    )
    captured = {}

    class FakeResponse:
        status = 200

        def read(self):
            return b'{"ok": true}'

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    def fake_urlopen(req, timeout):
        captured["request"] = req
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(usage_analytics.request, "urlopen", fake_urlopen)

    result = safely_persist_event(
        answer,
        mode="webhook",
        endpoint="https://example.test/events",
        bearer_token="secret-token",
        shared_secret="shared-secret",
    )

    assert result == {"ok": True, "mode": "webhook", "diagnostic": None}
    assert captured["timeout"] == 4.0
    envelope = json.loads(captured["request"].data)
    assert envelope["secret"] == "shared-secret"
    assert envelope["event"]["event_id"] == "answer-1"
    assert captured["request"].get_header("Authorization") == "Bearer secret-token"


def test_summary_reports_product_metrics():
    events = [
        build_answer_event(
            sample_answer("Question 1"),
            "Answer 1",
            question_kind="custom",
            ui_language="en",
            include_full_text=True,
            event_id="answer-1",
        ),
        build_answer_event(
            {
                **sample_answer("Question 2"),
                "intent": "unsupported_question",
                "status": "guidance",
                "guidance_code": "unsupported_question",
                "routing": {
                    "source": "rule",
                    "match_status": "unsupported",
                    "confidence": 0.0,
                },
                "routing_diagnostics": {
                    "ai_attempted": True,
                    "ai_succeeded": False,
                    "diagnostic_code": "api_unavailable",
                },
            },
            "Answer 2",
            question_kind="custom",
            ui_language="fr",
            event_id="answer-2",
        ),
        build_feedback_event(
            "answer-1",
            helpful=True,
            reason="correct_and_clear",
            event_id="feedback-1",
        ),
        build_feedback_event(
            "answer-2",
            helpful=False,
            reason="unsupported_question",
            event_id="feedback-2",
        ),
    ]

    summary = summarize_events(events)

    assert summary["answer_count"] == 2
    assert summary["feedback_count"] == 2
    assert summary["orphan_feedback_count"] == 0
    assert summary["helpful_rate"] == 50.0
    assert summary["unsupported_rate"] == 50.0
    assert summary["ai_attempt_count"] == 1
    assert summary["ai_success_rate"] == 0.0
    assert summary["full_text_opt_in_count"] == 1
    assert summary["languages"] == {"en": 1, "fr": 1}
