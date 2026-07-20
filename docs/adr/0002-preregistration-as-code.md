# ADR 0002: Pre-registration as code, not intention

## Status
Accepted.

## Context
The methodology requires that statistical tests be declared - hypothesis, specification, pass criteria - before they are run, with at most two attempts. As a practice held in someone's head, this discipline is unenforceable and unverifiable: nothing stops a quiet third attempt or a retroactively softened threshold.

## Decision
The registry (`monitor.registry`) makes the discipline mechanical. Declarations are immutable JSON artifacts hashed with SHA-256 at declaration time; outcomes can only be recorded against existing declarations; a third recorded attempt raises `PreregistrationViolation`. The registry directory is designed to live inside a git repository, so the commit history independently timestamps declarations relative to outcomes.

## Consequences
Curation of results becomes structurally difficult rather than merely discouraged. Changing a specification requires a new test id, leaving the failed original on the books. The residual trust assumption is filesystem-level: someone with write access could delete files - which is why the git history matters as the second, tamper-evident layer. The framework does not prevent bad faith; it makes bad faith leave fingerprints.
