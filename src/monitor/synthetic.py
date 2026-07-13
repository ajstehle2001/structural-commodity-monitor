"""Synthetic weekly market data with a known structural ground truth.

Generates an inventory-ratio path (bounded mean-reverting), weekly
grindings, implied stocks, and a price series derived FROM the
structural curve ln(P) = a + b/IR plus lognormal noise and occasional
narrative-spike episodes (price excursions unrelated to inventories,
mimicking crop-scare rallies).

Because the true coefficients are known, the test suite can assert the
fitting machinery recovers them — the honest way to validate a
calibration pipeline without redistributing licensed market data.

Run `python -m monitor.synthetic` to write data/demo/synthetic_weekly.csv.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SyntheticParams:
    """Ground-truth parameters for the generated market.

    Defaults chosen so IR spans roughly 2-8 and prices land in a
    cocoa-like range, purely for readability of the demo outputs.
    """

    a: float = 8.0                 # structural intercept (log-price)
    b: float = 1.8                 # scarcity coefficient on 1/IR
    noise_sigma: float = 0.08      # lognormal price noise (structural misses)
    n_weeks: int = 260             # ~5 years of weekly data
    seed: int = 42
    ir_low: float = 2.0            # reflecting bounds for the IR walk
    ir_high: float = 8.0
    ir_step_sigma: float = 0.15    # weekly IR innovation scale
    grindings_mean: float = 45.0   # thousand tonnes per week
    grindings_sigma: float = 1.5
    spike_probability: float = 0.01   # chance per week a narrative episode starts
    spike_magnitude: float = 0.35     # log-price boost at episode peak
    spike_half_life_weeks: float = 6.0


def generate_weekly_series(params: SyntheticParams | None = None) -> pd.DataFrame:
    """Generate the weekly series. Columns:

    week (int), stocks_kt, grindings_weekly_kt, ir, price,
    spike_component (the injected narrative excursion in log space,
    kept in the output so tests can distinguish structure from story).
    """
    p = params or SyntheticParams()
    rng = np.random.default_rng(p.seed)

    # Bounded mean-reverting IR path (reflected random walk toward midpoint)
    ir = np.empty(p.n_weeks)
    ir[0] = (p.ir_low + p.ir_high) / 2
    mid = ir[0]
    for t in range(1, p.n_weeks):
        pull = 0.03 * (mid - ir[t - 1])
        step = rng.normal(0.0, p.ir_step_sigma)
        nxt = ir[t - 1] + pull + step
        # Reflect at the bounds
        if nxt < p.ir_low:
            nxt = p.ir_low + (p.ir_low - nxt)
        if nxt > p.ir_high:
            nxt = p.ir_high - (nxt - p.ir_high)
        ir[t] = float(np.clip(nxt, p.ir_low, p.ir_high))

    grindings = rng.normal(p.grindings_mean, p.grindings_sigma, p.n_weeks)
    stocks = ir * grindings  # consistent with IR = stocks / weekly grindings scale

    # Narrative spike episodes: exponential-decay excursions in log space
    spike = np.zeros(p.n_weeks)
    decay = np.log(2) / p.spike_half_life_weeks
    for t in range(p.n_weeks):
        if rng.random() < p.spike_probability:
            length = int(p.spike_half_life_weeks * 4)
            for k in range(length):
                if t + k < p.n_weeks:
                    spike[t + k] += p.spike_magnitude * np.exp(-decay * k)

    log_price = p.a + p.b / ir + rng.normal(0.0, p.noise_sigma, p.n_weeks) + spike
    price = np.exp(log_price)

    return pd.DataFrame(
        {
            "week": np.arange(p.n_weeks),
            "stocks_kt": stocks,
            "grindings_weekly_kt": grindings,
            "ir": ir,
            "price": price,
            "spike_component": spike,
        }
    )


def write_demo_csv(path: Path = Path("data/demo/synthetic_weekly.csv")) -> Path:
    """Write the default synthetic series to disk for examples and docs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    generate_weekly_series().to_csv(path, index=False)
    return path


if __name__ == "__main__":
    out = write_demo_csv()
    print(f"Wrote {out}")
