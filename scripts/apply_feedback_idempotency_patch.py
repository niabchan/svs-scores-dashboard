from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


usage_path = ROOT / "usage_analytics.py"
app_path = ROOT / "app.py"
receiver_path = ROOT / "analytics/google_apps_script/Code.gs"
test_path = ROOT / "test_usage_analytics.py"
self_path = Path(__file__)

# Stable event IDs make a retry of feedback for the same answer idempotent.
replace_once(
    usage_path,
    "from uuid import uuid4\n",
    "from uuid import NAMESPACE_URL, uuid4, uuid5\n",
    "uuid imports",
)
replace_once(
    usage_path,
    "\ndef _json_value(value: Any) -> Any:\n",
    '''\ndef feedback_event_id_for_answer(answer_event_id: str) -> str:\n    """Return a stable feedback event ID so delivery retries are idempotent."""\n    if not isinstance(answer_event_id, str) or not answer_event_id.strip():\n        raise ValueError("answer_event_id is required")\n    return str(\n        uuid5(\n            NAMESPACE_URL,\n            f"svs-scores-dashboard-feedback:{answer_event_id.strip()}",\n        )\n    )\n\n\ndef _json_value(value: Any) -> Any:\n''',
    "stable feedback helper",
)
replace_once(
    usage_path,
    '        "event_id": event_id or str(uuid4()),\n        "answer_event_id": answer_event_id,\n',
    '        "event_id": event_id or feedback_event_id_for_answer(answer_event_id),\n        "answer_event_id": answer_event_id,\n',
    "feedback event id",
)
usage_text = usage_path.read_text(encoding="utf-8")
if usage_text.count("timeout_seconds: float = 4.0") != 2:
    raise RuntimeError("webhook timeout anchors changed")
usage_path.write_text(
    usage_text.replace("timeout_seconds: float = 4.0", "timeout_seconds: float = 10.0"),
    encoding="utf-8",
)

old_summary = '''    answers = [event for event in events if event.get("event_type") == "answer_generated"]
    feedback = [event for event in events if event.get("event_type") == "feedback_submitted"]
    answer_ids = {str(event.get("event_id")) for event in answers}
    helpful_count = sum(event.get("helpful") is True for event in feedback)
'''
new_summary = '''    answers = [event for event in events if event.get("event_type") == "answer_generated"]
    feedback = [event for event in events if event.get("event_type") == "feedback_submitted"]
    answer_ids = {str(event.get("event_id")) for event in answers}

    # Delivery is at-least-once. Keep the latest feedback per answer for product
    # metrics so a retry cannot inflate feedback or helpfulness counts.
    feedback_by_answer: dict[str, dict[str, Any]] = {}
    for event in feedback:
        answer_event_id = str(event.get("answer_event_id") or "")
        previous = feedback_by_answer.get(answer_event_id)
        if previous is None or str(previous.get("timestamp_utc") or "") <= str(
            event.get("timestamp_utc") or ""
        ):
            feedback_by_answer[answer_event_id] = event
    effective_feedback = list(feedback_by_answer.values())
    helpful_count = sum(event.get("helpful") is True for event in effective_feedback)
'''
replace_once(usage_path, old_summary, new_summary, "summary feedback dedupe")
replace_once(
    usage_path,
    '''        "feedback_count": len(feedback),
        "orphan_feedback_count": sum(
            str(event.get("answer_event_id")) not in answer_ids for event in feedback
        ),
        "helpful_count": helpful_count,
        "not_helpful_count": len(feedback) - helpful_count,
        "helpful_rate": rate(helpful_count, len(feedback)),
''',
    '''        "feedback_count": len(effective_feedback),
        "raw_feedback_event_count": len(feedback),
        "duplicate_retry_feedback_count": len(feedback) - len(effective_feedback),
        "orphan_feedback_count": sum(
            str(event.get("answer_event_id")) not in answer_ids for event in effective_feedback
        ),
        "helpful_count": helpful_count,
        "not_helpful_count": len(effective_feedback) - helpful_count,
        "helpful_rate": rate(helpful_count, len(effective_feedback)),
''',
    "summary feedback metrics",
)
replace_once(
    usage_path,
    '''        "feedback_reasons": dict(
            Counter(str(event.get("reason")) for event in feedback if event.get("reason"))
        ),
''',
    '''        "feedback_reasons": dict(
            Counter(
                str(event.get("reason"))
                for event in effective_feedback
                if event.get("reason")
            )
        ),
''',
    "summary feedback reasons",
)

