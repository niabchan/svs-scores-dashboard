from pathlib import Path
import re


def locale_block(text, locale, next_locale):
    start_marker = f'    "{locale}": {{\n'
    end_marker = f'    "{next_locale}": {{\n'
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return start, end, text[start:end]


def replace_locale_value(text, locale, next_locale, key, value):
    start, end, block = locale_block(text, locale, next_locale)
    pattern = re.compile(rf'^(        "{re.escape(key)}": )".*"(,?)$', re.MULTILINE)
    matches = list(pattern.finditer(block))
    if len(matches) != 1:
        raise RuntimeError(f"{locale}.{key}: expected one one-line value, found {len(matches)}")
    escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    replacement = rf'\1"{escaped}"\2'
    new_block = pattern.sub(replacement, block, count=1)
    return text[:start] + new_block + text[end:]


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


# --- French/Vietnamese deterministic answer prose ---
path = Path("ask_dashboard/_answer_i18n.py")
text = path.read_text(encoding="utf-8")

fr = {
    "metric_lost": "**Points perdus** correspond au total des points SVS enregistrés comme perdus. Ask Dashboard les affiche comme une quantité positive de pertes et les soustrait aux points gagnés lors du calcul du score net.",
    "metric_negative": "**Impact négatif** est la valeur absolue totale des **scores nets négatifs des joueurs** dans le périmètre sélectionné. Il indique de combien le côté négatif réduit le résultat, tout en présentant cette valeur sous forme positive pour faciliter la comparaison.",
    "metric_negative_share": "**Part négative** = **impact négatif ÷ (contribution positive + impact négatif) × 100**. Elle indique la part de l’impact négatif dans l’ensemble formé par la contribution positive et l’impact négatif, et non le pourcentage de joueurs ayant terminé avec un score négatif.",
    "alliance_positive_single": "{intro}, **{alliance}** est l’alliance qui apporte la plus forte contribution positive, avec **{score}**.",
    "player_positive_single": "{intro}{scope}, **{player}** est le joueur qui apporte la plus forte contribution positive, avec **{score}**.",
    "outcome_improved": "Le score net total **s’est amélioré de {amount}**. Les exclusions ont réduit l’impact négatif de **{negative}** mais la contribution positive de seulement **{positive}** ; la diminution de l’impact négatif a donc été plus importante que celle de la contribution positive.",
    "outcome_decreased": "Le score net total **a diminué de {amount}**. Les exclusions ont réduit la contribution positive de **{positive}** mais l’impact négatif de seulement **{negative}** ; la diminution de la contribution positive a donc été plus importante que celle de l’impact négatif.",
    "negative_no_magnitude": "La part négative ne peut pas être calculée car le groupe filtré actuel ne présente ni contribution positive ni impact négatif.",
    "negative_after_none": "Après les exclusions actuelles{period}, il ne reste ni contribution positive ni impact négatif dans le groupe sélectionné ; la part négative après exclusion ne peut donc pas être calculée.",
    "negative_formula": "Part négative = impact négatif ÷ (contribution positive + impact négatif).",
}
for key, value in fr.items():
    text = replace_locale_value(text, "fr", "vi", key, value)

