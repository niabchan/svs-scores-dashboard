# Ask Dashboard Analytics

Ask Dashboard analytics are optional developer/quality-review infrastructure. They are not required for score calculation, routing, answer rendering, or normal dashboard operation.

The feature was originally developed on a separate Streamlit preview app, so some configuration names and historical notes still use the word `preview`. Production may keep analytics disabled without affecting the dashboard.

## Default local mode

Without additional secrets, analytics can use:

```toml
ASK_DASHBOARD_ANALYTICS_MODE = "local"
```

Events are appended to:

```text
/tmp/svs_scores_dashboard_analytics.jsonl
```

This is **best-effort persistence only**. It can survive browser sessions while the same Streamlit app instance is running, but the file may be lost when Streamlit restarts or redeploys.

## Privacy behaviour

Every generated answer can store anonymous routing metadata such as:

- timestamp;
- UI language;
- SVS period;
- suggested/custom question type;
- intent, status, guidance code, and routing source;
- whether AI fallback was attempted or succeeded;
- the configured AI routing model when an AI attempt occurred;
- filter counts, but not selected alliance or player names;
- question and answer character counts.

The following are not collected by this feature:

- IP address;
- browser fingerprint;
- API keys;
- score rows or DataFrames;
- selected player names.

For a custom question, `question_text` and `answer_text` remain `null` unless the user explicitly checks the consent box. Feedback comments are stored only when the user chooses to submit them.

## Developer review

To show the password-protected analytics review inside the existing developer expander, configure:

```toml
ASK_DASHBOARD_DEBUG_LOG = "true"
ASK_DASHBOARD_ANALYTICS_ADMIN_PASSWORD = "replace-with-a-long-password"
```

The review shows answer count, feedback count, helpful rate, unsupported rate, detailed events, and a JSON download.

Do not enable the developer log without an admin password on a publicly accessible app. Set `ASK_DASHBOARD_DEBUG_LOG = "false"` when the developer review is not needed.

## Durable webhook mode

For persistence that survives Streamlit restarts, configure an HTTPS endpoint that accepts JSON `POST` requests:

```toml
ASK_DASHBOARD_ANALYTICS_MODE = "webhook"
ASK_DASHBOARD_ANALYTICS_ENDPOINT = "https://example.com/analytics/events"
ASK_DASHBOARD_ANALYTICS_SHARED_SECRET = "shared-secret"
ASK_DASHBOARD_APP_VERSION = "v1.0.0"
ASK_DASHBOARD_ANALYTICS_TOKEN = "optional-bearer-token-for-non-Apps-Script-backends"
```

Use a stable deployment identifier appropriate to the running app; `v1.0.0` above is an example for the feature-complete release checkpoint.

The endpoint receives one append-only event at a time. Answer and feedback records are linked through `answer_event_id`; the app does not require update or delete operations.

Webhook failures never prevent Ask Dashboard from returning its answer. Feedback delivery safely retries the pending answer event when needed, using stable identifiers so the receiver can remain idempotent.

## Disable persistence

```toml
ASK_DASHBOARD_ANALYTICS_MODE = "off"
```

The dashboard and Ask Dashboard remain functional. The existing in-session developer log is separate from durable persistence.

## Google Sheets receiver

For durable cloud storage with RawEvents, AnswerFeedbackView, Summary, and OptInTextReview sheets, follow `GOOGLE_SHEETS_ANALYTICS_SETUP.md`.

After changes to `analytics/google_apps_script/Code.gs`, the Apps Script deployment must be updated/redeployed before the live derived sheets reflect the new receiver code. In particular, the AI routing model field added during v1 is read from `raw_event_json` into rebuildable derived views; no destructive RawEvents header migration is required.

## v1 close-out status

Analytics configuration is intentionally treated as optional operations tooling rather than a release blocker. If the Google Sheets receiver is in active use, verify its latest deployment once during release smoke testing. If analytics are disabled, no additional setup is required to close the dashboard project.
