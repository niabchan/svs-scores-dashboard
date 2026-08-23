"""Responsive Streamlit UI helpers for the SVS Scores Dashboard.

The dashboard intentionally keeps score metrics as full comma-separated numbers.
Streamlit's default metric styling can truncate long values with an ellipsis when a
metric card becomes narrow.  This module installs a small page-config hook so the
responsive CSS is emitted on every Streamlit script rerun.
"""

from __future__ import annotations

from functools import wraps

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx


RESPONSIVE_METRIC_CSS = """
<style>
/* Let metric values scale with the width of their own card, not the viewport. */
[data-testid="stMetric"] {
    container-name: svs-metric;
    container-type: inline-size;
    min-width: 0;
}

[data-testid="stMetricValue"] {
    width: 100%;
    min-width: 0;
    overflow: visible !important;
}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] > div {
    font-size: clamp(0.75rem, 12.5cqw, 2.25rem) !important;
    line-height: 1.15 !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
    font-variant-numeric: tabular-nums;
}

/* Fallback for older browsers that do not support container-query units. */
@supports not (font-size: 1cqw) {
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] > div {
        font-size: clamp(0.85rem, 1.7vw, 2.25rem) !important;
    }
}
</style>
"""


def _emit_responsive_metric_styles() -> None:
    """Add the responsive metric stylesheet to the current Streamlit run."""
    st.markdown(RESPONSIVE_METRIC_CSS, unsafe_allow_html=True)


def install_responsive_metric_styles() -> None:
    """Emit metric CSS immediately after ``st.set_page_config`` on every rerun.

    ``app.py`` imports ``data_loading`` before it calls ``st.set_page_config``.
    Wrapping that call lets the stylesheet be inserted at a valid point in the
    Streamlit command sequence and keeps the style present across script reruns.
    The hook is skipped when modules are imported outside a Streamlit run (for
    example by unit tests), and installation is idempotent.
    """
    if get_script_run_ctx(suppress_warning=True) is None:
        return

    current_set_page_config = st.set_page_config
    if getattr(current_set_page_config, "_svs_responsive_metrics", False):
        return

    @wraps(current_set_page_config)
    def set_page_config_with_responsive_metrics(*args, **kwargs):
        result = current_set_page_config(*args, **kwargs)
        _emit_responsive_metric_styles()
        return result

    set_page_config_with_responsive_metrics._svs_responsive_metrics = True
    st.set_page_config = set_page_config_with_responsive_metrics
