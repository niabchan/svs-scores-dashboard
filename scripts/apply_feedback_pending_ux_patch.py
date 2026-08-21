from pathlib import Path
import re


def replace_once_or_confirm(text, old, new, label):
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        return text.replace(old, new, 1)
    if old_count == 0 and new_count == 1:
        return text
    raise RuntimeError(
        f"{label}: expected one old or one new match, found old={old_count}, new={new_count}"
    )


# Hide analytics retry plumbing from normal answer UI while preserving safe retries.
path = Path("app.py")
text = path.read_text(encoding="utf-8")
new_marker = "        feedback_target_id = last_answer_event_id\n"
if new_marker not in text:
    start_marker = '        if not last_answer_event_id and isinstance(pending_answer_event, dict):\n'
    end_marker = '    if _truthy_setting("ASK_DASHBOARD_DEBUG_LOG"):\n'
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("could not locate pending feedback UI block")
    new_block = '''        feedback_target_id = last_answer_event_id
        if not feedback_target_id and isinstance(pending_answer_event, dict):
            feedback_target_id = pending_answer_event.get("event_id")

        if feedback_target_id:
            if st.session_state.get("ask_dashboard_feedback_submitted_for") == feedback_target_id:
                st.success(ask_t("feedback_recorded"))
            else:
                st.markdown(f"#### {ask_t('was_helpful')}")
                feedback_choice = st.radio(
                    ask_t("was_helpful"),
                    FEEDBACK_CHOICES,
                    format_func=lambda value: feedback_choice_label(
                        st.session_state.get("lang", "en"), value
                    ),
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"ask_dashboard_feedback_choice_{feedback_target_id}",
                )
                feedback_reason = None
                if feedback_choice == "not_helpful":
                    reason_key = st.selectbox(
                        ask_t("what_went_wrong"),
                        FEEDBACK_REASON_KEYS,
                        format_func=lambda value: feedback_reason_label(
                            st.session_state.get("lang", "en"), value
                        ),
                        key=f"ask_dashboard_feedback_reason_{feedback_target_id}",
                    )
                    feedback_reason = FEEDBACK_REASON_CODES[reason_key]
                elif feedback_choice == "helpful":
                    feedback_reason = "correct_and_clear"

                feedback_comment = st.text_area(
                    ask_t("optional_comment"),
                    placeholder=ask_t("comment_placeholder"),
                    key=f"ask_dashboard_feedback_comment_{feedback_target_id}",
                )
                if st.button(
                    ask_t("submit_feedback"),
                    disabled=feedback_choice == "choose",
                    key=f"ask_dashboard_feedback_submit_{feedback_target_id}",
                ):
                    try:
                        confirmed_answer_event_id = last_answer_event_id
                        if (
                            not confirmed_answer_event_id
                            and isinstance(pending_answer_event, dict)
                        ):
                            retry_result = _persist_preview_analytics(
                                pending_answer_event
                            )
                            if retry_result.get("ok"):
                                confirmed_answer_event_id = pending_answer_event.get(
                                    "event_id"
                                )
                                if confirmed_answer_event_id:
                                    st.session_state[
                                        "ask_dashboard_last_answer_event_id"
                                    ] = confirmed_answer_event_id
                                    st.session_state.pop(
                                        "ask_dashboard_pending_answer_event", None
                                    )

                        if not confirmed_answer_event_id:
                            st.warning(ask_t("feedback_delivery_failed"))
                        else:
                            feedback_event = build_feedback_event(
                                confirmed_answer_event_id,
                                helpful=feedback_choice == "helpful",
                                reason=feedback_reason,
                                comment=feedback_comment.strip() or None,
                                app_version=analytics_config["app_version"],
                            )
                            result = _persist_preview_analytics(feedback_event)
                            if result.get("ok"):
                                st.session_state[
                                    "ask_dashboard_feedback_submitted_for"
                                ] = confirmed_answer_event_id
                                st.rerun()
                            else:
                                st.warning(ask_t("feedback_delivery_failed"))
                    except Exception:
                        st.warning(ask_t("feedback_delivery_failed"))

'''
    text = text[:start] + new_block + text[end:]
    path.write_text(text, encoding="utf-8")


# Remove obsolete analytics-specific answer UI copy and keep failure text user-facing.
path = Path("ui_copy.py")
text = path.read_text(encoding="utf-8")
for key in ("feedback_pending", "retry_analytics", "retry_failed"):
    pattern = rf'^        "{key}": .*\n'
    text, count = re.subn(pattern, "", text, flags=re.MULTILINE)
    if count not in {0, 5}:
        raise RuntimeError(f"remove {key}: expected 0 or 5 locale entries, found {count}")

replacements = {
    '"feedback_delivery_failed": "Feedback delivery could not be confirmed. You can retry safely; retries for the same answer will not create another feedback record.",':
        '"feedback_delivery_failed": "Your feedback couldn\'t be saved just now. You can try again safely; retrying for the same answer won\'t create a duplicate.",',
    '"feedback_delivery_failed": "No se pudo confirmar la entrega de los comentarios. Puedes reintentarlo de forma segura; los reintentos para la misma respuesta no crearán otro registro.",':
        '"feedback_delivery_failed": "No se pudo guardar tu comentario en este momento. Puedes intentarlo de nuevo; volver a intentarlo para la misma respuesta no creará un duplicado.",',
    '"feedback_delivery_failed": "La livraison du retour n’a pas pu être confirmée. Vous pouvez réessayer sans risque ; les nouvelles tentatives pour la même réponse ne créeront pas d’autre enregistrement.",':
        '"feedback_delivery_failed": "Votre retour n’a pas pu être enregistré pour le moment. Vous pouvez réessayer ; une nouvelle tentative pour la même réponse ne créera pas de doublon.",',
    '"feedback_delivery_failed": "Không thể xác nhận việc gửi phản hồi. Bạn có thể thử lại an toàn; việc thử lại cho cùng một câu trả lời sẽ không tạo thêm bản ghi phản hồi.",':
        '"feedback_delivery_failed": "Hiện chưa thể lưu phản hồi của bạn. Bạn có thể thử lại; việc thử lại cho cùng một câu trả lời sẽ không tạo bản ghi trùng lặp.",',
    '"feedback_delivery_failed": "Pengiriman umpan balik tidak dapat dikonfirmasi. Anda dapat mencoba lagi dengan aman; percobaan ulang untuk jawaban yang sama tidak akan membuat catatan umpan balik baru.",':
        '"feedback_delivery_failed": "Umpan balik Anda belum dapat disimpan saat ini. Anda dapat mencoba lagi; percobaan ulang untuk jawaban yang sama tidak akan membuat catatan duplikat.",',
}
for old, new in replacements.items():
    text = replace_once_or_confirm(text, old, new, f"replace feedback failure copy: {old[:35]}")
path.write_text(text, encoding="utf-8")