# Give Apps Script longer to finish derived-sheet rebuilding before declaring a
# transient failure. A lost response is still safe because event IDs are stable.
warning = "Feedback delivery could not be confirmed. You can retry safely; retries for the same answer will not create another feedback record."
app_text = app_path.read_text(encoding="utf-8")
old_warning = 'st.warning("Feedback could not be saved on this preview instance.")'
if app_text.count(old_warning) != 2:
    raise RuntimeError("feedback warning anchors changed")
app_path.write_text(app_text.replace(old_warning, f'st.warning("{warning}")'), encoding="utf-8")

# Receiver-side idempotency protects every analytics event, including an answer
# or feedback whose first response was lost after the row was appended.
replace_once(
    receiver_path,
    '''    const event = validateEvent_(envelope.event);
    const lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
      appendRawEvent_(spreadsheet, event);
      rebuildDerivedSheets_(spreadsheet);
    } finally {
      lock.releaseLock();
    }

    return jsonResponse_({ ok: true, event_id: event.event_id });
''',
    '''    const event = validateEvent_(envelope.event);
    const lock = LockService.getScriptLock();
    let appended = false;
    lock.waitLock(10000);
    try {
      const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
      appended = appendRawEvent_(spreadsheet, event);
      if (appended) {
        rebuildDerivedSheets_(spreadsheet);
      }
    } finally {
      lock.releaseLock();
    }

    return jsonResponse_({
      ok: true,
      event_id: event.event_id,
      duplicate: !appended,
    });
''',
    "receiver doPost idempotency",
)
replace_once(
    receiver_path,
    '''function appendRawEvent_(spreadsheet, event) {
  const sheet = getOrCreateSheet_(spreadsheet, RAW_SHEET_NAME);
  ensureHeaders_(sheet, RAW_HEADERS);

  const rowObject = Object.assign(
    { received_at_utc: new Date().toISOString() },
    event,
    { raw_event_json: JSON.stringify(event) }
  );
  const row = RAW_HEADERS.map((header) => safeCellValue_(rowObject[header]));
  sheet.appendRow(row);
}
''',
    '''function appendRawEvent_(spreadsheet, event) {
  const sheet = getOrCreateSheet_(spreadsheet, RAW_SHEET_NAME);
  ensureHeaders_(sheet, RAW_HEADERS);

  if (rawEventIdExists_(sheet, event.event_id)) {
    return false;
  }

  const rowObject = Object.assign(
    { received_at_utc: new Date().toISOString() },
    event,
    { raw_event_json: JSON.stringify(event) }
  );
  const row = RAW_HEADERS.map((header) => safeCellValue_(rowObject[header]));
  sheet.appendRow(row);
  return true;
}

function rawEventIdExists_(sheet, eventId) {
  if (sheet.getLastRow() < 2) {
    return false;
  }
  const eventIdColumn = RAW_HEADERS.indexOf("event_id") + 1;
  const values = sheet
    .getRange(2, eventIdColumn, sheet.getLastRow() - 1, 1)
    .getDisplayValues();
  return values.some((row) => String(row[0]) === String(eventId));
}
''',
    "receiver append dedupe",
)
replace_once(
    receiver_path,
    '''function writeSummary_(spreadsheet, answers, feedback, feedbackByAnswer) {
  const helpfulCount = feedback.filter((event) => event.helpful === true).length;
''',
    '''function writeSummary_(spreadsheet, answers, feedback, feedbackByAnswer) {
  const effectiveFeedback = Object.keys(feedbackByAnswer).map(
    (answerEventId) => feedbackByAnswer[answerEventId]
  );
  const helpfulCount = effectiveFeedback.filter(
    (event) => event.helpful === true
  ).length;
''',
    "receiver effective feedback",
)
replace_once(
    receiver_path,
    '''    ["Feedback", feedback.length],
    ["Feedback coverage", percent_(Object.keys(feedbackByAnswer).length, answers.length)],
    ["Helpful rate", percent_(helpfulCount, feedback.length)],
''',
    '''    ["Feedback", effectiveFeedback.length],
    ["Raw feedback events", feedback.length],
    ["Duplicate/retry feedback events", Math.max(0, feedback.length - effectiveFeedback.length)],
    ["Feedback coverage", percent_(Object.keys(feedbackByAnswer).length, answers.length)],
    ["Helpful rate", percent_(helpfulCount, effectiveFeedback.length)],
''',
    "receiver summary counts",
)
replace_once(
    receiver_path,
    '    ...counterRows_(feedback, "reason"),\n',
    '    ...counterRows_(effectiveFeedback, "reason"),\n',
    "receiver feedback reason counts",
)

