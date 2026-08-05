# Ask Dashboard Preview Analytics

This feature is for the separate Streamlit preview app. It is not intended to be merged into production until its privacy, usefulness, and storage approach have been reviewed.

## Default preview mode

Without additional secrets, the preview uses:

```toml
ASK_DASHBOARD_ANALYTICS_MODE = "local"
```

Events are appended to:

```text
/tmp/svs_scores_dashboard_analytics.jsonl
```

This is **best-effort persistence only**. It can survive browser sessions while the same Streamlit app instance is running, but the file may be lost when Streamlit restarts or redeploys.

## Privacy behavior

Every generated answer can store anonymous routing metadata such as:

- timestamp;
- UI language;
- SVS period;
- suggested/custom question type;
- intent, status, guidance code, and routing source;
- whether AI fallback was attempted or succeeded;
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

Do not enable the developer log without an admin password on a publicly accessible app.

## Durable webhook mode

For persistence that survives Streamlit restarts, configure an HTTPS endpoint that accepts JSON `POST` requests:

```toml
ASK_DASHBOARD_ANALYTICS_MODE = "webhook"
ASK_DASHBOARD_ANALYTICS_ENDPOINT = "https://example.com/analytics/events"
ASK_DASHBOARD_ANALYTICS_SHARED_SECRET = "shared-secret"
ASK_DASHBOARD_APP_VERSION = "preview-pr13"
ASK_DASHBOARD_ANALYTICS_TOKEN = "optional-bearer-token-for-non-Apps-Script-backends"
```

The endpoint receives one append-only event at a time. Answer and feedback records are linked through `answer_event_id`; the app does not require update or delete operations.

Webhook failures never prevent Ask Dashboard from returning its answer. Feedback is offered only when the answer event was saved successfully.

## Disable persistence

```toml
ASK_DASHBOARD_ANALYTICS_MODE = "off"
```

The existing in-session developer log remains separate and is not durable.


## Google Sheets receiver

For durable cloud storage with RawEvents, AnswerFeedbackView, Summary, and OptInTextReview sheets, follow `GOOGLE_SHEETS_ANALYTICS_SETUP.md`.
