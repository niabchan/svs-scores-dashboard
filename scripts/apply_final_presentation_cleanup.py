from pathlib import Path
import re


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def locale_block(text, locale, next_locale=None):
    start_marker = f'    "{locale}": {{\n'
    start = text.index(start_marker)
    if next_locale is None:
        end = text.index('\n    },\n}\n', start) + len('\n    },')
    else:
        end = text.index(f'    "{next_locale}": {{\n', start)
    return start, end, text[start:end]


def replace_locale_value(text, locale, next_locale, key, value):
    start, end, block = locale_block(text, locale, next_locale)
    pattern = re.compile(rf'^(        "{re.escape(key)}": )".*"(,?)$', re.MULTILINE)
    matches = list(pattern.finditer(block))
    if len(matches) != 1:
        raise RuntimeError(f"{locale}.{key}: expected one one-line value, found {len(matches)}")
    escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    new_block = pattern.sub(rf'\1"{escaped}"\2', block, count=1)
    return text[:start] + new_block + text[end:]


def remove_locale_key(text, locale, next_locale, key):
    start, end, block = locale_block(text, locale, next_locale)
    pattern = re.compile(rf'^        "{re.escape(key)}": ".*",\n', re.MULTILINE)
    matches = list(pattern.finditer(block))
    if len(matches) != 1:
        raise RuntimeError(f"{locale}.{key}: expected one one-line key, found {len(matches)}")
    new_block = pattern.sub('', block, count=1)
    return text[:start] + new_block + text[end:]


# UI copy: consolidate custom-question guidance into the textarea placeholder.
path = Path('ui_copy.py')
text = path.read_text(encoding='utf-8')
locale_order = [('en', 'es'), ('es', 'fr'), ('fr', 'vi'), ('vi', 'id'), ('id', None)]
for locale, next_locale in locale_order:
    text = remove_locale_key(text, locale, next_locale, 'custom_question_help')

replacements = {
    'en': {
        'analytics_privacy': 'Usage analytics & privacy',
        'question_placeholder': 'Ask about alliance rankings, player exclusions, negative share, top contributors, or net score — or type help',
    },
    'es': {
        'question_placeholder': 'Pregunta sobre clasificaciones de alianzas, exclusión de jugadores, participación negativa, principales contribuyentes o puntuación neta — o escribe help',
    },
    'fr': {
        'question_placeholder': 'Posez une question sur le classement des alliances, l’exclusion de joueurs, la part négative, les principaux contributeurs ou le score net — ou saisissez help',
    },
    'vi': {
        'analytics_privacy': 'Phân tích sử dụng và quyền riêng tư',
        'question_placeholder': 'Hỏi về xếp hạng liên minh, loại người chơi, tỷ trọng tiêu cực, người đóng góp hàng đầu hoặc điểm ròng — hoặc gõ help',
    },
    'id': {
        'question_placeholder': 'Tanyakan tentang peringkat aliansi, pengecualian pemain, persentase dampak negatif, kontributor teratas, atau poin bersih — atau ketik help',
    },
}
for locale, values in replacements.items():
    next_locale = dict(locale_order)[locale]
    for key, value in values.items():
        text = replace_locale_value(text, locale, next_locale, key, value)
path.write_text(text, encoding='utf-8')


# App: remove the now-redundant caption above the custom-question textarea.
path = Path('app.py')
text = path.read_text(encoding='utf-8')
text = replace_once(
    text,
    '    if suggested_question == QUESTION_CUSTOM:\n        st.caption(ask_t("custom_question_help"))\n        custom_question = st.text_area(\n',
    '    if suggested_question == QUESTION_CUSTOM:\n        custom_question = st.text_area(\n',
    'remove redundant custom-question helper caption',
)
path.write_text(text, encoding='utf-8')


# Localized answer renderer: polish Spanish top-contributor copy and separate summaries.
path = Path('ask_dashboard/_answer_i18n.py')
text = path.read_text(encoding='utf-8')
es_values = {
    'top_single_intro': 'Los principales contribuyentes{period} se ordenan según su **puntuación neta**.',
    'top_multi_intro': 'Con **{count} alianzas** seleccionadas{period}, el panel muestra los **{top_n}** principales contribuyentes de cada alianza. Los jugadores se ordenan según su **puntuación neta**.',
    'top_group_positive': 'contribuyentes con puntuación neta positiva',
    'top_player_detail': 'puntuación neta **{net}** (obtenidos {gained}, perdidos {lost})',
    'top_group_share': 'Los jugadores mostrados representan el **{share:.1f}%** de la contribución positiva de esta alianza en el ámbito de filtros actual.',
}
for key, value in es_values.items():
    text = replace_locale_value(text, 'es', 'fr', key, value)

