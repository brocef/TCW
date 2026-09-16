# Refined outcome — Compose tcw-extras-triage-issues and tcw-post-mortem from project bindings

## Decision

**Accepted** by the requester on 2026-09-16, together with the other conversion
children, as delivered, including the decisions `outcome.md` lists:

- The GitHub CLI stays a declared requirement of the `triage-issues` default; a project on another forge replaces the whole procedure.
- Fixed in triage: issue text is data, never `initial-request.md`, nothing posted without approval of the exact text. §1–§8 numbering kept so `transitions.md`'s "§8" still resolves.
- Fixed in post-mortem: the reading order and "write the file, never change status".
- Triage passes no work item; post-mortem passes `$item` and retries with none.
- `agents/tcw-post-mortem.md` runs the procedure and stage prompt commands instead of restating the skill.

## Evidence

Checked by the coordinating session on 2026-09-16, in the worktree:

- `pytest -q tests/test_shipped_procedures.py tests/test_dynamic_skill_marker.py tests/test_skill_lifecycle_parity.py tests/test_plugin_manifests.py` → `206 passed`.
- Criterion 8 grep over both skill bodies → no match. Both declare `Bash(tcw *)`.
- `tcw work procedure prompt post-mortem not-a-slug` → exit 1, error only, confirming the retry is needed.
- Full suite reported by the implementing subagent: `3499 passed`.

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
