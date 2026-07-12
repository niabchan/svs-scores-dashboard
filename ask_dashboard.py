import re
import unicodedata

import pandas as pd

# Ask the Dashboard
QUESTION_NET_VS_POSITIVE = (
    "Why does the top net-score alliance rank second in positive contribution?"
)
QUESTION_EXCLUSION_IMPACT = (
    "What changed after excluding the selected players?"
)
QUESTION_NEGATIVE_PERCENTAGE = (
    "Why did the negative percentage increase?"
)
QUESTION_TOP_CONTRIBUTORS = (
    "Which players contributed most to the selected alliance?"
)
QUESTION_CUSTOM = "Write my own question"

SUGGESTED_QUESTIONS = [
    QUESTION_NET_VS_POSITIVE,
    QUESTION_EXCLUSION_IMPACT,
    QUESTION_NEGATIVE_PERCENTAGE,
    QUESTION_TOP_CONTRIBUTORS,
    QUESTION_CUSTOM,
]


def format_score(value):
    """Format dashboard scores consistently for narrative answers."""
    return f"{value:,.0f}"


def format_signed_score(value):
    """Format a score change with an explicit plus or minus sign."""
    if value > 0:
        return f"+{value:,.0f}"
    return f"{value:,.0f}"


def normalize_question_text(question):
    """Normalize free-text questions for simple rule-based routing."""
    normalized = unicodedata.normalize("NFKC", str(question)).casefold()
    normalized = re.sub(r"[^\w\s%+-]", " ", normalized)
    return " ".join(normalized.split())


def extract_alliance_names_from_question(question, alliance_names):
    """Find alliance names mentioned in a question, case-insensitively."""
    question_text = unicodedata.normalize(
        "NFKC",
        str(question),
    ).casefold()

    matches = []
    for alliance in sorted(
        {str(name) for name in alliance_names if pd.notna(name)},
        key=len,
        reverse=True,
    ):
        alliance_text = unicodedata.normalize(
            "NFKC",
            alliance,
        ).casefold()

        # Boundaries prevent short alliance names from matching inside words.
        pattern = rf"(?<!\w){re.escape(alliance_text)}(?!\w)"
        if re.search(pattern, question_text):
            matches.append(alliance)

    return matches


