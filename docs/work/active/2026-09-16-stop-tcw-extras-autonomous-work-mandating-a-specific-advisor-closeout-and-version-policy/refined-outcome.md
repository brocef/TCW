# Refined outcome — Stop tcw-extras-autonomous-work mandating a specific advisor, closeout and version policy

## Decision

**Accepted** by the requester on 2026-09-16, together with the other conversion
children, as delivered, including the decisions `outcome.md` lists:

- Fixed in the skill: title, opening, "Ask once", the new "What an advisor must be" section, the hard blockers and the audit trail. Replaceable default (`unattended-work`): "The advisors" and "Checkpoint map".
- The weighing rule does not depend on the number of advisors; "two advisors" became "advisors" and "both" became "all of them".
- No work item is passed to the injected command.
- The closeout does not defer to `work.trunk-branch` or `work.publish-transitions`.
- `allowed-tools` declares the default's needs (`codex`, `git merge`, `Agent`, `SendMessage`) but not `git push`; `compatibility:` says it describes the default only.
- Criterion 8's grep covers the body; the frontmatter names the default's tools on purpose (criterion 9).

## Evidence

Checked by the coordinating session on 2026-09-16, in the worktree:

- `pytest -q tests/test_unattended_work_skill.py tests/test_shipped_procedures.py tests/test_dynamic_skill_marker.py tests/test_skill_lifecycle_parity.py tests/test_plugin_manifests.py` → `209 passed`.
- Criterion 8 grep over the skill body → no match.
- Rebuilt text (body with the command's output in place) against `main`: the only removed lines are the description, "the two advisors" and "both call"; everything else is added.
- Full suite reported by the implementing subagent: `3502 passed`.

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
