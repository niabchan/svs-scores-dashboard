from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path, old, new, label):
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


ask_path = ROOT / "ask_dashboard.py"
openai_path = ROOT / "openai_intent.py"
usage_path = ROOT / "usage_analytics.py"
app_path = ROOT / "app.py"
test_usage_path = ROOT / "test_usage_analytics.py"
workflow_path = ROOT / ".github/workflows/tests.yml"
preview_setup_path = ROOT / "PREVIEW_ANALYTICS_SETUP.md"
self_path = Path(__file__)
self_workflow_path = ROOT / ".github/workflows/apply-roadmap-patch.yml"

# ---------------------------------------------------------------------------
# Ask Dashboard: generic alliance-score overview with explicit-metric priority.
# ---------------------------------------------------------------------------
replace_once(
    ask_path,
    '    "net_score_leader_summary",\n    "player_net_score_leader",\n',
    '    "net_score_leader_summary",\n    "alliance_score_overview",\n    "player_net_score_leader",\n',
    "supported intent",
)

replace_once(
    ask_path,
    'POSITIVE_RANK_TERMS = {"positive contribution", "positive rank", "positive ranking", "first in positive", "top in positive"}\n',
    'POSITIVE_RANK_TERMS = {"positive contribution", "positive rank", "positive ranking", "first in positive", "top in positive"}\n'
    'GENERIC_ALLIANCE_SCORE_RANK_TERMS = {"top", "highest", "best", "lead", "leads", "leader", "leading", "winner", "first"}\n'
    'EXPLICIT_ALLIANCE_SCORE_METRIC_TERMS = {"gained", "gain", "lost", "loss", "positive", "negative", "contribution", "impact"}\n',
    "generic score terms",
)

route_anchor = '''    if asks_about_contributors and ("alliance" in normalized_question or mentioned_alliances):
        return _intent_contract("top_contributors", {"alliance_names": mentioned_alliances})

    # Indirect human-inference wording is checked only after every supported
'''
route_replacement = '''    if asks_about_contributors and ("alliance" in normalized_question or mentioned_alliances):
        return _intent_contract("top_contributors", {"alliance_names": mentioned_alliances})

    has_generic_score_word = bool(
        re.search(r"\\bscor(?:e|es|ing)\\b|\\bscore[ -]leading\\b", normalized_question)
    )
    asks_about_generic_alliance_score = (
        has_alliance_subject
        and has_generic_score_word
        and (
            _has_any_word(normalized_question, GENERIC_ALLIANCE_SCORE_RANK_TERMS)
            or _has_any_phrase(normalized_question, {"score leader", "score-leading"})
        )
        and not has_net_score_context
        and not has_exclusion_term
        and not _has_any_word(normalized_question, EXPLICIT_ALLIANCE_SCORE_METRIC_TERMS)
        and not _has_any_phrase(
            normalized_question,
            {"score gained", "score lost", "positive contribution", "negative impact"},
        )
    )
    if asks_about_generic_alliance_score:
        return _intent_contract("alliance_score_overview")

    # Indirect human-inference wording is checked only after every supported
'''
replace_once(ask_path, route_anchor, route_replacement, "generic score routing")

