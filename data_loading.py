"""Shared data-loading helpers for the SVS Scores Dashboard."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from ui_responsive import install_responsive_metric_styles


# app.py imports this module before calling st.set_page_config. Install the
# lightweight page-config wrapper here so responsive metric CSS is emitted on
# every Streamlit rerun without coupling the score formatting to a specific tab.
install_responsive_metric_styles()


DEFAULT_NUMERIC_COLUMNS = (
    "score_gained",
    "score_lost",
    "net_score",
    "competition_rank",
)


def _fill_missing_net_status(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Derive a missing ``net_status`` from the already-numeric ``net_score``.

    ``net_status`` is redundant source data because its meaning follows directly
    from the sign of ``net_score``.  Keep any explicit non-empty source value,
    but repair blank/NULL-like values so a newly uploaded SVS period cannot be
    filtered down to zero rows merely because that derived column was omitted.
    """
    if "net_score" not in cleaned.columns:
        return cleaned

    if "net_status" not in cleaned.columns:
        cleaned["net_status"] = pd.NA

    status_text = cleaned["net_status"].astype("string").str.strip()
    missing_status = (
        cleaned["net_status"].isna()
        | status_text.eq("")
        | status_text.str.upper().isin({"NULL", "NAN", "NONE"})
    )

    cleaned.loc[missing_status & cleaned["net_score"].gt(0), "net_status"] = "Positive"
    cleaned.loc[missing_status & cleaned["net_score"].lt(0), "net_status"] = "Negative"
    cleaned.loc[missing_status & cleaned["net_score"].eq(0), "net_status"] = "Zero"

    return cleaned


def coerce_numeric_columns(
    data: pd.DataFrame,
    columns: Iterable[str] = DEFAULT_NUMERIC_COLUMNS,
) -> pd.DataFrame:
    """Return a cleaned copy with score fields coerced and missing status derived.

    Source CSV values may contain thousands separators and whitespace around or
    inside a signed number, for example ``- 546,738,937``. Whitespace has no
    numeric meaning in these score fields, so it is removed before coercion.
    Missing and genuinely invalid numeric values continue to become ``NaN``.

    When ``net_score`` is available, blank/NULL-like ``net_status`` values are
    derived from its sign. Existing non-empty status values are preserved.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    cleaned = data.copy()
    for column in columns:
        if column not in cleaned.columns:
            continue

        normalized = (
            cleaned[column]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace(r"\s+", "", regex=True)
        )
        cleaned[column] = pd.to_numeric(normalized, errors="coerce")

    return _fill_missing_net_status(cleaned)
