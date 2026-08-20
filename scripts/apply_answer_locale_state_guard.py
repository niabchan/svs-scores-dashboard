from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


path = Path("app.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '        st.session_state["ask_dashboard_last_question"] = question\n'
    '        st.session_state["ask_dashboard_last_rendered_answer"] = rendered_answer\n',
    '        st.session_state["ask_dashboard_last_question"] = question\n'
    '        st.session_state["ask_dashboard_last_rendered_answer"] = rendered_answer\n'
    '        st.session_state["ask_dashboard_last_answer_locale"] = st.session_state.get("lang", "en")\n',
    "store answer locale",
)
text = replace_once(
    text,
    '    last_rendered_answer = st.session_state.get("ask_dashboard_last_rendered_answer")\n'
    '    last_answer_event_id = st.session_state.get("ask_dashboard_last_answer_event_id")\n',
    '    last_rendered_answer = st.session_state.get("ask_dashboard_last_rendered_answer")\n'
    '    last_answer_locale = st.session_state.get("ask_dashboard_last_answer_locale")\n'
    '    last_answer_event_id = st.session_state.get("ask_dashboard_last_answer_event_id")\n',
    "load answer locale",
)
text = replace_once(
    text,
    '    if last_rendered_answer and last_question == question:\n',
    '    if (\n'
    '        last_rendered_answer\n'
    '        and last_question == question\n'
    '        and last_answer_locale == st.session_state.get("lang", "en")\n'
    '    ):\n',
    "guard answer by locale",
)
path.write_text(text, encoding="utf-8")
