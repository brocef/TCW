# Refined outcome

## Verification decision

**Accepted**, under the standing decision to drive the epic to completion and
refine from use.

## Evidence

- 944 Python tests (from 873); 44 web tests; `tcw validate` OK.
- The parity test broken by hand in both directions — `Produce` and `Inputs` —
  and confirmed red each way before being trusted.
- `SKILL.md` at 58 lines against a 60-line budget.
- No reference to any of the four deleted documents survives outside the
  archives.

## Capability reconciliation

- **Changed:** `plugin/work-lifecycle` — the skill it names is restructured, and
  its description now points at the per-stage documents rather than the retired
  lifecycle files.
- No new capabilities. Reorganizing documentation adds nothing a user can do.

## The two prose criteria

Signed off by hand, and recorded as sign-off rather than test results:

- **No rule stated twice** — the destination table was the mechanism; each
  displaced section moved to exactly one place.
- **Followable by a Codex agent** — every stage document names
  `tcw work lifecycle --stage <id>`, which both harnesses run, and `--directive`
  appears only in `hooks.md` labelled as Claude-only sugar.

## Notes

**`pr` should be deleted before this epic closes.** Four children have now passed
without consuming it, and child 5 will not either. Leaving it is the exact
pattern — a persisted field nothing reads — that this epic removed twice.
