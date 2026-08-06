from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"
USAGE_PATH = ROOT / "usage_analytics.py"
TEST_PATH = ROOT / "test_usage_analytics.py"
SELF_PATH = Path(__file__)


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# Password verification is a pure helper so it can be regression-tested without
# importing Streamlit.
replace_once(
    USAGE_PATH,
    "from datetime import datetime, timezone\n",
    "from datetime import datetime, timezone\nfrom hmac import compare_digest\n",
    "compare digest import",
)
replace_once(
    USAGE_PATH,
    "\ndef feedback_event_id_for_answer(answer_event_id: str) -> str:\n",
    '''\ndef admin_password_matches(entered_password: Any, expected_password: Any) -> bool:\n    """Return True only for a configured, exact developer password match."""\n    if expected_password is None or str(expected_password) == "":\n        return False\n    return compare_digest(\n        str(entered_password or ""),\n        str(expected_password),\n    )\n\n\ndef feedback_event_id_for_answer(answer_event_id: str) -> str:\n''',
    "admin password helper",
)

# Import the helper into the Streamlit app.
replace_once(
    APP_PATH,
    "from usage_analytics import (\n    DEFAULT_LOCAL_PATH,\n",
    "from usage_analytics import (\n    DEFAULT_LOCAL_PATH,\n    admin_password_matches,\n",
    "analytics helper import",
)

# Preserve the exact answer event when delivery is uncertain so the UI can
# retry safely instead of silently removing feedback controls.
old_answer_persist = '''        rendered_answer = render_dashboard_answer(answer)
        try:
            answer_event = build_answer_event(
                answer,
                rendered_answer,
                question_kind=question_kind,
                ui_language=st.session_state.get("lang", "en"),
                suggested_question=(
                    suggested_question if question_kind == "suggested" else None
                ),
                include_full_text=include_full_text,
                selected_alliance_count=len(selected_alliances),
                selected_net_status_count=len(selected_net_status),
                selected_player_count=len(current_selected_players),
                total_player_count=total_players_in_scope,
                app_version=analytics_config["app_version"],
            )
            analytics_result = _persist_preview_analytics(answer_event)
            if analytics_result.get("ok"):
                st.session_state["ask_dashboard_last_answer_event_id"] = answer_event["event_id"]
                st.session_state["ask_dashboard_feedback_submitted_for"] = None
            else:
                st.session_state.pop("ask_dashboard_last_answer_event_id", None)
        except Exception as exc:
            st.session_state["ask_dashboard_analytics_last_result"] = {
                "ok": False,
                "mode": _analytics_config()["mode"],
                "diagnostic": f"{type(exc).__name__}",
            }
            st.session_state.pop("ask_dashboard_last_answer_event_id", None)

        st.session_state["ask_dashboard_last_question"] = question
'''
new_answer_persist = '''        rendered_answer = render_dashboard_answer(answer)
        st.session_state.pop("ask_dashboard_pending_answer_event", None)
        st.session_state.pop("ask_dashboard_last_answer_event_id", None)
        answer_event = None
        try:
            answer_event = build_answer_event(
                answer,
                rendered_answer,
                question_kind=question_kind,
                ui_language=st.session_state.get("lang", "en"),
                suggested_question=(
                    suggested_question if question_kind == "suggested" else None
                ),
                include_full_text=include_full_text,
                selected_alliance_count=len(selected_alliances),
                selected_net_status_count=len(selected_net_status),
                selected_player_count=len(current_selected_players),
                total_player_count=total_players_in_scope,
                app_version=analytics_config["app_version"],
            )
            # Keep the exact event until delivery is confirmed. The receiver is
            # idempotent by event_id, so retrying this object is safe even if the
            # first response was lost after the row was appended.
            st.session_state["ask_dashboard_pending_answer_event"] = answer_event
            analytics_result = _persist_preview_analytics(answer_event)
            if analytics_result.get("ok"):
                st.session_state["ask_dashboard_last_answer_event_id"] = answer_event["event_id"]
                st.session_state["ask_dashboard_feedback_submitted_for"] = None
                st.session_state.pop("ask_dashboard_pending_answer_event", None)
        except Exception as exc:
            st.session_state["ask_dashboard_analytics_last_result"] = {
                "ok": False,
                "mode": _analytics_config()["mode"],
                "diagnostic": f"{type(exc).__name__}",
            }
            if answer_event is None:
                st.session_state.pop("ask_dashboard_pending_answer_event", None)

        st.session_state["ask_dashboard_last_question"] = question
'''
replace_once(APP_PATH, old_answer_persist, new_answer_persist, "answer persistence")

