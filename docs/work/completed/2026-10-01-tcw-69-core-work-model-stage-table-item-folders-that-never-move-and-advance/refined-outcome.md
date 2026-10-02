# Refined outcome — Core work model: stage table, item folders that never move, and advance

## Decision

**Accepted**, on 2026-10-02, by adversarial review. On 2026-10-02 the owner
ruled that, for the TCW 3.0 epic, a child item is approved when it passes
adversarial review, and that the owner reviews nothing until the epic is
finished. The review was bounded in advance: one review round, one fix round,
one confirming round. Findings were sorted into "belongs to this change" and
"needs a separate change", and the item would have been held, not looped, had
the confirming round said NOT DONE.

## Evidence

- **Round 1** (`adversarial-code-reviewer` over `f2ce55ff..94fef974`):
  NOT DONE. It found five defects that belong to this change, each reproduced
  with a script, and checked every one against the code before fixing it:
  - B1: `advance` ignored the project part of the slug, so a slug naming
    another project moved this project's item with the same folder name.
  - B2: an infinite `work.hooks.timeout` passed validation and then crashed
    every hook run.
  - B3: `Slug.parse` accepted a trailing newline (`$` matches before one).
  - B4: drift dropped the `Missing` check when the newest declarations were
    `new` and `changed`, and called one item "items created the same day".
  - B5: two tests pinned less than they claimed (the external completion gate
    still checking review; the stale hint naming the right stage).

  It also listed five findings for separate changes; S1 (a `Layout` built
  apart from the backend could refuse every Jira-mode completion) was folded
  in here as a one-line consistency check in `advance`.
- **Fixes:** `6751205f`, each with a test written first and seen to fail.
- **Round 2** (confirming, over `94fef974..6751205f` only): DONE. It noted
  that `math.isfinite` overflows on a whole number of 309 or more digits,
  breaking `parse_work_config`'s "never raises". That was folded in as
  `ed44523e`, test first, without a further round.
- **Tests run now:** `pytest tests/work -q` → 274 passed. After Task 7 the
  four 2.x suites that reach the moved routing function passed (331 with
  `tests/work`). `tcw validate` on the branch: OK.
- **Merged:** `epic/tcw-3.0` fast-forwarded to `ed44523e`.

## Definition of Done

- **Tests pass:** the targeted suites, yes. **The full suite (AC 20) is
  deferred** to the end of the epic by the owner's instruction of 2026-10-02;
  a run after Task 7 was stopped at about 61% with no failures. AC 20 stays
  open until then.
- **Docs synced:** the developer changelog entry is the only entry that fires
  (`docs/changelogs/upcoming/2026-10-01-tcw-69-….md`); nothing user-facing
  changed.
- **Capabilities reconciled:** no capability changes in this slice (spec,
  "Capability changes").
- **Reviewed:** as above.
- **GitHub issue:** none; the item came from Jira (TCW-69).

## Deferred to other items

- **TCW-70 and TCW-71:** a stage name a backend reads that is not in the table
  (for example a hand-edited `stage: reveiw`) makes `advance` and
  `Query.matches` raise `UsageError` (exit 2), blaming the user. Each backend
  should validate the stage on read and report `None` or raise `BackendError`.
  TCW-70's contract test must also settle `create(..., request="")`: the
  filesystem backend answers `None` from `read_request`, the memory backend
  `""`. Build each `Layout` from `config.enabled` and
  `backend.external_stages`; `advance` now refuses otherwise.
- **TCW-73:** under `force`, `advance` returns overridden gate failures in
  `Outcome.overridden` and the trace note but does not print them; spec 6.5
  says each is reported on stderr. The command layer prints them.
- **TCW-72:** `origins` labels a whole binding list by its key path; a list
  merged from several layers needs a label per entry.
- **End of the epic:** the full suite (AC 20).

## Closeout choices

- **Merge route:** into `epic/tcw-3.0`, not `main`, as the owner chose for the
  whole epic. `main` receives 3.0 when the epic finishes.
- **Completion:** `tcw work complete` run from the primary checkout on `main`,
  whose `tcw` is the unmodified released code (all code changes are on the
  worktree branch). The plan had expected a hand completion; it was not
  needed, because the CLI being driven is not the code under change. Running
  it also syncs the Jira ticket and keeps the graveyard record that TCW-70's
  `blocked-by` relies on.
