import pandera.errors
import pytest

from src.etl.transform import transform
from src.etl.validate import validate


def test_clean_data_passes_validation(raw_lines):
    clean, _ = transform(raw_lines)
    validate(clean)


def test_a_sale_with_negative_quantity_is_rejected(raw_lines):
    clean, _ = transform(raw_lines)
    idx = clean.index[clean["line_type"] == "sale"][0]
    clean.loc[idx, "quantity"] = -1
    clean.loc[idx, "revenue"] = clean.loc[idx, "quantity"] * clean.loc[idx, "unit_price"]
    with pytest.raises(pandera.errors.SchemaErrors, match="sales_have_positive_qty_and_price"):
        validate(clean)


def test_wrong_revenue_is_rejected(raw_lines):
    clean, _ = transform(raw_lines)
    clean.loc[0, "revenue"] += 10
    with pytest.raises(pandera.errors.SchemaErrors, match="revenue_equals_qty_times_price"):
        validate(clean)
