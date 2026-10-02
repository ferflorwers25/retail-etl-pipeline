-- Star schema for the retail sales lines. Safe to run repeatedly.

CREATE TABLE IF NOT EXISTS dim_date (
    date_key      INTEGER PRIMARY KEY,          -- YYYYMMDD
    full_date     DATE NOT NULL UNIQUE,
    year          SMALLINT NOT NULL,
    quarter       SMALLINT NOT NULL,
    month         SMALLINT NOT NULL,
    month_name    TEXT NOT NULL,
    iso_week      SMALLINT NOT NULL,
    day_of_week   SMALLINT NOT NULL,            -- 1 = Monday
    is_weekend    BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_key     SERIAL PRIMARY KEY,
    stock_code      TEXT NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    is_merchandise  BOOLEAN NOT NULL            -- false for postage, fees, adjustments, tests
);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key  SERIAL PRIMARY KEY,
    customer_id   INTEGER NOT NULL UNIQUE,
    country       TEXT NOT NULL                 -- country of the customer's latest purchase
);

CREATE TABLE IF NOT EXISTS dim_country (
    country_key   SERIAL PRIMARY KEY,
    country_name  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS fact_sales_line (
    line_id       BIGSERIAL PRIMARY KEY,
    line_hash     CHAR(32) NOT NULL UNIQUE,     -- idempotency key: re-running a load never duplicates rows
    invoice       TEXT NOT NULL,
    line_type     TEXT NOT NULL CHECK (line_type IN ('sale', 'return', 'adjustment', 'fee', 'zero_price')),
    invoice_ts    TIMESTAMP NOT NULL,
    date_key      INTEGER NOT NULL REFERENCES dim_date (date_key),
    product_key   INTEGER NOT NULL REFERENCES dim_product (product_key),
    customer_key  INTEGER REFERENCES dim_customer (customer_key),   -- NULL for guest checkouts
    country_key   INTEGER NOT NULL REFERENCES dim_country (country_key),
    quantity      INTEGER NOT NULL CHECK (quantity <> 0),
    unit_price    NUMERIC(12, 2) NOT NULL,
    revenue       NUMERIC(14, 2) NOT NULL,
    loaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_fact_date ON fact_sales_line (date_key);
CREATE INDEX IF NOT EXISTS ix_fact_product ON fact_sales_line (product_key);
CREATE INDEX IF NOT EXISTS ix_fact_customer ON fact_sales_line (customer_key);
CREATE INDEX IF NOT EXISTS ix_fact_ts ON fact_sales_line (invoice_ts);

CREATE TABLE IF NOT EXISTS etl_runs (
    run_id          SERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ,
    watermark_from  TIMESTAMP,
    rows_candidate  INTEGER,
    rows_inserted   INTEGER,
    status          TEXT NOT NULL
);

-- Convenience view: merchandise sales only.
CREATE OR REPLACE VIEW v_sales AS
SELECT f.*, p.stock_code, p.description, d.full_date, d.year, d.month
FROM fact_sales_line f
JOIN dim_product p USING (product_key)
JOIN dim_date d USING (date_key)
WHERE f.line_type = 'sale' AND p.is_merchandise;
