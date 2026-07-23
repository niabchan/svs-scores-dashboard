"""OpenAI-backed intent extraction for Ask Dashboard.

This module only classifies a question into the existing intent contract. It does
not calculate scores, render answers, or import dashboard data libraries.
"""

import json

from ask_dashboard import (
    INTENT_CONTRACT_SCHEMA_VERSION,
    NEGATIVE_SHARE_DIRECTIONS,
    SUPPORTED_DASHBOARD_INTENTS,
    validate_intent_contract,
)

AI_DIAGNOSTIC_API_UNAVAILABLE = "api_unavailable"
AI_DIAGNOSTIC_API_REFUSAL = "api_refusal"
AI_DIAGNOSTIC_API_INCOMPLETE = "api_incomplete"
AI_DIAGNOSTIC_API_INVALID_OUTPUT = "api_invalid_output"

AI_INTENT_CANDIDATE_FIELDS = {
    "intent",
    "requested_direction",
    "alliance_names",
    "excluded_alliances",
    "match_status",
    "guidance_code",
    "confidence",
}

GUIDANCE_CODES = [None, "missing_alliance_name", "unsupported_question"]
AI_INTENT_CANDIDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": sorted(SUPPORTED_DASHBOARD_INTENTS)},
        "requested_direction": {"type": "string", "enum": sorted(NEGATIVE_SHARE_DIRECTIONS)},
        "alliance_names": {"type": "array", "items": {"type": "string"}},
        "excluded_alliances": {"type": "array", "items": {"type": "string"}},
        "match_status": {"type": "string", "enum": ["matched", "needs_clarification", "unsupported"]},
        "guidance_code": {"type": ["string", "null"], "enum": GUIDANCE_CODES},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": sorted(AI_INTENT_CANDIDATE_FIELDS),
    "additionalProperties": False,
}

SUPPORTED_INTENT_DEFINITIONS = {
    "net_vs_positive_ranking": "Explain why the top net-score alliance may not rank first for positive contribution.",
    "player_exclusion_impact": "Explain what changed after excluding currently selected players.",
    "negative_share_change": "Explain an increase, decrease, neutral change, or unspecified change in negative share/percentage/ratio.",
    "top_contributors": "Identify top contributing players overall or within named alliances.",
    "alliance_exclusion_total_net": "Calculate total net score after excluding one or more named alliances.",
    "net_score_leader_summary": "Summarize which alliance leads total net score.",
    "player_net_score_leader": "Identify the player with the highest net score overall or within named alliances.",
    "unsupported_question": "No supported Ask Dashboard intent applies.",
}


class OpenAIIntentError(Exception):
    """Safe exception carrying only a diagnostic code."""

    def __init__(self, diagnostic_code):
        super().__init__(diagnostic_code)
        self.diagnostic_code = diagnostic_code


def build_openai_client_options(api_key):
    """Return bounded OpenAI client options without constructing a client."""
    return {"api_key": api_key, "timeout": 10.0, "max_retries": 0}


def _field_names(fields):
    return ", ".join(sorted(str(field) for field in fields))


def _validate_candidate_shape(candidate):
    if not isinstance(candidate, dict):
        raise ValueError("AI intent candidate must be a dictionary")
    fields = set(candidate)
    missing = AI_INTENT_CANDIDATE_FIELDS.difference(fields)
    if missing:
        raise ValueError(f"missing AI intent candidate field(s): {_field_names(missing)}")
    unknown = fields.difference(AI_INTENT_CANDIDATE_FIELDS)
    if unknown:
        raise ValueError(f"unknown AI intent candidate field(s): {_field_names(unknown)}")
    if not isinstance(candidate["intent"], str):
        raise ValueError("AI intent candidate intent must be a string")
    if not isinstance(candidate["requested_direction"], str):
        raise ValueError("AI intent candidate requested_direction must be a string")
    for field in ["alliance_names", "excluded_alliances"]:
        if not isinstance(candidate[field], list) or not all(isinstance(name, str) for name in candidate[field]):
            raise ValueError(f"AI intent candidate {field} must be a list of strings")
    if not isinstance(candidate["match_status"], str):
        raise ValueError("AI intent candidate match_status must be a string")
    if candidate["guidance_code"] is not None and not isinstance(candidate["guidance_code"], str):
        raise ValueError("AI intent candidate guidance_code must be a string or None")
    if isinstance(candidate["confidence"], bool) or not isinstance(candidate["confidence"], (int, float)):
        raise ValueError("AI intent candidate confidence must be numeric")


def canonicalize_candidate_alliances(candidate, known_alliance_names):
    """Return a copy with AI-extracted alliances verified against known names."""
    _validate_candidate_shape(candidate)
    canonical_by_casefold = {str(name).casefold(): str(name) for name in (known_alliance_names or [])}
    normalized = dict(candidate)
    for field in ["alliance_names", "excluded_alliances"]:
        canonical_values = []
        for name in candidate[field]:
            canonical = canonical_by_casefold.get(name.casefold())
            if canonical is None:
                raise ValueError("AI intent candidate alliance name is outside the known allowlist")
            canonical_values.append(canonical)
        normalized[field] = canonical_values
    return normalized


