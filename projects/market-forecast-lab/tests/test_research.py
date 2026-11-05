import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from rithmscope.__main__ import main
from rithmscope.data import COLUMNS, alphavantage, coinbase, load, validate, yahoo_snapshot
from rithmscope.model import Config, FEATURES, evaluate, features, forecast, metrics, radius, splits, supervised
from rithmscope.report import render
from rithmscope.demo_data import fixture


class DataTests(unittest.TestCase):
    def yahoo_payload(self):
        days = pd.date_range("2023-01-01 14:30", periods=65, tz="UTC")
        return {"chart": {"result": [{"meta": {"symbol": "SPY", "exchangeTimezoneName": "America/New_York"},
            "timestamp": [int(d.timestamp()) for d in days], "indicators": {
                "quote": [{"open": [100]*65, "high": [110]*65, "low": [90]*65, "close": [105]*65, "volume": [1000]*65}],
                "adjclose": [{"adjclose": [52.5]*65}]}}]}}

    def test_yahoo_snapshot_adjustment_and_exchange_dates(self):
        frame = yahoo_snapshot("SPY", "2023-01-01", "2023-03-07", request=lambda _: self.yahoo_payload())
        self.assertEqual(frame.open.iloc[0], 50)
        self.assertEqual(frame.close.iloc[0], 52.5)
        self.assertEqual(str(frame.date.iloc[0].date()), "2023-01-01")

    def test_yahoo_snapshot_rejects_missing_values_and_symbol_mismatch(self):
        p = self.yahoo_payload()
        p["chart"]["result"][0]["indicators"]["quote"][0]["open"][0] = None
        with self.assertRaisesRegex(ValueError, "Missing"):
            yahoo_snapshot("SPY", "2023-01-01", "2023-03-07", request=lambda _: p)
        with self.assertRaisesRegex(ValueError, "symbol mismatch"):
            yahoo_snapshot("AMD", "2023-01-01", "2023-03-07", request=lambda _: self.yahoo_payload())
        p = self.yahoo_payload()
        p["chart"]["result"][0]["indicators"]["quote"][0]["close"][0] = 0
        with self.assertRaisesRegex(ValueError, "closing price"):
            yahoo_snapshot("SPY", "2023-01-01", "2023-03-07", request=lambda _: p)

    def test_reject_duplicate_or_unsorted_dates(self):
        for change in (lambda f: f.assign(date=f.date.iloc[0]), lambda f: f.iloc[::-1]):
            with self.assertRaises(ValueError): validate(change(fixture()))

    def test_reject_bad_ohlc_nonfinite_and_volume(self):
        for field, value in [("low", 100000), ("close", 0), ("open", np.inf), ("volume", -1)]:
            frame = fixture()
            frame.loc[7, field] = value
            with self.assertRaises(ValueError): validate(frame)

    def test_reject_ambiguous_dates_and_schema(self):
        for frame in [fixture().assign(extra=1), fixture().assign(date="01/02/2023")]:
            with self.assertRaises(ValueError): validate(frame)

    def test_completion_cutoff_and_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"bars.csv"
            fixture().to_csv(path, index=False)
            bars, digest = load(path, "2022-05-01")
            self.assertEqual(str(bars.date.max().date()), "2022-05-01")
            self.assertEqual(len(digest), 64)
            with self.assertRaises(ValueError): load(path, "2099-01-01")

    def test_stock_adapter_adjusts_all_price_fields_together(self):
        payload = {"Time Series (Daily)": {str(d.date()): {
            "1. open": "100", "2. high": "110", "3. low": "90", "4. close": "105",
            "5. adjusted close": "52.5", "6. volume": "1000"}
            for d in pd.date_range("2023-01-01", periods=65)}}
        with patch.dict(os.environ, {"ALPHAVANTAGE_API_KEY": "test-not-a-real-key"}):
            frame = alphavantage("SPY", request=lambda _: payload)
        self.assertEqual(frame.open.iloc[0], 50)
        self.assertEqual(frame.high.iloc[0], 55)
        self.assertEqual(frame.close.iloc[0], 52.5)

    def test_stock_adapter_entitlement_error_is_clear(self):
        with patch.dict(os.environ, {"ALPHAVANTAGE_API_KEY": "test"}):
            with self.assertRaisesRegex(ValueError, "entitlement"):
                alphavantage("AMD", request=lambda _: {"Information": "limited"})

    def test_coinbase_reverse_order_extra_rows_and_no_gap_filling(self):
        dates = pd.date_range("2023-01-01", periods=65, tz="UTC")
        rows = [[int(d.timestamp()), 90, 110, 100, 105, 1000] for d in dates]
        frame = coinbase("BTC-USD", "2023-01-01", "2023-03-07", request=lambda _: rows[::-1])
        self.assertEqual(len(frame), 65)
        self.assertTrue(frame.date.is_monotonic_increasing)
        with self.assertRaisesRegex(ValueError, "Missing"):
            coinbase("BTC-USD", "2023-01-01", "2023-03-07", request=lambda _: rows[:-1])

    def test_provider_path_injection_rejected(self):
        with self.assertRaises(ValueError): coinbase("../accounts", "2023-01-01", "2023-04-01")
        with self.assertRaises(ValueError): alphavantage("X&apikey=other")


