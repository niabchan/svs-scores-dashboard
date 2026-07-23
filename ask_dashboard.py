import json
import math
import re
import unicodedata
from datetime import datetime, timezone

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

INTENT_CONTRACT_SCHEMA_VERSION = 1
INTENT_MATCH_STATUSES = {"matched", "needs_clarification", "unsupported"}
INTENT_SOURCES = {"rule", "api"}
INTENT_CONTRACT_FIELDS = {
    "schema_version",
    "intent",
    "parameters",
    "source",
    "confidence",
    "match_status",
    "guidance_code",
}
SUPPORTED_DASHBOARD_INTENTS = {
    "net_vs_positive_ranking",
    "player_exclusion_impact",
    "negative_share_change",
    "top_contributors",
    "alliance_exclusion_total_net",
    "net_score_leader_summary",
    "player_net_score_leader",
    "unsupported_question",
}
NEGATIVE_SHARE_DIRECTIONS = {"increase", "decrease", "neutral", "unspecified"}

CONTRIBUTOR_CONTEXT_TERMS = {"contributor", "contributors", "contribution", "contributed", "contributing", "contribut", "player", "players", "who"}
CONTRIBUTOR_RANKING_TERMS = {"best", "top", "most"}
EXCLUSION_TERMS = {"exclude", "excluded", "excluding", "exclusion", "exclusions", "without", "remove", "removed", "removing", "except"}
EXCLUSION_EFFECT_TERMS = {"change", "changed", "impact", "happen", "happened", "result", "affect", "affected", "effect", "effects"}
NEGATIVE_INCREASE_TERMS = {"increase", "increased", "rise", "rose", "higher"}
NEGATIVE_DECREASE_TERMS = {"lower", "decrease", "decreased", "decline", "declined", "fall", "fell", "drop", "dropped", "reduce", "reduced"}
NEGATIVE_NEUTRAL_CHANGE_TERMS = {"change", "changed"}
NEGATIVE_CHANGE_TERMS = NEGATIVE_INCREASE_TERMS | NEGATIVE_DECREASE_TERMS | NEGATIVE_NEUTRAL_CHANGE_TERMS
NET_LEADER_WORD_TERMS = {"lead", "leads", "leader", "leading", "winner"}
NET_LEADER_PHRASE_TERMS = {"top net", "highest net", "best net", "first in net", "net score winner", "net score leader", "number one by net", "1 by net"}
NET_SCORE_PHRASE_TERMS = {"net score"}
EXPLICIT_PLAYER_SUBJECT_TERMS = {"player", "players"}
WHO_SUBJECT_TERMS = {"who"}
ALLIANCE_SUBJECT_TERMS = {"alliance", "alliances"}
POSITIVE_RANK_TERMS = {"positive contribution", "positive rank", "positive ranking", "first in positive", "top in positive"}


def _has_any_word(text, terms):
    words = set(text.split())
    return any(term in words for term in terms)


def _has_any_phrase(text, terms):
    return any(term in text for term in terms)


def _has_any_word_or_phrase(text, word_terms, phrase_terms):
    return _has_any_word(text, word_terms) or _has_any_phrase(text, phrase_terms)



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
        key=lambda value: (-len(value), value),
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


def _intent_contract(intent, parameters=None, match_status="matched", guidance_code=None, confidence=None):
    if confidence is None:
        confidence = 0.0 if match_status == "unsupported" else 1.0
    return {
        "schema_version": INTENT_CONTRACT_SCHEMA_VERSION,
        "intent": intent,
        "parameters": parameters or {},
        "source": "rule",
        "confidence": confidence,
        "match_status": match_status,
        "guidance_code": guidance_code,
    }


def _field_names(fields):
    return ", ".join(sorted(field if isinstance(field, str) else "<non-string>" for field in fields))


def route_dashboard_question(question, known_alliance_names=None):
    """Return a JSON-serializable intent contract for a dashboard question."""
    normalized_question = normalize_question_text(question)
    known_alliance_names = known_alliance_names or []
    mentioned_alliances = extract_alliance_names_from_question(question, known_alliance_names)

    if question == QUESTION_NET_VS_POSITIVE:
        return _intent_contract("net_vs_positive_ranking")
    if question == QUESTION_EXCLUSION_IMPACT:
        return _intent_contract("player_exclusion_impact")
    if question == QUESTION_NEGATIVE_PERCENTAGE:
        return _intent_contract("negative_share_change", {"requested_direction": "increase"})
    if question == QUESTION_TOP_CONTRIBUTORS:
        return _intent_contract("top_contributors", {"alliance_names": []})

    has_exclusion_term = _has_any_word(normalized_question, EXCLUSION_TERMS)
    asks_about_player_exclusion = has_exclusion_term and ("player" in normalized_question or "selected" in normalized_question)
    asks_about_exclusion_effect = _has_any_word(normalized_question, EXCLUSION_EFFECT_TERMS)
    asks_about_negative_share = (
        "negative" in normalized_question
        and _has_any_phrase(normalized_question, {"percentage", "percent", "share", "ratio"})
        and _has_any_word(normalized_question, NEGATIVE_CHANGE_TERMS)
    )
    asks_about_positive_rank = (
        _has_any_phrase(normalized_question, POSITIVE_RANK_TERMS)
        or ("positive" in normalized_question and _has_any_word(normalized_question, {"rank", "ranking", "first", "top"}))
    )
    has_net_score_context = _has_any_word(normalized_question, {"net"}) or _has_any_phrase(normalized_question, NET_SCORE_PHRASE_TERMS)
    has_explicit_player_subject = _has_any_word(normalized_question, EXPLICIT_PLAYER_SUBJECT_TERMS)
    has_alliance_subject = _has_any_word(normalized_question, ALLIANCE_SUBJECT_TERMS)
    has_who_subject = _has_any_word(normalized_question, WHO_SUBJECT_TERMS)
    has_player_subject = has_explicit_player_subject or (has_who_subject and not has_alliance_subject)
    asks_about_net_leader = has_net_score_context and (
        has_explicit_player_subject
        or has_alliance_subject
        or has_who_subject
        or _has_any_word_or_phrase(normalized_question, NET_LEADER_WORD_TERMS, NET_LEADER_PHRASE_TERMS)
    )
    asks_player_net_leader = asks_about_net_leader and has_player_subject and not asks_about_positive_rank
    asks_alliance_net_leader = asks_about_net_leader and has_alliance_subject and not has_explicit_player_subject and not asks_about_positive_rank
    asks_general_net_leader = asks_about_net_leader and not has_player_subject and not has_alliance_subject and not asks_about_positive_rank
    has_contributor_context = _has_any_phrase(normalized_question, CONTRIBUTOR_CONTEXT_TERMS)
    has_contributor_ranking = _has_any_word(normalized_question, CONTRIBUTOR_RANKING_TERMS)
    asks_about_contributors = has_contributor_context and (
        has_contributor_ranking
        or _has_any_phrase(normalized_question, {"contribut", "player"})
    )

    if has_exclusion_term and mentioned_alliances and any(term in normalized_question for term in ["alliance", "net", "score", "total", "change"]):
        return _intent_contract("alliance_exclusion_total_net", {"excluded_alliances": mentioned_alliances})
    if asks_about_player_exclusion and asks_about_exclusion_effect:
        return _intent_contract("player_exclusion_impact")
    if has_exclusion_term and ("net score" in normalized_question or "total net" in normalized_question) and not mentioned_alliances:
        return _intent_contract(
            "alliance_exclusion_total_net",
            {"excluded_alliances": []},
            match_status="needs_clarification",
            guidance_code="missing_alliance_name",
        )
    if asks_about_net_leader and asks_about_positive_rank:
        return _intent_contract("net_vs_positive_ranking")
    if asks_player_net_leader:
        return _intent_contract("player_net_score_leader", {"alliance_names": mentioned_alliances})
    if asks_alliance_net_leader or asks_general_net_leader:
        return _intent_contract("net_score_leader_summary")
    if asks_about_negative_share:
        return _intent_contract(
            "negative_share_change",
            {"requested_direction": classify_negative_share_requested_direction(question)},
        )
    if asks_about_contributors and ("alliance" in normalized_question or mentioned_alliances):
        return _intent_contract("top_contributors", {"alliance_names": mentioned_alliances})
    return _intent_contract(
        "unsupported_question",
        match_status="unsupported",
        guidance_code="unsupported_question",
    )


