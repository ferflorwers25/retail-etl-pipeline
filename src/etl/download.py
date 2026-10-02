"""Download the UCI Online Retail II dataset (CC BY 4.0).

Usage:
    python -m src.etl.download

Saves data/raw/online_retail_II.xlsx. Raw data is not committed to git.
Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {URL} ...")
    with urlopen(Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=600) as resp:
        payload = resp.read()
    print(f"  {len(payload) / 1e6:.1f} MB")
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        print("  archive contains:", zf.namelist())
        xlsx = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
        out = RAW_DIR / "online_retail_II.xlsx"
        out.write_bytes(zf.read(xlsx[0]))
    print(f"  saved {out}")


if __name__ == "__main__":
    main()
