"""Privacy-aware analytics helpers for the Ask Dashboard preview.

The preview can persist append-only analytics events either to a local JSONL
file or to a configured HTTPS webhook. Local files are best-effort on hosted
Streamlit and may be lost when the app restarts or redeploys.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any
from urllib import request
from uuid import uuid4

ANALYTICS_SCHEMA_VERSION = 1
ANALYTICS_EVENT_TYPES = {"answer_generated", "feedback_submitted"}
ANALYTICS_MODES = {"off", "local", "webhook"}
QUESTION_KINDS = {"suggested", "custom"}
FEEDBACK_REASONS = {
    "correct_and_clear",
    "misunderstood_question",
    "wrong_answer",
    "unsupported_question",
    "unclear_answer",
    "other",
}
DEFAULT_LOCAL_PATH = "/tmp/svs_scores_dashboard_analytics.jsonl"
MAX_QUESTION_CHARS = 1_500
MAX_ANSWER_CHARS = 8_000
MAX_COMMENT_CHARS = 1_500
MAX_EVENT_BYTES = 64_000
_LOCAL_WRITE_LOCK = Lock()


def _utc_timestamp(value: Any = None) -> str:
    if value is None:
        dt = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        dt = value.astimezone(timezone.utc)
    else:
        return str(value)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _bounded_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _json_value(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _validate_event(event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise TypeError("analytics event must be a dictionary")
    if event.get("schema_version") != ANALYTICS_SCHEMA_VERSION:
        raise ValueError("unsupported analytics schema_version")
    event_type = event.get("event_type")
    if event_type not in ANALYTICS_EVENT_TYPES:
        raise ValueError("unsupported analytics event_type")
    if not isinstance(event.get("event_id"), str) or not event["event_id"].strip():
        raise ValueError("analytics event_id is required")

    if event_type == "answer_generated":
        if event.get("question_kind") not in QUESTION_KINDS:
            raise ValueError("answer event question_kind is invalid")
        if not isinstance(event.get("full_text_consent"), bool):
            raise ValueError("answer event full_text_consent must be boolean")
        if not event["full_text_consent"] and (
            event.get("question_text") is not None or event.get("answer_text") is not None
        ):
            raise ValueError("answer full text requires consent")
    else:
        answer_event_id = event.get("answer_event_id")
        if not isinstance(answer_event_id, str) or not answer_event_id.strip():
            raise ValueError("feedback answer_event_id is required")
        if not isinstance(event.get("helpful"), bool):
            raise ValueError("feedback helpful must be boolean")
        reason = event.get("reason")
        if reason is not None and reason not in FEEDBACK_REASONS:
            raise ValueError("feedback reason is invalid")

    normalized = _json_value(event)
    encoded = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_EVENT_BYTES:
        raise ValueError("analytics event is too large")
    return normalized


def build_answer_event(
    answer: dict[str, Any],
    rendered_answer: str,
    *,
    question_kind: str,
    ui_language: str,
    suggested_question: str | None = None,
    include_full_text: bool = False,
    selected_alliance_count: int = 0,
    selected_net_status_count: int = 0,
    selected_player_count: int = 0,
    total_player_count: int = 0,
    app_variant: str = "preview",
    app_version: str = "unknown",
    timestamp_utc: Any = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Build an append-only answer event with opt-in full-text fields."""
    if question_kind not in QUESTION_KINDS:
        raise ValueError("question_kind must be suggested or custom")
    if not isinstance(answer, dict):
        raise TypeError("answer must be a dictionary")

    parameters = answer.get("parameters", {}) if isinstance(answer.get("parameters"), dict) else {}
    routing = answer.get("routing", {}) if isinstance(answer.get("routing"), dict) else {}
    diagnostics = (
        answer.get("routing_diagnostics", {})
        if isinstance(answer.get("routing_diagnostics"), dict)
        else {}
    )
    question = str(parameters.get("question", ""))
    allow_text = bool(include_full_text and question_kind == "custom")

    event = {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "event_type": "answer_generated",
        "event_id": event_id or str(uuid4()),
        "timestamp_utc": _utc_timestamp(timestamp_utc),
        "app_variant": str(app_variant),
        "app_version": str(app_version or "unknown"),
        "ui_language": str(ui_language or "en"),
        "question_kind": question_kind,
        "suggested_question": (
            _bounded_text(suggested_question, MAX_QUESTION_CHARS)
            if question_kind == "suggested"
            else None
        ),
        "full_text_consent": allow_text,
        "question_text": _bounded_text(question, MAX_QUESTION_CHARS) if allow_text else None,
        "answer_text": _bounded_text(rendered_answer, MAX_ANSWER_CHARS) if allow_text else None,
        "question_character_count": len(question),
        "answer_character_count": len(str(rendered_answer)),
        "intent": answer.get("intent"),
        "status": answer.get("status"),
        "guidance_code": answer.get("guidance_code"),
        "error_code": answer.get("error_code"),
        "period": answer.get("period"),
        "routing_source": routing.get("source", "rule"),
        "match_status": routing.get("match_status"),
        "routing_confidence": routing.get("confidence"),
        "ai_attempted": bool(diagnostics.get("ai_attempted", False)),
        "ai_succeeded": bool(diagnostics.get("ai_succeeded", False)),
        "ai_diagnostic_code": diagnostics.get("diagnostic_code"),
        "mentioned_alliance_count": len(parameters.get("mentioned_alliances", []) or []),
        "selected_alliance_count": int(selected_alliance_count),
        "selected_net_status_count": int(selected_net_status_count),
        "selected_player_count": int(selected_player_count),
        "total_player_count": int(total_player_count),
    }
    return _validate_event(event)


