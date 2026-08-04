from pathlib import Path
import py_compile

import pandas as pd

from data_quality import (
    build_data_quality_report,
    build_period_summary,
    parse_svs_period,
    score_gained_precision,
)


def sample_quality_data():
    return pd.DataFrame(
        [
            {
                "svs_date": "2026-W27",
                "alliance": "AAA",
                "player_name": "Alpha",
                "score_gained": 100,
                "score_lost": 40,
                "net_score": 60,
                "net_status": "Positive",
            },
            {
                "svs_date": "2026-W29",
                "alliance": "BBB",
                "player_name": "Beta",
                "score_gained": 50,
                "score_lost": 70,
                "net_score": -20,
                "net_status": "Negative",
            },
        ]
    )


def test_parse_svs_period_is_strict():
    assert parse_svs_period("2026-W29") == (2026, 29)
    assert parse_svs_period("2027-W01") == (2027, 1)
    assert parse_svs_period("W29") is None
    assert parse_svs_period("2026-W00") is None
    assert parse_svs_period("2026-W54") is None


def test_score_gained_precision_boundary():
    assert score_gained_precision("2026-W27") == "Full-value display"
    assert score_gained_precision("2026-W29") == "Rounded in-game display"
    assert score_gained_precision("2027-W01") == "Rounded in-game display"
    assert score_gained_precision("invalid") == "Unknown period format"


def test_clean_report_has_expected_counts_and_no_issues():
    data = sample_quality_data()
    original = data.copy(deep=True)

    report = build_data_quality_report(data)

    assert report["health"] == "No issues detected"
    assert report["row_count"] == 2
    assert report["period_count"] == 2
    assert report["player_count"] == 2
    assert report["alliance_count"] == 2
    assert report["missing_required_columns"] == []
    assert report["missing_identity_result_count"] == 0
    assert report["blank_score_side_count"] == 0
    assert report["exact_duplicate_rows"] == 0
    assert report["duplicate_key_groups"] == 0
    assert report["net_formula_mismatch_count"] == 0
    assert report["net_status_mismatch_count"] == 0
    assert report["malformed_period_count"] == 0
    pd.testing.assert_frame_equal(data, original)


def test_period_summary_reports_coverage_and_precision():
    summary = build_period_summary(sample_quality_data())

    assert summary["SVS Period"].tolist() == ["2026-W27", "2026-W29"]
    assert summary["Rows"].tolist() == [1, 1]
    assert summary["Players"].tolist() == [1, 1]
    assert summary["Alliances"].tolist() == [1, 1]
    assert summary["Score-gained precision"].tolist() == [
        "Full-value display",
        "Rounded in-game display",
    ]


def test_raw_comma_space_and_negative_score_text_is_parsed_like_dashboard():
    data = sample_quality_data().astype("object")
    data.loc[0, "score_gained"] = " 1,000 "
    data.loc[0, "score_lost"] = " 400 "
    data.loc[0, "net_score"] = " 600 "
    data.loc[1, "score_gained"] = " 50 "
    data.loc[1, "score_lost"] = " 70 "
    data.loc[1, "net_score"] = "- 20"

    report = build_data_quality_report(data)

    assert sum(report["invalid_numeric_by_column"].values()) == 0
    assert report["net_formula_mismatch_count"] == 0
    assert report["net_status_mismatch_count"] == 0


def test_report_flags_missing_columns_and_invalid_numbers():
    data = sample_quality_data().drop(columns=["net_status"])
    data["score_gained"] = data["score_gained"].astype("object")
    data.loc[0, "score_gained"] = "not-a-number"

    report = build_data_quality_report(data)

    assert report["health"] == "Needs attention"
    assert report["missing_required_columns"] == ["net_status"]
    assert report["invalid_numeric_by_column"]["score_gained"] == 1


def test_blank_score_side_is_information_and_zero_for_formula_review():
    data = sample_quality_data().astype("object")
    data.loc[0, "score_lost"] = None
    data.loc[0, "net_score"] = 100
    data.loc[1, "score_gained"] = None
    data.loc[1, "net_score"] = -70

    report = build_data_quality_report(data)

    assert report["blank_score_side_count"] == 2
    assert report["missing_identity_result_count"] == 0
    assert report["net_formula_mismatch_count"] == 0
    assert report["health"] == "No issues detected"


def test_report_flags_duplicates_formula_and_status_mismatches():
    data = sample_quality_data()
    duplicate = data.iloc[[0]].copy()
    data = pd.concat([data, duplicate], ignore_index=True)
    data.loc[1, "net_score"] = -25
    data.loc[1, "net_status"] = "Positive"

    report = build_data_quality_report(data)

    assert report["health"] == "Review suggested"
    assert report["exact_duplicate_rows"] == 2
    assert report["duplicate_key_rows"] == 2
    assert report["duplicate_key_groups"] == 1
    assert report["net_formula_mismatch_count"] == 1
    assert report["net_status_mismatch_count"] == 1


def test_report_counts_missing_cells_and_malformed_periods():
    data = sample_quality_data()
    data.loc[0, "player_name"] = None
    data.loc[1, "svs_date"] = "W29"

    report = build_data_quality_report(data)

    assert report["missing_by_column"]["player_name"] == 1
    assert report["missing_identity_result_count"] == 1
    assert report["malformed_period_count"] == 1
    assert report["health"] == "Needs attention"


def test_empty_data_returns_stable_report():
    data = pd.DataFrame(columns=[
        "svs_date",
        "alliance",
        "player_name",
        "score_gained",
        "score_lost",
        "net_score",
        "net_status",
    ])

    report = build_data_quality_report(data)

    assert report["row_count"] == 0
    assert report["period_count"] == 0
    assert report["period_summary"].empty
    assert report["health"] == "No issues detected"


def test_repository_csv_builds_a_stable_report():
    data = pd.read_csv("svs_scores_utf8.csv", encoding="utf-8")

    report = build_data_quality_report(data)

    assert report["row_count"] > 0
    assert report["period_count"] > 0
    assert report["missing_required_columns"] == []
    assert not report["period_summary"].empty
    assert sum(report["invalid_numeric_by_column"].values()) == 0


def test_preview_page_compiles():
    page_path = Path("pages/6_Data_Quality_Methodology.py")
    assert page_path.exists()
    py_compile.compile(str(page_path), doraise=True)
