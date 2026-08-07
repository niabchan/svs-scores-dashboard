"""Contribution-question constants, routing, and contract validation."""

from __future__ import annotations

import json
import math
import re
from typing import Any

from ._legacy import legacy

QUESTION_TOP_CONTRIBUTOR = "Who contributed the most under the current filters?"
QUESTION_TOP_CONTRIBUTORS = "Show the top contributors within each selected alliance."
SUGGESTED_QUESTIONS = [
    legacy.QUESTION_NET_VS_POSITIVE,
    legacy.QUESTION_EXCLUSION_IMPACT,
    legacy.QUESTION_NEGATIVE_PERCENTAGE,
    QUESTION_TOP_CONTRIBUTOR,
    QUESTION_TOP_CONTRIBUTORS,
    legacy.QUESTION_HELP,
    legacy.QUESTION_CUSTOM,
]

ALLIANCE_POSITIVE_CONTRIBUTION_INTENT = "alliance_positive_contribution_leader"
CONTRIBUTOR_MODES = {"leader", "grouped"}
ANALYSIS_SCOPES = {"current_filters", "server"}
SUPPORTED_DASHBOARD_INTENTS = set(legacy.SUPPORTED_DASHBOARD_INTENTS) | {
    ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
}
SCORE_DERIVED_INTENTS = set(legacy.SCORE_DERIVED_INTENTS) | {
    ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
}

_CONTRIBUTION_RE = re.compile(r"\bcontribut(?:e|ed|es|ing|ion|ions|or|ors)?\b")
_POSITIVE_PHRASES = {"positive contribution", "positive score", "server positive score"}
_GROUPED_PHRASES = {
    "within each alliance",
    "in each alliance",
    "for each alliance",
    "for every alliance",
    "each selected alliance",
    "every selected alliance",
}
_SERVER_PHRASES = {
    "server",
    "whole server",
    "entire server",
    "server wide",
    "server-wide",
    "overall server",
}


def _has_contribution_language(text: str) -> bool:
    return bool(_CONTRIBUTION_RE.search(text))


def _requested_scope(text: str) -> str:
    return "server" if any(phrase in text for phrase in _SERVER_PHRASES) else "current_filters"


def _is_grouped_request(text: str) -> bool:
    words = set(text.split())
    if any(phrase in text for phrase in _GROUPED_PHRASES):
        return True
    if words.intersection({"show", "list", "rank", "ranking"}) and words.intersection(
        {"contributors", "players"}
    ):
        return True
    return bool(
        re.search(r"\btop\s+\d+\b", text)
        and words.intersection({"contributors", "players"})
    )


def _is_alliance_leader_request(text: str) -> bool:
    positive_metric = any(phrase in text for phrase in _POSITIVE_PHRASES)
    if not (_has_contribution_language(text) or positive_metric):
        return False
    alliance_subject = bool(
        re.search(r"\b(?:which|what|the|top|best|highest)\s+alliance\b", text)
        or re.search(r"\balliance\s+that\b", text)
    )
    leader_language = bool(
        re.search(r"\b(?:most|top|best|highest|lead|leads|leader|first)\b", text)
    )
    return alliance_subject and (leader_language or positive_metric)


def _is_player_leader_request(text: str) -> bool:
    if not _has_contribution_language(text) or _is_grouped_request(text):
        return False
    words = set(text.split())
    player_subject = bool(
        "who" in words
        or "player" in words
        or re.search(r"\b(?:top|best|highest)\s+contributor\b", text)
    )
    leader_language = bool(
        re.search(r"\b(?:most|top|best|highest|lead|leads|leader|first)\b", text)
    )
    return player_subject and leader_language


