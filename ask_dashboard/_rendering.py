"""Direct, subject-aware rendering for Ask Dashboard answers."""

from __future__ import annotations

import re

from ._legacy import legacy
from ._routing import (
    ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
    SCORE_DERIVED_INTENTS,
    is_obvious_smalltalk_question,
)

_METRIC_DEFINITIONS = (
    (
        ("net score",),
        "**Net score** = **score gained − score lost**. A positive net score means the player or alliance gained more points than it lost; a negative value means losses were greater than gains. Ask Dashboard uses net score as its default measure of overall recorded result.",
    ),
    (
        ("score gained",),
        "**Score gained** is the total number of SVS points recorded as earned. It measures activity that added points, but it does not subtract score lost, so it is not the same as net score.",
    ),
    (
        ("score lost",),
        "**Score lost** is the total magnitude of SVS points recorded as lost. Ask Dashboard displays it as a positive loss amount and subtracts it from score gained when calculating net score.",
    ),
    (
        ("positive contribution",),
        "**Positive contribution** is the sum of **positive player net scores** in the selected scope. It counts only players whose net score is above zero; it is not simply the total score gained.",
    ),
    (
        ("negative impact", "negative contribution"),
        "**Negative impact** is the absolute total of **negative player net scores** in the selected scope. It shows how much the negative side reduced the result while keeping the displayed amount easy to compare as a positive magnitude.",
    ),
    (
        ("negative share", "negative percentage", "negative percent", "negative ratio"),
        "**Negative share** = **negative impact ÷ (positive contribution + negative impact) × 100**. It describes the negative side’s share of the total net-score magnitude, not the percentage of players who finished negative.",
    ),
)


def _metric_definition(answer):
    question = answer.get("parameters", {}).get("question", "")
    text = legacy.normalize_question_text(question)
    for aliases, definition in _METRIC_DEFINITIONS:
        if any(alias in text for alias in aliases):
            return definition
    return None


def _unsupported_message(answer):
    question = answer.get("parameters", {}).get("question", "")
    text = legacy.normalize_question_text(question)
    if is_obvious_smalltalk_question(question):
        return (
            "Hello! Ask Dashboard is ready to help with the recorded SVS data. "
            "Try asking about a player or alliance score, ranking, contribution, exclusion, or metric definition."
        )
    if re.search(r"\b(?:predict|prediction|future|next svs|will win|winner next)\b", text):
        return (
            "Ask Dashboard analyzes recorded SVS scores, so it cannot predict a future winner or the next SVS result. "
            "It can summarize current rankings, contributions, losses, exclusions, and net-score leaders from the available data."
        )
    return (
        "I could not match that question to one of the dashboard’s supported analyses. "
        "Ask about recorded player or alliance scores, rankings, exclusions, positive contribution, negative impact, or metric definitions.\n\n"
        "**Examples:**\n"
        "- What is net score?\n"
        "- Which player has the strongest overall balance?\n"
        "- What is the total net score without TDA?\n"
        "- Who contributed most in SnS?\n"
        "- Why did the negative share rise?"
    )


def _status_message(answer):
    code = answer.get("guidance_code") or answer.get("error_code")
    if code == "no_positive_contribution":
        if answer.get("parameters", {}).get("scope") == "server":
            return "No positive player net score is available for the full server in this SVS period."
        return "No positive player net score is available under the current sidebar filters."
    if code == "unsupported_question":
        return _unsupported_message(answer)
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
    if answer.get("intent") == "dashboard_help":
        metric_definition = _metric_definition(answer)
        if metric_definition:
            return metric_definition
    if answer.get("intent") == "unsupported_question":
        return _status_message(answer) or ""
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
