# Outcome — State the two rules for an overridable skill and mark every skill with its verdict

## What shipped

| Task | Commit | What |
| --- | --- | --- |
| 1 | `499d8ac6` | `skills/README.md`: the two rules (Rule 2 checked first), why a project cannot add a procedure id, what `dynamic_skill` means, and one verdict row for each of the 49 shipped documents. `tests/test_dynamic_skill_marker.py` with the three completeness tests |
| 2 | `e77771f2` | `dynamic_skill: true\|false # which skills a project may override, and why: ../README.md` as the last frontmatter line of all sixteen `skills/*/SKILL.md`; the two marker tests |
| 3 | `db5f4251` | `docs/changelogs/upcoming.md`, under `Added` |

Stage artifacts: `31a2ea80` spec, `4bc2514a` plan, and `cf993127` / `62f2e158`
adding the gate-refusal notes the coordinator asked for.

## Test result

- Full suite, bare, from the worktree root in its own `.venv`, on `e77771f2`:
  **`3435 passed in 1451.08s (0:24:11)`**.
- After the documentation and notes commits, the skill, manifest, pointer,
  documentation-sync and version-cut tests again: `206 passed in 10.44s`.

Every new test was watched go red for the right reason before it passed:

- Before `skills/README.md` existed, all three completeness tests failed on the
  missing file.
- Before the key existed, all 32 marker tests (16 skills × 2 tests) failed with
  "`<skill>` has no dynamic_skill key".
- Mutations (spec criterion 2), each read for its reason and then undone:
  - a. Deleting the `tcw-setup` `SKILL.md` row gave `skills/tcw-setup/SKILL.md: 0 rows`.
  - b. `touch skills/tcw-work/references/scratch.md` gave `...scratch.md: 0 rows`.
  - An extra row naming `agents/nope.md` gave "verdict rows naming no shipped document".
  - c. Deleting the key from `tcw-setup` gave "no dynamic_skill key", plus the comment test.
  - d. Flipping `tcw-post-mortem` to `false` gave "dynamic_skill is False but skills/README.md says 'overridable'".
  - e. Stripping the comment from `tcw-work` gave "must end in a comment naming ../README.md".

Other criteria:

- Criterion 4: `git diff --numstat main -- 'skills/*/SKILL.md'` gives sixteen
  files, each `1 0`.
- Criterion 5: `git diff --stat main -- agents 'skills/*/references'` prints
  nothing.
- Criterion 6: `claude plugin validate --strict skills` gives "Validation passed".

## Verification the suite cannot do

- **Reachability.** I opened `skills/tcw-extras-autonomous-work/SKILL.md` cold.
  Line 4 reads `dynamic_skill: true # which skills a project may override, and
  why: ../README.md`, and from that folder `../README.md` is
  `skills/README.md`. Its first section, "What `dynamic_skill` means", answers
  both "what is this key" and "may I change what this skill says". It also says
  that `true` on an unconverted skill records intent.
- **Codex.** Not exercised in a live session. `codex` 0.154.0 is installed, but
  the only way to list a plugin's skills is to install the plugin into the
  user's Codex configuration, which is outside this item's limits. The evidence
  is still the parser source cited in the spec (no `deny_unknown_fields`), plus
  the thirteen skills that already ship an unknown top-level `when_to_use`.
- **Verdicts.** Judgments. The ones the requester did not give are listed below.

## What the plan or spec got wrong

- **The plan's order of work.** Plan task 1 step 5 ran the full suite before
  committing task 1. It did not happen. The first suite run started before
  task 1 and ran against a tree I was editing, so it was not a clean starting
  point, and at about 25 minutes per run on this shared machine it was stopped.
  Tasks 1 and 2 were committed on the targeted test modules (168, then 227
  passing), and the full suite ran once, on the task 2 commit. So there is no
  full-suite result for the task 1 commit taken alone. Task 2 only adds
  frontmatter lines and tests, so a failure hidden at task 1 would still have
  shown at task 2.
