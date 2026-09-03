# Plan — The epic owner walk stops at a parent that has no work store

## Tasks

### 1. A fixture graph with a storeless intermediate node

**Creates** a fixture in `tests/conftest.py` (or `tests/fixtures/`, following
whatever the multi-node tests there already use).

Three nodes A → B → C, reciprocally registered, where B has a `tcw-config.yaml`
and no work component at all. A holds an epic; C holds a slice naming it as its
`initiative`.

Written first, and asserted against *current* behavior: `initiative_epic` returns
`None`, `escalate` from C refuses. Those assertions invert in task 2, which is
how the fix is proved rather than asserted.

**Proves it:** `tests/test_multiproject.py` — the fixture builds and
`tcw validate` in each node is clean, so the graph is legal today and the defect
is behavioral rather than a rejected configuration.

### 2. Walk to the nearest work-bearing ancestor

**Modifies** `tcw/store/fs.py`.

Add `nearest_work_ancestor(root)` beside `parent_node` (`:231`): open the
registry, take `registry.ancestors()`, and return the first whose locator has a
usable work store, else `None`. `ancestors()` walks the registry (`tcw/store/project.py`
`FsProjectRegistry.ancestors`), so no filter can terminate it early — that is the
point of using it rather than looping `parent_node`.

Leave `parent_node` unchanged. `_nodes` wants the direct-parent answer and task 5
builds on it.

Repoint the two upward walks:

- `FsWorkStore.initiative_epic` (`:4057-4063`) — replace the `while parent` loop
  with a single pass over the ancestors the helper yields.
- `_render_descendant_boards` (`tcw/work/cli.py:420`) — same substitution.

**Proves it:** `tests/test_multiproject.py` and `tests/test_epic_completable.py` —
the fixture's assertions from task 1 invert: `initiative_epic` finds A's epic
from C, and `tcw work list -i` in A nests the C slice under it. Existing
two-level tests unchanged.

### 3. Cross a storeless node downward too

**Modifies** `tcw/store/fs.py`.

`FsWorkStore.initiative_children` (`:4066-4070`) iterates `child_nodes`, which is
direct children with a store (`:221-228`), so it cannot see C from A. Move it to
the descendant walk `descendant_nodes` (`:241-247`) already performs — that one
filters `registry.descendants()` and therefore already crosses storeless nodes.

This removes the asymmetry the spec names: the two directions currently disagree
about whether a storeless node is passable.

**Proves it:** `tests/test_epic_completable.py` — `tcw work reconcile` in A lists
the C slice. Assert the count as well as the presence, so a duplicate introduced
by the wider walk fails rather than passing silently.

### 4. Escalate to the nearest work-bearing ancestor

**Modifies** `tcw/work/recursion.py`.

`escalate` (`:302-305`) uses the new helper. Refuse only when it returns `None`,
and split the message: no registered parent at all keeps "no parent node to
escalate to (this is the root)"; a registered ancestry with no work store
anywhere in it says that instead, naming the nearest registered ancestor.

**Proves it:** `tests/test_multiproject.py` — from C the request lands in A's
inbox carrying C's canonical id as `from:`; in a graph whose whole ancestry is
storeless, the refusal names that rather than claiming rootness.

### 5. Tell a storeless parent apart from no parent

**Modifies** `tcw/work/cli.py`.

`_nodes` (`:160-174`) prints `parent: (none — root)` in both cases. Keep
`parent_node` for the direct answer, and when it is `None` consult the registry
for a registered parent: if one exists, print it by id and say it keeps no work
store. A node with no registered parent is unchanged.

**Proves it:** `tests/test_multiproject.py` — `tcw work nodes` in C names B and
reports it as keeping no board; in A it still prints `(none — root)`.

### 6. Documentation Sync

One pass over the finished diff.

- **`README.md`** — [Public-API]. Fires. The Connected projects section describes
  cross-project operations over the registered graph; add that a node need not
  keep a work store, and that relations pass through one that does not.
- **`docs/release-notes/upcoming.md`** — [Public-API]. Fires. Plain language: a
  project that only groups other projects no longer hides their epics from each
  other.
- **`docs/changelogs/upcoming.md`** — [Any-Code-Change]. Fires. Fixed: the
  initiative-epic walk, the board's ownership walk, `initiative_children`,
  `escalate`, and the `tcw work nodes` wording.
- **`skills/<component>/SKILL.md`** — [Skill-Driven-Component]. Fires for
  `tcw-work`: `references/cross-node-deltas.md` and `references/epic-deltas.md`
  describe the parent relation an epic is resolved through. Check both for
  wording that assumes the direct parent holds a board.
- **`docs/capabilities/work/escalate-a-request-to-the-parent-node/`** and
  **`.../inspect-the-node-topology/`** — recorded as changed in
  `capabilities.yaml`; both quote the message strings this item changes. Drive
  them with the `tcw-capabilities` skill.

## Verification

What the suite cannot check:

- **Nothing real exercises this shape.** No node in this repository or in
  `proposit-app` is storeless today, so every criterion is a fixture and the fix
  ships unproven against a real graph. When the `proposit-app` root node is
  created, run `tcw work reconcile` on a cross-repository epic from the
  orchestration node and confirm the package slices still appear — and record
  here that this is the outstanding real-world check, rather than treating the
  fixture as equivalent.
- **That the wider walks did not get slower in a way anyone notices.** Task 3
  widens a walk that runs on every `reconcile`. Time `tcw work reconcile` on this
  repository's own board before and after; a difference a user could feel is a
  finding, not a footnote.

## Notes

Task 1 writing assertions against the *broken* behavior first is deliberate: it
is the repository's own rule that a bug fix starts from a failing reproduction,
and inverting those assertions in task 2 is what proves the walk changed rather
than that a new test agreed with new code.