def validate_intent_contract(contract):
    """Validate and normalize an Ask Dashboard intent contract."""
    if not isinstance(contract, dict):
        raise ValueError("intent contract must be a dictionary")
    unknown_fields = set(contract).difference(INTENT_CONTRACT_FIELDS)
    if unknown_fields:
        raise ValueError(f"unknown intent contract field(s): {_field_names(unknown_fields)}")
    normalized = dict(contract)
    if normalized.get("schema_version") != INTENT_CONTRACT_SCHEMA_VERSION:
        raise ValueError("unsupported intent contract schema_version")
    intent = normalized.get("intent")
    if intent not in SUPPORTED_DASHBOARD_INTENTS:
        raise ValueError("unknown intent")
    source = normalized.get("source")
    if source not in INTENT_SOURCES:
        raise ValueError("invalid intent source")
    confidence = normalized.get("confidence")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or confidence < 0
        or confidence > 1
    ):
        raise ValueError("confidence must be finite numeric between 0 and 1")
    match_status = normalized.get("match_status")
    if match_status not in INTENT_MATCH_STATUSES:
        raise ValueError("invalid match_status")
    parameters = normalized.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a dictionary")
    guidance_code = normalized.get("guidance_code")
    if guidance_code is not None and not isinstance(guidance_code, str):
        raise ValueError("guidance_code must be a string or None")
    if match_status == "matched" and guidance_code is not None:
        raise ValueError("matched contracts cannot include guidance_code")
    if match_status in {"needs_clarification", "unsupported"} and not guidance_code:
        raise ValueError("clarification and unsupported contracts require guidance_code")

    if intent == "unsupported_question":
        if match_status != "unsupported":
            raise ValueError("unsupported_question requires unsupported match_status")
        if guidance_code != "unsupported_question":
            raise ValueError("unsupported_question requires unsupported_question guidance_code")
        if confidence != 0.0:
            raise ValueError("unsupported_question requires confidence 0.0")
        if parameters:
            raise ValueError("unsupported_question parameters must be empty")
    elif match_status == "unsupported":
        raise ValueError("unsupported match_status requires unsupported_question intent")

    if match_status == "needs_clarification":
        if intent != "alliance_exclusion_total_net":
            raise ValueError("needs_clarification is only supported for alliance_exclusion_total_net")
        if guidance_code != "missing_alliance_name":
            raise ValueError("alliance exclusion clarification requires missing_alliance_name")

    if source == "rule":
        expected_confidence = 0.0 if match_status == "unsupported" else 1.0
        if confidence != expected_confidence:
            raise ValueError("rule contracts must use deterministic confidence values")

    params = dict(parameters)
    if intent == "negative_share_change":
        unknown_params = set(params).difference({"requested_direction"})
        if unknown_params:
            raise ValueError(f"unknown parameter field(s) for negative_share_change: {_field_names(unknown_params)}")
        direction = params.get("requested_direction", "unspecified")
        if direction not in NEGATIVE_SHARE_DIRECTIONS:
            raise ValueError("negative_share_change requested_direction is invalid")
        params["requested_direction"] = direction
    elif intent in {"top_contributors", "player_net_score_leader"}:
        unknown_params = set(params).difference({"alliance_names"})
        if unknown_params:
            raise ValueError(f"unknown parameter field(s) for {intent}: {_field_names(unknown_params)}")
        names = params.get("alliance_names", [])
        if not isinstance(names, list) or not all(isinstance(name, str) and name.strip() for name in names):
            raise ValueError(f"{intent} alliance_names must be a list of nonblank strings")
        params["alliance_names"] = list(names)
    elif intent == "alliance_exclusion_total_net":
        unknown_params = set(params).difference({"excluded_alliances"})
        if unknown_params:
            raise ValueError(f"unknown parameter field(s) for alliance_exclusion_total_net: {_field_names(unknown_params)}")
        names = params.get("excluded_alliances", [])
        if not isinstance(names, list) or not all(isinstance(name, str) and name.strip() for name in names):
            raise ValueError("alliance_exclusion_total_net excluded_alliances must be a list of nonblank strings")
        if match_status == "needs_clarification" and names:
            raise ValueError("alliance exclusion clarification cannot include excluded alliances")
        if match_status == "matched" and not names:
            raise ValueError("matched alliance_exclusion_total_net requires excluded_alliances")
        params["excluded_alliances"] = list(names)
    elif params:
        raise ValueError(f"{intent} does not accept parameters")

    normalized["parameters"] = params
    normalized["confidence"] = float(confidence)
    normalized = _json_value(normalized)
    try:
        json.dumps(normalized)
    except (TypeError, ValueError) as exc:
        raise ValueError("intent contract must be JSON serializable") from exc
    return normalized


def _utc_timestamp(timestamp_utc=None):
    if timestamp_utc is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if isinstance(timestamp_utc, datetime):
        if timestamp_utc.tzinfo is None or timestamp_utc.utcoffset() is None:
            raise ValueError("timestamp_utc datetime must be timezone-aware")
        return timestamp_utc.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return str(timestamp_utc)


def _plain_string_list(values):
    if values is None:
        return []
    return [str(_json_value(value)) for value in values]


