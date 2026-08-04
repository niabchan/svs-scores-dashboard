from pathlib import Path

import pandas as pd
import streamlit as st

from data_quality import build_data_quality_report

st.set_page_config(
    page_title="Data Quality & Methodology | SVS Scores Dashboard",
    page_icon="🔎",
    layout="wide",
)

DATA_PATH = Path(__file__).resolve().parents[1] / "svs_scores_utf8.csv"


@st.cache_data(show_spinner=False)
def load_dashboard_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8")


st.title("Data Quality & Methodology")
st.caption(
    "Preview feature — this page explains the dataset, calculation method, known precision limits, "
    "and automated checks. It does not modify source data or dashboard results."
)

try:
    data = load_dashboard_data(str(DATA_PATH))
except Exception:
    st.error("The dashboard data file could not be loaded for this report.")
    st.stop()

report = build_data_quality_report(data)

st.subheader("Dataset coverage")
metric_columns = st.columns(5)
metric_columns[0].metric("Quality status", report["health"])
metric_columns[1].metric("SVS periods", f'{report["period_count"]:,}')
metric_columns[2].metric("Rows", f'{report["row_count"]:,}')
metric_columns[3].metric("Players", f'{report["player_count"]:,}')
metric_columns[4].metric("Alliances", f'{report["alliance_count"]:,}')

st.dataframe(
    report["period_summary"],
    use_container_width=True,
    hide_index=True,
)

st.info(
    "For 2026-W29 and later, score-gained values for other players are collected from Evony’s "
    "rounded in-game display. Totals, net scores, rankings, and derived results for those periods "
    "should therefore be treated as approximate."
)

st.subheader("Automated data checks")
st.caption(
    "A flagged item means the record deserves review. It does not automatically mean the source entry is wrong."
)

missing_required = report["missing_required_columns"]
invalid_numeric_total = sum(report["invalid_numeric_by_column"].values())

check_rows = pd.DataFrame(
    [
        {
            "Check": "Required columns",
            "Result": "Pass" if not missing_required else "Review",
            "Count": len(missing_required),
            "Meaning": "Columns required for dashboard calculations",
        },
        {
            "Check": "Missing identity/result cells",
            "Result": "Pass" if report["missing_identity_result_count"] == 0 else "Review",
            "Count": report["missing_identity_result_count"],
            "Meaning": "Blank period, alliance, player, net-score, or net-status values",
        },
        {
            "Check": "Blank score-side cells",
            "Result": "Info",
            "Count": report["blank_score_side_count"],
            "Meaning": "Blank gained/lost side; treated as zero for formula review",
        },
        {
            "Check": "Non-numeric score values",
            "Result": "Pass" if invalid_numeric_total == 0 else "Review",
            "Count": invalid_numeric_total,
            "Meaning": "Nonblank score cells that cannot be parsed after removing commas and spaces",
        },
        {
            "Check": "Exact duplicate rows",
            "Result": "Pass" if report["exact_duplicate_rows"] == 0 else "Review",
            "Count": report["exact_duplicate_rows"],
            "Meaning": "Rows identical across every column",
        },
        {
            "Check": "Duplicate period/alliance/player keys",
            "Result": "Pass" if report["duplicate_key_groups"] == 0 else "Review",
            "Count": report["duplicate_key_groups"],
            "Meaning": "More than one row for the same period, alliance, and player",
        },
        {
            "Check": "Net-score formula",
            "Result": "Pass" if report["net_formula_mismatch_count"] == 0 else "Review",
            "Count": report["net_formula_mismatch_count"],
            "Meaning": "Rows where score gained − score lost differs from net score",
        },
        {
            "Check": "Net-status label",
            "Result": "Pass" if report["net_status_mismatch_count"] == 0 else "Review",
            "Count": report["net_status_mismatch_count"],
            "Meaning": "Positive/negative/zero label does not match the net-score sign",
        },
        {
            "Check": "SVS period format",
            "Result": "Pass" if report["malformed_period_count"] == 0 else "Review",
            "Count": report["malformed_period_count"],
            "Meaning": "Period values not written as YYYY-WNN",
        },
    ]
)
st.dataframe(check_rows, use_container_width=True, hide_index=True)

with st.expander("Missing and numeric-value details"):
    detail_columns = st.columns(2)
    with detail_columns[0]:
        st.markdown("**Missing values by dataset column**")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Column": column, "Missing": count}
                    for column, count in report["missing_by_column"].items()
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    with detail_columns[1]:
        st.markdown("**Non-numeric values by score column**")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Column": column, "Non-numeric": count}
                    for column, count in report["invalid_numeric_by_column"].items()
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

st.subheader("Methodology")
st.markdown(
    """
**Core score calculation**

- `net_score = score_gained − score_lost`
- Commas and spaces in score text are removed before numeric checks, matching the dashboard’s loading method.
- A blank `score_gained` or `score_lost` cell represents a one-sided score record and is treated as zero for formula validation. It is shown as information rather than automatically flagged as an error.
- A positive net score contributes to the dashboard’s positive side.
- A negative net score contributes to the negative side.
- Negative contribution charts use the absolute size of negative net scores so their shares are readable as positive percentages.

**Filters and scope**

- SVS period, alliance, net-status, and player-selection filters determine the records included in most charts and Ask Dashboard calculations.
- Results should always be read together with the current filter scope.

**What the dashboard can describe**

- Recorded score gained, score lost, net score, rankings, totals, contribution shares, and the effect of exclusions.

**What the dashboard cannot establish**

- A player’s motive, intention, character, skill, responsibility, strategy, or unseen gameplay circumstances.
- Why an event happened outside relationships that can be calculated directly from the recorded score fields.
"""
)

st.subheader("How to interpret this page")
st.markdown(
    """
This report is a transparency layer rather than an automatic cleaning tool. It deliberately leaves source records unchanged. A reviewer should examine the original collection context before correcting any flagged entry, especially where rounding, name changes, alliance movement, or repeated collection could explain an apparent anomaly.
"""
)
