"""Build the public dashboard bundle only from committed, derived research artifacts."""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = {"DEMO-STOCK": "Fictional stock sequence", "DEMO-ETF": "Fictional ETF sequence",
          "DEMO-CRYPTO-A": "Fictional crypto sequence A", "DEMO-CRYPTO-B": "Fictional crypto sequence B"}
MODELS = ["zero", "historical_mean", "ridge", "boosted_trees"]


def build(root=ROOT):
    assets = []
    for symbol, name in ASSETS.items():
        source = root/"results"/symbol
        report = json.loads((source/"report.json").read_text(encoding="utf-8"))
        provenance = json.loads((source/"data.metadata.json").read_text(encoding="utf-8"))
        if report["input_sha256"] != provenance["sha256"]:
            raise ValueError(f"Provenance mismatch: {symbol}")
        with (source/"indicators.csv").open(encoding="utf-8", newline="") as f:
            indicators = {r["target_date"]: r for r in csv.DictReader(f)}
        sessions = {}
        with (source/"predictions.csv").open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                day = row["target_date"]
                if day not in sessions:
                    ind = indicators[day]
                    sessions[day] = {"date": day, "featureDate": row["feature_date"],
                        "actual": float(row["actual"]), "fold": int(row["fold"]),
                        "regime": row["volatility_regime"],
                        "indicators": {k: float(ind[k]) for k in ("return_20", "volatility_20", "ema_gap", "rsi_14", "volume_ratio")},
                        "forecasts": {}}
                if row["model"] in sessions[day]["forecasts"]:
                    raise ValueError("Duplicate model/session prediction")
                sessions[day]["forecasts"][row["model"]] = {
                    "prediction": float(row["predicted"]), "lower": float(row["lower"]), "upper": float(row["upper"])}
        if len(sessions) != report["metrics"]["ridge"]["observations"]:
            raise ValueError("Held-out session count mismatch")
        ordered = [sessions[k] for k in sorted(sessions)]
        if any(set(r["forecasts"]) != set(MODELS) for r in ordered):
            raise ValueError("Missing model prediction")
        assets.append({"symbol": symbol, "name": name, "assetClass": report["asset_class"],
                       "report": report, "provenance": provenance, "sessions": ordered})
    return {"schemaVersion": 1, "models": MODELS, "assets": assets,
            "dataKind": "synthetic", "scope": "Invented engineering examples only. No market data, real tickers, investment performance or live signals."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the committed dashboard bundle is stale")
    args = parser.parse_args()
    content = json.dumps(build(), separators=(",", ":"), allow_nan=False, ensure_ascii=True)+"\n"
    target = ROOT/"assets"/"research.json"
    if args.check:
        if target.read_text(encoding="utf-8") != content:
            raise SystemExit("Dashboard bundle differs from source research artifacts; run build_dashboard.py")
        print("Dashboard bundle matches all four committed synthetic engineering datasets")
    else:
        target.parent.mkdir(exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"Built {target.name}: {len(content):,} bytes")


if __name__ == "__main__":
    main()
