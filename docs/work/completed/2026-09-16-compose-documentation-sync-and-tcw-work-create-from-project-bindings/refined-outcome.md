# Refined outcome — Compose documentation-sync and tcw-work-create from project bindings

## Decision

**Accepted** by the requester on 2026-09-16, together with the other conversion
children, as delivered, including the decisions `outcome.md` lists:

- `documentation-sync`'s two references stay whole files reached through the default; per-reference replacement would need a second id.
- tcw-work-create keeps its opening rules and the whole search step fixed; checkout choice, precedence order and report lines are replaceable.
- `documentation-sync` gains `allowed-tools: Bash(tcw *), Bash(cat *)`.
- **Changed at acceptance:** the `cat` fallback in `documentation-sync`'s injection is removed. Instead `tcw work procedure prompt <id>` without a slug prints TCW's default outside a TCW project (requester's decision), so a project's own failure is never hidden. Done on this branch during integration.
- **Changed at acceptance:** `stage-verify.md`'s direct pointer to `references/cut-version.md` goes through the `documentation-sync` procedure instead, so a project's replacement is respected (requester's decision). Done on this branch during integration.

## Evidence

Checked by the coordinating session on 2026-09-16, in the worktree:

- `pytest -q tests/test_shipped_procedures.py tests/test_dynamic_skill_marker.py tests/test_skill_lifecycle_parity.py tests/test_plugin_manifests.py tests/test_documentation_sync_wiring.py` → `212 passed`.
- Criterion 8 grep over both skill bodies → no match. `find-overlap.md` unchanged.
- Full suite reported by the implementing subagent: `3498 passed`.
- The outcome commit's `Claude-Session:` trailer was removed before merge, at the requester's instruction.

## Deferred, by the requester's decision

Live checks were not run: a live Claude Code session invoking the converted
text, a Codex session following the manual command block, and (where they
apply) a real dispatch of an agent or an unattended run. The requester accepted
without them.

## Integration

The four conversion children each changed `tests/test_shipped_procedures.py`'s
drift check in a different shape. They are merged one at a time; the
coordinating session unifies them into one design on the last branch and runs
the full suite once on the combined result before the epic closes.

## Closeout

- **Merge route:** `tcw work complete` merges the branch into `main` locally. Not
  pushed; the requester pushes once the whole epic is done and approved.
- **Documentation:** changelog and release-note bullets on this branch.
- **Version:** none cut; accumulated in `upcoming.md`.
- **GitHub issue:** none.

## Integration result

Recorded by the coordinating session on 2026-09-16, on this branch after `main`
(children 1–5 merged) was merged in and the requester's three changes were made:

- `04969ef5` — `tcw work procedure prompt <id>` without a slug prints TCW's
  default outside a TCW node; with a slug, or in an unprovisioned node, it still
  refuses. Tests written first and watched failing.
- `9aa663c9` — `documentation-sync` drops the `cat` fallback; its manual block
  reads the default file only when `tcw` is not installed.
- `5152db84` — `stage-verify.md` reaches the version cut through the
  `documentation-sync` procedure.
- `7765ace7` (merge) — `tests/test_shipped_procedures.py` uses one `Composes`
  marker for all ten converted sources; each check was broken on purpose and
  failed with a message naming the file.
- `033013d9` — changelog, release notes and `commands.md` updated to match.
- **Full suite, bare, on the combined branch:** `3505 passed in 828.95s`.
