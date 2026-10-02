-- Repeat purchase: share of customers who ordered again within 90 days of their first order, by first-order quarter.
-- Caveat: the data starts in Dec 2009, so the first cohort mixes truly new customers with existing ones.
WITH orders AS (
    SELECT DISTINCT f.customer_key, f.invoice, min(f.invoice_ts) OVER (PARTITION BY f.invoice) AS order_ts
    FROM fact_sales_line f
    WHERE f.line_type = 'sale' AND f.customer_key IS NOT NULL
),
firsts AS (
    SELECT customer_key, min(order_ts) AS first_order FROM orders GROUP BY customer_key
),
flags AS (
    SELECT fi.customer_key, date_trunc('quarter', fi.first_order)::date AS cohort,
           EXISTS (SELECT 1 FROM orders o
                   WHERE o.customer_key = fi.customer_key
                     AND o.order_ts > fi.first_order
                     AND o.order_ts <= fi.first_order + interval '90 days') AS repeated_90d
    FROM firsts fi
)
SELECT cohort, count(*) AS new_customers,
       round(100.0 * avg(repeated_90d::int), 1) AS repeat_within_90d_pct
FROM flags
WHERE cohort < '2011-09-01'          -- later cohorts have less than 90 days of history
GROUP BY cohort
ORDER BY cohort;
