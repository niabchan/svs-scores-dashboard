"""Compare Qwen3.8 BF16 and FP8 as Ask Dashboard intent classifiers.

This benchmark is intentionally separate from the Streamlit application. It
reuses the production prompt/decoder from ``openai_intent.py`` but never
changes runtime model settings or application secrets.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from openai import OpenAI

from ask_dashboard import route_dashboard_question
from openai_intent import (
    OpenAIIntentError,
    _chat_completion_text,
    _chat_messages,
    _decode_candidate,
    build_openai_client_options,
)

DEFAULT_MODELS = ("qwen3.8-27b", "qwen3.8-27b-fp8")
DEFAULT_BASE_URL = "https://gateway.9arm.co/v1"
CASES_PATH = Path(__file__).with_name("qwen38_intent_cases.json")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _safe_git_sha() -> str | None:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=REPO_ROOT,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
            or None
        )
    except Exception:
        return None


def _candidate_call(
    *,
    client: OpenAI,
    model: str,
    question: str,
    known_alliance_names: list[str],
) -> tuple[str, dict[str, Any], Any]:
    """Make the same chat-completions request shape used by production."""
    response = client.chat.completions.create(
        model=model,
        messages=_chat_messages(question, known_alliance_names),
        temperature=0,
        max_tokens=1200,
        timeout=60.0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    raw_text = _chat_completion_text(response)
    contract = _decode_candidate(raw_text, known_alliance_names)
    return raw_text, contract, response


def _expected_matches(
    contract: dict[str, Any] | None,
    expected: dict[str, Any],
) -> dict[str, bool]:
    if contract is None:
        return {
            "intent_correct": False,
            "parameters_correct": False,
            "match_status_correct": False,
            "guidance_code_correct": False,
            "exact_contract_correct": False,
        }

    checks = {
        "intent_correct": contract.get("intent") == expected.get("intent"),
        "parameters_correct": contract.get("parameters", {})
        == expected.get("parameters", {}),
        "match_status_correct": contract.get("match_status")
        == expected.get("match_status"),
        "guidance_code_correct": contract.get("guidance_code")
        == expected.get("guidance_code"),
    }
    checks["exact_contract_correct"] = all(checks.values())
    return checks


def _usage_fields(response: Any) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "completion_tokens": getattr(usage, "completion_tokens", None)
        if usage
        else None,
        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
    }


def _fallback_relevance(case: dict[str, Any], known: list[str]) -> dict[str, Any]:
    local = route_dashboard_question(case["question"], known)
    is_fallback = (
        local.get("intent") == "unsupported_question"
        and local.get("match_status") == "unsupported"
    )
    return {
        "would_reach_ai_after_rules": is_fallback,
        "rule_intent": local.get("intent"),
        "rule_match_status": local.get("match_status"),
    }


def _percent(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "—"
    return f"{100.0 * numerator / denominator:.1f}%"


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _format_seconds(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}s"


def _model_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    attempted = len(rows)
    valid = sum(row["valid_contract"] for row in rows)
    exact = sum(row["exact_contract_correct"] for row in rows)
    intent = sum(row["intent_correct"] for row in rows)
    params = sum(row["parameters_correct"] for row in rows)
    fallback_rows = [row for row in rows if row["would_reach_ai_after_rules"]]
    fallback_exact = sum(row["exact_contract_correct"] for row in fallback_rows)
    latencies = [
        row["latency_seconds"]
        for row in rows
        if row["latency_seconds"] is not None
    ]
    return {
        "attempted": attempted,
        "valid_contracts": valid,
        "exact_contracts": exact,
        "intent_correct": intent,
        "parameters_correct": params,
        "fallback_attempted": len(fallback_rows),
        "fallback_exact_contracts": fallback_exact,
        "avg_latency_seconds": statistics.mean(latencies) if latencies else None,
        "median_latency_seconds": statistics.median(latencies) if latencies else None,
        "p95_latency_seconds": _p95(latencies),
        "errors": sum(bool(row["error_code"]) for row in rows),
        "prompt_tokens": sum(
            row["prompt_tokens"] or 0
            for row in rows
            if row["prompt_tokens"] is not None
        )
        or None,
        "completion_tokens": sum(
            row["completion_tokens"] or 0
            for row in rows
            if row["completion_tokens"] is not None
        )
        or None,
    }


def _markdown_report(run: dict[str, Any]) -> str:
    rows = run["results"]
    models = run["metadata"]["models"]
    by_model = {
        model: _model_summary([row for row in rows if row["model"] == model])
        for model in models
    }

    lines = [
        "# Qwen3.8 Intent Routing Benchmark",
        "",
        f"- Run UTC: `{run['metadata']['run_utc']}`",
        f"- Repository SHA: `{run['metadata'].get('git_sha') or 'unknown'}`",
        f"- Gateway: `{run['metadata']['base_url']}`",
        f"- Repetitions per case/model: `{run['metadata']['repetitions']}`",
        f"- Model call ordering: `{run['metadata']['model_ordering']}`",
        f"- Inter-call delay: `{run['metadata']['inter_call_delay_seconds']}s`",
        f"- Benchmark cases: `{run['metadata']['case_count']}`",
        f"- Total API calls attempted: `{len(rows)}`",
        "",
        "## Executive summary",
        "",
        "This benchmark compares the two Qwen3.8-27B service variants only in the role "
        "used by Ask Dashboard: structured intent classification and parameter extraction. "
        "It does **not** test score calculation, answer generation, or long-context quality. "
        "The application continues to calculate and render score answers locally in Python.",
        "",
        "| Model | Valid contract | Exact contract | Intent accuracy | Parameter accuracy | Production-fallback exact | Avg latency | Median latency | P95 latency | Errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for model in models:
        s = by_model[model]
        lines.append(
            "| {model} | {valid} | {exact} | {intent} | {params} | {fallback} | {avg} | {median} | {p95} | {errors} |".format(
                model=model,
                valid=_percent(s["valid_contracts"], s["attempted"]),
                exact=_percent(s["exact_contracts"], s["attempted"]),
                intent=_percent(s["intent_correct"], s["attempted"]),
                params=_percent(s["parameters_correct"], s["attempted"]),
                fallback=_percent(
                    s["fallback_exact_contracts"], s["fallback_attempted"]
                ),
                avg=_format_seconds(s["avg_latency_seconds"]),
                median=_format_seconds(s["median_latency_seconds"]),
                p95=_format_seconds(s["p95_latency_seconds"]),
                errors=s["errors"],
            )
        )

    lines += [
        "",
        "The **Production-fallback exact** column is the primary project metric. It counts "
        "only benchmark questions that the deterministic router would leave unsupported, "
        "which is when the live application would actually call the model.",
        "",
        "## Accuracy by language",
        "",
        "| Language | Model | Exact | Cases |",
        "|---|---|---:|---:|",
    ]

    languages = sorted({row["language"] for row in rows})
    for language in languages:
        for model in models:
            subset = [
                row
                for row in rows
                if row["language"] == language and row["model"] == model
            ]
            lines.append(
                f"| {language} | {model} | "
                f"{_percent(sum(r['exact_contract_correct'] for r in subset), len(subset))} | "
                f"{len(subset)} |"
            )

    lines += [
        "",
        "## Accuracy by category",
        "",
        "| Category | Model | Exact | Cases |",
        "|---|---|---:|---:|",
    ]
    categories = sorted({row["category"] for row in rows})
    for category in categories:
        for model in models:
            subset = [
                row
                for row in rows
                if row["category"] == category and row["model"] == model
            ]
            lines.append(
                f"| {category} | {model} | "
                f"{_percent(sum(r['exact_contract_correct'] for r in subset), len(subset))} | "
                f"{len(subset)} |"
            )

    failures = [row for row in rows if not row["exact_contract_correct"]]
    lines += ["", "## Mismatches and failures", ""]
    if not failures:
        lines.append("No exact-contract mismatches occurred in this run.")
    else:
        lines.append(
            "| Case | Language | Model | Expected intent | Observed intent | Error | Latency |"
        )
        lines.append("|---|---|---|---|---|---|---:|")
        for row in failures:
            lines.append(
                "| {case_id} | {language} | {model} | `{expected}` | `{observed}` | {error} | {latency} |".format(
                    case_id=row["case_id"],
                    language=row["language"],
                    model=row["model"],
                    expected=row["expected"]["intent"],
                    observed=(row.get("contract") or {}).get("intent", "—"),
                    error=row.get("error_code") or "—",
                    latency=_format_seconds(row.get("latency_seconds")),
                )
            )

    lines += [
        "",
        "## Methodology",
        "",
        "- Both models receive the same benchmark question, known-alliance allowlist, system instruction, JSON schema, temperature, token limit, and thinking-disabled setting.",
        "- Model order alternates by benchmark case to reduce systematic warm-cache or second-request latency bias.",
        "- The request and decoder are reused from the Ask Dashboard OpenAI-compatible intent integration so the test stays close to production behavior.",
        "- Expected results are hand-authored intent contracts. Exact-contract accuracy requires the intent, parameters, match status, and guidance code to all match.",
        "- Raw model text and validated contracts are preserved in `results.json` for auditability.",
        "- No score rows, DataFrames, player names, Streamlit secrets, API keys, or session logs are included in the benchmark payload or report.",
        "",
        "## Caveats",
        "",
        "- A single-pass run measures one sample per case/model. Use `--repetitions 2` or more if you want a stability study.",
        "- Gateway latency can include queueing, model loading, and network effects; latency should not be interpreted as pure inference speed.",
        "- These prompts are short. This benchmark therefore does not test the 128k vs 256k context-window difference.",
        "- Results describe performance on the Ask Dashboard intent-routing task, not overall model intelligence.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "export OPENAI_API_KEY='...'",
        "export OPENAI_BASE_URL='https://gateway.9arm.co/v1'",
        "python benchmarks/compare_qwen38_intent.py --repetitions 1",
        "```",
        "",
        "The script writes a timestamped directory under `benchmark_runs/` containing "
        "`report.md`, `results.json`, and `results.csv`.",
        "",
    ]
    return "\n".join(lines)


def _write_outputs(output_dir: Path, run: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "results.json").open("w", encoding="utf-8") as handle:
        json.dump(run, handle, ensure_ascii=False, indent=2)

    fieldnames = [
        "case_id",
        "category",
        "language",
        "question",
        "model",
        "repetition",
        "call_index",
        "model_order_position",
        "would_reach_ai_after_rules",
        "rule_intent",
        "valid_contract",
        "intent_correct",
        "parameters_correct",
        "match_status_correct",
        "guidance_code_correct",
        "exact_contract_correct",
        "latency_seconds",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "error_code",
    ]
    with (output_dir / "results.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in run["results"]:
            writer.writerow({field: row.get(field) for field in fieldnames})

    (output_dir / "report.md").write_text(
        _markdown_report(run),
        encoding="utf-8",
    )


def _dry_run(cases_data: dict[str, Any], models: list[str], repetitions: int) -> int:
    known = cases_data["known_alliance_names"]
    cases = cases_data["cases"]
    fallback_count = 0
    for case in cases:
        relevance = _fallback_relevance(case, known)
        fallback_count += int(relevance["would_reach_ai_after_rules"])
        print(
            f"{case['id']}: local={relevance['rule_intent']} "
            f"fallback={relevance['would_reach_ai_after_rules']}"
        )
    print()
    print(f"Cases: {len(cases)}")
    print(f"Production-fallback subset: {fallback_count}")
    print(f"Models: {', '.join(models)}")
    print(f"Repetitions: {repetitions}")
    print(f"Planned API calls: {len(cases) * len(models) * repetitions}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        type=Path,
        default=CASES_PATH,
        help="Benchmark case JSON file.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_MODELS),
        help="Model identifiers to compare.",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=1,
        help="Calls per case/model. Default: 1.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional exact output directory.",
    )
    parser.add_argument(
        "--inter-call-delay",
        type=float,
        default=0.25,
        help="Seconds to pause after each API call. Default: 0.25.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate routing relevance and print planned call count without using the API.",
    )
    args = parser.parse_args()

    if args.repetitions < 1:
        parser.error("--repetitions must be at least 1")
    if args.inter_call_delay < 0:
        parser.error("--inter-call-delay must be non-negative")

    cases_data = _read_json(args.cases)
    known = [str(name) for name in cases_data["known_alliance_names"]]
    cases = cases_data["cases"]
    models = [str(model) for model in args.models]

    if args.dry_run:
        return _dry_run(cases_data, models, args.repetitions)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        parser.error(
            "OPENAI_API_KEY is required for a live run. "
            "Use --dry-run to inspect the benchmark without API calls."
        )
    base_url = os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    client = OpenAI(**build_openai_client_options(api_key, base_url=base_url))

    run_utc = datetime.now(timezone.utc)
    run_id = run_utc.strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or (
        REPO_ROOT / "benchmark_runs" / f"qwen38_intent_{run_id}"
    )

    results: list[dict[str, Any]] = []
    call_index = 0
    for case_index, case in enumerate(cases):
        relevance = _fallback_relevance(case, known)
        # Alternate the model order by case so the same model is not always
        # advantaged by being the second request after a potential warm-up.
        model_order = models if case_index % 2 == 0 else list(reversed(models))
        for model_order_position, model in enumerate(model_order, start=1):
            for repetition in range(1, args.repetitions + 1):
                call_index += 1
                started = time.perf_counter()
                raw_text = None
                contract = None
                response = None
                error_code = None
                try:
                    raw_text, contract, response = _candidate_call(
                        client=client,
                        model=model,
                        question=case["question"],
                        known_alliance_names=known,
                    )
                except OpenAIIntentError as exc:
                    error_code = exc.diagnostic_code
                except Exception as exc:
                    # Avoid serializing provider exception text because it can contain
                    # request metadata. The exception class is sufficient for the audit.
                    error_code = type(exc).__name__
                latency = time.perf_counter() - started

                checks = _expected_matches(contract, case["expected"])
                usage = _usage_fields(response)
                row = {
                    "case_id": case["id"],
                    "category": case["category"],
                    "language": case["language"],
                    "question": case["question"],
                    "expected": case["expected"],
                    "model": model,
                    "repetition": repetition,
                    "call_index": call_index,
                    "model_order_position": model_order_position,
                    **relevance,
                    "valid_contract": contract is not None,
                    **checks,
                    "latency_seconds": round(latency, 6),
                    **usage,
                    "error_code": error_code,
                    "raw_text": raw_text,
                    "contract": contract,
                }
                results.append(row)
                status = "PASS" if row["exact_contract_correct"] else "FAIL"
                print(
                    f"[{status}] #{call_index} {case['id']} | {model} | "
                    f"{latency:.2f}s | {error_code or 'ok'}"
                )
                if args.inter_call_delay:
                    time.sleep(args.inter_call_delay)

    run = {
        "metadata": {
            "benchmark_name": "qwen3.8 Ask Dashboard intent routing",
            "benchmark_version": cases_data.get("benchmark_version", 1),
            "run_utc": run_utc.isoformat(),
            "git_sha": _safe_git_sha(),
            "base_url": base_url,
            "models": models,
            "repetitions": args.repetitions,
            "inter_call_delay_seconds": args.inter_call_delay,
            "model_ordering": "alternating_by_case",
            "case_count": len(cases),
            "known_alliance_names": known,
        },
        "results": results,
    }
    _write_outputs(output_dir, run)
    print()
    print(f"Report: {output_dir / 'report.md'}")
    print(f"Raw results: {output_dir / 'results.json'}")
    print(f"CSV: {output_dir / 'results.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
