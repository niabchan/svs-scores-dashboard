import json
from types import SimpleNamespace

import pytest

from openai_intent import (
    AI_DIAGNOSTIC_API_INCOMPLETE,
    AI_DIAGNOSTIC_API_INVALID_OUTPUT,
    AI_API_STYLE_CHAT_COMPLETIONS,
    OpenAIIntentError,
    build_openai_client_options,
    extract_intent_contract_with_openai,
    resolve_ai_api_style,
)


def valid_candidate(**updates):
    candidate = {
        "intent": "top_contributors",
        "requested_direction": "unspecified",
        "alliance_names": ["AAA"],
        "excluded_alliances": [],
        "match_status": "matched",
        "guidance_code": None,
        "confidence": 0.84,
    }
    candidate.update(updates)
    return candidate


class FakeChatCompletions:
    def __init__(self, content=None, finish_reason="stop"):
        self.content = content or json.dumps(valid_candidate())
        self.finish_reason = finish_reason
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason=self.finish_reason,
                    message=SimpleNamespace(content=self.content, refusal=None),
                )
            ]
        )


class FakeChatClient:
    def __init__(self, content=None, finish_reason="stop"):
        self.completions = FakeChatCompletions(content, finish_reason)
        self.chat = SimpleNamespace(completions=self.completions)


def test_client_options_accept_openai_compatible_base_url(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    assert build_openai_client_options("secret") == {
        "api_key": "secret",
        "timeout": 10.0,
        "max_retries": 0,
    }

    options = build_openai_client_options(
        "secret",
        base_url="https://gateway.9arm.co/v1/",
    )
    assert options["base_url"] == "https://gateway.9arm.co/v1"


def test_client_options_read_standard_base_url_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://gateway.9arm.co/v1")
    options = build_openai_client_options("secret")
    assert options["base_url"] == "https://gateway.9arm.co/v1"


def test_chat_completions_transport_returns_validated_contract_and_minimizes_data():
    client = FakeChatClient()
    contract = extract_intent_contract_with_openai(
        "Who contributed most in AAA?",
        ["AAA", "BBB"],
        client=client,
        model="qwen3.6-35b-a3b",
        api_style=AI_API_STYLE_CHAT_COMPLETIONS,
    )

    assert contract["intent"] == "top_contributors"
    assert contract["parameters"] == {"alliance_names": ["AAA"]}
    assert contract["source"] == "api"

    request = client.completions.calls[0]
    assert request["model"] == "qwen3.6-35b-a3b"
    assert request["temperature"] == 0
    assert request["max_tokens"] == 500
    assert "response_format" not in request
    assert request["messages"][0]["role"] == "system"
    assert request["messages"][1]["role"] == "user"

    user_payload = json.loads(request["messages"][1]["content"])
    assert user_payload["question"] == "Who contributed most in AAA?"
    assert user_payload["known_alliance_names"] == ["AAA", "BBB"]
    serialized = json.dumps(user_payload).lower()
    for forbidden in [
        "score_gained",
        "score_lost",
        "net_score",
        "player_name",
        "dataframe",
        "api_key",
    ]:
        assert forbidden not in serialized


def test_chat_completions_accepts_json_code_fence():
    content = "```json\n" + json.dumps(valid_candidate()) + "\n```"
    contract = extract_intent_contract_with_openai(
        "Who contributed most in AAA?",
        ["AAA"],
        client=FakeChatClient(content=content),
        model="qwen3.6-35b-a3b",
        api_style="chat",
    )
    assert contract["parameters"]["alliance_names"] == ["AAA"]


def test_chat_completions_rejects_malformed_json_with_safe_code():
    with pytest.raises(OpenAIIntentError) as error:
        extract_intent_contract_with_openai(
            "Question",
            ["AAA"],
            client=FakeChatClient(content="not-json"),
            model="qwen3.6-35b-a3b",
            api_style="chat_completions",
        )
    assert error.value.diagnostic_code == AI_DIAGNOSTIC_API_INVALID_OUTPUT


def test_chat_completions_maps_length_finish_to_incomplete():
    with pytest.raises(OpenAIIntentError) as error:
        extract_intent_contract_with_openai(
            "Question",
            ["AAA"],
            client=FakeChatClient(finish_reason="length"),
            model="qwen3.6-35b-a3b",
            api_style="chat_completions",
        )
    assert error.value.diagnostic_code == AI_DIAGNOSTIC_API_INCOMPLETE


def test_environment_can_select_chat_completions(monkeypatch):
    monkeypatch.setenv("ASK_DASHBOARD_AI_API_STYLE", "chat_completions")
    assert resolve_ai_api_style() == AI_API_STYLE_CHAT_COMPLETIONS

    client = FakeChatClient()
    contract = extract_intent_contract_with_openai(
        "Who contributed most in AAA?",
        ["AAA"],
        client=client,
        model="qwen3.6-35b-a3b",
    )
    assert contract["source"] == "api"
    assert len(client.completions.calls) == 1


def test_invalid_api_style_is_hidden_as_unavailable():
    with pytest.raises(OpenAIIntentError) as error:
        extract_intent_contract_with_openai(
            "Question",
            ["AAA"],
            client=FakeChatClient(),
            model="qwen3.6-35b-a3b",
            api_style="unknown",
        )
    assert error.value.diagnostic_code == "api_unavailable"
