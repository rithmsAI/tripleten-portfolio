# RithmScope · Market Forecast Lab

**Can a daily return forecast improve on simple baselines once time ordering, uncertainty and trading costs are respected?** RithmScope makes that question reproducible for stocks, ETFs and crypto. It produces auditable forecasts, evaluation tables and a portable HTML report rather than treating an indicator as a profitable strategy.

Python 3.12 · scikit-learn · chronological evaluation · empirical prediction intervals · read-only data adapters

**[Open the interactive research dashboard](https://rithmsai.github.io/tripleten-portfolio/projects/market-forecast-lab/)**

## Interactive dashboard

The browser application explores **real, committed historical research outputs** for AMD (stock), SPY (ETF), BTC-USD and ETH-USD. Select an asset, model, evaluation fold and volatility group. Inspect individual sessions with the chart or keyboard-accessible slider, compare every model against the same zero baseline, and explore a cost-sensitive strategy simulation. Data dates and input fingerprints remain visible.

The simulator distinguishes the original interval-based entry rule from an **exploratory point-forecast rule**. Fee, slippage and entry-buffer controls operate on frozen predictions; they do not retrain a model or create an untouched performance test. CSV exports include the selected forecasts, simulated outcomes and execution assumptions. JSON exports include provenance, original evaluation, selection and exploratory simulation configuration.

This is a buildless, dependency-free browser interface with native SVG charts, accessible controls and responsive layouts. The Python pipeline performs model training locally; the public interface has no backend, broker access, credentials, live quotes or trade execution. No analytics or external chart CDN is required. The rithmsAI portfolio homepage and résumé are not changed by this dashboard update.

To preview the dashboard locally from this folder, run `python -m http.server 8000` and open `http://localhost:8000`. Opening `index.html` directly as a file will not load the JSON bundle in browsers that restrict file-origin fetches.

## What it does

- Builds nine causal price/volume features from completed daily bars: 1/5/20-session returns, 20-session volatility, daily range/body, EMA gap, normalized rolling RSI and relative volume.
- Compares **Ridge regression and gradient boosted trees** against **zero-return and past-mean baselines**, reporting every model and fold.
- Predicts **the next observed session's open-to-close fractional return**. It does not predict an exact future price, market top, or calibrated probability of winning.
- Uses expanding training windows, a separate past calibration block, and one-row gaps to keep future labels out of each stage.
- Estimates nominal 90% residual-based prediction intervals and measures their realized coverage.
- Simulates a long/cash rule with fees and slippage charged on entry and exit. It can abstain; abstention is not a profitable trade.
- Exports JSON provenance/settings, per-session predictions/positions/equity, and a standalone HTML report with no external scripts or server.

## Real-data experiments: no demonstrated forecasting edge

AMD and SPY use Yahoo Finance public chart snapshots over 2023-01-01 through 2025-12-31, **752 input sessions each**. Their final 189 target sessions run from **2025-04-02 through 2025-12-31**. Crypto has more sessions per year, so its last-189-session window is different; asset runs are independent and are not a combined portfolio or calendar-matched asset ranking.

| Asset | Model | MAE, percentage points | Direction accuracy | Conservative simulated trades |
|---|---|---:|---:|---:|
| AMD | Zero baseline | 2.006 | 49.7% | 0 |
| AMD | Historical mean | 2.007 | 47.1% | 0 |
| AMD | Ridge | 2.064 | 50.3% | 0 |
| AMD | Boosted trees | 2.088 | 55.0% | 0 |
| SPY | Zero baseline | 0.603 | 48.1% | 0 |
| SPY | Historical mean | 0.603 | 51.9% | 0 |
| SPY | Ridge | 0.628 | 49.7% | 1 |
| SPY | Boosted trees | 0.619 | 50.8% | 1 |

Both learned models have higher forecast MAE than the zero baseline on AMD and SPY too. The conservative SPY rule enters **one** trade for each learned model (the same observed session); each isolated simulation returns about **+0.407%** after default modeled costs. One profitable observation is not evidence of a robust strategy. The dashboard flags small trade samples. [AMD evidence](results/AMD/report.json) · [SPY evidence](results/SPY/report.json).

Coinbase BTC-USD and ETH-USD daily UTC bars, **2023-01-01 through 2025-12-31**, 1,096 input bars each. Evaluation uses the final **189 target sessions, 2025-06-26 through 2025-12-31**, in three non-overlapping 63-session test blocks. All model settings are fixed in source; there is no holdout-driven winner selection.

| Asset | Model | MAE, percentage points | Direction accuracy | Nominal 90% interval coverage | Simulated trades |
|---|---|---:|---:|---:|---:|
| BTC-USD | Zero baseline | 1.405 | 50.8% | 90.5% | 0 |
| BTC-USD | Historical mean | 1.420 | 49.2% | 88.9% | 0 |
| BTC-USD | Ridge | 1.439 | 49.2% | 89.4% | 0 |
| BTC-USD | Boosted trees | 1.501 | 51.9% | 86.2% | 0 |
| ETH-USD | Zero baseline | 2.552 | 47.6% | 89.9% | 0 |
| ETH-USD | Historical mean | 2.554 | 52.4% | 90.5% | 0 |
| ETH-USD | Ridge | 2.586 | 47.6% | 90.5% | 0 |
| ETH-USD | Boosted trees | 2.683 | 48.1% | 90.5% | 0 |

**Both learned models have higher MAE than the zero baseline on both crypto assets.** The crypto interval-based rule never enters: simulated net return and drawdown are both zero because it holds cash, not because it found a safe profitable strategy. These results do not establish a useful trading edge. This sample is small and its outcomes do not establish statistical significance.

[BTC results](results/BTC-USD/report.json) · [ETH results](results/ETH-USD/report.json) · [BTC predictions](results/BTC-USD/predictions.csv) · [ETH predictions](results/ETH-USD/predictions.csv). Download `results/<symbol>/report.html` to view the visual report locally. Input hashes and retrieval manifests are included; raw provider bars are kept out of git. This repository contains derived research outputs, not a licensed market-data redistribution service.

## Run locally

From this project directory, use Python 3.12 in a virtual environment:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux alternative: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python demo.py
```

Open `output/synthetic-demo/report.html`. **This offline demo contains invented prices, not market results.** It needs no keys, trading account, or network connection after dependency installation. Run commands one line at a time; use the activation command for your OS.

### Reproduce the real crypto experiment

```bash
python -m rithmscope download --provider coinbase --symbol BTC-USD --start 2023-01-01 --end 2026-01-01 --output data/BTC-USD.csv
python -m rithmscope evaluate --csv data/BTC-USD.csv --symbol BTC-USD --asset-class crypto --through 2025-12-31 --source "Coinbase Exchange daily UTC candles" --output output/BTC-USD
python -m rithmscope forecast --csv data/BTC-USD.csv --symbol BTC-USD --asset-class crypto --through 2025-12-31 --source "Coinbase Exchange daily UTC candles" --output output/BTC-USD
```

Repeat with `ETH-USD`. The download end is **exclusive**. The example forecast is historical as of December 31, 2025, not today's signal. For a newer research run, download a later completed range, supply its completion cutoff, and rerun. Forecasting always uses the prespecified Ridge model, even if another model scored better on a test fold.

The Coinbase adapter is public/read-only, paginates 250-day chunks, filters extra response candles, sorts, detects conflicting duplicates and rejects missing UTC days. Missing bars are not forward filled. Historical providers may revise data; a new download can have a different hash and results. Coinbase documents incomplete historical intervals and a 300-candle limit per request.

### Stocks and ETFs

Use the same `evaluate` and `forecast` commands with `--asset-class stock` or `--asset-class etf`. AMD and SPY now have measured historical results above. The Alpha Vantage adapter remains covered by mocked-provider tests; no authenticated Alpha Vantage download has been verified.

To reproduce the included stock/ETF snapshot import:

```bash
python -m rithmscope download --provider yahoo-snapshot --symbol SPY --start 2023-01-01 --end 2026-01-01 --output data/SPY.csv
python -m rithmscope evaluate --csv data/SPY.csv --symbol SPY --asset-class etf --through 2025-12-31 --source "Yahoo Finance public chart snapshot" --output output/SPY
```

Repeat with `AMD` and `--asset-class stock`. **Yahoo's public chart endpoint is experimental, not a supported API contract or a production feed.** Availability may change; failure is explicit and does not silently substitute another source. No authentication, cookie or access restriction is bypassed. Yahoo's [SPY](https://finance.yahoo.com/quote/SPY/history/) and [AMD](https://finance.yahoo.com/quote/AMD/history/) history pages identify the source instruments. All OHLC fields are scaled consistently by adjusted-close/raw-close; volume retains the provider's values. Dates use the exchange timezone. Adjustment histories are retrospective and can be revised. Provider terms continue to apply; use licensed CSV imports for a stable, entitled data workflow. Raw bars are not committed.

Option A: provide a CSV you are entitled to use, with **exactly** these columns and ascending unique session dates:

```csv
date,open,high,low,close,volume
2025-01-02,100,103,99,102,1000000
2025-01-03,102,104,101,103,1100000
```

Those two rows show the schema only. Default evaluation needs at least **527 raw bars** without missing feature rows; use several years. All four OHLC prices must use a consistent adjustment basis. Do not mix adjusted close with raw open. You must verify exchange sessions, symbol identity, corporate actions, provider licensing and that each included bar is complete. The CSV validator cannot certify these.

Option B: use the read-only Alpha Vantage adjusted daily adapter:

```powershell
$env:ALPHAVANTAGE_API_KEY = "your-local-key"
python -m rithmscope download --provider alphavantage --symbol SPY --output data/SPY.csv
python -m rithmscope evaluate --csv data/SPY.csv --symbol SPY --asset-class etf --through 2025-12-31 --source "Alpha Vantage adjusted daily" --output output/SPY
```

The **adjusted daily/full history endpoint may require a paid provider entitlement**; do not assume a free key is sufficient. No purchase is required to use CSV imports or the crypto demo. The adapter applies `adjusted_close / raw_close` to all OHLC prices; volume remains the provider's raw volume. Adjustment histories can be revised, and raw volume can jump around splits. API keys stay in environment variables and are never included in output manifests. Provider requests are read-only; broker credentials are not used.

## Evaluation and simulation contract

At completed bar `t`, features use only bars up to `t`; the target is `close[t+1]/open[t+1] - 1`. Each fold uses all earlier training rows, one omitted feature row, 63 calibration rows, another omitted feature row, and 63 test rows. The omitted rows ensure the last label in a block predates the first feature date in the next block. Calibration data does not fit the model. Trees disable random early-stopping validation; the Ridge scaler fits training rows only. Later folds may train on outcomes from earlier folds once those outcomes are historical. No random train/test split is used.

For residual radius, sort absolute calibration errors and take order statistic `ceil((n+1)*(1-alpha))`. Intervals are `prediction ± radius`. This resembles split conformal calibration, but **market observations are dependent and nonstationary; no distribution-free coverage guarantee is claimed**. Nominal coverage is a target, not a success probability or a confidence level about profitability.

Entry is decided using `lower_bound > 2*(fee_bps + slippage_bps)/10000`. Entry is modeled at the following session's open and exit at its close, using 100% of the isolated per-symbol research notional; cash otherwise earns zero. A trade's net factor is `(1 + actual_return) * (1-c)/(1+c)`, where `c` is the per-side combined cost. The entry threshold is a conservative approximate cost screen; the realized cost formula is used for P&L. There is no leverage, shorting, cross-asset capital allocation or order handling.

Default fees and slippage are **hypothetical 5 bps each per side**, not a quote from a broker or exchange. Change both with CLI flags. Always-long intraday is a same-window comparison with the same daily round-trip costs; it is **not buy-and-hold**. Crypto UTC boundaries offer essentially no computation delay between bars: modeled next-open fills are idealized and may not be attainable. Equity auction availability, latency, spread changes, market impact, partial fills, taxes, financing and cash interest are not modeled. No annualized Sharpe ratio is reported.

`--through` is the user's explicit completed-bar cutoff and must precede today's UTC date. Data after it is excluded; the hash covers the whole input file. Forecasts use the last available completed bar, which can be stale; `as_of_completed_bar` is always included. Stocks/ETFs use observed session order rather than a hard-coded holiday calendar. No claim of current live-market status is made.

Volatility groups are defined using the 33rd/67th percentiles of 20-session volatility in the **first fold's training rows** and then frozen across all folds. Each test session's group uses its preceding completed bar's feature. Dashboard subgroup metrics are descriptive, can have very few observations, and reuse the same held-out sample. Selecting a group in the sandbox compounds only those selected sessions; omitted dates are excluded from that exploratory comparison. Group results must not be mistaken for an independently validated regime-switching strategy.

## Verification and files

**21 Python tests and 14 JavaScript tests** exercise malformed data, adjustment consistency, provider failures, chronological label availability, future-data perturbations, training-only regime thresholds, finite-sample calibration, two-sided costs, first-trade drawdown, abstention, empty selections, deterministic results, stock/ETF/crypto CLI paths and HTML escaping. Browser calculations are reconciled with all 16 asset/model Python result sets. GitHub Actions runs both suites, a deterministic dashboard-bundle check and an offline end-to-end demo on Linux and Windows; no account keys or provider network requests are required in CI.

```bash
python build_dashboard.py --check
node --test tests/dashboard.test.mjs
```

`build_dashboard.py` derives `assets/research.json` from committed JSON/CSV outputs. Regenerating model results also writes `indicators.csv` with derived features for the held-out target sessions. After intentionally replacing the source artifacts, run `python build_dashboard.py` and rerun the checks. Never change the browser bundle alone to improve a displayed result.

```text
rithmscope/data.py       bounded CSV validation and read-only provider adapters
rithmscope/model.py      features, folds, models, calibration, simulation
rithmscope/report.py     self-contained HTML and SVG report
rithmscope/__main__.py   download / evaluate / forecast CLI
tests/                  leakage and behavior checks
results/                measured AMD/SPY/BTC/ETH outputs and provenance
index.html              interactive research dashboard
assets/core.mjs         independently tested browser calculations
assets/app.mjs          controls, SVG charts and downloads
assets/research.json    deterministic bundle of four real-data experiments
build_dashboard.py      bundle generation and stale-output checks
```

For review: start with the split-boundary tests, compare the zero baseline with the learned models, inspect `boundaries` and `fold_metrics` in JSON, then reconcile predictions with the source hash. Separate asset runs are independent experiments; their returns cannot be summed into a portfolio return.

## Boundaries and next experiments

This is an independent engineering and forecasting research project, not an autonomous trading bot. It has no Robinhood, E-Trade, TradingView or order-routing integration. It does not cover options, forex, news sentiment or intraday streaming. It is not a registered advisory service or a claim of SEC/FINRA approval. Broker integration would require separate design, authorization and operational controls.

Useful next experiments: validate corporate-action handling and exchange calendars against a licensed point-in-time feed; predefine additional assets and longer horizons; add nested chronological model selection if tuning is introduced; measure execution latency and realistic venue costs; keep a genuinely untouched forward paper-research period. The current test window is now observed and must not be presented as a new untouched test after tuning. No scheduled data refresh or forward-forecast archive is active.

Primary references: [Coinbase candle API](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles), [Alpha Vantage adjusted daily API](https://www.alphavantage.co/documentation/#dailyadj), [scikit-learn time-series evaluation and uncertainty example](https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html).

Created by Kaya Robinson / **rithmsAI**. AI-assisted development was used; source, assumptions, tests and measured limitations are available for review. MIT-licensed code; third-party data retains its providers' terms.
