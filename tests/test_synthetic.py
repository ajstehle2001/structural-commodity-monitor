"""Tests for the synthetic data generator."""

from __future__ import annotations

import numpy as np

from monitor.synthetic import SyntheticParams, generate_weekly_series


def test_shapes_and_columns():
    df = generate_weekly_series()
    assert len(df) == 260
    assert set(df.columns) == {
        "week", "stocks_kt", "grindings_weekly_kt", "ir", "price", "spike_component"
    }
    assert not df.isna().any().any()


def test_ir_respects_bounds():
    p = SyntheticParams()
    df = generate_weekly_series(p)
    assert df["ir"].min() >= p.ir_low
    assert df["ir"].max() <= p.ir_high


def test_prices_positive():
    df = generate_weekly_series()
    assert (df["price"] > 0).all()


def test_reproducible_with_seed():
    a = generate_weekly_series(SyntheticParams(seed=7))
    b = generate_weekly_series(SyntheticParams(seed=7))
    assert np.allclose(a["price"], b["price"])


def test_different_seeds_differ():
    a = generate_weekly_series(SyntheticParams(seed=1))
    b = generate_weekly_series(SyntheticParams(seed=2))
    assert not np.allclose(a["price"], b["price"])