calculator_anchor = '''def _player_scope(data, include_status=False):
'''
calculator = '''def calculate_alliance_score_overview(data, svs_period=None):
    """Summarize alliance leaders across several score dimensions."""
    intent = "alliance_score_overview"
    required = {"alliance", "score_gained", "score_lost", "net_score"}
    missing = required.difference(data.columns)
    if missing:
        return _missing_columns_result(intent, missing, svs_period)

    df = _numeric_scope(
        data,
        ["alliance", "score_gained", "score_lost", "net_score"],
    ).dropna(subset=["alliance"])
    if df.empty:
        return _base_result(intent, "guidance", svs_period, "empty_score_scope")

    summary = df.groupby("alliance", as_index=False).agg(
        total_score_gained=("score_gained", "sum"),
        total_score_lost=("score_lost", "sum"),
        total_net_score=("net_score", "sum"),
        positive_contribution=(
            "net_score",
            lambda scores: scores[scores > 0].sum(),
        ),
    )

    def leaders(column, *, lowest=False):
        best_value = summary[column].min() if lowest else summary[column].max()
        return (
            summary[summary[column] == best_value]
            .sort_values("alliance")
            .to_dict("records")
        )

    metrics = {
        "alliance_count": summary["alliance"].nunique(),
        "net_score_leaders": leaders("total_net_score"),
        "score_gained_leaders": leaders("total_score_gained"),
        "lowest_score_lost_leaders": leaders("total_score_lost", lowest=True),
        "positive_contribution_leaders": leaders("positive_contribution"),
    }
    rankings = {
        "alliances": summary.sort_values(
            ["total_net_score", "total_score_gained", "alliance"],
            ascending=[False, False, True],
        ).to_dict("records")
    }
    return _base_result(intent, "ok", svs_period, metrics=metrics, rankings=rankings)


'''
replace_once(ask_path, calculator_anchor, calculator + calculator_anchor, "overview calculator")

replace_once(
    ask_path,
    '    elif intent == "net_score_leader_summary":\n        result = calculate_net_score_leader_summary(data, svs_period)\n',
    '    elif intent == "net_score_leader_summary":\n        result = calculate_net_score_leader_summary(data, svs_period)\n'
    '    elif intent == "alliance_score_overview":\n        result = calculate_alliance_score_overview(data, svs_period)\n',
    "overview execution",
)

renderer_anchor = '''def _excluded_text(players):
'''
renderer = '''def _render_alliance_score_overview(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance

    metrics = answer["metrics"]
    period_text = _period_text(answer.get("period"))

    def metric_line(label, rows, field, *, signed=False):
        names = ", ".join(f"**{row['alliance']}**" for row in rows)
        value = rows[0][field]
        formatted = format_signed_score(value) if signed else format_score(value)
        tie_note = " (tie)" if len(rows) > 1 else ""
        return f"- **{label}:** {names} — **{formatted}**{tie_note}"

    return (
        f"Score can refer to several metrics. Under the current sidebar filters{period_text}:\\n\\n"
        f"{metric_line('Overall leader by net score', metrics['net_score_leaders'], 'total_net_score', signed=True)}\\n"
        f"{metric_line('Highest score gained', metrics['score_gained_leaders'], 'total_score_gained')}\\n"
        f"{metric_line('Lowest score lost', metrics['lowest_score_lost_leaders'], 'total_score_lost')}\\n"
        f"{metric_line('Highest positive contribution', metrics['positive_contribution_leaders'], 'positive_contribution')}\\n\\n"
        "For a broad question about overall alliance performance, Ask Dashboard uses net score as the default measure. "
        "Name a metric such as score gained, score lost, net score, or positive contribution when you want one specific ranking."
    )


'''
replace_once(ask_path, renderer_anchor, renderer + renderer_anchor, "overview renderer")

replace_once(
    ask_path,
    '        "Supported areas include player and alliance net-score leaders, positive contribution "\n',
    '        "Supported areas include broad alliance score overviews, player and alliance net-score leaders, positive contribution "\n',
    "help supported areas",
)
replace_once(
    ask_path,
    '        "- Which alliance leads net score?\\n"\n',
    '        "- Top alliance score\\n"\n        "- Which alliance leads net score?\\n"\n',
    "help example",
)
replace_once(
    ask_path,
    '        "net_score_leader_summary": _render_net_score_leader_summary,\n',
    '        "net_score_leader_summary": _render_net_score_leader_summary,\n'
    '        "alliance_score_overview": _render_alliance_score_overview,\n',
    "overview renderer map",
)

