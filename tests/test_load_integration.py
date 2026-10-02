"""Integration test against a real PostgreSQL.

Runs only when TEST_DATABASE_URL is set (CI provides a throwaway database).
WARNING: it drops the pipeline tables, so never point it at a database you care about.
"""
import os

import pytest

from src.etl.transform import transform

TEST_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_URL, reason="needs TEST_DATABASE_URL")


def test_load_is_incremental_and_idempotent(raw_lines, monkeypatch):
    from src.etl.load import connect, load

    monkeypatch.setenv("DATABASE_URL", TEST_URL)

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