def route_dashboard_question(question, known_alliance_names=None):
    normalized = legacy.normalize_question_text(question)
    known_alliance_names = known_alliance_names or []
    mentioned = legacy.extract_alliance_names_from_question(question, known_alliance_names)
    scope = _requested_scope(normalized)

    if question == QUESTION_TOP_CONTRIBUTOR:
        return legacy._intent_contract(
            "top_contributors", {"alliance_names": [], "mode": "leader"}
        )
    if question == QUESTION_TOP_CONTRIBUTORS:
        # Keep the historical parameter shape for existing callers/tests.
        return legacy._intent_contract("top_contributors", {"alliance_names": []})
    if _is_alliance_leader_request(normalized):
        params = {} if scope == "current_filters" else {"scope": scope}
        return legacy._intent_contract(ALLIANCE_POSITIVE_CONTRIBUTION_INTENT, params)
    if _is_player_leader_request(normalized):
        params: dict[str, Any] = {"alliance_names": mentioned, "mode": "leader"}
        if scope == "server":
            params["scope"] = "server"
        return legacy._intent_contract("top_contributors", params)
    if _is_grouped_request(normalized) and _has_contribution_language(normalized):
        return legacy._intent_contract("top_contributors", {"alliance_names": mentioned})
    return legacy.route_dashboard_question(question, known_alliance_names)


def _validate_common(contract):
    if not isinstance(contract, dict):
        raise ValueError("intent contract must be a dictionary")
    unknown = set(contract).difference(legacy.INTENT_CONTRACT_FIELDS)
    if unknown:
        raise ValueError(f"unknown intent contract field(s): {legacy._field_names(unknown)}")
    if contract.get("schema_version") != legacy.INTENT_CONTRACT_SCHEMA_VERSION:
        raise ValueError("unsupported intent contract schema_version")
    if contract.get("intent") not in SUPPORTED_DASHBOARD_INTENTS:
        raise ValueError("unknown intent")
    if contract.get("source") not in legacy.INTENT_SOURCES:
        raise ValueError("invalid intent source")
    confidence = contract.get("confidence")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
    ):
        raise ValueError("confidence must be finite numeric between 0 and 1")
    if contract.get("match_status") not in legacy.INTENT_MATCH_STATUSES:
        raise ValueError("invalid match_status")
    if not isinstance(contract.get("parameters"), dict):
        raise ValueError("parameters must be a dictionary")
    guidance = contract.get("guidance_code")
    if guidance is not None and not isinstance(guidance, str):
        raise ValueError("guidance_code must be a string or None")
    if contract["match_status"] == "matched" and guidance is not None:
        raise ValueError("matched contracts cannot include guidance_code")
    if contract["match_status"] != "matched":
        raise ValueError(f"{contract['intent']} requires matched status")
    if contract["source"] == "rule" and confidence != 1.0:
        raise ValueError("rule contracts must use deterministic confidence values")


def _alliance_names(value, label):
    if not isinstance(value, list) or not all(
        isinstance(name, str) and name.strip() for name in value
    ):
        raise ValueError(f"{label} must be a list of nonblank strings")
    return list(value)


def validate_intent_contract(contract):
    intent = contract.get("intent") if isinstance(contract, dict) else None
    if intent not in {"top_contributors", ALLIANCE_POSITIVE_CONTRIBUTION_INTENT}:
        return legacy.validate_intent_contract(contract)

    _validate_common(contract)
    params = dict(contract["parameters"])
    if intent == "top_contributors":
        unknown = set(params).difference({"alliance_names", "mode", "scope"})
        if unknown:
            raise ValueError(
                "unknown parameter field(s) for top_contributors: "
                f"{legacy._field_names(unknown)}"
            )
        params["alliance_names"] = _alliance_names(
            params.get("alliance_names", []), "top_contributors alliance_names"
        )
        if "mode" in params and params["mode"] not in CONTRIBUTOR_MODES:
            raise ValueError("top_contributors mode is invalid")
        if "scope" in params and params["scope"] not in ANALYSIS_SCOPES:
            raise ValueError("top_contributors scope is invalid")
    else:
        unknown = set(params).difference({"scope"})
        if unknown:
            raise ValueError(
                "unknown parameter field(s) for alliance_positive_contribution_leader: "
                f"{legacy._field_names(unknown)}"
            )
        if "scope" in params and params["scope"] not in ANALYSIS_SCOPES:
            raise ValueError("alliance_positive_contribution_leader scope is invalid")

    normalized = dict(contract)
    normalized["parameters"] = params
    normalized["confidence"] = float(contract["confidence"])
    normalized = legacy._json_value(normalized)
    json.dumps(normalized)
    return normalized
