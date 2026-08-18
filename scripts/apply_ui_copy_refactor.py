"""Apply the reviewed Ask Dashboard UI-copy integration to app.py.

This is intentionally a one-shot, exact-match refactor helper for the
agent/localize-and-distill-ui branch. Every replacement asserts that the
expected source snippet exists exactly once so an unexpected app.py revision
fails instead of being modified ambiguously.
"""

from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main():
    text = APP_PATH.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "from data_loading import coerce_numeric_columns\n",
        "from data_loading import coerce_numeric_columns\n"
        "from ui_copy import (\n"
        "    FEEDBACK_CHOICES,\n"
        "    FEEDBACK_REASON_CODES,\n"
        "    FEEDBACK_REASON_KEYS,\n"
        "    feedback_choice_label,\n"
        "    feedback_reason_label,\n"
        "    suggested_question_label,\n"
        "    ui_text,\n"
        ")\n",
        "ui_copy import",
    )

    text = replace_once(
        text,
        "def t(key):\n"
        "    lang = st.session_state.get(\"lang\", \"en\")\n"
        "    return TEXT.get(lang, {}).get(key, TEXT[\"en\"].get(key, key))\n",
        "def t(key):\n"
        "    lang = st.session_state.get(\"lang\", \"en\")\n"
        "    return TEXT.get(lang, {}).get(key, TEXT[\"en\"].get(key, key))\n\n"
        "def ask_t(key, **values):\n"
        "    return ui_text(st.session_state.get(\"lang\", \"en\"), key, **values)\n",
        "ask_t helper",
    )

    text = replace_once(
        text,
        "@st.dialog(\"Ask the Dashboard\", width=\"large\")\n",
        "@st.dialog(ask_t(\"ask_dashboard\"), width=\"large\")\n",
        "localized dialog title",
    )

    text = replace_once(
        text,
        "    alliance_scope = \", \".join(map(str, selected_alliances)) or \"None\"\n"
        "    status_scope = \", \".join(map(str, selected_net_status)) or \"None\"\n",
        "    alliance_scope = \", \".join(map(str, selected_alliances)) or ask_t(\"none\")\n"
        "    status_scope = (\n"
        "        \", \".join(translate_net_status(status) for status in selected_net_status)\n"
        "        or ask_t(\"none\")\n"
        "    )\n",
        "localized scope values",
    )

    text = replace_once(
        text,
        "    st.caption(\n"
        "        f\"Current scope — SVS: {selected_svs} | \"\n"
        "        f\"Alliances: {alliance_scope} | Net status: {status_scope} | \"\n"
        "        f\"Included players: {len(current_selected_players)}/\"\n"
        "        f\"{total_players_in_scope}\"\n"
        "    )\n",
        "    st.caption(\n"
        "        ask_t(\n"
        "            \"current_scope\",\n"
        "            svs=selected_svs,\n"
        "            alliances=alliance_scope,\n"
        "            net_status=status_scope,\n"
        "            included=len(current_selected_players),\n"
        "            total=total_players_in_scope,\n"
        "        )\n"
        "    )\n",
        "localized scope caption",
    )

    text = replace_once(
        text,
        "    with st.expander(\"Preview analytics & privacy\", expanded=False):\n",
        "    with st.expander(ask_t(\"analytics_privacy\"), expanded=False):\n",
        "localized privacy expander",
    )

    privacy_replacements = [
        (
            "            st.caption(\n"
            "                \"Anonymous routing metadata and feedback are saved to a best-effort local file \"\n"
            "                \"on this running preview instance. It can persist across browser sessions, but \"\n"
            "                \"may reset when Streamlit restarts or redeploys.\"\n"
            "            )\n",
            "            st.caption(ask_t(\"analytics_local\"))\n",
            "local analytics copy",
        ),
        (
            "            st.caption(\n"
            "                \"Anonymous routing metadata and feedback are sent to the configured HTTPS \"\n"
            "                \"analytics endpoint.\"\n"
            "            )\n",
            "            st.caption(ask_t(\"analytics_webhook\"))\n",
            "webhook analytics copy",
        ),
        (
            "            st.caption(\"Persistent preview analytics are currently disabled.\")\n",
            "            st.caption(ask_t(\"analytics_disabled\"))\n",
            "disabled analytics copy",
        ),
        (
            "        st.caption(\n"
            "            \"A custom question and its generated answer are saved only when you explicitly opt in. \"\n"
            "            \"The analytics event does not collect IP addresses, browser fingerprints, API keys, \"\n"
            "            \"score rows, or selected player names.\"\n"
            "        )\n",
            "        st.caption(ask_t(\"analytics_opt_in\"))\n",
            "analytics opt-in copy",
        ),
    ]
    for old, new, label in privacy_replacements:
        text = replace_once(text, old, new, label)

    text = replace_once(
        text,
        "    suggested_question = st.selectbox(\n"
        "        \"Choose a suggested question\",\n"
        "        SUGGESTED_QUESTIONS,\n"
        "    )\n",
        "    suggested_question = st.selectbox(\n"
        "        ask_t(\"choose_suggested_question\"),\n"
        "        SUGGESTED_QUESTIONS,\n"
        "        format_func=lambda value: suggested_question_label(\n"
        "            st.session_state.get(\"lang\", \"en\"), value\n"
        "        ),\n"
        "    )\n",
        "localized suggested questions",
    )

    text = replace_once(
        text,
        "        st.caption(\n"
        "            \"Need help? Start with “help” to learn how to use the dashboard, \"\n"
        "            \"or ask your question directly. Free-text questions use rule-first routing. Supported \"\n"
        "            \"topics include alliance ranking, player exclusions, negative \"\n"
        "            \"share, top contributors, and total net score without named \"\n"
        "            \"alliances.\"\n"
        "        )\n"
        "        custom_question = st.text_area(\n"
        "            \"Enter your question\",\n"
        "            placeholder=(\n"
        "                \"Try: Top net score player — or type help\"\n"
        "            ),\n"
        "        )\n\n"
        "        include_full_text = st.checkbox(\n"
        "            \"Allow this custom question and its generated answer to be saved for improving Ask Dashboard\",\n"
        "            value=False,\n"
        "            help=(\n"
        "                \"When unchecked, only anonymous routing metadata is saved. Avoid entering private \"\n"
        "                \"information even when opting in.\"\n"
        "            ),\n"
        "        )\n",
        "        st.info(ask_t(\"custom_question_notice\"))\n"
        "        st.caption(ask_t(\"custom_question_help\"))\n"
        "        custom_question = st.text_area(\n"
        "            ask_t(\"enter_question\"),\n"
        "            placeholder=ask_t(\"question_placeholder\"),\n"
        "        )\n\n"
        "        include_full_text = st.checkbox(\n"
        "            ask_t(\"allow_save_text\"),\n"
        "            value=False,\n"
        "            help=ask_t(\"allow_save_help\"),\n"
        "        )\n",
        "localized custom question controls",
    )

    text = replace_once(
        text,
        "        \"Explain\",\n"
        "        type=\"primary\",\n",
        "        ask_t(\"explain\"),\n"
        "        type=\"primary\",\n",
        "localized explain button",
    )

    text = replace_once(
        text,
        "        st.markdown(\"### Explanation\")\n",
        "        st.subheader(ask_t(\"explanation\"))\n",
        "localized explanation heading",
    )

    text = replace_once(
        text,
        "            st.info(\n"
        "                \"Feedback is temporarily unavailable because analytics delivery \"\n"
        "                \"for this answer has not been confirmed.\"\n"
        "            )\n",
        "            st.info(ask_t(\"feedback_pending\"))\n",
        "localized feedback pending",
    )

    text = replace_once(
        text,
        "                \"Retry analytics connection\",\n",
        "                ask_t(\"retry_analytics\"),\n",
        "localized retry button",
    )

    text = replace_once(
        text,
        "                    st.warning(\n"
        "                        \"Analytics delivery still could not be confirmed. The answer \"\n"
        "                        \"remains available, and retrying the same event is safe.\"\n"
        "                    )\n",
        "                    st.warning(ask_t(\"retry_failed\"))\n",
        "localized retry warning",
    )

    text = replace_once(
        text,
        "                st.success(\"Thank you — your feedback was recorded.\")\n",
        "                st.success(ask_t(\"feedback_recorded\"))\n",
        "localized feedback success",
    )

    text = replace_once(
        text,
        "                st.markdown(\"#### Was this answer helpful?\")\n"
        "                feedback_choice = st.radio(\n"
        "                    \"Answer quality\",\n"
        "                    [\"Choose…\", \"Helpful\", \"Not helpful\"],\n"
        "                    horizontal=True,\n"
        "                    label_visibility=\"collapsed\",\n"
        "                    key=f\"ask_dashboard_feedback_choice_{last_answer_event_id}\",\n"
        "                )\n"
        "                feedback_reason = None\n"
        "                if feedback_choice == \"Not helpful\":\n"
        "                    reason_label = st.selectbox(\n"
        "                        \"What went wrong?\",\n"
        "                        [\n"
        "                            \"It misunderstood my question\",\n"
        "                            \"The answer was incorrect\",\n"
        "                            \"My question is not supported\",\n"
        "                            \"The answer was unclear\",\n"
        "                            \"Other\",\n"
        "                        ],\n"
        "                        key=f\"ask_dashboard_feedback_reason_{last_answer_event_id}\",\n"
        "                    )\n"
        "                    feedback_reason = {\n"
        "                        \"It misunderstood my question\": \"misunderstood_question\",\n"
        "                        \"The answer was incorrect\": \"wrong_answer\",\n"
        "                        \"My question is not supported\": \"unsupported_question\",\n"
        "                        \"The answer was unclear\": \"unclear_answer\",\n"
        "                        \"Other\": \"other\",\n"
        "                    }[reason_label]\n"
        "                elif feedback_choice == \"Helpful\":\n"
        "                    feedback_reason = \"correct_and_clear\"\n\n"
        "                feedback_comment = st.text_area(\n"
        "                    \"Optional comment\",\n"
        "                    placeholder=\"Tell us what worked or what you expected. Do not include private information.\",\n"
        "                    key=f\"ask_dashboard_feedback_comment_{last_answer_event_id}\",\n"
        "                )\n"
        "                if st.button(\n"
        "                    \"Submit feedback\",\n"
        "                    disabled=feedback_choice == \"Choose…\",\n",
        "                st.markdown(f\"#### {ask_t('was_helpful')}\")\n"
        "                feedback_choice = st.radio(\n"
        "                    ask_t(\"was_helpful\"),\n"
        "                    FEEDBACK_CHOICES,\n"
        "                    format_func=lambda value: feedback_choice_label(\n"
        "                        st.session_state.get(\"lang\", \"en\"), value\n"
        "                    ),\n"
        "                    horizontal=True,\n"
        "                    label_visibility=\"collapsed\",\n"
        "                    key=f\"ask_dashboard_feedback_choice_{last_answer_event_id}\",\n"
        "                )\n"
        "                feedback_reason = None\n"
        "                if feedback_choice == \"not_helpful\":\n"
        "                    reason_key = st.selectbox(\n"
        "                        ask_t(\"what_went_wrong\"),\n"
        "                        FEEDBACK_REASON_KEYS,\n"
        "                        format_func=lambda value: feedback_reason_label(\n"
        "                            st.session_state.get(\"lang\", \"en\"), value\n"
        "                        ),\n"
        "                        key=f\"ask_dashboard_feedback_reason_{last_answer_event_id}\",\n"
        "                    )\n"
        "                    feedback_reason = FEEDBACK_REASON_CODES[reason_key]\n"
        "                elif feedback_choice == \"helpful\":\n"
        "                    feedback_reason = \"correct_and_clear\"\n\n"
        "                feedback_comment = st.text_area(\n"
        "                    ask_t(\"optional_comment\"),\n"
        "                    placeholder=ask_t(\"comment_placeholder\"),\n"
        "                    key=f\"ask_dashboard_feedback_comment_{last_answer_event_id}\",\n"
        "                )\n"
        "                if st.button(\n"
        "                    ask_t(\"submit_feedback\"),\n"
        "                    disabled=feedback_choice == \"choose\",\n",
        "localized feedback controls",
    )

    text = replace_once(
        text,
        "                            helpful=feedback_choice == \"Helpful\",\n",
        "                            helpful=feedback_choice == \"helpful\",\n",
        "stable localized feedback boolean",
    )

    warning = (
        "st.warning(\"Feedback delivery could not be confirmed. You can retry safely; "
        "retries for the same answer will not create another feedback record.\")"
    )
    count = text.count(warning)
    if count != 2:
        raise RuntimeError(f"localized feedback failure: expected 2 matches, found {count}")
    text = text.replace(warning, "st.warning(ask_t(\"feedback_delivery_failed\"))")

    text = replace_once(
        text,
        "if st.button(\"💬 Ask the Dashboard\", type=\"primary\"):\n",
        "if st.button(f\"💬 {ask_t('ask_dashboard')}\", type=\"primary\"):\n",
        "localized Ask Dashboard launcher",
    )

    # Remove tab labels that are immediately repeated as large headings.
    text = replace_once(
        text,
        "with tab_overview:\n    st.subheader(t(\"overview\"))\n\n",
        "with tab_overview:\n",
        "remove duplicate Overview heading",
    )
    text = replace_once(
        text,
        "with tab_alliance:\n    st.subheader(t(\"alliance_summary\"))\n    st.caption(\n",
        "with tab_alliance:\n    st.caption(\n",
        "remove duplicate Alliance Summary heading",
    )
    text = replace_once(
        text,
        "with tab_contribution:\n    st.header(t(\"contribution_insight\"))\n    st.caption(t(\"contribution_insight_caption\"))\n",
        "with tab_contribution:\n    st.caption(t(\"contribution_insight_caption\"))\n",
        "remove duplicate Contribution heading",
    )
    text = replace_once(
        text,
        "with tab_player_selection:\n    st.header(t(\"player_selection_insight\"))\n    st.caption(t(\"player_selection_insight_caption\"))\n",
        "with tab_player_selection:\n    st.caption(t(\"player_selection_insight_caption\"))\n",
        "remove duplicate Player Selection heading",
    )

    APP_PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
