import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from rithmscope.__main__ import main
from rithmscope.data import load, validate
from rithmscope.model import Config, FEATURES, evaluate, features, forecast, metrics, radius, splits, supervised
from rithmscope.report import render
from rithmscope.demo_data import fixture


class DataTests(unittest.TestCase):



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






class ResearchTests(unittest.TestCase):
    cfg = Config(folds=2, test_size=30, calibration_size=30, min_train=100)

    def test_public_outcomes_match_independent_fictional_generator(self):
        from generate_demo_research import DEMO
        root = Path(__file__).resolve().parents[1]
        for symbol, _, seed, calendar in DEMO:
            bars = fixture(900, seed=seed, calendar=calendar)
            expected = dict(zip(bars.date.dt.strftime("%Y-%m-%d"), bars.close/bars.open-1))
            observed = pd.read_csv(root/"results"/symbol/"predictions.csv")
            for day, value in zip(observed.target_date, observed.actual):
                self.assertAlmostEqual(value, expected[day], places=10)

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
