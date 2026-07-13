"""Pre-registration as code: frozen test declarations and attempt limits.

The discipline from the methodology, made mechanical:

1. A test's hypothesis, exact specification, and pass/fail criteria are
   DECLARED before the test is run. The declaration is serialized to
   canonical JSON and hashed (SHA-256); the hash is the tamper-evidence.
2. Outcomes can only be recorded against an existing declaration.
3. At most MAX_ATTEMPTS (2) outcomes may be recorded per test. A third
   attempt raises PreregistrationViolation - in this framework a failed
   test stays failed, and reworking a test until it passes is the exact
   behavior the registry exists to prevent.

The registry is a directory of JSON files (declarations/ and outcomes/),
designed to live inside a git repository so the commit history itself
becomes part of the evidence trail.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

MAX_ATTEMPTS = 2


class PreregistrationViolation(Exception):
    """Raised when an action would violate the pre-registration discipline."""


@dataclass(frozen=True)
class TestDeclaration:
    """A frozen statement of what will be tested and how it will be judged."""

    __test__ = False  # prevent pytest from collecting this as a test class

    test_id: str
    hypothesis: str          # plain-language claim under test
    specification: str       # exact procedure: data, transformation, statistic
    pass_criteria: str       # numeric thresholds, written before running
    declared_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def canonical_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TestOutcome:
    """A recorded result of running a declared test."""

    __test__ = False  # prevent pytest from collecting this as a test class

    test_id: str
    attempt: int             # 1-based
    passed: bool
    metrics: dict            # the numbers behind the verdict
    notes: str = ""
    recorded_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Registry:
    """File-backed pre-registration registry.

    Layout:
        <root>/declarations/<test_id>.json
        <root>/outcomes/<test_id>_attempt<N>.json
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.declarations_dir = self.root / "declarations"
        self.outcomes_dir = self.root / "outcomes"
        self.declarations_dir.mkdir(parents=True, exist_ok=True)
        self.outcomes_dir.mkdir(parents=True, exist_ok=True)

    # --- declarations -------------------------------------------------------

    def declare(self, declaration: TestDeclaration) -> Path:
        """Freeze a declaration. Re-declaring an existing test_id raises.

        Immutability is the point: if the specification needs to change,
        that is a NEW test with a new id, and the old declaration (and any
        failures recorded against it) remains on the books.
        """
        path = self.declarations_dir / f"{declaration.test_id}.json"
        if path.exists():
            raise PreregistrationViolation(
                f"Test '{declaration.test_id}' is already declared. "
                "Declarations are immutable; a changed specification is a new test."
            )
        payload = asdict(declaration)
        payload["sha256"] = declaration.sha256
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def get_declaration(self, test_id: str) -> dict:
        path = self.declarations_dir / f"{test_id}.json"
        if not path.exists():
            raise KeyError(f"No declaration for test '{test_id}'")
        return json.loads(path.read_text(encoding="utf-8"))

    # --- outcomes -----------------------------------------------------------

    def outcomes(self, test_id: str) -> list[dict]:
        found = sorted(self.outcomes_dir.glob(f"{test_id}_attempt*.json"))
        return [json.loads(p.read_text(encoding="utf-8")) for p in found]

    def record_outcome(
        self,
        test_id: str,
        passed: bool,
        metrics: dict,
        notes: str = "",
    ) -> TestOutcome:
        """Record a result against a declared test.

        Raises:
            PreregistrationViolation: if the test was never declared, or
                if MAX_ATTEMPTS outcomes already exist for it.
        """
        self.get_declaration(test_id)  # raises KeyError if undeclared
        prior = self.outcomes(test_id)
        if len(prior) >= MAX_ATTEMPTS:
            raise PreregistrationViolation(
                f"Test '{test_id}' already has {len(prior)} recorded attempts "
                f"(limit {MAX_ATTEMPTS}). A failed test stays failed."
            )
        outcome = TestOutcome(
            test_id=test_id,
            attempt=len(prior) + 1,
            passed=passed,
            metrics=metrics,
            notes=notes,
        )
        path = self.outcomes_dir / f"{test_id}_attempt{outcome.attempt}.json"
        path.write_text(json.dumps(asdict(outcome), indent=2), encoding="utf-8")
        return outcome

    def verdict(self, test_id: str) -> str:
        """'passed' | 'failed' | 'undetermined' based on recorded outcomes.

        A single pass on any attempt is a pass; attempts exhausted without
        a pass is a fail; no outcomes yet is undetermined.
        """
        results = self.outcomes(test_id)
        if any(r["passed"] for r in results):
            return "passed"
        if len(results) >= MAX_ATTEMPTS:
            return "failed"
        return "undetermined"

