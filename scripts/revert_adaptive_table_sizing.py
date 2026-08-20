from pathlib import Path


APP_PATH = Path("app.py")
TEST_PATH = Path("test_table_layout.py")
WORKFLOW_PATH = Path(".github/workflows/tests.yml")
SELF_PATH = Path("scripts/revert_adaptive_table_sizing.py")
TABLE_LAYOUT_PATH = Path("table_layout.py")


app = APP_PATH.read_text(encoding="utf-8")

import_line = "from table_layout import estimate_column_width\n"
if app.count(import_line) != 1:
    raise RuntimeError(f"expected one adaptive table-layout import, found {app.count(import_line)}")
app = app.replace(import_line, "", 1)

old_helper = '''def alliance_summary_column_config(data):
    """Build one localized, content-aware column configuration for summary tables."""
    def displayed_values(column, formatter=str):
        if column not in data.columns:
            return []
        return [
            formatter(value)
            for value in data[column].dropna().tolist()
        ]

    def width(column, header, formatter=str, *, max_width=280):
        return estimate_column_width(
            header,
            displayed_values(column, formatter),
            max_width=max_width,
        )

    integer = lambda value: f"{int(value):d}"
    score = lambda value: f"{float(value):,.0f}"

    return {
        "alliance": st.column_config.TextColumn(
            t("alliance"),
            width=width("alliance", t("alliance"), max_width=220),
        ),
        "players": st.column_config.NumberColumn(
            t("players"),
            format="%d",
            width=width("players", t("players"), integer),
        ),
        "positive_players": st.column_config.NumberColumn(
            t("positive_players"),
            format="%d",
            width=width("positive_players", t("positive_players"), integer),
        ),
        "negative_players": st.column_config.NumberColumn(
            t("negative_players"),
            format="%d",
            width=width("negative_players", t("negative_players"), integer),
        ),
        "total_score_gained": st.column_config.NumberColumn(
            t("score_gained"),
            format="%,.0f",
            width=width("total_score_gained", t("score_gained"), score),
        ),
        "total_score_lost": st.column_config.NumberColumn(
            t("score_lost"),
            format="%,.0f",
            width=width("total_score_lost", t("score_lost"), score),
        ),
        "total_net_score": st.column_config.NumberColumn(
            t("net_score"),
            format="%,.0f",
            width=width("total_net_score", t("net_score"), score),
        ),
        "average_net_score": st.column_config.NumberColumn(
            t("net_per_player"),
            format="%,.0f",
            width=width("average_net_score", t("net_per_player"), score),
        ),
    }
'''

new_helper = '''def alliance_summary_column_config():
    """Build the shared localized column configuration for alliance summary tables."""
    return {
        "alliance": st.column_config.TextColumn(
            t("alliance"),
            width="small",
        ),
        "players": st.column_config.NumberColumn(
            t("players"),
            format="%d",
            width="small",
        ),
        "positive_players": st.column_config.NumberColumn(
            t("positive_players"),
            format="%d",
        ),
        "negative_players": st.column_config.NumberColumn(
            t("negative_players"),
            format="%d",
        ),
        "total_score_gained": st.column_config.NumberColumn(
            t("score_gained"),
            format="%,.0f",
        ),
        "total_score_lost": st.column_config.NumberColumn(
            t("score_lost"),
            format="%,.0f",
        ),
        "total_net_score": st.column_config.NumberColumn(
            t("net_score"),
            format="%,.0f",
        ),
        "average_net_score": st.column_config.NumberColumn(
            t("net_per_player"),
            format="%,.0f",
            width="medium",
        ),
    }
'''

if app.count(old_helper) != 1:
    raise RuntimeError(f"expected one adaptive summary config helper, found {app.count(old_helper)}")
app = app.replace(old_helper, new_helper, 1)

old_alliance_call = '''column_config=alliance_summary_column_config(
            alliance_summary
        )'''
old_selection_call = '''column_config=alliance_summary_column_config(
                    selected_alliance_summary
                )'''
if app.count(old_alliance_call) != 1:
    raise RuntimeError(f"expected one Alliance Summary config call, found {app.count(old_alliance_call)}")
if app.count(old_selection_call) != 1:
    raise RuntimeError(f"expected one Player Selection config call, found {app.count(old_selection_call)}")
app = app.replace(old_alliance_call, "column_config=alliance_summary_column_config()", 1)
app = app.replace(old_selection_call, "column_config=alliance_summary_column_config()", 1)

if "estimate_column_width" in app:
    raise RuntimeError("adaptive pixel sizing reference still remains in app.py")
APP_PATH.write_text(app, encoding="utf-8")

TEST_PATH.write_text(
    '''from pathlib import Path


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
''',
    encoding="utf-8",
)

if not TABLE_LAYOUT_PATH.exists():
    raise RuntimeError("table_layout.py is missing before cleanup")
TABLE_LAYOUT_PATH.unlink()

WORKFLOW_PATH.write_text(
    '''name: Tests

on:
  pull_request:
  push:
    branches:
      - ask-dashboard-wip
      - work

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install test dependencies
        run: python -m pip install -r requirements-test.txt
      - name: Compile Python files
        run: python -m py_compile app.py ask_dashboard.py openai_intent.py data_loading.py usage_analytics.py ui_copy.py test_ask_dashboard.py test_alliance_score_overview.py test_data_loading.py test_table_layout.py test_usage_analytics.py test_ui_copy.py test_ui_copy_shell.py
      - name: Run tests
        run: python -m pytest -q
''',
    encoding="utf-8",
)

SELF_PATH.unlink()
