-- Return rate by country (value of returns / value of sales), top 10 countries by sales.
SELECT co.country_name,
       round(sum(f.revenue) FILTER (WHERE f.line_type = 'sale'))   AS gross_sales,
       round(-sum(f.revenue) FILTER (WHERE f.line_type = 'return')) AS returned_value,
       round(100.0 * -sum(f.revenue) FILTER (WHERE f.line_type = 'return')
             / sum(f.revenue) FILTER (WHERE f.line_type = 'sale'), 1) AS return_rate_pct
FROM fact_sales_line f
JOIN dim_country co USING (country_key)
JOIN dim_product p USING (product_key)
WHERE p.is_merchandise AND f.line_type IN ('sale', 'return')
GROUP BY co.country_name
ORDER BY gross_sales DESC
LIMIT 10;
