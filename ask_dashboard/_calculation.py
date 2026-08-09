"""Contribution-leader calculations and execution integration."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from ._legacy import REPOSITORY_ROOT, legacy
from ._routing import (
    ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
    is_obvious_smalltalk_question,
    route_dashboard_question,
    validate_intent_contract,
)


def _contribution_frame(data):
    required = {"alliance", "player_name", "score_gained", "score_lost", "net_score"}
    missing = required.difference(data.columns)
    if missing:
        return None, missing
    frame = legacy._numeric_scope(
        data,
        ["alliance", "player_name", "score_gained", "score_lost", "net_score"],
    )
    return frame.dropna(subset=["alliance", "player_name", "net_score"]), set()


def calculate_player_positive_contribution_leader(
    data,
    svs_period=None,
    alliance_names=None,
    *,
    scope="current_filters",
):
    intent = "top_contributors"
    params = {
        "alliance_names": [str(name) for name in (alliance_names or [])],
        "mode": "leader",
    }
    if scope == "server":
        params["scope"] = "server"

    frame, missing = _contribution_frame(data)
    if missing:
        return legacy._missing_columns_result(intent, missing, svs_period, params)
    if alliance_names:
        frame, matched, outside = legacy._filter_by_alliance_names(frame, alliance_names)
        params.update(
            {"matched_alliances": matched, "outside_scope_alliances": outside}
        )
        if outside:
            return legacy._base_result(
                intent,
                "guidance",
                svs_period,
                "alliance_outside_scope",
                parameters=params,
            )
    if frame.empty:
        return legacy._base_result(
            intent,
            "guidance",
            svs_period,
            "empty_player_scope",
            parameters=params,
        )

    summary = frame.groupby(["alliance", "player_name"], as_index=False).agg(
        score_gained=("score_gained", "sum"),
        score_lost=("score_lost", "sum"),
        positive_contribution=("net_score", "sum"),
    )
    summary = summary[summary["positive_contribution"] > 0].copy()
    if summary.empty:
        return legacy._base_result(
            intent,
            "guidance",
            svs_period,
            "no_positive_contribution",
            parameters=params,
        )

    total_positive = summary["positive_contribution"].sum()
    alliance_totals = summary.groupby("alliance")["positive_contribution"].sum()
    summary["share_of_scope_positive"] = (
        summary["positive_contribution"] / total_positive * 100
    )
    summary["share_of_alliance_positive"] = summary.apply(
        lambda row: row["positive_contribution"]
        / alliance_totals.loc[row["alliance"]]
        * 100,
        axis=1,
    )
    summary = summary.sort_values(
        ["positive_contribution", "score_gained", "player_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    summary["rank"] = summary["positive_contribution"].rank(
        method="min", ascending=False
    ).astype(int)
    records = summary.to_dict("records")
    leaders = [row for row in records if row["rank"] == 1]
    return legacy._base_result(
        intent,
        "ok",
        svs_period,
        parameters=params,
        metrics={
            "mode": "leader",
            "scope": scope,
            "leader_count": len(leaders),
            "top_positive_contribution": leaders[0]["positive_contribution"],
            "total_positive_contribution": total_positive,
            "player_count": len(records),
            "leaders": leaders,
        },
        rankings={"players": records},
    )


def calculate_alliance_positive_contribution_leader(
    data,
    svs_period=None,
    *,
    scope="current_filters",
):
    intent = ALLIANCE_POSITIVE_CONTRIBUTION_INTENT
    params = {} if scope == "current_filters" else {"scope": scope}
    missing = {"alliance", "net_score"}.difference(data.columns)
    if missing:
        return legacy._missing_columns_result(intent, missing, svs_period, params)

    frame = legacy._numeric_scope(data, ["alliance", "net_score"]).dropna(
        subset=["alliance", "net_score"]
    )
    if frame.empty:
        return legacy._base_result(
            intent,
            "guidance",
            svs_period,
            "empty_score_scope",
            parameters=params,
        )

    summary = frame.groupby("alliance", as_index=False).agg(
        positive_contribution=(
            "net_score",
            lambda values: values[values > 0].sum(),
        ),
        negative_impact=(
            "net_score",
            lambda values: values[values < 0].abs().sum(),
        ),
        total_net_score=("net_score", "sum"),
    )
    total_positive = summary["positive_contribution"].sum()
    if total_positive <= 0:
        return legacy._base_result(
            intent,
            "guidance",
            svs_period,
            "no_positive_contribution",
            parameters=params,
        )

    summary["share_of_scope_positive"] = (
        summary["positive_contribution"] / total_positive * 100
    )
    summary = summary.sort_values(
        ["positive_contribution", "total_net_score", "alliance"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    summary["rank"] = summary["positive_contribution"].rank(
        method="min", ascending=False
    ).astype(int)
    records = summary.to_dict("records")
    leaders = [row for row in records if row["rank"] == 1]
    return legacy._base_result(
        intent,
        "ok",
        svs_period,
        parameters=params,
        metrics={
            "scope": scope,
            "leader_count": len(leaders),
            "top_positive_contribution": leaders[0]["positive_contribution"],
            "total_positive_contribution": total_positive,
            "alliance_count": len(records),
            "leaders": leaders,
        },
        rankings={"alliances": records},
    )


def calculate_top_contributors(
    data,
    svs_period=None,
    alliance_names=None,
    *,
    mode="grouped",
    scope="current_filters",
):
    if mode == "leader":
        return calculate_player_positive_contribution_leader(
            data,
            svs_period,
            alliance_names,
            scope=scope,
        )
    result = legacy.calculate_top_contributors(
        data, svs_period, alliance_names=alliance_names
    )
    result.setdefault("metrics", {})["mode"] = "grouped"
    return result


@lru_cache(maxsize=8)
def _load_server_period_data(svs_period):
    from data_loading import coerce_numeric_columns

    source = pd.read_csv(REPOSITORY_ROOT / "svs_scores_utf8.csv")
    source = source.loc[:, ~source.columns.str.contains(r"^Unnamed")].dropna(how="all")
    source = coerce_numeric_columns(source)
    if svs_period is not None and "svs_date" in source.columns:
        source = source[source["svs_date"].astype(str) == str(svs_period)]
    return source.reset_index(drop=True)


def _analysis_data(data, svs_period, scope, server_data=None):
    if scope != "server":
        return data
    return server_data if server_data is not None else _load_server_period_data(svs_period).copy()


def execute_dashboard_intent(
    contract,
    data,
    svs_period=None,
    selected_player_names=None,
    known_alliance_names=None,
    *,
    server_data=None,
):
    contract = validate_intent_contract(contract)
    intent = contract["intent"]
    params = contract["parameters"]
    if intent == "top_contributors":
        scope = params.get("scope", "current_filters")
        result = calculate_top_contributors(
            _analysis_data(data, svs_period, scope, server_data),
            svs_period,
            alliance_names=params.get("alliance_names") or None,
            mode=params.get("mode", "grouped"),
            scope=scope,
        )
        return legacy._attach_routing(result, contract)
    if intent == ALLIANCE_POSITIVE_CONTRIBUTION_INTENT:
        scope = params.get("scope", "current_filters")
        result = calculate_alliance_positive_contribution_leader(
            _analysis_data(data, svs_period, scope, server_data),
            svs_period,
            scope=scope,
        )
        return legacy._attach_routing(result, contract)
    return legacy.execute_dashboard_intent(
        contract,
        data,
        svs_period,
        selected_player_names,
        known_alliance_names,
    )


def route_dashboard_question_hybrid(
    question,
    known_alliance_names=None,
    *,
    ai_enabled=False,
    ai_extractor=None,
):
    rule_contract = validate_intent_contract(
        route_dashboard_question(question, known_alliance_names)
    )
    if (
        rule_contract["match_status"] != "unsupported"
        or not ai_enabled
        or is_obvious_smalltalk_question(question)
    ):
        return {
            "contract": rule_contract,
            "ai_attempted": False,
            "ai_succeeded": False,
            "diagnostic_code": None,
        }
    if ai_extractor is None:
        return {
            "contract": rule_contract,
            "ai_attempted": False,
            "ai_succeeded": False,
            "diagnostic_code": "api_unavailable",
        }
    try:
        api_contract = validate_intent_contract(
            ai_extractor(question, known_alliance_names or [])
        )
    except Exception as exc:
        code = getattr(exc, "diagnostic_code", "api_invalid_output")
        if code not in {
            "api_unavailable",
            "api_refusal",
            "api_incomplete",
            "api_invalid_output",
        }:
            code = "api_invalid_output"
        return {
            "contract": rule_contract,
            "ai_attempted": True,
            "ai_succeeded": False,
            "diagnostic_code": code,
        }
    return {
        "contract": api_contract,
        "ai_attempted": True,
        "ai_succeeded": True,
        "diagnostic_code": None,
    }


def calculate_dashboard_answer(
    question,
    data,
    svs_period=None,
    selected_player_names=None,
    known_alliance_names=None,
    *,
    intent_router=None,
    server_data=None,
):
    if known_alliance_names is None:
        known_alliance_names = (
            data["alliance"].dropna().unique().tolist()
            if "alliance" in data.columns
            else []
        )
    if intent_router is None:
        contract = route_dashboard_question(question, known_alliance_names)
        routing_result = None
    else:
        routing_result = intent_router(question, known_alliance_names)
        contract = routing_result["contract"] if isinstance(routing_result, dict) else routing_result
    validated = validate_intent_contract(contract)
    result = execute_dashboard_intent(
        validated,
        data,
        svs_period,
        selected_player_names,
        known_alliance_names,
        server_data=server_data,
    )
    result["parameters"] = {
        "question": question,
        "mentioned_alliances": legacy.extract_alliance_names_from_question(
            question, known_alliance_names
        ),
        **result.get("parameters", {}),
    }
    if routing_result is not None and isinstance(routing_result, dict):
        result["routing_diagnostics"] = {
            "ai_attempted": bool(routing_result.get("ai_attempted", False)),
            "ai_succeeded": bool(routing_result.get("ai_succeeded", False)),
            "diagnostic_code": routing_result.get("diagnostic_code"),
        }
    return result
