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
    "required": [
        "intent",
        "requested_direction",
        "alliance_names",
        "excluded_alliances",
        "match_status",
        "guidance_code",
        "confidence",
    ],
    "additionalProperties": False,
}

SUPPORTED_INTENT_DEFINITIONS = {
    "net_vs_positive_ranking": "Explain why the top net-score alliance may not rank first for positive contribution.",
    "player_exclusion_impact": "Explain what changed after excluding currently selected players.",
    "negative_share_change": "Explain an increase, decrease, neutral change, or unspecified change in negative share/percentage/ratio.",
    "top_contributors": "Identify top contributing players overall or within named alliances.",
    "alliance_exclusion_total_net": "Calculate total net score after excluding one or more named alliances.",
    "net_score_leader_summary": "Summarize which alliance leads total net score.",
    "unsupported_question": "No supported Ask Dashboard intent applies.",
}


class OpenAIIntentError(Exception):
    """Safe exception carrying only a diagnostic code."""

    def __init__(self, diagnostic_code):
        super().__init__(diagnostic_code)
        self.diagnostic_code = diagnostic_code


def build_api_intent_contract(candidate):
    """Build and validate an API-sourced intent contract from a plain candidate."""
    if not isinstance(candidate, dict):
        raise ValueError("AI intent candidate must be a dictionary")

    intent = candidate.get("intent")
    parameters = {}
    if intent == "negative_share_change":
        parameters = {"requested_direction": candidate.get("requested_direction")}
    elif intent == "top_contributors":
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
            return build_api_intent_contract(candidate)
        except ValueError as exc:
            raise OpenAIIntentError(AI_DIAGNOSTIC_API_INVALID_OUTPUT) from exc
    except OpenAIIntentError:
        raise
    except TimeoutError as exc:
        raise OpenAIIntentError(AI_DIAGNOSTIC_API_UNAVAILABLE) from exc
    except Exception as exc:
        raise OpenAIIntentError(AI_DIAGNOSTIC_API_UNAVAILABLE) from exc
