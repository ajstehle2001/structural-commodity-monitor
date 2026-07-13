"""Structural model core: inventory ratio, curve fit, sigma residuals.

The model is a single OLS regression in transformed space:

    ln(P) = a + b * (1 / IR)

fitted with scipy.stats.linregress. The evidence standard follows the
methodology doc: sign and significance before goodness-of-fit, and a
spike-exclusion refit to verify the coefficient is a property of the
market rather than a souvenir of one extreme episode.

This module claims EXPLANATION of price levels only. It contains no
forecasting machinery — pre-registered predictive tests of this
framework failed, and that boundary is documented in
docs/METHODOLOGY.md rather than papered over.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

MIN_OBSERVATIONS = 30


@dataclass(frozen=True)
class FitResult:
    """Fitted structural curve with its evidence statistics."""

    a: float             # intercept (base log-price level)
    b: float             # scarcity coefficient on 1/IR
    p_value: float       # significance of b
    r_squared: float
    n_obs: int
    residual_sigma: float  # std dev of log-space residuals (the sigma unit)

    def fair_value(self, ir: float | np.ndarray) -> np.ndarray:
        """Structural fair price for a given inventory ratio."""
        return np.exp(self.a + self.b / np.asarray(ir, dtype=float))


@dataclass(frozen=True)
class StabilityResult:
    """Full-sample fit vs. spike-excluded fit, for robustness assessment."""

    full: FitResult
    excluded: FitResult
    b_relative_change: float  # |b_excl - b_full| / |b_full|

    def is_stable(self, tolerance: float = 0.25) -> bool:
        """True if the scarcity coefficient survives spike exclusion.

        A coefficient that moves materially when one extreme episode is
        removed is a souvenir of that episode, not market structure.
        """
        return self.b_relative_change <= tolerance


def inventory_ratio(
    stocks: pd.Series,
    grindings_weekly: pd.Series,
    window: int = 52,
) -> pd.Series:
    """IR = stocks / trailing mean of weekly grindings.

    The trailing window converts noisy weekly consumption into the
    smooth denominator the theory calls for: how many units of steady
    demand are already sitting in the warehouse?
    """
    trailing = grindings_weekly.rolling(window, min_periods=window).mean()
    return stocks / trailing


def fit_structural_curve(ir: pd.Series, price: pd.Series) -> FitResult:
    """OLS fit of ln(price) on 1/IR.

    Raises ValueError if fewer than MIN_OBSERVATIONS clean rows remain
    after dropping NaNs — a curve fitted on a handful of points is not
    evidence of anything.
    """
    df = pd.DataFrame({"ir": ir, "price": price}).dropna()
    if len(df) < MIN_OBSERVATIONS:
        raise ValueError(
            f"Need at least {MIN_OBSERVATIONS} observations to fit; got {len(df)}"
        )
    x = 1.0 / df["ir"].to_numpy(dtype=float)
    y = np.log(df["price"].to_numpy(dtype=float))
    res = stats.linregress(x, y)
    fitted = res.intercept + res.slope * x
    resid = y - fitted
    return FitResult(
        a=float(res.intercept),
        b=float(res.slope),
        p_value=float(res.pvalue),
        r_squared=float(res.rvalue**2),
        n_obs=len(df),
        residual_sigma=float(np.std(resid, ddof=2)),
    )


def residuals_in_sigma(fit: FitResult, ir: pd.Series, price: pd.Series) -> pd.Series:
    """Gap between market price and structural fair value, in sigma units.

    +1.0 means the market trades one typical model-error above what
    inventories justify; +2.0 is (in the motivating calibration) the
    historical extreme.
    """
    log_gap = np.log(price.astype(float)) - (fit.a + fit.b / ir.astype(float))
    return log_gap / fit.residual_sigma


def fit_with_spike_exclusion(
    ir: pd.Series,
    price: pd.Series,
    exclude_top_fraction: float = 0.05,
) -> StabilityResult:
    """Fit on the full sample, then refit excluding the highest-price weeks.

    The robustness discipline from the methodology: if the scarcity
    coefficient barely moves when the most extreme price episode is
    removed, the relationship is a property of the market. If it moves
    materially, it was a souvenir of one wild year.
    """
    full = fit_structural_curve(ir, price)
    df = pd.DataFrame({"ir": ir, "price": price}).dropna()
    cutoff = df["price"].quantile(1.0 - exclude_top_fraction)
    kept = df[df["price"] <= cutoff]
    excluded = fit_structural_curve(kept["ir"], kept["price"])
    change = abs(excluded.b - full.b) / abs(full.b)
    return StabilityResult(full=full, excluded=excluded, b_relative_change=change)
