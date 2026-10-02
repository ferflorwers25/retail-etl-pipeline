-- Top 15 products by net revenue, with their return rate (units returned / units sold).
WITH by_product AS (
    SELECT p.stock_code, p.description,
           sum(f.revenue)                                         AS net_revenue,
           sum(f.quantity) FILTER (WHERE f.line_type = 'sale')    AS units_sold,
           -sum(f.quantity) FILTER (WHERE f.line_type = 'return') AS units_returned
    FROM fact_sales_line f
    JOIN dim_product p USING (product_key)
    WHERE p.is_merchandise AND f.line_type IN ('sale', 'return')
    GROUP BY p.stock_code, p.description
)
SELECT stock_code, description, round(net_revenue) AS net_revenue, units_sold,
       coalesce(units_returned, 0) AS units_returned,
       round(100.0 * coalesce(units_returned, 0) / nullif(units_sold, 0), 1) AS return_rate_pct,
       rank() OVER (ORDER BY net_revenue DESC) AS revenue_rank
FROM by_product
ORDER BY net_revenue DESC
LIMIT 15;
