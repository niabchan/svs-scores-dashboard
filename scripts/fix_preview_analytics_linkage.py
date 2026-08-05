from pathlib import Path

APP_PATH = Path("app.py")
WORKFLOW_PATH = Path(".github/workflows/fix-preview-analytics-linkage.yml")
SCRIPT_PATH = Path(__file__)

text = APP_PATH.read_text(encoding="utf-8")
old = '''            _persist_preview_analytics(answer_event)
            st.session_state["ask_dashboard_last_answer_event_id"] = answer_event["event_id"]
            st.session_state["ask_dashboard_feedback_submitted_for"] = None
'''
new = '''            analytics_result = _persist_preview_analytics(answer_event)
            if analytics_result.get("ok"):
                st.session_state["ask_dashboard_last_answer_event_id"] = answer_event["event_id"]
                st.session_state["ask_dashboard_feedback_submitted_for"] = None
            else:
                st.session_state.pop("ask_dashboard_last_answer_event_id", None)
'''
if old not in text:
    raise RuntimeError("answer analytics linkage anchor not found")
text = text.replace(old, new, 1)
APP_PATH.write_text(text, encoding="utf-8")
WORKFLOW_PATH.unlink(missing_ok=True)
SCRIPT_PATH.unlink(missing_ok=True)
