"""Regression tests for responsive Streamlit metric styling."""

import ui_responsive


def test_metric_css_scales_with_card_width_and_keeps_full_value():
    css = ui_responsive.RESPONSIVE_METRIC_CSS

    assert 'container-type: inline-size' in css
    assert '12.5cqw' in css
    assert 'font-size: clamp(0.75rem, 12.5cqw, 2.25rem)' in css
    assert 'white-space: nowrap !important' in css
    assert 'overflow: visible !important' in css
    assert 'text-overflow: clip !important' in css


def test_metric_rows_use_equal_card_widths_above_mobile_breakpoint():
    css = ui_responsive.RESPONSIVE_METRIC_CSS

    assert '@media (min-width: 641px)' in css
    assert '[data-testid="stHorizontalBlock"]:has(' in css
    assert '> [data-testid="stColumn"] [data-testid="stMetric"]' in css
    assert 'flex: 1 1 0 !important' in css
    assert 'width: 0 !important' in css
    assert 'min-width: 0 !important' in css


def test_install_wraps_page_config_and_emits_css_once_per_call(monkeypatch):
    calls = []

    def fake_set_page_config(*args, **kwargs):
        calls.append(("config", args, kwargs))
        return "configured"

    def fake_markdown(body, *, unsafe_allow_html=False):
        calls.append(("markdown", body, unsafe_allow_html))

    monkeypatch.setattr(
        ui_responsive,
        "get_script_run_ctx",
        lambda suppress_warning=True: object(),
    )
    monkeypatch.setattr(ui_responsive.st, "set_page_config", fake_set_page_config)
    monkeypatch.setattr(ui_responsive.st, "markdown", fake_markdown)

    ui_responsive.install_responsive_metric_styles()
    wrapped = ui_responsive.st.set_page_config

    assert wrapped is not fake_set_page_config
    assert getattr(wrapped, "_svs_responsive_metrics", False) is True

    result = wrapped(page_title="SVS Scores Dashboard", layout="wide")

    assert result == "configured"
    assert calls[0] == (
        "config",
        (),
        {"page_title": "SVS Scores Dashboard", "layout": "wide"},
    )
    assert calls[1] == (
        "markdown",
        ui_responsive.RESPONSIVE_METRIC_CSS,
        True,
    )

    # Re-installation must not wrap the wrapper again.
    ui_responsive.install_responsive_metric_styles()
    assert ui_responsive.st.set_page_config is wrapped


def test_install_is_noop_without_streamlit_run_context(monkeypatch):
    def fake_set_page_config(*args, **kwargs):
        return None

    monkeypatch.setattr(
        ui_responsive,
        "get_script_run_ctx",
        lambda suppress_warning=True: None,
    )
    monkeypatch.setattr(ui_responsive.st, "set_page_config", fake_set_page_config)

    ui_responsive.install_responsive_metric_styles()

    assert ui_responsive.st.set_page_config is fake_set_page_config
