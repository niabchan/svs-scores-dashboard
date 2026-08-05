from pathlib import Path


APP_PATH = Path("app.py")
WORKFLOW_PATH = Path(".github/workflows/apply-preview-analytics.yml")
SCRIPT_PATH = Path(__file__)

text = APP_PATH.read_text(encoding="utf-8")

import_anchor = '''from ask_dashboard import (
    QUESTION_CUSTOM,
    QUESTION_EXCLUSION_IMPACT,
    QUESTION_NEGATIVE_PERCENTAGE,
    QUESTION_NET_VS_POSITIVE,
    QUESTION_TOP_CONTRIBUTORS,
    SUGGESTED_QUESTIONS,
    calculate_dashboard_answer,
    route_dashboard_question_hybrid,
    safely_append_question_log_record,
    render_dashboard_answer,
)
'''
analytics_import = import_anchor + '''from usage_analytics import (
    DEFAULT_LOCAL_PATH,
    build_answer_event,
    build_feedback_event,
    load_local_events,
    safely_persist_event,
    summarize_events,
)
'''
if "from usage_analytics import (" not in text:
    if text.count(import_anchor) != 1:
        raise RuntimeError("Ask Dashboard import anchor not found exactly once")
    text = text.replace(import_anchor, analytics_import, 1)

secret_anchor = '''def _secret_or_env(name):
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.environ.get(name)


'''
analytics_helpers = secret_anchor + '''def _truthy_setting(name):
    return str(_secret_or_env(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _analytics_config():
    return {
        "mode": str(_secret_or_env("ASK_DASHBOARD_ANALYTICS_MODE") or "local").strip().lower(),
        "local_path": str(
            _secret_or_env("ASK_DASHBOARD_ANALYTICS_LOCAL_PATH") or DEFAULT_LOCAL_PATH
        ),
        "endpoint": _secret_or_env("ASK_DASHBOARD_ANALYTICS_ENDPOINT"),
        "bearer_token": _secret_or_env("ASK_DASHBOARD_ANALYTICS_TOKEN"),
    }


def _persist_preview_analytics(event):
    config = _analytics_config()
    result = safely_persist_event(
        event,
        mode=config["mode"],
        local_path=config["local_path"],
        endpoint=config["endpoint"],
        bearer_token=config["bearer_token"],
    )
    st.session_state["ask_dashboard_analytics_last_result"] = result
    return result


'''
if "def _analytics_config():" not in text:
    if text.count(secret_anchor) != 1:
        raise RuntimeError("secret helper anchor not found exactly once")
    text = text.replace(secret_anchor, analytics_helpers, 1)

scope_anchor = '''    st.caption(
        f"Current scope — SVS: {selected_svs} | "
        f"Alliances: {alliance_scope} | Net status: {status_scope} | "
        f"Included players: {len(current_selected_players)}/"
        f"{total_players_in_scope}"
    )

'''
privacy_block = scope_anchor + '''    analytics_config = _analytics_config()
    with st.expander("Preview analytics & privacy", expanded=False):
        if analytics_config["mode"] == "local":
            st.caption(
                "Anonymous routing metadata and feedback are saved to a best-effort local file "
                "on this running preview instance. It can persist across browser sessions, but "
                "may reset when Streamlit restarts or redeploys."
            )
        elif analytics_config["mode"] == "webhook":
            st.caption(
                "Anonymous routing metadata and feedback are sent to the configured HTTPS "
                "analytics endpoint."
            )
        else:
            st.caption("Persistent preview analytics are currently disabled.")
        st.caption(
            "A custom question and its generated answer are saved only when you explicitly opt in. "
            "The analytics event does not collect IP addresses, browser fingerprints, API keys, "
            "score rows, or selected player names."
        )

'''
if "Preview analytics & privacy" not in text:
    if text.count(scope_anchor) != 1:
        raise RuntimeError("scope caption anchor not found exactly once")
    text = text.replace(scope_anchor, privacy_block, 1)

custom_anchor = '''    custom_question = ""

    if suggested_question == QUESTION_CUSTOM:
'''
custom_replacement = '''    custom_question = ""
    include_full_text = False

    if suggested_question == QUESTION_CUSTOM:
'''
if "include_full_text = False" not in text:
    if text.count(custom_anchor) != 1:
        raise RuntimeError("custom question anchor not found exactly once")
    text = text.replace(custom_anchor, custom_replacement, 1)

