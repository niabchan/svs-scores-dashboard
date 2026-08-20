from pathlib import Path


table_layout = '''"""Small, framework-independent helpers for responsive table column sizing."""

import unicodedata


def text_width_units(value):
    """Approximate rendered text width without depending on a browser or font engine."""
    text = "" if value is None else str(value)
    units = 0
    for char in text:
        if unicodedata.category(char).startswith("M"):
            continue
        units += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return units


def estimate_column_width(
    header,
    values=(),
    *,
    min_width=88,
    max_width=280,
    pixels_per_unit=8,
    padding=32,
):
    """Estimate a bounded pixel width from both the header and displayed cell values."""
    if min_width <= 0 or max_width < min_width:
        raise ValueError("column width bounds must satisfy 0 < min_width <= max_width")

    candidates = [header, *values]
    widest_units = max((text_width_units(value) for value in candidates), default=0)
    estimated = int(round(widest_units * pixels_per_unit + padding))
    return max(min_width, min(max_width, estimated))
'''
Path("table_layout.py").write_text(table_layout, encoding="utf-8")


tests = '''from pathlib import Path

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
'''
Path("test_table_layout.py").write_text(tests, encoding="utf-8")


app_path = Path("app.py")
text = app_path.read_text(encoding="utf-8")

import_anchor = "from data_loading import coerce_numeric_columns\n"
if text.count(import_anchor) != 1:
    raise RuntimeError("expected one data_loading import anchor")
text = text.replace(
    import_anchor,
    import_anchor + "from table_layout import estimate_column_width\n",
    1,
)

helper_anchor = '''    return alliance_summary\n\n# Fuction: translate net status filter\n'''
helper_code = '''    return alliance_summary\n\n\ndef alliance_summary_column_config(data):\n    """Build one localized, content-aware column configuration for summary tables."""\n    def displayed_values(column, formatter=str):\n        if column not in data.columns:\n            return []\n        return [\n            formatter(value)\n            for value in data[column].dropna().tolist()\n        ]\n\n    def width(column, header, formatter=str, *, max_width=280):\n        return estimate_column_width(\n            header,\n            displayed_values(column, formatter),\n            max_width=max_width,\n        )\n\n    integer = lambda value: f"{int(value):d}"\n    score = lambda value: f"{float(value):,.0f}"\n\n    return {\n        "alliance": st.column_config.TextColumn(\n            t("alliance"),\n            width=width("alliance", t("alliance"), max_width=220),\n        ),\n        "players": st.column_config.NumberColumn(\n            t("players"),\n            format="%d",\n            width=width("players", t("players"), integer),\n        ),\n        "positive_players": st.column_config.NumberColumn(\n            t("positive_players"),\n            format="%d",\n            width=width("positive_players", t("positive_players"), integer),\n        ),\n        "negative_players": st.column_config.NumberColumn(\n            t("negative_players"),\n            format="%d",\n            width=width("negative_players", t("negative_players"), integer),\n        ),\n        "total_score_gained": st.column_config.NumberColumn(\n            t("score_gained"),\n            format="%,.0f",\n            width=width("total_score_gained", t("score_gained"), score),\n        ),\n        "total_score_lost": st.column_config.NumberColumn(\n            t("score_lost"),\n            format="%,.0f",\n            width=width("total_score_lost", t("score_lost"), score),\n        ),\n        "total_net_score": st.column_config.NumberColumn(\n            t("net_score"),\n            format="%,.0f",\n            width=width("total_net_score", t("net_score"), score),\n        ),\n        "average_net_score": st.column_config.NumberColumn(\n            t("net_per_player"),\n            format="%,.0f",\n            width=width("average_net_score", t("net_per_player"), score),\n        ),\n    }\n\n\n# Fuction: translate net status filter\n'''
if text.count(helper_anchor) != 1:
    raise RuntimeError("expected one alliance summary helper anchor")
text = text.replace(helper_anchor, helper_code, 1)

alliance_old = '''        column_config={\n            "alliance": st.column_config.TextColumn(t("alliance"), width="small"),\n            "players": st.column_config.NumberColumn(t("players"), format="%d", width="small"),\n            "positive_players": st.column_config.NumberColumn(t("positive_players"), format="%d"),\n            "negative_players": st.column_config.NumberColumn(t("negative_players"), format="%d"),\n            "total_score_gained": st.column_config.NumberColumn(t("score_gained"), format="%,.0f"),\n            "total_score_lost": st.column_config.NumberColumn(t("score_lost"), format="%,.0f"),\n            "total_net_score": st.column_config.NumberColumn(t("net_score"), format="%,.0f"),\n            "average_net_score": st.column_config.NumberColumn(t("net_per_player"), format="%,.0f", width="medium"),\n        }\n'''
alliance_new = '''        column_config=alliance_summary_column_config(\n            alliance_summary\n        )\n'''
if text.count(alliance_old) != 1:
    raise RuntimeError(
        f"expected one Alliance Summary column config, found {text.count(alliance_old)}"
    )
text = text.replace(alliance_old, alliance_new, 1)

selection_old = '''                column_config={\n                    "alliance": st.column_config.TextColumn(t("alliance")),\n                    "players": st.column_config.NumberColumn(t("players"), format="%d"),\n                    "positive_players": st.column_config.NumberColumn(t("positive_players"), format="%d"),\n                    "negative_players": st.column_config.NumberColumn(t("negative_players"), format="%d"),\n                    "total_score_gained": st.column_config.NumberColumn(t("score_gained"), format="%,.0f"),\n                    "total_score_lost": st.column_config.NumberColumn(t("score_lost"), format="%,.0f"),\n                    "total_net_score": st.column_config.NumberColumn(t("net_score"), format="%,.0f"),\n                    "average_net_score": st.column_config.NumberColumn(t("net_per_player"), format="%,.0f"),\n                }\n'''
selection_new = '''                column_config=alliance_summary_column_config(\n                    selected_alliance_summary\n                )\n'''
if text.count(selection_old) != 1:
    raise RuntimeError(
        "expected one Player Selection summary column config, "
        f"found {text.count(selection_old)}"
    )
text = text.replace(selection_old, selection_new, 1)
app_path.write_text(text, encoding="utf-8")