def explain_total_net_excluding_alliances(
    data,
    excluded_alliances,
    svs_period=None,
):
    """Calculate total net score before and after excluding alliances."""
    required_columns = {
        "alliance",
        "player_name",
        "score_gained",
        "score_lost",
        "net_score",
    }
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return (
            "This calculation cannot be completed because the current data "
            f"is missing: {missing_text}."
        )

    if not excluded_alliances:
        return (
            "I understood that you want to exclude an alliance, but I could "
            "not identify its name. Include an alliance name in the question, "
            "for example: **What is the total net score without TDA?**"
        )

    working_df = data[
        [
            "alliance",
            "player_name",
            "score_gained",
            "score_lost",
            "net_score",
        ]
    ].copy()

    for column in ["score_gained", "score_lost", "net_score"]:
        working_df[column] = pd.to_numeric(
            working_df[column],
            errors="coerce",
        )

    working_df = working_df.dropna(subset=["alliance", "net_score"])

    if working_df.empty:
        return (
            "There is no score data in the current filter scope. Select at "
            "least one alliance and net-status option, then try again."
        )

    requested_lookup = {
        str(name).casefold(): str(name)
        for name in excluded_alliances
    }
    in_scope_lookup = {
        str(name).casefold(): str(name)
        for name in working_df["alliance"].dropna().unique()
    }

    recognized_in_scope = [
        in_scope_lookup[key]
        for key in requested_lookup
        if key in in_scope_lookup
    ]
    outside_scope = [
        requested_lookup[key]
        for key in requested_lookup
        if key not in in_scope_lookup
    ]

    before_net = working_df["net_score"].sum()
    before_players = working_df["player_name"].nunique()

    if not recognized_in_scope:
        outside_text = ", ".join(f"**{name}**" for name in outside_scope)
        return (
            f"{outside_text} is not included in the current alliance filter, "
            f"so excluding it does not change the current total net score of "
            f"**{format_signed_score(before_net)}**. Add the alliance to the "
            "sidebar selection first if you want a before-and-after comparison."
        )

    excluded_mask = working_df["alliance"].astype(str).str.casefold().isin(
        {name.casefold() for name in recognized_in_scope}
    )
    excluded_df = working_df[excluded_mask].copy()
    remaining_df = working_df[~excluded_mask].copy()

    excluded_net = excluded_df["net_score"].sum()
    excluded_gained = excluded_df["score_gained"].sum()
    excluded_lost = excluded_df["score_lost"].sum()
    after_net = remaining_df["net_score"].sum()
    net_change = after_net - before_net
    after_players = remaining_df["player_name"].nunique()

    alliance_text = ", ".join(
        f"**{name}**" for name in recognized_in_scope
    )
    period_text = f" for **{svs_period}**" if svs_period else ""

    if excluded_net < 0:
        interpretation = (
            "The total improves because the excluded alliance group had a "
            "negative net contribution in this scope."
        )
    elif excluded_net > 0:
        interpretation = (
            "The total decreases because the excluded alliance group had a "
            "positive net contribution in this scope."
        )
    else:
        interpretation = (
            "The total does not change because the excluded alliance group "
            "had a net contribution of zero in this scope."
        )

    outside_note = ""
    if outside_scope:
        outside_note = (
            "\n\nThe following named alliance(s) were already outside the "
            "current filter and therefore had no additional effect: "
            + ", ".join(f"**{name}**" for name in outside_scope)
            + "."
        )

    return (
        f"Within the current dashboard filters{period_text}, excluding "
        f"{alliance_text} changes total net score from "
        f"**{format_signed_score(before_net)}** to "
        f"**{format_signed_score(after_net)}** "
        f"(**{format_signed_score(net_change)}**).\n\n"
        f"The excluded alliance group contributed:\n"
        f"- Score gained: **{format_score(excluded_gained)}**\n"
        f"- Score lost: **{format_score(excluded_lost)}**\n"
        f"- Net score: **{format_signed_score(excluded_net)}**\n\n"
        f"Players remaining: **{after_players}/{before_players}**. "
        f"{interpretation}{outside_note}"
    )