def build_api_intent_contract(candidate):
    """Build and validate an API-sourced intent contract from a plain candidate."""
    _validate_candidate_shape(candidate)

    intent = candidate.get("intent")
    parameters = {}
    if intent == "negative_share_change":
        parameters = {"requested_direction": candidate.get("requested_direction")}
    elif intent in {"top_contributors", "player_net_score_leader"}:
        parameters = {"alliance_names": candidate.get("alliance_names")}
    elif intent == "alliance_exclusion_total_net":
        parameters = {"excluded_alliances": candidate.get("excluded_alliances")}

    contract = {
        "schema_version": INTENT_CONTRACT_SCHEMA_VERSION,
        "intent": intent,
        "parameters": parameters,
        "source": "api",
        "confidence": candidate.get("confidence"),
        "match_status": candidate.get("match_status"),
        "guidance_code": candidate.get("guidance_code"),
    }
    try:
        return validate_intent_contract(contract)
    except ValueError as exc:
        raise ValueError("invalid AI intent contract") from exc


def _response_text(response):
    text = getattr(response, "output_text", None)
    if text:
        return text
    output = getattr(response, "output", None) or []
    for item in output:
        contents = getattr(item, "content", None) or []
        for content in contents:
            refusal = getattr(content, "refusal", None)
            if refusal:
                raise OpenAIIntentError(AI_DIAGNOSTIC_API_REFUSAL)
            content_text = getattr(content, "text", None)
            if content_text:
                return content_text
    raise OpenAIIntentError(AI_DIAGNOSTIC_API_INVALID_OUTPUT)


def _ensure_complete_response(response):
    status = getattr(response, "status", None)
    if status and status != "completed":
        if status in {"incomplete", "cancelled", "failed"}:
            raise OpenAIIntentError(AI_DIAGNOSTIC_API_INCOMPLETE)
        raise OpenAIIntentError(AI_DIAGNOSTIC_API_INVALID_OUTPUT)
    incomplete_details = getattr(response, "incomplete_details", None)
    if incomplete_details:
        raise OpenAIIntentError(AI_DIAGNOSTIC_API_INCOMPLETE)


def _request_payload(question, known_alliance_names):
    known_alliance_names = [str(name) for name in (known_alliance_names or [])]
    developer_instruction = (
        "Classify only among the supported Ask Dashboard intents. Never calculate scores. "
        "Never invent alliance names outside the supplied known_alliance_names list. "
        "Use unsupported_question when no supported intent applies. Use needs_clarification "
        "only for alliance_exclusion_total_net with a missing alliance name. Do not answer "
        "the user's question in prose. Return only the structured extraction candidate."
    )
    user_payload = {
        "question": str(question),
        "supported_intent_definitions": SUPPORTED_INTENT_DEFINITIONS,
        "parameter_rules": {
            "negative_share_change": ["requested_direction"],
            "top_contributors": ["alliance_names"],
            "player_net_score_leader": ["alliance_names"],
            "alliance_exclusion_total_net": ["excluded_alliances"],
            "other_intents": [],
        },
        "known_alliance_names": known_alliance_names,
    }
    return [
        {"role": "developer", "content": developer_instruction},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
    ]


def extract_intent_contract_with_openai(question, known_alliance_names, *, client, model):
    """Extract a validated intent contract with one OpenAI Responses API call."""
    if client is None or not model:
        raise OpenAIIntentError(AI_DIAGNOSTIC_API_UNAVAILABLE)
    try:
        response = client.responses.create(
            model=model,
            input=_request_payload(question, known_alliance_names),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "ask_dashboard_intent_candidate",
                    "strict": True,
                    "schema": AI_INTENT_CANDIDATE_SCHEMA,
                }
            },
            store=False,
        )
        _ensure_complete_response(response)
        text = _response_text(response)
        try:
            candidate = json.loads(text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise OpenAIIntentError(AI_DIAGNOSTIC_API_INVALID_OUTPUT) from exc
        try:
            candidate = canonicalize_candidate_alliances(candidate, known_alliance_names)
            return build_api_intent_contract(candidate)
        except ValueError as exc:
            raise OpenAIIntentError(AI_DIAGNOSTIC_API_INVALID_OUTPUT) from exc
    except OpenAIIntentError:
        raise
    except TimeoutError as exc:
        raise OpenAIIntentError(AI_DIAGNOSTIC_API_UNAVAILABLE) from exc
    except Exception as exc:
        raise OpenAIIntentError(AI_DIAGNOSTIC_API_UNAVAILABLE) from exc