old = '''        if group.get("positive_total", 0) > 0:\n            ranked_total = sum(\n                row["net_score"] for row in group.get("players", []) if row["net_score"] > 0\n            )\n            lines.append(\n                _t(\n                    locale,\n                    "top_group_share",\n                    share=ranked_total / group["positive_total"] * 100,\n                )\n            )\n        lines.append(_t(locale, "alliance_total", net=legacy.format_signed_score(group["net_total"])))\n'''
new = '''        if group.get("positive_total", 0) > 0:\n            ranked_total = sum(\n                row["net_score"] for row in group.get("players", []) if row["net_score"] > 0\n            )\n            lines.append("")\n            lines.append(\n                _t(\n                    locale,\n                    "top_group_share",\n                    share=ranked_total / group["positive_total"] * 100,\n                )\n            )\n        lines.append("")\n        lines.append(_t(locale, "alliance_total", net=legacy.format_signed_score(group["net_total"])))\n'''
text = replace_once(text, old, new, 'separate top-contributor group summaries')
path.write_text(text, encoding='utf-8')


# Regression coverage for the rendered findings.
path = Path('test_answer_i18n.py')
text = path.read_text(encoding='utf-8')
text = replace_once(
    text,
    'from ui_copy import SUPPORTED_UI_LOCALES\n',
    'from ui_copy import ASK_UI_TEXT, SUPPORTED_UI_LOCALES\n',
    'import Ask Dashboard UI copy for presentation tests',
)
append = r'''


def test_custom_question_guidance_is_consolidated_into_placeholder():
    for locale in SUPPORTED_UI_LOCALES:
        assert "custom_question_help" not in ASK_UI_TEXT[locale]
        placeholder = ASK_UI_TEXT[locale]["question_placeholder"]
        assert "help" in placeholder.casefold()
        assert len(placeholder) > 60

    source = open("app.py", encoding="utf-8").read()
    assert 'st.caption(ask_t("custom_question_help"))' not in source
    assert ASK_UI_TEXT["en"]["analytics_privacy"] == "Usage analytics & privacy"


def test_spanish_top_contributor_copy_and_group_summary_spacing():
    answer = {
        "intent": "top_contributors",
        "status": "ok",
        "period": None,
        "parameters": {},
        "metrics": {"mode": "ranking", "top_n": 2},
        "rankings": {
            "alliances": [
                {
                    "alliance": "MBV",
                    "positive_total": 2000,
                    "net_total": -300,
                    "players": [
                        {
                            "player_name": "Alpha",
                            "net_score": 1200,
                            "score_gained": 1500,
                            "score_lost": 300,
                            "share_of_positive": 60.0,
                        },
                        {
                            "player_name": "Beta",
                            "net_score": 800,
                            "score_gained": 1000,
                            "score_lost": 200,
                            "share_of_positive": 40.0,
                        },
                    ],
                },
                {
                    "alliance": "NoM",
                    "positive_total": 500,
                    "net_total": 400,
                    "players": [
                        {
                            "player_name": "Gamma",
                            "net_score": 500,
                            "score_gained": 600,
                            "score_lost": 100,
                            "share_of_positive": 100.0,
                        }
                    ],
                },
            ]
        },
    }
    rendered = render_dashboard_answer(answer, locale="es")
    assert "Con **2 alianzas** seleccionadas" in rendered
    assert "según su **puntuación neta**" in rendered
    assert "**MBV** — contribuyentes con puntuación neta positiva:" in rendered
    assert "puntuación neta **+1.200**" in rendered
    assert "\n\nLos jugadores mostrados representan el **100,0\u202f%**" in rendered
    assert "\n\nPuntuación neta total de la alianza" in rendered
'''
if 'def test_custom_question_guidance_is_consolidated_into_placeholder' in text:
    raise RuntimeError('presentation cleanup tests already exist')
text = text.rstrip() + append.rstrip() + '\n'
path.write_text(text, encoding='utf-8')
