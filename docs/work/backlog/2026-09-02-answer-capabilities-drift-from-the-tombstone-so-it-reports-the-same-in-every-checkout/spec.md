# Spec — Answer capabilities drift from the tombstone so it reports the same in every checkout

## Capability changes

Planned ledger deltas. No records are written at this stage.

| Capability | id | Delta |
| --- | --- | --- |
| `capabilities/detect-capability-drift` | cap-c38e6d | **Amend.** Drift is reported the same way in every checkout, not only on the machine that completed the work. Add the reproducibility promise and the limit on it: a shipped item is recognized from the record its resolution left behind, and where no resolution was recorded the command stays silent rather than guessing. Status stays **Supported**. |

No new capability and no status flips. The command already promises to report
drift; this makes it keep that promise everywhere.

## Problem

`_drift` (`tcw/capabilities/cli.py:195-213`) decides whether a `Missing`
capability's work has shipped by asking the work store for the item:

```python
item = work.get(str(slug))
...
if item is not None and item.status == "completed":
    out.append((c.path, str(slug)))
```

`completed/` and `discarded/` are gitignored by default
(`resolved_ignore_rules`, `tcw/store/fs.py:698-706`), and completing an item
*moves* its folder there rather than deleting it. So the folder exists on the
machine that ran the transition and reaches no other clone. `work.get()` answers
there and returns `None` everywhere else, and the `item.status == "completed"`
branch never fires.

The result: **`tcw capabilities drift` reports drift for whoever completed the
work and reports nothing for everybody else, at the same commit.** It fails in
the quiet direction — a capability left `Missing` after its work shipped is
invisible in CI and in every colleague's clone, and the command still exits 0,
which reads as "no drift" rather than "could not tell".

This is the same defect the tombstone item removed for references between items,
pointing at a different reader. That item's spec recorded a repo-wide sweep for
this exact pattern and listed two negative results; it did not find this one.

### Sweep

Repo-wide, as the request asks, and grounded rather than recalled. The pattern
searched for: **a decision about finished work whose answer changes depending on
whether the resolved folder happens to be present.**

Two searches over `tcw/`: every `get()` on a work store outside the store module,
and every comparison against `completed` / `discarded` / `RESOLVED_STATUSES`.
What they turned up:

| Site | Affected? | Why |
| --- | --- | --- |
| `capabilities/cli.py:203-211` `_drift` | **Yes** — the reported defect | Decides "did it ship?" from `get()` |
| `store/base.py:2141-2150` `epic_completable` | **Yes — a second confirmed instance** | See below |
| `store/base.py:2281-2288` the `complete` epic gate | No | It filters children *out* when resolved; an invisible child and an excluded child produce the same list |
| `store/base.py:2191` `unresolved_blockers` | Out of scope, by prior decision | Already fails open, and making it precise changes when transitions refuse |
| `work/cli.py:322` `list` filtering | No | Excludes resolved statuses anyway, so it prints the same either way |
| `work/recursion.py:133,136` | No | Operates on items already in hand, not on a store lookup |
| `serve/__init__.py` (7 `work.get` calls) | No | A local viewer showing local state; a resolved item has nothing to open, and references to one are already handled by `resolve_tcw_ref` |
| `store/fs.py:4488-4500` `_status_resolution_problems` | Not fixable | `check()` reports a status/resolution disagreement *inside* an item's own file. An absent file cannot be checked, and the tombstone does not carry enough to substitute |

#### The second instance: `epic_completable`

`epic_completable` (`tcw/store/base.py:2141-2150`) calls `initiative_children`,
which filters `query()` — so a resolved child is simply absent from the list in
any clone that never received its folder. An epic whose children have **all**
been resolved therefore has zero visible children, and the `bool(children)`
guard ("an empty epic is not completable") makes it report **not completable**.

Measured, not reasoned — same node, before and after removing the child's
`completed/` folder:

```
HERE  (completed/ present):    children: ['…-a-child']   epic_completable: True
CLONE (completed/ absent):     children: []              epic_completable: False
```

That is worse than the drift defect, because it does not merely under-report —
it **blocks an operation**. `epic_completable` gates the backlog→completed
bypass at `base.py:2271`, so an epic that legitimately can close refuses to in
every checkout but one, with `cannot complete from backlog as 'done'`. It also
drives the `| ready-to-close` hint in `tcw work list` (`work/cli.py:350`) and
`reconcile`'s auto-completion (`work/recursion.py:210`).

