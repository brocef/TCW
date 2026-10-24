# Implement round 1 — TCW-116

Built on the branch `impl-116`, from `e309b806` on `v4`, in the worktree
`.claude/worktrees/impl-116`. The code under test was run from that
worktree's own virtual environment (`.venv/bin/pytest`). Hand runs of `tcw`
went only through a wrapper that refuses to run outside the session's
scratchpad, unsets every `TCW_*` variable and gives the run its own home
and cache folders; they were made against scratch projects and scratch
clones, never this repository. The released 3.0.2 `tcw` was run only inside
scratch folders, to record what TCW 3 lists for each fixture. No lifecycle
command was run, no `git pull`, and no ticket was moved or written to: the
dispatching session makes every move. Jira was only ever the suite's
stand-in. This is the first implement round, so it answers no rejection. It
gives no verdict.

## Commits

| Commit     | Steps |
| ---------- | ----- |
| `001685a5` | 1: the `tcw migrate` command, spared every check made before a command |
| `bf95865b` | 2, before it: two guards' exemptions matched by whole path parts |
| `a041dcd8` | 2: the 3.x readers part 1 needs, F-single, the goldens |
| `973eb4c3` | 3: the executor, its phases and the progress record |
| `d52197f2` | 4: the configuration editor's three edits, `rewrite_yaml`'s function form |
| `4074b8d3` | 5: the configuration into `.tcw/` (C1, C2, C6, C7) |
| `3d20aa15` | 6: state files, `cap-…` ids into `.tcw/tcw-migration.yaml` (C9-C12) |
| `eccb269b` | 7: loose files into `resources/` (C13), A3 |
| `ba950de4` | 8: the project's own references (C16) |
| `272f5ab9` | 9: each ticket's `TCW Item` (C17), last |
| `857420d8` | 10: the planned files checked as TCW 4 reads them; the check after the run |
| `87d72772` | 11: F-single end to end; B17 before any write |
| `8d11e29f` | 12: the ledger test reads this repository's records in either form |
| `3cf76fad` | 13: `tcw migrate` recorded in this repository's ledgers |
| (no commit) | 14: the proof on scratch clones |
| `91410a14` | 15: the 3.x readers part 2 needs; F-full |
| `2cfd1947` | 16: the related projects, placed, read only when asked |
| `05d9600f` | 17: `projects:` as `parents:` and `children:` |
| `882b28f4` | 18: manifest entries (C4, M1-M6) |
| `886386e8` | 19: `extends` as parent links (C8, E1-E5, D1, D6, D8, A8) |
| `9d501b05` | 20: store locations outside the project (C5, B6, B7) |
| `1b1a102d` | 21: overrides to their original's path (C14, C15, B9, D2-D4) |
| `de6aad9d` | 22: references owned by another project (C16, B10) |
| `eeea2794` | 23: the migration record kept correct across a move |
| `569b2d75` | 24: F-full end to end |
| `d9d85f3d` | 24: the monorepo, and the second person (Design 2.11) |
| `a76200ab` | 25, found by it: the ownership sweep lists the migration's callers |
| `3494ac7e` | 26: the way back for the tickets |
| `596fd9d7` | 28: the changelog and release-note entries |

## What was done, step by step

**Step 0.** TCW-106 to TCW-115 were on `v4`; `git diff v3.0.2 main -- tcw/`
is empty, so `main` (`64042c2b`) holds 3.0.2's code. The baseline suite had
one failure, `tests/test_shipped_prompts.py`, caused by this worktree's
untracked `node_modules` link (it copies the link as a folder). Every plan
reference to `tcw/cli.py`, `tcw/validate.py`, the guards and the readers was
checked against the code at `e309b806`; where it had moved, the step was
adapted, as listed under "What the plan or spec got wrong".

**Steps 1 to 13 (part 1).** Built as the plan says, with these additions:

- Step 1: `tests/test_cli_contract.py` gained a row for `migrate`, which
  its every-command test demands.
- Step 2: the goldens' recorder, `tests/migrate/record_3x_listings.py`,
  gained `--tcw`, so the goldens were recorded
  with the released 3.0.2 as the brief asks; a byte changed in a fixture
  turns both currency tests red, naming the golden and the script.
