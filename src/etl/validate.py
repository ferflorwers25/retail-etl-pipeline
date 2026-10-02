"""Validate: data contracts for the cleaned lines (Pandera). The pipeline stops if any check fails."""
from __future__ import annotations

import pandas as pd

try:
    import pandera.pandas as pa
except ImportError:  # older pandera
    import pandera as pa

from .transform import LINE_TYPES

clean_lines_schema = pa.DataFrameSchema(
    {
        "line_hash": pa.Column(str, pa.Check.str_length(32, 32), unique=True),
        "invoice": pa.Column(str, pa.Check.str_matches(r"^[AC]?\d{6}$")),
        "line_type": pa.Column(str, pa.Check.isin(LINE_TYPES)),
        "invoice_ts": pa.Column("datetime64[ns]", pa.Check.in_range(pd.Timestamp("2009-12-01"), pd.Timestamp("2011-12-31"))),
        "stock_code": pa.Column(str, pa.Check.str_length(min_value=1)),
        "description": pa.Column("string", nullable=False),
        "customer_id": pa.Column("Int64", pa.Check.gt(0), nullable=True),
        "country": pa.Column(str, nullable=False),
        "quantity": pa.Column(int, pa.Check.ne(0)),
        "unit_price": pa.Column(float),
        "revenue": pa.Column(float),
    },
    checks=[
        pa.Check(lambda d: (d["revenue"] - (d["quantity"] * d["unit_price"]).round(2)).abs() < 0.01,
                 name="revenue_equals_qty_times_price"),
        pa.Check(lambda d: ~((d["line_type"] == "sale") & ((d["quantity"] <= 0) | (d["unit_price"] <= 0))),
                 name="sales_have_positive_qty_and_price"),
        pa.Check(lambda d: ~((d["line_type"] == "return") & (d["quantity"] >= 0)),
                 name="returns_have_negative_qty"),
    ],
    strict=False,
)


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Raise pandera.errors.SchemaErrors listing every failing check (lazy=True)."""
    return clean_lines_schema.validate(df, lazy=True)
