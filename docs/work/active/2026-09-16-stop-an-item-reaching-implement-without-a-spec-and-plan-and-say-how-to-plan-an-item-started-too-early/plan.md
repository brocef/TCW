# Plan — Stop an item reaching implement without a spec and plan

1. **Tests first** (`tests/test_unplanned_start.py`): acceptance criteria 1–5;
   update `tests/test_stage_verb.py`'s literal table and the no-overlap test
   (exception for `plan`, reason stated).
2. **Code**: `STAGE_STATUSES` spec/plan → `("backlog", "active")` with the
   comment updated; a `_missing_plan_warning(st, bare)` helper in
   `tcw/work/cli.py` called after a successful start and in the implement
   gate; `STAGE_NEXT_STEPS["plan"]` names both branches.
3. **Config**: `tcw-config.yaml` `implement.pre` binds
   `require_artifact.py spec` and `plan`.
4. **Docs**: `tcw/work/prompts/plan.md` step 7, transitions.md (`start` check
   now printed; recovery), `skills/work/SKILL.md` if it states legality, the
   changelog and release notes.

Verification: the reproduction by hand with the worktree's `tcw` in a scratch
node.
