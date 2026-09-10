# Refined outcome: resolve a work store inside a project the registry already located

## Decision

**Accepted.** The user reviewed the assessment and directed that the work be
merged into `main` locally.

## Evidence

Every claim below came from a command run during verification, not from reading
the diff.

**The reported case.** The workspace from issue #31 rebuilt by hand — three
repositories cloned flat, the nested-layout config untouched, `TCW_PROJECT_*`
set:

```
$ tcw work path
…/orchestration/docs/proposit-core/work

$ tcw provision
  work: already available at …/orchestration/docs/proposit-core/work
  proposit-app: already available
```

Both lines agree. In the reporter's paste they contradicted each other, one
project reported already available while the line above cloned the same
repository. The cache directory stayed empty throughout.

**Nothing publishes.** With the orchestration checkout on
`feature/working-branch` while the declaration named `main`, a real
`tcw work start` committed the transition on that branch and pushed nothing. The
store reported `declaration: None` and `publishes: False`.

**Suite.** `2526 passed in 594.53s`, run after the last code change. The real
`~/.cache/tcw/stores` was confirmed empty afterwards.

## Capability ledger reconciled

The three capabilities in `capabilities.yaml` were amended and none flipped
status. `tcw capabilities check` reports `capabilities OK` and
`tcw validate --no-recurse` reports `validate OK`. Nothing was left `Omitted`.

`cli/validate-a-node` was a **correction**, not an extension: it already claimed
validation tells a store's three failure modes apart in different words, and did
not when a broken path and an unprovisioned declaration were both present. The
ledger now matches behaviour.

## Deferred, deliberately

**The originating GitHub issue stays open.** `docs/work/dod.yaml` lists
_"originating GitHub issue answered and closed, if the item came from one"_, and
issue #31 is not closed here. This project's guide sequences that after
publication: an issue closed before the fix ships tells the reporter it is fixed
while they still cannot install it. The order is complete every item → cut the
version → push → then answer and close. The acknowledgement comment already
posted on #31 says the issue stays open until the change ships in a released
version, so the reporter has not been left silent.

**No version was cut.** The change set is on a local branch and the user chose
to merge without cutting; the release-note and changelog entries are written into
the `upcoming.md` working files and rotate with whatever bump comes next.

## Found during verification, outside this item's scope

Two things, both acted on rather than filed away.

**My own test wrote to the real cache directory.** The `XDG_CACHE_HOME` guard
existed only inside `tests/test_store_provisioning.py`, and a test added to
`tests/test_validate.py` left four working copies in `~/.cache/tcw/stores`.
Moved to `tests/conftest.py` as suite-wide (`a6f9074`), which is the argument
the guards beside it already make. Stray directories deleted, real cache
confirmed clean after a full run.

**A fifth instance of the store-root/node-root hazard, fixed at the user's
request** (`78df20d`). `tcw work tags add` staged the node's `tcw-config.yaml`
using the *store's* git repository, so `git add` refused the path and the verb
was unusable on any node with an external `work.path` — the orchestrator layout
this project documents as intended. Reproduced with a bare `work.path` and no
declaration at all, so no part of this item's change is involved.

It is the mirror image of closed issue #16: that ran git in the code repository
against a store file, this ran git in the store repository against a code file.
Issues #15 through #18 were four instances of this family and are all closed;
this is a fifth. **No open GitHub issue covers it** — all six were scanned — so
it is fixed here without an issue to answer, and it is worth someone deciding
whether the family deserves a sweep rather than a fifth patch.

## Notes

- The plan was wrong about the `Skill-Driven-Component` trigger and about the
  message naming the configured path; both are recorded in `outcome.md` with
  what was done instead.
- No post-mortem was offered or run. The problems verification surfaced were
  ordinary and were fixed in place; none of them indicates a lifecycle stage
  that should have caught something earlier.
