"""Extract: read both Excel sheets into one DataFrame and cache it as Parquet.

Reading the 45 MB workbook takes about a minute, so later steps use the Parquet cache.
"""
from __future__ import annotations

import logging

import pandas as pd

from .config import INTERIM, RAW_XLSX, RENAME

log = logging.getLogger(__name__)
CACHE = INTERIM / "raw_combined.parquet"


def extract(force: bool = False) -> pd.DataFrame:
    if CACHE.exists() and not force:
        log.info("Reading cached extract %s", CACHE.name)
        return pd.read_parquet(CACHE)

    log.info("Reading %s (both sheets)", RAW_XLSX.name)
    # Text columns are forced to str: some descriptions are stored as numbers in Excel.
    sheets = pd.read_excel(
        RAW_XLSX, sheet_name=None,
        dtype={"Invoice": str, "StockCode": str, "Description": str, "Country": str},
    )
    frames = []
    for name, frame in sheets.items():
        frame = frame.rename(columns=RENAME)
        frame["source_sheet"] = name
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    INTERIM.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CACHE, index=False)
    log.info("Extracted %s rows from %s sheets", f"{len(df):,}", len(sheets))
    return df
