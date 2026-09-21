# Spec: Let a work item on a board with no capabilities ledger declare deltas against its child nodes' ledgers

## Capability changes

Planned ledger changes only. No records are written at this stage.

- **New:** `work/declare-capability-changes-in-a-child-nodes-ledger` —
  "Declare capability changes in a child node's ledger". As a user working an item
  on a board whose own node keeps no capabilities ledger (a repository root that
  groups packages, for example), I name the capabilities my item adds, changes or
  removes in a child's ledger by prefixing each path in `capabilities.yaml` with
  the child's project id (`proposit-shared/authoring/x`), and `tcw work complete`
  checks each one against that child's ledger. Subject `work-item`, `node`,
  `capability`; Feature `connected-project-registry`.
- **Changed:** `work/complete-a-work-item` — its paragraph on the
  capability-reconciliation gate gains the child-qualified form, and states that a
  declared path nothing can check is refused rather than passed.
- **Changed:** `skills/capabilities` — the skill's `capabilities.yaml` guidance
  teaches the child-qualified form and where to run `tcw capabilities set` for it.

## Problem

A node that keeps a work board but no capabilities ledger cannot declare the
capability changes its items make, and anything it does declare is never checked.

The completion gate is `capability_gate` (`tcw/work/recursion.py:27`). Its first
step asks whether the item's own node has a ledger by testing for the literal
directory `<node root>/docs/capabilities`, and returns "no problems" when it is
absent (`tcw/work/recursion.py:39-41`). Everything after that runs against the
item's own node's ledger only (`FsCapabilitiesStore.open(st.node_root)`,
`tcw/work/recursion.py:47`). So on proposit-app's repo-root node, which keeps a
board but no ledger, a `capabilities.yaml` naming `proposit-shared/authoring/x` is
never read: the gate passes whether the child's capability exists, still reads
`Missing`, or was never written. The existing test
`test_complete_gate_work_only_node_unaffected` (`tests/test_work.py:1021`) pins
that pass as intended behavior.

Qualified paths do resolve today, but only through inheritance. A capabilities
store's `get` treats a first segment as a qualifier only when it names a project
the node's own ledger `extends` (`tcw/store/fs.py:2665-2668`; the aliases are
project ids, `tcw/store/fs.py:1348-1383`). That is why
`tcw capabilities show proposit-shared/...` works inside proposit-mobile, which
extends proposit-shared, and why nothing resolves at a node with no ledger: there
is no store to extend anything.

