import pandas as pd
import pytest


@pytest.fixture
def raw_lines() -> pd.DataFrame:
    """Small synthetic extract that contains one example of every data problem the pipeline handles."""
    rows = [
        # invoice, stock, description, qty, ts, price, customer, country, sheet
        ("536365", "85123A", "WHITE HANGING HEART", 6, "2010-12-01 08:26", 2.55, 17850, "United Kingdom", "Year 2010-2011"),
        ("536365", "85123A", "WHITE HANGING HEART", 6, "2010-12-01 08:26", 2.55, 17850, "United Kingdom", "Year 2009-2010"),  # sheet overlap
        ("489434", "85048", "15CM CHRISTMAS GLASS", 12, "2009-12-01 07:45", 6.95, 13085, "United Kingdom", "Year 2009-2010"),
        ("489434", "85048", "15CM CHRISTMAS GLASS", 12, "2009-12-01 07:45", 6.95, 13085, "United Kingdom", "Year 2009-2010"),  # exact dup
        ("C489449", "22087", "PAPER BUNTING", -12, "2009-12-01 10:33", 2.95, 16321, "Australia", "Year 2009-2010"),       # return
        ("489597", "POST", "POSTAGE", 1, "2009-12-01 14:28", 18.0, 12533, "Germany", "Year 2009-2010"),                    # fee
        ("A506401", "B", "Adjust bad debt", 1, "2010-04-29 13:36", -53594.36, None, "United Kingdom", "Year 2009-2010"),  # bad debt
        ("491186", "21844", None, -5, "2009-12-09 12:00", 0.0, None, "United Kingdom", "Year 2009-2010"),                # stock adjustment
        ("491187", "21844", "RED RETROSPOT MUG", 3, "2009-12-09 12:05", 2.95, None, "EIRE", "Year 2009-2010"),           # guest, EIRE
        ("491188", "21844", "RED SPOT MUG", 2, "2009-12-10 12:05", 2.95, 14000, "France", "Year 2009-2010"),             # other name
        ("491189", "21844", "RED RETROSPOT MUG", 1, "2009-12-10 13:00", 0.0, 14000, "France", "Year 2009-2010"),         # zero price
    ]
    df = pd.DataFrame(rows, columns=["invoice", "stock_code", "description", "quantity", "invoice_ts",
                                     "unit_price", "customer_id", "country", "source_sheet"])
    df["invoice_ts"] = pd.to_datetime(df["invoice_ts"])
    df["customer_id"] = df["customer_id"].astype("float64")
    return df
