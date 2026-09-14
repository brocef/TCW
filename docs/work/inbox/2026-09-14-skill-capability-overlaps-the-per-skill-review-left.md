# Skill capability overlaps the per-skill ledger review left

Found while verifying `2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill`,
which gave each skill one capability under `docs/capabilities/skills/`. Both
reviewers placed these outside that item's scope.

## 1. `work/run-a-lifecycle-stage` still describes the `tcw-work-stage` skill

`docs/capabilities/work/run-a-lifecycle-stage/description.md` has two paragraphs
("Under Claude I can take both halves in one read" and "And I can ask for any
stage by name") about the `tcw-work-stage` skill, which now has its own
capability, `skills/tcw-work-stage`. That item's second goal was that no second
capability describes the same skill. Its spec left this capability to the skill
restructure item, which only reworded the paragraphs, so the goal is only partly
met.

Move what those paragraphs say that `skills/tcw-work-stage` does not already say
into it, and leave `work/run-a-lifecycle-stage` describing the two CLI commands.

## 2. The issue-closing rules are written in two capabilities

`work/complete-a-work-item` (its last paragraph) and `skills/tcw-extras-triage-issues`
both say which resolutions close the originating GitHub issue. This was true
before the per-skill item, which only moved the triage entry. Pick one home and
link to it from the other.

## 3. No test keeps removed skill and command names out of the ledger

`tests/test_skill_lifecycle_parity.py` checks `DELETED_NAMES` against
`LIVE_ROUTES`, which does not include `docs/capabilities` or `docs/taxonomy`. The
per-skill item checked those folders with a one-off `git grep` (its acceptance
criterion 8), which misses names written without a leading slash, such as
`tcw-audit-work-backlog`. A hand scan with the whole-name matcher found both
folders clean on 2026-09-14. Adding both folders to `LIVE_ROUTES` would keep them
clean. Exempt `tcw://C/skills/...` links, which contain skill names on purpose.
