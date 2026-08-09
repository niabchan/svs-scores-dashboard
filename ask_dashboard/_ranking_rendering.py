"""Ranking-focused rendering layered on top of the standard dashboard renderer."""

from __future__ import annotations

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

    leader_details = ""
    if metrics.get("leader_count", len(leaders)) == 1:
        leader = leaders[0]
        leader_details = (
            "\n\n**Leader breakdown**\n"
            f"- **Positive contribution:** {legacy.format_score(leader['positive_contribution'])}\n"
            f"- **Negative impact:** {legacy.format_score(leader['negative_impact'])}\n"
            f"- **Positive-contribution rank:** #{leader['positive_rank']}"
        )

    filter_note = (
        "This ranking uses only the data remaining under the current sidebar filters "
        "and the selected SVS period. Selecting an earlier period recalculates the "
        "ranking for that period; it does not default to the latest SVS."
    )

    return (
        f"{intro}\n\n"
        f"**Alliance net-score ranking — current filters**\n{ranking_lines}"
        f"{leader_details}\n\n{filter_note}"
    )


def render_dashboard_answer(answer):
    if isinstance(answer, dict) and answer.get("intent") == "net_score_leader_summary":
        rendered = _render_alliance_net_score_ranking(answer)
        if _show_notice(answer):
            rendered += f"\n\n---\n\n{legacy.ROUNDED_SCORE_NOTICE}"
        return rendered
    return _base_render_dashboard_answer(answer)


def answer_dashboard_question(*args, **kwargs):
    from ._calculation import calculate_dashboard_answer

    return render_dashboard_answer(calculate_dashboard_answer(*args, **kwargs))