# ---------------------------------------------------------------------------
# AI intent catalog remains compatible with the new deterministic intent.
# ---------------------------------------------------------------------------
replace_once(
    openai_path,
    '    "net_score_leader_summary": "Summarize which alliance leads total net score.",\n',
    '    "net_score_leader_summary": "Summarize which alliance leads total net score.",\n'
    '    "alliance_score_overview": "Answer a broad alliance-score leader question by summarizing multiple score metrics without silently assuming one metric.",\n',
    "AI overview definition",
)
replace_once(
    openai_path,
    '        "qualities from score data. "\n',
    '        "qualities from score data. Classify broad questions such as top alliance score, "\n'
    '        "where no specific metric is named, as alliance_score_overview. "\n',
    "AI overview instruction",
)

# ---------------------------------------------------------------------------
# Analytics: app version and Apps Script-compatible shared-secret envelope.
# ---------------------------------------------------------------------------
replace_once(
    usage_path,
    '    app_variant: str = "preview",\n    timestamp_utc: Any = None,\n',
    '    app_variant: str = "preview",\n    app_version: str = "unknown",\n    timestamp_utc: Any = None,\n',
    "answer app version signature",
)
replace_once(
    usage_path,
    '        "app_variant": str(app_variant),\n        "ui_language": str(ui_language or "en"),\n',
    '        "app_variant": str(app_variant),\n        "app_version": str(app_version or "unknown"),\n        "ui_language": str(ui_language or "en"),\n',
    "answer app version field",
)
replace_once(
    usage_path,
    '    app_variant: str = "preview",\n    timestamp_utc: Any = None,\n    event_id: str | None = None,\n) -> dict[str, Any]:\n    """Build feedback linked to a previously generated answer event."""\n',
    '    app_variant: str = "preview",\n    app_version: str = "unknown",\n    timestamp_utc: Any = None,\n    event_id: str | None = None,\n) -> dict[str, Any]:\n    """Build feedback linked to a previously generated answer event."""\n',
    "feedback app version signature",
)
replace_once(
    usage_path,
    '        "app_variant": str(app_variant),\n        "helpful": helpful,\n',
    '        "app_variant": str(app_variant),\n        "app_version": str(app_version or "unknown"),\n        "helpful": helpful,\n',
    "feedback app version field",
)
replace_once(
    usage_path,
    '    bearer_token: str | None = None,\n    timeout_seconds: float = 4.0,\n) -> None:\n',
    '    bearer_token: str | None = None,\n    shared_secret: str | None = None,\n    timeout_seconds: float = 4.0,\n) -> None:\n',
    "webhook shared secret signature",
)
replace_once(
    usage_path,
    '    normalized = _validate_event(event)\n    headers = {"Content-Type": "application/json; charset=utf-8"}\n',
    '    normalized = _validate_event(event)\n'
    '    if not shared_secret:\n'
    '        raise ValueError("analytics webhook shared secret is required")\n'
    '    headers = {"Content-Type": "application/json; charset=utf-8"}\n',
    "webhook require secret",
)
replace_once(
    usage_path,
    '    payload = json.dumps(normalized, ensure_ascii=False).encode("utf-8")\n',
    '    payload = json.dumps(\n'
    '        {"secret": str(shared_secret), "event": normalized},\n'
    '        ensure_ascii=False,\n'
    '    ).encode("utf-8")\n',
    "webhook envelope",
)
replace_once(
    usage_path,
    '        if status < 200 or status >= 300:\n            raise RuntimeError(f"analytics webhook returned HTTP {status}")\n',
    '        if status < 200 or status >= 300:\n'
    '            raise RuntimeError(f"analytics webhook returned HTTP {status}")\n'
    '        body = getattr(response, "read", lambda: b"")()\n'
    '        if body:\n'
    '            try:\n'
    '                response_payload = json.loads(body.decode("utf-8"))\n'
    '            except (UnicodeDecodeError, json.JSONDecodeError) as exc:\n'
    '                raise RuntimeError("analytics webhook returned invalid JSON") from exc\n'
    '            if isinstance(response_payload, dict) and response_payload.get("ok") is False:\n'
    '                raise RuntimeError("analytics webhook rejected the event")\n',
    "webhook response validation",
)
replace_once(
    usage_path,
    '    bearer_token: str | None = None,\n    timeout_seconds: float = 4.0,\n) -> dict[str, Any]:\n',
    '    bearer_token: str | None = None,\n    shared_secret: str | None = None,\n    timeout_seconds: float = 4.0,\n) -> dict[str, Any]:\n',
    "safe persistence shared secret signature",
)
replace_once(
    usage_path,
    '            if not endpoint:\n                return {"ok": False, "mode": "webhook", "diagnostic": "missing_endpoint"}\n            post_webhook_event(\n',
    '            if not endpoint:\n'
    '                return {"ok": False, "mode": "webhook", "diagnostic": "missing_endpoint"}\n'
    '            if not shared_secret:\n'
    '                return {"ok": False, "mode": "webhook", "diagnostic": "missing_shared_secret"}\n'
    '            post_webhook_event(\n',
    "safe persistence missing secret",
)
replace_once(
    usage_path,
    '                bearer_token=bearer_token,\n                timeout_seconds=timeout_seconds,\n',
    '                bearer_token=bearer_token,\n'
    '                shared_secret=shared_secret,\n'
    '                timeout_seconds=timeout_seconds,\n',
    "safe persistence pass secret",
)

