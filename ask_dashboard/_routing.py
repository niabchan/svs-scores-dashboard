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
_CONTRIBUTION_PHRASES = {
    # Spanish
    "contribuyente",
    "contribuyentes",
    "contribuyó",
    "contribuyeron",
    "contribución",
    # French
    "contributeur",
    "contributeurs",
    "contributrice",
    "contributrices",
    "contribué",
    "contribution",
    # Vietnamese
    "đóng góp",
    "người đóng góp",
    # Indonesian
    "kontributor",
    "kontribusi",
    "berkontribusi",
    # Thai (custom questions are accepted even though Thai is not a UI locale)
    "มีส่วนร่วม",
    "ผู้มีส่วนร่วม",
}
_POSITIVE_PHRASES = {"positive contribution", "positive score", "server positive score"}
_GROUPED_PHRASES = {
    "within each alliance",
    "in each alliance",
    "for each alliance",
    "for every alliance",
    "each selected alliance",
    "every selected alliance",
    # Spanish
    "cada alianza",
    "por alianza",
    # French
    "chaque alliance",
    "par alliance",
    # Vietnamese
    "mỗi liên minh",
    # Indonesian
    "setiap aliansi",
    "per aliansi",
    # Thai
    "แต่ละพันธมิตร",
}
_SERVER_PHRASES = {
    "server",
    "whole server",
    "entire server",
    "server wide",
    "server-wide",
    "overall server",
}
_METRIC_DEFINITION_PATTERNS = (
    r"^(?:what is|define|explain) (?:the )?(?:net score|score gained|score lost|positive contribution|negative impact|negative contribution|negative share|negative percentage|negative percent|negative ratio)$",
    r"^what does (?:the )?(?:net score|score gained|score lost|positive contribution|negative impact|negative contribution|negative share|negative percentage|negative percent|negative ratio) mean$",
    r"^how is (?:the )?(?:net score|score gained|score lost|positive contribution|negative impact|negative contribution|negative share|negative percentage|negative percent|negative ratio) (?:calculated|computed)$",
    r"^how do you calculate (?:the )?(?:net score|score gained|score lost|positive contribution|negative impact|negative contribution|negative share|negative percentage|negative percent|negative ratio)$",
)
_PLAYER_BALANCE_PHRASES = {
    "overall balance",
    "final balance",
    "best overall result",
    "strongest overall result",
    "best gain versus loss result",
    "best gain vs loss result",
    "finished furthest ahead",
    "finished the furthest ahead",
}
_PLAYER_SUBJECT_WORDS = {
    "who",
    "player",
    "players",
    "quién",
    "quien",
    "jugador",
    "jugadores",
    "qui",
    "joueur",
    "joueurs",
    "ai",
    "siapa",
    "pemain",
    "ใคร",
    "ผู้เล่น",
}
_PLAYER_SUBJECT_PHRASES = {
    "người chơi",
    "ผู้เล่น",
}
_ALLIANCE_SUBJECT_PHRASES = {
    "alliance",
    "alliances",
    "alianza",
    "alianzas",
    "liên minh",
    "aliansi",
    "พันธมิตร",
}
_GENERIC_PLAYER_BEST_PHRASES = {
    # English
    "best player",
    "top player",
    "strongest player",
    "who is the best",
    "who s the best",
    # Spanish
    "mejor jugador",
    "quién es el mejor",
    "quien es el mejor",
    # French
    "meilleur joueur",
    "qui est le meilleur",
    # Vietnamese
    "người chơi tốt nhất",
    "người chơi giỏi nhất",
    "ai là người giỏi nhất",
    "ai là người chơi tốt nhất",
    # Indonesian
    "pemain terbaik",
    "siapa yang terbaik",
    # Thai
    "ใครเก่งที่สุด",
    "ใครดีที่สุด",
    "ผู้เล่นที่เก่งที่สุด",
    "ผู้เล่นเก่งที่สุด",
}
_CONTRIBUTOR_LEADER_PHRASES = {
    # English
    "top contributor",
    "best contributor",
    "highest contributor",
    "contributed the most",
    "contributed most",
    # Spanish
    "mejor contribuyente",
    "principal contribuyente",
    "contribuyó más",
    "contribuyo más",
    "más contribuyó",
    "mas contribuyo",
    # French
    "meilleur contributeur",
    "meilleure contributrice",
    "plus contribué",
    "plus contribue",
    # Vietnamese
    "đóng góp nhiều nhất",
    "người đóng góp nhiều nhất",
    "người đóng góp tốt nhất",
    # Indonesian
    "kontributor terbaik",
    "berkontribusi paling banyak",
    "kontribusi paling besar",
    # Thai
    "มีส่วนร่วมมากที่สุด",
    "ผู้มีส่วนร่วมที่ดีที่สุด",
}
_SMALLTALK_PATTERNS = (
    r"^(?:hello|hi|hey)(?: there)?(?: how are you)?$",
    r"^how are you$",
    r"^good (?:morning|afternoon|evening)$",
    r"^(?:thanks|thank you)(?: very much)?$",
)


