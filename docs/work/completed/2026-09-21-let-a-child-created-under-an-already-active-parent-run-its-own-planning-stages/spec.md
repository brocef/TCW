# Spec — Let a child created under an already-active parent run its own planning stages

## Capability changes

**Changed.** One existing record:

- `work/decompose-a-work-item-into-children` (`cap-33852a`) — its description says
  children "travel with" the parent: _"A child shares its parent's status by living
  inside it; starting or completing the parent carries its children along, and
  transitioning a child on its own promotes it to a top-level item."_ None of that
  is true for children created after this change. The new description says a
  child has its own status, starts in `backlog`, keeps its parent through every
  transition, and that a parent cannot be completed, discarded or dropped while
  anything beneath it is still open.

**New.** None. **Removed.** None — decomposition stays; what changes is how a
child's status behaves.

No taxonomy entry changes: no Vocabulary term describes nesting or a work item's
status (`work-item` is "a unit of change … that moves through a status state
machine", which still holds).

No records are written at this stage; the ledger is reconciled at completion.

## Problem

A child created with `tcw work new "<title>" --parent <slug>` has no status of its
own. The filesystem store takes an item's status from the top-level folder it sits
under, and puts a child inside its parent's folder:

- `tcw/store/fs.py:4110-4113` — `_status_of` returns
  `d.relative_to(self.root).parts[0]`, "so a nested child reports its top-level
  status folder".
- `tcw/store/fs.py:6444-6447` — `create_work` puts a child at `parent_dir / slug`.
- `tcw/store/fs.py:4115-4124` — `_parent_slug` derives the parent purely from that
  nesting.

So a child created under an `active` parent is born `active`. The stage gates key on
status (`tcw/work/cli.py:1922-1926`; the same check guards `tcw work scaffold` at
`tcw/work/cli.py:1977-1980`), so `request`, `spec` and `plan` refuse it and only
`implement` passes.

The lifecycle's own order guarantees this. The plan stage prompt says "Commit
`plan.md` on its own, before `tcw work start`" (`tcw/work/prompts/plan.md:33`), and
the children are listed in the parent's plan, so the parent is active by the time
they are created. The decompose procedure promises the opposite
(`tcw/work/procedures/decompose.md:12-15`): "Each child gets its own
`initial-request.md`/`spec.md`/`plan.md` as it's planned — the parent stays a thin
umbrella."

Reproduced on this checkout's CLI in a scratch repository
(`/private/tmp/claude-501/nestrepro`):

1. `tcw work new "Parent thing"`, `tcw work start <parent> --owner me`.
2. `tcw work new "Child thing" --parent <parent>` prints "created at
   docs/work/active/<parent>/<child>" and "next: when you begin implementing, run
   `tcw work start <child>`" (`tcw/work/cli.py:544`).
3. `tcw work stage gate spec <child>` → "'spec' is not legal for an item in
   'active'; it runs in backlog".
4. The suggested `tcw work start <child> --owner me` → "already claimed by an
   unknown owner since an unknown time" — the child is active with no claim.
5. `tcw work submit <child>` moves it to `docs/work/review/<child>`, and `tcw work
   show` no longer lists a parent: a child's own transition targets the top-level
   status folder (`tcw/store/fs.py:6225`), and the relation ended with the nesting.
   `tests/test_work.py:1575-1585` pins that as intended.
6. Completing the parent carries a second nested child into `completed/`, and `tcw
   validate` then reports "`<child>`: status 'completed' with missing or invalid
   resolution None".

The requester chose on 2026-09-21 (`initial-request.md`): **children get their own
status.** A child starts in `backlog` and moves through the lifecycle on its own.

## Goals

1. A child created with `--parent` starts in `backlog`, whatever its parent's
   status — including a parent in `backlog` — so its `request`, `spec` and `plan`
   stages are legal.
2. A child keeps its own status when its parent moves, and keeps its parent through
   every one of its own transitions.
3. Nothing open is left beneath a resolved item: an item cannot reach `completed` or
   `discarded`, or be dropped, while any descendant with its own status is open.
   `--force` does not change that.
4. Boards written by earlier versions read as they do today: a child that was
   created nested keeps following its parent's status.
5. The relation and the rule belong to the abstract model; how the filesystem holds
   them is private to the filesystem adapter.

## Non-goals

- **Letting `spec` or `plan` run on an `active` item, or a way back to `backlog`.**
  That is the "Recovery" question of
  `2026-09-16-stop-an-item-reaching-implement-without-a-spec-and-plan-and-say-how-to-plan-an-item-started-too-early`,
  which covers items started by hand before planning. This item removes the one way
  an item was _born_ active. Neither item fixes or blocks the other.
- **Rewriting existing boards.** Nothing converts a nested child on disk. The four
  nested children on the proposit-app board
  (`docs/proposit-app-repo/work/active/2026-09-15-share-the-argument-action-menus-…/`)
  keep following their parent.
- **A gate that stops a child starting before its parent is active.** Settled: no
  such gate (initiative children have one, `tcw/store/base.py:3735-3745`; `--parent`
  children do not get one).
- **A CLI verb to re-parent.** `tcw work edit` has no `--parent`
  (`tcw/work/cli.py:4291`); re-parenting stays a web-app and store operation.
- **A cross-node parent.** `parent:` names a slug in the same store, as today.
  Crossing nodes stays the job of `--initiative`.
- **Strict tracker mode refusing child creation** — tracked by
  `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`.

## Design

### The model (store-independent)

Every work item has its own status. `parent` is a relation between two items and
says nothing about either one's status — how a tracker already behaves (a Jira
sub-task has its own workflow status and a parent link). The abstraction test —
_could a non-filesystem store implement this?_ — is answered yes.