vi = {
    "metric_lost": "**Điểm bị mất** là tổng số điểm SVS được ghi nhận là đã mất. Ask Dashboard hiển thị số điểm bị mất dưới dạng một giá trị dương và trừ giá trị này khỏi điểm kiếm được khi tính điểm ròng.",
    "metric_negative": "**Tác động tiêu cực** là tổng trị tuyệt đối của **điểm ròng âm của người chơi** trong phạm vi đã chọn. Chỉ số này cho biết phần điểm ròng âm làm giảm kết quả bao nhiêu, đồng thời hiển thị giá trị đó dưới dạng số dương để dễ so sánh.",
    "metric_negative_share": "**Tỷ trọng tiêu cực** = **tác động tiêu cực ÷ (đóng góp tích cực + tác động tiêu cực) × 100**. Chỉ số này cho biết tác động tiêu cực chiếm bao nhiêu trong tổng của đóng góp tích cực và tác động tiêu cực, không phải tỷ lệ người chơi có điểm ròng âm.",
    "alliance_positive_single": "{intro}, **{alliance}** là liên minh có đóng góp tích cực lớn nhất, với **{score}**.",
    "positive_share": "Liên minh này chiếm **{share:.1f}%** trong tổng đóng góp tích cực của phạm vi này.",
    "player_positive_single": "{intro}{scope}, **{player}** là người có đóng góp tích cực lớn nhất, với **{score}**.",
    "label_share_positive": "Tỷ trọng trong tổng đóng góp tích cực của phạm vi này",
    "exclusion_intro": "Sau khi áp dụng lựa chọn loại người chơi hiện tại{period}, phân tích còn **{after}/{before} người chơi**. **Người chơi bị loại:** {excluded}.",
    "outcome_improved": "Tổng điểm ròng **tăng thêm {amount}**. Việc loại người chơi đã giảm tác động tiêu cực **{negative}** nhưng chỉ làm giảm đóng góp tích cực **{positive}**, nên tác động tiêu cực giảm nhiều hơn đóng góp tích cực.",
    "outcome_decreased": "Tổng điểm ròng **giảm {amount}**. Việc loại người chơi đã làm giảm đóng góp tích cực **{positive}** nhưng chỉ giảm tác động tiêu cực **{negative}**, nên đóng góp tích cực giảm nhiều hơn tác động tiêu cực.",
    "negative_no_magnitude": "Không thể tính tỷ trọng tiêu cực vì nhóm đã lọc hiện tại không có đóng góp tích cực hoặc tác động tiêu cực.",
    "negative_none": "Hiện không có người chơi nào bị loại khỏi nhóm đã lọc{period}. Tỷ trọng tiêu cực giữ nguyên ở **{share:.1f}%**. Hãy bỏ chọn ít nhất một người chơi trong tab Phân tích lựa chọn người chơi để tạo so sánh trước và sau.",
    "negative_after_none": "Sau khi áp dụng lựa chọn loại người chơi hiện tại{period}, nhóm được chọn không còn đóng góp tích cực hoặc tác động tiêu cực nên không thể tính tỷ trọng tiêu cực sau khi loại.",
    "negative_mismatch": "Tiền đề không khớp với lựa chọn hiện tại: tỷ trọng tiêu cực",
    "negative_normal": "Tỷ trọng tiêu cực",
    "negative_formula": "Tỷ trọng tiêu cực = tác động tiêu cực ÷ (đóng góp tích cực + tác động tiêu cực).",
    "help_text": "## Cách sử dụng Ask Dashboard\n\n1. Trước tiên hãy chọn kỳ SVS và các bộ lọc trên thanh bên.\n2. Hỏi về điểm của người chơi hoặc liên minh, xếp hạng, việc loại người chơi hoặc tác động tiêu cực.\n3. Câu trả lời chỉ sử dụng dữ liệu nằm trong các bộ lọc hiện tại.\n\nCác nội dung được hỗ trợ gồm tổng quan điểm của liên minh, người dẫn đầu về điểm ròng của người chơi và liên minh, đóng góp tích cực so với tác động tiêu cực, việc loại người chơi, thay đổi tỷ trọng tiêu cực, người đóng góp hàng đầu và tổng điểm ròng sau khi loại liên minh được nêu tên.\n\n**Ví dụ câu hỏi (hãy nhập bằng tiếng Anh):**\n- Top net score player\n- Top alliance score\n- Which alliance leads net score?\n- Who contributed most in SnS?\n- What changed after excluding the selected players?\n\n**Trợ giúp thêm (dùng lệnh tiếng Anh):** `help filters`, `help questions`, `help player selection` hoặc `help limitations`.\n\nAsk Dashboard mô tả kết quả điểm đã ghi nhận. Công cụ không thể xác định động cơ, ý định, tính cách, kỹ năng, chiến lược, trách nhiệm hoặc hoàn cảnh chơi không được ghi nhận của người chơi chỉ từ dữ liệu điểm.",
    "rounded_notice": "Lưu ý về dữ liệu: một số giá trị điểm kiếm được trong kỳ này dựa trên các số đã được Evony làm tròn khi hiển thị trong trò chơi. Vì vậy, tổng điểm, điểm ròng, thứ hạng và các kết quả được tính từ những giá trị này chỉ mang tính xấp xỉ và có thể chênh lệch nhẹ so với giá trị chính xác.",
}
for key, value in vi.items():
    text = replace_locale_value(text, "vi", "id", key, value)

number_helpers = '''\n\n_GROUPED_NUMBER_RE = re.compile(r"(?<![\\w])([+-]?\\d{1,3}(?:,\\d{3})+)(?![\\w])")\n_PERCENT_RE = re.compile(r"(?<![\\w])([+-]?\\d+(?:\\.\\d+)?)%")\n\n\ndef _localize_rendered_number_punctuation(rendered, locale):\n    """Apply locale punctuation to already-rendered numeric values only."""\n    if not isinstance(rendered, str) or locale not in {"fr", "vi"}:\n        return rendered\n\n    thousands_separator = "\\u202f" if locale == "fr" else "."\n    rendered = _GROUPED_NUMBER_RE.sub(\n        lambda match: match.group(1).replace(",", thousands_separator),\n        rendered,\n    )\n\n    def percent(match):\n        value = match.group(1).replace(".", ",")\n        return value + ("\\u202f%" if locale == "fr" else "%")\n\n    return _PERCENT_RE.sub(percent, rendered)\n'''
anchor = 'validate_answer_copy_parity()\n\n\ndef _t(locale, key, **values):\n'
if '_localize_rendered_number_punctuation' not in text:
    text = replace_once(
        text,
        anchor,
        'validate_answer_copy_parity()' + number_helpers + '\n\ndef _t(locale, key, **values):\n',
        'insert locale number formatter',
    )
text = replace_once(
    text,
    '    return rendered\n',
    '    return _localize_rendered_number_punctuation(rendered, locale)\n',
    'localize final rendered punctuation',
)
path.write_text(text, encoding="utf-8")


