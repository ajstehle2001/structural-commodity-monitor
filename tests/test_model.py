"""Tests for the structural model core.

The key property under test: because the synthetic generator produces
prices FROM a known curve, the fitting machinery must recover the true
coefficients. That closes the loop on the calibration pipeline without
any licensed data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from monitor.model import (
    MIN_OBSERVATIONS,
    fit_structural_curve,
    fit_with_spike_exclusion,
    inventory_ratio,
    residuals_in_sigma,
)
from monitor.synthetic import SyntheticParams, generate_weekly_series


# Quiet synthetic market (no narrative spikes) for clean recovery tests.
CLEAN = SyntheticParams(spike_probability=0.0, n_weeks=520, seed=11)


def test_fit_recovers_true_coefficients():
    df = generate_weekly_series(CLEAN)
    fit = fit_structural_curve(df["ir"], df["price"])
    assert fit.a == pytest.approx(CLEAN.a, rel=0.05)
    assert fit.b == pytest.approx(CLEAN.b, rel=0.15)


def test_fit_has_correct_sign_and_significance():
    df = generate_weekly_series(CLEAN)
    fit = fit_structural_curve(df["ir"], df["price"])
    assert fit.b > 0            # scarcity premium: price rises as IR shrinks
    assert fit.p_value < 0.01


def test_fair_value_decreases_as_ir_grows():
    df = generate_weekly_series(CLEAN)
    fit = fit_structural_curve(df["ir"], df["price"])
    fv = fit.fair_value(np.array([2.0, 4.0, 8.0]))
    assert fv[0] > fv[1] > fv[2]


def test_residuals_standardized():
    df = generate_weekly_series(CLEAN)
    fit = fit_structural_curve(df["ir"], df["price"])
    sig = residuals_in_sigma(fit, df["ir"], df["price"])
    assert abs(sig.mean()) < 0.1
    assert sig.std() == pytest.approx(1.0, rel=0.05)


def test_spike_exclusion_stable_on_clean_market():
    df = generate_weekly_series(CLEAN)
    stability = fit_with_spike_exclusion(df["ir"], df["price"])
    assert stability.is_stable()
    assert stability.b_relative_change < 0.15


def test_spiky_market_still_recovers_structure_after_exclusion():
    spiky = SyntheticParams(
        spike_probability=0.03, spike_magnitude=0.6, n_weeks=520, seed=13
    )
    df = generate_weekly_series(spiky)
    stability = fit_with_spike_exclusion(df["ir"], df["price"], exclude_top_fraction=0.10)
    # The excluded fit should sit closer to ground truth than the full fit.
    err_full = abs(stability.full.b - spiky.b)
    err_excl = abs(stability.excluded.b - spiky.b)
    assert err_excl <= err_full


def test_fit_raises_on_too_few_points():
    ir = pd.Series(np.linspace(2, 8, MIN_OBSERVATIONS - 1))
    price = pd.Series(np.exp(8.0 + 1.8 / ir))
    with pytest.raises(ValueError):
        fit_structural_curve(ir, price)


def test_inventory_ratio_needs_full_window():
    stocks = pd.Series(np.full(60, 270.0))
    grindings = pd.Series(np.full(60, 45.0))
    ir = inventory_ratio(stocks, grindings, window=52)
    assert ir.iloc[:51].isna().all()          # incomplete window -> NaN
    assert ir.iloc[51:].notna().all()
    assert ir.iloc[-1] == pytest.approx(6.0)  # 270 / 45
