# Refined outcome — Compose a procedure's instructions from project bindings the way a stage's are composed

## Decision

**Accepted** by the requester on 2026-09-16, as delivered, including every
decision `outcome.md` lists and the coordinating session presented at verify:

1. Ten procedure ids: `unattended-work`, `triage-issues`, `documentation-sync`,
   `post-mortem`, `create-work`, `audit-backlog`, `consolidate-plans`,
   `decompose`, `delegation`, `search`. `unattended-work` replaces the suggested
   `autonomous-work`, a removed skill name the removed-names test
   (`DELETED_NAMES`, `tests/test_skill_lifecycle_parity.py`) refuses.
2. Defaults are verbatim copies of today's text, guarded by a parity test; each
   conversion child changes its default and its parity row together.
3. Each id holds a plain list of bindings; an empty list is refused.
4. The command's output has no header or footer.
5. No harness adaptation in the command.
6. With no slug and only conditional bindings, it prints nothing, notes why on
   stderr, and exits 0.
7. A procedure's `generate:` script uses `work.lifecycle.timeout` and
   `output-cap`, and sees `TCW_HOOK_ROLE=procedure`.
8. `tcw work lifecycle` does not list procedures.

## Evidence

Checked by the coordinating session on 2026-09-16:

- In the worktree, the new tests
  (`tests/test_shipped_procedures.py`, `test_procedure_config.py`,
  `test_procedure_verb.py`, `test_resolve_procedure.py`) → `51 passed`.
- `tcw work procedure prompt delegation` with nothing configured is identical to
  `skills/tcw-work/references/procedures/delegation.md` (`diff` empty).
- `tcw work procedure prompt nope` → exit 1, naming the ten valid ids.
- `tcw validate` → `validate OK`; `tcw capabilities check` → `capabilities OK`.
- **Combined with child 1**, already on `main`: `git merge-tree` reports a clean
  merge; in a throwaway worktree of that merge, the marker, skill parity,
  manifest, shipped-procedure and verb tests → `218 passed`.
- Full suite, bare, reported by the implementing subagent: `3460 passed in
  1935.88s`. Not re-run in full by the coordinating session.

## Capability reconciliation

`work/run-a-procedure` and `work/configure-procedures` set to `Supported`
(`212f69cb`); `work/configure-the-work-lifecycle` changed as declared.
`tcw capabilities check` passes after the flip.

## Follow-ups

- The epic's `spec.md` is corrected on `main`: acceptance criterion 8's grep
  applies to converted `SKILL.md` files only, never to
  `tcw/work/procedures/`, whose `unattended-work` default names Codex by design;
  and the conversion children's briefs carry the shipped ids and the parity-test
  rule.
- Conversion children 3–6 are unblocked by this item and child 1.

## Closeout

- **Merge route:** `tcw work complete` merges `work/<slug>` into `main` locally.
  Not pushed.
- **Documentation:** README, release notes and changelog `upcoming.md`,
  `skills/tcw-work/references/commands.md` and `hooks.md`,
  `skills/tcw-configure/references/work.md`, `docs/guide/configuration.md`
  (`fcf57fcc`).
- **Version:** none cut; accumulated in `upcoming.md` per the epic's plan.
- **GitHub issue:** none.
