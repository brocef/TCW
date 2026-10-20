# Refined outcome

Written by hand, like every other artifact in this item: the `tcw` CLI is the
thing being changed, so the project's guide forbids driving the lifecycle with
it here. No stage gate or hook ran; what they would have checked is below.

## The sixteen acceptance criteria

`live` means run against a real Jira project (`proposit.atlassian.net`) with
throwaway items the user approved. `test` means the suite. Several are both, and
where they are, the live run is the one that settles it — the whole feature
exists because of a behaviour no stub can produce.

| # | Criterion | Evidence |
| - | --------- | -------- |
| 1 | creates, binds, board shows the key | **live** TCW-63, bound, `ticket: TCW-63` on the board |
| 2 | created ticket is not in the inbox query | **live** — Jira made TCW-63 in `Triage`, creation moved it to `To Do`, the issue changelog records the hop, and the configured inbox query afterwards returned only the pre-existing TCW-1 |
| 3 | no `statuses.backlog` ⇒ refuses, creates nothing | **live** — refused by name, and a Jira search for the refused summary returned **0 issues** |
| 4 | `validate` accepts `backlog`, still refuses an unknown key | test |
| 5 | running it twice creates one ticket | test |
| 6 | an interrupted run resumes by binding | test, plus the `created` record read back from disk |
| 7 | `--dry-run` creates nothing | **live** (no tracker calls) and test |
| 8 | `--all` sweeps unbound, skips bound | **live** — four tickets, distinct keys, epic first and Epic-typed; and separately an item whose binding had been unlinked, which the first implementation silently skipped |
| 9 | creation-on-filing off ⇒ no tracker call at all | test, with the credential variables removed so a call would fail loudly |
| 10 | on ⇒ filing produces a bound ticket obeying 2 and 3 | **live** TCW-63 was filed this way |
| 11 | tracker unreachable ⇒ item filed, ticket owed, `tracker create` settles it | **live** both halves |
| 12 | `inbox accept` of a raw entry ⇒ bound item; a ticket key still goes through `import` | test |
| 13 | `--epic` ⇒ bound Epic-typed ticket | test; **live** for the Epic type through the sweep |
| 14 | `strict` + creation-on-filing validates; epic filed, task refused | test |
| 15 | `strict` alone keeps today's message | test, asserted as the criterion words it — the *absence* of any wording this item added |
| 16 | `pytest` and `tcw validate` | `3888 passed`, `pytest_exit=0`, `validate OK`, `validate_exit=0`, at `f8eefa2a`, clean tree, commit read before and after |

Criterion 11 said `tcw work tracker sync` settles an owed ticket. It never could,
and correcting Rule 6 during implementation did not correct the criterion that
repeated it — found here, reading the criteria rather than recalling them, and
corrected in `spec.md`.

## Beyond the criteria: what the reviews changed

Four review rounds found twenty-five defects between them. The criteria above
would have passed before any of them: none of the crashes, the sweep filter, the
blank web page or the silent data loss is expressed as an acceptance criterion,
because each lives in an interaction the spec did not think to name. That is the
finding worth carrying out of this item, and it is recorded in `outcome.md`
rather than repeated here.

Verified live against the fixed code, not only in tests:

- `tcw work start` on an item that owes a ticket, and on a **different, bound**
  item while an owed one sits on the board — the two `KeyError`s that would have
  shipped.
- `tcw work drop` refusing an item that holds a created key, in a **non-strict**
  project: `drop_exit=1`, item still present, both remedies named.
- The board rendering the new state: `ticket: TCW-63 made, not bound`.
- `tcw work tracker sync` on an owed item naming `tracker create`.
- The owed reason bounded to one line of 200 characters, where it had been the
  raw Jira response body written verbatim into a committed file.
- `work.tracker.link` reaching the created ticket's description.

One method note, because it has bitten this item twice: an exit code read
through a pipeline is the pipeline's, not the command's. The first reading of
the drop refusal said `exit=0`; measured without a pipe it is 1.

## Deferred, with reasons

- **GitHub #43 is not closed.** The project's rule is that an issue closes after
  publication, not at completion: an issue closed before the fix ships tells the
  reporter it is fixed when they still cannot install it. Nothing is posted to
  it without the exact text being approved first.
- **Nothing is published or pushed.** The user asked for a local merge only.

## Follow-ups

**Taken here, at the user's direction:** `.github/workflows/test.yml` now has a
`web-build` job running `pnpm check:build`. The check existed the whole time and
nothing ran it — the workflow installed no Node and no test shells out to it —
which is how a fixed page kept rendering blank for four commits. It is a CI
change rather than a change to this feature, and it is here because the failure
it catches is the one this item produced.

That job is not covered by the suite; nothing in `tests/` reads a workflow file,
so the gate above is unaffected by it. It is verified by `pnpm check:build`
exiting 0 locally and by the YAML parsing into two jobs.

**Filed as its own item:** `created_record` in `tcw/tracker/intake.py` duplicates
`_created_key` in `tcw/store/base.py` — two definitions of a valid `created`
record, one over raw text and one over parsed data. They agree today. If either
loosens, the resume path and the board row begin disagreeing about the same
file.

## Held at verify

Not completed, and deliberately. The work skill's instruction is to stop here
and hold until closeout is explicitly approved: the merge route, the
documentation updates and any follow-up items are confirmed with the user before
`complete` runs.