**The tombstone as it exists cannot fix it.** The record carries `slug`,
`resolution` and `resolved` — and nothing about which epic a child belonged to.
Confirmed in the same run: the child's tombstone survives into the clone, and
says nothing that would let `initiative_children` reconstruct it. Answering this
one needs the record to carry the `initiative`, which changes what a tombstone
*is*, and that is a different request from the one filed here. Out of scope, and
filed as its own item.

## Goals

1. `tcw capabilities drift` reports the same capabilities in every checkout of a
   project at the same commit.
2. A capability whose work was **discarded** is still not reported, preserving
   the distinction the command makes deliberately today.
3. Where the record cannot settle whether the work shipped, the command reports
   nothing rather than guessing.
4. The sweep the request asked for is on the record, including the instance this
   item does not fix and why.

## Non-goals

- **Making `epic_completable` reproducible.** Confirmed above, not fixable with
  the current record, and it changes what a tombstone carries. Its own item.
- **`unresolved_blockers`.** Non-goaled once already, for the same reason:
  acting on the new distinction changes when transitions refuse.
- **Backfilling resolutions into an existing graveyard.** Goal 3 accepts that an
  unrecorded resolution is silent; it does not ask for a pass that fills them in.
- **Making `tcw validate` or `check()` read the index rather than the working
  tree.** A separate and much larger question, and not what under-reports here.
- **Any change to what `.gitignore` keeps.** The repo manager's call, as before.

## Design

`_shipped_but_missing` asks one question — *did the work behind this capability
ship?* — and today answers it from a source that is not present everywhere. The
tombstone is the same answer from a source that is.

Where `get()` returns an item, nothing changes: a live item is authoritative and
its status is the answer. Where `get()` returns `None`, consult the tombstone.
`resolution_status` (`tcw/store/base.py`) already maps a resolution onto the
status it closes into — `done → completed`, everything else → `discarded` — so
the shipped test stays a single comparison and the completed/discarded
distinction is preserved by the same function `complete()` uses. No second
mapping to drift out of step.

A tombstone with **no** recorded resolution answers nothing and the capability is
not reported. That is the requester's decision, taken with the trade-off stated:
a project that backfilled without resolutions gets no drift detection for those
items, which is preferred to ever reporting abandoned work as shipped.

Litmus test — *could a non-filesystem store implement this?* Yes, and it already
must: `tombstone()` is an abstract `WorkStore` method, and an adapter whose
resolved items stay retrievable answers it from those directly. This adds no
interface method and mentions no file, path or commit.

Nothing about the change is harness-specific: it is CLI behaviour, identical
under Claude and Codex.

## Acceptance criteria

Criteria 1 and 2 have been run against the tree as it stands and **fail** today
in the way each describes; that is the point.

1. In a project where a capability is `Missing` and its `Planning doc` names an
   item completed and then removed from the working tree, `tcw capabilities
   drift` reports that capability and exits non-zero. Today it reports nothing
   and exits 0.
2. `tcw capabilities drift` gives the same output and the same exit code on the
   machine that completed the item and in a fresh clone at the same commit.
3. A capability whose `Planning doc` names an item that was **discarded** —
   resolution `wontfix`, `duplicate` or `superseded` — is **not** reported,
   whether the folder is present or absent.
4. A capability whose `Planning doc` names an item with a tombstone carrying **no
   resolution** is **not** reported.
5. A capability whose `Planning doc` names a slug that never existed is not
   reported, and the command does not error.
6. A live item in `backlog`, `active` or `review` is still not reported.
7. The unreviewed-inherited half of the command's output is unchanged.
8. The full suite passes.

## Risks

- **Silence on backfilled records is a real loss, not a theoretical one.** Any
  project adopting tombstones by backfilling without resolutions gets no drift
  detection for those items. Accepted deliberately (Goal 3), and worth one
  sentence in the release note so nobody reads the silence as a clean bill.
- **`epic_completable` stays broken after this ships**, and it is the more
  damaging of the two because it blocks a completion rather than under-reporting.
  Filing it is not fixing it; the release note should not imply the class is
  closed.
- **The sweep may still be incomplete.** Two previous sweeps for this pattern
  were recorded as complete and were not. This one is grounded in two mechanical
  searches with every hit adjudicated in the table above, which is stronger than
  its predecessors — but the honest claim is "every site those two searches
  reach", not "every site".
- **A capability could point at a slug that a *different* project resolved.**
  The lookup already resolves through the configured work store, so the tombstone
  read inherits whatever store `work.path` names. No new exposure, but the
  existing behaviour is now reachable through a second path.

## Notes

- The `epic_completable` finding is the most valuable thing the sweep produced
  and was not in the request. It is recorded here in full rather than only in the
  follow-up item, because the next person to read this spec should be able to see
  what "the sweep" actually covered without opening another document.
- Requester was asked for reference material; none provided.
