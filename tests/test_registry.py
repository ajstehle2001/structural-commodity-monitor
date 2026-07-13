"""Tests for the pre-registration registry: the no-curation guarantees."""

from __future__ import annotations

import pytest

from monitor.registry import (
    MAX_ATTEMPTS,
    PreregistrationViolation,
    Registry,
    TestDeclaration,
)


def make_declaration(test_id: str = "levels-fit-01") -> TestDeclaration:
    return TestDeclaration(
        test_id=test_id,
        hypothesis="ln(P) is linear in 1/IR with positive slope",
        specification="OLS of ln(price) on 1/IR, weekly data, full sample",
        pass_criteria="slope > 0 and p_value < 0.01",
        declared_at="2026-07-01T00:00:00+00:00",
    )


def test_declaration_hash_is_deterministic():
    a = make_declaration()
    b = make_declaration()
    assert a.sha256 == b.sha256


def test_declaration_hash_changes_with_content():
    a = make_declaration()
    b = TestDeclaration(
        test_id=a.test_id,
        hypothesis=a.hypothesis,
        specification=a.specification,
        pass_criteria="slope > 0 and p_value < 0.05",  # weakened criteria
        declared_at=a.declared_at,
    )
    assert a.sha256 != b.sha256


def test_declare_writes_file_with_hash(tmp_path):
    reg = Registry(tmp_path)
    path = reg.declare(make_declaration())
    assert path.exists()
    stored = reg.get_declaration("levels-fit-01")
    assert stored["sha256"] == make_declaration().sha256


def test_redeclaring_same_id_raises(tmp_path):
    reg = Registry(tmp_path)
    reg.declare(make_declaration())
    with pytest.raises(PreregistrationViolation):
        reg.declare(make_declaration())


def test_outcome_requires_declaration(tmp_path):
    reg = Registry(tmp_path)
    with pytest.raises(KeyError):
        reg.record_outcome("never-declared", passed=True, metrics={})


def test_two_attempts_allowed_third_raises(tmp_path):
    reg = Registry(tmp_path)
    reg.declare(make_declaration())
    reg.record_outcome("levels-fit-01", passed=False, metrics={"p": 0.30})
    reg.record_outcome("levels-fit-01", passed=False, metrics={"p": 0.20})
    with pytest.raises(PreregistrationViolation):
        reg.record_outcome("levels-fit-01", passed=False, metrics={"p": 0.04})
    assert len(reg.outcomes("levels-fit-01")) == MAX_ATTEMPTS


def test_verdict_lifecycle(tmp_path):
    reg = Registry(tmp_path)
    reg.declare(make_declaration())
    assert reg.verdict("levels-fit-01") == "undetermined"
    reg.record_outcome("levels-fit-01", passed=False, metrics={})
    assert reg.verdict("levels-fit-01") == "undetermined"
    reg.record_outcome("levels-fit-01", passed=False, metrics={})
    assert reg.verdict("levels-fit-01") == "failed"


def test_verdict_pass_on_any_attempt(tmp_path):
    reg = Registry(tmp_path)
    reg.declare(make_declaration())
    reg.record_outcome("levels-fit-01", passed=False, metrics={})
    reg.record_outcome("levels-fit-01", passed=True, metrics={})
    assert reg.verdict("levels-fit-01") == "passed"
