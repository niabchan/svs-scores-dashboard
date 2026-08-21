from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_count(text, old, new, expected, label):
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} matches, found {count}")
    return text.replace(old, new)


# Narrow, deterministic routing for standalone/general help requests.
path = Path("ask_dashboard/_routing.py")
text = path.read_text(encoding="utf-8")
old = '''def _is_metric_definition_request(text: str) -> bool:\n    return any(re.fullmatch(pattern, text) for pattern in _METRIC_DEFINITION_PATTERNS)\n\n\ndef _is_player_net_balance_request(text: str) -> bool:\n'''
new = '''def _is_metric_definition_request(text: str) -> bool:\n    return any(re.fullmatch(pattern, text) for pattern in _METRIC_DEFINITION_PATTERNS)\n\n\n_GENERAL_HELP_PATTERNS = (\n    r"^(?:(?:hello|hi|hey)(?: there)? )?(?:can|could|would|will) you help me(?: please)?$",\n    r"^(?:(?:hello|hi|hey)(?: there)? )?please help me$",\n    r"^(?:(?:hello|hi|hey)(?: there)? )?help me(?: please)?$",\n    r"^(?:(?:hello|hi|hey)(?: there)? )?i (?:need|would like) help$",\n)\n\n\ndef _is_general_help_request(text: str) -> bool:\n    """Recognize only standalone/general help requests, not analytical questions."""\n    return any(re.fullmatch(pattern, text) for pattern in _GENERAL_HELP_PATTERNS)\n\n\ndef _is_player_net_balance_request(text: str) -> bool:\n'''
text = replace_once(text, old, new, "insert general help helper")
old = '''    if _is_metric_definition_request(normalized):\n        # Metric explanations are deterministic dashboard help and do not need\n        # an API classification or access to score rows.\n        return legacy._intent_contract("dashboard_help")\n    if _is_player_net_balance_request(normalized):\n'''
new = '''    if _is_metric_definition_request(normalized):\n        # Metric explanations are deterministic dashboard help and do not need\n        # an API classification or access to score rows.\n        return legacy._intent_contract("dashboard_help")\n    if _is_general_help_request(normalized):\n        # Generic requests for help are deterministic product guidance. Keep\n        # this intentionally narrow so analytical questions containing "help"\n        # still proceed through normal rule/API routing.\n        return legacy._intent_contract("dashboard_help")\n    if _is_player_net_balance_request(normalized):\n'''
text = replace_once(text, old, new, "wire general help rule")
path.write_text(text, encoding="utf-8")


# Make English examples/commands explicit instead of looking like missed localization.
path = Path("ask_dashboard/_answer_i18n.py")
text = path.read_text(encoding="utf-8")
heading_replacements = {
    "**Ejemplos:**": "**Ejemplos de preguntas (escríbelas en inglés):**",
    "**Exemples :**": "**Exemples de questions (à saisir en anglais) :**",
    "**Ví dụ:**": "**Ví dụ câu hỏi (hãy nhập bằng tiếng Anh):**",
    "**Contoh:**": "**Contoh pertanyaan (ketik dalam bahasa Inggris):**",
}
for old, new in heading_replacements.items():
    text = replace_count(text, old, new, 2, f"localized English-example label: {old}")

command_replacements = {
    "**Más ayuda:**": "**Más ayuda (usa los comandos en inglés):**",
    "**Aide supplémentaire :**": "**Aide supplémentaire (utilisez les commandes en anglais) :**",
    "**Trợ giúp thêm:**": "**Trợ giúp thêm (dùng lệnh tiếng Anh):**",
    "**Bantuan lainnya:**": "**Bantuan lainnya (gunakan perintah bahasa Inggris):**",
}
for old, new in command_replacements.items():
    text = replace_once(text, old, new, f"localized English-command label: {old}")

