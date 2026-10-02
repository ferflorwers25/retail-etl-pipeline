"""Load: incremental, idempotent load into the PostgreSQL star schema.

1. Read the watermark (latest invoice_ts already loaded).
2. Stage only lines newer than watermark - 1 day (the overlap day is safe: see 4).
3. Upsert dimensions from the staged lines.
4. Insert facts with ON CONFLICT (line_hash) DO NOTHING, so a re-run inserts 0 rows.
"""
from __future__ import annotations

import io
import logging
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import psycopg

from .config import ROOT
from .transform import is_non_product

log = logging.getLogger(__name__)
STAGE_COLS = ["line_hash", "invoice", "line_type", "invoice_ts", "invoice_date", "stock_code", "description",
              "is_merchandise", "customer_id", "country", "quantity", "unit_price", "revenue"]


def connect() -> psycopg.Connection:
    if url := os.getenv("DATABASE_URL"):
        return psycopg.connect(url)
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"), port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"), dbname=os.getenv("POSTGRES_DB"),
    )


def create_schema(conn: psycopg.Connection) -> None:
    conn.execute((ROOT / "sql" / "schema.sql").read_text())


def get_watermark(conn: psycopg.Connection) -> datetime | None:
    return conn.execute("SELECT max(invoice_ts) FROM fact_sales_line").fetchone()[0]


def stage(conn: psycopg.Connection, df: pd.DataFrame) -> None:
    conn.execute("""
        CREATE TEMP TABLE stg (
            line_hash CHAR(32), invoice TEXT, line_type TEXT, invoice_ts TIMESTAMP, invoice_date DATE,
            stock_code TEXT, description TEXT, is_merchandise BOOLEAN, customer_id INTEGER, country TEXT,
            quantity INTEGER, unit_price NUMERIC(12,2), revenue NUMERIC(14,2)
        ) ON COMMIT DROP""")
    out = df.assign(is_merchandise=~is_non_product(df["stock_code"]))[STAGE_COLS]
    buf = io.StringIO()
    out.to_csv(buf, index=False, header=False, date_format="%Y-%m-%d %H:%M:%S")
    with conn.cursor().copy("COPY stg FROM STDIN (FORMAT CSV)") as copy:
        copy.write(buf.getvalue())


UPSERTS = [
    """INSERT INTO dim_date (date_key, full_date, year, quarter, month, month_name, iso_week, day_of_week, is_weekend)
       SELECT DISTINCT to_char(invoice_date, 'YYYYMMDD')::int, invoice_date, extract(year FROM invoice_date),
              extract(quarter FROM invoice_date), extract(month FROM invoice_date), trim(to_char(invoice_date, 'Month')),
              extract(week FROM invoice_date), extract(isodow FROM invoice_date), extract(isodow FROM invoice_date) >= 6
       FROM stg ON CONFLICT (date_key) DO NOTHING""",
    """INSERT INTO dim_product (stock_code, description, is_merchandise)
       SELECT DISTINCT ON (stock_code) stock_code, description, is_merchandise FROM stg ORDER BY stock_code
       ON CONFLICT (stock_code) DO UPDATE SET description = EXCLUDED.description""",
    """INSERT INTO dim_country (country_name) SELECT DISTINCT country FROM stg ON CONFLICT DO NOTHING""",
    """INSERT INTO dim_customer (customer_id, country)
       SELECT DISTINCT ON (customer_id) customer_id, country FROM stg WHERE customer_id IS NOT NULL
       ORDER BY customer_id, invoice_ts DESC
       ON CONFLICT (customer_id) DO UPDATE SET country = EXCLUDED.country""",
]

INSERT_FACTS = """
INSERT INTO fact_sales_line (line_hash, invoice, line_type, invoice_ts, date_key, product_key, customer_key,
                             country_key, quantity, unit_price, revenue)
SELECT s.line_hash, s.invoice, s.line_type, s.invoice_ts, to_char(s.invoice_date, 'YYYYMMDD')::int,
       p.product_key, c.customer_key, co.country_key, s.quantity, s.unit_price, s.revenue
FROM stg s
JOIN dim_product p ON p.stock_code = s.stock_code
JOIN dim_country co ON co.country_name = s.country
LEFT JOIN dim_customer c ON c.customer_id = s.customer_id
ON CONFLICT (line_hash) DO NOTHING
"""


def load(df: pd.DataFrame) -> dict:
    started = datetime.now(timezone.utc)
    with connect() as conn:
        create_schema(conn)
        watermark = get_watermark(conn)
        batch = df if watermark is None else df[df["invoice_ts"] > pd.Timestamp(watermark) - timedelta(days=1)]
        log.info("Watermark: %s -> %s candidate rows", watermark, f"{len(batch):,}")
        inserted = 0
        if len(batch):
            stage(conn, batch)
            for sql in UPSERTS:
                conn.execute(sql)
            inserted = conn.execute(INSERT_FACTS).rowcount
        conn.execute(
            "INSERT INTO etl_runs (started_at, finished_at, watermark_from, rows_candidate, rows_inserted, status) "
            "VALUES (%s, now(), %s, %s, %s, 'success')", (started, watermark, len(batch), inserted))
        total = conn.execute("SELECT count(*) FROM fact_sales_line").fetchone()[0]
    log.info("Inserted %s new rows (fact table now has %s)", f"{inserted:,}", f"{total:,}")
    return {"watermark": watermark, "candidates": len(batch), "inserted": inserted, "total": total}
