"""The decay rule: signals must keep earning their place on unseen data.

Modeled on the retirement discipline of systematic funds. Every signal
is a state machine:

    HYPOTHESIS --(2 consecutive passing OOS quarters)--> ACTIVE
    ACTIVE     --(2 consecutive failing OOS quarters)--> RETIRED
    RETIRED    --(no path back)

Retirement is permanent by design: a retired signal may only return as
a NEW declaration in the pre-registration registry, restarting the
graduation clock. This prevents the quiet resurrection of dead ideas -
a signal that "starts working again" after retirement is, evidentially,
a different claim and must be treated as one.

In-sample performance plays no role in any transition. History can
disqualify ideas; it cannot promote them. Only out-of-sample quarters
move the state machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

GRADUATION_QUARTERS = 2   # consecutive OOS passes: HYPOTHESIS -> ACTIVE
RETIREMENT_QUARTERS = 2   # consecutive OOS failures: ACTIVE -> RETIRED


class SignalStatus(Enum):
    HYPOTHESIS = "hypothesis"
    ACTIVE = "active"
    RETIRED = "retired"


class DecayRuleViolation(Exception):
    """Raised on transitions the decay rule forbids."""


@dataclass(frozen=True)
class QuarterlyEvaluation:
    """One out-of-sample quarterly re-scoring of a signal."""

    period: str      # e.g. "2026Q3"
    passed: bool
    metrics: dict = field(default_factory=dict)


@dataclass
class SignalRecord:
    """A signal's lifecycle under the decay rule."""

    signal_id: str
    status: SignalStatus = SignalStatus.HYPOTHESIS
    evaluations: list[QuarterlyEvaluation] = field(default_factory=list)

    def record_quarter(self, evaluation: QuarterlyEvaluation) -> SignalStatus:
        """Append an out-of-sample quarter and apply the state machine.

        Raises:
            DecayRuleViolation: if the signal is already retired (nothing
                may be recorded against a retired signal), or if the
                period is not strictly newer than the last recorded one.
        """
        if self.status == SignalStatus.RETIRED:
            raise DecayRuleViolation(
                f"Signal '{self.signal_id}' is retired. Retirement is permanent; "
                "re-propose it as a new declaration."
            )
        if self.evaluations and evaluation.period <= self.evaluations[-1].period:
            raise DecayRuleViolation(
                f"Period {evaluation.period} is not after "
                f"{self.evaluations[-1].period}; quarters must be recorded in order."
            )

        self.evaluations.append(evaluation)

        if self.status == SignalStatus.HYPOTHESIS:
            if self._consecutive_tail(passed=True) >= GRADUATION_QUARTERS:
                self.status = SignalStatus.ACTIVE
        elif self.status == SignalStatus.ACTIVE:
            if self._consecutive_tail(passed=False) >= RETIREMENT_QUARTERS:
                self.status = SignalStatus.RETIRED

        return self.status

    def _consecutive_tail(self, *, passed: bool) -> int:
        """Length of the run of quarters at the end matching `passed`."""
        count = 0
        for ev in reversed(self.evaluations):
            if ev.passed == passed:
                count += 1
            else:
                break
        return count
