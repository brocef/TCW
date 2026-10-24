# Implement round 2 — TCW-116

Answers review round 1 (`review/round-1.md`, rejected), findings 1 to 3 and
"What implement must do" (a) to (d). Built on the branch `v4` in the
worktree `.claude/worktrees/v4`, with that worktree's own virtual
environment (`.venv/bin/pytest`). No lifecycle command was run, no ticket
was moved or written to, nothing was pushed or merged: the dispatching
session makes every move. Jira was only ever the suite's stand-in. The one
hand run went through the guarded wrapper (every `TCW_*` variable unset,
scratch home and cache folders), in a scratch folder, never this
repository. This round gives no verdict.

## The findings and what was done

1. **An absolute path the 3.x shared file held for everyone (M1, M4) was
   moved into one person's untracked file without a word**
   (`tcw/migrate/config.py`, `_plan_entry`). The run now reports each such
   path as a new report, A14, under `needs attention:`, in the same form as
   the other reports (`<code> <where>: <text>`, the `where` being the file
   written, as A6's is):

   ```
   A14 .tcw/tcw-manifest.local.yaml: projects.core.path: /abs/far/core, which
   tcw-config.yaml's projects.upstream.core held for everyone, is now only in
   this file, which is not shared; every other person must add their own
   .tcw/tcw-manifest.local.yaml entry for 'core'
   ```

   It names the entry written, the 3.x file and entry it came from (a
   related project's file, by its path from the project's folder, when the
   entry was found there), and what every other person must do. It is
   given once per entry written, in a dry run too, and a second run gives
   none. A relative path, which stays in the shared manifest, gives none.
   Every 3.x `projects:` entry is read from the shared `tcw-config.yaml`
   (`family.Member.raw`), so every M1 or M4 absolute path is one that was
   shared. By hand, the reviewer's case (app's shared file holding
   `projects: upstream: core: <absolute folder>` and `taxonomy: extends:
   [core]`), rebuilt in a scratch folder: one A14 line naming `core`; a
   second run says `nothing to migrate`.

2. **A ticket whose edit Jira made but whose answer was lost was left out of
   the way back** (`tcw/migrate/jira.py`, `edited_tickets`). A stopped run
   prints each ticket left under `not done:` as `  edit <key>: C17 TCW
   Item: <old> -> <new>` (two spaces, then the same line a made edit gets;
   `cli.phase_f`). `edited_tickets` now reads those lines too, and names
   each ticket once, in the order first named, so the outputs of several
   runs can be joined and read together. A dry run's `would edit` lines are
   still left out, indented or not. Offering a ticket never edited is
   harmless: `set_item_values` edits only a ticket still holding the 4.0
   value, and one already holding the 3.x value counts as done.

3. **`restore_tickets` lost the list of tickets it put back when it left
   one out.** It still raises `set_item_values`'s error then (`BackendError`,
   or `Unreachable` when Jira could not be reached), and the error now
   carries `restored`, the keys put back, beside the `pending` it already
   had, the keys left out. A run with nothing left out returns the keys put
   back, as before.

## Decisions, decided by the implementing agent

- **A new report, A14, rather than widening A6.** A6 is about TCW 3's
  per-machine cache clone (M5); this is a path the 3.x shared file held,
  and what the person must do differs. The spec lists A1 to A13 (Design
  2.9); this adds one, a departure for review to accept. `Report`'s and
  `report.py`'s docstrings now say A1-A14.
- **The 3.x value is not kept in `.tcw/tcw-migration.yaml`.** Keeping it
  would let a second person's run offer it, but the value is the path on
  the first person's machine, which is right on another only by chance;
  the record is read only by `tcw migrate` and its sections are fixed by
  Design 7, so a new section of machine paths is a spec change; and the
  path is still in version control, in the history of the 3.x
  `tcw-config.yaml`. The A14 line tells the first person what each other
  person must write.
- **`edited_tickets` keeps a ticket's first pair** when several runs name
  it. Each run plans from the ticket's value at the time, and a ticket a
  run converted is not planned again, so the pairs agree.