# Tests lock the retry contract and ensure summaries are not inflated.
replace_once(
    test_path,
    '''    build_feedback_event,
    load_local_events,
''',
    '''    build_feedback_event,
    feedback_event_id_for_answer,
    load_local_events,
''',
    "test helper import",
)
replace_once(
    test_path,
    '''def test_feedback_requires_a_persisted_answer_event_id():
    with pytest.raises(ValueError, match="answer_event_id"):
        build_feedback_event("", helpful=True)


def test_local_jsonl_round_trip_and_malformed_count(tmp_path):
''',
    '''def test_feedback_requires_a_persisted_answer_event_id():
    with pytest.raises(ValueError, match="answer_event_id"):
        build_feedback_event("", helpful=True)


def test_feedback_retry_uses_a_stable_event_id():
    first = build_feedback_event(
        "answer-1",
        helpful=True,
        reason="correct_and_clear",
    )
    retry = build_feedback_event(
        "answer-1",
        helpful=True,
        reason="correct_and_clear",
    )

    assert first["event_id"] == retry["event_id"]
    assert first["event_id"] == feedback_event_id_for_answer("answer-1")
    assert first["event_id"] != feedback_event_id_for_answer("answer-2")


def test_local_jsonl_round_trip_and_malformed_count(tmp_path):
''',
    "stable feedback test",
)
replace_once(
    test_path,
    '    assert captured["timeout"] == 4.0\n',
    '    assert captured["timeout"] == 10.0\n',
    "webhook timeout test",
)
replace_once(
    test_path,
    '''        build_feedback_event(
            "answer-2",
            helpful=False,
            reason="unsupported_question",
            event_id="feedback-2",
        ),
    ]
''',
    '''        build_feedback_event(
            "answer-2",
            helpful=False,
            reason="unsupported_question",
            event_id="feedback-2",
            timestamp_utc="2026-08-05T03:05:00Z",
        ),
        # Simulate a retry that reached the backend after the client reported
        # a transient failure. Product metrics keep only the latest feedback
        # for the answer instead of counting both deliveries.
        build_feedback_event(
            "answer-2",
            helpful=False,
            reason="unsupported_question",
            event_id="feedback-2-retry",
            timestamp_utc="2026-08-05T03:06:00Z",
        ),
    ]
''',
    "duplicate feedback fixture",
)
replace_once(
    test_path,
    '''    assert summary["feedback_count"] == 2
    assert summary["orphan_feedback_count"] == 0
''',
    '''    assert summary["feedback_count"] == 2
    assert summary["raw_feedback_event_count"] == 3
    assert summary["duplicate_retry_feedback_count"] == 1
    assert summary["orphan_feedback_count"] == 0
''',
    "duplicate feedback assertions",
)

self_path.unlink(missing_ok=True)
