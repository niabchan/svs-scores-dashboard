# SVS Scores Dashboard

Explore player and alliance impact on SVS results for Evony Server 559+461.

**Live dashboard:** https://svs-scores-dashboard.streamlit.app

SVS Scores Dashboard is a Streamlit analytics project for comparing score gained, score lost, net score, rankings, alliance contribution, and player-selection impact across recorded SVS periods. It also includes **Ask Dashboard**, a bounded question-and-answer layer that combines deterministic routing with an optional AI intent-classification fallback while keeping score calculation in Python.

## What you can explore

- **Overview** — full-server metrics for the selected SVS period.
- **Alliance Summary** — compare score gained, score lost, net score, player counts, and net score per player.
- **Player Data** — inspect the filtered player-level records behind the analysis.
- **Contribution Insight** — compare positive and negative net-score contribution by alliance.
- **Player Selection Insight** — see how including or excluding selected players changes server-level results and alliance summaries.
- **Ask Dashboard** — ask supported analytical questions about rankings, contribution, exclusions, metric definitions, and the active filter scope.

The source dataset currently contains recorded periods through **2026-W31**.

## Languages

The dashboard interface and deterministic Ask Dashboard answers support:

- English
- Spanish
- French
- Vietnamese
- Indonesian

Common free-text questions are also routed deterministically in several languages. English currently has the broadest deterministic free-text coverage, and a focused set of Thai custom-question patterns is regression-tested. This project does not claim unrestricted multilingual natural-language understanding.

Player names and alliance names are never translated.

## Ask Dashboard architecture

Ask Dashboard is intentionally not an unconstrained chatbot.

```text
User question
    |
    v
Deterministic rule routing
    |
    |-- matched ----------> validated intent contract
    |
    `-- unsupported
            |
            `-- optional AI intent classifier
                    |
                    v
              validated intent contract
                    |
                    v
             Python calculation
                    |
                    v
        deterministic localized rendering
```

The optional AI fallback is used only to classify unfamiliar wording into an existing supported intent and extract permitted parameters. The model does **not** calculate scores or write the final analytical answer.

The AI request does not include score rows, rankings, DataFrames, player names, or selected-player lists. See [`NINEARM_API_SETUP.md`](NINEARM_API_SETUP.md) for the current integration boundary.

## Metric meanings

| Metric | Meaning |
|---|---|
| **Score Gained** | Points earned during the selected SVS period |
| **Score Lost** | Points lost during the selected SVS period |
| **Net Score** | Score Gained minus Score Lost |
| **Positive Contribution** | Positive net-score impact within the selected scope |
| **Negative Contribution** | Negative net-score impact within the selected scope |
| **Net per Player** | Alliance total net score divided by represented included players |

A broad “best player” question uses **Net Score** as the dashboard's default overall-result measure. That is a metric choice, not a claim about a player's skill, intent, character, or unseen gameplay behaviour.

## Data notes

Some score-gained values are based on Evony's rounded in-game display. Where that limitation applies, calculated totals, net scores, rankings, and derived results are approximate and the dashboard preserves a data notice.

Blank one-sided score fields and source formatting are handled by the data loader without silently changing the source CSV. The project keeps Score Gained, Score Lost, Net Score, Positive Contribution, and Negative Contribution as distinct concepts.

## Privacy-aware analytics

Usage analytics and feedback are optional and are not required for the dashboard to answer questions.

Anonymous routing metadata may be stored when analytics are enabled. A custom question and its generated answer are stored only when the user explicitly opts in for that question. The analytics layer does not collect IP addresses, browser fingerprints, API keys, score rows, DataFrames, or selected player names.

See [`PREVIEW_ANALYTICS_SETUP.md`](PREVIEW_ANALYTICS_SETUP.md) and [`GOOGLE_SHEETS_ANALYTICS_SETUP.md`](GOOGLE_SHEETS_ANALYTICS_SETUP.md) for the optional developer infrastructure.

## Tech stack

- Python 3.12
- Streamlit
- pandas / NumPy
- Plotly
- PyArrow
- OpenAI Python SDK used with an OpenAI-compatible 9arm endpoint for optional intent routing
- pytest / GitHub Actions
- optional Google Apps Script + Google Sheets analytics receiver

## Run locally

```bash
git clone https://github.com/niabchan/svs-scores-dashboard.git
cd svs-scores-dashboard
python -m venv .venv
```

Activate the virtual environment for your platform, then install dependencies:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The dashboard works without AI routing. To enable the optional intent classifier, configure Streamlit Secrets as documented in [`NINEARM_API_SETUP.md`](NINEARM_API_SETUP.md). Never commit real API keys or analytics secrets.

## Tests

Install the test environment and run the complete suite:

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q
```

The v1 close-out baseline is **379 passing tests** before the final documentation/CI cleanup changes in this repository close-out.

## Project documentation

- [`PRODUCT.md`](PRODUCT.md) — product scope, truths, and non-goals
- [`DESIGN.md`](DESIGN.md) — information hierarchy, responsive and multilingual design rules
- [`CONTENT.md`](CONTENT.md) — v1 content decisions and deferred maintenance
- [`LOCALIZATION.md`](LOCALIZATION.md) — language capability boundary and terminology rules
- [`NINEARM_API_SETUP.md`](NINEARM_API_SETUP.md) — optional AI intent-routing setup and data boundary
- [`PREVIEW_ANALYTICS_SETUP.md`](PREVIEW_ANALYTICS_SETUP.md) — optional analytics behaviour
- [`GOOGLE_SHEETS_ANALYTICS_SETUP.md`](GOOGLE_SHEETS_ANALYTICS_SETUP.md) — optional durable analytics receiver

## Project status

The dashboard is treated as **feature-complete for v1**. Future work should primarily be data updates, bug fixes, dependency/security maintenance, and evidence-based routing improvements rather than open-ended feature expansion.

Deferred technical work includes separating the main translation dictionary from `app.py`, eventually simplifying the historical Ask Dashboard compatibility layer if justified, and considering Thai tokenization only if future tests demonstrate a real word-segmentation problem.

## License

No open-source license has been selected for this repository. The absence of a license should not be interpreted as permission to reuse or redistribute the code.