Rules in the core (`tcw/store/base.py`), so every adapter enforces them alike:

1. **Creating a child creates it in `backlog`.** The abstract `create` docstring
   (`tcw/store/base.py:3033-3034`) already calls parent "an abstract node relation;
   the adapter realizes the nesting"; this pins down that the relation never sets a
   status.
2. **The parent must be live.** `create` with a parent, and re-parenting an open
   item, are refused when the named parent — or any ancestor above it — is
   `completed` or `discarded`. Today `create_work` checks only that the parent
   exists (`tcw/store/fs.py:6420-6425`). Re-parenting also refuses a cycle (the new
   parent is the item or one of its descendants), walking the relation rather than
   folder ancestry.
3. **Nothing open beneath a resolved item.** `complete` (to either resolved status)
   is refused while any **descendant** of the item — the whole subtree, not just
   direct children — is open and has its own status. The refusal names each one and
   says to complete or discard it first. It sits **outside** the `if not force:`
   block (`tcw/store/base.py:3804`), so `complete --force` does not bypass it; its
   shape (query, filter unresolved, name them) follows the initiative-children check
   at `tcw/store/base.py:3808-3815`, and its children query is built the way
   `initiative_children` is (`tcw/store/base.py:3545-3551`: `query()` filtered on a
   relation field), as a `parent` counterpart the plan names.
4. **Drop** (`tcw/store/base.py:3861`) is refused while the item has any
   descendant with its own status, open or resolved — a dropped item leaves no
   tombstone, so any child pointing at it would be left with a parent that never
   existed. Legacy nested children are still deleted with the folder, as today
   (`tests/test_work.py:1588-1594`).
5. **Epics agree with themselves.** `epic_completable` (`tcw/store/base.py:3638-3649`)
   and `epic_children_all_resolved` look only at initiative children, so an epic
   with an open `--parent` child would show "Ready to close" and then fail the
   auto-completion that `reconcile --complete-when-ready` performs
   (`tcw/work/recursion.py:221-228`) under rule 3. Readiness also requires rule 3 to
   pass, so readiness and completion give one answer.

"Has its own status" is where the one filesystem-only exception enters: a legacy
nested child (below) moves with its parent by construction, so it is never left
behind and does not itself block — but rule 3 still walks through it to the
descendants beneath it, so a legacy child cannot hide an open grandchild. The core
asks the adapter which descendants are open with their own status; the default
answer is every open descendant, and only the filesystem adapter narrows it.

### The filesystem realization (adapter-private)

**A new child is an ordinary top-level item that records its parent.**

```
docs/work/active/<parent>/state.yaml
docs/work/backlog/<child>/state.yaml        # contains  parent: <parent>
```

