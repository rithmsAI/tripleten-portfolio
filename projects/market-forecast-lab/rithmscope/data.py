"""Provider-neutral validation of user-supplied, rights-cleared daily CSV bars."""
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
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


def save_download(frame, output, metadata):
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, date_format="%Y-%m-%d", float_format="%.12g")
    metadata.update({"retrieved_utc": datetime.now(timezone.utc).isoformat(),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": len(frame),
                     "first_date": str(frame.date.iloc[0].date()), "last_date": str(frame.date.iloc[-1].date())})
    path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
