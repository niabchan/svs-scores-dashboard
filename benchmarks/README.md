# Qwen3.8 Intent Routing Benchmark

This directory contains a small, auditable benchmark for comparing the two Qwen3.8-27B variants currently available through the 9arm OpenAI-compatible gateway:

- `qwen3.8-27b` — BF16 service variant
- `qwen3.8-27b-fp8` — FP8 service variant

The benchmark is intentionally **separate from the Streamlit production path**. It does not change `OPENAI_INTENT_MODEL`, production secrets, filters, score calculations, or rendered answers.

## What this benchmark measures

Ask Dashboard uses the model only as a fallback intent classifier. Deterministic rules run first. When those rules cannot confidently map a custom question, the model receives:

- the user's question;
- supported intent definitions and parameter rules;
- a short allowlist of known alliance names.

The model does **not** receive player rows, score values, rankings, DataFrames, selected-player lists, API keys, or session logs.

For that reason, this benchmark measures the model in the role the application actually needs:

1. valid structured contract rate;
2. intent accuracy;
3. parameter extraction accuracy;
4. exact contract accuracy;
5. accuracy on the subset that would reach AI after deterministic rules;
6. latency;
7. API/contract failure rate;
8. token usage when the gateway returns usage metadata.

It does not attempt to measure score-calculation ability because score calculations are performed locally in Python.

## Case set

`qwen38_intent_cases.json` contains 24 hand-authored cases: four each in English, Spanish, French, Vietnamese, Indonesian, and Thai.

The cases cover:

- broad alliance score overview;
- alliance net-score leader;
- player net-score leader;
- top contributors;
- alliance exclusion;
- negative-share change;
- dashboard limitations around human intent/behavior;
- unsupported questions;
- product/help guidance.

Each case contains a ground-truth intent contract. The benchmark also runs the deterministic router locally and marks whether that wording would actually reach the AI fallback in the current application.

## Safe dry run

A dry run does not require an API key and makes no network calls:

```bash
python benchmarks/compare_qwen38_intent.py --dry-run
```

It prints the local rule result for every case and the planned number of live calls.

With the default 24 cases, two models, and one repetition, a live run makes **48 API calls**.

## Live run

Set the 9arm key only in your local shell/session. Do not commit it.

```bash
export OPENAI_API_KEY='...'
export OPENAI_BASE_URL='https://gateway.9arm.co/v1'
python benchmarks/compare_qwen38_intent.py --repetitions 1
```

On PowerShell:

```powershell
$env:OPENAI_API_KEY = "..."
$env:OPENAI_BASE_URL = "https://gateway.9arm.co/v1"
python benchmarks/compare_qwen38_intent.py --repetitions 1
```

The model identifiers default to:

```text
qwen3.8-27b
qwen3.8-27b-fp8
```

You can override them:

```bash
python benchmarks/compare_qwen38_intent.py \
  --models qwen3.8-27b qwen3.8-27b-fp8 \
  --repetitions 1
```

## Outputs

Each live run creates:

```text
benchmark_runs/qwen38_intent_<UTC timestamp>/
  report.md
  results.json
  results.csv
```

`report.md` is designed to be shareable. `results.json` preserves the raw model text and validated contracts for auditability. `results.csv` provides a flat result table for analysis.

The `benchmark_runs/` directory is ignored by Git so a local run cannot accidentally publish raw results. A report can be copied into a reviewed location later if you deliberately want to share it.

## Fair-comparison controls

Both models receive the same:

- production intent prompt and JSON schema;
- known-alliance allowlist;
- `temperature=0`;
- `max_tokens=1200`;
- `enable_thinking=False`;
- OpenAI-compatible chat-completions transport;
- local validation/decoding logic.

The script reuses the private request/decoder helpers from `openai_intent.py` on purpose. If production intent prompting changes, the benchmark should be reviewed at the same time so it continues to test the same interface.

## Interpreting the report

The primary project metric is **Production-fallback exact** because that subset represents questions that deterministic rules leave unsupported and would therefore trigger the API in the live application.

The all-case score is still useful for comparing classifier behavior, but some of those questions may already be handled locally and therefore never incur an API call in production.

Latency is informative but noisy. It may include gateway queueing, model loading, and network conditions; it is not a pure inference-speed measurement.

The benchmark uses short prompts, so it does not test the advertised 128k vs 256k context-window difference. It should not be presented as a general benchmark of the models' overall intelligence.

## Stability follow-up

For a second-stage stability test:

```bash
python benchmarks/compare_qwen38_intent.py --repetitions 3
```

That would make 144 calls with the current 24-case/two-model set. Use it only when the first 48-call run shows a meaningful reason to investigate variance.
