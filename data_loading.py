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


def coerce_numeric_columns(
    data: pd.DataFrame,
    columns: Iterable[str] = DEFAULT_NUMERIC_COLUMNS,
) -> pd.DataFrame:
    """Return a copy with selected columns safely coerced to numeric values.

    Source CSV values may contain thousands separators and whitespace around or
    inside a signed number, for example ``- 546,738,937``. Whitespace has no
    numeric meaning in these score fields, so it is removed before coercion.
    Missing and genuinely invalid values continue to become ``NaN``.
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

    return cleaned
