"""Transform: clean the raw lines and classify each one.

Every rule is a small function so it can be unit-tested, and every step logs how many
rows it removed or changed. The log becomes docs/data_quality_report.md.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

import pandas as pd

from .config import NON_PRODUCT_CODES, NON_PRODUCT_PREFIXES

log = logging.getLogger(__name__)

COUNTRY_FIXES = {"EIRE": "Ireland", "RSA": "South Africa", "USA": "United States"}
LINE_TYPES = ("sale", "return", "adjustment", "fee", "zero_price")
HASH_COLS = ["invoice", "stock_code", "description_raw", "quantity", "invoice_ts", "unit_price", "customer_id", "country_raw"]


@dataclass
class CleaningLog:
    steps: list[tuple[str, int, int]] = field(default_factory=list)  # (step, rows_before, rows_after)

    def add(self, step: str, before: int, after: int) -> None:
        self.steps.append((step, before, after))
        log.info("%-45s %10s -> %10s rows", step, f"{before:,}", f"{after:,}")


def drop_sheet_overlap(df: pd.DataFrame) -> pd.DataFrame:
    """The workbook's sheets overlap (1-9 Dec 2010 appears in both). Keep the later sheet for the overlap."""
    sheets = sorted(df["source_sheet"].unique())
    keep = pd.Series(True, index=df.index)
    for earlier, later in zip(sheets, sheets[1:]):
        later_start = df.loc[df["source_sheet"] == later, "invoice_ts"].min()
        keep &= ~((df["source_sheet"] == earlier) & (df["invoice_ts"] >= later_start))
    return df[keep]


def drop_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in df.columns if c != "source_sheet"]
    return df.drop_duplicates(subset=cols)


def is_non_product(codes: pd.Series) -> pd.Series:
    return codes.isin(NON_PRODUCT_CODES) | codes.str.startswith(NON_PRODUCT_PREFIXES, na=False)


def classify(df: pd.DataFrame) -> pd.Series:
    """One label per line. Order matters: the first rule that matches wins."""
    inv = df["invoice"].astype(str)
    non_product = is_non_product(df["stock_code"])
    conditions = [
        inv.str.startswith("A"),                                   # bad-debt accounting entries
        inv.str.startswith("C") & (df["quantity"] < 0),            # cancellations / returns
        inv.str.startswith("C"),                                   # "C" lines with qty >= 0 (manual fixes)
        non_product & ~df["stock_code"].isin({"ADJUST", "ADJUST2", "B"}),  # postage, fees, tests
        non_product | (df["quantity"] <= 0),                       # stock adjustments
        df["unit_price"] == 0,                                     # free items / data errors
    ]
    labels = ["adjustment", "return", "adjustment", "fee", "adjustment", "zero_price"]
    out = pd.Series("sale", index=df.index)
    for cond, label in reversed(list(zip(conditions, labels))):
        out[cond] = label
    return out


def canonical_descriptions(df: pd.DataFrame) -> pd.Series:
    """Most frequent non-empty description per stock code (product names change over time)."""
    d = df.dropna(subset=["description"])
    d = d[d["description"].str.strip() != ""]
    return (d.groupby(["stock_code", "description"]).size()
             .reset_index(name="n")
             .sort_values(["stock_code", "n", "description"], ascending=[True, False, True])
             .drop_duplicates("stock_code")
             .set_index("stock_code")["description"])


def line_hash(df: pd.DataFrame) -> pd.Series:
    """Stable fingerprint of the original line. Used as the idempotency key when loading."""
    # Each column is formatted explicitly so the hash is identical across pandas versions
    # and missing values never break it.
    parts = []
    for col in HASH_COLS:
        values = df[col]
        if pd.api.types.is_datetime64_any_dtype(values):
            text = values.dt.strftime("%Y-%m-%d %H:%M:%S")
        elif pd.api.types.is_float_dtype(values):
            text = values.map(lambda v: "" if pd.isna(v) else f"{v:.2f}")
        else:
            text = values.astype("string")
        parts.append(text.fillna("").astype(object))
    joined = pd.concat(parts, axis=1).agg("|".join, axis=1)
    return joined.map(lambda s: hashlib.md5(s.encode("utf-8")).hexdigest())


def transform(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningLog]:
    clog = CleaningLog()
    df = raw.copy()

    n = len(df); df = drop_sheet_overlap(df); clog.add("Remove sheet overlap (1-9 Dec 2010)", n, len(df))
    n = len(df); df = drop_exact_duplicates(df); clog.add("Remove exact duplicate lines", n, len(df))

    df["description"] = df["description"].astype("string").str.strip().str.upper()
    df["stock_code"] = df["stock_code"].astype(str).str.strip().str.upper()
    df["description_raw"] = df["description"]
    df["country_raw"] = df["country"]
    df["customer_id"] = df["customer_id"].astype("Int64")
    df["line_hash"] = line_hash(df)

    canon = canonical_descriptions(df)
    missing = df["description"].isna().sum()
    df["description"] = df["stock_code"].map(canon).fillna(df["description"]).fillna("UNKNOWN")
    clog.add(f"Canonical product names ({missing:,} blanks filled)", len(df), len(df))

    df["country"] = df["country"].replace(COUNTRY_FIXES)
    df["line_type"] = classify(df)
    df["revenue"] = (df["quantity"] * df["unit_price"]).round(2)
    df["invoice_date"] = df["invoice_ts"].dt.normalize()

    cols = ["line_hash", "invoice", "line_type", "invoice_ts", "invoice_date", "stock_code", "description",
            "customer_id", "country", "quantity", "unit_price", "revenue"]
    return df[cols].reset_index(drop=True), clog