textarea_anchor = '''        custom_question = st.text_area(
            "Enter your question",
            placeholder=(
                "Try: Top net score player — or type help"
            ),
        )

'''
consent_block = textarea_anchor + '''        include_full_text = st.checkbox(
            "Allow this custom question and its generated answer to be saved for improving Ask Dashboard",
            value=False,
            help=(
                "When unchecked, only anonymous routing metadata is saved. Avoid entering private "
                "information even when opting in."
            ),
        )

'''
if "Allow this custom question and its generated answer" not in text:
    if text.count(textarea_anchor) != 1:
        raise RuntimeError("custom text-area anchor not found exactly once")
    text = text.replace(textarea_anchor, consent_block, 1)

question_anchor = '''    question = (
        custom_question.strip()
        if suggested_question == QUESTION_CUSTOM
        else suggested_question
    )

'''
question_replacement = question_anchor + '''    question_kind = (
        "custom" if suggested_question == QUESTION_CUSTOM else "suggested"
    )

'''
if "question_kind = (" not in text:
    if text.count(question_anchor) != 1:
        raise RuntimeError("question assignment anchor not found exactly once")
    text = text.replace(question_anchor, question_replacement, 1)

start_marker = '''    if st.button(
        "Explain",
        type="primary",
        disabled=not question,
    ):
'''
end_marker = '''    if os.environ.get("ASK_DASHBOARD_DEBUG_LOG", "").strip().lower() in {"1", "true", "yes", "on"}:
'''
start = text.find(start_marker)
end = text.find(end_marker)
if start == -1 or end == -1 or end <= start:
    raise RuntimeError("Ask Dashboard action block markers not found")

new_action_block = '''    if st.button(
        "Explain",
        type="primary",
        disabled=not question,
    ):
        answer = calculate_dashboard_answer(
            question,
            filtered_df,
            selected_svs,
            current_selected_players,
            alliance_options,
            intent_router=_build_ai_intent_router(),
        )
        routing = answer.get("routing", {})
        routing_diagnostics = answer.get("routing_diagnostics", {})
        st.session_state["ask_dashboard_last_routing"] = {
            "source": routing.get("source", "rule"),
            "ai_attempted": bool(routing_diagnostics.get("ai_attempted", False)),
            "diagnostic_code": routing_diagnostics.get("diagnostic_code"),
        }
        if routing_diagnostics.get("diagnostic_code"):
            st.session_state["ask_dashboard_ai_diagnostic"] = routing_diagnostics.get("diagnostic_code")
        elif routing_diagnostics.get("ai_attempted"):
            st.session_state.pop("ask_dashboard_ai_diagnostic", None)
        records, logging_error = safely_append_question_log_record(
            st.session_state.get("ask_dashboard_question_log", []),
            answer,
            selected_alliances=selected_alliances,
            selected_net_status=selected_net_status,
            selected_player_count=len(current_selected_players),
            total_player_count=total_players_in_scope,
            max_entries=100,
        )
        st.session_state["ask_dashboard_question_log"] = records
        if logging_error:
            st.session_state["ask_dashboard_logging_error"] = logging_error
        else:
            st.session_state.pop("ask_dashboard_logging_error", None)

        rendered_answer = render_dashboard_answer(answer)
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
            )
            _persist_preview_analytics(answer_event)
            st.session_state["ask_dashboard_last_answer_event_id"] = answer_event["event_id"]
            st.session_state["ask_dashboard_feedback_submitted_for"] = None
        except Exception as exc:
            st.session_state["ask_dashboard_analytics_last_result"] = {
                "ok": False,
                "mode": _analytics_config()["mode"],
                "diagnostic": f"{type(exc).__name__}",
            }
            st.session_state.pop("ask_dashboard_last_answer_event_id", None)

        st.session_state["ask_dashboard_last_question"] = question
        st.session_state["ask_dashboard_last_rendered_answer"] = rendered_answer

    last_question = st.session_state.get("ask_dashboard_last_question")
    last_rendered_answer = st.session_state.get("ask_dashboard_last_rendered_answer")
    last_answer_event_id = st.session_state.get("ask_dashboard_last_answer_event_id")
    if last_rendered_answer and last_question == question:
        st.markdown("### Explanation")
        st.markdown(last_rendered_answer)

        if last_answer_event_id:
            if st.session_state.get("ask_dashboard_feedback_submitted_for") == last_answer_event_id:
                st.success("Thank you — your feedback was recorded.")
            else:
                st.markdown("#### Was this answer helpful?")
                feedback_choice = st.radio(
                    "Answer quality",
                    ["Choose…", "Helpful", "Not helpful"],
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"ask_dashboard_feedback_choice_{last_answer_event_id}",
                )
                feedback_reason = None
                if feedback_choice == "Not helpful":
                    reason_label = st.selectbox(
                        "What went wrong?",
                        [
                            "It misunderstood my question",
                            "The answer was incorrect",
                            "My question is not supported",
                            "The answer was unclear",
                            "Other",
                        ],
                        key=f"ask_dashboard_feedback_reason_{last_answer_event_id}",
                    )
                    feedback_reason = {
                        "It misunderstood my question": "misunderstood_question",
                        "The answer was incorrect": "wrong_answer",
                        "My question is not supported": "unsupported_question",
                        "The answer was unclear": "unclear_answer",
                        "Other": "other",
                    }[reason_label]
                elif feedback_choice == "Helpful":
                    feedback_reason = "correct_and_clear"

                feedback_comment = st.text_area(
                    "Optional comment",
                    placeholder="Tell us what worked or what you expected. Do not include private information.",
                    key=f"ask_dashboard_feedback_comment_{last_answer_event_id}",
                )
                if st.button(
                    "Submit feedback",
                    disabled=feedback_choice == "Choose…",
                    key=f"ask_dashboard_feedback_submit_{last_answer_event_id}",
                ):
                    try:
                        feedback_event = build_feedback_event(
                            last_answer_event_id,
                            helpful=feedback_choice == "Helpful",
                            reason=feedback_reason,
                            comment=feedback_comment.strip() or None,
                        )
                        result = _persist_preview_analytics(feedback_event)
                        if result.get("ok"):
                            st.session_state["ask_dashboard_feedback_submitted_for"] = last_answer_event_id
                            st.rerun()
                        else:
                            st.warning("Feedback could not be saved on this preview instance.")
                    except Exception:
                        st.warning("Feedback could not be saved on this preview instance.")

'''
text = text[:start] + new_action_block + text[end:]
text = text.replace(
    '    if os.environ.get("ASK_DASHBOARD_DEBUG_LOG", "").strip().lower() in {"1", "true", "yes", "on"}:\n',
    '    if _truthy_setting("ASK_DASHBOARD_DEBUG_LOG"):\n',
    1,
)