def build_question_log_record(
    answer,
    *,
    selected_alliances=None,
    selected_net_status=None,
    selected_player_count=None,
    total_player_count=None,
    timestamp_utc=None,
):
    """Build a minimal JSON-serializable Ask Dashboard session log record."""
    params = answer.get("parameters", {}) if isinstance(answer, dict) else {}
    metrics = answer.get("metrics", {}) if isinstance(answer, dict) else {}
    routing = answer.get("routing", {}) if isinstance(answer, dict) else {}
    total_count = int(_json_value(total_player_count or 0))
    selected_count = int(_json_value(selected_player_count if selected_player_count is not None else total_count))
    excluded_count = max(total_count - selected_count, 0)
    if isinstance(metrics, dict) and "excluded_player_count" in metrics:
        excluded_count = int(_json_value(metrics.get("excluded_player_count") or excluded_count))
    record = {
        "schema_version": 1,
        "timestamp_utc": _utc_timestamp(timestamp_utc),
        "question": str(params.get("question", "")),
        "normalized_question": normalize_question_text(params.get("question", "")),
        "intent": str(answer.get("intent")) if isinstance(answer, dict) else None,
        "status": str(answer.get("status")) if isinstance(answer, dict) else None,
        "guidance_code": _json_value(answer.get("guidance_code")) if isinstance(answer, dict) else None,
        "error_code": _json_value(answer.get("error_code")) if isinstance(answer, dict) else None,
        "source": str(routing.get("source", "rule")) if isinstance(routing, dict) else "rule",
        "period": _json_value(answer.get("period")) if isinstance(answer, dict) else None,
        "mentioned_alliances": _plain_string_list(params.get("mentioned_alliances")),
        "requested_direction": _json_value(params.get("requested_direction")),
        "selected_alliances": _plain_string_list(selected_alliances),
        "selected_net_status": _plain_string_list(selected_net_status),
        "selected_player_count": selected_count,
        "total_player_count": total_count,
        "excluded_player_count": excluded_count,
    }
    return _json_value(record)


def append_question_log_record(records, record, max_entries=100):
    """Append a question log record and keep only the newest bounded entries."""
    if not isinstance(max_entries, int) or isinstance(max_entries, bool) or max_entries < 1:
        raise ValueError("max_entries must be a positive integer")
    updated = list(records or [])
    updated.append(record)
    return updated[-max_entries:]


def safely_append_question_log_record(
    records,
    answer,
    *,
    selected_alliances=None,
    selected_net_status=None,
    selected_player_count=None,
    total_player_count=None,
    max_entries=100,
    timestamp_utc=None,
    record_builder=build_question_log_record,
    record_appender=append_question_log_record,
):
    """Best-effort question logging that never raises to callers."""
    valid_records = records if isinstance(records, list) else []
    state_error = None if isinstance(records, list) or records is None else "question log state was reset"
    try:
        record = record_builder(
            answer,
            selected_alliances=selected_alliances,
            selected_net_status=selected_net_status,
            selected_player_count=selected_player_count,
            total_player_count=total_player_count,
            timestamp_utc=timestamp_utc,
        )
        updated_records = record_appender(valid_records, record, max_entries=max_entries)
    except Exception as exc:
        return valid_records, f"question logging skipped: {type(exc).__name__}"
    return updated_records, state_error

def _numeric_scope(data, columns):
    working_df = data[list(columns)].copy()
    for column in ["score_gained", "score_lost", "net_score"]:
        if column in working_df.columns:
            working_df[column] = pd.to_numeric(working_df[column], errors="coerce")
    return working_df


def _json_value(value):
    """Convert pandas/numpy scalar containers to JSON-serializable Python values."""
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is pd.NA:
        return None
    return value


def _base_result(intent, status="ok", period=None, guidance_code=None, error_code=None, parameters=None, metrics=None, rankings=None):
    return _json_value({
        "kind": "dashboard_answer",
        "intent": intent,
        "status": status,
        "period": period,
        "parameters": parameters or {},
        "metrics": metrics or {},
        "rankings": rankings or {},
        "guidance_code": guidance_code,
        "error_code": error_code,
    })

def _missing_columns_result(intent, missing, period, parameters=None):
    return _base_result(
        intent,
        status="error",
        period=period,
        error_code="missing_columns",
        parameters={**(parameters or {}), "missing_columns": sorted(missing)},
    )


def calculate_total_net_excluding_alliances(data, excluded_alliances, svs_period=None):
    intent = "alliance_exclusion_total_net"
    required = {"alliance", "player_name", "score_gained", "score_lost", "net_score"}
    missing = required.difference(data.columns)
    params = {"excluded_alliances": [str(name) for name in (excluded_alliances or [])]}
    if missing:
        return _missing_columns_result(intent, missing, svs_period, params)
    if not excluded_alliances:
        return _base_result(intent, "guidance", svs_period, "missing_alliance_name", parameters=params)
    df = _numeric_scope(data, ["alliance", "player_name", "score_gained", "score_lost", "net_score"]).dropna(subset=["alliance", "net_score"])
    if df.empty:
        return _base_result(intent, "guidance", svs_period, "empty_score_scope", parameters=params)
    requested_lookup = {str(name).casefold(): str(name) for name in excluded_alliances}
    in_scope_lookup = {str(name).casefold(): str(name) for name in df["alliance"].dropna().unique()}
    recognized = [in_scope_lookup[key] for key in requested_lookup if key in in_scope_lookup]
    outside = [requested_lookup[key] for key in requested_lookup if key not in in_scope_lookup]
    before_net = df["net_score"].sum()
    before_players = df["player_name"].nunique()
    if not recognized:
        return _base_result(intent, "guidance", svs_period, "alliance_outside_scope", parameters={**params, "recognized_alliances": [], "outside_scope_alliances": outside}, metrics={"before_net_score": before_net, "before_player_count": before_players})
    mask = df["alliance"].astype(str).str.casefold().isin({name.casefold() for name in recognized})
    excluded_df = df[mask]
    remaining_df = df[~mask]
    after_net = remaining_df["net_score"].sum()
    metrics = {
        "before_net_score": before_net,
        "after_net_score": after_net,
        "net_score_change": after_net - before_net,
        "excluded_score_gained": excluded_df["score_gained"].sum(),
        "excluded_score_lost": excluded_df["score_lost"].sum(),
        "excluded_net_score": excluded_df["net_score"].sum(),
        "before_player_count": before_players,
        "after_player_count": remaining_df["player_name"].nunique(),
    }
    return _base_result(intent, "ok", svs_period, parameters={**params, "recognized_alliances": recognized, "outside_scope_alliances": outside}, metrics=metrics)


