#!/usr/bin/env python3
"""
Investment Time Machine — data downloader
Run this once to generate data.json for the static site.
  pip install -r requirements.txt
  python download_data.py
"""

import json
import time
import yfinance as yf
from datetime import datetime

# ── Ticker list ────────────────────────────────────────────────────────────────

from tickers import ALL_TICKERS

# ── Download ───────────────────────────────────────────────────────────────────


def download_all(tickers: dict, batch_size: int = 50) -> dict:
    symbols = list(tickers.keys())
    total = len(symbols)
    out = {}  # { ticker: { "name": str, "data": { "YYYY-MM": price } } }

    print(f"Downloading {total} tickers in batches of {batch_size}…\n")

    for i in range(0, total, batch_size):
        batch = symbols[i : i + batch_size]
        print(f"  Batch {i // batch_size + 1} — {batch[0]} … {batch[-1]}")

        try:
            raw = yf.download(
                batch,
                period="max",
                interval="1mo",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
        except Exception as e:
            print(f"    ✗ Batch failed: {e}")
            continue

        # yfinance returns multi-level columns when >1 ticker
        if len(batch) == 1:
            ticker = batch[0]
            if "Close" in raw.columns and not raw["Close"].empty:
                series = raw["Close"].dropna()
                out[ticker] = {
                    "name": tickers[ticker],
                    "data": {
                        str(d.date())[:7]: round(float(v), 4)
                        for d, v in series.items()
                        if v > 0
                    },
                }
        else:
            if "Close" not in raw.columns.get_level_values(0):
                continue
            closes = raw["Close"]
            for ticker in batch:
                if ticker not in closes.columns:
                    continue
                series = closes[ticker].dropna()
                if series.empty:
                    continue
                out[ticker] = {
                    "name": tickers[ticker],
                    "data": {
                        str(d.date())[:7]: round(float(v), 4)
                        for d, v in series.items()
                        if v > 0
                    },
                }

        time.sleep(0.5)  # be polite

    return out


def build_meta(data: dict) -> dict:
    """Build a lightweight search index: ticker → name + date range."""
    meta = {}
    for ticker, info in data.items():
        dates = list(info["data"].keys())
        if not dates:
            continue
        meta[ticker] = {
            "name": info["name"],
            "from": min(dates),
            "to": max(dates),
        }
    return meta


def main():
    print("=" * 60)
    print("Investment Time Machine — data downloader")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60 + "\n")

    data = download_all(ALL_TICKERS)

    print(f"\n✓ Downloaded {len(data)} tickers successfully.")

    # Save full price data
    with open("data.json", "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print("✓ Saved data.json")

    # Save lightweight metadata for search
    meta = build_meta(data)
    with open("meta.json", "w") as f:
        json.dump(meta, f, separators=(",", ":"))
    print("✓ Saved meta.json")

    # Stats
    sizes = [len(v["data"]) for v in data.values()]
    print("\nStats:")
    print(f"  Tickers:      {len(data)}")
    print(f"  Avg months:   {sum(sizes) // len(sizes) if sizes else 0}")
    print(
        f"  Date range:   {min(d for v in data.values() for d in v['data'])} → {max(d for v in data.values() for d in v['data'])}"
    )


if __name__ == "__main__":
    main()
