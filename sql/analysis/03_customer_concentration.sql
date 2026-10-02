-- How concentrated is revenue? Customers ranked into deciles by net revenue (identified customers only).
WITH customer_revenue AS (
    SELECT f.customer_key, sum(f.revenue) AS net_revenue, count(DISTINCT f.invoice) AS orders
    FROM fact_sales_line f
    JOIN dim_product p USING (product_key)
    WHERE p.is_merchandise AND f.line_type IN ('sale', 'return') AND f.customer_key IS NOT NULL
    GROUP BY f.customer_key
),
deciles AS (
    SELECT *, ntile(10) OVER (ORDER BY net_revenue DESC) AS decile FROM customer_revenue
)
SELECT decile,
       count(*)                                                     AS customers,
       round(sum(net_revenue))                                      AS net_revenue,
       round(100.0 * sum(net_revenue) / sum(sum(net_revenue)) OVER (), 1) AS share_of_revenue_pct,
       round(100.0 * sum(sum(net_revenue)) OVER (ORDER BY decile) / sum(sum(net_revenue)) OVER (), 1) AS cumulative_share_pct,
       round(avg(orders), 1)                                        AS avg_orders
FROM deciles
GROUP BY decile
ORDER BY decile;
