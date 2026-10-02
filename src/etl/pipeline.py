"""Run the full pipeline: extract -> transform -> validate -> load -> report.

Usage:
    python -m src.etl.pipeline                      # load everything new
    python -m src.etl.pipeline --until 2010-12-31   # load only up to a date (simulates a first daily batch)
    python -m src.etl.pipeline --no-load            # clean + validate + report, without a database
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd
from dotenv import load_dotenv

from .extract import extract
from .report import write_report
from .transform import transform
from .validate import validate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--until", help="only load lines up to this date (YYYY-MM-DD)")
    parser.add_argument("--no-load", action="store_true", help="skip the database load")
    parser.add_argument("--force-extract", action="store_true", help="re-read the Excel file instead of the cache")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    load_dotenv()

    raw = extract(force=args.force_extract)
    clean, clog = transform(raw)
    validate(clean)
    logging.info("Validation passed: %s clean lines", f"{len(clean):,}")

    if args.until:
        clean = clean[clean["invoice_ts"] < pd.Timestamp(args.until) + pd.Timedelta(days=1)]
        logging.info("--until %s: keeping %s lines", args.until, f"{len(clean):,}")

    stats = None
    if not args.no_load:
        from .load import load
        stats = load(clean)
    write_report(raw, clean, clog, stats)
    logging.info("Report written to docs/data_quality_report.md")


if __name__ == "__main__":
    main()