def explain_net_vs_positive_ranking(data, svs_period=None):
    """
    Explain why the alliance with the highest total net score may rank lower
    in positive contribution.

    Positive contribution = sum of positive player net scores.
    Negative impact = absolute sum of negative player net scores.
    Total net score = positive contribution - negative impact.
    """
    required_columns = {"alliance", "net_score"}
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return (
            "This explanation cannot be calculated because the current data "
            f"is missing: {missing_text}."
        )

    working_df = data[["alliance", "net_score"]].copy()
    working_df["net_score"] = pd.to_numeric(
        working_df["net_score"],
        errors="coerce"
    )
    working_df = working_df.dropna(subset=["alliance", "net_score"])

    if working_df.empty:
        return (
            "There is no score data in the current filter scope. "
            "Select at least one alliance and net status, then try again."
        )

    alliance_count = working_df["alliance"].nunique()
    if alliance_count < 2:
        return (
            "This comparison needs at least two alliances in the current "
            "filter scope. Select more alliances and try again."
        )

    # This question depends on both the positive and negative sides.
    if "net_status" in data.columns:
        status_values = {
            str(value).strip().lower()
            for value in data["net_status"].dropna().unique()
        }
        if not {"positive", "negative"}.issubset(status_values):
            return (
                "This question is intended to compare positive contribution "
                "with negative impact, but the current Net Status filter does "
                "not include both Positive and Negative. Select both statuses "
                "to get the full explanation."
            )

    alliance_analysis = (
        working_df
        .groupby("alliance", as_index=False)
        .agg(
            total_net_score=("net_score", "sum"),
            positive_net_score=(
                "net_score",
                lambda scores: scores[scores > 0].sum()
            ),
            negative_impact=(
                "net_score",
                lambda scores: scores[scores < 0].abs().sum()
            ),
        )
    )

    alliance_analysis["net_rank"] = (
        alliance_analysis["total_net_score"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    alliance_analysis["positive_rank"] = (
        alliance_analysis["positive_net_score"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    top_net_rows = alliance_analysis[
        alliance_analysis["net_rank"] == 1
    ].copy()

    if len(top_net_rows) > 1:
        tied_alliances = ", ".join(
            sorted(top_net_rows["alliance"].astype(str))
        )
        tied_score = top_net_rows["total_net_score"].iloc[0]
        return (
            "The current filters produce a tie for first place in total net "
            f"score: {tied_alliances}, each with {format_score(tied_score)}. "
            "Because there is no single top net-score alliance, the premise "
            "of this question does not currently apply."
        )

    top_net = top_net_rows.iloc[0]
    top_name = str(top_net["alliance"])
    positive_rank = int(top_net["positive_rank"])

    positive_leaders = alliance_analysis[
        alliance_analysis["positive_rank"] == 1
    ].copy()

    # If the net leader is also a positive-contribution leader, explain that
    # the suggested question does not match the current filtered data.
    if positive_rank == 1:
        period_text = f" for {svs_period}" if svs_period else ""
        return (
            f"The premise does not match the current filtered data{period_text}. "
            f"**{top_name}** ranks first in both total net score "
            f"({format_score(top_net['total_net_score'])}) and positive "
            f"contribution ({format_score(top_net['positive_net_score'])})."
        )

    # Compare the net leader with one of the alliances leading positive
    # contribution. Sorting by total net score makes the comparison stable
    # if more than one alliance is tied for the positive lead.
    positive_leader = (
        positive_leaders
        .sort_values("total_net_score", ascending=False)
        .iloc[0]
    )
    positive_leader_name = str(positive_leader["alliance"])

    positive_gap = (
        positive_leader["positive_net_score"]
        - top_net["positive_net_score"]
    )
    negative_advantage = (
        positive_leader["negative_impact"]
        - top_net["negative_impact"]
    )
    net_lead = (
        top_net["total_net_score"]
        - positive_leader["total_net_score"]
    )

    period_text = f" in {svs_period}" if svs_period else ""
    rank_statement = (
        "second"
        if positive_rank == 2
        else f"#{positive_rank}, not second"
    )

    explanation = (
        f"Under the current sidebar filters{period_text}, **{top_name}** "
        f"ranks first in total net score with "
        f"**{format_score(top_net['total_net_score'])}**, while it ranks "
        f"{rank_statement} in positive contribution with "
        f"**{format_score(top_net['positive_net_score'])}**.\n\n"
        f"**{positive_leader_name}** leads positive contribution with "
        f"**{format_score(positive_leader['positive_net_score'])}**, which is "
        f"**{format_score(positive_gap)}** more than {top_name}. However, "
        f"{positive_leader_name}'s negative impact is "
        f"**{format_score(positive_leader['negative_impact'])}**, compared "
        f"with **{format_score(top_net['negative_impact'])}** for {top_name}. "
        f"That gives {top_name} a **{format_score(negative_advantage)}** "
        f"advantage from losing fewer points.\n\n"
        f"The lower negative impact offsets the smaller positive contribution, "
        f"leaving {top_name} ahead of {positive_leader_name} by "
        f"**{format_score(net_lead)}** in total net score. Here, positive "
        f"contribution is the sum of positive player net scores, and total "
        f"net score equals positive contribution minus negative impact."
    )

    return explanation


def explain_exclusion_impact(
    data,
    selected_player_names=None,
    svs_period=None,
):
    """Explain the before/after effect of the current player exclusions."""
    required_columns = {
        "player_name",
        "score_gained",
        "score_lost",
        "net_score",
    }
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return (
            "This explanation cannot be calculated because the current data "
            f"is missing: {missing_text}."
        )

    working_df = data[
        ["player_name", "score_gained", "score_lost", "net_score"]
    ].copy()

    for column in ["score_gained", "score_lost", "net_score"]:
        working_df[column] = pd.to_numeric(
            working_df[column],
            errors="coerce",
        )

    working_df = working_df.dropna(
        subset=["player_name", "net_score"]
    )

    if working_df.empty:
        return (
            "There is no player score data in the current filter scope. "
            "Select at least one alliance and net status, then try again."
        )

    all_player_names = sorted(
        working_df["player_name"].dropna().unique().tolist()
    )

    if selected_player_names is None:
        selected_player_names = all_player_names

    valid_players = set(all_player_names)
    selected_player_names = [
        player for player in selected_player_names
        if player in valid_players
    ]

    selected_df = working_df[
        working_df["player_name"].isin(selected_player_names)
    ].copy()
    excluded_df = working_df[
        ~working_df["player_name"].isin(selected_player_names)
    ].copy()

    before_player_count = working_df["player_name"].nunique()
    after_player_count = selected_df["player_name"].nunique()
    excluded_player_names = sorted(
        excluded_df["player_name"].dropna().unique().tolist()
    )
    excluded_player_count = len(excluded_player_names)

    period_text = f" in {svs_period}" if svs_period else ""

    if excluded_player_count == 0:
        before_net = working_df["net_score"].sum()
        return (
            f"No players are currently excluded from the filtered group"
            f"{period_text}. The before-and-after results are therefore "
            f"identical: **{before_player_count} players** with a total net "
            f"score of **{format_score(before_net)}**. Remove at least one "
            "player in the Player Selection Insight tab to compare the "
            "impact."
        )

    def calculate_metrics(frame):
        positive_contribution = frame.loc[
            frame["net_score"] > 0,
            "net_score",
        ].sum()
        negative_impact = frame.loc[
            frame["net_score"] < 0,
            "net_score",
        ].abs().sum()

        return {
            "score_gained": frame["score_gained"].sum(),
            "score_lost": frame["score_lost"].sum(),
            "net_score": frame["net_score"].sum(),
            "positive_contribution": positive_contribution,
            "negative_impact": negative_impact,
        }

    before = calculate_metrics(working_df)
    after = calculate_metrics(selected_df)

    changes = {
        key: after[key] - before[key]
        for key in before
    }

    positive_removed = (
        before["positive_contribution"]
        - after["positive_contribution"]
    )
    negative_removed = (
        before["negative_impact"]
        - after["negative_impact"]
    )
    net_change = changes["net_score"]

    if net_change > 0:
        outcome = (
            f"The total net score **improved by "
            f"{format_score(net_change)}**. The exclusions removed "
            f"**{format_score(negative_removed)}** of negative impact but "
            f"only **{format_score(positive_removed)}** of positive "
            "contribution, so the reduction in losses was greater than the "
            "reduction in gains."
        )
    elif net_change < 0:
        outcome = (
            f"The total net score **decreased by "
            f"{format_score(abs(net_change))}**. The exclusions removed "
            f"**{format_score(positive_removed)}** of positive contribution "
            f"but only **{format_score(negative_removed)}** of negative "
            "impact, so more useful contribution was removed than harmful "
            "impact."
        )
    else:
        outcome = (
            "The total net score did not change. The removed positive "
            f"contribution (**{format_score(positive_removed)}**) and removed "
            f"negative impact (**{format_score(negative_removed)}**) offset "
            "each other exactly."
        )

    if excluded_player_count <= 5:
        excluded_text = ", ".join(
            map(str, excluded_player_names)
        )
    else:
        preview = ", ".join(
            map(str, excluded_player_names[:5])
        )
        excluded_text = (
            f"{preview}, and {excluded_player_count - 5} others"
        )

    return (
        f"After the current exclusions{period_text}, the analysis includes "
        f"**{after_player_count} of {before_player_count} players**. "
        f"**Excluded:** {excluded_text}.\n\n"
        f"- **Score gained:** {format_score(before['score_gained'])} → "
        f"{format_score(after['score_gained'])} "
        f"({format_signed_score(changes['score_gained'])})\n"
        f"- **Score lost:** {format_score(before['score_lost'])} → "
        f"{format_score(after['score_lost'])} "
        f"({format_signed_score(changes['score_lost'])})\n"
        f"- **Positive contribution:** "
        f"{format_score(before['positive_contribution'])} → "
        f"{format_score(after['positive_contribution'])} "
        f"({format_signed_score(changes['positive_contribution'])})\n"
        f"- **Negative impact:** "
        f"{format_score(before['negative_impact'])} → "
        f"{format_score(after['negative_impact'])} "
        f"({format_signed_score(changes['negative_impact'])})\n"
        f"- **Total net score:** {format_score(before['net_score'])} → "
        f"{format_score(after['net_score'])} "
        f"({format_signed_score(net_change)})\n\n"
        f"{outcome}"
    )


def explain_negative_percentage_change(
    data,
    selected_player_names=None,
    svs_period=None,
):
    """Explain how player exclusions changed the negative-score share."""
    required_columns = {"player_name", "net_score"}
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return (
            "This explanation cannot be calculated because the current data "
            f"is missing: {missing_text}."
        )

    working_columns = ["player_name", "net_score"]
    if "net_status" in data.columns:
        working_columns.append("net_status")

    working_df = data[working_columns].copy()
    working_df["net_score"] = pd.to_numeric(
        working_df["net_score"],
        errors="coerce",
    )
    working_df = working_df.dropna(
        subset=["player_name", "net_score"]
    )

    if working_df.empty:
        return (
            "There is no player score data in the current filter scope. "
            "Select at least one alliance and net status, then try again."
        )

    # A positive-versus-negative percentage is only meaningful when both
    # sides are included in the current scope.
    if "net_status" in working_df.columns:
        status_values = {
            str(value).strip().lower()
            for value in working_df["net_status"].dropna().unique()
        }
        if not {"positive", "negative"}.issubset(status_values):
            return (
                "This question compares the positive and negative sides, but "
                "the current Net Status filter does not include both Positive "
                "and Negative. Select both statuses and try again."
            )

    all_player_names = sorted(
        working_df["player_name"].dropna().unique().tolist()
    )

    if selected_player_names is None:
        selected_player_names = all_player_names

    valid_players = set(all_player_names)
    selected_player_names = [
        player for player in selected_player_names
        if player in valid_players
    ]

    selected_df = working_df[
        working_df["player_name"].isin(selected_player_names)
    ].copy()
    excluded_df = working_df[
        ~working_df["player_name"].isin(selected_player_names)
    ].copy()

    excluded_player_names = sorted(
        excluded_df["player_name"].dropna().unique().tolist()
    )
    excluded_player_count = len(excluded_player_names)
    period_text = f" in {svs_period}" if svs_period else ""

    def calculate_balance(frame):
        positive = frame.loc[
            frame["net_score"] > 0,
            "net_score",
        ].sum()
        negative = frame.loc[
            frame["net_score"] < 0,
            "net_score",
        ].abs().sum()
        total_magnitude = positive + negative
        negative_share = (
            negative / total_magnitude * 100
            if total_magnitude > 0
            else None
        )
        return {
            "positive": positive,
            "negative": negative,
            "total_magnitude": total_magnitude,
            "negative_share": negative_share,
        }

    before = calculate_balance(working_df)
    after = calculate_balance(selected_df)

    if before["negative_share"] is None:
        return (
            "The negative percentage cannot be calculated because the "
            "current filtered group has no positive or negative net-score "
            "magnitude."
        )

    if excluded_player_count == 0:
        return (
            f"No players are currently excluded from the filtered group"
            f"{period_text}. The negative share is unchanged at "
            f"**{before['negative_share']:.1f}%**. Remove at least one "
            "player in the Player Selection Insight tab to create a "
            "before-and-after comparison."
        )

    if after["negative_share"] is None:
        return (
            f"After the current exclusions{period_text}, no score magnitude "
            "remains in the selected group, so an after-exclusion negative "
            "percentage cannot be calculated."
        )

    share_change = (
        after["negative_share"] - before["negative_share"]
    )
    positive_removed = before["positive"] - after["positive"]
    negative_removed = before["negative"] - after["negative"]

    positive_reduction_rate = (
        positive_removed / before["positive"] * 100
        if before["positive"] > 0
        else 0
    )
    negative_reduction_rate = (
        negative_removed / before["negative"] * 100
        if before["negative"] > 0
        else 0
    )

    if excluded_player_count <= 5:
        excluded_text = ", ".join(map(str, excluded_player_names))
    else:
        preview = ", ".join(map(str, excluded_player_names[:5]))
        excluded_text = (
            f"{preview}, and {excluded_player_count - 5} others"
        )

    formula_text = (
        "Negative percentage = negative impact ÷ "
        "(positive contribution + negative impact)."
    )

    if share_change > 0.05:
        direction_text = (
            f"The negative share **increased by {share_change:.1f} "
            "percentage points**, from "
            f"**{before['negative_share']:.1f}%** to "
            f"**{after['negative_share']:.1f}%**."
        )

        if positive_reduction_rate > negative_reduction_rate:
            if negative_removed > 0:
                raw_negative_note = (
                    "Although the raw negative impact also decreased, it "
                    "became a larger share of the smaller remaining total."
                )
            else:
                raw_negative_note = (
                    "The raw negative impact did not increase; it stayed the "
                    "same but became a larger share of the smaller remaining "
                    "total."
                )

            reason_text = (
                "This happened because the exclusions removed a larger "
                "proportion of positive contribution than negative impact. "
                f"Positive contribution fell by "
                f"**{positive_reduction_rate:.1f}%**, while negative impact "
                f"fell by **{negative_reduction_rate:.1f}%**. "
                f"{raw_negative_note}"
            )
        else:
            reason_text = (
                "The remaining score mix became more negative. The raw "
                "values and their relative changes are shown below; the "
                "percentage rose because negative impact occupies a larger "
                "part of the remaining positive-plus-negative total."
            )

    elif share_change < -0.05:
        direction_text = (
            "The premise does not match the current selection: the negative "
            f"share **decreased by {abs(share_change):.1f} percentage "
            f"points**, from **{before['negative_share']:.1f}%** to "
            f"**{after['negative_share']:.1f}%**."
        )
        reason_text = (
            "The exclusions removed a larger proportion of negative impact "
            "than positive contribution. "
            f"Negative impact fell by **{negative_reduction_rate:.1f}%**, "
            f"while positive contribution fell by "
            f"**{positive_reduction_rate:.1f}%**."
        )

    else:
        direction_text = (
            "The negative share is effectively unchanged at "
            f"**{after['negative_share']:.1f}%** "
            f"({share_change:+.1f} percentage points)."
        )
        reason_text = (
            "Positive contribution and negative impact changed in nearly "
            "the same proportion, so the balance between the two sides "
            "remained stable."
        )

    return (
        f"After excluding **{excluded_player_count} player(s)**"
        f"{period_text} — **{excluded_text}** — {direction_text}\n\n"
        f"- **Positive contribution:** "
        f"{format_score(before['positive'])} → "
        f"{format_score(after['positive'])} "
        f"(removed {format_score(positive_removed)}, "
        f"{positive_reduction_rate:.1f}%)\n"
        f"- **Negative impact:** "
        f"{format_score(before['negative'])} → "
        f"{format_score(after['negative'])} "
        f"(removed {format_score(negative_removed)}, "
        f"{negative_reduction_rate:.1f}%)\n\n"
        f"{reason_text}\n\n"
        f"{formula_text}"
    )


def explain_top_contributors(
    data,
    svs_period=None,
    alliance_names=None,
):
    """
    Rank the strongest player contributors within each alliance currently
    included by the dashboard filters.

    The ranking uses player net score. For players with positive net scores,
    contribution share is measured against the alliance's total positive net
    score in the current filter scope.
    """
    required_columns = {
        "alliance",
        "player_name",
        "score_gained",
        "score_lost",
        "net_score",
    }
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return (
            "This explanation cannot be calculated because the current data "
            f"is missing: {missing_text}."
        )

    working_df = data[
        [
            "alliance",
            "player_name",
            "score_gained",
            "score_lost",
            "net_score",
        ]
    ].copy()

    for column in ["score_gained", "score_lost", "net_score"]:
        working_df[column] = pd.to_numeric(
            working_df[column],
            errors="coerce",
        )

    working_df = working_df.dropna(
        subset=["alliance", "player_name", "net_score"]
    )

    if alliance_names:
        requested = {str(name).casefold() for name in alliance_names}
        available_lookup = {
            str(name).casefold(): str(name)
            for name in working_df["alliance"].dropna().unique()
        }
        matched = [
            available_lookup[name]
            for name in requested
            if name in available_lookup
        ]

        if not matched:
            named_text = ", ".join(
                f"**{name}**" for name in alliance_names
            )
            return (
                f"I recognized {named_text}, but it is not included in the "
                "current alliance filter. Add it in the sidebar, then ask "
                "again."
            )

        working_df = working_df[
            working_df["alliance"].astype(str).str.casefold().isin(
                {name.casefold() for name in matched}
            )
        ].copy()

    if working_df.empty:
        return (
            "There is no player score data in the current filter scope. "
            "Select at least one alliance and a net-status option, then try "
            "again."
        )

    # Grouping keeps the answer correct even if a player appears in more than
    # one row within the selected scope.
    player_summary = (
        working_df
        .groupby(["alliance", "player_name"], as_index=False)
        .agg(
            score_gained=("score_gained", "sum"),
            score_lost=("score_lost", "sum"),
            net_score=("net_score", "sum"),
        )
    )

    alliances = sorted(
        player_summary["alliance"].dropna().astype(str).unique().tolist()
    )

    if not alliances:
        return (
            "No alliance is available in the current filter scope. Select "
            "at least one alliance and try again."
        )

    period_text = f" for **{svs_period}**" if svs_period else ""
    single_alliance = len(alliances) == 1
    top_n = 5 if single_alliance else 3
    sections = []

    for alliance in alliances:
        alliance_players = player_summary[
            player_summary["alliance"].astype(str) == alliance
        ].copy()

        alliance_players = alliance_players.sort_values(
            ["net_score", "score_gained", "player_name"],
            ascending=[False, False, True],
        )

        positive_players = alliance_players[
            alliance_players["net_score"] > 0
        ].copy()
        alliance_positive_total = positive_players["net_score"].sum()
        alliance_net_total = alliance_players["net_score"].sum()

        if not positive_players.empty:
            ranked_players = positive_players.head(top_n).copy()
            ranking_description = "positive contributors by net score"
        else:
            ranked_players = alliance_players.head(top_n).copy()
            ranking_description = (
                "players with the highest net scores; no player has a "
                "positive net score in this scope"
            )

        lines = [
            f"**{alliance}** — {ranking_description}:"
        ]

        for rank, row in enumerate(
            ranked_players.itertuples(index=False),
            start=1,
        ):
            score_details = (
                f"net **{format_signed_score(row.net_score)}** "
                f"(gained {format_score(row.score_gained)}, "
                f"lost {format_score(row.score_lost)})"
            )

            if row.net_score > 0 and alliance_positive_total > 0:
                share = row.net_score / alliance_positive_total * 100
                score_details += (
                    f", **{share:.1f}%** of the alliance's positive "
                    "contribution"
                )

            lines.append(
                f"{rank}. **{row.player_name}** — {score_details}"
            )

        if not positive_players.empty:
            ranked_positive_total = ranked_players["net_score"].sum()
            ranked_share = (
                ranked_positive_total / alliance_positive_total * 100
                if alliance_positive_total > 0
                else 0
            )
            lines.append(
                f"The listed player(s) account for **{ranked_share:.1f}%** "
                "of this alliance's positive contribution in the current "
                "filter scope."
            )

        lines.append(
            f"Alliance total net score in this scope: "
            f"**{format_signed_score(alliance_net_total)}**."
        )
        sections.append("\n".join(lines))

    if single_alliance:
        introduction = (
            f"The strongest contributors{period_text} are ranked by "
            "**player net score**."
        )
    else:
        introduction = (
            f"Because **{len(alliances)} alliances** are selected"
            f"{period_text}, the dashboard shows the top **{top_n}** "
            "contributors within each alliance. Players are ranked by "
            "**player net score**."
        )

    return introduction + "\n\n" + "\n\n".join(sections)


def _calculate_dashboard_answer_markdown(
    question,
    data,
    svs_period=None,
    selected_player_names=None,
    known_alliance_names=None,
):
    """Route suggested and free-text questions to supported analyses."""
    normalized_question = normalize_question_text(question)

    if known_alliance_names is None:
        known_alliance_names = (
            data["alliance"].dropna().unique().tolist()
            if "alliance" in data.columns
            else []
        )

    mentioned_alliances = extract_alliance_names_from_question(
        question,
        known_alliance_names,
    )

    # Exact suggested questions remain deterministic.
    if question == QUESTION_NET_VS_POSITIVE:
        return explain_net_vs_positive_ranking(data, svs_period)

    if question == QUESTION_EXCLUSION_IMPACT:
        return explain_exclusion_impact(
            data,
            selected_player_names,
            svs_period,
        )

    if question == QUESTION_NEGATIVE_PERCENTAGE:
        return explain_negative_percentage_change(
            data,
            selected_player_names,
            svs_period,
        )

    if question == QUESTION_TOP_CONTRIBUTORS:
        return explain_top_contributors(data, svs_period)

    exclusion_terms = {
        "exclude",
        "excluded",
        "excluding",
        "without",
        "remove",
        "removed",
        "removing",
        "except",
    }
    has_exclusion_term = any(
        term in normalized_question.split()
        for term in exclusion_terms
    )

    # A named-alliance exclusion is checked before the generic player-
    # exclusion route so "What changed after excluding TDA?" is interpreted
    # as an alliance calculation, not the Player Selection widget.
    if has_exclusion_term and mentioned_alliances and (
        "alliance" in normalized_question
        or "net" in normalized_question
        or "score" in normalized_question
        or "total" in normalized_question
        or "change" in normalized_question
    ):
        return explain_total_net_excluding_alliances(
            data,
            mentioned_alliances,
            svs_period,
        )

    if has_exclusion_term and (
        "net score" in normalized_question
        or "total net" in normalized_question
    ) and not mentioned_alliances:
        available_text = ", ".join(
            map(str, known_alliance_names)
        )
        return (
            "I understood that you want a total net score after excluding "
            "an alliance, but I could not identify the alliance name. "
            f"Available alliance names for this SVS period are: "
            f"**{available_text}**."
        )

    # Natural-language paraphrases of the existing analyses.
    # Compare the net-score leader with positive-contribution ranking.
    # Users do not have to include the word "alliance" explicitly; phrases
    # such as "net-score leader" or "top net score" imply it.
    ranking_subject_terms = [
        "alliance",
        "leader",
        "top net",
        "highest net",
        "first in net",
        "net score winner",
    ]
    ranking_comparison_terms = [
        "positive contribution",
        "positive rank",
        "positive ranking",
        "first in positive",
        "top in positive",
    ]

    if (
        "net" in normalized_question
        and any(
            term in normalized_question
            for term in ranking_subject_terms
        )
        and (
            any(
                term in normalized_question
                for term in ranking_comparison_terms
            )
            or (
                "positive" in normalized_question
                and any(
                    term in normalized_question
                    for term in ["rank", "ranking", "first", "top"]
                )
            )
        )
    ):
        return explain_net_vs_positive_ranking(data, svs_period)

    if (
        has_exclusion_term
        and (
            "player" in normalized_question
            or "selected" in normalized_question
        )
        and (
            "change" in normalized_question
            or "impact" in normalized_question
            or "happen" in normalized_question
            or "result" in normalized_question
        )
    ):
        return explain_exclusion_impact(
            data,
            selected_player_names,
            svs_period,
        )

    if (
        "negative" in normalized_question
        and any(
            term in normalized_question
            for term in ["percentage", "percent", "share", "ratio"]
        )
        and any(
            term in normalized_question
            for term in ["increase", "increased", "rise", "rose", "change"]
        )
    ):
        return explain_negative_percentage_change(
            data,
            selected_player_names,
            svs_period,
        )

    if (
        any(term in normalized_question for term in ["player", "who"])
        and any(
            term in normalized_question
            for term in [
                "contribut",
                "top",
                "best",
                "highest net",
                "most",
            ]
        )
        and (
            "alliance" in normalized_question
            or mentioned_alliances
        )
    ):
        return explain_top_contributors(
            data,
            svs_period,
            alliance_names=mentioned_alliances or None,
        )

    return (
        "I could not map that question to a supported dashboard analysis yet. "
        "This version uses rule-based matching rather than an AI API. Try one "
        "of these forms:\n\n"
        "- **What is the total net score without TDA?**\n"
        "- **Who contributed most in SnS?**\n"
        "- **How did excluding selected players change the result?**\n"
        "- **Why did the negative share rise?**\n"
        "- **Why is the net-score leader not first in positive contribution?**"
    )

def _as_structured(kind, markdown):
    return {"kind": kind, "markdown": markdown}


def calculate_dashboard_answer(*args, **kwargs):
    """Route a question and return a structured Ask Dashboard answer."""
    markdown = _calculate_dashboard_answer_markdown(*args, **kwargs)
    return _as_structured("dashboard_answer", markdown)


def render_dashboard_answer(answer):
    """Render a structured Ask Dashboard answer as Markdown."""
    if isinstance(answer, dict):
        return answer.get("markdown", "")
    return str(answer)


def answer_dashboard_question(*args, **kwargs):
    """Return the rendered Markdown answer for backward-compatible callers."""
    return render_dashboard_answer(calculate_dashboard_answer(*args, **kwargs))