Cross-package work has to live on that root board, because `delegate` and
`reconcile` reach only one level down and skip nodes without boards (GitHub #30).
So the node where cross-package items belong is exactly the node that cannot
declare their capability changes. The reporter worked around it by running
`tcw capabilities add` in the child by hand and writing no `capabilities.yaml`,
which leaves the completion gate with nothing to enforce.

## Goals

1. An item's `capabilities.yaml` may name a path as `<child-id>/<path>`, where
   `<child-id>` is a project id declared under the item's node's
   `connected-projects.children`. The gate resolves `<path>` against that child's
   own ledger and applies the existing rules there: `new:` resolves and no longer
   reads `Missing`; `changed:` resolves; `removed:` no longer resolves as a local
   capability of that child.
2. This works on a node with no ledger (the reported case) and on a node that has
   one (mixing local, inherited and child-qualified paths in one file).
3. The gate fails closed on every child-qualified path it cannot check: a child
   declared but not present in this checkout, a child with no ledger, a child whose
   ledger is declared but not provisioned or is misconfigured. Each becomes a
   problem line, never an exception, so a discard still completes.
4. "Does this node have a ledger?" is asked of the node's resolved capabilities
   store, not of a literal `docs/capabilities` folder, for both the item's node and
   each child. A child whose ledger lives at `capabilities.path` or in another
   repository through `capabilities.repository` is checked where it actually is.
5. The capabilities skill and the user guides say how to write a child-qualified
   path and where to reconcile it.

## Non-goals

- **Handing each path to the child's own gate.** Considered and not chosen by the
  requester on 2026-09-21 (see `initial-request.md`). The item's node's gate reads
  the child's ledger directly.
- **Grandchildren and other non-children.** Only direct children declared under
  `connected-projects.children` qualify. Descending through a node without a board
  or ledger to reach its children is the subject of GitHub #30
  (`2026-09-09-descend-through-a-storeless-routing-node-in-delegate-and-reconcile`);
  if that item introduces a descending walk, extending qualifiers to it is a
  follow-up. Siblings and ancestors stay reachable only through `extends`, as today.
- **`tcw capabilities show/set/add` accepting child-qualified paths at a node with
  no ledger.** The user still runs those commands inside the child. Worth a
  follow-up item; not needed for the gate.
- **Checking `capabilities.yaml` paths before completion** (`tcw validate`,
  `tcw capabilities check`). That is GitHub #27
  (`2026-09-09-resolve-capabilities-yaml-sidecar-paths-while-an-item-is-still-being-worked`).
  This item defines the resolution rule #27 should check against, and puts it in
  one place so #27 can reuse it.
- **Short prefixes** such as `shared/` standing for `proposit-shared` (raised in
  #27). Only a full project id qualifies.
- **Requiring a `capabilities.yaml` when the spec declares deltas**
  (`2026-08-21-nothing-enforces-a-spec-s-declared-capability-deltas-without-a-capabilities-yaml`).
- **An unreadable `capabilities.yaml` taking down the board**, and the `_json_safe`
  check. Those are part 2 of
  `2026-09-15-make-the-capability-gate-honor-a-configured-ledger` and stay there.
- **Parsing or rewriting any `capabilities.yaml` in completed items.** The gate runs
  only at completion; completed items are not re-checked.

## Design

### Order of work in the gate

1. **Read the item's `capabilities.yaml` first**, through `declared_capabilities`
   (`tcw/store/base.py:291`), before opening the project registry or any
   capabilities store. An absent or empty file, or one declaring no paths, passes
   immediately — so a node whose capabilities declaration or `connected-projects`
   is broken is not refused for an item that declares nothing. An unreadable file
   is a problem, as today (fails closed). The file's schema does not change.
2. Only when at least one path is declared, open the node's project registry and
   its own capabilities store, and resolve each path by the rule below.
3. **Every failure to open a registry or a store becomes a problem line, never an
   exception out of the gate.** The registry's `require_valid` and every store
   opening failure (`StoreNotProvisioned`, `StoreDeclarationError`,
   `StoreLocationUnusable`, all `ValueError`s, `tcw/store/base.py:57-101`) are
   caught and reported with their own message. This is what keeps a discard
   completing: the CLI turns problems into warnings on a discard
   (`tcw/work/cli.py:3667-3681`), but an escaping exception would abort it.

### Resolution rule

For each declared path `P` on an item whose node is `N`, split `P` at its first
`/` into a head `H` and a remainder `R`. Project ids cannot contain `/`
(`tcw/store/project.py:22`), so the split is unambiguous. Then, in this order:

1. **`H` is a project `N`'s own ledger extends.** Resolved by `N`'s ledger exactly
   as today (`tcw/store/fs.py:2667-2668`). **This wins even when `H` is also a
   declared child of `N`**: every existing sidecar that names an inherited
   capability this way keeps its meaning, and the two readings would usually agree
   anyway, since both reach the same project's ledger (the inheritance reading
   additionally applies `N`'s local override, which is what `N` shows its users).
2. **`H` is a declared child of `N`** (by id, from the registry's declared
   children, reachable or not — `declared_child_ids`, `tcw/store/base.py:210`).
   Before treating it as child-qualified, check for ambiguity (below). If not
   ambiguous, `R` is checked against the child's ledger with the gate's existing
   rules: `new:` and `changed:` through the child store's `get(R)`, `removed:`
   through its `get_local(R)` (`tcw/store/fs.py:2631`, `2665`). Because the child's
   own `get` is used, `R` may be bare, local to the child, inherited by it, or
   qualified by a project the child extends. So `proposit-server/authoring/x`
   resolves to proposit-server's view of the inherited capability, including a
   local override that sets `Supported` — the reporter's "`Supported` overrides in
   both apps".
3. **Otherwise** the path is `N`'s own. If `N` has a ledger, it is checked there as
   today. If `N` has no ledger, it is a problem: the message says `N` keeps no
   capabilities ledger and lists `N`'s declared children as qualifiers.

**Ambiguity** is judged over `N`'s *resolved* view, not only its local folders.
When `N` has a ledger and `H` is a declared child (and not an extends alias), the
path is ambiguous if `N`'s ledger lists any capability — local, or inherited
through `get`'s bare fall-through to an extended project
(`tcw/store/fs.py:2669-2677`) — whose path starts with `H/`. An ambiguous path is
refused with a message naming both readings. This also covers the redirection
case: a sidecar path `kid/x` that resolved through inheritance before `kid` was
declared as a child is refused once `kid` is declared, rather than silently
switching to the child's ledger. The check uses the ledger's namespace listing
(`list_all(namespace=H)`), which a non-filesystem store can answer.

**`removed:` stays local-only**, in the child exactly as in `N` today
(`tcw/store/fs.py` `get_local`, and the comment at `tcw/work/recursion.py:70-72`).
Two consequences, both deliberate:

- A `removed:` remainder whose first segment is a project the child extends
  (`removed: [kid/lib/auth/x]`) is refused: "`tcw capabilities rm` deletes only
  local capabilities; kid cannot remove a capability it inherits from lib". Today
  such a path would pass silently, because `get_local` finds nothing at that
  literal path. The same function applies the same refusal to `N`'s own
  `removed:` paths qualified by an extends alias (rule 1), which is the identical
  defect in today's gate.
- A child that deletes a local capability which was shadowing an inherited one at
  the same path passes, even though `get(R)` would now resolve the inherited one.
  That is today's local rule, whose reasoning (`rm` refuses inherited
  capabilities, so counting them would be a dead end) applies unchanged.

### Settled decisions

- **Unqualified paths on a node with no ledger are refused** (rule 3). Decided
  2026-09-21 on advisor review. A declared delta that nothing can check is the
  hole this item closes; passing it silently would leave the reporter's failure in
  place for anyone who forgets the prefix. `--force` skips the gate, a discard
  only warns, and an absent or empty `capabilities.yaml` still passes. This
  reverses `test_complete_gate_work_only_node_unaffected`
  (`tests/test_work.py:1021`) and is a **compatibility change for the release
  notes**: an active item on such a node that declares unqualified paths was passed
  before and is refused after.
- **This item absorbs part 1 of
  `2026-09-15-make-the-capability-gate-honor-a-configured-ledger`** (the gate's
  literal `docs/capabilities` test). Decided 2026-09-21: this item must rewrite
  that exact step anyway, and doing the child check with the old test would add a
  second copy of the defect. That item's part 2 (an unreadable
  `capabilities.yaml`, and the `_json_safe` check) stays there; the lead narrows it.
  Its suggested regression — a node whose `capabilities.path` points outside
  `docs/capabilities` — is the source of criteria 13-14, extended here to
  `capabilities.repository`.

