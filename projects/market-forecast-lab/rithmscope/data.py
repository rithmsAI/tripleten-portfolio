"""Strict canonical bars and read-only, bounded market-data imports."""
import hashlib
import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

COLUMNS = ["date", "open", "high", "low", "close", "volume"]
MAX_BYTES = 20_000_000


def validate(frame):
    if set(frame.columns) != set(COLUMNS):
        raise ValueError("Expected exactly: date,open,high,low,close,volume")
    if not 60 <= len(frame) <= 100_000:
        raise ValueError("Require 60–100,000 completed daily bars")
    out = frame[COLUMNS].copy()
    dates = out["date"].astype(str)
    if not dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        raise ValueError("Dates must be ISO YYYY-MM-DD")
    out["date"] = pd.to_datetime(dates, format="%Y-%m-%d", errors="raise")
    if out.date.duplicated().any() or not out.date.is_monotonic_increasing:
        raise ValueError("Dates must be unique and strictly increasing; do not silently sort")
    for name in COLUMNS[1:]:
        out[name] = pd.to_numeric(out[name], errors="raise")
    if not np.isfinite(out[COLUMNS[1:]].to_numpy()).all():
        raise ValueError("Nonfinite market data")
    if (out[["open", "high", "low", "close"]] <= 0).any().any() or (out.volume < 0).any():
        raise ValueError("Prices must be positive; volume nonnegative")
    if ((out.low > out[["open", "close", "high"]].min(axis=1)) |
            (out.high < out[["open", "close", "low"]].max(axis=1))).any():
        raise ValueError("Invalid OHLC bounds")
    return out.reset_index(drop=True)


def load(path, through):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("CSV exceeds 20 MB")
    raw = pd.read_csv(path)
    frame = validate(raw)
    cutoff = pd.Timestamp(date.fromisoformat(through))
    if cutoff.date() >= datetime.now(timezone.utc).date():
        raise ValueError("--through must precede today's UTC date; completed bars only")
    frame = frame.loc[frame.date <= cutoff].reset_index(drop=True)
    if len(frame) < 60:
        raise ValueError("Insufficient bars before completion cutoff")
    return frame, hashlib.sha256(path.read_bytes()).hexdigest()


def get_json(url):
    """No account endpoints, credentials, arbitrary hosts or unbounded responses."""
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "rithmsAI-RithmScope/0.1"})
            with urlopen(request, timeout=30) as response:
                body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("Provider response too large")
            return json.loads(body)
        except (OSError, ValueError):
            if attempt < 2:
                time.sleep(attempt + 1)
    # Never print request URLs: a stock-provider URL contains a key.
    raise ValueError("Market-data request failed; check provider availability and credentials") from None


def coinbase(symbol, start, end, request=get_json):
    if not re.fullmatch(r"[A-Z0-9]{2,12}-USD", symbol):
        raise ValueError("Use a Coinbase USD product such as BTC-USD")
    first, stop = date.fromisoformat(start), date.fromisoformat(end)
    if not first < stop <= datetime.now(timezone.utc).date() or (stop-first).days > 7305:
        raise ValueError("Use an exclusive end no later than today UTC; max 20 years")
    rows = {}
    cursor = first
    while cursor < stop:
        nxt = min(cursor + timedelta(days=250), stop)
        query = urlencode({"granularity": 86400, "start": f"{cursor}T00:00:00Z", "end": f"{nxt}T00:00:00Z"})
        payload = request(f"https://api.exchange.coinbase.com/products/{symbol}/candles?{query}")
        if not isinstance(payload, list):
            raise ValueError("Coinbase did not return candles")
        for item in payload:
            if not isinstance(item, list) or len(item) != 6:
                raise ValueError("Malformed Coinbase candle")
            stamp, low, high, opening, close, volume = item
            day = datetime.fromtimestamp(stamp, timezone.utc)
            if day.time().isoformat() != "00:00:00":
                raise ValueError("Non-daily Coinbase timestamp")
            if cursor <= day.date() < nxt:
                row = [day.date().isoformat(), opening, high, low, close, volume]
                if row[0] in rows and rows[row[0]] != row:
                    raise ValueError("Conflicting Coinbase duplicate")
                rows[row[0]] = row
        cursor = nxt
        time.sleep(0.15)
    expected = {(first + timedelta(days=i)).isoformat() for i in range((stop-first).days)}
    if set(rows) != expected:
        raise ValueError("Missing crypto daily bars; no silent forward filling")
    return validate(pd.DataFrame([rows[k] for k in sorted(rows)], columns=COLUMNS))