def calculate_net_vs_positive_ranking(data, svs_period=None):
    intent = "net_vs_positive_ranking"
    missing = {"alliance", "net_score"}.difference(data.columns)
    if missing:
        return _missing_columns_result(intent, missing, svs_period)
    df = data[["alliance", "net_score"]].copy()
    df["net_score"] = pd.to_numeric(df["net_score"], errors="coerce")
    df = df.dropna(subset=["alliance", "net_score"])
    if df.empty:
        return _base_result(intent, "guidance", svs_period, "empty_score_scope")
    if df["alliance"].nunique() < 2:
        return _base_result(intent, "guidance", svs_period, "requires_multiple_alliances", metrics={"alliance_count": df["alliance"].nunique()})
    if "net_status" in data.columns:
        statuses = {str(v).strip().lower() for v in data["net_status"].dropna().unique()}
        if not {"positive", "negative"}.issubset(statuses):
            return _base_result(intent, "guidance", svs_period, "requires_positive_and_negative_status", parameters={"net_statuses": sorted(statuses)})
    analysis = df.groupby("alliance", as_index=False).agg(
        total_net_score=("net_score", "sum"),
        positive_net_score=("net_score", lambda scores: scores[scores > 0].sum()),
        negative_impact=("net_score", lambda scores: scores[scores < 0].abs().sum()),
    )
    analysis["net_rank"] = analysis["total_net_score"].rank(method="min", ascending=False).astype(int)
    analysis["positive_rank"] = analysis["positive_net_score"].rank(method="min", ascending=False).astype(int)
    records = analysis.sort_values(["net_rank", "positive_rank", "alliance"]).to_dict("records")
    top_rows = analysis[analysis["net_rank"] == 1]
    metrics = {"alliance_count": df["alliance"].nunique()}
    rankings = {"alliances": records}
    if len(top_rows) > 1:
        return _base_result(intent, "guidance", svs_period, "tied_top_net_score", metrics=metrics, rankings=rankings)
    top = top_rows.iloc[0]
    metrics.update({"top_net_alliance": str(top["alliance"]), "top_net_score": top["total_net_score"], "top_positive_rank": int(top["positive_rank"])})
    leaders = analysis[analysis["positive_rank"] == 1].sort_values("total_net_score", ascending=False)
    if not leaders.empty:
        leader = leaders.iloc[0]
        metrics.update({"positive_leader_alliance": str(leader["alliance"]), "positive_gap": leader["positive_net_score"] - top["positive_net_score"], "negative_advantage": leader["negative_impact"] - top["negative_impact"], "net_lead": top["total_net_score"] - leader["total_net_score"]})
    return _base_result(intent, "ok", svs_period, metrics=metrics, rankings=rankings)


def calculate_net_score_leader_summary(data, svs_period=None):
    intent = "net_score_leader_summary"
    missing = {"alliance", "net_score"}.difference(data.columns)
    if missing:
        return _missing_columns_result(intent, missing, svs_period)
    df = data[["alliance", "net_score"]].copy()
    df["net_score"] = pd.to_numeric(df["net_score"], errors="coerce")
    df = df.dropna(subset=["alliance", "net_score"])
    if df.empty:
        return _base_result(intent, "guidance", svs_period, "empty_score_scope")
    analysis = df.groupby("alliance", as_index=False).agg(
        total_net_score=("net_score", "sum"),
        positive_contribution=("net_score", lambda scores: scores[scores > 0].sum()),
        negative_impact=("net_score", lambda scores: scores[scores < 0].abs().sum()),
    )
    analysis["net_rank"] = analysis["total_net_score"].rank(method="min", ascending=False).astype(int)
    analysis["positive_rank"] = analysis["positive_contribution"].rank(method="min", ascending=False).astype(int)
    records = analysis.sort_values(["net_rank", "positive_rank", "alliance"]).to_dict("records")
    leaders = analysis[analysis["net_rank"] == 1].sort_values("alliance")
    leader_records = leaders.to_dict("records")
    metrics = {
        "alliance_count": df["alliance"].nunique(),
        "leader_count": len(leader_records),
        "top_net_score": leaders.iloc[0]["total_net_score"],
        "leaders": leader_records,
    }
    if len(leader_records) == 1:
        leader = leader_records[0]
        metrics.update(
            {
                "top_net_alliance": str(leader["alliance"]),
                "top_positive_contribution": leader["positive_contribution"],
                "top_negative_impact": leader["negative_impact"],
                "top_positive_rank": int(leader["positive_rank"]),
            }
        )
    return _base_result(intent, "ok", svs_period, metrics=metrics, rankings={"alliances": records})


def _player_scope(data, include_status=False):
    cols = ["player_name", "score_gained", "score_lost", "net_score"] + (["net_status"] if include_status and "net_status" in data.columns else [])
    return _numeric_scope(data, cols).dropna(subset=["player_name", "net_score"])


def _balance(frame):
    positive = frame.loc[frame["net_score"] > 0, "net_score"].sum()
    negative = frame.loc[frame["net_score"] < 0, "net_score"].abs().sum()
    total = positive + negative
    return {"positive": positive, "negative": negative, "total_magnitude": total, "negative_share": (negative / total * 100 if total > 0 else None)}


def _impact(frame):
    return {"score_gained": frame["score_gained"].sum(), "score_lost": frame["score_lost"].sum(), "net_score": frame["net_score"].sum(), "positive_contribution": frame.loc[frame["net_score"] > 0, "net_score"].sum(), "negative_impact": frame.loc[frame["net_score"] < 0, "net_score"].abs().sum()}


def calculate_exclusion_impact(data, selected_player_names=None, svs_period=None):
    intent = "player_exclusion_impact"
    missing = {"player_name", "score_gained", "score_lost", "net_score"}.difference(data.columns)
    if missing:
        return _missing_columns_result(intent, missing, svs_period)
    df = _player_scope(data)
    if df.empty:
        return _base_result(intent, "guidance", svs_period, "empty_player_scope")
    all_players = sorted(df["player_name"].dropna().unique().tolist())
    selected = all_players if selected_player_names is None else [p for p in selected_player_names if p in set(all_players)]
    selected_df = df[df["player_name"].isin(selected)]
    excluded_df = df[~df["player_name"].isin(selected)]
    before = _impact(df); after = _impact(selected_df)
    changes = {k: after[k] - before[k] for k in before}
    metrics = {"before": before, "after": after, "changes": changes, "before_player_count": df["player_name"].nunique(), "after_player_count": selected_df["player_name"].nunique(), "excluded_player_count": excluded_df["player_name"].nunique(), "positive_removed": before["positive_contribution"] - after["positive_contribution"], "negative_removed": before["negative_impact"] - after["negative_impact"]}
    return _base_result(intent, "ok", svs_period, guidance_code=("no_excluded_players" if metrics["excluded_player_count"] == 0 else None), parameters={"selected_players": selected, "excluded_players": sorted(excluded_df["player_name"].dropna().unique().tolist())}, metrics=metrics)


def classify_negative_share_requested_direction(question):
    """Classify the direction asserted by a negative-share question."""
    normalized = normalize_question_text(question)
    if _has_any_word(normalized, NEGATIVE_INCREASE_TERMS):
        return "increase"
    if _has_any_word(normalized, NEGATIVE_DECREASE_TERMS):
        return "decrease"
    if _has_any_word(normalized, NEGATIVE_NEUTRAL_CHANGE_TERMS):
        return "neutral"
    return "unspecified"


def _actual_share_direction(share_change):
    if share_change > 0.05:
        return "increase"
    if share_change < -0.05:
        return "decrease"
    return "unchanged"


