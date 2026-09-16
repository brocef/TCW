# Refined outcome — Compose the five tcw-work procedure documents from project bindings

## Decision

**Accepted** by the requester on 2026-09-16, together with the other conversion
children, as delivered, including the decisions `outcome.md` lists:

- Fixed on the pages: delegation's stage/transition rules, the delegable table, verify's split, "Delegable means permitted, never required" and "Custom agents"; audit-backlog's whole approval rule; consolidate-plans' "start only when asked" and deletion rules; decompose's nesting behaviour and the `--parent`/`--initiative` choice; search's "It is read-only".
- Two sentences in `delegation.md` reworded to name no harness.
- The documents pass no work item; `tcw-backlog-auditor` passes its item.
- No fallback copy of any default; a reader whose command fails reports it.
- The README auditor row describes checking against the project's procedure.

## Evidence

Checked by the coordinating session on 2026-09-16, in the worktree:

- `pytest -q tests/test_shipped_procedures.py tests/test_dynamic_skill_marker.py tests/test_skill_lifecycle_parity.py tests/test_plugin_manifests.py` → `206 passed`.
- Criterion 8 grep over the five documents and `agents/tcw-backlog-auditor.md` → no match.
- Full suite reported by the implementing subagent: `3499 passed`.
- The last commit's `Claude-Session:` trailer was removed before merge, at the requester's instruction.

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
