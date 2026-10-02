-- Monthly net revenue, orders and average order value, with month-over-month growth.
-- Net revenue = merchandise sales + returns (returns are negative). Fees and adjustments are excluded.
-- Caveat: Dec 2011 only covers 1-9 Dec and includes one 80,995-unit order that was cancelled the same day.
WITH monthly AS (
    SELECT date_trunc('month', f.invoice_ts)::date                               AS month,
           sum(f.revenue) FILTER (WHERE f.line_type = 'sale')                   AS gross_sales,
           sum(f.revenue) FILTER (WHERE f.line_type = 'return')                 AS returns,
           count(DISTINCT f.invoice) FILTER (WHERE f.line_type = 'sale')        AS orders
    FROM fact_sales_line f
    JOIN dim_product p USING (product_key)
    WHERE p.is_merchandise AND f.line_type IN ('sale', 'return')
    GROUP BY 1
)
SELECT month,
       round(gross_sales)                                    AS gross_sales,
       round(coalesce(returns, 0))                           AS returns,
       round(gross_sales + coalesce(returns, 0))             AS net_revenue,
       orders,
       round(gross_sales / orders, 2)                        AS avg_order_value,
       round(100.0 * (gross_sales + coalesce(returns, 0))
             / lag(gross_sales + coalesce(returns, 0)) OVER (ORDER BY month) - 100, 1) AS mom_growth_pct
FROM monthly
ORDER BY month;