def calculate_negative_percentage_change(data, selected_player_names=None, svs_period=None, requested_direction="unspecified"):
    intent = "negative_share_change"
    missing = {"player_name", "net_score"}.difference(data.columns)
    if missing:
        return _missing_columns_result(intent, missing, svs_period)
    df = _player_scope(data, include_status=True)
    if df.empty:
        return _base_result(intent, "guidance", svs_period, "empty_player_scope")
    if "net_status" in df.columns:
        statuses = {str(v).strip().lower() for v in df["net_status"].dropna().unique()}
        if not {"positive", "negative"}.issubset(statuses):
            return _base_result(intent, "guidance", svs_period, "requires_positive_and_negative_status", parameters={"net_statuses": sorted(statuses)})
    all_players = sorted(df["player_name"].dropna().unique().tolist())
    selected = all_players if selected_player_names is None else [p for p in selected_player_names if p in set(all_players)]
    selected_df = df[df["player_name"].isin(selected)]
    excluded_df = df[~df["player_name"].isin(selected)]
    before = _balance(df); after = _balance(selected_df)
    metrics = {"before": before, "after": after, "excluded_player_count": excluded_df["player_name"].nunique(), "excluded_players": sorted(excluded_df["player_name"].dropna().unique().tolist())}
    if before["negative_share"] is not None and after["negative_share"] is not None:
        metrics.update({"share_change": after["negative_share"] - before["negative_share"], "positive_removed": before["positive"] - after["positive"], "negative_removed": before["negative"] - after["negative"]})
    return _base_result(intent, "ok", svs_period, guidance_code=("no_excluded_players" if metrics["excluded_player_count"] == 0 else None), parameters={"selected_players": selected, "excluded_players": metrics["excluded_players"], "requested_direction": requested_direction}, metrics=metrics)


def _filter_by_alliance_names(df, alliance_names):
    requested = {str(n).casefold(): str(n) for n in (alliance_names or [])}
    lookup = {str(n).casefold(): str(n) for n in df["alliance"].dropna().unique()}
    matched = [lookup[key] for key in requested if key in lookup]
    outside = [requested[key] for key in requested if key not in lookup]
    if matched:
        df = df[df["alliance"].astype(str).str.casefold().isin({n.casefold() for n in matched})]
    return df, matched, outside


def calculate_player_net_score_leader(data, svs_period=None, alliance_names=None):
    intent = "player_net_score_leader"
    required = {"alliance", "player_name", "score_gained", "score_lost", "net_score"}
    missing = required.difference(data.columns)
    params = {"alliance_names": [str(n) for n in (alliance_names or [])]}
    if missing:
        return _missing_columns_result(intent, missing, svs_period, params)
    df = _numeric_scope(data, ["alliance", "player_name", "score_gained", "score_lost", "net_score"]).dropna(subset=["alliance", "player_name"])
    if alliance_names:
        df, matched, outside = _filter_by_alliance_names(df, alliance_names)
        params.update({"matched_alliances": matched, "outside_scope_alliances": outside})
        if outside:
            return _base_result(intent, "guidance", svs_period, "alliance_outside_scope", parameters=params)
    df = df.dropna(subset=["net_score"])
    if df.empty:
        return _base_result(intent, "guidance", svs_period, "empty_player_scope", parameters=params)
    summary = df.groupby(["alliance", "player_name"], as_index=False).agg(score_gained=("score_gained", "sum"), score_lost=("score_lost", "sum"), net_score=("net_score", "sum"))
    if summary["net_score"].isna().all():
        return _base_result(intent, "guidance", svs_period, "empty_player_scope", parameters=params)
    summary = summary.sort_values(["net_score", "score_gained", "player_name"], ascending=[False, False, True]).reset_index(drop=True)
    summary["rank"] = summary["net_score"].rank(method="min", ascending=False).astype(int)
    records = summary[["rank", "player_name", "alliance", "score_gained", "score_lost", "net_score"]].to_dict("records")
    leaders = [row for row in records if row["rank"] == 1]
    metrics = {"leader_count": len(leaders), "top_net_score": leaders[0]["net_score"], "player_count": len(records), "leaders": leaders}
    if len(leaders) == 1:
        top = leaders[0]
        metrics.update({"top_player": top["player_name"], "top_alliance": top["alliance"], "top_score_gained": top["score_gained"], "top_score_lost": top["score_lost"]})
    return _base_result(intent, "ok", svs_period, parameters=params, metrics=metrics, rankings={"players": records})


def calculate_top_contributors(data, svs_period=None, alliance_names=None):
    intent = "top_contributors"
    missing = {"alliance", "player_name", "score_gained", "score_lost", "net_score"}.difference(data.columns)
    params = {"alliance_names": [str(n) for n in (alliance_names or [])]}
    if missing:
        return _missing_columns_result(intent, missing, svs_period, params)
    df = _numeric_scope(data, ["alliance", "player_name", "score_gained", "score_lost", "net_score"]).dropna(subset=["alliance", "player_name", "net_score"])
    if alliance_names:
        requested = [str(n).casefold() for n in alliance_names]
        lookup = {str(n).casefold(): str(n) for n in df["alliance"].dropna().unique()}
        matched = [lookup[n] for n in requested if n in lookup]
        if not matched:
            return _base_result(intent, "guidance", svs_period, "alliance_outside_scope", parameters={**params, "matched_alliances": []})
        df = df[df["alliance"].astype(str).str.casefold().isin({n.casefold() for n in matched})]
        params["matched_alliances"] = matched
    if df.empty:
        return _base_result(intent, "guidance", svs_period, "empty_player_scope", parameters=params)
    summary = df.groupby(["alliance", "player_name"], as_index=False).agg(score_gained=("score_gained", "sum"), score_lost=("score_lost", "sum"), net_score=("net_score", "sum"))
    alliances = sorted(summary["alliance"].dropna().astype(str).unique().tolist())
    top_n = 5 if len(alliances) == 1 else 3
    groups = []
    for alliance in alliances:
        players = summary[summary["alliance"].astype(str) == alliance].sort_values(["net_score", "score_gained", "player_name"], ascending=[False, False, True])
        positive_players = players[players["net_score"] > 0]
        ranked = (positive_players if not positive_players.empty else players).head(top_n)
        positive_total = positive_players["net_score"].sum()
        groups.append({"alliance": alliance, "positive_total": positive_total, "net_total": players["net_score"].sum(), "top_n": top_n, "ranking_description": ("positive contributors by net score" if not positive_players.empty else "players with the highest net scores; no player has a positive net score in this scope"), "players": [{**row._asdict(), "share_of_positive": (row.net_score / positive_total * 100 if row.net_score > 0 and positive_total > 0 else None)} for row in ranked.itertuples(index=False)]})
    return _base_result(intent, "ok", svs_period, parameters=params, metrics={"alliance_count": len(alliances), "top_n": top_n}, rankings={"alliances": groups})

def _attach_routing(result, contract):
    result["routing"] = contract
    return result