def build_feedback_event(
    answer_event_id: str,
    *,
    helpful: bool,
    reason: str | None = None,
    comment: str | None = None,
    app_variant: str = "preview",
    app_version: str = "unknown",
    timestamp_utc: Any = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Build feedback linked to a previously generated answer event."""
    if not isinstance(answer_event_id, str) or not answer_event_id.strip():
        raise ValueError("answer_event_id is required")
    if not isinstance(helpful, bool):
        raise TypeError("helpful must be a boolean")
    if reason is not None and reason not in FEEDBACK_REASONS:
        raise ValueError("unsupported feedback reason")
    event = {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "event_type": "feedback_submitted",
        "event_id": event_id or str(uuid4()),
        "answer_event_id": answer_event_id,
        "timestamp_utc": _utc_timestamp(timestamp_utc),
        "app_variant": str(app_variant),
        "app_version": str(app_version or "unknown"),
        "helpful": helpful,
        "reason": reason,
        "comment": _bounded_text(comment, MAX_COMMENT_CHARS),
    }
    return _validate_event(event)


def append_local_event(path: str, event: dict[str, Any]) -> None:
    """Append one validated event as a single JSONL record."""
    normalized = _validate_event(event)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(normalized, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND

    with _LOCAL_WRITE_LOCK:
        fd = os.open(target, flags, 0o600)
        try:
            remaining = memoryview(payload)
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0:
                    raise OSError("analytics write returned no progress")
                remaining = remaining[written:]
        finally:
            os.close(fd)


def post_webhook_event(
    endpoint: str,
    event: dict[str, Any],
    *,
    bearer_token: str | None = None,
    shared_secret: str | None = None,
    timeout_seconds: float = 4.0,
) -> None:
    """POST one event to a configured HTTPS JSON endpoint."""
    if not isinstance(endpoint, str) or not endpoint.startswith("https://"):
        raise ValueError("analytics webhook endpoint must use https://")
    normalized = _validate_event(event)
    if not shared_secret:
        raise ValueError("analytics webhook shared secret is required")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    payload = json.dumps(
        {"secret": str(shared_secret), "event": normalized},
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(endpoint, data=payload, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout_seconds) as response:
        status = getattr(response, "status", 200)
        if status < 200 or status >= 300:
            raise RuntimeError(f"analytics webhook returned HTTP {status}")
        body = getattr(response, "read", lambda: b"")()
        if body:
            try:
                response_payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RuntimeError("analytics webhook returned invalid JSON") from exc
            if isinstance(response_payload, dict) and response_payload.get("ok") is False:
                raise RuntimeError("analytics webhook rejected the event")


def safely_persist_event(
    event: dict[str, Any],
    *,
    mode: str = "local",
    local_path: str = DEFAULT_LOCAL_PATH,
    endpoint: str | None = None,
    bearer_token: str | None = None,
    shared_secret: str | None = None,
    timeout_seconds: float = 4.0,
) -> dict[str, Any]:
    """Persist an event without allowing analytics failures to break the app."""
    normalized_mode = str(mode or "off").strip().lower()
    if normalized_mode not in ANALYTICS_MODES:
        return {"ok": False, "mode": normalized_mode, "diagnostic": "invalid_mode"}
    if normalized_mode == "off":
        return {"ok": False, "mode": "off", "diagnostic": "analytics_disabled"}
    try:
        if normalized_mode == "local":
            append_local_event(local_path, event)
        elif normalized_mode == "webhook":
            if not endpoint:
                return {"ok": False, "mode": "webhook", "diagnostic": "missing_endpoint"}
            if not shared_secret:
                return {"ok": False, "mode": "webhook", "diagnostic": "missing_shared_secret"}
            post_webhook_event(
                endpoint,
                event,
                bearer_token=bearer_token,
                shared_secret=shared_secret,
                timeout_seconds=timeout_seconds,
            )
    except Exception as exc:
        return {
            "ok": False,
            "mode": normalized_mode,
            "diagnostic": type(exc).__name__,
        }
    return {"ok": True, "mode": normalized_mode, "diagnostic": None}


def load_local_events(path: str, *, max_entries: int = 5_000) -> tuple[list[dict[str, Any]], int]:
    """Read recent valid JSONL events and count malformed records."""
    if max_entries < 1:
        raise ValueError("max_entries must be positive")
    target = Path(path)
    if not target.exists():
        return [], 0
    valid: list[dict[str, Any]] = []
    malformed = 0
    with target.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                valid.append(_validate_event(item))
            except Exception:
                malformed += 1
    return valid[-max_entries:], malformed


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Return compact product metrics for an analytics-review view."""
    answers = [event for event in events if event.get("event_type") == "answer_generated"]
    feedback = [event for event in events if event.get("event_type") == "feedback_submitted"]
    answer_ids = {str(event.get("event_id")) for event in answers}
    helpful_count = sum(event.get("helpful") is True for event in feedback)
    unsupported_count = sum(
        event.get("intent") == "unsupported_question"
        or event.get("match_status") == "unsupported"
        for event in answers
    )
    ai_attempt_count = sum(bool(event.get("ai_attempted")) for event in answers)
    ai_success_count = sum(bool(event.get("ai_succeeded")) for event in answers)

    def rate(numerator: int, denominator: int) -> float | None:
        return numerator / denominator * 100 if denominator else None

    return {
        "answer_count": len(answers),
        "feedback_count": len(feedback),
        "orphan_feedback_count": sum(
            str(event.get("answer_event_id")) not in answer_ids for event in feedback
        ),
        "helpful_count": helpful_count,
        "not_helpful_count": len(feedback) - helpful_count,
        "helpful_rate": rate(helpful_count, len(feedback)),
        "unsupported_count": unsupported_count,
        "unsupported_rate": rate(unsupported_count, len(answers)),
        "ai_attempt_count": ai_attempt_count,
        "ai_success_count": ai_success_count,
        "ai_success_rate": rate(ai_success_count, ai_attempt_count),
        "full_text_opt_in_count": sum(bool(event.get("full_text_consent")) for event in answers),
        "intents": dict(Counter(str(event.get("intent")) for event in answers)),
        "languages": dict(Counter(str(event.get("ui_language")) for event in answers)),
        "guidance_codes": dict(
            Counter(str(event.get("guidance_code")) for event in answers if event.get("guidance_code"))
        ),
        "feedback_reasons": dict(
            Counter(str(event.get("reason")) for event in feedback if event.get("reason"))
        ),
    }