old_feedback_entry = '''    last_question = st.session_state.get("ask_dashboard_last_question")
    last_rendered_answer = st.session_state.get("ask_dashboard_last_rendered_answer")
    last_answer_event_id = st.session_state.get("ask_dashboard_last_answer_event_id")
    if last_rendered_answer and last_question == question:
        st.markdown("### Explanation")
        st.markdown(last_rendered_answer)

        if last_answer_event_id:
'''
new_feedback_entry = '''    last_question = st.session_state.get("ask_dashboard_last_question")
    last_rendered_answer = st.session_state.get("ask_dashboard_last_rendered_answer")
    last_answer_event_id = st.session_state.get("ask_dashboard_last_answer_event_id")
    pending_answer_event = st.session_state.get("ask_dashboard_pending_answer_event")
    if last_rendered_answer and last_question == question:
        st.markdown("### Explanation")
        st.markdown(last_rendered_answer)

        if not last_answer_event_id and isinstance(pending_answer_event, dict):
            st.info(
                "Feedback is temporarily unavailable because analytics delivery "
                "for this answer has not been confirmed."
            )
            if st.button(
                "Retry analytics connection",
                key=f"ask_dashboard_retry_answer_{pending_answer_event.get('event_id', 'pending')}",
            ):
                retry_result = _persist_preview_analytics(pending_answer_event)
                if retry_result.get("ok"):
                    st.session_state["ask_dashboard_last_answer_event_id"] = pending_answer_event["event_id"]
                    st.session_state["ask_dashboard_feedback_submitted_for"] = None
                    st.session_state.pop("ask_dashboard_pending_answer_event", None)
                    st.rerun()
                else:
                    st.warning(
                        "Analytics delivery still could not be confirmed. The answer "
                        "remains available, and retrying the same event is safe."
                    )

        if last_answer_event_id:
'''
replace_once(APP_PATH, old_feedback_entry, new_feedback_entry, "feedback retry entry")

# Replace the entire developer section. Nothing from the session log or
# persistent backend is rendered until the configured password is accepted.
app_text = APP_PATH.read_text(encoding="utf-8")
start_marker = '    if _truthy_setting("ASK_DASHBOARD_DEBUG_LOG"):\n'
end_marker = '\n\n\nif st.button("💬 Ask the Dashboard", type="primary"):'
start = app_text.find(start_marker)
end = app_text.find(end_marker, start)
if start < 0 or end < 0 or app_text.find(start_marker, start + 1) >= 0:
    raise RuntimeError("developer section anchors changed")