### Child failures

Each is one problem line naming the full declared path and the child's project id.
A problem refuses a shipping completion and is a warning on a discard, and
`--force` skips the gate, all as today (`tcw/work/cli.py:3667-3681`).

- Child declared but not present in this checkout: the registry's existing
  "declared but not reachable here" wording (`unreachable_project_note`,
  `tcw/store/fs.py:364`), which names `tcw provision` when a repository is
  declared.
- Child present but keeps no capabilities ledger: "project '<id>' keeps no
  capabilities ledger".
- Child's ledger declared (`capabilities.path` or `capabilities.repository`) but
  unprovisioned, or its declaration malformed: the store's own message, which
  already names the remedy (`tcw provision` for an unprovisioned repository).
- `R` empty (`proposit-shared/`): "names project '<id>' but no capability".
- The existing "declared (new) but does not resolve", "still Missing" and
  "declared (removed) but still resolves" wordings, prefixed with the full declared
  path and naming the child, so the user knows where to run
  `tcw capabilities set` or `rm`.

### "Does this node have a ledger?"

The gate can no longer return early when `N` has no ledger, because child-qualified
paths still need checking. For `N` and for each child, the question is asked of the
resolved capabilities store, the way `find_node` already asks it
(`tcw/store/fs.py:192-226`: open the configured store, then ask whether its root
exists; a declared-but-unprovisioned store raises rather than reading as absent,
and that raise becomes a problem). Ledgers at `capabilities.path` or in another
repository through `capabilities.repository` are therefore found where they are.

If `N`'s own store is declared but unprovisioned (or misdeclared), **every**
declared path is refused with the store's message — including an all-child-qualified
file. Rule 1 and the ambiguity check both need `N`'s extends list and resolved view,
so without `N`'s store the gate cannot tell which reading a path has. The user
provisions the store or passes `--force`.

### Where the rule lives

One function that, given the item's node and a declared path, returns which
ledger answers for it and the path within that ledger, or a problem. The gate is
its first caller; #27's validator should be its second. It uses only the project
registry's declared children and "get project by id", and the capabilities
store's `get`, `get_local` and namespace listing — all answerable by a
non-filesystem store, so it passes the abstraction litmus test in
`docs/lifecycle/abstraction.md`. It sits beside `capability_gate`, in the
cross-node layer that already reaches into child nodes, not in the abstract
`WorkStore`.

### Callers

