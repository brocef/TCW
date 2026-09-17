## Inbox manifest

- `2026-09-14-guards-and-gaps-the-skill-restructure-review-left.md`

## Inbox body

# Guards and gaps the skill restructure's review left for separate changes

Found by the adversarial code review of
`2026-09-14-restructure-tcw-s-skills-setup-and-configure-skills-command-and-extras-skills-and-no-slash-commands`.
None is caused by that item's own requirements, and each needs its own decision.

1. **The removed-names test scans only part of the repository.** It covers
   `skills/`, the two manifest folders, `README.md`, `docs/guide/` and
   `docs/lifecycle/`, as the item's spec asked. `agents/`, `hooks/`, `scripts/`,
   `evals/`, `tests/`, `AGENTS.md` and `CLAUDE.md` are clean today, but nothing
   stops a removed skill or command name coming back there.
2. **Nothing checks that `EXCLUSIONS` and `PARTIAL` in `evals/coverage.py` name
   skills that still ship.** A stale key (say a deleted skill) passes
   `tests/test_eval_coverage.py`.
3. **`tcw-setup`'s `install.md` never says how to run the bootstrap script under
   Codex.** It says "Under Codex there is no hook, and you run it", without the
   path to `scripts/session_bootstrap.sh` or its two arguments. `README.md` says
   the skill "runs the same install script". This predates the restructure; the
   text moved from `tcw-plugin` unchanged.
4. **`tcw-work-stage`'s manual fallback writes `<plugin>` for the plugin folder**
   with no instruction for finding that folder under Codex.
5. **Small duplication in tests.** The "body after the frontmatter" slice and the
   frontmatter parse are written three times (`tests/test_skill_lifecycle_parity.py`,
   `tests/test_documentation_sync_wiring.py`, `tests/test_plugin_manifests.py`).
   A shared helper would keep the rule for what counts as a skill body in one place.
6. **B4 and B8 only catch a wrong route into `tcw-setup`.** Each asserts
   `tool_input_absent` `tcw-setup/references/`, as the spec asked. A B8 run ("Set
   it up.") that opened a `tcw-configure` document instead passes every mechanized
   check, although "set it up" there asks for a term, a capability and a work item,
   not a configuration change. This is a gap in the spec, not a departure from it;
   adding `tool_input_absent` `tcw-configure/references/` to both cases would close it.

## Triage (2026-09-15)

Merged at triage because every part is about what the plugin's skills and their
capability documents tell a reader: the Codex instructions missing from
`tcw-setup`'s `install.md` and `tcw-work-stage`'s fallback, and skills described
in two capabilities at once. The maintainer asked for items touching the same feature
to be combined.

- **In scope:** parts 3 and 4 of the entry above, and §1 and §2 of the skill
  capability overlaps folded in below.
- **Not in scope here:** parts 1 and 5 above, and §3 below, are tracked in
  `2026-09-15-check-the-whole-tracked-tree-ledgers-included-for-removed-skill-names`; parts 2 and 6 above are tracked in
  `2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly`.

## Folded in: inbox entry `2026-09-14-skill-capability-overlaps-the-per-skill-review-left.md`

## Skill capability overlaps the per-skill ledger review left

Found while verifying `2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill`,
which gave each skill one capability under `docs/capabilities/skills/`. Both
reviewers placed these outside that item's scope.

### 1. `work/run-a-lifecycle-stage` still describes the `tcw-work-stage` skill

`docs/capabilities/work/run-a-lifecycle-stage/description.md` has two paragraphs
("Under Claude I can take both halves in one read" and "And I can ask for any
stage by name") about the `tcw-work-stage` skill, which now has its own
capability, `skills/tcw-work-stage`. That item's second goal was that no second
capability describes the same skill. Its spec left this capability to the skill
restructure item, which only reworded the paragraphs, so the goal is only partly
met.

Move what those paragraphs say that `skills/tcw-work-stage` does not already say
into it, and leave `work/run-a-lifecycle-stage` describing the two CLI commands.

### 2. The issue-closing rules are written in two capabilities

`work/complete-a-work-item` (its last paragraph) and `skills/tcw-extras-triage-issues`
both say which resolutions close the originating GitHub issue. This was true
before the per-skill item, which only moved the triage entry. Pick one home and
link to it from the other.

### 3. No test keeps removed skill and command names out of the ledger

`tests/test_skill_lifecycle_parity.py` checks `DELETED_NAMES` against
`LIVE_ROUTES`, which does not include `docs/capabilities` or `docs/taxonomy`. The
per-skill item checked those folders with a one-off `git grep` (its acceptance
criterion 8), which misses names written without a leading slash, such as
`tcw-audit-work-backlog`. A hand scan with the whole-name matcher found both
folders clean on 2026-09-14. Adding both folders to `LIVE_ROUTES` would keep them
clean. Exempt `tcw://C/skills/...` links, which contain skill names on purpose.