new_developer_section = '''    if _truthy_setting("ASK_DASHBOARD_DEBUG_LOG"):
        with st.expander("Developer: Question analysis log", expanded=False):
            admin_password = _secret_or_env("ASK_DASHBOARD_ANALYTICS_ADMIN_PASSWORD")
            if not admin_password:
                st.caption(
                    "Developer tools are disabled because no analytics admin password is configured."
                )
            else:
                entered_password = st.text_input(
                    "Analytics admin password",
                    type="password",
                    key="ask_dashboard_analytics_admin_password_input",
                )
                if not admin_password_matches(entered_password, admin_password):
                    st.caption(
                        "Enter the analytics admin password to view, download, or clear developer logs."
                    )
                    if entered_password:
                        st.error("Incorrect analytics admin password.")
                else:
                    records = st.session_state.get("ask_dashboard_question_log", [])
                    st.caption(f"{len(records)} record(s) in the current Streamlit session.")
                    logging_error = st.session_state.get("ask_dashboard_logging_error")
                    if logging_error:
                        st.caption(f"Last logging diagnostic: {logging_error}")
                    last_routing = st.session_state.get("ask_dashboard_last_routing", {})
                    if records:
                        last_record = records[-1]
                        st.caption(
                            f"Routing source: {last_routing.get('source') or last_record.get('source', 'rule')}"
                        )
                    if last_routing:
                        st.caption(
                            f"AI attempted: {'yes' if last_routing.get('ai_attempted') else 'no'}"
                        )
                    ai_diagnostic = st.session_state.get("ask_dashboard_ai_diagnostic")
                    if ai_diagnostic:
                        st.caption(f"AI diagnostic: {ai_diagnostic}")
                    if records:
                        st.dataframe(records, use_container_width=True)
                        st.download_button(
                            "Download session log JSON",
                            data=json.dumps(records, indent=2),
                            file_name="ask_dashboard_question_log.json",
                            mime="application/json",
                        )

                    analytics_config = _analytics_config()
                    analytics_result = st.session_state.get(
                        "ask_dashboard_analytics_last_result"
                    )
                    if analytics_result:
                        st.caption(
                            f"Persistent analytics mode: {analytics_result.get('mode')} | "
                            f"last write: {'ok' if analytics_result.get('ok') else analytics_result.get('diagnostic')}"
                        )
                    if analytics_config["mode"] == "local":
                        persistent_events, malformed_count = load_local_events(
                            analytics_config["local_path"]
                        )
                        summary = summarize_events(persistent_events)
                        metric_columns = st.columns(4)
                        metric_columns[0].metric("Answers", summary["answer_count"])
                        metric_columns[1].metric("Feedback", summary["feedback_count"])
                        helpful_rate = summary["helpful_rate"]
                        metric_columns[2].metric(
                            "Helpful rate",
                            "—" if helpful_rate is None else f"{helpful_rate:.1f}%",
                        )
                        unsupported_rate = summary["unsupported_rate"]
                        metric_columns[3].metric(
                            "Unsupported rate",
                            "—" if unsupported_rate is None else f"{unsupported_rate:.1f}%",
                        )
                        if malformed_count:
                            st.caption(
                                f"Skipped malformed analytics records: {malformed_count}"
                            )
                        st.json(summary)
                        if persistent_events:
                            st.dataframe(persistent_events, use_container_width=True)
                            st.download_button(
                                "Download persistent analytics JSON",
                                data=json.dumps(
                                    persistent_events,
                                    ensure_ascii=False,
                                    indent=2,
                                ),
                                file_name="ask_dashboard_persistent_analytics.json",
                                mime="application/json",
                            )
                    elif analytics_config["mode"] == "webhook":
                        st.caption(
                            "Webhook events are reviewed in the configured analytics backend."
                        )

                    if st.button("Clear question analysis log"):
                        st.session_state["ask_dashboard_question_log"] = []
                        st.rerun()
'''
APP_PATH.write_text(app_text[:start] + new_developer_section + app_text[end:], encoding="utf-8")

# Regression tests for the password gate helper.
test_text = TEST_PATH.read_text(encoding="utf-8")
replace_anchor = "    MAX_QUESTION_CHARS,\n"
if test_text.count(replace_anchor) != 1:
    raise RuntimeError("test import anchor changed")
test_text = test_text.replace(
    replace_anchor,
    replace_anchor + "    admin_password_matches,\n",
    1,
)
insert_anchor = "\n\ndef sample_answer(question=\"Why did the negative percentage increase?\"):\n"
if test_text.count(insert_anchor) != 1:
    raise RuntimeError("test function anchor changed")
test_text = test_text.replace(
    insert_anchor,
    '''\n\ndef test_admin_password_gate_requires_configured_exact_match():
    assert admin_password_matches("correct", "correct") is True
    assert admin_password_matches("wrong", "correct") is False
    assert admin_password_matches("", "correct") is False
    assert admin_password_matches("anything", "") is False
    assert admin_password_matches("anything", None) is False
\n\ndef sample_answer(question="Why did the negative percentage increase?"):\n''',
    1,
)
TEST_PATH.write_text(test_text, encoding="utf-8")

# Remove the one-time patch script from the resulting branch commit.
SELF_PATH.unlink(missing_ok=True)
