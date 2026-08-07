"""Direct, subject-aware rendering for contribution leader answers."""

from __future__ import annotations

from ._legacy import legacy
from ._routing import (
    ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
    SCORE_DERIVED_INTENTS,
)


def _status_message(answer):
    code = answer.get("guidance_code") or answer.get("error_code")
    if code == "no_positive_contribution":
        if answer.get("parameters", {}).get("scope") == "server":
            return "No positive player net score is available for the full server in this SVS period."
        return "No positive player net score is available under the current sidebar filters."
    return legacy._status_message(answer)


def _scope_intro(answer):
    scope = answer.get("metrics", {}).get(
        "scope",
        answer.get("parameters", {}).get("scope", "current_filters"),
    )
    period = legacy._period_text(answer.get("period"))
    return (
        f"Across the full server{period}"
        if scope == "server"
        else f"Under the current sidebar filters{period}"
    )


def _render_player_leader(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance
    metrics = answer["metrics"]
    leaders = metrics.get("leaders", [])
    intro = _scope_intro(answer)
    scope_names = (
        answer.get("parameters", {}).get("matched_alliances")
        or answer.get("parameters", {}).get("alliance_names")
        or []
    )
    alliance_scope = (
        f" within **{'/'.join(map(str, scope_names))}**" if scope_names else ""
    )
    if metrics.get("leader_count", 0) > 1:
        names = ", ".join(
            f"**{row['player_name']}** ({row['alliance']})" for row in leaders
        )
        return (
            f"{intro}{alliance_scope}, {names} are tied for the largest positive "
            f"contribution at **{legacy.format_signed_score(metrics['top_positive_contribution'])}** each."
        )
    top = leaders[0]
    return (
        f"{intro}{alliance_scope}, **{top['player_name']}** contributed the most to the "
        f"positive score with **{legacy.format_signed_score(top['positive_contribution'])}**.\n\n"
        f"- **Alliance:** {top['alliance']}\n"
        f"- **Score gained:** {legacy.format_score(top['score_gained'])}\n"
        f"- **Score lost:** {legacy.format_score(top['score_lost'])}\n"
        f"- **Share of positive contribution in this scope:** "
        f"{top['share_of_scope_positive']:.1f}%"
    )


def _render_alliance_leader(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance
    metrics = answer["metrics"]
    leaders = metrics.get("leaders", [])
    intro = _scope_intro(answer)
    if metrics.get("leader_count", 0) > 1:
        names = ", ".join(f"**{row['alliance']}**" for row in leaders)
        return (
            f"{intro}, {names} are tied for the largest positive contribution at "
            f"**{legacy.format_signed_score(metrics['top_positive_contribution'])}** each."
        )
    leader = leaders[0]
    rows = answer.get("rankings", {}).get("alliances", [])
    ranking = "\n".join(
        f"{row['rank']}. **{row['alliance']}** — "
        f"{legacy.format_score(row['positive_contribution'])} "
        f"({row['share_of_scope_positive']:.1f}%)"
        for row in rows[:5]
    )
    return (
        f"{intro}, **{leader['alliance']}** contributed the most to the positive score "
        f"with **{legacy.format_signed_score(leader['positive_contribution'])}**.\n\n"
        f"It generated **{leader['share_of_scope_positive']:.1f}%** of the positive "
        f"contribution in this scope.\n\n"
        f"**Positive-contribution ranking**\n{ranking}"
    )


def _show_notice(answer):
    period = legacy._parse_svs_period(answer.get("period"))
    if period is None or answer.get("status") != "ok":
        return False
    if answer.get("intent") not in SCORE_DERIVED_INTENTS:
        return False
    return period >= legacy.ROUNDED_SCORE_GAINED_START_PERIOD and (
        legacy.ROUNDED_SCORE_GAINED_END_PERIOD is None
        or period <= legacy.ROUNDED_SCORE_GAINED_END_PERIOD
    )


def render_dashboard_answer(answer):
    if not isinstance(answer, dict):
        return str(answer)
    if answer.get("intent") == ALLIANCE_POSITIVE_CONTRIBUTION_INTENT:
        rendered = _render_alliance_leader(answer)
    elif (
        answer.get("intent") == "top_contributors"
        and answer.get("metrics", {}).get("mode") == "leader"
    ):
        rendered = _render_player_leader(answer)
    else:
        return legacy.render_dashboard_answer(answer)
    if _show_notice(answer):
        rendered += f"\n\n---\n\n{legacy.ROUNDED_SCORE_NOTICE}"
    return rendered


def answer_dashboard_question(*args, **kwargs):
    from ._calculation import calculate_dashboard_answer

    return render_dashboard_answer(calculate_dashboard_answer(*args, **kwargs))