old = "Area yang didukung mencakup ringkasan umum poin aliansi, pemimpin poin bersih pemain dan aliansi, kontribusi positif dibandingkan dampak negatif, pengecualian pemain, perubahan persentase negatif, kontributor teratas, dan total poin bersih setelah mengecualikan aliansi tertentu."
new = "Ask Dashboard dapat membantu menjelaskan ringkasan skor aliansi, pemain atau aliansi dengan poin bersih tertinggi, kontribusi positif dan dampak negatif, dampak pengecualian pemain, perubahan persentase negatif, kontributor teratas, serta total poin bersih setelah mengecualikan aliansi tertentu."
text = replace_once(text, old, new, "polish Indonesian help scope")
old = "Ask Dashboard menjelaskan hasil poin yang tercatat. Ask Dashboard tidak dapat menentukan motif, niat, karakter, keterampilan, strategi, tanggung jawab, atau keadaan permainan yang tidak terlihat dari data poin saja."
new = "Ask Dashboard menjelaskan hasil skor yang tercatat, tetapi tidak dapat menentukan motif, niat, karakter, keterampilan, strategi, tanggung jawab, atau situasi permainan yang tidak tercatat dalam data."
text = replace_once(text, old, new, "polish Indonesian help limitation")
old = "2. Tanyakan tentang poin pemain atau aliansi, peringkat, pengecualian, atau kontribusi negatif."
new = "2. Tanyakan tentang poin pemain atau aliansi, peringkat, pengecualian, kontribusi positif, atau dampak negatif."
text = replace_once(text, old, new, "polish Indonesian help step")
path.write_text(text, encoding="utf-8")


# Regression tests: general help stays on rules; analytical help wording stays available to AI.
path = Path("test_ask_dashboard.py")
text = path.read_text(encoding="utf-8")
append = '''\n\n@pytest.mark.parametrize(\n    "question",\n    [\n        "Can you help me?",\n        "Hello. Can you help me?",\n        "Could you help me please?",\n        "Please help me",\n        "I need help",\n    ],\n)\ndef test_general_help_requests_route_deterministically(question):\n    contract = route_dashboard_question(question, ["SnS"])\n    assert contract["intent"] == "dashboard_help"\n    assert contract["source"] == "rule"\n    assert contract["match_status"] == "matched"\n\n\ndef test_general_help_hybrid_does_not_call_ai():\n    from ask_dashboard import route_dashboard_question_hybrid\n\n    def fail_if_called(*args, **kwargs):\n        raise AssertionError("AI extractor should not be called for generic help")\n\n    result = route_dashboard_question_hybrid(\n        "Hello. Can you help me?",\n        ["SnS"],\n        ai_enabled=True,\n        ai_extractor=fail_if_called,\n    )\n    assert result["contract"]["intent"] == "dashboard_help"\n    assert result["ai_attempted"] is False\n    assert result["ai_succeeded"] is False\n\n\ndef test_help_wording_does_not_swallow_analytical_questions():\n    contract = route_dashboard_question(\n        "Can you help me understand why SnS has the highest net score?",\n        ["SnS"],\n    )\n    assert contract["intent"] != "dashboard_help"\n'''
if "def test_general_help_requests_route_deterministically" in text:
    raise RuntimeError("general help routing tests already exist")
path.write_text(text + append, encoding="utf-8")


# Localized help should explain why examples and commands remain English.
path = Path("test_answer_i18n.py")
text = path.read_text(encoding="utf-8")
append = '''\n\ndef test_localized_help_marks_english_examples_as_exact_input_language():\n    answer = {\n        "intent": "dashboard_help",\n        "status": "ok",\n        "parameters": {"question": "Hello. Can you help me?"},\n    }\n    markers = {\n        "es": ("escríbelas en inglés", "comandos en inglés"),\n        "fr": ("à saisir en anglais", "commandes en anglais"),\n        "vi": ("nhập bằng tiếng Anh", "lệnh tiếng Anh"),\n        "id": ("ketik dalam bahasa Inggris", "perintah bahasa Inggris"),\n    }\n    for locale, (example_marker, command_marker) in markers.items():\n        rendered = render_dashboard_answer(answer, locale=locale)\n        assert example_marker in rendered\n        assert command_marker in rendered\n        assert "Which alliance leads net score?" in rendered\n        assert "`help filters`" in rendered\n\n\ndef test_indonesian_help_copy_is_polished_without_changing_capability_boundary():\n    answer = {\n        "intent": "dashboard_help",\n        "status": "ok",\n        "parameters": {"question": "Hello. Can you help me?"},\n    }\n    rendered = render_dashboard_answer(answer, locale="id")\n    assert "Ask Dashboard dapat membantu menjelaskan" in rendered\n    assert "kontribusi positif dan dampak negatif" in rendered\n    assert "hasil skor yang tercatat, tetapi tidak dapat menentukan" in rendered\n    assert "Ask Dashboard menjelaskan hasil poin yang tercatat. Ask Dashboard" not in rendered\n'''
if "def test_localized_help_marks_english_examples_as_exact_input_language" in text:
    raise RuntimeError("localized help copy tests already exist")
path.write_text(text + append, encoding="utf-8")
