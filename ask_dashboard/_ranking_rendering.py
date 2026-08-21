"""Ranking-focused rendering layered on top of the standard dashboard renderer."""

from __future__ import annotations

from ._answer_i18n import render_localized_dashboard_answer
from ._legacy import legacy
from ._rendering import (
    _show_notice,
    _status_message,
    render_dashboard_answer as _base_render_dashboard_answer,
)


def _render_alliance_net_score_ranking(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance

    metrics = answer.get("metrics", {})
    rows = answer.get("rankings", {}).get("alliances", [])
    period_text = legacy._period_text(answer.get("period"))
    leaders = metrics.get("leaders", [])

    if metrics.get("leader_count", len(leaders)) > 1:
        names = ", ".join(f"**{row['alliance']}**" for row in leaders)
        intro = (
            f"Under the current sidebar filters{period_text}, {names} are tied for first "
            f"in total net score at **{legacy.format_signed_score(metrics['top_net_score'])}**."
        )
    else:
        leader = leaders[0]
        intro = (
            f"Under the current sidebar filters{period_text}, **{leader['alliance']}** "
            f"leads total net score with "
            f"**{legacy.format_signed_score(leader['total_net_score'])}**."
        )

    ranking_lines = "\n".join(
        f"{row['net_rank']}. **{row['alliance']}** — "
        f"**{legacy.format_signed_score(row['total_net_score'])}**"
        for row in rows
    )

    metric_note = (
        "Only alliance total net score is ranked here. Positive-contribution rank "
        "is a separate metric and is not part of this list."
    )

    return (
        f"{intro}\n\n"
        f"**Alliance net-score ranking — current filters**\n{ranking_lines}"
        f"\n\n{metric_note}"
    )


def render_dashboard_answer(answer, locale="en"):
    """Render an answer in the requested UI locale, defaulting to established English."""
    localized = render_localized_dashboard_answer(answer, locale)
    if localized is not None:
        return localized

    if isinstance(answer, dict) and answer.get("intent") == "net_score_leader_summary":
        rendered = _render_alliance_net_score_ranking(answer)
        if _show_notice(answer):
            rendered += f"\n\n---\n\n{legacy.ROUNDED_SCORE_NOTICE}"
        return rendered
    return _base_render_dashboard_answer(answer)


def answer_dashboard_question(*args, locale="en", **kwargs):
    from ._calculation import calculate_dashboard_answer

    return render_dashboard_answer(
        calculate_dashboard_answer(*args, **kwargs),
        locale=locale,
    )
