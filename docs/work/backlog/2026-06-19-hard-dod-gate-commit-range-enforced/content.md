# Hard DoD gate (commit-range enforced)

## Product changes

## Technical changes

## Meta changes

Refuse `tcw work complete` unless the item's declared capability files actually appear in its commit range. Today the Definition-of-Done gate is a checklist acknowledgement only; this makes "capabilities reconciled" mechanically enforced.

Spec: docs/plan/phase-6-beyond.md; phase-5-work A.7, B.9.
