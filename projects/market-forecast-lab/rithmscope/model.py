"""Causal features, purged chronological folds and transparent comparisons."""
from dataclasses import asdict, dataclass
import math

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["return_1", "return_5", "return_20", "volatility_20", "range",
            "body", "ema_gap", "rsi_14", "volume_ratio"]


@dataclass(frozen=True)
class Config:
    folds: int = 3
    test_size: int = 63
    calibration_size: int = 63
    min_train: int = 252
    alpha: float = 0.10
    fee_bps: float = 5.0
    slippage_bps: float = 5.0
    seed: int = 17

    def __post_init__(self):
        if not (1 <= self.folds <= 20 and 10 <= self.test_size <= 1000 and
                20 <= self.calibration_size <= 1000 and self.min_train >= 60):
            raise ValueError("Invalid chronological window sizes")
        if not (0.01 <= self.alpha <= 0.5):
            raise ValueError("alpha must be between .01 and .5")
        if not all(math.isfinite(v) and 0 <= v <= 500 for v in (self.fee_bps, self.slippage_bps)):
            raise ValueError("Costs must be finite, between 0 and 500 basis points per side")


def features(bars):
    close = bars.close
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(14).mean()
    losses = -delta.clip(upper=0).rolling(14).mean()
    rsi = gains / (gains + losses).replace(0, np.nan)
    out = pd.DataFrame({
        "return_1": close.pct_change(fill_method=None),
        "return_5": close.pct_change(5, fill_method=None),
        "return_20": close.pct_change(20, fill_method=None),
        "volatility_20": close.pct_change(fill_method=None).rolling(20).std(),
        "range": (bars.high-bars.low) / close,
        "body": (close-bars.open) / bars.open,
        "ema_gap": close / close.ewm(span=20, adjust=False).mean() - 1,
        "rsi_14": rsi.fillna(0.5),
        "volume_ratio": bars.volume / bars.volume.rolling(20).mean().replace(0, np.nan),
    })
    return out[FEATURES].replace([np.inf, -np.inf], np.nan)


def supervised(bars):
    table = features(bars)
    table["feature_date"] = bars.date
    table["target_date"] = bars.date.shift(-1)
    table["actual"] = (bars.close / bars.open - 1).shift(-1)
    # Only completed target rows; latest completed bar is reserved for a new forecast.
    return table.dropna().reset_index(drop=True)


def splits(length, cfg):
    start = length - cfg.folds * cfg.test_size
    for fold in range(cfg.folds):
        test_start = start + fold * cfg.test_size
        cal_stop = test_start - 1  # one feature row embargoed: its target is not earlier
        cal_start = cal_stop - cfg.calibration_size
        train_stop = cal_start - 1
        if train_stop < cfg.min_train:
            raise ValueError("Too few usable bars for fixed folds; need at least " +
                             str(cfg.min_train + cfg.calibration_size + 2 + cfg.folds * cfg.test_size + 21))
        yield slice(0, train_stop), slice(cal_start, cal_stop), slice(test_start, test_start+cfg.test_size)


def estimator(name, cfg):
    if name == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    if name == "boosted_trees":
        return HistGradientBoostingRegressor(max_iter=80, max_leaf_nodes=7, min_samples_leaf=30,
                                             l2_regularization=10, early_stopping=False, random_state=cfg.seed)
    raise ValueError("Unknown model")


def radius(actual, predicted, alpha):
    errors = np.sort(np.abs(np.asarray(actual)-np.asarray(predicted)))
    rank = math.ceil((len(errors)+1)*(1-alpha))
    if not 1 <= rank <= len(errors):
        raise ValueError("Too few calibration observations for requested interval")
    return float(errors[rank-1])


def predict_block(train, calibration, test, name, cfg):
    if not (train.target_date.max() < calibration.feature_date.min() and
            calibration.target_date.max() < test.feature_date.min()):
        raise ValueError("Label availability violated at a split boundary")
    model = estimator(name, cfg)
    model.fit(train[FEATURES], train.actual)
    predicted = model.predict(test[FEATURES])
    width = radius(calibration.actual, model.predict(calibration[FEATURES]), cfg.alpha)
    return predicted, width


