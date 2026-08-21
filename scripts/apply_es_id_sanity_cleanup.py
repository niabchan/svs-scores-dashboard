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


# --- Spanish and Indonesian deterministic answer prose ---
path = Path("ask_dashboard/_answer_i18n.py")
text = path.read_text(encoding="utf-8")

es = {
    "metric_lost": "**Puntos perdidos** corresponde al total de puntos SVS registrados como perdidos. Ask Dashboard los muestra como una cantidad positiva y los resta de los puntos obtenidos al calcular la puntuación neta.",
    "metric_negative": "**Impacto negativo** es el valor absoluto total de las **puntuaciones netas negativas de los jugadores** en el ámbito seleccionado. Indica cuánto reduce el resultado el lado negativo y muestra ese valor como una cifra positiva para facilitar la comparación.",
    "metric_negative_share": "**Participación negativa** = **impacto negativo ÷ (contribución positiva + impacto negativo) × 100**. Indica qué parte del total combinado de contribución positiva e impacto negativo corresponde al impacto negativo, no el porcentaje de jugadores que terminaron con puntuación neta negativa.",
    "alliance_positive_single": "{intro}, **{alliance}** es la alianza con la mayor contribución positiva, con **{score}**.",
    "player_positive_single": "{intro}{scope}, **{player}** tiene la mayor contribución positiva, con **{score}**.",
    "outcome_improved": "La puntuación neta total **mejoró en {amount}**. Las exclusiones redujeron el impacto negativo en **{negative}**, pero la contribución positiva solo en **{positive}**; por tanto, la reducción del impacto negativo fue mayor que la reducción de la contribución positiva.",
    "outcome_decreased": "La puntuación neta total **disminuyó en {amount}**. Las exclusiones redujeron la contribución positiva en **{positive}**, pero el impacto negativo solo en **{negative}**; por tanto, la reducción de la contribución positiva fue mayor que la reducción del impacto negativo.",
    "negative_no_magnitude": "No se puede calcular la participación negativa porque el grupo filtrado actual no tiene contribución positiva ni impacto negativo.",
    "negative_after_none": "Después de las exclusiones actuales{period}, no queda contribución positiva ni impacto negativo en el grupo seleccionado, por lo que no se puede calcular la participación negativa posterior a la exclusión.",
    "negative_formula": "Participación negativa = impacto negativo ÷ (contribución positiva + impacto negativo).",
}
for key, value in es.items():
    text = replace_locale_value(text, "es", "fr", key, value)

