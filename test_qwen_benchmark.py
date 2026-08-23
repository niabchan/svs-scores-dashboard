from collections import Counter

from ask_dashboard import SUPPORTED_DASHBOARD_INTENTS
from benchmarks.compare_qwen38_intent import (
    CASES_PATH,
    DEFAULT_MODELS,
    _expected_matches,
    _read_json,
)


def test_qwen38_benchmark_case_set_is_balanced_and_well_formed():
    data = _read_json(CASES_PATH)
    cases = data["cases"]

    assert data["benchmark_version"] == 1
    assert data["known_alliance_names"] == ["MBV", "NoM", "SnS", "TDA"]
    assert len(cases) == 24
    assert len({case["id"] for case in cases}) == len(cases)
    assert Counter(case["language"] for case in cases) == {
        "en": 4,
        "es": 4,
        "fr": 4,
        "vi": 4,
        "id": 4,
        "th": 4,
    }

    for case in cases:
        assert case["category"]
        assert case["question"].strip()
        expected = case["expected"]
        assert expected["intent"] in SUPPORTED_DASHBOARD_INTENTS
        assert isinstance(expected["parameters"], dict)
        assert expected["match_status"] in {
            "matched",
            "needs_clarification",
            "unsupported",
        }
        assert "guidance_code" in expected


def test_qwen38_benchmark_defaults_compare_expected_service_variants():
    assert DEFAULT_MODELS == ("qwen3.8-27b", "qwen3.8-27b-fp8")


def test_qwen38_exact_contract_scoring_ignores_confidence_but_requires_contract_fields():
    expected = {
        "intent": "player_net_score_leader",
        "parameters": {"alliance_names": []},
        "match_status": "matched",
        "guidance_code": None,
    }
    contract = {
        "schema_version": 1,
        "intent": "player_net_score_leader",
        "parameters": {"alliance_names": []},
        "source": "api",
        "confidence": 0.73,
        "match_status": "matched",
        "guidance_code": None,
    }

    checks = _expected_matches(contract, expected)
    assert checks["exact_contract_correct"] is True

    contract["parameters"] = {"alliance_names": ["TDA"]}
    checks = _expected_matches(contract, expected)
    assert checks["intent_correct"] is True
    assert checks["parameters_correct"] is False
    assert checks["exact_contract_correct"] is False
