import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import sklearn

from .data import alphavantage, coinbase, load, save_download, yahoo_snapshot
from .model import Config, evaluate, forecast, supervised
from .report import render


def main(argv=None):
    parser = argparse.ArgumentParser(description="RithmScope daily market forecasting research — no order execution")
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("download", help="Read-only provider import")
    fetch.add_argument("--provider", choices=["coinbase", "alphavantage", "yahoo-snapshot"], required=True)
    fetch.add_argument("--symbol", required=True)
    fetch.add_argument("--start", default="2023-01-01")
    fetch.add_argument("--end", default="2026-01-01", help="Exclusive UTC end for Coinbase")
    fetch.add_argument("--output", required=True)
    for name in ("evaluate", "forecast"):
        p = sub.add_parser(name)
        p.add_argument("--csv", required=True)
        p.add_argument("--symbol", required=True)
        p.add_argument("--asset-class", choices=["stock", "etf", "crypto"], required=True)
        p.add_argument("--through", required=True, help="Last date you attest contains completed bars, YYYY-MM-DD")
        p.add_argument("--source", required=True, help="Data provider or source citation; never credentials")
        p.add_argument("--fee-bps", type=float, default=5)
        p.add_argument("--slippage-bps", type=float, default=5)
        p.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "download":
            if args.provider == "coinbase":
                frame = coinbase(args.symbol, args.start, args.end)
                metadata = {"provider": "Coinbase Exchange", "symbol": args.symbol,
                            "start_inclusive": args.start, "end_exclusive": args.end,
                            "price_basis": "venue trades, daily UTC"}
            elif args.provider == "alphavantage":
                frame = alphavantage(args.symbol)
                metadata = {"provider": "Alpha Vantage", "symbol": args.symbol,
                            "price_basis": "all OHLC adjusted by adjusted_close/raw_close; provider raw volume"}
            else:
                frame = yahoo_snapshot(args.symbol, args.start, args.end)
                metadata = {"provider": "Yahoo Finance public chart snapshot (experimental)", "symbol": args.symbol,
                            "source_url": f"https://finance.yahoo.com/quote/{args.symbol}/history/",
                            "start_inclusive": args.start, "end_exclusive": args.end,
                            "price_basis": "all OHLC scaled by adjusted_close/raw_close; provider volume; retrospective snapshot"}
            save_download(frame, args.output, metadata)
            print(f"Saved {len(frame)} daily bars to {args.output}")
            return 0
        cfg = Config(fee_bps=args.fee_bps, slippage_bps=args.slippage_bps)
        bars, digest = load(args.csv, args.through)
        meta = {"symbol": args.symbol, "asset_class": args.asset_class, "source": args.source,
                "input_sha256": digest, "through": args.through,
                "first_date": str(bars.date.iloc[0].date()), "last_date": str(bars.date.iloc[-1].date()),
                "input_rows_used": len(bars), "config": asdict(cfg),
                "versions": {"numpy": np.__version__, "pandas": pd.__version__, "scikit_learn": sklearn.__version__},
                "warning": "Historical research; no demonstrated predictive edge or order execution"}
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        if args.command == "forecast":
            result = {**meta, "forecast": forecast(bars, cfg)}
            (out/"forecast.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
            print(json.dumps(result["forecast"], indent=2))
        else:
            result, predictions = evaluate(bars, cfg)
            result = {**meta, **result}
            (out/"report.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
            predictions.to_csv(out/"predictions.csv", index=False, date_format="%Y-%m-%d", float_format="%.12g")
            indicators = supervised(bars)
            indicators = indicators[indicators.target_date.isin(predictions.target_date.unique())]
            indicators.drop(columns="actual").to_csv(out/"indicators.csv", index=False, date_format="%Y-%m-%d", float_format="%.12g")
            (out/"report.html").write_text(render(result, predictions), encoding="utf-8")
            print(json.dumps(result["metrics"], indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"RithmScope: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
