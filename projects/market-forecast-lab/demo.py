"""Offline engineering demo. Invented prices, never market evidence."""
import argparse
from pathlib import Path

from rithmscope.__main__ import main
from rithmscope.demo_data import fixture

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", default="output/synthetic-demo")
args = parser.parse_args()
root = Path(args.output)
root.mkdir(parents=True, exist_ok=True)
path = root/"SYNTHETIC.csv"
fixture(620).to_csv(path, index=False)
raise SystemExit(main(["evaluate", "--csv", str(path), "--symbol", "SYNTHETIC-NOT-MARKET-DATA",
                       "--asset-class", "stock", "--through", "2024-01-01", "--source", "Invented engineering fixture, seed 29",
                       "--output", str(root)]))