def alphavantage(symbol, request=get_json):
    if not re.fullmatch(r"[A-Z0-9.\-]{1,16}", symbol):
        raise ValueError("Invalid stock/ETF symbol")
    key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not key:
        raise ValueError("Set ALPHAVANTAGE_API_KEY locally; never commit credentials")
    query = urlencode({"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": symbol,
                       "outputsize": "full", "apikey": key})
    payload = request(f"https://www.alphavantage.co/query?{query}")
    bars = payload.get("Time Series (Daily)", {}) if isinstance(payload, dict) else {}
    if not bars:
        raise ValueError("No adjusted daily data; check provider entitlement, key or rate limit")
    rows = []
    for day, bar in sorted(bars.items()):
        close = float(bar["4. close"])
        if not np.isfinite(close) or close <= 0:
            raise ValueError("Invalid provider closing price")
        factor = float(bar["5. adjusted close"]) / close
        # One factor for all four prices avoids mixing raw open with adjusted close.
        rows.append([day, float(bar["1. open"]) * factor, float(bar["2. high"]) * factor,
                     float(bar["3. low"]) * factor, close * factor, float(bar["6. volume"])])
    return validate(pd.DataFrame(rows, columns=COLUMNS))


def yahoo_snapshot(symbol, start, end, request=get_json):
    """Experimental public chart snapshot; not a supported or guaranteed Yahoo API."""
    if not re.fullmatch(r"[A-Z0-9.\-]{1,16}", symbol):
        raise ValueError("Invalid stock/ETF symbol")
    first, stop = date.fromisoformat(start), date.fromisoformat(end)
    if not first < stop <= datetime.now(timezone.utc).date() or (stop-first).days > 7305:
        raise ValueError("Use an exclusive end no later than today UTC; max 20 years")
    stamp = lambda d: int(datetime.combine(d, datetime.min.time(), timezone.utc).timestamp())
    query = urlencode({"period1": stamp(first), "period2": stamp(stop), "interval": "1d", "events": "div,splits"})
    payload = request(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}")
    results = payload.get("chart", {}).get("result") if isinstance(payload, dict) else None
    if not results or len(results) != 1:
        raise ValueError("Yahoo snapshot unavailable; use a licensed CSV or Alpha Vantage instead")
    result = results[0]
    if result.get("meta", {}).get("symbol") != symbol:
        raise ValueError("Provider symbol mismatch")
    zone = ZoneInfo(result["meta"]["exchangeTimezoneName"])
    quotes = result["indicators"]["quote"][0]
    adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    timestamps = result["timestamp"]
    if any(len(quotes.get(c, [])) != len(timestamps) for c in COLUMNS[1:]) or len(adjusted) != len(timestamps):
        raise ValueError("Mismatched Yahoo snapshot arrays")
    rows = []
    for i, timestamp in enumerate(timestamps):
        day = datetime.fromtimestamp(timestamp, zone).date()
        if first <= day < stop:
            values = [quotes[c][i] for c in COLUMNS[1:]] + [adjusted[i]]
            if any(v is None for v in values):
                raise ValueError("Missing Yahoo candle value; no silent dropping")
            close = float(quotes["close"][i])
            if not np.isfinite(close) or close <= 0:
                raise ValueError("Invalid provider closing price")
            factor = float(adjusted[i]) / close
            rows.append([day.isoformat(), *[float(quotes[c][i])*factor for c in COLUMNS[1:5]], quotes["volume"][i]])
    return validate(pd.DataFrame(rows, columns=COLUMNS))


def save_download(frame, output, metadata):
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, date_format="%Y-%m-%d", float_format="%.12g")
    metadata.update({"retrieved_utc": datetime.now(timezone.utc).isoformat(),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": len(frame),
                     "first_date": str(frame.date.iloc[0].date()), "last_date": str(frame.date.iloc[-1].date())})
    path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