# Streamlit configuration and event version fields.
replace_once(
    app_path,
    '        "bearer_token": _secret_or_env("ASK_DASHBOARD_ANALYTICS_TOKEN"),\n',
    '        "bearer_token": _secret_or_env("ASK_DASHBOARD_ANALYTICS_TOKEN"),\n'
    '        "shared_secret": _secret_or_env("ASK_DASHBOARD_ANALYTICS_SHARED_SECRET"),\n'
    '        "app_version": str(_secret_or_env("ASK_DASHBOARD_APP_VERSION") or "preview-unknown"),\n',
    "app analytics config",
)
replace_once(
    app_path,
    '        bearer_token=config["bearer_token"],\n    )\n',
    '        bearer_token=config["bearer_token"],\n'
    '        shared_secret=config["shared_secret"],\n'
    '    )\n',
    "app persist secret",
)
replace_once(
    app_path,
    '                total_player_count=total_players_in_scope,\n            )\n            analytics_result = _persist_preview_analytics(answer_event)\n',
    '                total_player_count=total_players_in_scope,\n'
    '                app_version=analytics_config["app_version"],\n'
    '            )\n'
    '            analytics_result = _persist_preview_analytics(answer_event)\n',
    "answer event app version",
)
replace_once(
    app_path,
    '                            comment=feedback_comment.strip() or None,\n                        )\n',
    '                            comment=feedback_comment.strip() or None,\n'
    '                            app_version=analytics_config["app_version"],\n'
    '                        )\n',
    "feedback event app version",
)

