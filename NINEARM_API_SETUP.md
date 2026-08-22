# 9arm API setup for Ask Dashboard

Ask Dashboard uses 9arm through the OpenAI Python SDK as an optional intent-routing fallback. The integration keeps a narrow safety boundary:

- deterministic rules run first;
- the API is called only when local routing returns `unsupported` and AI routing is enabled;
- the model only classifies an intent and extracts permitted parameters;
- Python validates the result and performs all score calculations;
- Python renders the final answer in the selected dashboard locale;
- score rows, rankings, DataFrames, player names, selected-player lists, API keys, and session logs are not sent to the model.

The interface and deterministic answers support English, Spanish, French, Vietnamese, and Indonesian. Common tested free-text wording also routes deterministically in several languages, with focused Thai custom-question coverage. English currently has the broadest deterministic free-text coverage. The AI fallback may help classify unfamiliar wording, but it must not be described as unrestricted multilingual answer generation.

## Streamlit Community Cloud secrets

Configure these values in Streamlit Secrets. When changing provider/model settings, test them on a preview deployment before changing production where practical.

```toml
ASK_DASHBOARD_AI_ROUTING = "true"
ASK_DASHBOARD_AI_API_STYLE = "chat_completions"
OPENAI_API_KEY = "<your private 9arm API key>"
OPENAI_BASE_URL = "https://gateway.9arm.co/v1"
OPENAI_INTENT_MODEL = "qwen3.8-27b-fp8"
```

Do not commit the real API key to GitHub and do not paste it into issues, pull requests, logs, screenshots, or test files.

The project keeps the existing `OPENAI_*` variable names because it uses the OpenAI Python SDK as a client for an OpenAI-compatible endpoint. The provider is selected by the base URL and API style. `OPENAI_INTENT_MODEL` is intentionally a runtime setting, so a provider model replacement normally requires changing the secret value rather than application code.

## What the model receives

The request is limited to:

- the user's custom question;
- supported intent definitions and parameter rules;
- currently known alliance names needed for parameter validation.

The model is instructed to return one structured extraction candidate rather than a prose answer. Local validation rejects malformed JSON, unknown intents, invalid parameters, unknown alliance references, or otherwise invalid contracts.

## Test sequence

1. Let GitHub Actions run the full unit test suite. Tests use fake clients and do not call 9arm.
2. For provider/model changes, deploy the integration branch to a separate Streamlit preview app where practical.
3. Add or update the runtime secrets only in Streamlit Community Cloud.
4. Confirm that existing rule-matched questions still report `source = rule` and do not attempt the API.
5. Try unfamiliar wording that should map to an existing intent and confirm `source = api`.
6. Confirm that malformed, unavailable, or timed-out API responses fall back safely without exposing provider errors or secrets.
7. Confirm that the final answer is still calculated/rendered locally and uses the selected dashboard locale.

## Suggested smoke tests

Use wording that is intentionally outside the strongest deterministic patterns but still means one of the supported analyses. Examples:

```text
Which group carried the server result overall?
Show me the strongest contributors from SnS.
What happens to the total if TDA is left out?
Which player finished with the best overall balance?
```

Also verify a clearly unsupported question:

```text
Predict who will win the next SVS.
```

The unsupported question should remain guidance-only. The model is not allowed to calculate, predict future results, or infer player intent/character from the score data.

## Observability

When an AI routing attempt occurs, analytics may record the configured `ai_routing_model` identifier. Rule-only answers leave that field blank. This identifies the classifier involved in a routing attempt; it is not an answer-generation model field.