- **Creation.** `create_work` (`tcw/store/fs.py:6444-6447`) writes
  `backlog/<slug>/` and a `parent: <slug>` key in `state.yaml`, whatever the
  parent's status. The precedent is `initiative:`, the relation pointer `accept`
  already writes into a new item's `state.yaml` (`tcw/store/fs.py:6108-6111`).
- **Reading the parent.** `_parent_slug` reads the `parent:` field first and falls
  back to folder nesting only when the field is absent. `_status_of` does not
  change.
- **Legacy child.** An item nested inside its parent's folder with no `parent:`
  field — every child any earlier version created — reads exactly as today: its
  status is its top-level folder, and it moves with its parent. When such a child
  transitions on its own, the move takes it to the top-level folder of its new
  status as today, and **writes `parent:` in the same move** (the claim's
  `state.yaml` edit in `start`, `tcw/store/fs.py:4049-4052`, and the fields a
  transition already writes, `:6226-6241`), so it keeps its parent and from then on
  has its own status. When its parent resolves, a legacy child is carried with it
  and carries the parent's resolution: the resolution check reads it as such
  rather than as corrupt (Problem, step 6).
- **Re-parenting.** `update_work` (`tcw/store/fs.py:6560-6578`) becomes a field write
  with the rule-2 checks, not a folder move: setting a parent writes `parent:`,
  clearing it removes the key. Status never changes. The web app reaches this
  through the work PATCH route's field allowlist (`tcw/serve/__init__.py:1161-1164`,
  which already admits `parent`). A legacy nested child re-parented this way is
  first moved to its top-level status folder, then given the field.
- **Code paths that then need no change for new children**, because a new child
  sits where any top-level item sits: transitions (`tcw/store/fs.py:6219-6225`), the
  claim and its take-over (`:3960-3962`, `:4044-4053`), status-path references
  (`:433-438`), deletion and tombstone lookups under `work.retain: false`
  (`_commit_holds` `:4974-4992`, `_committed_item_path` `:5036-5055`), the retention
  probes (`:4625`, `:4662`), the resolved-work `.gitignore` rules, and the
  `start --worktree` commit paths (`tcw/work/cli.py:1287`). Listing, the projection
  (`tcw/work/projection.py:192,209`) and the web tree
  (`web/client/src/model/tree.ts:76-98`) already nest by the `parent` field.

**Places that still need work:**

- **The claim window.** `start` moves the item into the adapter's private
  `.claiming/` folder before publishing it to `active/`
  (`tcw/store/fs.py:4046-4055`), and `_item_dirs` does not look there, so for that
  moment the child is invisible to any children query. Rule 3 in the filesystem
  adapter must count an in-flight claim whose `state.yaml` names the item (or a
  descendant) as open, rather than read that moment as "no open children". Take-over
  of an interrupted claim needs nothing new for a new child — `parent:` is inside
  the `state.yaml` that moves with it — but must write `parent:` for a legacy child
  being claimed, as the main claim path does.
- **Worktree completion.** `tcw work complete` merges a worktree branch before the
  store's `complete` runs (`tcw/work/cli.py:3641-3642`). The rule-3 check has to run
  before that merge, as the strict-tracker refusal already does at `:3638-3640`, so a
  refusal never follows an integration. `start --worktree` of a legacy child has to
  commit its nested source path, not `backlog/<slug>` (`tcw/work/cli.py:1287`).
- **Legacy children on deletion.** `delete_resolved` (`tcw/store/fs.py:5131`)
  removes a whole folder but records a tombstone only for the addressed item. A
  resolved parent's folder can hold legacy children; each one removed must get a
  tombstone and recorded commit too, so it stays answerable by `tombstone` and by
  status-path references.
- **`tcw validate`** reports a `parent:` field that names neither a live item nor a
  tombstone in this store (a dangling pointer), and a `parent:` field on a nested
  item that disagrees with the folder it sits in.

### Rejected alternative: status folders inside the parent's folder

The first draft of this spec kept children nested and gave each one a status folder
inside its parent's (`active/<parent>/backlog/<child>/`). It preserved "status is
where it lives" and atomic renames, and old boards would read unchanged. It was
rejected because every piece of code that builds a path from a status — the claim
and take-over, status-path references, deletion and tombstone lookups, retention
probes, the `.gitignore` rules, worktree commit paths — would have had to learn
about parent folders, and each one missed would silently lose the relation or
refuse a legitimate operation. A `parent:` field puts a new child where every one of
those paths already works, so the fewest code paths change.

