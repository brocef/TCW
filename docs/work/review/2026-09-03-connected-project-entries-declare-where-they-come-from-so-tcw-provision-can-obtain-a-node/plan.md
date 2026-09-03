# Plan — Connected-project entries declare where they come from

Depends on [Unreachable connected projects degrade](tcw://W/2026-09-03-unreachable-connected-projects-degrade-instead-of-failing-every-command),
recorded as a blocker on the item. Without it, task 3's third ladder rung has
nowhere to fall to and every declared-but-unprovisioned node still fails every
command.

## Tasks

### 1. Accept a mapping form for a connected-projects entry

**Modifies** `tcw/store/project.py`.

Introduce a parsed entry type — declared id, locator string or `None`, and an
optional `RepositoryDeclaration` — and have `_relation` (`:294-312`) produce it
for both forms. A bare string keeps producing a locator-only entry. A mapping
accepts `path` and `repository` and nothing else; an unknown key, a mapping with
neither, and a non-string `path` are problems in the existing style.

`repository` is parsed by `parse_repository_declaration`
(`tcw/store/base.py:1191`) with `where` =
`connected-projects.<relation>.<id>.repository`, so its messages and its
fail-closed behavior are inherited rather than reimplemented. Its problems are
appended to the registry's error list, not the unreachable list — a malformed
declaration is present and wrong.

`_Config.parent` / `.children` change type from `dict[str, str]` to a mapping of
id to the new entry; `_visit` (`:209`) and `_validate_reciprocity` (`:349`) are
updated to read `.locator` where they read the string today.

**Proves it:** `tests/test_project_registry.py` — a bare-string entry and an
equivalent `{path: ...}` mapping produce identical graphs; a mapping with an
unknown key, an empty mapping, and a malformed `repository` each report their own
message and raise from `require_valid()`.

### 2. Give a node a resolution ladder

**Modifies** `tcw/store/project.py`, `tcw/store/fs.py`.

`_target_path` (`:313`) takes the parsed entry instead of a string and applies:
locator when a sentinel is present there; else the provisioned checkout when a
sentinel is present there; else the locator unchanged, so the existing
unreachable path reports it.

The provisioned location is `checkout_root(node_root, declaration)` joined with
`declaration.path` — the same computation `provisioned_store_root`
(`tcw/store/fs.py:2703`) performs for a store. Extract that join into one
function both call, so a node and a store can never disagree about where a
declared thing lands. `tcw/store/project.py` may not import `tcw/store/fs.py` —
`fs` imports `project` (`tcw/store/project.py:57-63` records the same
constraint for `worktree_anchors`) — so the shared helper lives in
`tcw/store/base.py` beside `RepositoryDeclaration`, which is where the pure
`(url, ref) → directory name` logic belongs anyway.

The worktree re-anchoring rules in `_target_path` apply to the locator rung only;
leave their comments intact and note in one line that a declaration is not an
offset from anything.

**Proves it:** `tests/test_project_registry.py` — with a sentinel at the locator
the declaration is not consulted (assert by pointing it at a url no test could
reach); with no sentinel at the locator but one at the computed checkout path,
the node resolves; with neither, it is unreachable and the recorded entry names
the declared url.

### 3. Report a declared-but-unprovisioned node by name

**Modifies** `tcw/store/project.py`, `tcw/store/fs.py`.

The blocking item's unreachable record grows a declaration field, so the three
message sites it updated (`_extended_component_roots`,
`resolve_qualified_work_ref` / `qualified_work_ref_problem`,
`registered_project_id`) can say the node is declared in `<url>` and has not been
provisioned here, and name `tcw provision` — the wording `StoreNotProvisioned`
already uses (`tcw/store/fs.py:2827-2831`). An unreachable node with no
declaration keeps the blocking item's wording.

**Proves it:** `tests/test_capabilities_federation.py` and
`tests/test_qualified_ref.py` — a declared, unprovisioned node produces the
`run tcw provision` wording; an undeclared absent node does not.

### 4. Read node declarations for provisioning

**Modifies** `tcw/store/fs.py`.

`declared_repository` (`:2833`) reads `<component>.repository`. Add the node
counterpart: given a node root, return the declared connected projects that are
not present here, each as (id, declaration), plus any parse problems. It reads
the config directly for the same reason `declared_repository` does — it must
answer for a graph that cannot be fully loaded.

**Proves it:** `tests/test_repo_lifecycle.py` — a node declaring two connected
projects, one present and one not, returns only the absent one; a malformed
declaration returns a problem rather than an entry.

### 5. Provision nodes, transitively

**Modifies** `tcw/cli.py`.

`run_provision` (`:90-153`) gains a node pass after its component pass. Work a
queue: for the current node, obtain each declared-and-absent connected project
with `FsStoreProvisioner`; for each node obtained, read its own declarations and
enqueue them. Dedupe on `(url, ref)` and on the resolved checkout path, which is
already the working-copy cache key (`tcw/store/fs.py:2629-2650`), so one copy
serves every reference and a cycle terminates.

Each node is resolved, reported and failed on its own, exactly as components are,
so one bad declaration does not suppress another's result. Every remote is
printed before it is contacted, transitive ones included. `--dry-run` walks the
same queue and contacts nothing — for a node not yet obtained it reports that its
own declarations cannot be read until it is, rather than guessing.

`--refresh` covers nodes: a provisioned node's checkout goes stale exactly as a
store's does.

**Proves it:** `tests/test_repo_lifecycle.py` — against local git repositories on
disk, not a network: A declares B, B declares C; one `tcw provision` obtains both
and `tcw work nodes` sees them. `--dry-run` first lists A→B and says C is behind
an unobtained node. A second run reports everything already available and creates
no new working copy. Two entries naming one `(url, ref)` produce one directory.

### 6. Refuse a `checkout` holding something else

**Modifies** nothing if `_require_declared_checkout` already covers it; otherwise
`tcw/store/fs.py`.

Confirm the node path goes through the same guard a store does before any fetch
or write. This is a read-and-assert task, not a change: if the guard is already
on the shared code path, the task is the test.

**Proves it:** `tests/test_repo_lifecycle.py` — a node declaration whose
`checkout` directory holds an unrelated repository is refused before contacting
anything, and the directory is left untouched.

### 7. Decide the transitive-trust question

**Modifies** `tcw/cli.py` and, if the decision requires it, the messages in
task 5.

The spec's first risk: a configuration in a repository the user chose can name a
repository they did not. Decide between reporting only (every url printed before
contact, `--dry-run` shows the full plan) and requiring something stronger for a
url discovered inside a node that was itself just obtained. Record the decision
and its reasoning in a comment at the queue, because the next reader will
otherwise assume nobody thought about it.

Do not invent a consent prompt: `tcw` commands are non-interactive by design and
a prompt would break every script that calls `tcw provision`. If reporting is
judged insufficient, the shape is a flag that bounds the walk, defaulting to
whichever behavior the decision picks.

**Proves it:** `tests/test_repo_lifecycle.py` — whichever behavior is chosen,
asserted directly, plus the printed-before-contacted ordering for a transitive
url.

### 8. Documentation Sync

One pass over the finished diff, answering every entry whose trigger fired.

- **`README.md`** — [Public-API]. Fires. The "To keep a project's work in another
  Git repository" section (`README.md:201-260`) documents the `repository` block
  per component; it gains the connected-projects form and the transitive
  provisioning rule. The Connected projects section (`:330-345`) gains the entry
  shape. Say plainly that declarations follow the graph.
- **`docs/release-notes/upcoming.md`** — [Public-API]. Fires. Plain language: you
  can say where a connected project comes from, and `tcw provision` fetches it,
  including projects the first one points at.
- **`docs/changelogs/upcoming.md`** — [Any-Code-Change]. Fires. Added: the entry
  mapping form, node provisioning, the node pass in `run_provision`. Changed:
  `_relation`, `_target_path`, `declared_repository`'s node counterpart.
- **`skills/<component>/SKILL.md`** — [Skill-Driven-Component]. Fires for
  `tcw-work`: `references/commands.md` documents `tcw provision` and states that
  `--component` "currently accepts only `work`" and that "nothing else reaches
  the network". Both sentences move. Check `tcw-capabilities` and `tcw-taxonomy`
  for `extends` wording that assumes a sibling is always on disk.
- **`docs/capabilities/cli/declare-a-connected-projects-home-repository/`** —
  seeded `Missing` at planning (`cap-596612`); flip it to `Supported` at
  completion, not before.
- **`docs/capabilities/cli/provision-declared-stores/`** and
  **`.../host-multiple-projects-in-one-repo/`** — both recorded as changed in
  `capabilities.yaml`. The second is also edited by the blocking item; read that
  edit before writing this one.

## Verification

What the suite cannot check:

- **The real graph.** After implementing, run `tcw provision` then `tcw validate`
  and `tcw work nodes` in `apps/server` of a `proposit-app` checkout with no
  other repository present, and paste the output into `outcome.md`. The
  session-validated arrangement in `intake.md` is the expected end state; the
  fixtures cannot reproduce configurations written by someone else months ago.
- **What a user sees before a network call.** Read the actual terminal output of
  `tcw provision` and `--dry-run` on a two-hop graph. Ordering and wording are
  the entire mitigation for the transitive-trust risk, and no assertion proves
  they read clearly.
- **That nothing else reaches the network.** Run the full suite with outbound
  network unavailable and confirm no test that is not about provisioning
  attempts a fetch — the invariant the ledger promises, checked rather than
  assumed.

## Notes

Order keeps the tree green at every boundary: 1 changes a type behind unchanged
behavior, 2 adds a rung nothing yet populates, 3 improves a message, 4 adds an
unused reader, 5 is the first task that contacts anything, 6-7 harden it.

Task 2 carries the one structural constraint worth flagging early: `project.py`
cannot import `fs.py`, so the shared checkout-path computation has to move to
`base.py`. Discovering that during task 5 instead would mean redoing task 2.
