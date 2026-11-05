# RithmScope · Market Forecast Lab

**[Open the synthetic engineering demonstration](https://rithmsai.github.io/tripleten-portfolio/projects/market-forecast-lab/)**

Python 3.12 · scikit-learn · chronological evaluation · uncertainty intervals · responsive dashboard

## Current public scope

The public dashboard contains **invented prices only**. DEMO-STOCK, DEMO-ETF, DEMO-CRYPTO-A and DEMO-CRYPTO-B are fictional sequences, not actual securities, funds, tokens or venue observations. Every forecast, indicator, chart, score and simulated return in the bundled outputs is derived from an independent random generator. These examples demonstrate engineering behavior and establish no real-world prediction accuracy, trading performance or market edge.

Earlier versions included third-party market-derived research outputs. Those outputs and direct provider-download adapters have been removed from the current branch and demo following a review of data-use restrictions. This normal update does not erase earlier commits, forks, downloads or copies, and is not a determination that earlier use was authorized. Historical exposure and any commercial use require separate review.

## What the software demonstrates

- Nine causal features: 1/5/20-session returns, 20-session volatility, range/body, EMA gap, normalized rolling RSI and relative volume.
- Ridge regression and gradient boosted trees compared with zero-return and historical-mean baselines.
- Prediction target: the following observed bar's open-to-close fractional return, using the preceding completed bar's features.
- Three expanding test folds, separate earlier calibration blocks and one-row gaps at both boundaries to prevent unavailable labels crossing a split.
- Empirical residual-based nominal 90% intervals, with measured coverage rather than guaranteed coverage claims.
- Training-only volatility-group thresholds, frozen across all folds.
- A dependency-free browser dashboard with SVG charts, session inspection, model/fold/group selection and CSV/JSON exports.
- An exploratory long/cash simulator with fees, slippage, entry buffer and separate interval-bound/point-forecast rules.

No accounts, live quotes, model-provider calls, external data downloads, broker integration or order execution are included. The browser reads a bundled synthetic JSON file; Python performs local model fitting. No server, analytics service or external chart CDN is required.

## Run locally

Use Python 3.12 from this directory:

```bash
python -m venv .venv
# Windows PowerShell activation:
.venv\Scripts\Activate.ps1
# macOS/Linux alternative: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python demo.py
python build_dashboard.py --check
node --test tests/dashboard.test.mjs
python -m http.server 8000
```

Open http://localhost:8000. Node 24 is used for the JavaScript tests; the browser application itself has no Node build step. `demo.py` also creates a standalone HTML report in `output/synthetic-demo/`. Run the activation command appropriate to your OS.

To regenerate all four public examples without network access:

```bash
python generate_demo_research.py
python build_dashboard.py
python build_dashboard.py --check
node --test tests/dashboard.test.mjs
```

Each example has 900 independently generated input rows. Fixed seeds 101/202/303/404 and the generator source are recorded in its manifest. The fictional stock/ETF examples use a business-day sequence, not a verified exchange holiday calendar. Crypto-shaped examples use daily date steps. Differences among these invented sequences are not real asset comparisons.

## User-supplied CSV research

The local engine accepts a CSV with exactly `date,open,high,low,close,volume`, ascending unique ISO dates, finite positive OHLC prices, consistent high/low bounds and nonnegative volume. Default evaluation requires at least 527 raw bars without missing feature rows. All four prices must share a consistent adjustment basis.

```bash
python -m rithmscope evaluate --csv your-authorized-bars.csv --symbol YOUR-SYMBOL --asset-class stock --through 2025-12-31 --source "Your independently authorized source" --output output/private-run
python -m rithmscope forecast --csv your-authorized-bars.csv --symbol YOUR-SYMBOL --asset-class stock --through 2025-12-31 --source "Your independently authorized source" --output output/private-run
```

`--asset-class` also accepts `etf` and `crypto`. Dates are examples, not instructions to obtain or use any provider's data. Verify that your rights explicitly cover the intended access, ML training/evaluation, retention, display, derived outputs and commercial use. A public endpoint, API key or paid subscription alone does not establish those rights. The engine cannot certify data licensing, corporate actions, session completeness or commercial suitability. Keep private or restricted input and output files out of public git.

The completion cutoff must precede today's UTC date. Later rows are excluded, while the input fingerprint covers the whole CSV. The latest available bar may be stale; forecasts always identify their completed-bar date. There is no automatic freshness assertion or market-hours service.

## Evaluation and simulation contract

At completed bar t, inputs use only bars through t. The target is close[t+1]/open[t+1] - 1. Training labels precede calibration feature dates; calibration labels precede test feature dates. Ridge scaling uses training rows only. Trees disable random early-stopping validation. Calibration does not fit the estimator. Later folds may train on earlier outcomes after those outcomes become historical. All model settings are fixed; there is no test-driven winner selection.

Absolute calibration errors are sorted; interval radius is order statistic ceil((n+1)*(1-alpha)). Market dependence and distribution changes can invalidate nominal coverage. No distribution-free guarantee or calibrated win probability is claimed. Public examples use invented data and cannot validate these assumptions for financial use.

Volatility groups use first-fold training terciles of 20-session volatility and remain fixed. Group metrics reuse the selected observed outcomes, may contain very few rows and are descriptive rather than independent validation.

The conservative entry rule requires lower interval bound > 2*(fee_bps+slippage_bps)/10000 plus any sandbox buffer. The exploratory point rule substitutes the point forecast. A modeled trade enters at the next open and exits at that close; its net factor is (1+actual_return)*(1-c)/(1+c), with per-side cost c. Cash has zero return. Defaults of 5 bps fee and 5 bps slippage per side are hypothetical and do not quote any broker. No-trade results have no win-rate claim.

The always-long intraday comparison pays daily round-trip costs and is not buy-and-hold. Starting cash is included in drawdown calculations. Selected volatility-group simulations omit other dates. Latency, auctions, spread dynamics, liquidity, market impact, taxes, financing, interest, leverage, shorts and portfolio capital allocation are not modeled. Sandbox adjustments do not retrain the model or create an untouched test.

## Verification and public artifacts

16 Python tests exercise strict input validation, chronological label availability, future-input perturbations, training-only regime thresholds, finite-sample calibration, two-sided costs, deterministic results, forecasting, three asset-class CLI paths and HTML escaping. 15 JavaScript tests exercise filtering, simulation costs, initial-trade drawdown, abstention, empty selections, malformed inputs and synthetic-only provenance. Browser calculations reconcile with all 16 synthetic asset/model Python result sets. GitHub Actions runs both suites and the deterministic bundle check on Windows and Linux without provider requests or account keys.

`results/DEMO-*/` contains synthetic report.json, predictions.csv, indicators.csv, report.html and data.metadata.json. `build_dashboard.py` checks their manifests and derives `assets/research.json`; `--check` rejects a stale bundle. Public files must be regenerated from independent fictional inputs, not substituted market observations or adjusted scores.

## Commercial boundary and licensing

This public research code was released under the MIT License. MIT permits commercial use, modification and redistribution subject to its conditions, and permits others to exercise those rights too. This project does not promise exclusive commercial rights to code already released. The MIT notice is retained; it does not license third-party data or authorize uses restricted by data-provider agreements.

A future paid offering would require a separately designed private service, a deliberate licensing/ownership decision, appropriately authorized data, customer terms and a review of applicable financial regulation. That offering does not exist in this public repository. An educational label or disclaimer does not determine regulatory status. No SEC/FINRA approval, compliance certification, expected return or paid-product readiness is claimed.

This cleanup changes the current branch and deployed demonstration; it does not remove earlier material from repository history or third-party copies. Review that history before making exclusivity, rights-clearance or commercial-launch claims.

Created by Kaya Robinson / rithmsAI. AI-assisted development was used. Source, assumptions, synthetic provenance and validation are available for review.