debug_anchor = '''            if records:
                st.dataframe(records, use_container_width=True)
                st.download_button(
                    "Download session log JSON",
                    data=json.dumps(records, indent=2),
                    file_name="ask_dashboard_question_log.json",
                    mime="application/json",
                )
            if st.button("Clear question analysis log"):
'''
expanded_debug = '''            if records:
                st.dataframe(records, use_container_width=True)
                st.download_button(
                    "Download session log JSON",
                    data=json.dumps(records, indent=2),
                    file_name="ask_dashboard_question_log.json",
                    mime="application/json",
                )

            analytics_config = _analytics_config()
            analytics_result = st.session_state.get("ask_dashboard_analytics_last_result")
            if analytics_result:
                st.caption(
                    f"Persistent analytics mode: {analytics_result.get('mode')} | "
                    f"last write: {'ok' if analytics_result.get('ok') else analytics_result.get('diagnostic')}"
                )
            if analytics_config["mode"] == "local":
                admin_password = _secret_or_env("ASK_DASHBOARD_ANALYTICS_ADMIN_PASSWORD")
                if admin_password:
                    entered_password = st.text_input(
                        "Analytics admin password",
                        type="password",
                        key="ask_dashboard_analytics_admin_password_input",
                    )
                    if entered_password == str(admin_password):
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
                            st.caption(f"Skipped malformed analytics records: {malformed_count}")
                        st.json(summary)
                        if persistent_events:
                            st.dataframe(persistent_events, use_container_width=True)
                            st.download_button(
                                "Download persistent analytics JSON",
                                data=json.dumps(persistent_events, ensure_ascii=False, indent=2),
                                file_name="ask_dashboard_persistent_analytics.json",
                                mime="application/json",
                            )
                else:
                    st.caption(
                        "Set ASK_DASHBOARD_ANALYTICS_ADMIN_PASSWORD to enable local analytics review."
                    )
            elif analytics_config["mode"] == "webhook":
                st.caption(
                    "Webhook events are reviewed in the configured analytics backend."
                )

            if st.button("Clear question analysis log"):
'''
if debug_anchor not in text:
    raise RuntimeError("debug log anchor not found")
text = text.replace(debug_anchor, expanded_debug, 1)

APP_PATH.write_text(text, encoding="utf-8")
WORKFLOW_PATH.unlink(missing_ok=True)
SCRIPT_PATH.unlink(missing_ok=True)
