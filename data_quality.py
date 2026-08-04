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

IDENTITY_RESULT_COLUMNS = (
    "svs_date",
    "alliance",
    "player_name",
    "net_score",
    "net_status",
)
SCORE_SIDE_COLUMNS = ("score_gained", "score_lost")
KEY_COLUMNS = ("svs_date", "alliance", "player_name")
SCORE_COLUMNS = ("score_gained", "score_lost", "net_score")
ROUNDED_SCORE_GAINED_START_PERIOD = (2026, 29)
MISSING_SCORE_TOKENS = {"", "null", "none", "nan", "na", "n/a"}


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


def _app_normalized_score_text(data: pd.DataFrame, column: str) -> pd.Series:
    """Normalize score text exactly as the current dashboard loader does."""
    if column not in data.columns:
        return pd.Series(pd.NA, index=data.index, dtype="string")

    normalized = (
        data[column]
        .astype("string")
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    missing_like = normalized.str.casefold().isin(MISSING_SCORE_TOKENS)
    return normalized.mask(missing_like, pd.NA)


def _relaxed_score_text(data: pd.DataFrame, column: str) -> pd.Series:
    """Remove all whitespace to identify formatting-only parse failures."""
    return _app_normalized_score_text(data, column).str.replace(
        r"\s+", "", regex=True
    )


def _app_numeric_series(data: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(_app_normalized_score_text(data, column), errors="coerce")


def _review_numeric_series(data: pd.DataFrame, column: str) -> pd.Series:
    """Parse formatting-recoverable values for source formula review."""
    return pd.to_numeric(_relaxed_score_text(data, column), errors="coerce")


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
    Blank gained/lost cells are reported separately because one-sided score
    records use a blank side as zero for formula validation.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    missing_required = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    present_required = [column for column in REQUIRED_COLUMNS if column in data.columns]
    missing_by_column = {
        column: int(data[column].isna().sum()) for column in present_required
    }
    missing_identity_result_count = sum(
        missing_by_column.get(column, 0) for column in IDENTITY_RESULT_COLUMNS
    )
    blank_score_side_count = sum(
        missing_by_column.get(column, 0) for column in SCORE_SIDE_COLUMNS
    )

    invalid_numeric_by_column: dict[str, int] = {}
    loader_formatting_by_column: dict[str, int] = {}
    numeric: dict[str, pd.Series] = {}
    for column in SCORE_COLUMNS:
        app_text = _app_normalized_score_text(data, column)
        app_numeric = _app_numeric_series(data, column)
        review_numeric = _review_numeric_series(data, column)
        numeric[column] = review_numeric

        loader_formatting_by_column[column] = int(
            (app_text.notna() & app_numeric.isna() & review_numeric.notna()).sum()
        )
        invalid_numeric_by_column[column] = int(
            (app_text.notna() & review_numeric.isna()).sum()
        )

    exact_duplicate_rows = int(data.duplicated(keep=False).sum()) if not data.empty else 0

    if all(column in data.columns for column in KEY_COLUMNS):
        duplicate_key_mask = data.duplicated(list(KEY_COLUMNS), keep=False)
        duplicate_key_rows = int(duplicate_key_mask.sum())
        duplicate_key_groups = int(
            data.loc[duplicate_key_mask, list(KEY_COLUMNS)]
            .drop_duplicates()
            .shape[0]
        )
    else:
        duplicate_key_rows = 0
        duplicate_key_groups = 0

    if all(column in data.columns for column in SCORE_COLUMNS):
        comparable = numeric["net_score"].notna()
        expected_net = (
            numeric["score_gained"].fillna(0)
            - numeric["score_lost"].fillna(0)
        )
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

    invalid_numeric_total = sum(invalid_numeric_by_column.values())
    loader_formatting_total = sum(loader_formatting_by_column.values())
    review_issue_count = (
        duplicate_key_groups
        + net_formula_mismatch_count
        + net_status_mismatch_count
        + malformed_period_count
    )
    if (
        missing_required
        or invalid_numeric_total
        or loader_formatting_total
        or missing_identity_result_count
    ):
        health = "Needs attention"
    elif review_issue_count:
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
        "missing_identity_result_count": int(missing_identity_result_count),
        "blank_score_side_count": int(blank_score_side_count),
        "loader_formatting_by_column": loader_formatting_by_column,
        "invalid_numeric_by_column": invalid_numeric_by_column,
        "exact_duplicate_rows": exact_duplicate_rows,
        "duplicate_key_rows": duplicate_key_rows,
        "duplicate_key_groups": duplicate_key_groups,
        "net_formula_mismatch_count": net_formula_mismatch_count,
        "net_status_mismatch_count": net_status_mismatch_count,
        "malformed_period_count": malformed_period_count,
        "period_summary": period_summary,
    }
