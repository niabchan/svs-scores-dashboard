from pathlib import Path

from table_layout import estimate_column_width, text_width_units


APP_PATH = Path(__file__).with_name("app.py")


def test_column_width_accounts_for_localized_header_length():
    short = estimate_column_width("Players", ["12"])
    long = estimate_column_width("Nombre de jugadores positivos", ["12"])
    assert long > short


def test_column_width_accounts_for_formatted_cell_values():
    short = estimate_column_width("Score", ["12"])
    long = estimate_column_width("Score", ["12,345,678,901"])
    assert long > short


def test_column_width_is_bounded():
    assert estimate_column_width("A", [], min_width=96, max_width=240) == 96
    assert estimate_column_width("X" * 200, [], min_width=96, max_width=240) == 240


def test_wide_unicode_characters_receive_more_width_units():
    assert text_width_units("玩家") > text_width_units("AB")


def test_alliance_summary_tables_share_one_column_config_builder():
    source = APP_PATH.read_text(encoding="utf-8")
    assert "def alliance_summary_column_config(data):" in source
    assert source.count("column_config=alliance_summary_column_config(") == 2
