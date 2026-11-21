"""Reproduce the public engineering demonstration from independent fictional prices.

No network access, provider data, market calibration or real symbols are used.
"""
import hashlib
import json
from pathlib import Path

from rithmscope.__main__ import main as run
from rithmscope.demo_data import fixture
from rithmscope.report import render

ROOT = Path(__file__).resolve().parent
DEMO = [("DEMO-STOCK", "stock", 101, "B"), ("DEMO-ETF", "etf", 202, "B"),
        ("DEMO-CRYPTO-A", "crypto", 303, "D"), ("DEMO-CRYPTO-B", "crypto", 404, "D")]


def main():
    for symbol, kind, seed, calendar in DEMO:
        bars = fixture(900, seed=seed, calendar=calendar)
        path = ROOT/"data"/"synthetic"/f"{symbol}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        bars.to_csv(path, index=False, date_format="%Y-%m-%d", float_format="%.12g", lineterminator="\n")
        out = ROOT/"results"/symbol
        through = str(bars.date.iloc[-1].date())
        code = run(["evaluate", "--csv", str(path), "--symbol", symbol, "--asset-class", kind,
                    "--through", through, "--source", f"Independent synthetic fixture; seed {seed}; no market data",
                    "--output", str(out)])
        if code:
            raise SystemExit(code)
        report = json.loads((out/"report.json").read_text(encoding="utf-8"))
        report.update(data_kind="synthetic", warning="Invented prices for engineering demonstration only; not market evidence")
        (out/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
        import pandas as pd
        predictions = pd.read_csv(out/"predictions.csv")
        (out/"report.html").write_text(render(report, predictions), encoding="utf-8")
        provenance = {"kind": "synthetic", "provider": "Independent synthetic generator", "symbol": symbol,
            "seed": seed, "generator": "rithmscope.demo_data.fixture; independent normal draws; 900 rows",
            "calendar": calendar, "price_basis": "Fictional OHLCV; no actual securities, tokens or exchange observations",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": len(bars),
            "first_date": str(bars.date.iloc[0].date()), "last_date": through}
        (out/"data.metadata.json").write_text(json.dumps(provenance, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
