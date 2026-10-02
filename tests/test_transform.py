import pandas as pd

from src.etl.transform import (canonical_descriptions, classify, drop_exact_duplicates, drop_sheet_overlap,
                               line_hash, transform)


def test_sheet_overlap_keeps_only_the_later_sheet(raw_lines):
    out = drop_sheet_overlap(raw_lines)
    overlap = out[out["invoice"] == "536365"]
    assert len(overlap) == 1
    assert overlap["source_sheet"].item() == "Year 2010-2011"


def test_exact_duplicates_are_removed(raw_lines):
    out = drop_exact_duplicates(raw_lines)
    assert (out["invoice"] == "489434").sum() == 1


def test_every_problem_line_gets_the_right_type(raw_lines):
    labels = dict(zip(raw_lines["invoice"], classify(raw_lines)))
    assert labels["C489449"] == "return"
    assert labels["489597"] == "fee"
    assert labels["A506401"] == "adjustment"
    assert labels["491186"] == "adjustment"
    assert labels["491189"] == "zero_price"
    assert labels["491187"] == "sale"


def test_cancellation_with_positive_quantity_is_not_a_return():
    df = pd.DataFrame({"invoice": ["C496350"], "stock_code": ["M"], "quantity": [1], "unit_price": [373.57]})
    assert classify(df).item() == "adjustment"


def test_canonical_description_is_the_most_frequent_name(raw_lines):
    raw_lines["description"] = raw_lines["description"].astype("string")
    assert canonical_descriptions(raw_lines)["21844"] == "RED RETROSPOT MUG"


def test_line_hash_is_stable_and_unique():
    df = pd.DataFrame({c: ["x", "y"] for c in ["invoice", "stock_code", "description_raw", "quantity",
                                               "invoice_ts", "unit_price", "customer_id", "country_raw"]})
    first, second = line_hash(df), line_hash(df)
    assert first.equals(second)
    assert first.nunique() == 2


def test_transform_end_to_end(raw_lines):
    clean, clog = transform(raw_lines)
    assert len(clean) == 9                                    # 11 raw - 1 overlap - 1 duplicate
    assert clean.loc[clean["invoice"] == "491187", "country"].item() == "Ireland"
    assert clean.loc[clean["invoice"] == "491186", "description"].item() == "RED RETROSPOT MUG"  # blank filled
    assert clean["customer_id"].dtype == "Int64"
    assert [s for s, _, _ in clog.steps][:2] == ["Remove sheet overlap (1-9 Dec 2010)", "Remove exact duplicate lines"]
