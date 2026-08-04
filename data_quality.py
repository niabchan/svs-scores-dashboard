"""Data-quality and methodology helpers for the SVS Scores Dashboard.

The functions in this module inspect data and return plain Python values or
pandas DataFrames. They never alter source data or change dashboard scores.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = (
    "svs_date",
    "alliance",
    "player_name",
    "score_gained",
    "score_lost",
    "net_score",
    "net_status",
)

KEY_COLUMNS = ("svs_date", "alliance", "player_name")
SCORE_COLUMNS = ("score_gained", "score_lost", "net_score")
ROUNDED_SCORE_GAINED_START_PERIOD = (2026, 29)


def parse_svs_period(value: Any) -> tuple[int, int] | None:
    """Parse a strict YYYY-WNN period, returning ``None`` when invalid."""
    match = re.fullmatch(r"(\d{4})-W(\d{2})", str(value))
    if not match:
        return None
    year, week = map(int, match.groups())
    if not 1 <= week <= 53:
        return None
    return year, week


def score_gained_precision(period: Any) -> str:
    """Describe the known precision of collected score-gained values."""
    parsed = parse_svs_period(period)
    if parsed is None:
        return "Unknown period format"
    if parsed >= ROUNDED_SCORE_GAINED_START_PERIOD:
        return "Rounded in-game display"
    return "Full-value display"


def _numeric_series(data: pd.DataFrame, column: str) -> pd.Series:
    if column not in data.columns:
        return pd.Series(index=data.index, dtype="float64")
    return pd.to_numeric(data[column], errors="coerce")


def _count_net_status_mismatches(data: pd.DataFrame, numeric_net: pd.Series) -> int:
    if "net_status" not in data.columns or "net_score" not in data.columns:
        return 0

    statuses = data["net_status"].astype("string").str.strip().str.casefold()
    expected = pd.Series("zero", index=data.index, dtype="string")
    expected.loc[numeric_net > 0] = "positive"
    expected.loc[numeric_net < 0] = "negative"

    recognized = statuses.isin({"positive", "negative", "zero"})
    comparable = recognized & numeric_net.notna()
    return int((statuses[comparable] != expected[comparable]).sum())


def build_period_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Return period-level coverage and precision metadata for display."""
    columns = [
        "SVS Period",
        "Rows",
        "Players",
        "Alliances",
        "Score-gained precision",
    ]
    if "svs_date" not in data.columns or data.empty:
        return pd.DataFrame(columns=columns)

    records: list[dict[str, Any]] = []
    period_values = sorted(
        data["svs_date"].dropna().astype(str).unique().tolist(),
        key=lambda value: parse_svs_period(value) or (9999, 99),
    )
    for period in period_values:
        scope = data[data["svs_date"].astype(str) == period]
        records.append(
            {
                "SVS Period": period,
                "Rows": int(len(scope)),
                "Players": int(scope["player_name"].nunique(dropna=True))
                if "player_name" in scope.columns
                else 0,
                "Alliances": int(scope["alliance"].nunique(dropna=True))
                if "alliance" in scope.columns
                else 0,
                "Score-gained precision": score_gained_precision(period),
            }
        )
    return pd.DataFrame.from_records(records, columns=columns)


def build_data_quality_report(data: pd.DataFrame) -> dict[str, Any]:
    """Inspect the dashboard dataset without mutating it.

    Counts are intentionally conservative. A reported duplicate or mismatch is
    a prompt for review, not an automatic conclusion that a record is wrong.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    missing_required = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    present_required = [column for column in REQUIRED_COLUMNS if column in data.columns]
    missing_by_column = {
        column: int(data[column].isna().sum()) for column in present_required
    }

    invalid_numeric_by_column: dict[str, int] = {}
    numeric: dict[str, pd.Series] = {}
    for column in SCORE_COLUMNS:
        series = _numeric_series(data, column)
        numeric[column] = series
        if column in data.columns:
            invalid_numeric_by_column[column] = int(
                (data[column].notna() & series.isna()).sum()
            )
        else:
            invalid_numeric_by_column[column] = 0

    exact_duplicate_rows = int(data.duplicated(keep=False).sum()) if not data.empty else 0

    if all(column in data.columns for column in KEY_COLUMNS):
        duplicate_key_rows = int(data.duplicated(list(KEY_COLUMNS), keep=False).sum())
        duplicate_key_groups = int(
            data.loc[data.duplicated(list(KEY_COLUMNS), keep=False), list(KEY_COLUMNS)]
            .drop_duplicates()
            .shape[0]
        )
    else:
        duplicate_key_rows = 0
        duplicate_key_groups = 0

    if all(column in data.columns for column in SCORE_COLUMNS):
        comparable = (
            numeric["score_gained"].notna()
            & numeric["score_lost"].notna()
            & numeric["net_score"].notna()
        )
        expected_net = numeric["score_gained"] - numeric["score_lost"]
        net_formula_mismatch_count = int(
            (comparable & ((expected_net - numeric["net_score"]).abs() > 0.5)).sum()
        )
    else:
        net_formula_mismatch_count = 0

    net_status_mismatch_count = _count_net_status_mismatches(
        data, numeric.get("net_score", pd.Series(index=data.index, dtype="float64"))
    )

    period_summary = build_period_summary(data)
    malformed_period_count = 0
    if "svs_date" in data.columns:
        malformed_period_count = int(
            data["svs_date"].dropna().map(parse_svs_period).isna().sum()
        )

    issue_count = (
        len(missing_required)
        + sum(missing_by_column.values())
        + sum(invalid_numeric_by_column.values())
        + duplicate_key_groups
        + net_formula_mismatch_count
        + net_status_mismatch_count
        + malformed_period_count
    )
    if missing_required or sum(invalid_numeric_by_column.values()):
        health = "Needs attention"
    elif issue_count:
        health = "Review suggested"
    else:
        health = "No issues detected"

    return {
        "health": health,
        "row_count": int(len(data)),
        "period_count": int(data["svs_date"].nunique(dropna=True))
        if "svs_date" in data.columns
        else 0,
        "player_count": int(data["player_name"].nunique(dropna=True))
        if "player_name" in data.columns
        else 0,
        "alliance_count": int(data["alliance"].nunique(dropna=True))
        if "alliance" in data.columns
        else 0,
        "missing_required_columns": missing_required,
        "missing_by_column": missing_by_column,
        "invalid_numeric_by_column": invalid_numeric_by_column,
        "exact_duplicate_rows": exact_duplicate_rows,
        "duplicate_key_rows": duplicate_key_rows,
        "duplicate_key_groups": duplicate_key_groups,
        "net_formula_mismatch_count": net_formula_mismatch_count,
        "net_status_mismatch_count": net_status_mismatch_count,
        "malformed_period_count": malformed_period_count,
        "period_summary": period_summary,
    }