class ResearchTests(unittest.TestCase):
    cfg = Config(folds=2, test_size=30, calibration_size=30, min_train=100)

    def test_causal_features_do_not_change_when_future_changes(self):
        original = fixture()
        mutated = original.copy()
        mutated.loc[401:, ["open", "high", "low", "close", "volume"]] *= 9
        assert_frame_equal(features(original).iloc[:401], features(mutated).iloc[:401])

    def test_target_is_following_session_open_to_close(self):
        bars = fixture()
        row = supervised(bars).iloc[0]
        target = bars.loc[bars.date == row.target_date].iloc[0]
        self.assertAlmostEqual(row.actual, target.close/target.open-1)
        self.assertGreater(row.target_date, row.feature_date)

    def test_all_split_targets_are_known_before_next_block(self):
        table = supervised(fixture())
        covered = []
        for train, cal, test in splits(len(table), self.cfg):
            self.assertLess(table.iloc[train].target_date.max(), table.iloc[cal].feature_date.min())
            self.assertLess(table.iloc[cal].target_date.max(), table.iloc[test].feature_date.min())
            covered.extend(range(test.start, test.stop))
        self.assertEqual(len(covered), len(set(covered)))
        self.assertEqual(covered[-1], len(table)-1)

    def test_volatility_thresholds_use_only_initial_training_history(self):
        bars = fixture(320)
        report, rows = evaluate(bars, self.cfg)
        table = supervised(bars)
        first_train = table.iloc[next(splits(len(table), self.cfg))[0]]
        self.assertAlmostEqual(report["regime_thresholds"]["lower"], first_train.volatility_20.quantile(1/3))
        self.assertAlmostEqual(report["regime_thresholds"]["upper"], first_train.volatility_20.quantile(2/3))
        self.assertTrue(set(rows.volatility_regime) <= {"lower", "middle", "higher"})

    def test_future_fold_cannot_change_first_fold_predictions(self):
        bars = fixture(320)
        table = supervised(bars)
        first_test = list(splits(len(table), self.cfg))[0][2]
        last_first_target = table.iloc[first_test].target_date.max()
        changed = bars.copy()
        changed.loc[changed.date > last_first_target, ["open", "high", "low", "close"]] *= 2
        _, before = evaluate(bars, self.cfg)
        _, after = evaluate(changed, self.cfg)
        assert_frame_equal(before[before.fold == 1], after[after.fold == 1])

    def test_calibration_quantile_uses_finite_sample_rank(self):
        self.assertEqual(radius(np.arange(1, 10), np.zeros(9), .1), 9)
        with self.assertRaises(ValueError): radius([1], [0], .01)

    def test_costs_charge_both_sides_and_no_trade_means_no_cost(self):
        frame = pd.DataFrame({"actual": [0., 0.], "predicted": [.1, .1], "lower": [.05, -.05], "upper": [.2, .2]})
        cfg = Config(fee_bps=50, slippage_bps=50)
        m = metrics(frame, cfg)
        self.assertEqual(m["simulated_trades"], 1)
        self.assertAlmostEqual(m["simulated_net_return"], .99/1.01-1)
        self.assertAlmostEqual(m["simulated_max_drawdown"], .99/1.01-1)

    def test_invalid_costs_and_insufficient_history_fail(self):
        for cost in [-1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError): Config(fee_bps=cost)
        with self.assertRaises(ValueError): list(splits(200, Config()))

    def test_reproducible_models_and_report_html_escaping(self):
        a, rows = evaluate(fixture(320), self.cfg)
        b, other = evaluate(fixture(320), self.cfg)
        self.assertEqual(a, b)
        assert_frame_equal(rows, other)
        self.assertEqual(set(a["metrics"]), {"zero", "historical_mean", "ridge", "boosted_trees"})
        a.update(symbol="<script>alert(1)</script>", asset_class="stock", first_date="2022-01-01",
                 last_date="2023-01-01", source="<img src=x>", input_sha256="abc", input_rows_used=320)
        html = render(a, rows)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_forecast_preserves_latest_completed_bar(self):
        bars = fixture(320)
        result = forecast(bars, self.cfg)
        self.assertEqual(result["as_of_completed_bar"], str(bars.date.iloc[-1].date()))
        self.assertLessEqual(result["lower"], result["predicted_return"])
        self.assertLess(result["predicted_return"], result["upper"])
        self.assertIn(result["research_signal"], {"ABSTAIN", "LONG_CANDIDATE"})

    def test_cli_stock_etf_crypto_use_same_validated_pipeline(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"bars.csv"
            fixture().to_csv(path, index=False)
            for kind in ("stock", "etf", "crypto"):
                dest = Path(folder)/kind
                code = main(["forecast", "--csv", str(path), "--symbol", "SYNTHETIC",
                             "--asset-class", kind, "--through", "2024-01-01", "--source", "Synthetic test",
                             "--output", str(dest)])
                self.assertEqual(code, 0)
                report = json.loads((dest/"forecast.json").read_text())
                self.assertEqual(report["asset_class"], kind)


if __name__ == "__main__":
    unittest.main()