def _has_contribution_language(text: str) -> bool:
    return bool(_CONTRIBUTION_RE.search(text)) or any(
        phrase in text for phrase in _CONTRIBUTION_PHRASES
    )


def _has_player_subject(text: str) -> bool:
    words = set(text.split())
    return bool(words.intersection(_PLAYER_SUBJECT_WORDS)) or any(
        phrase in text for phrase in _PLAYER_SUBJECT_PHRASES
    )


def _has_alliance_subject(text: str) -> bool:
    return any(phrase in text for phrase in _ALLIANCE_SUBJECT_PHRASES)


def _requested_scope(text: str) -> str:
    return "server" if any(phrase in text for phrase in _SERVER_PHRASES) else "current_filters"


def _is_metric_definition_request(text: str) -> bool:
    return any(re.fullmatch(pattern, text) for pattern in _METRIC_DEFINITION_PATTERNS)


_GENERAL_HELP_PATTERNS = (
    r"^(?:(?:hello|hi|hey)(?: there)? )?(?:can|could|would|will) you help me(?: please)?$",
    r"^(?:(?:hello|hi|hey)(?: there)? )?please help me$",
    r"^(?:(?:hello|hi|hey)(?: there)? )?help me(?: please)?$",
    r"^(?:(?:hello|hi|hey)(?: there)? )?i (?:need|would like) help$",
)


def _is_general_help_request(text: str) -> bool:
    """Recognize only standalone/general help requests, not analytical questions."""
    return any(re.fullmatch(pattern, text) for pattern in _GENERAL_HELP_PATTERNS)


def _is_player_net_balance_request(text: str) -> bool:
    words = set(text.split())
    player_subject = bool(words.intersection({"who", "player", "players"}))
    leader_language = bool(
        words.intersection({"top", "best", "highest", "strongest", "furthest"})
    )
    balance_language = any(phrase in text for phrase in _PLAYER_BALANCE_PHRASES)
    return player_subject and leader_language and balance_language


def _is_generic_player_best_request(text: str) -> bool:
    """Treat broad 'best player/person' wording as a player net-score request.

    Net score is the dashboard's established default for broad overall performance.
    The phrases cover the five UI languages plus Thai, which is accepted as custom
    free text even though the interface itself has no Thai locale.
    """
    if _has_contribution_language(text) or _has_alliance_subject(text):
        return False
    return any(phrase in text for phrase in _GENERIC_PLAYER_BEST_PHRASES)


def is_obvious_smalltalk_question(question: str) -> bool:
    """Return True only for clear conversational messages that need no AI routing."""
    text = legacy.normalize_question_text(question)
    return any(re.fullmatch(pattern, text) for pattern in _SMALLTALK_PATTERNS)


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
    player_subject = _has_player_subject(text) or any(
        phrase in text for phrase in _CONTRIBUTOR_LEADER_PHRASES
    )
    leader_language = bool(
        re.search(r"\b(?:most|top|best|highest|lead|leads|leader|first)\b", text)
    ) or any(phrase in text for phrase in _CONTRIBUTOR_LEADER_PHRASES)
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
    if _is_metric_definition_request(normalized):
        # Metric explanations are deterministic dashboard help and do not need
        # an API classification or access to score rows.
        return legacy._intent_contract("dashboard_help")
    if _is_general_help_request(normalized):
        # Generic requests for help are deterministic product guidance. Keep
        # this intentionally narrow so analytical questions containing "help"
        # still proceed through normal rule/API routing.
        return legacy._intent_contract("dashboard_help")
    if _is_player_net_balance_request(normalized) or _is_generic_player_best_request(
        normalized
    ):
        return legacy._intent_contract(
            "player_net_score_leader", {"alliance_names": mentioned}
        )
    if _is_alliance_leader_request(normalized):
        params = {} if scope == "current_filters" else {"scope": scope}
        return legacy._intent_contract(ALLIANCE_POSITIVE_CONTRIBUTION_INTENT, params)
    if _is_player_leader_request(normalized):
        # Preserve the historical named-alliance list response for questions
        # such as "Who contributed most in SnS?" Existing users may rely on
        # seeing several contributors from that alliance. An unqualified
        # singular question asks for one player leader across the active scope.
        if mentioned:
            return legacy._intent_contract(
                "top_contributors", {"alliance_names": mentioned}
            )
        params: dict[str, Any] = {"alliance_names": [], "mode": "leader"}
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
    try:
        json.dumps(normalized)
    except (TypeError, ValueError) as exc:
        raise ValueError("intent contract must be JSON serializable") from exc
    return normalized
