# Plan — Close four instruction gaps proposit found in 3.0.1

Step 2 onward edits `tcw/`. As soon as it starts, the lifecycle is worked by
hand until the edits are committed, as this repository's CLAUDE.md requires.

1. **Tests first (red).** In `tests/test_shipped_prompts.py`: the Jira
   request passage contains "keep everything else in the description"; the
   spec prompt has an "Exit badly" bullet for a requester revising the request
   that says the item stays at spec and names the description and `## Added`;
   plan step 6 names `--project`, a commit and `tcw work edit`, in that order.
   For the message: find the existing Jira delegation test that makes an item
   (`grep -rn "left uncommitted\|delegate" tests/work/jira`) and assert the new
   wording there. Run; confirm each fails for the missing text.
2. **Design 1**: `tcw/work/prompts/request.md`.
3. **Design 2**: `tcw/work/prompts/spec.md`.
4. **Design 4**: plan step 6, `skills/work/SKILL.md` delegation bullet, and the
   message at `tcw/work/jira/tickets.py:395`.
5. **Design 3**: `skills/commands-plan-work/SKILL.md`; the capability
   description `docs/capabilities/skills/commands-plan-work/description.md`.
6. **Documentation entries**: changelog and release notes for TCW-101;
   `docs/guide/multi-repo.md` case 3 (Jira) names the new advice; the `work`
   skill is covered by step 4. README: check whether it describes
   `--project` filing; update only if it says something now incomplete.
7. Targeted tests, then bare `pytest`, `tcw validate`.
8. Multi review (own, Codex, `bllm`), since the user accepts on that basis.