- `tcw work complete` (`tcw/work/cli.py:3667`): the gate call is unchanged, but the
  remedy line printed after the problem list (`tcw/work/cli.py:3673-3674`, today
  "Reconcile them (tcw capabilities set <path> --status <S>) or re-run with
  --force.") and the discard hint after the warnings (`tcw/work/cli.py:3678-3680`)
  are **edited** to say that a child-qualified path is reconciled by running
  `tcw capabilities set` (or `rm`) inside the named child, with the path minus its
  child prefix.
- `tcw work reconcile --complete-when-ready` (`tcw/work/recursion.py:222`): no edit;
  it joins the problems into its error message.
- The epic rollup's list of declared deltas (`_capability_deltas`,
  `tcw/work/recursion.py:101`) prints paths verbatim and needs no change.

### Harness compatibility

The requirement is carried entirely by the `tcw` CLI's completion gate, so it
behaves identically under Claude and Codex. The skill text only teaches the
syntax.

### Documentation

- `skills/capabilities/SKILL.md` (the schema block at lines 40-50): the
  child-qualified form, a worked example, and that `tcw capabilities add/set/rm`
  for such a path is run inside the child.
- `docs/guide/work.md` (the `complete` paragraph at line 299) and
  `docs/guide/taxonomy-and-capabilities.md` (around line 99): the same, briefly.
- `skills/work/references/cross-node-deltas.md`: a cross-package item on a
  repository-root board declares its capability changes with child-qualified
  paths.
- Changelog, and release notes including the compatibility change above.

## Acceptance criteria