- Step 3: a write records the other files its text was planned from, with
  their digests, so a re-run after a hand edit writes nothing more
  (criterion 60). `tests/move_stops.every_stop` gained `stopped_says`.
- Step 4: `tests/test_parent_links_static.py` (TCW-108's guard against
  `projects:` in tests) needed an exemption for `tests/migrate/`, which the
  plan did not name; added by whole path parts, with a reach test.
- Step 10: `parse_project_file_text`, `parse_state_text` and
  `collect_findings` did not exist; they were written in `tcw/config.py`,
  `tcw/object_folders.py` and `tcw/cli.py`. Found and fixed: the function
  form of `rewrite_yaml` turned `Roles: 5` into a reference; it is now
  never asked about a value YAML reads as something other than text.
- Step 11: found and fixed, a run following a progress record wrote the
  steps before a hand-edited file before refusing (B17); every step is now
  judged first. B6 and A7 were built here, since the tests showed them
  missing.
- Step 13: the capability `cli/migrate-a-tcw-3-x-project-to-tcw-4`
  (`cap-eeaeb9`, Supported) and the term `migration`, in 3.x form; TCW
  3.0.2's validate on a scratch copy of `docs/`: 0 errors.

**Step 14, the proof on this repository** (scratch clones of `impl-116` at
`3cf76fad`; nothing pushed). `tcw migrate --no-jira`: exit 0, 295 files
written, 2 moved, 231 deleted, 0 tickets; 58 work items, 111 capabilities
and 61 terms in 4.0 form; 111 ids recorded; 2 loose files moved into
`resources/` (TCW-76's `notes-from-tcw-74.md`, TCW-99's `design.md`); 214
writes carry C16; 23 A3 and 1 A4. A second run: `nothing to migrate in the
files`. A run stopped by a read-only folder (TCW-106's) and run again gave
files identical to the uninterrupted clone. A plain `tcw migrate` with no
credentials: exit 1, nothing written. The suite on the migrated clone, both
halves: one failure, `tests/test_eval_runner.py`'s source-tree trace, which
expects the virtual environment's install to be the clone's (it was the
worktree's). TCW 4's validate: 0 errors, 0 warnings. **Step 1 of the proof
(the dry run against the live board) was not run**: the brief forbids any
live Jira site, so the tickets it would list are not known here.

**Steps 15 to 24 (part 2).** Built as the plan says, with the departures
listed below. F-full was built in Step 15 rather than Step 24, since Step
15's reader tests compare with its golden. Step 24's tests found and
fixed four things:

- folders an override's moves left empty are removed at the end of a
  finished run, since TCW 4's validate reports an empty folder;
- each missing folder is made as its own counted write, which the
  stop-at-every-write test showed was not so;
- A8, the list of related projects still in 3.x form, now names every
  project TCW 3's walk reaches, so a run in a package names the root and
  its siblings;
- a second person's run in a project someone else migrated writes their
  personal manifest entry for each TCW 3 cache clone on their machine
  (`config.clone_entries`), as Design 2.11 and TCW-115's note ask.

**Step 25, the proof again** (scratch clones of `impl-116` at `d9d85f3d`).
The same counts as Step 14, which is expected: this repository has no
`projects:`, `extends` or overrides, so part 2 changes nothing here. The
stop and finish, the second run and the run without credentials behaved as
in Step 14. The suite on the migrated clone found two failures in
`tests/test_ownership_sweep.py` that the code had caused in the worktree as
well: the relations converter's list and set edits and TCW 3's reading of a
relative `TCW_PROJECT_<ID>` against the working folder were not listed.
They are listed in `a76200ab`. TCW 4's validate on the clone: 0 errors, 0
warnings, 0 unresolved. **The rehearsal of Design 9.3 step 3 was not
made**: TCW-117 has only its spec and plan on `v4`, so there is no
`UNMIGRATED_RECORDS` to delete.

**Step 26.** `tcw/migrate/jira.py` gained `edited_tickets`, which reads the
ticket edits from a run's saved output, and `restore_tickets(pairs,
client, root, project_id)`, which puts each 3.x value back through
`set_item_values` with the pairs swapped. Its fake run: F-single migrated
with Jira edits APP-1, APP-2 and APP-3; `restore_tickets` with a client
talking to the fake puts every ticket's `TCW Item` back as it was, and a
second call edits nothing. With the pairs not swapped, the test goes red.

**Step 27.** The notes for the later children are below, for the
dispatching session to post.

**Step 28.** The documentation entries were read from the root
`tcw-config.yaml` directly (the brief forbids `tcw work docs`); they are
the eight the plan's table names, and each was answered as the table says:
the changelog and release-note entry files are written; `README.md`,
`docs/guide/jira.md`, the migration guide, the `setup` and `work` skills,
and `docs/use-cases.md` S-8 and S-9 are TCW-117's; no configuration key
changed, so `skills/configure/references/` does not fire.

## Test result

Run just now, at `596fd9d7`, as CI runs it, with
`env -u TCW_JIRA_EMAIL -u TCW_JIRA_API_KEY .venv/bin/pytest -q -p no:cacheprovider`:

- `tests/work tests/serve`: 2243 passed, 2 skipped.
- The rest, run in two parts to stay inside the shell's time limit:
  `--ignore=tests/work --ignore=tests/serve --ignore=tests/migrate`: 5158
  passed, 111 skipped, 1 failed; `tests/migrate`: 314 passed.

The one failure is the baseline's,
`tests/test_shipped_prompts.py::test_the_wheel_carries_exactly_the_prompts_and_procedures`:
it copies the untracked `node_modules` link in this worktree as a folder.
It passes in a clone, which has no such link (Steps 14 and 25).

Every new test was red before its code, or, where it was written with the
code (Steps 15 and 22, said so in the notes), was shown to go red by
breaking what it observes. Each step's mutation checks are recorded in the
commit's step above in the notes kept for this round; among them: the
`_check_here` skip, the progress record's own digest, the anchor and final
checks of the editor, the ancestor-before rule of E4, the `moved:` map,
B7, A8, D2, and the way back's swap.

## What the plan or spec got wrong

**Departures from the spec.**

- **Criterion 46.** It expects a package below a 3.x root to stop with exit
  7, naming the root and `work.jira`. TCW 4 refuses a related project still
  in 3.x form before reading anything it would inherit (TCW-106 Design
  4.2): exit 1, `<root>: is a TCW 3.x project …; run 'tcw migrate' in it`.
  The monorepo test asserts that, with a comment. The spec's line is wrong,
  not the code.
- **Criterion 64.** Its case "M's own `ov/login` → `auth/login` under
  `moved:`, changed by a rename" cannot happen: TCW 4 refuses to rename an
  override. The `moved:` rewrite is tested on a record that outlived its
  override, and the reader's case without a rename.
- **An emptied override folder.** The spec says an emptied `<alias>/`
  folder is left in place; TCW 4's validate reports it as holding no TCW
  object, so the run removes it.
- **Design 2.11, the second person.** M1 and M4's per-machine paths come
  from the 3.x shared file, which the first person's run converted; they
  cannot be recovered, so only M5's cache clone gets a personal entry, and
  the person writes the others by hand.

**Adaptations, decided by the implementing agent** (each with its reason
in the notes kept for this round; the larger ones):

- C12's fallback name is the one TCW 3 showed (`Customer`, `Z`), not the
  plan's `name: customer`, which would change what TCW 4 shows.
- TCW 3's `Roles` and `When` name capabilities under `roles/` and
  `conditions/`, so F-single holds them as capabilities.
- A `resources` folder directly in an object's folder is its 4.0
  `resources/`; a 3.x object listed there is A2, not converted.
- `--no-jira`'s run, and a run with a blocker, never build a Jira client;
  a run refused locally does not ask Jira at all.
- Each entry of an override's folder is its own move, so that no planned
  move lies inside another, which keeps the executor's re-run check sound.
- An override folder holding another capability is B9; the spec does not
  cover it.
- No hidden folder is converted: TCW 3 listed `.git/…` as terms in a store
  at a clone's root.
- The proof (Steps 14, 25) used clones of `impl-116`, not a merge of
  `main` and `v4`, since the engine is on `impl-116`, and the worktree's own
  install through the wrapper, as the brief requires.
- Step 12's `compare_outcomes.py` does not exist; the proof is the test
  file green before and after, and the full suite.
- The way back's parsing is a library function, so it is tested, rather
  than a snippet in a comment.

**Not done from the plan.**

- Step 24: every F-single test is not repeated over F-full. F-full repeats
  the central ones (dry run, second run, stop at every write, two orders,
  TCW 4 reading the family, the second person); B4, B9, B10, B12, B13 and
  criteria 61, 66 and 68 are tested on small fixtures in the per-step files,
  not on F-full.
- Step 14 and 25's step 1, the live dry run, and Step 25's rehearsal of
  Design 9.3 step 3: see above.
- Step 13's lifecycle `tcw validate` in the worktree and
  `tcw work advance --dry-run`: the brief forbids both; they are the
  dispatching session's.

**Self-review.** The plan was written before TCW-108 to TCW-115 landed,
and many of its line references had moved; the shape of each step held.
What the plan could not know is what TCW 4 would refuse or report once the
migrated files were read by it, which is where every spec departure above
came from. The tests for Steps 15 and 22 were written together with the
code, not before it; their proof is the mutation checks.

## Records changed

- New: `docs/capabilities/cli/migrate-a-tcw-3-x-project-to-tcw-4`
  (`cap-eeaeb9`, Supported, Subject `project` and `migration`).
- Changed: `docs/capabilities/cli/read-a-file-by-the-format-version-it-records`
  names `tcw migrate`.
- New term: `docs/taxonomy/migration`.

All in 3.x form, as this repository's records stay until TCW-118. They
match the item's `capabilities.yaml`.

## Answers to the notes left on the ticket

For the dispatching session to post, one per note.

- **TCW-115 (2026-10-24T15:15:14Z).** Done. A repository-only store or
  project TCW 3 cloned into its per-machine cache gets a personal manifest
  entry pointing at the clone when it is on this machine, with A6 saying it
  is a cache folder; when it is not, A6 says `tcw project provision` will
  fetch it (M5). A second person's run in a project already migrated
  writes the same entry (Design 2.11). The three capabilities' `meta.yaml`
  files are converted with the rest; the proof's run converted every
  capability, 111 ids recorded.
- **TCW-114 (2026-10-24T12:06:09Z).** Done. Phase F rewrites each ticket's
  3.x `TCW Item` (C17), after every local write, through
  `set_item_values`, which checks the old value first; the way back is the
  same call with the pairs swapped. The five capabilities and the
  `owning-project` term are converted with the rest. A 3.x state file
  holds no `parent` or `blocked-by`, so nothing there is converted.
- **TCW-112 (2026-10-24T07:45:02Z).** Done. An override moves to the
  id-path its pointer resolves to (C14); a move onto a taken path, a
  pointer naming nothing or more than one capability, two overrides of one
  capability, and an override folder holding another capability are B9;
  `id: cap-…` goes into the record and out of the state file; an override
  with no documents of its own while its original has some is D3; an own
  object at a path an ancestor has is D2. A hand-written object overriding
  nothing gets C12's name and an empty `description.md`; one with no
  `Status` is left without one, which TCW 3's validate reported too, and
  the run lists TCW 4's finding for it as A12. `MIGRATION_CODE`
  and `MIGRATION_TESTS` are set, with reach tests.
- **TCW-109 (2026-10-24T05:45:16Z).** Done. A credential variable starting
  `TCW_` and holding `__` is A9, in the project's own `work.jira` and in a
  `projects:` entry's dropped `jira` block; a `null` at `work.tags`,
  `work.jira` or below is D5. The new records are converted with the rest.
- **TCW-111 (2026-10-24T05:07:33Z).** Done. `tests/test_ledger_3_0.py`
  reads the records under either name and runs every check on a 4.0 copy
  too; a hand-written `id:` that is not the folder's name is A1;
  `MIGRATION_FOLDERS` holds `tcw/migrate` for both of the sweep's rules.
  The commit hook's rule for nested items is TCW-118's to see at step 4.
- **TCW-108 (2026-10-24T02:16:19Z).** Done. `extends` becomes parent links
  (C8): an extended project already passing the axis needs nothing (E1),
  an upstream gains the axis (E2), a listed child is inverted into a
  parent passing the axis with the child link dropped on both sides (E3,
  D6), anything else becomes a parent (E4), and a loop or a descendant is
  B4 (E5). The 3.x `projects:` reader is copied from tag `v3.0.2` into
  `tcw/migrate/legacy.py`.
- **TCW-110's handoff (2026-10-23T21:41:20Z).** Done, except the last
  point. Absolute and `~` store paths are converted (C5) or B6; names that
  break the identifier rule are B8; 3.x `TCW Item` values are C17 or A10;
  stores that nest or coincide are B7, against related projects' stores
  too. This repository's links and `capabilities.yaml` files are converted
  by the proof's run (214 writes). `RESERVED_PROJECT_IDS` still holding
  `t`, `c` and `w` is not a migration matter and is left as it is; it
  belongs to TCW-118 or a follow-up.

## Notes for the later children (Step 27)

For the dispatching session to post.

- **TCW-117.** The spec's "Handoffs to later items" entry for TCW-117 and
  its "Handoff to TCW-117", as written, plus: the summary's line forms
  (`would write <file>: <codes>`, `move`, `delete`, `edit <key>: C17 TCW
  Item: <old> -> <new>`, the `changed:` counts line, `nothing to migrate`,
  and the `left in another repository:` lines); `--no-jira` is the way to
  keep a run off the live board, never builds a Jira client, and leaves
  the work store out of the check after the run (`tcw validate` checks
  it); a stopped run names its progress record and says `do not save these
  files in version control until 'tcw migrate' finishes`; a stopped run
  re-run while Jira cannot be reached writes nothing more and is finished
  with `--no-jira`. Also: a package below a 3.x root is refused with exit
  1 naming the root (not exit 7), and a second person's run writes their
  personal entry for a TCW 3 cache clone but not M1 or M4's absolute paths.
- **TCW-118.** Design 9.3 steps 0 to 8 and the way back, with the spec's
  "Handoff to TCW-118", and these concrete forms: the proof's commands are
  in this round's Step 14; step 2 saves `tcw migrate --dry-run`'s output
  outside the repository as `tcw116-dry-run.txt`; step 3 also deletes
  `UNMIGRATED_RECORDS` once TCW-117 has landed (not rehearsed here, as
  TCW-117 had not), and runs the suite with the credential variables
  unset; step 6 saves its output as `tcw116-step6.txt`. The way back:
  ```python
  from pathlib import Path
  from tcw.migrate.jira import edited_tickets, restore_tickets, settings
  from tcw.work.jira.client import JiraClient
  root = Path(".")                       # the primary checkout
  done = edited_tickets(Path("tcw116-step6.txt").read_text())
  dry = {k for k, _, _ in edited_tickets(
      Path("tcw116-dry-run.txt").read_text().replace("would edit ", "edit "))}
  print(sorted({k for k, _, _ in done} ^ dry))   # read these first
  restore_tickets(done, JiraClient(settings(root)), root, "tcw")
  ```
  Build the client this way only on the day it is needed.
- **TCW-110, TCW-111, TCW-112 and TCW-114.** The spec's handoff to each is
  answered in the code: each guard's exemption is set, by whole path
  parts, with a test of its reach; `tests/move_stops.py` drives a function
  as well as a command. Nothing more for them to do.
- **TCW-99.** C5 departs from the design in one point, decision 4: a
  store's `repository` declaration stays on the store in 4.0, as the
  request's constraints require; it is not moved into a manifest.

## Added by the dispatching session

Rebased onto `v4` at `f1755e1b` (TCW-113 completed) with no conflicts, then landed
in `v4`. The full suite as CI runs it, `.venv/bin/pytest -q -p
no:cacheprovider` with every `TCW_*` variable unset, run by the dispatching
session on the rebased branch at `6c16a8d2` (2026-10-24) in two halves by
folder: `2246 passed, 2 skipped` and `5474 passed, 111 skipped, 1 failed`. The
one failure, `tests/test_shipped_prompts.py::test_the_wheel_carries_exactly_the_prompts_and_procedures`,
is the worktree's `node_modules` link (`IsADirectoryError` on it); the same
file run in `v4`, where `node_modules` is a real folder, gives `120 passed`.
`pnpm test` `247 passed`; `tsc --noEmit`, `pnpm lint` and `pnpm check:build`
clean.

The live-board dry run (Steps 14 and 25, step 1) is not run here: it runs
the new `tcw migrate` against the real Jira site, so it is left for
TCW-118's gate 2 rehearsal, under the user's go. Decided by the dispatching
session, 2026-10-24.