id_copy = {
    "metric_lost": "**Poin yang hilang** adalah total poin SVS yang tercatat sebagai hilang. Ask Dashboard menampilkannya sebagai nilai kehilangan positif dan menguranginya dari poin yang diperoleh saat menghitung poin bersih.",
    "metric_negative": "**Dampak negatif** adalah total nilai absolut dari **poin bersih negatif pemain** dalam cakupan yang dipilih. Metrik ini menunjukkan seberapa besar sisi negatif mengurangi hasil dan menampilkan nilai tersebut sebagai angka positif agar mudah dibandingkan.",
    "metric_negative_share": "**Persentase dampak negatif** = **dampak negatif ÷ (kontribusi positif + dampak negatif) × 100**. Metrik ini menunjukkan porsi dampak negatif dalam gabungan kontribusi positif dan dampak negatif, bukan persentase pemain yang berakhir dengan poin bersih negatif.",
    "alliance_positive_single": "{intro}, **{alliance}** adalah aliansi dengan kontribusi positif terbesar, sebesar **{score}**.",
    "player_positive_single": "{intro}{scope}, **{player}** adalah pemain dengan kontribusi positif terbesar, sebesar **{score}**.",
    "positive_share": "Aliansi ini menyumbang **{share:.1f}%** dari total kontribusi positif dalam cakupan ini.",
    "label_share_positive": "Persentase dari total kontribusi positif dalam cakupan ini",
    "outcome_improved": "Total poin bersih **membaik sebesar {amount}**. Pengecualian mengurangi dampak negatif sebesar **{negative}**, tetapi kontribusi positif hanya sebesar **{positive}**; jadi penurunan dampak negatif lebih besar daripada penurunan kontribusi positif.",
    "outcome_decreased": "Total poin bersih **menurun sebesar {amount}**. Pengecualian mengurangi kontribusi positif sebesar **{positive}**, tetapi dampak negatif hanya sebesar **{negative}**; jadi penurunan kontribusi positif lebih besar daripada penurunan dampak negatif.",
    "negative_no_magnitude": "Persentase dampak negatif tidak dapat dihitung karena kelompok terfilter saat ini tidak memiliki kontribusi positif maupun dampak negatif.",
    "negative_none": "Saat ini tidak ada pemain yang dikecualikan dari kelompok terfilter{period}. Persentase dampak negatif tetap **{share:.1f}%**. Hapus setidaknya satu pemain di tab Analisis Pemilihan Pemain untuk membuat perbandingan sebelum dan sesudah.",
    "negative_after_none": "Setelah pengecualian saat ini{period}, kelompok terpilih tidak lagi memiliki kontribusi positif maupun dampak negatif, sehingga persentase dampak negatif setelah pengecualian tidak dapat dihitung.",
    "negative_mismatch": "Premis tidak sesuai dengan pilihan saat ini: persentase dampak negatif",
    "negative_normal": "Persentase dampak negatif",
    "negative_reason_increase_down": "Hal ini terjadi karena pengecualian menghapus proporsi kontribusi positif yang lebih besar daripada dampak negatif. Kontribusi positif turun **{positive_rate:.1f}%**, sementara dampak negatif turun **{negative_rate:.1f}%**. Walaupun nilai dampak negatif juga menurun, porsinya menjadi lebih besar dalam total tersisa yang lebih kecil.",
    "negative_reason_increase_same": "Hal ini terjadi karena pengecualian menghapus proporsi kontribusi positif yang lebih besar daripada dampak negatif. Kontribusi positif turun **{positive_rate:.1f}%**, sementara dampak negatif turun **{negative_rate:.1f}%**. Nilai dampak negatif tidak meningkat; nilainya tetap sama tetapi porsinya menjadi lebih besar dalam total tersisa yang lebih kecil.",
    "negative_formula": "Persentase dampak negatif = dampak negatif ÷ (kontribusi positif + dampak negatif).",
}
# Indonesian is the final locale block, so append a temporary sentinel for safe scoped replacement.
sentinel = '\n    "__sentinel__": {\n'
text_with_sentinel = text.replace('\n}\n\n\ndef _format_fields', sentinel + '}\n\n\ndef _format_fields', 1)
for key, value in id_copy.items():
    text_with_sentinel = replace_locale_value(text_with_sentinel, "id", "__sentinel__", key, value)
text = text_with_sentinel.replace(sentinel + '}\n\n\ndef _format_fields', '\n}\n\n\ndef _format_fields', 1)

old_formatter = '''def _localize_rendered_number_punctuation(rendered, locale):\n    """Apply locale punctuation to already-rendered numeric values only."""\n    if not isinstance(rendered, str) or locale not in {"fr", "vi"}:\n        return rendered\n\n    thousands_separator = "\\u202f" if locale == "fr" else "."\n    rendered = _GROUPED_NUMBER_RE.sub(\n        lambda match: match.group(1).replace(",", thousands_separator),\n        rendered,\n    )\n\n    def percent(match):\n        value = match.group(1).replace(".", ",")\n        return value + ("\\u202f%" if locale == "fr" else "%")\n\n    return _PERCENT_RE.sub(percent, rendered)\n'''
new_formatter = '''def _localize_rendered_number_punctuation(rendered, locale):\n    """Apply locale punctuation to already-rendered numeric values only."""\n    if not isinstance(rendered, str) or locale not in {"es", "fr", "vi", "id"}:\n        return rendered\n\n    thousands_separator = "\\u202f" if locale == "fr" else "."\n    rendered = _GROUPED_NUMBER_RE.sub(\n        lambda match: match.group(1).replace(",", thousands_separator),\n        rendered,\n    )\n\n    def percent(match):\n        value = match.group(1).replace(".", ",")\n        percent_suffix = "\\u202f%" if locale in {"es", "fr"} else "%"\n        return value + percent_suffix\n\n    return _PERCENT_RE.sub(percent, rendered)\n'''
text = replace_once(text, old_formatter, new_formatter, "extend locale number punctuation")
path.write_text(text, encoding="utf-8")


# --- Ask Dashboard UI copy exposed in rendered review ---
path = Path("ui_copy.py")
text = path.read_text(encoding="utf-8")
ui_es = {
    "analytics_privacy": "Estadísticas de uso y privacidad",
    "suggest_negative_share": "¿Por qué aumentó la participación negativa?",
}
for key, value in ui_es.items():
    text = replace_locale_value(text, "es", "fr", key, value)

