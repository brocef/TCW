---
verdict: rejected
judges: 1
---
# Review round 1 (TCW-76, Task B22)

Four reviewers, each a separate agent that did not write the change and could
only read, reviewed the work at `c6bb5451` (`epic/tcw-3.0`): one the
migration guide (`docs/migration-guide-2.8-to-3.0.0.md`), one the combined
difference of the guide, the migration log, `AGENTS.md`, the release notes
and the changelog, one the tests, and one the board and the Jira record. The
coordinating session sorted their findings into those accepted for this
item, below, and those that need a separate change. This round records that
sorting; the session that fixes the findings checks each against the
repository again before acting on it (implement round 2).

**Verdict: rejected.** The acceptance criteria that bear on the guide's
correctness (criteria 1 to 10 and 32: the guide gives a migration an agent can
follow, with a check per step) are not met while the defects below stand,
since several of them make a step's action or check wrong for some project
(G2 to G7, G11a to G11f). The others are wrong statements in the guide, the
log, `AGENTS.md`, the release notes, the changelog and the bound lifecycle
files. No criterion was found unmet in the code: nothing under `tcw/`,
`skills/`, `agents/` or `web/` changed (criterion 23), and the suite was
green at `61af5c5a` (criterion 21, this item's log, Task B20).

Implement must fix every finding below, verifying each against the code or
files first, changing only `docs/`, `tests/`, `AGENTS.md` and the migration
log.

## Accepted findings

Line numbers are at `c6bb5451`.

### The guide's reviewer

- **G1.** The Hook variables table's `TCW_RESOLUTION` row (line 1263) says a
  discard's reason is in `TCW_REASON`. `hook_env` (`tcw/work/advance.py`,
  164-179) sets `TCW_REASON` only on a forced move, and `discard()` does not
  force. The reason is in the discard's comment, not in a variable.
- **G2.** The guide never says that optional stages are on by default
  (`tcw/work/config.py`, about line 361), so a project that wants one off must
  write `work.stages.<stage>.enabled: false`. Step 1's plan, step 3's rewrite
  and the Configuration table should say so.
- **G3.** The `work.tracker.statuses` row (about line 1177) does not cover a
  2.x `statuses.discarded` given as a mapping by resolution (v2.8.1
  `tcw/store/base.py`, about 1734-1744), or two stages sharing one status,
  which 3.0 refuses ("each stage needs its own status",
  `tcw/work/config.py`, about 419). The plan must decide both; the second is
  fixed with a new Jira status at step 2.
- **G4.** Status names must now match Jira's exactly: 3.0 compares them
  exactly, while 2.x ignored case and spacing (v2.8.1 `_same_status`). Say so
  at the statuses row, and have step 3 check the spelling before changing
  Jira.
- **G5.** Step 9 (about 622-644): the rewrite and the check must match whole
  names, not substrings; rewrite the longest names first; follow chained
  `renames.yaml` pairs to their end; and test the rewrite on a small sample,
  including a name that is a prefix of another.
- **G6.** Step 12 does not follow symbolic links inside the folders it lists:
  neither GNU nor macOS `grep -r` reads them. The log's sentence about it
  (about 1740-1751) overstates what amendment 7 covers.
- **G7.** Step 12's private files (about 826, 830-832, 848) have no project in
  their names, so two projects migrated by one person would share them. Give
  them the project's ID, and update this run's log where it names them.
- **G8.** (Suspected; no Jira test.) The rule "the child cannot be placed
  under that parent: list it in the plan" covers only tickets being created.
  It applies equally to an existing ticket whose parent Jira's hierarchy
  would refuse.
- **G9.** `tcw capabilities reset` changed: 3.0 refuses when something is
  nested under the override (`tcw/store/fs.py`, about 2563); v2.8.1 removed it
  all. It belongs in "Behavior that changed", the Commands table should not
  call it unchanged, and the test's list of changed behavior should name it.
- **G10.** `tests/test_migration_guide.py`:
  `test_no_check_before_step_8_needs_the_inbox_gone` would pass if step 4's
  check lost its inbox exception, and `test_steps_9_and_10_check_only_their_scope`
  would pass with a step 10 check over the whole repository. Amendments 4 to
  7, and the fixes for G5 to G7, have no tests. Every new or changed test is
  mutation-checked.
- **G11a.** Step 5's filesystem-mode comment is a new file each time, so a
  rerun writes a second one. Step 5 needs the skip check Jira mode has.
- **G11b.** Step 9's list of old names leaves out the inbox entries renamed at
  step 8.
