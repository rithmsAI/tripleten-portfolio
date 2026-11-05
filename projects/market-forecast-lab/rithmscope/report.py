"""Portable, escaped, network-free HTML report; no dashboard server needed."""
from html import escape
import numpy as np


def render(report, predictions):
    rows = []
    for name, m in report["metrics"].items():
        rows.append(f"<tr><th>{escape(name)}</th><td>{m['mae']*100:.3f}%</td>"
                    f"<td>{m['direction_accuracy']:.1%}</td><td>{m['interval_coverage']:.1%}</td>"
                    f"<td>{m['mean_interval_width']:.1%}</td><td>{m['simulated_trades']}</td>"
                    f"<td>{m['simulated_net_return']:.2%}</td></tr>")
    ridge = predictions[predictions.model == "ridge"]
    vals = np.r_[ridge.actual, ridge.lower, ridge.upper]
    lo, hi = float(vals.min()), float(vals.max())
    span = max(hi-lo, .001)
    def coords(values):
        return " ".join(f"{30+i*940/max(len(values)-1,1):.2f},{225-(v-lo)/span*190:.2f}" for i,v in enumerate(values))
    actual, lower, upper = coords(ridge.actual), coords(ridge.lower), coords(ridge.upper)
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RithmScope · {escape(report['symbol'])} research report</title>
<style>:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#0b171e;color:#e4eeee;font:16px/1.65 system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:48px 24px}}small,.muted{{color:#a6bcc1}}h1{{font-size:clamp(36px,6vw,64px);line-height:1.1;margin:12px 0}}h2{{font-size:23px;margin-top:36px}}.brand{{color:#b6e9df;letter-spacing:.12em;font-weight:700}}.panel{{background:#11232c;border:1px solid #29404a;border-radius:16px;padding:24px;margin:24px 0}}.pill{{color:#e5a278;font-weight:600}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;padding:13px 10px;border-bottom:1px solid #29404a;white-space:nowrap}}.scroll{{overflow:auto}}svg{{width:100%;height:auto}}code{{overflow-wrap:anywhere;font-size:12px}}a{{color:#b6e9df}}</style>
<main><div class="brand">rithmsAI / RITHMSCOPE</div><h1>Measure the forecast.<br>Question the edge.</h1>
<p class="muted">{escape(report['symbol'])} · {escape(report['asset_class'])} · {escape(report['first_date'])} → {escape(report['last_date'])}</p>
<div class="panel"><span class="pill">HISTORICAL RESEARCH</span><p>Predict the next observed session’s open-to-close return from the preceding completed daily bar. Three expanding evaluation folds; separate past calibration; one-row gaps at both boundaries. Fixed model settings, no winner selection.</p><p>No orders, live quotes or guaranteed profits. Forecast intervals are empirical estimates; time dependence can invalidate nominal coverage.</p></div>
<h2>All models, including the baselines</h2><p class="muted">MAE is in percentage points of return. Direction accuracy counts zero as non-positive. Costs per side: {report['config']['fee_bps']:g} bps fee + {report['config']['slippage_bps']:g} bps slippage. Full-notional independent intraday simulations.</p>
<div class="panel scroll"><table><thead><tr><th>Model</th><th>MAE</th><th>Direction</th><th>Coverage</th><th>Interval width</th><th>Trades</th><th>Net return</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>Ridge forecast interval and realized return</h2><p class="muted">Observed sessions left to right. Mint: realized next-session return; copper: lower and upper nominal 90% bounds. Bounds are fixed within each evaluation fold.</p>
<div class="panel"><svg viewBox="0 0 1000 260" role="img" aria-label="Historical realized return and Ridge prediction interval"><text x="28" y="20" fill="#a6bcc1">{hi:.1%}</text><text x="28" y="254" fill="#a6bcc1">{lo:.1%}</text><polyline points="{lower}" fill="none" stroke="#d99b76" stroke-width="2"/><polyline points="{upper}" fill="none" stroke="#d99b76" stroke-width="2"/><polyline points="{actual}" fill="none" stroke="#b6e9df" stroke-width="1.5"/></svg></div>
<h2>Reproduce and inspect</h2><p>Source: {escape(report['source'])}. {report['input_rows_used']} completed input bars. Input SHA-256: <code>{escape(report['input_sha256'])}</code>.</p>
<p>The adjacent report.json contains every fold’s dates, metrics, settings and library versions. predictions.csv contains every held-out forecast and realized target. No profitable result is suppressed. LONG_CANDIDATE requires a positive lower interval bound above estimated round-trip costs; otherwise the model abstains.</p>
<p class="muted">Independent research project by Kaya Robinson / rithmsAI. Dataset changes, provider revisions, costs, execution delay, missing sessions and regime shifts can change these results. This is not a brokerage or an investment recommendation.</p></main></html>'''