def metrics(frame, cfg):
    y, p = frame.actual.to_numpy(), frame.predicted.to_numpy()
    entered = frame.lower.to_numpy() > 2*(cfg.fee_bps+cfg.slippage_bps)/10000
    # Position is decided on feature day, filled at following open, liquidated at that close.
    c = (cfg.fee_bps+cfg.slippage_bps)/10000
    trade_return = (1+y)*(1-c)/(1+c)-1
    net = np.where(entered, trade_return, 0.0)
    equity = np.r_[1.0, np.cumprod(1+net)]
    drawdown = equity / np.maximum.accumulate(equity) - 1
    always_long = np.cumprod(1+trade_return)[-1]-1
    return {"observations": len(y), "mae": float(np.abs(y-p).mean()),
            "rmse": float(np.sqrt(np.mean((y-p)**2))),
            "direction_accuracy": float(((p > 0) == (y > 0)).mean()),
            "interval_coverage": float(((y >= frame.lower) & (y <= frame.upper)).mean()),
            "mean_interval_width": float((frame.upper-frame.lower).mean()),
            "simulated_trades": int(entered.sum()), "simulated_net_return": float(equity[-1]-1),
            "simulated_max_drawdown": float(drawdown.min()),
            "always_long_intraday_net_return": float(always_long)}


def evaluate(bars, cfg):
    table = supervised(bars)
    all_rows, boundaries = [], []
    for fold, (tr, ca, te) in enumerate(splits(len(table), cfg), 1):
        train, calibration, test = table.iloc[tr], table.iloc[ca], table.iloc[te]
        boundaries.append({"fold": fold, "train_rows": len(train),
                           "train_last_target": str(train.target_date.max().date()),
                           "calibration_first_feature": str(calibration.feature_date.min().date()),
                           "calibration_last_target": str(calibration.target_date.max().date()),
                           "test_first_feature": str(test.feature_date.min().date()),
                           "test_first_target": str(test.target_date.min().date()),
                           "test_last_target": str(test.target_date.max().date())})
        for name in ("zero", "historical_mean", "ridge", "boosted_trees"):
            if name in ("zero", "historical_mean"):
                mean = 0.0 if name == "zero" else float(train.actual.mean())
                predicted = np.full(len(test), mean)
                width = radius(calibration.actual, np.full(len(calibration), mean), cfg.alpha)
            else:
                predicted, width = predict_block(train, calibration, test, name, cfg)
            result = test[["feature_date", "target_date", "actual"]].copy()
            result["model"], result["fold"] = name, fold
            result["predicted"] = predicted
            result["lower"], result["upper"] = predicted-width, predicted+width
            all_rows.append(result)
    predictions = pd.concat(all_rows, ignore_index=True)
    predictions["long_candidate"] = False
    predictions["strategy_return"] = 0.0
    predictions["strategy_equity"] = 1.0
    totals, folds = {}, []
    for name, frame in predictions.groupby("model", sort=True):
        totals[name] = metrics(frame, cfg)
        for fold, group in frame.groupby("fold"):
            folds.append({"model": name, "fold": int(fold), **metrics(group, cfg)})
        cost = (cfg.fee_bps+cfg.slippage_bps)/10000
        entries = frame.lower > 2*cost
        net = np.where(entries, (1+frame.actual)*(1-cost)/(1+cost)-1, 0.0)
        predictions.loc[frame.index, "long_candidate"] = entries.to_numpy()
        predictions.loc[frame.index, "strategy_return"] = net
        predictions.loc[frame.index, "strategy_equity"] = np.cumprod(1+net)
    return {"config": asdict(cfg), "boundaries": boundaries, "metrics": totals,
            "fold_metrics": folds}, predictions


def forecast(bars, cfg):
    table = supervised(bars)
    latest = features(bars).iloc[[-1]].copy()
    if latest.isna().any().any():
        raise ValueError("Latest completed bar has insufficient finite features")
    calibration = table.iloc[-cfg.calibration_size:]
    train = table.iloc[:len(table)-cfg.calibration_size-1]
    if len(train) < cfg.min_train:
        raise ValueError("Insufficient forecast training history")
    model = estimator("ridge", cfg)  # fixed in advance; no holdout-driven winner selection
    model.fit(train[FEATURES], train.actual)
    p = float(model.predict(latest)[0])
    width = radius(calibration.actual, model.predict(calibration[FEATURES]), cfg.alpha)
    cost = 2*(cfg.fee_bps+cfg.slippage_bps)/10000
    return {"model": "ridge", "as_of_completed_bar": str(bars.date.iloc[-1].date()),
            "horizon": "next observed session open-to-close; not a closing price target",
            "predicted_return": p, "lower": p-width, "upper": p+width,
            "nominal_coverage": 1-cfg.alpha,
            "research_signal": "LONG_CANDIDATE" if p-width > cost else "ABSTAIN",
            "reason": "Lower interval bound must exceed round-trip cost estimate; no broker execution"}
