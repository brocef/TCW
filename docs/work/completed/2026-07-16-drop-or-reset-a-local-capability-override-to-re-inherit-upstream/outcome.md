# Outcome: drop/reset a local capability override

Work completed successfully. Small store + CLI addition; TDD; dual-reviewed
(no bugs). Full suite green (635 passed → +7 reset tests).

## What changed

- `tcw/store/base.py` — `CapabilitiesStore.reset(identifier)` (abstract).
- `tcw/store/fs.py` — `FsCapabilitiesStore.reset`: refuse a standalone-local path
  (use `remove`); resolve the override via `_override_index()` by upstream id
  (`cap.id` / `f"{cap.origin}/{cap.id}"`, the exact keys `_write_target` writes) so
  it finds bare or alias-qualified placements; refuse an un-overridden inherited
  path; `_rm` **only** the local override folder — never the upstream node.
- `tcw/capabilities/cli.py` — `tcw capabilities reset <path>` subcommand.
- New capability `capabilities/reset-an-override` (flipped `Missing → Supported`).
- Docs: README, release notes, changelog, `tcw-capabilities` skill.

## Verification performed

- `pytest` — 635 passed; new `tests/test_capabilities_reset.py` (7): re-inherit +
  upstream-tree-hash-unchanged, alias-qualified placement variant, and the four
  refusals (standalone-local, un-overridden, unknown, ambiguous-ref).
- CLI end-to-end (two-node federated throwaway): `set` override → `reset`
  re-inherits (Status back to upstream, override folder gone) → `reset` again
  refuses with a clear message + exit 1 → upstream node untouched.
- `tcw validate` + `tcw capabilities check` clean.

## Review (dual)

1. **Subagent (targeted-code-reviewer)** — traced all five high-risk areas:
   **never-touch-upstream guarantee HOLDS** (`_override_index` scans only the local
   store root; `ov[0]` is provably a local folder); override-resolution keys are
   byte-identical to `_write_target`/`_apply_override` (no override `set` writes that
   `reset` can't find); all four refusals covered; placement variant handled; CLI
   wiring correct. **No bugs.** Findings: (a) untracked hand-created override folder
   → `CalledProcessError` — pre-existing pattern identical to `remove`, `set` always
   stages, note only (kept for parity); (b) docstring omitted `AmbiguousRef`;
   (c) ambiguous-ref path untested.
2. **`bllm-review-many` (qwen25)** — no concrete defect; generic "add tests / confirm"
   advisories, all already satisfied or covered by the subagent's trace.

**Applied** (commit after impl): documented `AmbiguousRef` on the abstract `reset`;
added the two-alias ambiguous-ref test. **Dismissed** finding (a) for parity with
the existing `remove` (hand-created untracked deltas only; out of the normal flow).

## Deviations from plan

None. Web surface intentionally out of scope (no override-lifecycle web control
exists).

## Follow-up notes

None.
