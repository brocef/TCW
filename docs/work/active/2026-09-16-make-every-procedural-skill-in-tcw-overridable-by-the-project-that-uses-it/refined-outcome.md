# Refined outcome — Make every procedural skill in TCW overridable by the project that uses it

## Decision

**Accepted.** Each child was accepted by the requester on 2026-09-16; the
requester then instructed: merge everything to `main` and push, with no version
bump, and without re-running the full suite after the rename merge.

## Criteria checked on `main`

- 2, 3: `dynamic_skill` on all 16 skills — 10 `false`, 6 `true`; marker test in
  the targeted run.
- 4–7: `tcw work procedure prompt search` prints the default; `tcw validate`
  OK.
- 8: the grep over the five converted skill bodies prints nothing (0 matches
  each).
- 13: `tcw capabilities check` OK.
- 12: not re-run in full after the rename merge (requester's instruction); see
  `outcome.md`.
- 14: all six children completed.

## Deferred

Live Claude Code and Codex sessions exercising the converted skills, an
unattended run, and eval arms touching these skills — accepted without them.

## Closeout

- **Merge route:** all children merged into `main` locally; pushed.
- **Version:** none cut (requester's instruction); entries stay in `upcoming.md`.
- **Follow-ups:** the two lifecycle defects filed in `outcome.md`; per-reference
  replacement for documentation-sync belongs to
  `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`.
- **GitHub issue:** none.
