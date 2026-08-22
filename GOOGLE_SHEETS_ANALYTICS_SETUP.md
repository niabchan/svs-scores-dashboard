# Google Sheets Analytics Setup

This optional setup replaces best-effort local JSONL analytics with durable append-only cloud storage in a private Google Spreadsheet. It was developed through the separate Streamlit preview workflow, but the same receiver can be used for a deployed app if the owner chooses to keep analytics enabled.

Analytics are not required for dashboard operation or the v1 release.

## What the receiver creates

The Apps Script receiver maintains four sheets:

- `RawEvents` — append-only source of truth;
- `AnswerFeedbackView` — one answer per row joined with its latest feedback, including the AI routing model when an AI routing attempt occurred;
- `Summary` — answer, feedback, helpful, unsupported, AI, AI routing model, language, intent, and version metrics;
- `OptInTextReview` — only answer rows where the user explicitly allowed full question and answer text to be saved.

Do not manually edit `RawEvents`. The other three sheets are rebuilt from it whenever a new event arrives.

## 1. Create the Spreadsheet

1. Create a new private Google Spreadsheet.
2. Give it a clear name such as `SVS Dashboard Analytics`.
3. Do not enable `Anyone with the link` sharing for the Spreadsheet itself.

## 2. Add the Apps Script receiver

1. In the Spreadsheet, open **Extensions → Apps Script**.
2. Replace the default code with the contents of `analytics/google_apps_script/Code.gs` from the repository version you intend to deploy.
3. Save the project.

## 3. Add the shared secret

Create a long random secret in a password manager. In Apps Script:

1. Open **Project Settings**.
2. Under **Script Properties**, add:
   - Property: `ANALYTICS_SHARED_SECRET`
   - Value: your random secret

Do not place this secret in the GitHub repository or inside `Code.gs`.

## 4. Initialize the sheets

1. Select the `setupSheets` function in Apps Script.
2. Run it once.
3. Approve the requested permission to edit the bound Spreadsheet.

This stores the Spreadsheet ID in Script Properties and creates the four sheets.

## 5. Deploy as a Web App

1. Choose **Deploy → New deployment**.
2. Select **Web app**.
3. Execute the app as yourself.
4. Choose an access setting that permits the Streamlit app to send HTTP POST requests.
5. Deploy and copy the `/exec` Web App URL.

The Web App URL is public enough to receive requests, but every payload must also contain the shared secret. A wrong secret is rejected by the receiver response.

Keep both the Web App URL and shared secret private.

## 6. Configure Streamlit Secrets

Add or update:

```toml
ASK_DASHBOARD_ANALYTICS_MODE = "webhook"
ASK_DASHBOARD_ANALYTICS_ENDPOINT = "https://script.google.com/macros/s/REPLACE_WITH_DEPLOYMENT_ID/exec"
ASK_DASHBOARD_ANALYTICS_SHARED_SECRET = "REPLACE_WITH_THE_SAME_RANDOM_SECRET"
ASK_DASHBOARD_APP_VERSION = "v1.0.0"

ASK_DASHBOARD_DEBUG_LOG = "true"
ASK_DASHBOARD_ANALYTICS_ADMIN_PASSWORD = "REPLACE_WITH_A_DIFFERENT_LONG_PASSWORD"
```

Use an app-version value that identifies the actual deployment. `v1.0.0` is an example for the feature-complete release checkpoint.

`ASK_DASHBOARD_ANALYTICS_ADMIN_PASSWORD` protects the in-app developer view. It should not be the same value as the webhook shared secret.

The older `ASK_DASHBOARD_ANALYTICS_TOKEN` bearer-token setting remains optional for non-Apps-Script receivers. Apps Script authentication uses the payload shared secret because Apps Script web-app event objects do not expose arbitrary authorization headers to `doPost(e)`.

## 7. Test

1. Refresh/reboot the deployed app after saving Secrets.
2. Ask one suggested question and submit Helpful feedback.
3. Ask one custom question without full-text consent.
4. Ask one custom question with full-text consent and submit Not helpful feedback.
5. Trigger one AI-routed question if AI routing is enabled.
6. Open the Spreadsheet and confirm:
   - `RawEvents` contains separate answer and feedback events;
   - `AnswerFeedbackView` joins feedback to the correct answer;
   - `OptInTextReview` contains only the opted-in custom question;
   - `Summary` updates its counts and rates;
   - `ai_routing_model` appears in the derived answer/summary views for the AI attempt and remains blank for rule-only answers.

## Security and privacy behaviour

- The receiver accepts only analytics schema version 1 and the two expected event types.
- Answer and feedback events must have nonblank identifiers.
- Payload size is bounded.
- User-controlled strings beginning with spreadsheet formula characters are prefixed as plain text before being written, preventing formula execution.
- The shared secret is compared before any event is appended.
- Custom question and generated answer text remain null unless the user opts in for that question.
- No IP address, browser fingerprint, score rows, DataFrame, API key, or selected player name is sent by the dashboard analytics module.

## Updating the Apps Script later

Editing `Code.gs` does not automatically update an existing deployment. After code changes, create a new deployment version or edit the deployment to use the new version, then verify the Web App URL used in Streamlit Secrets.

The AI routing model field is stored inside `raw_event_json` and read into rebuildable derived views. The existing `RawEvents` header layout is intentionally unchanged, so current analytics rows remain compatible and no destructive migration is required.

## v1 close-out decision

If Google Sheets analytics are actively used, verify the receiver is deployed from the latest `Code.gs` once during release smoke testing. If analytics are not needed, set analytics mode to `off` and treat this file as optional operations documentation rather than a release requirement.