- **Mutation checks in a dirty tree.** For the first attempt at mutations c–e,
  I undid each one with `git checkout`, which also threw away the uncommitted
  key additions in `tcw-setup`, `tcw-post-mortem` and `tcw-work`. That made the
  d and e results worthless. I noticed from the output, added the three lines
  back, and redid d and e by restoring from backup copies. The results above
  come from the second run. The committed diff was checked afterwards: sixteen
  one-line additions.
- **Spec, Problem 2** first said "twenty-seven" unclassified documents. The
  count is twenty-three; this was corrected before the spec was committed.
- **Epic documents** (already recorded in the spec's Notes):
  - The ownership table leaves out `agents/tcw-backlog-auditor.md`, which must
    change when `audit-backlog.md` is converted.
  - The plan's check of reachability "from a fresh reading of
    `tcw-work/SKILL.md`" is replaced by the comment on the key and the
    completeness test.
  - `tcw/store/base.py:2267` has moved to `:2266`.
  - The plan gives child 6 all of `skills/tcw-work-create/**`, but the verdicts
    keep `references/find-overlap.md` fixed.

## Decisions for the requester to confirm

1. The rules document is `skills/README.md`. A reader reaches it from a comment
   on each `dynamic_skill` line, and a failing completeness test names it. No
   link was added to any skill body.
2. `dynamic_skill` is a top-level key, not under `metadata:`. The Agentskills
   specification limits `metadata` to text values. The `skills-ref` validator
   would reject the top-level key, as it already rejects `when_to_use` and
   `arguments`; nothing here runs `skills-ref`.
3. `tcw-work-stage` has the verdict `composes already` and `dynamic_skill: true`.
4. The seven `references/lifecycle/stage-*.md` documents and `commands.md`,
   `transitions.md`, `hooks.md`, `tags.md`, `epic-deltas.md` and
   `cross-node-deltas.md` are fixed under Rule 1.
5. `documentation-sync`'s `cut-version.md` and
   `release-notes-and-changelogs.md` are overridable and go with their skill.
6. `tcw-setup`'s `install.md` and `project.md` are fixed under Rule 1.
   `taxonomy.md` and `capabilities.md` are also fixed under Rule 1, although
   they describe conduct, because they run once during setup, before a project
   has any bindings.
7. `tcw-work-create`'s `find-overlap.md` is fixed under Rule 1 and does **not**
   go with its overridable skill, because it defines what counts as a duplicate.
8. The three agents have a fifth verdict, `fixed (accelerator)`: the project's
   choice lives in the text that dispatches an agent. `tcw-verifier.md` does not
   strictly pass Rule 2.
9. `tcw validate` does not report the key; only the test checks it.
10. The key records intent, not something derived from the code: until children
    3–6 land, five skills read `true` while nothing in them can yet be replaced.

## Notes

- **Documentation Sync.** `docs/changelogs/upcoming.md` fired and is updated.
  The release notes, `README.md`, `skills/<component>/SKILL.md`,
  `skills/tcw-configure/references/<document>.md` and `docs/guide/jira.md` did
  not fire, for the reasons in the plan's task 3. Re-checked against the
  finished diff, which touches no CLI command, configuration key or tracker.
- **The `tcw` CLI, as observed during this item. Nothing was changed.**
  - When an item is started into a worktree before planning, the `spec` and
    `plan` gates cannot be run at all: both refuse on status. So `plan`'s `pre`
    check, `require_artifact.py spec`, cannot be run through the gate either;
    it was run by hand with `TCW_SLUG` set.
  - `tcw work stage gate implement` passed on an item that had no `spec.md` and
    no `plan.md`. This project binds no artifact check to `implement`, so
    nothing requires a plan before implementation. That is a gap in this
    project's configuration rather than a defect in the CLI, but it means the
    gates alone would not have stopped implementation from starting unplanned.
- The worktree `.venv/` is gitignored and left in place.