Fixture for criteria 1-12: a parent node `root` with a work board and **no**
capabilities ledger, declaring child `kid` under `connected-projects.children`;
`kid` has its own ledger (with or without a board — it must not matter). An item on
`root`'s board carries a `capabilities.yaml`. "Refused" means `tcw work complete
<slug> --resolution done --confirm` exits 1, prints the named text on stderr, and
the item stays in its status; "passes" means it exits 0.

1. `new: [kid/auth/login]` with `auth/login` reading `Missing` in `kid`'s ledger is
   refused, naming `kid/auth/login` and "still Missing", and the remedy line names
   `kid` as where to run `tcw capabilities set`. After
   `tcw capabilities set auth/login --status Supported` run in `kid`, it passes.
2. Criterion 1 repeated on a `--worktree` item on `root`, with the status flip made
   in `kid` on the work branch (same repository), completed from the primary
   checkout: it passes only because the gate runs after merge-back.
   (`test_complete_gate_reads_after_worktree_mergeback` covers the own-ledger case
   only.)
3. `new: [kid/auth/ghost]` (absent from `kid`) is refused with "does not resolve".
4. `changed: [kid/auth/login]` passes when `auth/login` exists in `kid` whatever its
   status, and is refused with "does not resolve" when it does not.
5. `removed: [kid/auth/login]` is refused with "still resolves" while `kid` has a
   local `auth/login`, and passes once it is deleted with `tcw capabilities rm`.
6. `kid` extends a sibling `lib` whose ledger has `auth/login`. With a local
   override in `kid` setting `Status: Supported`, `new: [kid/auth/login]` passes;
   with the override absent and `lib`'s status `Missing`, it is refused.
7. `kid` has a local `auth/login` shadowing `lib`'s `auth/login`. After `rm` of the
   local one in `kid`, `removed: [kid/auth/login]` passes although `lib`'s still
   resolves through inheritance.
8. `removed: [kid/lib/auth/login]` is refused with text saying `rm` deletes only
   local capabilities. On a node that has a ledger extending `lib`,
   `removed: [lib/auth/login]` is refused the same way.
9. With `kid` declared but its directory absent from the checkout, any `kid/...`
   path is refused with the "declared ... not reachable" / "run `tcw provision`"
   wording. With `kid` present but keeping no ledger, it is refused with "keeps no
   capabilities ledger".
10. `new: [auth/login]` (unqualified) on `root` is refused with a message saying
    `root` keeps no capabilities ledger and listing `kid` as a qualifier.
    `test_complete_gate_work_only_node_unaffected` (`tests/test_work.py:1021`) is
    updated to assert this.
11. On a genuinely work-only node (built with `node(...)`, not `_wc_node`, which
    has a ledger — `tests/test_work.py:895-899`), an item with no
    `capabilities.yaml` passes, and an item with an empty `capabilities.yaml`
    passes. The same two pass on a node whose `capabilities` declaration is broken
    (for example `capabilities.path` naming a missing directory) and on a node whose
    `connected-projects` fails validation.
12. Criteria 1, 9 and 10 completed with `--resolution wontfix --confirm` are not
    refused: the problems print as warnings and the item moves to `discarded/`.
    This includes a node whose own store or registry fails to open (no exception
    escapes the gate).
13. `kid`'s ledger moved by `capabilities.path: ledger` (no `kid/docs/capabilities`
    exists): criteria 1 and 3 still hold. On a node that has its own ledger at
    `capabilities.path`, a local `new:` path still reading `Missing` is refused
    (part 1 of `2026-09-15-make-the-capability-gate-honor-a-configured-ledger`).
14. `kid`'s ledger declared through `capabilities.repository` and provisioned:
    criterion 1 holds. Declared but not provisioned: any `kid/...` path is refused
    with the store's own message naming `tcw provision`.
15. A parent node with its own ledger that also declares `kid` as a child: one
    `capabilities.yaml` mixing `new: [auth/login]` (local), `new: [kid/auth/login]`
    and `new: [lib/auth/x]` (extends-qualified) checks each against the right
    ledger.
16. When the parent **extends** `kid` as well as declaring it a child,
    `new: [kid/auth/login]` is resolved through inheritance: with `kid`'s
    `auth/login` reading `Missing` but the parent holding a local override setting
    `Supported`, it passes.
17. When the parent's resolved view has a capability under `kid/` — a local
    `kid/x`, or an inherited `kid/x` reached by bare fall-through from an extended
    `lib` — a `kid/...` path is refused as ambiguous, and the message names both
    readings.
18. On a node whose own capabilities store is declared but unprovisioned, a
    `capabilities.yaml` holding only `kid/...` paths is refused with the store's
    message.
19. `tcw work reconcile <epic> --complete-when-ready` on `root`, with an epic whose
    `capabilities.yaml` holds criterion 1's still-Missing path, raises the same
    problem and does not complete the epic.
20. Every existing capability-gate test still passes:
    `python -m pytest tests/test_work.py -k complete_gate tests/test_capabilities_rm.py tests/test_capabilities_sidecar.py`
    (14 passing on today's tree; criterion 10 updates one of them).
21. `skills/capabilities/SKILL.md`, `docs/guide/work.md` and
    `docs/guide/taxonomy-and-capabilities.md` each contain a child-qualified
    example path and say where to run `tcw capabilities set` for it;
    `docs/release-notes/upcoming.md` names the compatibility change.

## Risks

- **Items that passed silently start being refused** (settled decision above). The
  message says how to fix it, `--force` remains, and completed items are never
  re-checked.
- **Declaring a new child can refuse an existing item.** An active item's `kid/x`
  path that resolved through inheritance becomes ambiguous once `kid` is declared a
  child (criterion 17). Refusing is chosen over silently switching ledgers.
- **The child's working tree is what is read.** For a child in another repository,
  a status flip made there but not committed or pushed still satisfies the gate.
  That matches how the gate treats the item's own ledger today (capability writes
  are staged, not committed); the guide says so rather than the gate trying to
  prove more.
- **Worktree items.** The gate runs after merge-back on the primary checkout
  (`tcw/work/cli.py:3660-3666`). A child in the same repository is merged with it
  (criterion 2); a child in another repository is read from that repository's
  checkout.

## Open questions

None. Both earlier questions were settled on 2026-09-21 (see "Settled decisions").

## Notes

- Checked on today's tree: the gate tests named in criterion 20 pass (14 passed).
  The other criteria describe new behavior and fail today by construction;
  criterion 10's current opposite is asserted by `tests/test_work.py:1021`.
- Assumption, not verified against proposit-app: its children declare themselves
  under the root's `connected-projects.children` with ids `proposit-shared`,
  `proposit-server` and `proposit-mobile`, as the intake says.
- `child_nodes` (`tcw/store/fs.py:236`) is not the right list for this: it keeps
  only children with a work board, and a child may keep a ledger and no board.
- Sibling sweep, repo-wide: the only reader of `capabilities.yaml` paths that
  resolves them is `capability_gate`; the epic rollup (`tcw/work/recursion.py:101`)
  displays them and the web app edits the file without resolving it. The one
  sibling defect found in the gate itself — an extends-qualified `removed:` path
  passing silently — is fixed here (criterion 8).
- Relation to the other items named in the brief: none blocks this one. #30
  explains why the work sits on the root board and would extend the qualifier reach
  if it lands; #27 is the natural second caller of the resolution function;
  2026-08-21 is about the file existing at all and is unaffected; 2026-09-15 loses
  its part 1 to this item.
