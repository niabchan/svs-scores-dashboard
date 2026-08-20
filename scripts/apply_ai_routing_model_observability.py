from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# usage_analytics.py
path = Path("usage_analytics.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    'MAX_COMMENT_CHARS = 1_500\nMAX_EVENT_BYTES = 64_000\n',
    'MAX_COMMENT_CHARS = 1_500\nMAX_MODEL_CHARS = 200\nMAX_EVENT_BYTES = 64_000\n',
    "analytics model length constant",
)
text = replace_once(
    text,
    '    ui_language: str,\n    suggested_question: str | None = None,\n',
    '    ui_language: str,\n    ai_routing_model: str | None = None,\n    suggested_question: str | None = None,\n',
    "answer event model parameter",
)
text = replace_once(
    text,
    '    question = str(parameters.get("question", ""))\n    allow_text = bool(include_full_text and question_kind == "custom")\n\n    event = {\n',
    '    question = str(parameters.get("question", ""))\n    allow_text = bool(include_full_text and question_kind == "custom")\n    ai_attempted = bool(diagnostics.get("ai_attempted", False))\n\n    event = {\n',
    "answer event ai attempted local",
)
text = replace_once(
    text,
    '        "ai_attempted": bool(diagnostics.get("ai_attempted", False)),\n        "ai_succeeded": bool(diagnostics.get("ai_succeeded", False)),\n        "ai_diagnostic_code": diagnostics.get("diagnostic_code"),\n',
    '        "ai_attempted": ai_attempted,\n        "ai_succeeded": bool(diagnostics.get("ai_succeeded", False)),\n        "ai_routing_model": (\n            _bounded_text(ai_routing_model, MAX_MODEL_CHARS)\n            if ai_attempted and ai_routing_model\n            else None\n        ),\n        "ai_diagnostic_code": diagnostics.get("diagnostic_code"),\n',
    "answer event model field",
)
text = replace_once(
    text,
    '        "ai_success_rate": rate(ai_success_count, ai_attempt_count),\n        "full_text_opt_in_count": sum(bool(event.get("full_text_consent")) for event in answers),\n',
    '        "ai_success_rate": rate(ai_success_count, ai_attempt_count),\n        "ai_routing_models": dict(\n            Counter(\n                str(event.get("ai_routing_model"))\n                for event in answers\n                if event.get("ai_attempted") and event.get("ai_routing_model")\n            )\n        ),\n        "full_text_opt_in_count": sum(bool(event.get("full_text_consent")) for event in answers),\n',
    "analytics model summary",
)
path.write_text(text, encoding="utf-8")


# app.py: pass runtime-configured model into the event builder. build_answer_event
# itself blanks the field for rule-only answers, so configured != used.
path = Path("app.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '                question_kind=question_kind,\n                ui_language=st.session_state.get("lang", "en"),\n                suggested_question=(\n',
    '                question_kind=question_kind,\n                ui_language=st.session_state.get("lang", "en"),\n                ai_routing_model=_secret_or_env("OPENAI_INTENT_MODEL"),\n                suggested_question=(\n',
    "app answer event model wiring",
)
path.write_text(text, encoding="utf-8")


# Google Apps Script: keep RAW_HEADERS untouched. The model lives inside
# raw_event_json and is surfaced only in rebuildable derived views.
path = Path("analytics/google_apps_script/Code.gs")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '  "ai_attempted",\n  "ai_succeeded",\n  "feedback_timestamp_utc",\n',
    '  "ai_attempted",\n  "ai_succeeded",\n  "ai_routing_model",\n  "feedback_timestamp_utc",\n',
    "derived answer headers model field",
)
text = replace_once(
    text,
    '      answer.ai_attempted,\n      answer.ai_succeeded,\n      feedbackEvent.timestamp_utc,\n',
    '      answer.ai_attempted,\n      answer.ai_succeeded,\n      answer.ai_routing_model,\n      feedbackEvent.timestamp_utc,\n',
    "derived answer row model field",
)
text = replace_once(
    text,
    '    ["App version", "Count"],\n    ...counterRows_(answers, "app_version"),\n    [],\n    ["Feedback reason", "Count"],\n',
    '    ["App version", "Count"],\n    ...counterRows_(answers, "app_version"),\n    [],\n    ["AI routing model", "Count"],\n    ...counterRows_(\n      answers.filter((event) => event.ai_attempted === true),\n      "ai_routing_model"\n    ),\n    [],\n    ["Feedback reason", "Count"],\n',
    "summary model counter",
)
path.write_text(text, encoding="utf-8")


# 9arm setup docs: the secret key remains stable; only the runtime value changes.
path = Path("NINEARM_API_SETUP.md")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    'OPENAI_INTENT_MODEL = "qwen3.6-35b-a3b"',
    'OPENAI_INTENT_MODEL = "qwen3.8-27b-fp8"',
    "documented 9arm model",
)
text = replace_once(
    text,
    'The project keeps the existing `OPENAI_*` variable names because it uses the OpenAI Python SDK as a client for an OpenAI-compatible endpoint. The provider is selected by the base URL and API style.\n',
    'The project keeps the existing `OPENAI_*` variable names because it uses the OpenAI Python SDK as a client for an OpenAI-compatible endpoint. The provider is selected by the base URL and API style. `OPENAI_INTENT_MODEL` is intentionally a runtime setting, so a provider model replacement normally requires changing the secret value rather than changing application code.\n',
    "runtime model documentation",
)
path.write_text(text, encoding="utf-8")


# Google Sheets setup docs: explain the derived model field and migration path.
path = Path("GOOGLE_SHEETS_ANALYTICS_SETUP.md")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '- `AnswerFeedbackView` — one answer per row joined with its latest feedback;\n',
    '- `AnswerFeedbackView` — one answer per row joined with its latest feedback, including the AI routing model when an AI routing attempt occurred;\n',
    "answer feedback view docs",
)
text = replace_once(
    text,
    '- `Summary` — answer, feedback, helpful, unsupported, AI, language, intent, and version metrics;\n',
    '- `Summary` — answer, feedback, helpful, unsupported, AI, AI routing model, language, intent, and version metrics;\n',
    "summary docs",
)
text = replace_once(
    text,
    'Editing `Code.gs` does not automatically update an existing deployment. After code changes, create a new deployment version or edit the deployment to use the new version, then verify the Web App URL used in Streamlit Secrets.\n',
    'Editing `Code.gs` does not automatically update an existing deployment. After code changes, create a new deployment version or edit the deployment to use the new version, then verify the Web App URL used in Streamlit Secrets. The AI routing model field is added only to rebuildable derived views and `raw_event_json`; the existing `RawEvents` header layout is intentionally unchanged, so current analytics rows remain compatible.\n',
    "analytics migration docs",
)
path.write_text(text, encoding="utf-8")
