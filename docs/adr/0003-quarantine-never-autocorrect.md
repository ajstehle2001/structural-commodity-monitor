# ADR 0003: Quarantine, never auto-correct

## Status
Accepted.

## Context
Series-level validation catches suspect extractions: week-over-week jumps beyond plausibility, duplicate dates, out-of-order records. A tempting design is to have the pipeline fix these automatically - interpolate the jump, drop the duplicate, re-sort the dates.

## Decision
`validate_series` returns flags and never mutates. Suspect records are quarantined for human review. Auto-correction is deliberately not offered.

## Consequences
An auto-correction is an extraction error with better manners: it replaces a visible anomaly with an invisible assumption. A 51% week-over-week drop might be an extraction error - or a genuine market event that is precisely the thing the monitor exists to catch. Only a human (or a documented human-approved rule) can make that call. The cost is operational: flagged weeks require attention. That cost is the feature.
