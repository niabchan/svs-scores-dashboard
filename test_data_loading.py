import pandas as pd

from data_loading import coerce_numeric_columns


def legacy_coerce_numeric_columns(data, columns):
    """Reproduce the loader behavior before the embedded-whitespace fix."""
    cleaned = data.copy()
    for column in columns:
        cleaned[column] = (
            cleaned[column]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    return cleaned


def test_loader_parses_embedded_whitespace_in_signed_numbers():
    source = pd.DataFrame(
        {
            "score_gained": [" 2,878,535 "],
            "score_lost": [" 549,617,472 "],
            "net_score": ["- 546,738,937 "],
            "competition_rank": [" 28 "],
        }
    )

    loaded = coerce_numeric_columns(source)

    assert loaded.loc[0, "score_gained"] == 2_878_535
    assert loaded.loc[0, "score_lost"] == 549_617_472
    assert loaded.loc[0, "net_score"] == -546_738_937
    assert loaded.loc[0, "competition_rank"] == 28


def test_loader_preserves_missing_and_invalid_value_behavior():
    source = pd.DataFrame(
        {
            "score_gained": [None, "NULL", "not-a-number"],
            "score_lost": ["", " ", "1,000"],
        }
    )

    loaded = coerce_numeric_columns(source, ["score_gained", "score_lost"])

    assert loaded["score_gained"].isna().all()
    assert loaded["score_lost"].isna().iloc[:2].all()
    assert loaded.loc[2, "score_lost"] == 1_000


def test_loader_does_not_mutate_source_dataframe():
    source = pd.DataFrame({"net_score": ["- 20"]})
    original = source.copy(deep=True)

    loaded = coerce_numeric_columns(source, ["net_score"])

    pd.testing.assert_frame_equal(source, original)
    assert loaded.loc[0, "net_score"] == -20


def test_repository_csv_loader_impact_diagnostic():
    raw = pd.read_csv("svs_scores_utf8.csv")
    columns = ["score_gained", "score_lost", "net_score", "competition_rank"]
    legacy = legacy_coerce_numeric_columns(raw, columns)
    fixed = coerce_numeric_columns(raw, columns)

    restored_mask = legacy["net_score"].isna() & fixed["net_score"].notna()
    restored = raw.loc[
        restored_mask,
        ["svs_date", "alliance", "player_name", "net_score"],
    ].copy()

    w23 = raw["svs_date"].astype(str) == "2026-W23"
    legacy_w23_total = legacy.loc[w23, "net_score"].sum()
    fixed_w23_total = fixed.loc[w23, "net_score"].sum()

    raise AssertionError(
        {
            "restored_rows": restored.to_dict(orient="records"),
            "restored_count": int(restored_mask.sum()),
            "legacy_w23_total": int(legacy_w23_total),
            "fixed_w23_total": int(fixed_w23_total),
            "w23_difference": int(fixed_w23_total - legacy_w23_total),
        }
    )
