# Plan: Let a work item on a board with no capabilities ledger declare deltas against its child nodes' ledgers

Implements `spec.md` (committed in `3d962fe1`). Criterion numbers below ("C1"…"C21")
are the spec's acceptance criteria.

## Setup (before Task 1)

Implementation runs in `.worktrees/<slug>/` on branch `work/<slug>`, created by the
lead's `tcw work start --worktree`. The shared editable install points at the
primary checkout, so worktree source is not what bare `pytest` imports. Use a
private virtual environment, per the project memory on worktree testing:

```sh
S=<scratchpad>/venv-ledgerless
python -m venv --system-site-packages $S
$S/bin/pip install -e /Users/brian/Projects/TCW/.worktrees/<slug> --no-deps
$S/bin/pip install --ignore-installed pytest
```

Every test command below is run **from the worktree root** as
`PATH="$S/bin:$PATH" pytest <args>` — bare `pytest`, as CI runs it
(`pyproject.toml:36-44` sets `pythonpath = ["."]`). Before Task 1, run the full
suite once that way and record the baseline; every later task must end at the same
count plus its new tests, with nothing newly red.

Also before Task 1, the item's own capability bookkeeping (the TCW node has a
ledger, so these are ordinary local paths):

- `tcw capabilities add work/declare-capability-changes-in-a-child-nodes-ledger "Declare capability changes in a child node's ledger" --status Missing`,
  then `tcw capabilities set … --field "Planning doc=<slug>"`,
  `--field "Subject=work-item, node, capability"`,
  `--field "Feature=connected-project-registry"`, and the body from the spec's
  "Capability changes" section.
- Write the item's `capabilities.yaml`:

  ```yaml
  new:
      - work/declare-capability-changes-in-a-child-nodes-ledger
  changed:
      - work/complete-a-work-item
      - skills/capabilities
  ```

Commit these with the first implementation commit. The new capability is flipped
to `Supported` in Task 8.

## Tasks