ui_id = {
    "analytics_privacy": "Analitik penggunaan dan privasi",
    "custom_question_help": "Ketik “help” untuk panduan penggunaan, atau tanyakan langsung tentang peringkat aliansi, pengecualian pemain, persentase dampak negatif, kontributor teratas, atau poin bersih.",
    "suggest_negative_share": "Mengapa persentase dampak negatif meningkat?",
}
text_with_sentinel = text.replace('\n}\n\n\nSUGGESTED_QUESTION_KEYS', sentinel + '}\n\n\nSUGGESTED_QUESTION_KEYS', 1)
for key, value in ui_id.items():
    text_with_sentinel = replace_locale_value(text_with_sentinel, "id", "__sentinel__", key, value)
text = text_with_sentinel.replace(sentinel + '}\n\n\nSUGGESTED_QUESTION_KEYS', '\n}\n\n\nSUGGESTED_QUESTION_KEYS', 1)
path.write_text(text, encoding="utf-8")


# --- Regression tests ---
path = Path("test_answer_i18n.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''    expected = {\n        "es": ("contribución positiva", "1,200"),\n        "fr": ("contribution positive", "1\\u202f200"),\n        "vi": ("đóng góp tích cực", "1.200"),\n        "id": ("kontribusi positif", "1,200"),\n    }\n''',
    '''    expected = {\n        "es": ("contribución positiva", "1.200"),\n        "fr": ("contribution positive", "1\\u202f200"),\n        "vi": ("đóng góp tích cực", "1.200"),\n        "id": ("kontribusi positif", "1.200"),\n    }\n''',
    "update dynamic number expectations",
)
text = replace_once(
    text,
    '''def test_french_and_vietnamese_answers_use_locale_number_punctuation():\n    answer = _alliance_positive_answer()\n    fr = render_dashboard_answer(answer, locale="fr")\n    vi = render_dashboard_answer(answer, locale="vi")\n\n    assert "1\\u202f200" in fr\n    assert "60,0\\u202f%" in fr\n    assert "1.200" in vi\n    assert "60,0%" in vi\n    assert "1,200" not in fr\n    assert "1,200" not in vi\n\n\n''',
    '''def test_localized_answers_use_locale_number_punctuation():\n    answer = _alliance_positive_answer()\n    es = render_dashboard_answer(answer, locale="es")\n    fr = render_dashboard_answer(answer, locale="fr")\n    vi = render_dashboard_answer(answer, locale="vi")\n    id_rendered = render_dashboard_answer(answer, locale="id")\n\n    assert "1.200" in es\n    assert "60,0\\u202f%" in es\n    assert "1\\u202f200" in fr\n    assert "60,0\\u202f%" in fr\n    assert "1.200" in vi\n    assert "60,0%" in vi\n    assert "1.200" in id_rendered\n    assert "60,0%" in id_rendered\n    for rendered in (es, fr, vi, id_rendered):\n        assert "1,200" not in rendered\n\n\n''',
    "extend localized number punctuation test",
)
append = '''\n\ndef test_spanish_cleanup_avoids_translation_calques():\n    assert "magnitud" not in ANSWER_TEXT["es"]["metric_lost"].casefold()\n    assert "magnitud" not in ANSWER_TEXT["es"]["metric_negative"].casefold()\n    assert "aporte útil" not in ANSWER_TEXT["es"]["outcome_decreased"].casefold()\n    assert ANSWER_TEXT["es"]["negative_formula"].startswith("Participación negativa")\n    assert "mayor contribución positiva" in ANSWER_TEXT["es"]["player_positive_single"]\n\n\ndef test_indonesian_cleanup_avoids_translation_calques():\n    assert "besaran" not in ANSWER_TEXT["id"]["metric_lost"].casefold()\n    assert "besaran" not in ANSWER_TEXT["id"]["negative_no_magnitude"].casefold()\n    assert "kontribusi bermanfaat" not in ANSWER_TEXT["id"]["outcome_decreased"].casefold()\n    assert "dampak negatif mentah" not in ANSWER_TEXT["id"]["negative_reason_increase_down"].casefold()\n    assert ANSWER_TEXT["id"]["negative_formula"].startswith("Persentase dampak negatif")\n    assert "kontribusi positif terbesar" in ANSWER_TEXT["id"]["player_positive_single"]\n'''
if "def test_spanish_cleanup_avoids_translation_calques" not in text:
    text += append
path.write_text(text, encoding="utf-8")