- **G11c.** Step 12's check and its `expected-names` reading do not handle a
  second run (`## Run 2`), as step 1's check does.
- **G11d.** About 636-638: "the step 6 commit renames…" assumes commits, which
  rule 5 makes optional.
- **G11e.** Step 3 copies only `tcw-config.yaml` into the scratch folder and
  greps only it, though `tcw-config.local.yaml` is rewritten too. Step 10's
  `<hook files>` can name `tcw-config.local.yaml`, a file git does not track,
  while rule 7 sends check output into the committed log.
- **G11f.** Amendment 7's link replacement writes absolute paths, so a link
  inside the repository would put the home folder's path into the committed
  `expected-names` block.

### The combined reviewer

- **C1.** Guide line 38 ("only a shell, `curl` and `tcw`") and the release
  note (`docs/release-notes/upcoming/TCW-76-…md`, lines 5-6) leave out `jq`,
  which Jira mode needs.
- **C2.** `AGENTS.md` (lines 35-36) says every stage's instructions start with
  `git pull --ff-only`, but `inbox` binds no prompt; the changelog
  (`docs/changelogs/upcoming/TCW-76-…md`, lines 24-26) says "on every stage"
  for both the prompt and the commit hook. Both should match
  `tcw-config.yaml`, which stays as it is.
- **C3.** `AGENTS.md` line 21 says the stage prompt "behaves identically
  under Claude and Codex"; TCW ships to Claude Code, Codex and Pi.
- **C4.** The log's "Amendments to the guide" summary (about 110-170) stops at
  amendment 6, though amendment 7 was made.
- **C5.** Step 12's places leave out Pi's: `~/.pi/agent/AGENTS.md`,
  `~/.pi/agent/skills/`, `~/.pi/agent/prompts/`, a project's `.pi/` folder,
  and the packages `~/.pi/agent/settings.json` lists. This run's step 12
  should record that they were searched.
- **C6.** `docs/lifecycle/harness.md` line 19, "a skill may instruct
  delegation directly without a single-session fallback", contradicts the
  Pi paragraph below it and `skills/work/SKILL.md` (lines 77-78).

### The tests' reviewer

- **T1.** `tests/test_repo_lifecycle.py`'s `SPEC_HEADINGS` (about line 27) is
  a copy of the seven sections `tcw/work/prompts/spec.md` asks for, so the
  test cannot notice the prompt changing. Read it from the prompt, and
  mutation-check it.

### The board's reviewer

- **B-B.** `docs/lifecycle/review.md` (lines 34-35) says "the qa round
  records" that closing an issue waits for publication; in Jira mode qa is
  kept in Jira. Use `AGENTS.md`'s wording.
- **B-C.** The log's evidence line for criterion 31 (about 2308) says an
  `updated >=` search was run; it was not. Say the rerun was checked by the
  call log, and why the search cannot be run now.
- **B-D.** The log does not record the tag the plan's D7 approved: `tcw-2.x-final`
  on `8b5a212b`, made by the agent on 2026-10-16, a lightweight tag, local
  only, not pushed.
- **B-E.** `implement/round-1.md` (lines 3-6) opens by calling itself the
  migration log, then says the log is elsewhere.
- **B-F.** The log (about 552-554) says TCW-69 to TCW-75 and TCW-77 "become
  untracked references under TCW-68". 3.0 lists only an item's parent and
  blockers as untracked (`tcw/work/jira/backend.py`, about 373-375), never
  its children.
- **B-G.** The log (about 1115) commits the owner's Jira account ID.

## Needs a separate change

Not fixed by this item; listed so they are not lost.

- `skills/documentation-sync/references/release-notes-and-changelogs.md`
  line 31 still describes date-named entry files, and
  `docs/guide/configuration.md` line 195 leaves Pi out. The first is under
  `skills/`, which the freeze forbids changing; both belong with that fix.
- `work.jira.inbox-query`: its documentation
  (`skills/configure/references/jira.md`, 78-81) does not match
  `tcw/work/jira/tickets.py` (83-84).
- `tcw work procedure` has no answer for live documents, and the documentation
  scans do not read keys written in YAML form.
- The template-binding assertion in `tests/test_repo_lifecycle.py`.
- The `jira_project` fixture's error when tests run in a mixed order.
- The round-counted deadline in `check_versions`.
- For the owner at the 3.0.0 cut: the combined changelog's history of the
  documentation allowance, TCW-75's stale line 43, and the release notes'
  `## Upgrading` section coming last.