Each task is one commit and leaves the full suite green. Tests are written first
and seen to fail for the stated reason (read the failure message, not only the
colour — `docs/lifecycle/implementation.md`, "Tests that cannot narrow a
criterion").

New tests go in one new module, **`tests/test_capability_gate_children.py`**,
except where a task says otherwise. Its fixtures:

- `_graph(tmp_path, *, parent_ledger: bool, kid_ledger: str | None, kid_repo: str)`
  builds `root` (work board; a local capabilities ledger only when
  `parent_ledger`) and child `kid`, reciprocally registered under
  `connected-projects`. `kid_ledger` is `"default"`, `"path"` (the ledger at
  `capabilities.path: ledger`, no `docs/capabilities`), `"repository"` (declared
  through `capabilities.repository`, see Task 6) or `None` (no ledger).
  `kid_repo` is `"same"` (a subfolder of `root`'s repository, like
  proposit-app's `packages/shared`) or `"separate"` (its own git repository).
  **No argument has a default**: the implementation rules forbid a shared
  fixture defaulting an axis the code branches on. Built from the existing
  `subnode`/`node` helpers in `tests/test_work.py:16-44` and `init`, and
  `set_component_key` from `tests/nodeconfig.py`.
- `_item(root, sidecar: str | None)` creates and starts an item and writes its
  `capabilities.yaml` (`None` writes no file, `""` writes an empty one), like
  `_item_with_delta` at `tests/test_work.py:902-909`.
- `_refused(capsys, *needles, absent=())` and `_passed(...)`: one assertion helper
  per property ("refused" = exit 1, each needle on stderr, each `absent` string not
  on stderr, item still in its status; "passed" = exit 0). Every criterion test
  calls one of them.

### Task 1 — Gate reads the sidecar first, finds ledgers through the resolved store, and never raises

Absorbs part 1 of `2026-09-15-make-the-capability-gate-honor-a-configured-ledger`.
Behavior for child-qualified paths does not change yet; an unqualified path on a
node with no ledger still passes in this task (that flips in Task 2).

Modify **`tcw/work/recursion.py`**:

- In `capability_gate` (line 27), move `declared_capabilities(item.capabilities)`
  to the top. Return `[]` when it declares nothing, before any registry or store
  is opened. Keep the `SidecarError` → `"capabilities.yaml is unreadable: …"`
  problem as is.
- Add a private `_open_ledger(node_root: Path) -> tuple[FsCapabilitiesStore | None, str | None]`:
  opens `FsCapabilitiesStore.open(node_root)` inside `try/except ValueError`
  (covers `StoreNotProvisioned`, `StoreDeclarationError`,
  `StoreLocationUnusable` and the registry's `require_valid` failure, all
  `ValueError`s — `tcw/store/base.py:57-101`, `tcw/store/project.py:328-331`).
  Returns `(store, None)` when `store.root.is_dir()`, `(None, None)` when the
  store opened but its root is absent (no ledger — the same question
  `find_node` asks at `tcw/store/fs.py:226`), and `(None, str(error))` on an
  exception.
- Replace the literal `st.node_root / "docs" / "capabilities"` test
  (lines 39-41) with `_open_ledger(st.node_root)`. On `(None, msg)`, return one
  problem per declared path: `f"{path}: {msg}"`. On `(None, None)`, return `[]`
  (unchanged for now).
- Rewrite the docstring: drop "A work-only node … passes silently", say the
  sidecar is read first and store failures become problems.

Tests (write first):

- In `tests/test_capability_gate_children.py`: **C13 second half** — a node with
  its ledger at `capabilities.path` (outside `docs/capabilities`) and a local
  `new:` path still `Missing` is refused with "still Missing". Fails today because
  the gate returns `[]`.
- **C11** — on genuine work-only nodes (built with `node(...)`, never
  `_wc_node`, which has a ledger — `tests/test_work.py:895-899`): an item with no
  `capabilities.yaml` passes and an item with an empty one passes. Then the same
  two on a node whose `capabilities.path` names a missing directory, and on a node
  whose `connected-projects` fails validation (a child entry pointing at a
  directory with no `tcw-config.yaml`). Fails today on the last two only if the
  sidecar is not read first — confirm by reading the failure.
- **C12 (store-failure half)** — on the broken-`capabilities.path` node, an item
  declaring `new: [auth/login]` completed with `--resolution wontfix --confirm`
  exits 0, moves to `discarded/`, and prints `warning: unreconciled capability:`.
  Today this raises out of the gate.
- Existing gate tests still pass: `pytest tests/test_work.py -k complete_gate
  tests/test_capabilities_rm.py tests/test_capabilities_sidecar.py` (C20).

### Task 2 — Child-qualified paths, and refusing unqualified paths on a node with no ledger

The core change. Modify **`tcw/work/recursion.py`**:

- Add `Route = NamedTuple("Route", owner: str | None, store: FsCapabilitiesStore, path: str)`
  (`owner` is the child project id, or `None` for the item's own node) and a
  public `route_capability_path(path: str, *, own: FsCapabilitiesStore | None,
  registry: ProjectRegistry, node_id: str, open_child) -> Route | str`, where a
  `str` return is a problem line. This is the single place the resolution rule
  lives (spec "Where the rule lives"); GitHub #27's validator is meant to call it
  later. It uses only `registry.declared_child_ids()`, `registry.get(id)`,
  `unreachable_project_note(registry, id)` (`tcw/store/fs.py:364`) and the
  stores it is handed, so it passes the abstraction litmus test. `open_child`
  is a callable `(project_id) -> FsCapabilitiesStore | str` that `capability_gate`
  supplies, caching one `_open_ledger` result per child per gate call.
- The rule, in this order, with `H, _, R = path.partition("/")`:
  1. `own is not None and H in own.extends` → `Route(None, own, path)`
     (the existing inheritance reading wins, even when `H` is also a child).
  2. `H in registry.declared_child_ids()` →
     - `R == ""` → `f"{path}: names project '{H}' but no capability"`;
     - `registry.get(H) is None` → `f"{path}: {note}"`, `note` from
       `unreachable_project_note`, or `f"project '{H}' is declared but not reachable in this checkout"`
       when it returns `None`;
     - `open_child(H)` returns a problem → `f"{path}: {problem}"`;
     - child has no ledger → `f"{path}: project '{H}' keeps no capabilities ledger"`;
     - else `Route(H, child_store, R)`.
     (Ambiguity is added in Task 3.)
  3. otherwise: `own is not None` → `Route(None, own, path)`; else
     `f"{path}: this node ('{node_id}') keeps no capabilities ledger; qualify the path with a child project id ({ids})"`,
     where `ids` is the comma-joined declared children, or
     `"it declares no child projects"` when there are none.
- In `capability_gate`, after Task 1's opening of `own`: open the registry with
  `FsProjectRegistry.open(st.node_root).require_valid()` inside the same
  `ValueError` → one-problem-per-path handling; route each declared path; apply
  the existing checks against `route.store` and `route.path` (`get` for `new:`
  and `changed:`, `get_local` for `removed:`, `RefError` caught as today). For a
  child route, the existing messages gain the child: `"still Missing in project
  '{owner}' (declared new; …)"`, `"declared (changed) but does not resolve in
  project '{owner}'"`, `"declared (removed) but still resolves in project
  '{owner}' (…)"`. Local messages stay byte-identical, so existing tests hold.
- The `(None, None)` branch from Task 1 no longer returns early: with no own
  ledger, routing still runs, and unqualified paths get the rule-3 problem.
- If the own store failed to open (`(None, msg)` from Task 1), every path stays
  refused with `msg` — including all-child-qualified files (spec: rule 1 and the
  ambiguity check need the node's own view).

Tests (write first), using `_graph(..., parent_ledger=False, kid_ledger="default", kid_repo="same")`
unless stated:

- **C1** (without the remedy-line assertion, which is Task 5): refused naming
  `kid/auth/login` and "still Missing in project 'kid'"; after
  `FsCapabilitiesStore.open(kid).set("auth/login", {"Status": "Supported"})`,
  passes.
- **C3**, **C4**, **C5**, as written in the spec.
- **C6** — `kid` extends sibling `lib` (a third node, reciprocally connected to
  `kid`); override present → passes; override absent and `lib` `Missing` →
  refused.
- **C9** — two cases: `kid` declared, directory deleted → refused with
  "declared" and "tcw provision" or "not reachable" (whichever
  `unreachable_project_note` yields for a plain path declaration — assert the
  actual wording once, from the code, not a guess); `kid_ledger=None` → refused
  with "keeps no capabilities ledger".
- **C10** — unqualified `new: [auth/login]` on `root` refused with
  "keeps no capabilities ledger" and "kid". **Update**
  `test_complete_gate_work_only_node_unaffected` (`tests/test_work.py:1021`):
  rename to `test_complete_gate_work_only_node_refuses_an_unqualified_path`,
  assert exit 1 and "keeps no capabilities ledger" and "it declares no child
  projects".
- **C13 first half** — `kid_ledger="path"`: C1 and C3 hold.
- **C15** — `parent_ledger=True` and `root` extends `lib`: a file mixing a local
  `new:`, `new: [kid/auth/login]` and `new: [lib/auth/x]` refuses exactly the
  unreconciled ones and names each against the right ledger.
- **C16** — `root` both extends and declares `kid` as a child; `kid`'s
  `auth/login` `Missing`, `root` holds a local override setting `Supported` →
  passes (inheritance reading won). Mutation check: temporarily swap rules 1 and
  2 and confirm this test goes red for that reason.
- **C18** — `root`'s own `capabilities.repository` declared, not provisioned,
  file holds only `kid/...` paths → refused with the store's message
  (contains "tcw provision").
- **C12 (child half)** — C1's unreconciled state and C9/C10's cases completed
  with `--resolution wontfix --confirm` → exit 0, `discarded/`, warnings printed.

### Task 3 — Ambiguity between a child id and the parent's own namespace (riskiest)

Isolated in its own commit, after the routing and its tests exist, because it is
the one rule that can refuse a path that used to pass on a node with a ledger.

Modify **`tcw/work/recursion.py`**, rule 2 of `route_capability_path`: before
routing to the child, when `own is not None`, compute
`clash = [c.path for c in own.list_all(namespace=H)]` — `list_all` without
`local_only` includes inherited capabilities (`tcw/store/fs.py:2649-2664`), so
this is the parent's **resolved** view, covering both a local `kid/x` and one
reached through `get`'s bare fall-through to an extended project
(`tcw/store/fs.py:2669-2677`). If `clash` is non-empty, return
`f"{path}: ambiguous — '{H}' is both a child project of this node and a namespace in this node's capabilities ledger ({clash[0]}{', …' if more}); rename one of them, or complete with --force"`.

Note on `list_all(namespace=H)`: an inherited capability's `path` is its path
within the extended project, which is exactly what `get`'s bare fall-through
matches, so the namespace filter sees the same paths the fall-through would.

Tests (write first):

- **C17** — two cases on `_graph(..., parent_ledger=True, ...)`: (a) `root` has a
  local `kid/x`; (b) `root` extends `lib`, `lib` has `kid/x`, `root` has nothing
  local under `kid/`. Both: `new: [kid/auth/login]` refused with "ambiguous" and
  naming `kid/x`. Case (b) is the redirection case from the spec: first run the
  same item with `kid` **not** yet declared and `lib`'s `kid/x` as the declared
  path, see it pass through inheritance, then declare `kid` and see it refused.
- Regression: C15 and C16 still pass (C16's `kid` is an extends alias, so rule 1
  takes it before the ambiguity check runs).

### Task 4 — `removed:` stays local-only in child and parent

Modify **`tcw/work/recursion.py`**: in the `removed:` loop, before `get_local`,
if `route.path`'s first segment is in `route.store.extends`, report
`f"{path}: `tcw capabilities rm` deletes only local capabilities; {who} cannot remove a capability it inherits from '{alias}'"`,
where `who` is `f"project '{route.owner}'"` or `"this node"`. This applies to the
parent's own extends-qualified `removed:` paths too (rule 1), which today pass
silently.

Tests (write first):

- **C8** — `removed: [kid/lib/auth/login]` refused with "deletes only local
  capabilities" and "'lib'"; on a parent with a ledger extending `lib`,
  `removed: [lib/auth/login]` refused the same way.
- **C7** — `kid` has a local `auth/login` shadowing `lib`'s; after
  `FsCapabilitiesStore.open(kid).remove("auth/login")`,
  `removed: [kid/auth/login]` passes. (Mirrors
  `test_gate_removed_ignores_an_inherited_capability_at_the_same_path`,
  `tests/test_capabilities_rm.py:325`, for the child route.)

### Task 5 — CLI remedy text names the owning child

Modify **`tcw/work/cli.py`**, the `complete` gate block:

- Lines 3673-3674: replace `"Reconcile them (tcw capabilities set <path> --status <S>) or re-run with --force."`
  with `"Reconcile them (tcw capabilities set <path> --status <S>). For a path that starts with a child project's id, run it inside that child's folder, with the path after the id. Or re-run with --force."`
- Lines 3678-3680: the discard hint `"Mark them Omitted (tcw capabilities set <path> --status Omitted) if they will never be built."`
  gains the same sentence about child-qualified paths.

Tests (write first):

- **C1 remedy half** — extend C1's test: stderr contains "inside that child's
  folder", and the old text `"--status <S>) or re-run with --force."` is
  **absent** (the implementation rules require asserting the
  replaced message is gone).
- Same pair of assertions for the discard hint on C12's wontfix case.
- Grep `tests/` for the old remedy string; any test asserting it is updated in
  this commit.

### Task 6 — Two-repository cases: a child in its own repository and a child ledger declared by `capabilities.repository`

Tests only, unless one fails (then the fix goes in `tcw/work/recursion.py` in
this commit). The implementation rules require real separate git repositories
for store-location defects; a single-repo fixture reproduces none of them.

Add to `tests/test_capability_gate_children.py`, reusing `_tree_node`-style
config and `_remote_with_tree` from `tests/test_store_provisioning.py:1225-1296`
(import them, as `tests/test_edit_type.py:7-8` imports from sibling test
modules):

- `_graph(..., kid_repo="separate", kid_ledger="default")`: C1 and C3 hold.
- **C14** — `kid_ledger="repository"`: provisioned (via `FsStoreProvisioner(...).ensure_available()`,
  as in `tests/test_store_provisioning.py:1291-1293`) → C1 holds; declared but not
  provisioned → any `kid/...` path refused with the store's own message, which
  contains "tcw provision".

### Task 7 — Worktree merge-back and `reconcile --complete-when-ready`

Tests only, same rule as Task 6.

- **C2** — `_graph(..., kid_repo="same", ...)`, item on `root` started with
  `--worktree`; flip `kid`'s `auth/login` to `Supported` inside the worktree's
  copy of `kid` and commit on the branch; assert the primary `kid` still reads
  `Missing`; `tcw work complete` from the primary checkout exits 0. Modeled on
  `test_complete_gate_reads_after_worktree_mergeback` (`tests/test_work.py:1030`),
  which covers only the node's own ledger. Run with `TCW_WORK_OWNER` set, as
  `tests/test_tracker_cli.py`'s fixture does, because `start` needs a claimant and
  the CI runner has no git identity.
- **C19** — an epic on `root` whose `capabilities.yaml` holds C1's still-Missing
  path, all children resolved; `reconcile(root, epic, complete_when_ready=True)`
  raises `ValueError` containing "still Missing in project 'kid'" and the epic is
  not completed. Model on the existing `--complete-when-ready` tests in
  `tests/test_epic_completable.py`.

### Task 8 — Documentation Sync and ledger records

One pass over the finished diff. Each trigger from `tcw work docs`:

| Entry | Fires? | Action |
|---|---|---|
| `README.md` [Public-API] | Evaluate | User-facing gate behavior changes. README's capabilities section (lines ~320-335) describes the ledger but not the gate's rules; expected **no change** — confirm, and record the decision in the commit message. |
| `docs/guide/jira.md` [Tracker-Change] | No | No tracker behavior changes. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | Yes | `docs/guide/work.md` (the `complete` paragraph, line 299): child-qualified form, the refusal of unqualified paths on a node with no ledger, and that a child's working tree is what is read. `docs/guide/taxonomy-and-capabilities.md` (around line 99): the same, briefly, with an example. `docs/guide/multi-repo.md` (near line 348, where cross-node commands are described): a cross-package item on a repository-root board declares its capability changes with child-qualified paths. |
| `docs/release-notes/upcoming.md` [Public-API] | Yes | The new ability, and the **compatibility change**: an active item on a node with no ledger that declares unqualified paths is now refused at completion (`--force` or qualify the paths). Plain language. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | Yes | Added: child-qualified paths, `route_capability_path`. Changed: unqualified paths on a ledgerless node are refused; extends-qualified `removed:` paths are refused; store and registry failures become gate problems; remedy text. Fixed: the gate found a ledger only at `docs/capabilities` (from `2026-09-15-…`, part 1). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | Yes | `skills/capabilities/SKILL.md` schema block (lines 40-50): a child-qualified example, where to run `tcw capabilities add/set/rm` for it, and the ambiguity and `removed:` rules in one sentence each. `skills/work/references/cross-node-deltas.md`: one paragraph pointing at the capabilities skill for how a root-board item declares child capability changes. `skills/work/SKILL.md`: evaluate, expected no change (it does not describe the gate). |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | No | No configuration key is added or changes meaning; `connected-projects.children` is read, not redefined. |

Ledger records (the spec's "Capability changes"):

- `tcw capabilities set work/declare-capability-changes-in-a-child-nodes-ledger --status Supported`.
- Edit the body of `work/complete-a-work-item`: its capability-reconciliation
  paragraph gains the child-qualified form and the refusal of an uncheckable
  path.
- Edit the body of `skills/capabilities` if its text describes the
  `capabilities.yaml` guidance; otherwise leave it and remove it from the
  item's `changed:` list, saying so in the commit.

Proves it (**C21**): `grep -n "kid/\|proposit-shared/\|<child-id>/" skills/capabilities/SKILL.md docs/guide/work.md docs/guide/taxonomy-and-capabilities.md`
finds an example in each, each says where to run `tcw capabilities set`, and
`docs/release-notes/upcoming.md` names the compatibility change. Then run
`tcw validate` and `tcw capabilities check` in the worktree (both clean) and the
full bare `pytest` suite.

## Documentation Sync

Scheduled as Task 8, above, after all code tasks. Fires: the guides (`work.md`,
`taxonomy-and-capabilities.md`, `multi-repo.md`), release notes, changelog,
`skills/capabilities/SKILL.md` and `skills/work/references/cross-node-deltas.md`.
Evaluated and expected not to fire: `README.md`, `skills/work/SKILL.md` (confirm
at Task 8). Does not fire: `docs/guide/jira.md`,
`skills/configure/references/*`.

## Verification

What the suite cannot check:

1. **The reporter's real layout.** In a local checkout of proposit-app (if one is
   on this machine; otherwise say so in `refined-outcome.md`), with the worktree's
   `tcw` on `PATH`: from the repository root, create a scratch item whose
   `capabilities.yaml` names `changed: [proposit-shared/<an existing path>]` and
   `new: [proposit-shared/<a Missing path>]`, and confirm `tcw work complete`
   refuses only the second with the child named, then discard the scratch item
   with `tcw work drop`. Read-only against proposit-app otherwise; nothing is
   committed there. This also confirms the spec's unverified assumption about
   proposit-app's child ids.
2. **Message readability.** Read every new problem line and the new remedy text
   as printed, in one terminal, and check each names the path, the owning child
   and what to do. The suite pins substrings, not whether the sentences read well.
3. **Codex parity.** Nothing here is Claude-specific: the rule is enforced by the
   CLI and the skill change is text. No separate check needed beyond confirming no
   Claude-only syntax was added to `skills/capabilities/SKILL.md`.
4. **Combined review with the rest of the v2.5.1 batch.** Other items filed from
   the proposit-app reports change `tcw/store/fs.py` (the leftover pre-2.5.0 store
   config item changes how `FsCapabilitiesStore.open` treats a legacy
   `.config.yaml`), `tcw/validate.py`, and `tcw/work/cli.py`. This item plans no
   edit to `tcw/store/fs.py` or `tcw/validate.py`; if implementation finds it must
   touch either, say so in the handoff. After the batch lands, review the combined
   diff of `tcw/work/recursion.py`, `tcw/work/cli.py` and `tcw/store/fs.py`.
   Specific interaction to check: any new refusal raised from
   `FsCapabilitiesStore.open` by the legacy-config item reaches this gate as a
   `ValueError` and becomes a problem line (refusing a shipping completion,
   warning on a discard). Confirm that is the intended outcome for a node carrying
   a leftover legacy config, and that its message still reads sensibly after the
   `"{path}: "` prefix.
5. **Restore the environment.** Delete the private venv; the shared editable
   install was never re-pointed, so it needs no restore. Confirm with
   `python -c "import tcw; print(tcw.__file__)"` from the primary checkout.

## Notes

- **Coverage check.** C1: Tasks 2, 5. C2: Task 7. C3-C6: Task 2. C7-C8: Task 4.
  C9-C10: Task 2. C11: Task 1. C12: Tasks 1, 2, 5. C13: Tasks 1, 2. C14: Task 6.
  C15-C16: Task 2. C17: Task 3. C18: Task 2. C19: Task 7. C20: every task.
  C21: Task 8.
- **No blockers recorded.** Part 1 of `2026-09-15-make-the-capability-gate-honor-a-configured-ledger`
  is absorbed here (the lead narrowed that item in `0fbac2ab`); its remaining part
  (unreadable `capabilities.yaml`) touches `FsWorkStore._read_item`, not the gate,
  and does not block this. #30 and #27 do not block it either.
- **Why Task 1 keeps the old pass for one commit.** Flipping the ledgerless
  unqualified case in Task 1 would refuse paths before the child-qualified form
  exists to fix them, so the refusal and its remedy land together in Task 2.
- **`route_capability_path` is public** only so GitHub #27 can reuse it; nothing
  else calls it in this item. If review prefers a leading underscore until #27
  exists, that is a rename, not a design change.
- **Undecided, left to implementation with a stated default:** whether the
  own-store failure produces one problem per declared path (default, matches the
  spec's "every declared path is refused") or one line for the whole file. Tests
  assert that each path is refused, so either passes them; pick the per-path form
  unless it reads badly in Verification step 2.

## Decisions taken on the plan's open points (2026-09-21, autonomous run)

- **Own-store open failure:** one problem line per declared path, as the spec says.
- **`route_capability_path`** stays public; #27's early check is its intended second caller.
- **Interaction with the legacy-config item:** that item reports a leftover
  `config.yaml` / `.config.yaml` from `check()`, and its spec states that a leftover
  never causes a store to fail to open. So nothing it adds reaches this gate as a
  problem line. The combined review of `recursion.py` and `cli.py` with the other
  v2.5.1 items still happens before the release.
- **proposit-app real-layout check:** a checkout exists at
  `/Users/brian/Projects/proposit-orchestration/proposit-app`. Run the check
  read-only, against a copy if it would write.