def execute_dashboard_intent(contract, data, svs_period=None, selected_player_names=None, known_alliance_names=None):
    """Validate and execute a dashboard intent contract."""
    contract = validate_intent_contract(contract)
    intent = contract["intent"]
    params = contract["parameters"]

    if contract["match_status"] == "unsupported":
        return _attach_routing(
            _base_result("unsupported_question", "guidance", svs_period, contract["guidance_code"]),
            contract,
        )
    if contract["match_status"] == "needs_clarification":
        result_params = {}
        if intent == "alliance_exclusion_total_net":
            result_params["excluded_alliances"] = params.get("excluded_alliances", [])
            if known_alliance_names is not None:
                result_params["available_alliances"] = list(map(str, known_alliance_names))
        return _attach_routing(
            _base_result(intent, "guidance", svs_period, contract["guidance_code"], parameters=result_params),
            contract,
        )

    if intent == "net_vs_positive_ranking":
        result = calculate_net_vs_positive_ranking(data, svs_period)
    elif intent == "player_exclusion_impact":
        result = calculate_exclusion_impact(data, selected_player_names, svs_period)
    elif intent == "negative_share_change":
        result = calculate_negative_percentage_change(
            data,
            selected_player_names,
            svs_period,
            params.get("requested_direction", "unspecified"),
        )
    elif intent == "top_contributors":
        result = calculate_top_contributors(data, svs_period, alliance_names=params.get("alliance_names") or None)
    elif intent == "player_net_score_leader":
        result = calculate_player_net_score_leader(data, svs_period, alliance_names=params.get("alliance_names") or None)
    elif intent == "alliance_exclusion_total_net":
        result = calculate_total_net_excluding_alliances(data, params.get("excluded_alliances", []), svs_period)
    elif intent == "net_score_leader_summary":
        result = calculate_net_score_leader_summary(data, svs_period)
    else:
        raise ValueError(f"unknown intent: {intent}")
    return _attach_routing(result, contract)


def route_dashboard_question_hybrid(
    question,
    known_alliance_names=None,
    *,
    ai_enabled=False,
    ai_extractor=None,
):
    """Route rule-first, with an optional provider-independent AI fallback."""
    rule_contract = validate_intent_contract(
        route_dashboard_question(question, known_alliance_names)
    )
    if rule_contract["match_status"] != "unsupported" or not ai_enabled:
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
        api_contract = ai_extractor(question, known_alliance_names or [])
        api_contract = validate_intent_contract(api_contract)
    except Exception as exc:
        diagnostic_code = getattr(exc, "diagnostic_code", "api_invalid_output")
        if diagnostic_code not in {
            "api_unavailable",
            "api_refusal",
            "api_incomplete",
            "api_invalid_output",
        }:
            diagnostic_code = "api_invalid_output"
        return {
            "contract": rule_contract,
            "ai_attempted": True,
            "ai_succeeded": False,
            "diagnostic_code": diagnostic_code,
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
):
    """Route a question and return a structured Ask Dashboard answer."""
    if known_alliance_names is None:
        known_alliance_names = data["alliance"].dropna().unique().tolist() if "alliance" in data.columns else []
    if intent_router is None:
        contract = route_dashboard_question(question, known_alliance_names)
        routing_result = None
    else:
        routing_result = intent_router(question, known_alliance_names)
        contract = routing_result["contract"] if isinstance(routing_result, dict) else routing_result
    validated_contract = validate_intent_contract(contract)
    mentioned_alliances = extract_alliance_names_from_question(question, known_alliance_names)
    common = {"question": question, "mentioned_alliances": mentioned_alliances}
    result = execute_dashboard_intent(
        validated_contract,
        data,
        svs_period,
        selected_player_names,
        known_alliance_names,
    )
    result["parameters"] = {**common, **result.get("parameters", {})}
    if routing_result is not None and isinstance(routing_result, dict):
        result["routing_diagnostics"] = {
            "ai_attempted": bool(routing_result.get("ai_attempted", False)),
            "ai_succeeded": bool(routing_result.get("ai_succeeded", False)),
            "diagnostic_code": routing_result.get("diagnostic_code"),
        }
    return result

def _period_text(period, prefix=" in ", bold=False):
    if not period:
        return ""
    return f"{prefix}{'**' if bold else ''}{period}{'**' if bold else ''}"


def _status_message(answer):
    intent = answer.get("intent")
    code = answer.get("guidance_code") or answer.get("error_code")
    params = answer.get("parameters", {})
    metrics = answer.get("metrics", {})
    missing = params.get("missing_columns", [])
    if code == "missing_columns":
        subject = "calculation" if intent == "alliance_exclusion_total_net" else "explanation"
        return f"This {subject} cannot be completed because the current data is missing: {', '.join(missing)}."
    if code == "empty_score_scope":
        return "There is no score data in the current filter scope. Select at least one alliance and net-status option, then try again."
    if code == "empty_player_scope":
        return "There is no player score data in the current filter scope. Select at least one alliance and a net-status option, then try again."
    if code == "requires_multiple_alliances":
        return "This comparison needs at least two alliances in the current filter scope. Select more alliances and try again."
    if code == "requires_positive_and_negative_status":
        if intent == "negative_share_change":
            return "This question compares the positive and negative sides, but the current Net Status filter does not include both Positive and Negative. Select both statuses and try again."
        return "This question is intended to compare positive contribution with negative impact, but the current Net Status filter does not include both Positive and Negative. Select both statuses to get the full explanation."
    if code == "missing_alliance_name":
        available = params.get("available_alliances")
        if available is not None:
            return "I understood that you want a total net score after excluding an alliance, but I could not identify the alliance name. Available alliance names for this SVS period are: " + f"**{', '.join(map(str, available))}**."
        return "I understood that you want to exclude an alliance, but I could not identify its name. Include an alliance name in the question, for example: **What is the total net score without TDA?**"
    if code == "alliance_outside_scope":
        names = params.get("outside_scope_alliances") or params.get("alliance_names") or []
        named = ", ".join(f"**{name}**" for name in names)
        if intent in {"top_contributors", "player_net_score_leader"}:
            return f"I recognized {named}, but it is not included in the current alliance filter. Add it in the sidebar, then ask again."
        before_net = metrics.get("before_net_score", 0)
        return f"{named} is not included in the current alliance filter, so excluding it does not change the current total net score of **{format_signed_score(before_net)}**. Add the alliance to the sidebar selection first if you want a before-and-after comparison."
    if code == "tied_top_net_score":
        tied = [row["alliance"] for row in answer.get("rankings", {}).get("alliances", []) if row.get("net_rank") == 1]
        score = next((row.get("total_net_score") for row in answer.get("rankings", {}).get("alliances", []) if row.get("net_rank") == 1), 0)
        return f"The current filters produce a tie for first place in total net score: {', '.join(tied)}, each with {format_score(score)}. Because there is no single top net-score alliance, the premise of this question does not currently apply."
    if code == "unsupported_question":
        return "I could not map that question to a supported dashboard analysis yet. This version uses rule-based matching rather than an AI API. Try one of these forms:\n\n- **What is the total net score without TDA?**\n- **Who contributed most in SnS?**\n- **How did excluding selected players change the result?**\n- **Why did the negative share rise?**\n- **Why is the net-score leader not first in positive contribution?**"
    return None