A `status:` field in a nested child's `state.yaml` was also rejected: it would be a
second source of truth beside the folder, and it would turn the claim — which is
safe because it is one atomic rename — into a field write. A `parent:` field has
neither problem, because the parent relation was never what the folder encoded
atomically.

### Instructions and documentation

Rewritten to the new behavior:

- `tcw/work/procedures/decompose.md` and
  `skills/work/references/procedures/decompose.md`. The "Which path?" section chose
  `--parent` for "pieces worked together and transitioned as a unit", which no
  longer describes it. The rewrite states what still separates the two relations:
  `--parent` is local to one store, needs no epic, has no start gate, and blocks its
  parent's completion; `--initiative` points at a `type: epic`, crosses nodes, gates
  a slice's `start` on the epic being active, and is followed by `reconcile`. It
  also says children may be created before or after the parent's `start`, and each
  is started on its own.
- `docs/guide/work.md:482-487`, the capability description, the `FsWorkStore`
  docstring (`tcw/store/fs.py:3768-3774`, "a child item is a folder nested inside its
  parent's"), and `docs/lifecycle/abstraction.md:28`, which says "the FS adapter
  derives it from nesting" — now it records it, and derives it only for legacy
  children.
- `tests/cli/scenarios/10-cross-node-epics-and-nesting.md` row 4 asserts an epic
  "whose only open child was created with `--parent` completes anyway, exit 0";
  that half inverts under rules 3 and 5.

## Acceptance criteria

"Child" means one created after this change; checks run against the filesystem
store in a fresh node unless stated.

**Creation and status**

1. With a parent in `active`, `tcw work new "C" --parent <parent>` creates the
   child at `docs/work/backlog/<child>/` with `parent: <parent>` in its
   `state.yaml`; `tcw work show <child>` reports `status: backlog` and
   `parent: <parent>`; `tcw work stage gate request|spec|plan <child>` each exit 0
   given the artifacts each gate requires.
2. The same holds with the parent in `backlog` and in `review`.
3. `tcw work new "C" --parent <p>` is refused, and nothing is written, when `<p>`
   is `completed` or `discarded`.
4. `tcw work start <child> --owner x` succeeds; then `submit`, `rework` and
   `complete --resolution done` each succeed, and after every one `tcw work show
   <child>` still reports `parent: <parent>`.
5. Starting a backlog parent that has a backlog child leaves the child in `backlog`
   with its parent unchanged.

**The rule on resolving and dropping**

6. `tcw work complete <parent>` with `--resolution done`, with `--resolution
   wontfix`, and each with `--force`, is refused while a child is `backlog`,
   `active` or `review`; the message names the child; nothing moves. Once every
   child is resolved, the parent completes.
7. The refusal covers the subtree: a parent whose only direct child is resolved (or
   in `backlog`) but which has an `active` grandchild is refused, naming the
   grandchild.
8. `tcw work drop <parent>` is refused while it has any child recorded by
   `parent:`, open or resolved.
9. During a child's claim — its folder in `.claiming/`, not yet in `active/` —
   completing or dropping its parent is refused (tested by leaving a claim folder
   in place, as an interrupted claim does).
10. `tcw work start <child> --take-over --owner x` after an interrupted claim
    publishes the child to `active/` with its `parent:` intact.
11. With a worktree-started parent and an open child, `tcw work complete <parent>
    --resolution done` is refused **before** the branch is merged: the parent's
    branch, worktree and status are unchanged afterwards.
12. An epic with every initiative child resolved but an open `--parent` child is not
    reported ready to close, and `tcw work reconcile <epic> --complete-when-ready`
    does not complete it and does not fail; once the child resolves, both agree it
    is ready.

**Re-parenting**

13. Through `update_work` and the web app's PATCH route: a `backlog` item given an
    `active` parent stays `backlog`; clearing an `active` child's parent leaves it
    `active`; re-parenting an item under itself or its descendant is refused;
    re-parenting an open item under a resolved item, or under an item with a
    resolved ancestor, is refused.

**Legacy boards** (built by hand: `active/<parent>/<child>/state.yaml`, no
`parent:` field)

14. `<child>` reads as `active` with parent `<parent>`; completing the parent is not
    refused because of it and carries it to `completed/`; `tcw validate` does not
    report its missing resolution.
15. A legacy child that has a new-style open child of its own (`parent: <legacy
    child>`) makes completing the top parent refuse, naming that grandchild.
16. A legacy child's own `submit` (in a board where the parent is `active`) moves it
    to `review/<child>/` with `parent: <parent>` written, and `tcw work show` still
    reports the parent. The same for a legacy child under a `backlog` parent started
    with `start --owner x`, and with `start --worktree` with
    `work.auto-commit-transitions: false` and with the store in a separate
    repository — its commit removes the nested source path.
17. With `work.retain.completed: false` and resolved work tracked, completing a
    parent that holds a legacy child and running the deletion records a tombstone
    for the parent **and** the legacy child, each naming a commit that contains it;
    `tcw work show completed/<legacy child>` reports it archived.

**Other surfaces**

18. `tcw validate` reports a `parent:` naming no live item and no tombstone, and a
    `parent:` on a nested item that disagrees with its folder.
19. The web app's transition route (`tcw/serve/__init__.py` complete handler,
    `:970-985`) returns an error status for the rule-3 refusal, with the child named
    in the body. The projection reports each child's own status and `parent`, and
    the web tree nests a child under a parent whose status differs from its own
    (a unit test on `web/client/src/model/tree.ts` with mixed statuses).
