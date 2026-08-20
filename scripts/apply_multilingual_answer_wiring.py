from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Wire the selected UI locale into the public answer renderer.
path = Path("app.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    "        rendered_answer = render_dashboard_answer(answer)\n",
    "        rendered_answer = render_dashboard_answer(\n"
    "            answer,\n"
    "            locale=st.session_state.get(\"lang\", \"en\"),\n"
    "        )\n",
    "app answer locale wiring",
)
path.write_text(text, encoding="utf-8")


# Keep the question-understanding limitation accurate now that answers localize.
path = Path("ui_copy.py")
text = path.read_text(encoding="utf-8")
replacements = {
    "Free-text questions and generated explanations currently work in English. You can still use the dashboard interface in your selected language.":
        "Free-text questions currently work best in English. Generated explanations are shown in your selected dashboard language.",
    "Las preguntas de texto libre y las explicaciones generadas funcionan actualmente en inglés. Puedes seguir usando la interfaz del panel en el idioma seleccionado.":
        "Por ahora, las preguntas de texto libre funcionan mejor si se escriben en inglés. Las explicaciones se muestran en el idioma seleccionado del panel.",
    "Les questions en texte libre et les explications générées fonctionnent actuellement en anglais. Vous pouvez continuer à utiliser l’interface du tableau de bord dans la langue sélectionnée.":
        "Pour le moment, les questions en texte libre fonctionnent mieux lorsqu’elles sont saisies en anglais. Les explications sont affichées dans la langue sélectionnée du tableau de bord.",
    "Câu hỏi dạng văn bản tự do và phần giải thích được tạo hiện chỉ hoạt động bằng tiếng Anh. Bạn vẫn có thể dùng giao diện bảng điều khiển bằng ngôn ngữ đã chọn.":
        "Hiện tại, câu hỏi dạng văn bản tự do hoạt động tốt nhất khi được nhập bằng tiếng Anh. Phần giải thích sẽ hiển thị bằng ngôn ngữ bảng điều khiển đã chọn.",
    "Pertanyaan teks bebas dan penjelasan yang dihasilkan saat ini bekerja dalam bahasa Inggris. Anda tetap dapat menggunakan antarmuka dasbor dalam bahasa yang dipilih.":
        "Untuk saat ini, pertanyaan teks bebas bekerja paling baik jika ditulis dalam bahasa Inggris. Penjelasan ditampilkan dalam bahasa dasbor yang dipilih.",
}
for old, new in replacements.items():
    text = replace_once(text, old, new, f"ui notice: {old[:24]}")
path.write_text(text, encoding="utf-8")


# Document the split between localized rendering and English-first free-text routing.
path = Path("LOCALIZATION.md")
text = path.read_text(encoding="utf-8")
old = """## Current capability boundary

The interface is multilingual, but free-text Ask Dashboard routing and generated explanations are currently English-first. Do not imply full multilingual question understanding until routing and answer-generation tests exist for that language.

Use localized limitation copy near the custom-question input rather than leaving users to infer the limitation after an unsupported answer.
"""
new = """## Current capability boundary

The interface and deterministic Ask Dashboard explanations support English, Spanish, French, Vietnamese, and Indonesian. Final answer rendering follows the selected dashboard UI locale after the structured answer has been calculated.

Free-text question routing remains English-first, so custom questions currently work best when entered in English. Suggested questions keep their canonical English/internal values for routing and are localized only for display. Do not imply full multilingual question understanding until routing tests exist for those languages.

Localized answer rendering is a presentation layer only: it does not send score rows, player names, alliance names, rankings, or calculated values to a translation model. Player and alliance names remain unchanged, and metric meanings and scope boundaries must match the English canonical answer.

Keep localized limitation copy near the custom-question input so users understand this distinction before submitting a free-text question.
"""
text = replace_once(text, old, new, "localization capability boundary")
path.write_text(text, encoding="utf-8")
