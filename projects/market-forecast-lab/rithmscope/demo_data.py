"""Invented prices for offline engineering checks, not evidence about markets."""
import numpy as np
import pandas as pd


def fixture(n=620):
    rng = np.random.default_rng(29)
    opening = 100*np.exp(np.cumsum(rng.normal(0, .01, n)))
    closing = opening*np.exp(rng.normal(0, .008, n))
    return pd.DataFrame({"date": pd.date_range("2022-01-01", periods=n),
                         "open": opening, "high": np.maximum(opening, closing)*1.01,
                         "low": np.minimum(opening, closing)*.99, "close": closing,
                         "volume": rng.integers(100, 10000, n)})
