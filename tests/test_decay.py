"""Tests for the decay rule state machine."""

from __future__ import annotations

import pytest

from monitor.decay import (
    DecayRuleViolation,
    QuarterlyEvaluation,
    SignalRecord,
    SignalStatus,
)


def q(period: str, passed: bool) -> QuarterlyEvaluation:
    return QuarterlyEvaluation(period=period, passed=passed)


def test_starts_as_hypothesis():
    s = SignalRecord(signal_id="fade-pattern")
    assert s.status == SignalStatus.HYPOTHESIS


def test_graduates_after_two_consecutive_passes():
    s = SignalRecord(signal_id="fade-pattern")
    s.record_quarter(q("2026Q3", True))
    assert s.status == SignalStatus.HYPOTHESIS
    s.record_quarter(q("2026Q4", True))
    assert s.status == SignalStatus.ACTIVE


def test_failure_resets_graduation_run():
    s = SignalRecord(signal_id="fade-pattern")
    s.record_quarter(q("2026Q3", True))
    s.record_quarter(q("2026Q4", False))
    s.record_quarter(q("2027Q1", True))
    assert s.status == SignalStatus.HYPOTHESIS  # run of 1, not 2
    s.record_quarter(q("2027Q2", True))
    assert s.status == SignalStatus.ACTIVE


def test_retires_after_two_consecutive_failures():
    s = SignalRecord(signal_id="fade-pattern", status=SignalStatus.ACTIVE)
    s.record_quarter(q("2026Q3", False))
    assert s.status == SignalStatus.ACTIVE
    s.record_quarter(q("2026Q4", False))
    assert s.status == SignalStatus.RETIRED


def test_pass_resets_retirement_run():
    s = SignalRecord(signal_id="fade-pattern", status=SignalStatus.ACTIVE)
    s.record_quarter(q("2026Q3", False))
    s.record_quarter(q("2026Q4", True))
    s.record_quarter(q("2027Q1", False))
    assert s.status == SignalStatus.ACTIVE  # run of 1, not 2


def test_retirement_is_permanent():
    s = SignalRecord(signal_id="fade-pattern", status=SignalStatus.ACTIVE)
    s.record_quarter(q("2026Q3", False))
    s.record_quarter(q("2026Q4", False))
    assert s.status == SignalStatus.RETIRED
    with pytest.raises(DecayRuleViolation):
        s.record_quarter(q("2027Q1", True))


def test_quarters_must_be_in_order():
    s = SignalRecord(signal_id="fade-pattern")
    s.record_quarter(q("2026Q4", True))
    with pytest.raises(DecayRuleViolation):
        s.record_quarter(q("2026Q3", True))
    with pytest.raises(DecayRuleViolation):
        s.record_quarter(q("2026Q4", True))  # duplicate period


def test_hypothesis_is_not_retired_by_failures():
    """An unproven idea failing OOS stays a hypothesis (it was never active).

    Retirement is a demotion from active use; a hypothesis that keeps
    failing simply never graduates.
    """
    s = SignalRecord(signal_id="fade-pattern")
    for i, period in enumerate(["2026Q3", "2026Q4", "2027Q1"]):
        s.record_quarter(q(period, False))
    assert s.status == SignalStatus.HYPOTHESIS