20. A child with a tracker binding is found by tracker lookup and sync after its own
    transitions and after its parent's.
21. `tcw work procedure prompt decompose`, the plugin copy, `docs/guide/work.md`,
    the capability description, `FsWorkStore`'s docstring and
    `docs/lifecycle/abstraction.md` no longer say a child shares its parent's status,
    rides along, or de-nests; the "Which path?" section names the differences listed
    under Design; scenario 10 row 4 asserts the refusal.
22. The tests pinning the old behavior for new children
    (`test_create_child_nests_and_derives_parent`,
    `test_parent_transition_carries_children`,
    `test_child_transition_denests_to_top_level` in `tests/test_work.py`) are replaced
    by tests of criteria 1, 4 and 5, and the old-layout behavior they pinned is kept
    as tests of criteria 14 and 16.

## Risks

1. **Two sources for one relation on legacy boards.** A nested item can carry a
   `parent:` field only by a hand edit; the field wins and `validate` reports the
   disagreement (criterion 18). Acceptable because nothing TCW writes produces it.
2. **The claim window is filesystem-private and easy to miss.** Criterion 9 is the
   guard; without it rule 3 fails open for the length of one rename.
3. **Readers that assumed nesting means parent.** A sweep found only `_parent_slug`
   deriving the relation (`grep` for `_parent_slug`, `.parent`, `"parent"` across
   `tcw/`); the CLI list (`tcw/work/cli.py:780-792`, `:825`), the projection and the
   web tree all read the `parent` field. A new reader that walks folders instead
   would treat new children as top-level; criterion 19 covers the existing ones.
4. **Older CLIs reading a new board** see new children as top-level items with an
   unknown `state.yaml` key. Old code reading new data is not a constraint in this
   project; accepted.
5. **Collision with other work on the same code.** The claim and take-over code is
   also the subject of
   `2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app`
   (backlog), and is adjacent to the active
   `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`. This item
   adds only the legacy-child `parent:` write and the claim-window check there.
6. **Size.** Core rules, a field-based parent in the adapter, legacy handling in
   four places, documents, and cross-surface tests. It is at the upper end of one
   item, but splitting it would ship children with their own status that the
   resolve-and-drop rule does not yet protect, so it stays whole.

## Open questions

None. The three raised by the first draft were settled on 2026-09-21: `complete
--force` does not bypass rule 3; every new child gets its own status, including
under a `backlog` parent, and only legacy nested children inherit; there is no gate
on starting a child before its parent is active.

## Notes

- The reporter's workaround (the parent's spec and plan carry every child's design,
  children write only `outcome.md`) stays possible; it is no longer the only option.
- Assumption, not verified against a live tracker: a tracker-backed store would
  answer the children query from its own parent/sub-task link. No tracker adapter
  implements `WorkStore` today, so there is no code to cite.
