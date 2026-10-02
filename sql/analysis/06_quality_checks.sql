-- Post-load assertions. Every query must return 0.
SELECT 'duplicate line_hash' AS check_name, count(*) - count(DISTINCT line_hash) AS failures FROM fact_sales_line
UNION ALL
SELECT 'sales with non-positive qty or price', count(*) FROM fact_sales_line
 WHERE line_type = 'sale' AND (quantity <= 0 OR unit_price <= 0)
UNION ALL
SELECT 'revenue <> qty * price', count(*) FROM fact_sales_line WHERE abs(revenue - quantity * unit_price) > 0.01
UNION ALL
SELECT 'returns with positive qty', count(*) FROM fact_sales_line WHERE line_type = 'return' AND quantity > 0
UNION ALL
SELECT 'facts outside the source date range', count(*) FROM fact_sales_line
 WHERE invoice_ts < '2009-12-01' OR invoice_ts >= '2011-12-10';