## Corrections to round 1, and to the spec

- `implement/round-1.md`, the departure "Design 2.11, the second person",
  and the note for TCW-117 now say that only M5's cache clone is recovered
  for a second person and that M1 and M4's paths are reported as A14 to
  the first. Round 1 said the person writes those by hand, but its run
  told nobody to.
- `implement/round-1.md`'s way-back snippet for TCW-118 now joins every
  step 6 run's saved output (`tcw116-step6*.txt`), and prints the tickets
  put back and those left out when `restore_tickets` raises.
- **The spec's Design 2.11 promised too much.** It says a second person's
  `tcw migrate` converts "the per-machine paths of C4 (M4, M5)" and writes
  their `.tcw/tcw-manifest.local.yaml`. Only M5's can be: an absolute M1
  or M4 path was in the shared 3.x file, which the first person's run
  converted, so no later run can read it. The spec is not edited at
  implement; this is for review, or a later revision, to record.
- The upcoming changelog entry now describes A14 and the way back's two
  changes; the upcoming release note says what a person who migrates and
  everyone else must do about an absolute path.

## Tests

The tests were written just after the code, not before it; their proof
that they observe the change is the mutation checks below, each of which
undoes one part of the change. In `tests/migrate/test_migrate_manifests.py`:

- `test_m1_an_absolute_locator_goes_to_the_personal_manifest` now asserts
  exactly one A14 line, word for word;
- `test_m1_an_absolute_locator_extended_is_reported_once`, the reviewer's
  case with `taxonomy.extends`;
- `test_m1_the_dry_run_reports_it_too`, and the dry run writes nothing;
- `test_a_relative_locator_is_not_a14`;
- `test_m1_an_absolute_locator_with_a_repository_keeps_m5_s_shared_path`
  and `test_m4_an_absolute_checkout` assert A14; the latter also that a
  second run gives none.

In `tests/migrate/test_migrate_jira.py`:

- `test_the_way_back_offers_a_ticket_whose_answer_was_lost`: the stand-in
  drops the answer to the second edit (`drop_after_next_write` on the
  second PUT); run 1 lists APP-2 under `not done:` and not as made, while
  Jira holds APP-2's 4.0 value; run 2 says `nothing to migrate`; the way
  back over both outputs puts every ticket back as it was.
- `test_a_not_done_ticket_never_edited_is_left_alone`: offering a ticket
  still holding its 3.x value sends no edit.
- `test_edited_tickets_names_each_ticket_once`: an indented and a plain
  line for one ticket give one pair; an indented `would edit` gives none.
- `test_a_way_back_that_leaves_a_ticket_out_names_those_it_put_back`:
  APP-2 edited by hand since the run; the error's `pending` is `["APP-2"]`,
  its `restored` `["APP-1", "APP-3"]`, and APP-1 holds its 3.x value again.

## Mutation checks

Each made in the worktree, run, and undone (the files compared equal to
their copies after):

| Mutation | Result |
| --- | --- |
| A14 never appended | `test_migrate_manifests.py` 5 failed |
| M4's A14 not made (M1's kept) | 1 failed |
| `edited_tickets` reads unindented lines only | `test_migrate_jira.py` 1 failed |
| `edited_tickets` keeps every line, not each ticket once | 1 failed |
| `restore_tickets` sets no `restored` | 1 failed |
| A14 given without the check that the entry is not already planned | all pass |

The last survives because no path in `config.Links.convert` gives one
project two manifest entries (each `projects:` entry is added only when no
entry for that id is there yet). The check is kept so that the report
follows `out.personal.setdefault`, which keeps only the first entry for an
id: a report is never given for an entry that is not written.

## Checks run

- `.venv/bin/pytest -q -p no:cacheprovider tests/migrate`: `321 passed`
  (314 before this round, 7 new). No file under `tests/work/jira/` was
  changed.

## The suite

Not run here, as the brief asks: the dispatching session runs the full
suite as CI runs it.
