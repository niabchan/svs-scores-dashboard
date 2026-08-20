# 9arm API setup for Ask Dashboard

This integration keeps the existing safety boundary:

- deterministic rules run first;
- the API is called only when rule routing returns `unsupported`;
- the model only classifies an intent and extracts permitted parameters;
- Python validates the result and performs all score calculations;
- score rows, rankings, DataFrames, player names, API keys, and session logs are not sent to the model.

## Streamlit Community Cloud secrets

Add these values to the **preview app** secrets first:

```toml
ASK_DASHBOARD_AI_ROUTING = "true"
ASK_DASHBOARD_AI_API_STYLE = "chat_completions"
OPENAI_API_KEY = "<your private 9arm API key>"
OPENAI_BASE_URL = "https://gateway.9arm.co/v1"
OPENAI_INTENT_MODEL = "qwen3.8-27b-fp8"
```

Do not commit the real API key to GitHub and do not paste it into issues, pull requests, logs, screenshots, or test files.

The project keeps the existing `OPENAI_*` variable names because it uses the OpenAI Python SDK as a client for an OpenAI-compatible endpoint. The provider is selected by the base URL and API style. `OPENAI_INTENT_MODEL` is intentionally a runtime setting, so a provider model replacement normally requires changing the secret value rather than changing application code.

## Test sequence

1. Let GitHub Actions run the full unit test suite. Tests use fake clients and do not call 9arm.
2. Deploy the integration branch to the separate Streamlit preview app.
3. Add the secrets above only in Streamlit Community Cloud.
4. Confirm that existing rule-matched questions still report `source = rule` and do not attempt the API.
5. Try unsupported wording that should map to an existing intent and confirm `source = api`.
6. Confirm that malformed, unavailable, or timed-out API responses fall back safely without exposing provider errors or secrets.
7. Review anonymous routing diagnostics and feedback before considering a merge to `main`.

## Suggested preview smoke tests

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

The unsupported question should remain guidance-only; the model is not allowed to calculate or predict results.
