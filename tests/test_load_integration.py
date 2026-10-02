"""Integration test against a real PostgreSQL. Runs only when DATABASE_URL is set (CI provides one)."""
import os

import pytest

from src.etl.transform import transform

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL")


def test_load_is_incremental_and_idempotent(raw_lines):
    from src.etl.load import connect, load

    with connect() as conn:  # start from an empty database
        conn.execute("DROP TABLE IF EXISTS fact_sales_line, dim_date, dim_product, dim_customer, dim_country, etl_runs CASCADE")

    clean, _ = transform(raw_lines)
    first = clean[clean["invoice_ts"] < "2010-01-01"]

    run1 = load(first)
    assert run1["inserted"] == len(first)

    run2 = load(clean)                      # only the newer lines are inserted
    assert run2["inserted"] == len(clean) - len(first)

    run3 = load(clean)                      # re-running changes nothing
    assert run3["inserted"] == 0
    assert run3["total"] == len(clean)
