from pathlib import Path


APP_PATH = Path(__file__).with_name("app.py")


def _summary_config_source():
    source = APP_PATH.read_text(encoding="utf-8")
    start = source.index("def alliance_summary_column_config():")
    end = source.index("# Fuction: translate net status filter", start)
    return source, source[start:end]


def test_alliance_summary_tables_share_one_column_config_builder():
    source, _ = _summary_config_source()
    assert source.count("column_config=alliance_summary_column_config()") == 2


def test_summary_config_preserves_balanced_baseline_widths():
    source, config = _summary_config_source()
    assert "estimate_column_width" not in source
    assert 'width="small"' in config
    assert config.count('width="small"') == 2
    assert config.count('width="medium"') == 1
    assert "width=88" not in config
    assert "width=280" not in config


def test_summary_config_uses_table_specific_player_status_labels_and_help():
    _, config = _summary_config_source()
    assert 't("table_positive_players")' in config
    assert 'help=t("table_positive_players_help")' in config
    assert 't("table_negative_players")' in config
    assert 'help=t("table_negative_players_help")' in config
    assert 't("positive_players")' not in config
    assert 't("negative_players")' not in config


def test_indonesian_table_labels_are_concise_and_distinguishable():
    source = APP_PATH.read_text(encoding="utf-8")
    assert '"table_positive_players": "Pemain Positif"' in source
    assert '"table_negative_players": "Pemain Negatif"' in source
    assert '"table_positive_players_help": "Pemain dengan poin bersih positif."' in source
    assert '"table_negative_players_help": "Pemain dengan poin bersih negatif."' in source