def _render_alliance_exclusion(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance
    params = answer["parameters"]
    metrics = answer["metrics"]
    alliances = params.get("recognized_alliances", params.get("excluded_alliances", []))
    alliance_text = ", ".join(f"**{name}**" for name in alliances)
    excluded_net = metrics["excluded_net_score"]
    if excluded_net < 0:
        interpretation = "The total improves because the excluded alliance group had a negative net contribution in this scope."
    elif excluded_net > 0:
        interpretation = "The total decreases because the excluded alliance group had a positive net contribution in this scope."
    else:
        interpretation = "The total does not change because the excluded alliance group had a net contribution of zero in this scope."
    outside = params.get("outside_scope_alliances", [])
    outside_note = ""
    if outside:
        outside_note = "\n\nThe following named alliance(s) were already outside the current filter and therefore had no additional effect: " + ", ".join(f"**{name}**" for name in outside) + "."
    return (
        f"Within the current dashboard filters{_period_text(answer.get('period'), ' for ', True)}, excluding {alliance_text} changes total net score from "
        f"**{format_signed_score(metrics['before_net_score'])}** to **{format_signed_score(metrics['after_net_score'])}** "
        f"(**{format_signed_score(metrics['net_score_change'])}**).\n\n"
        f"The excluded alliance group contributed:\n"
        f"- Score gained: **{format_score(metrics['excluded_score_gained'])}**\n"
        f"- Score lost: **{format_score(metrics['excluded_score_lost'])}**\n"
        f"- Net score: **{format_signed_score(metrics['excluded_net_score'])}**\n\n"
        f"Players remaining: **{metrics['after_player_count']}/{metrics['before_player_count']}**. {interpretation}{outside_note}"
    )


def _render_net_vs_positive(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance
    rows = answer.get("rankings", {}).get("alliances", [])
    metrics = answer["metrics"]
    top = next(row for row in rows if row.get("alliance") == metrics.get("top_net_alliance"))
    if top.get("positive_rank") == 1:
        return f"The premise does not match the current filtered data{_period_text(answer.get('period'), ' for ')}. **{top['alliance']}** ranks first in both total net score ({format_score(top['total_net_score'])}) and positive contribution ({format_score(top['positive_net_score'])})."
    leader = next(row for row in rows if row.get("alliance") == metrics.get("positive_leader_alliance"))
    rank_statement = "second" if top.get("positive_rank") == 2 else f"#{top.get('positive_rank')}, not second"
    return (
        f"Under the current sidebar filters{_period_text(answer.get('period'))}, **{top['alliance']}** ranks first in total net score with **{format_score(top['total_net_score'])}**, while it ranks {rank_statement} in positive contribution with **{format_score(top['positive_net_score'])}**.\n\n"
        f"**{leader['alliance']}** leads positive contribution with **{format_score(leader['positive_net_score'])}**, which is **{format_score(metrics['positive_gap'])}** more than {top['alliance']}. However, {leader['alliance']}'s negative impact is **{format_score(leader['negative_impact'])}**, compared with **{format_score(top['negative_impact'])}** for {top['alliance']}. That gives {top['alliance']} a **{format_score(metrics['negative_advantage'])}** advantage from losing fewer points.\n\n"
        f"The lower negative impact offsets the smaller positive contribution, leaving {top['alliance']} ahead of {leader['alliance']} by **{format_score(metrics['net_lead'])}** in total net score. Here, positive contribution is the sum of positive player net scores, and total net score equals positive contribution minus negative impact."
    )


def _render_net_score_leader_summary(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance
    metrics = answer["metrics"]
    period_text = _period_text(answer.get("period"))
    leaders = metrics.get("leaders", [])
    if metrics.get("leader_count", 0) > 1:
        names = ", ".join(f"**{leader['alliance']}**" for leader in leaders)
        details = "\n".join(
            f"- **{leader['alliance']}**: total net **{format_signed_score(leader['total_net_score'])}**, "
            f"positive contribution **{format_score(leader['positive_contribution'])}**, "
            f"negative impact **{format_score(leader['negative_impact'])}**, "
            f"positive-contribution rank **#{leader['positive_rank']}**"
            for leader in leaders
        )
        return (
            f"Under the current sidebar filters{period_text}, total net score is tied for first between {names} "
            f"at **{format_signed_score(metrics['top_net_score'])}**.\n\n"
            f"{details}\n\n"
            "They lead because their positive contribution minus negative impact produces the highest total net score in the current filter scope."
        )
    leader = leaders[0]
    return (
        f"Under the current sidebar filters{period_text}, **{leader['alliance']}** leads total net score with "
        f"**{format_signed_score(leader['total_net_score'])}**.\n\n"
        f"- **Positive contribution:** {format_score(leader['positive_contribution'])}\n"
        f"- **Negative impact:** {format_score(leader['negative_impact'])}\n"
        f"- **Positive-contribution rank:** #{leader['positive_rank']}\n\n"
        f"It leads because its positive contribution minus negative impact produces the highest total net score under the current filters."
    )


def _excluded_text(players):
    if len(players) <= 5:
        return ", ".join(map(str, players))
    return ", ".join(map(str, players[:5])) + f", and {len(players) - 5} others"


def _render_exclusion_impact(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance
    m = answer["metrics"]
    before = m["before"]
    after = m["after"]
    changes = m["changes"]
    period_text = _period_text(answer.get("period"))
    if m["excluded_player_count"] == 0:
        return f"No players are currently excluded from the filtered group{period_text}. The before-and-after results are therefore identical: **{m['before_player_count']} players** with a total net score of **{format_score(before['net_score'])}**. Remove at least one player in the Player Selection Insight tab to compare the impact."
    net_change = changes["net_score"]
    if net_change > 0:
        outcome = f"The total net score **improved by {format_score(net_change)}**. The exclusions removed **{format_score(m['negative_removed'])}** of negative impact but only **{format_score(m['positive_removed'])}** of positive contribution, so the reduction in losses was greater than the reduction in gains."
    elif net_change < 0:
        outcome = f"The total net score **decreased by {format_score(abs(net_change))}**. The exclusions removed **{format_score(m['positive_removed'])}** of positive contribution but only **{format_score(m['negative_removed'])}** of negative impact, so more useful contribution was removed than harmful impact."
    else:
        outcome = f"The total net score did not change. The removed positive contribution (**{format_score(m['positive_removed'])}**) and removed negative impact (**{format_score(m['negative_removed'])}**) offset each other exactly."
    return (
        f"After the current exclusions{period_text}, the analysis includes **{m['after_player_count']} of {m['before_player_count']} players**. **Excluded:** {_excluded_text(answer['parameters'].get('excluded_players', []))}.\n\n"
        f"- **Score gained:** {format_score(before['score_gained'])} → {format_score(after['score_gained'])} ({format_signed_score(changes['score_gained'])})\n"
        f"- **Score lost:** {format_score(before['score_lost'])} → {format_score(after['score_lost'])} ({format_signed_score(changes['score_lost'])})\n"
        f"- **Positive contribution:** {format_score(before['positive_contribution'])} → {format_score(after['positive_contribution'])} ({format_signed_score(changes['positive_contribution'])})\n"
        f"- **Negative impact:** {format_score(before['negative_impact'])} → {format_score(after['negative_impact'])} ({format_signed_score(changes['negative_impact'])})\n"
        f"- **Total net score:** {format_score(before['net_score'])} → {format_score(after['net_score'])} ({format_signed_score(changes['net_score'])})\n\n{outcome}"
    )


def _render_negative_share(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance
    m = answer["metrics"]
    before = m["before"]
    after = m["after"]
    period_text = _period_text(answer.get("period"))
    if before.get("negative_share") is None:
        return "The negative percentage cannot be calculated because the current filtered group has no positive or negative net-score magnitude."
    if m["excluded_player_count"] == 0:
        return f"No players are currently excluded from the filtered group{period_text}. The negative share is unchanged at **{before['negative_share']:.1f}%**. Remove at least one player in the Player Selection Insight tab to create a before-and-after comparison."
    if after.get("negative_share") is None:
        return f"After the current exclusions{period_text}, no score magnitude remains in the selected group, so an after-exclusion negative percentage cannot be calculated."
    share_change = m["share_change"]
    actual_direction = _actual_share_direction(share_change)
    requested_direction = answer.get("parameters", {}).get("requested_direction", "unspecified")
    premise_mismatch = requested_direction in {"increase", "decrease"} and actual_direction != requested_direction
    positive_removed = m["positive_removed"]
    negative_removed = m["negative_removed"]
    positive_rate = positive_removed / before["positive"] * 100 if before["positive"] > 0 else 0
    negative_rate = negative_removed / before["negative"] * 100 if before["negative"] > 0 else 0
    if share_change > 0.05:
        prefix = "The premise does not match the current selection: the negative share" if premise_mismatch else "The negative share"
        direction = f"{prefix} **increased by {share_change:.1f} percentage points**, from **{before['negative_share']:.1f}%** to **{after['negative_share']:.1f}%**."
        reason = f"This happened because the exclusions removed a larger proportion of positive contribution than negative impact. Positive contribution fell by **{positive_rate:.1f}%**, while negative impact fell by **{negative_rate:.1f}%**. " + ("Although the raw negative impact also decreased, it became a larger share of the smaller remaining total." if negative_removed > 0 else "The raw negative impact did not increase; it stayed the same but became a larger share of the smaller remaining total.")
    elif share_change < -0.05:
        prefix = "The premise does not match the current selection: the negative share" if premise_mismatch else "The negative share"
        direction = f"{prefix} **decreased by {abs(share_change):.1f} percentage points**, from **{before['negative_share']:.1f}%** to **{after['negative_share']:.1f}%**."
        reason = f"The exclusions removed a larger proportion of negative impact than positive contribution. Negative impact fell by **{negative_rate:.1f}%**, while positive contribution fell by **{positive_rate:.1f}%**."
    else:
        prefix = "The premise does not match the current selection: the negative share" if premise_mismatch else "The negative share"
        direction = f"{prefix} is effectively unchanged at **{after['negative_share']:.1f}%** ({share_change:+.1f} percentage points)."
        reason = "Positive contribution and negative impact changed in nearly the same proportion, so the balance between the two sides remained stable."
    return (
        f"After excluding **{m['excluded_player_count']} player(s)**{period_text} — **{_excluded_text(answer['parameters'].get('excluded_players', []))}** — {direction}\n\n"
        f"- **Positive contribution:** {format_score(before['positive'])} → {format_score(after['positive'])} (removed {format_score(positive_removed)}, {positive_rate:.1f}%)\n"
        f"- **Negative impact:** {format_score(before['negative'])} → {format_score(after['negative'])} (removed {format_score(negative_removed)}, {negative_rate:.1f}%)\n\n{reason}\n\nNegative percentage = negative impact ÷ (positive contribution + negative impact)."
    )


def _render_player_net_score_leader(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance
    metrics = answer["metrics"]
    players = answer.get("rankings", {}).get("players", [])
    period_text = _period_text(answer.get("period"))
    params = answer.get("parameters", {})
    scope_names = params.get("matched_alliances") or params.get("alliance_names") or []
    scope_text = f" for {'/'.join(map(str, scope_names))}" if scope_names else ""
    if metrics.get("leader_count", 0) > 1:
        leaders = metrics.get("leaders", [])
        names = ", ".join(f"**{row['player_name']}** ({row['alliance']})" for row in leaders)
        details = "\n".join(f"- **{row['player_name']}** — alliance **{row['alliance']}**, gained **{format_score(row['score_gained'])}**, lost **{format_score(row['score_lost'])}**, net **{format_signed_score(row['net_score'])}**" for row in leaders)
        return f"Under the current sidebar filters{period_text}{scope_text}, these players are tied for first by net score at **{format_signed_score(metrics['top_net_score'])}**: {names}.\n\n{details}"
    top = next(row for row in players if row.get("rank") == 1)
    return (
        f"Under the current sidebar filters{period_text}{scope_text}, **{top['player_name']}** has the highest net score with **{format_signed_score(top['net_score'])}**.\n\n"
        f"Alliance: **{top['alliance']}**\n"
        f"Score gained: **{format_score(top['score_gained'])}**\n"
        f"Score lost: **{format_score(top['score_lost'])}**\n"
        f"Net-score rank: **#{top['rank']}**"
    )


def _render_top_contributors(answer):
    guidance = _status_message(answer)
    if guidance:
        return guidance
    groups = answer.get("rankings", {}).get("alliances", [])
    period_text = _period_text(answer.get("period"), " for ", True)
    single = len(groups) == 1
    top_n = answer.get("metrics", {}).get("top_n", 5 if single else 3)
    if single:
        intro = f"The strongest contributors{period_text} are ranked by **player net score**."
    else:
        intro = f"Because **{len(groups)} alliances** are selected{period_text}, the dashboard shows the top **{top_n}** contributors within each alliance. Players are ranked by **player net score**."
    sections = []
    for group in groups:
        lines = [f"**{group['alliance']}** — {group['ranking_description']}:"]
        for rank, row in enumerate(group.get("players", []), start=1):
            details = f"net **{format_signed_score(row['net_score'])}** (gained {format_score(row['score_gained'])}, lost {format_score(row['score_lost'])})"
            if row.get("share_of_positive") is not None:
                details += f", **{row['share_of_positive']:.1f}%** of the alliance's positive contribution"
            lines.append(f"{rank}. **{row['player_name']}** — {details}")
        if group.get("positive_total", 0) > 0:
            ranked_total = sum(row["net_score"] for row in group.get("players", []) if row["net_score"] > 0)
            lines.append(f"The listed player(s) account for **{ranked_total / group['positive_total'] * 100:.1f}%** of this alliance's positive contribution in the current filter scope.")
        lines.append(f"Alliance total net score in this scope: **{format_signed_score(group['net_total'])}**.")
        sections.append("\n".join(lines))
    return intro + "\n\n" + "\n\n".join(sections)


def render_dashboard_answer(answer):
    """Render a structured Ask Dashboard answer as Markdown."""
    if not isinstance(answer, dict):
        return str(answer)
    renderers = {
        "alliance_exclusion_total_net": _render_alliance_exclusion,
        "net_vs_positive_ranking": _render_net_vs_positive,
        "player_exclusion_impact": _render_exclusion_impact,
        "negative_share_change": _render_negative_share,
        "top_contributors": _render_top_contributors,
        "net_score_leader_summary": _render_net_score_leader_summary,
        "player_net_score_leader": _render_player_net_score_leader,
    }
    renderer = renderers.get(answer.get("intent"))
    if renderer:
        return renderer(answer)
    return _status_message(answer) or ""

def answer_dashboard_question(*args, **kwargs):
    """Return the rendered Markdown answer for backward-compatible callers."""
    return render_dashboard_answer(calculate_dashboard_answer(*args, **kwargs))