# Existing analytics tests now assert the secure envelope and version field.
replace_once(
    test_usage_path,
    '    missing_endpoint = safely_persist_event(answer, mode="webhook", endpoint=None)\n    insecure_endpoint = safely_persist_event(\n        answer,\n        mode="webhook",\n        endpoint="http://example.test/events",\n    )\n',
    '    missing_endpoint = safely_persist_event(answer, mode="webhook", endpoint=None)\n'
    '    missing_secret = safely_persist_event(\n'
    '        answer,\n'
    '        mode="webhook",\n'
    '        endpoint="https://example.test/events",\n'
    '    )\n'
    '    insecure_endpoint = safely_persist_event(\n'
    '        answer,\n'
    '        mode="webhook",\n'
    '        endpoint="http://example.test/events",\n'
    '        shared_secret="shared-secret",\n'
    '    )\n',
    "safe persistence tests inputs",
)
replace_once(
    test_usage_path,
    '    assert missing_endpoint["diagnostic"] == "missing_endpoint"\n    assert insecure_endpoint["diagnostic"] == "ValueError"\n',
    '    assert missing_endpoint["diagnostic"] == "missing_endpoint"\n'
    '    assert missing_secret["diagnostic"] == "missing_shared_secret"\n'
    '    assert insecure_endpoint["diagnostic"] == "ValueError"\n',
    "safe persistence tests assertions",
)
replace_once(
    test_usage_path,
    '    class FakeResponse:\n        status = 204\n\n        def __enter__(self):\n',
    '    class FakeResponse:\n'
    '        status = 200\n\n'
    '        def read(self):\n'
    '            return b\'{"ok": true}\'\n\n'
    '        def __enter__(self):\n',
    "webhook fake response",
)
replace_once(
    test_usage_path,
    '        bearer_token="secret-token",\n    )\n\n    assert result == {"ok": True, "mode": "webhook", "diagnostic": None}\n    assert captured["timeout"] == 4.0\n    assert json.loads(captured["request"].data)["event_id"] == "answer-1"\n',
    '        bearer_token="secret-token",\n'
    '        shared_secret="shared-secret",\n'
    '    )\n\n'
    '    assert result == {"ok": True, "mode": "webhook", "diagnostic": None}\n'
    '    assert captured["timeout"] == 4.0\n'
    '    envelope = json.loads(captured["request"].data)\n'
    '    assert envelope["secret"] == "shared-secret"\n'
    '    assert envelope["event"]["event_id"] == "answer-1"\n',
    "webhook envelope test",
)
replace_once(
    test_usage_path,
    '        event_id="answer-2",\n    )\n\n    assert event["full_text_consent"] is True\n',
    '        event_id="answer-2",\n'
    '        app_version="preview-pr13",\n'
    '    )\n\n'
    '    assert event["app_version"] == "preview-pr13"\n'
    '    assert event["full_text_consent"] is True\n',
    "answer app version test",
)
replace_once(
    test_usage_path,
    '        event_id="feedback-1",\n    )\n\n    assert event["event_type"] == "feedback_submitted"\n',
    '        event_id="feedback-1",\n'
    '        app_version="preview-pr13",\n'
    '    )\n\n'
    '    assert event["app_version"] == "preview-pr13"\n'
    '    assert event["event_type"] == "feedback_submitted"\n',
    "feedback app version test",
)

# CI compiles the new tests.
replace_once(
    workflow_path,
    'usage_analytics.py test_ask_dashboard.py test_data_loading.py test_usage_analytics.py\n',
    'usage_analytics.py test_ask_dashboard.py test_alliance_score_overview.py test_data_loading.py test_usage_analytics.py\n',
    "CI compile list",
)

# Preview setup points to the durable Google Sheets receiver.
text = preview_setup_path.read_text(encoding="utf-8")
text = text.replace(
    'ASK_DASHBOARD_ANALYTICS_TOKEN = "optional-bearer-token"',
    'ASK_DASHBOARD_ANALYTICS_SHARED_SECRET = "shared-secret"\nASK_DASHBOARD_APP_VERSION = "preview-pr13"\nASK_DASHBOARD_ANALYTICS_TOKEN = "optional-bearer-token-for-non-Apps-Script-backends"',
)
if "GOOGLE_SHEETS_ANALYTICS_SETUP.md" not in text:
    text += (
        "\n\n## Google Sheets receiver\n\n"
        "For durable cloud storage with RawEvents, AnswerFeedbackView, Summary, and "
        "OptInTextReview sheets, follow `GOOGLE_SHEETS_ANALYTICS_SETUP.md`.\n"
    )
preview_setup_path.write_text(text, encoding="utf-8")

# Remove the one-time patch machinery from the resulting branch.
self_workflow_path.unlink(missing_ok=True)
self_path.unlink(missing_ok=True)
