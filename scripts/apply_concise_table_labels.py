from pathlib import Path


APP_PATH = Path("app.py")
TEST_PATH = Path("test_table_layout.py")


TRANSLATION_REPLACEMENTS = {
    '''        "positive_players": "Positive Players",\n        "negative_players": "Negative Players",\n''': '''        "positive_players": "Positive Players",\n        "negative_players": "Negative Players",\n        "table_positive_players": "Positive Players",\n        "table_negative_players": "Negative Players",\n        "table_positive_players_help": "Players with a positive net score.",\n        "table_negative_players_help": "Players with a negative net score.",\n''',
    '''        "positive_players": "Jugadores positivos",\n        "negative_players": "Jugadores negativos",\n''': '''        "positive_players": "Jugadores positivos",\n        "negative_players": "Jugadores negativos",\n        "table_positive_players": "Jugadores positivos",\n        "table_negative_players": "Jugadores negativos",\n        "table_positive_players_help": "Jugadores con puntuación neta positiva.",\n        "table_negative_players_help": "Jugadores con puntuación neta negativa.",\n''',
    '''        "positive_players": "Joueurs positifs",\n        "negative_players": "Joueurs négatifs",\n''': '''        "positive_players": "Joueurs positifs",\n        "negative_players": "Joueurs négatifs",\n        "table_positive_players": "Joueurs positifs",\n        "table_negative_players": "Joueurs négatifs",\n        "table_positive_players_help": "Joueurs ayant un score net positif.",\n        "table_negative_players_help": "Joueurs ayant un score net négatif.",\n''',
    '''        "positive_players": "Người chơi dương",\n        "negative_players": "Người chơi âm",\n''': '''        "positive_players": "Người chơi dương",\n        "negative_players": "Người chơi âm",\n        "table_positive_players": "Người chơi dương",\n        "table_negative_players": "Người chơi âm",\n        "table_positive_players_help": "Người chơi có điểm ròng dương.",\n        "table_negative_players_help": "Người chơi có điểm ròng âm.",\n''',
    '''        "positive_players": "Pemain dengan Poin Bersih Positif",\n        "negative_players": "Pemain dengan Poin Bersih Negatif",\n''': '''        "positive_players": "Pemain dengan Poin Bersih Positif",\n        "negative_players": "Pemain dengan Poin Bersih Negatif",\n        "table_positive_players": "Pemain Positif",\n        "table_negative_players": "Pemain Negatif",\n        "table_positive_players_help": "Pemain dengan poin bersih positif.",\n        "table_negative_players_help": "Pemain dengan poin bersih negatif.",\n''',
}

CONFIG_REPLACEMENTS = {
    '''        "positive_players": st.column_config.NumberColumn(\n            t("positive_players"),\n            format="%d",\n        ),\n''': '''        "positive_players": st.column_config.NumberColumn(\n            t("table_positive_players"),\n            help=t("table_positive_players_help"),\n            format="%d",\n        ),\n''',
    '''        "negative_players": st.column_config.NumberColumn(\n            t("negative_players"),\n            format="%d",\n        ),\n''': '''        "negative_players": st.column_config.NumberColumn(\n            t("table_negative_players"),\n            help=t("table_negative_players_help"),\n            format="%d",\n        ),\n''',
}


def replace_once_or_accept_applied(text, old, new, description):
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        return text.replace(old, new, 1)
    if old_count == 0 and new_count == 1:
        return text
    raise RuntimeError(
        f"Unexpected state for {description}: old={old_count}, new={new_count}"
    )


text = APP_PATH.read_text(encoding="utf-8")
for index, (old, new) in enumerate(TRANSLATION_REPLACEMENTS.items(), start=1):
    text = replace_once_or_accept_applied(text, old, new, f"translation block {index}")
for index, (old, new) in enumerate(CONFIG_REPLACEMENTS.items(), start=1):
    text = replace_once_or_accept_applied(text, old, new, f"column config {index}")
APP_PATH.write_text(text, encoding="utf-8")


test_text = '''from pathlib import Path\n\n\nAPP_PATH = Path(__file__).with_name("app.py")\n\n\ndef _summary_config_source():\n    source = APP_PATH.read_text(encoding="utf-8")\n    start = source.index("def alliance_summary_column_config():")\n    end = source.index("# Fuction: translate net status filter", start)\n    return source, source[start:end]\n\n\ndef test_alliance_summary_tables_share_one_column_config_builder():\n    source, _ = _summary_config_source()\n    assert source.count("column_config=alliance_summary_column_config()") == 2\n\n\ndef test_summary_config_preserves_balanced_baseline_widths():\n    source, config = _summary_config_source()\n    assert "estimate_column_width" not in source\n    assert 'width="small"' in config\n    assert config.count('width="small"') == 2\n    assert config.count('width="medium"') == 1\n    assert "width=88" not in config\n    assert "width=280" not in config\n\n\ndef test_summary_config_uses_table_specific_player_status_labels_and_help():\n    _, config = _summary_config_source()\n    assert 't("table_positive_players")' in config\n    assert 'help=t("table_positive_players_help")' in config\n    assert 't("table_negative_players")' in config\n    assert 'help=t("table_negative_players_help")' in config\n    assert 't("positive_players")' not in config\n    assert 't("negative_players")' not in config\n\n\ndef test_indonesian_table_labels_are_concise_and_distinguishable():\n    source = APP_PATH.read_text(encoding="utf-8")\n    assert '\"table_positive_players\": \"Pemain Positif\"' in source\n    assert '\"table_negative_players\": \"Pemain Negatif\"' in source\n    assert '\"table_positive_players_help\": \"Pemain dengan poin bersih positif.\"' in source\n    assert '\"table_negative_players_help\": \"Pemain dengan poin bersih negatif.\"' in source\n'''
TEST_PATH.write_text(test_text, encoding="utf-8")