# --- UI copy exposed around Ask Dashboard ---
path = Path("ui_copy.py")
text = path.read_text(encoding="utf-8")
ui_fr = {
    "analytics_privacy": "Statistiques d’utilisation et confidentialité",
    "custom_question_notice": "Pour le moment, les questions en texte libre fonctionnent mieux lorsqu’elles sont saisies en anglais. Les explications sont affichées dans la langue sélectionnée pour le tableau de bord.",
    "suggest_negative_share": "Pourquoi la part négative a-t-elle augmenté ?",
}
for key, value in ui_fr.items():
    text = replace_locale_value(text, "fr", "vi", key, value)
ui_vi = {
    "custom_question_help": "Gõ “help” để xem hướng dẫn sử dụng, hoặc hỏi trực tiếp về xếp hạng liên minh, loại người chơi, tỷ trọng tiêu cực, người đóng góp hàng đầu hoặc điểm ròng.",
    "suggest_negative_share": "Vì sao tỷ trọng tiêu cực tăng lên?",
}
for key, value in ui_vi.items():
    text = replace_locale_value(text, "vi", "id", key, value)
path.write_text(text, encoding="utf-8")


# --- French ranking selector copy in main dashboard UI ---
path = Path("app.py")
text = path.read_text(encoding="utf-8")
app_fr = {
    "top_10_net_score": "10 scores nets les plus élevés",
    "bottom_10_net_score": "10 scores nets les plus faibles",
    "top_10_score_gained": "10 totaux de points gagnés les plus élevés",
    "top_10_score_lost": "10 totaux de points perdus les plus élevés",
}
for key, value in app_fr.items():
    text = replace_locale_value(text, "fr", "vi", key, value)
path.write_text(text, encoding="utf-8")


# --- Regression tests ---
path = Path("test_answer_i18n.py")
text = path.read_text(encoding="utf-8")
old = '''    expected_language_markers = {\n        "es": "contribución positiva",\n        "fr": "contribution positive",\n        "vi": "đóng góp tích cực",\n        "id": "kontribusi positif",\n    }\n    for locale, marker in expected_language_markers.items():\n        rendered = render_dashboard_answer(answer, locale=locale)\n        assert "SnS" in rendered\n        assert "TDA" in rendered\n        assert "1,200" in rendered\n        assert marker.casefold() in rendered.casefold()\n'''
new = '''    expected = {\n        "es": ("contribución positiva", "1,200"),\n        "fr": ("contribution positive", "1\\u202f200"),\n        "vi": ("đóng góp tích cực", "1.200"),\n        "id": ("kontribusi positif", "1,200"),\n    }\n    for locale, (marker, formatted_number) in expected.items():\n        rendered = render_dashboard_answer(answer, locale=locale)\n        assert "SnS" in rendered\n        assert "TDA" in rendered\n        assert formatted_number in rendered\n        assert marker.casefold() in rendered.casefold()\n'''
text = replace_once(text, old, new, 'update dynamic number expectations')
append = '''\n\ndef test_french_and_vietnamese_answers_use_locale_number_punctuation():\n    answer = _alliance_positive_answer()\n    fr = render_dashboard_answer(answer, locale="fr")\n    vi = render_dashboard_answer(answer, locale="vi")\n\n    assert "1\\u202f200" in fr\n    assert "60,0\\u202f%" in fr\n    assert "1.200" in vi\n    assert "60,0%" in vi\n    assert "1,200" not in fr\n    assert "1,200" not in vi\n\n\ndef test_french_cleanup_avoids_translation_calques():\n    assert "magnitude" not in ANSWER_TEXT["fr"]["metric_lost"].casefold()\n    assert "magnitude" not in ANSWER_TEXT["fr"]["metric_negative"].casefold()\n    assert "gains utiles" not in ANSWER_TEXT["fr"]["outcome_improved"].casefold()\n    assert ANSWER_TEXT["fr"]["negative_formula"].startswith("Part négative")\n\n\ndef test_vietnamese_cleanup_uses_consistent_negative_share_terminology():\n    assert "độ lớn" not in ANSWER_TEXT["vi"]["negative_no_magnitude"].casefold()\n    assert "độ lớn" not in ANSWER_TEXT["vi"]["negative_after_none"].casefold()\n    assert ANSWER_TEXT["vi"]["negative_formula"].startswith("Tỷ trọng tiêu cực")\n    assert "người có đóng góp tích cực lớn nhất" in ANSWER_TEXT["vi"]["player_positive_single"]\n\n\ndef test_french_ranking_selector_has_no_top_bottom_english_leakage():\n    source = open("app.py", encoding="utf-8").read()\n    assert '"top_10_net_score": "Top 10 score net"' not in source\n    assert '"bottom_10_net_score": "Bottom 10 score net"' not in source\n    assert '"top_10_net_score": "10 scores nets les plus élevés"' in source\n    assert '"bottom_10_net_score": "10 scores nets les plus faibles"' in source\n'''
if 'test_french_and_vietnamese_answers_use_locale_number_punctuation' not in text:
    text += append
path.write_text(text, encoding="utf-8")
