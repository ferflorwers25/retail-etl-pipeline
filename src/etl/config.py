"""Paths and business rules shared by every pipeline step."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_XLSX = ROOT / "data" / "raw" / "online_retail_II.xlsx"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"

# Column names in the source file -> snake_case names used in the pipeline.
RENAME = {
    "Invoice": "invoice",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_ts",
    "Price": "unit_price",
    "Customer ID": "customer_id",
    "Country": "country",
}

# Stock codes that are fees, postage, adjustments or tests, not products.
# Found during profiling (docs/data_quality_profile.md).
NON_PRODUCT_CODES = {
    "POST", "DOT", "M", "C2", "D", "S", "B", "BANK CHARGES", "ADJUST", "ADJUST2",
    "AMAZONFEE", "CRUK", "PADS", "TEST001", "TEST002",
}
NON_PRODUCT_PREFIXES = ("gift_", "DCGS")
