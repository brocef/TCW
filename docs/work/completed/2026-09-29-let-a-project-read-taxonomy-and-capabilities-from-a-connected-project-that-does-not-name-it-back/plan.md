# Plan — Let a project read taxonomy and capabilities from a connected project that does not name it back

Implements `spec.md` in this folder (after its second review round, `a6ece7d2`).
Every task leaves the suite green at its commit; tests are written first in the
same task and watched fail; each new assertion is mutation-checked
(`docs/lifecycle/implementation.md`). Mutations are undone with an exact reverse
edit on a committed tree, never `git checkout -- <file>`.

New tests go in **`tests/test_upstream_projects.py`**. Fixtures build real git
repositories under `tmp_path` with `tcw.store.fs.init` and write
`connected-projects` explicitly per project — no helper defaults a relation, a
path or a repository entry (the "fixture may not default an axis" rule). Where a
`repository` entry is needed, the fixture makes a local bare repository and
points the entry's `url` at it. `extends` is declared with
`tests/nodeconfig.py`'s `declare_extends`.

## Task 1 — Parse and load `upstream`

**Modifies** `tcw/store/base.py`, `tcw/store/project.py`; **creates**
`tests/test_upstream_projects.py`.

- `ProjectRegistry` (`tcw/store/base.py:191`): add abstract
  `declared_upstream_ids(project_id=None) -> list[str]` and
  `read_only_reason(project_id, from_id=None) -> str | None` (implemented in
  Task 2; declared here so the interface change is one commit).
- `_Config` (`project.py:~147`): add `upstream: dict[str, ConnectedProject]`.
- `_read_config` (`project.py:~480-500`): accept `upstream` beside `parent` and
  `children` in the allowed keys, parsed with `_relation(path, …, "upstream")`.
- `_visit` (`project.py:392-429`): take a `via_upstream: bool` argument. Follow
  each loaded config's `upstream` edges with `via_upstream=True`. A config first
  reached with `via_upstream=True` is cached and recorded in a new
  `self._upstream_only: set[Path]`, and its own edges are **not** followed. If
  the same path is later reached through a `children`/`parent` edge (or is the
  current node), remove it from `_upstream_only` and follow its edges then — so a
  project reached both ways is loaded fully. Parse-level problems in an
  upstream-only config's `connected-projects` block are not recorded: its edges
  are not the reader's to check. Its `id` and file shape still are.
- `declared_upstream_ids` implemented like `declared_child_ids`
  (`project.py:~244`).
- `checkout_of` (`project.py:~290`): also search `upstream` entries.
- Tests (spec criteria 1's loading half, 3's ladder, 7's "not beyond"):
  - an `upstream` entry as a bare path and as a `path` + `repository` mapping
    both load, and `registry.get("core")` finds it;
  - `TCW_PROJECT_CORE` pointing at another copy wins, and a `repository`-only
    entry resolves after the checkout exists;
  - an absent upstream is in `unreachable()` and not in `check()`;
  - core's own child `x` is not in the reader's registry (`get("x") is None`);
  - `declared_upstream_ids` returns the declared ids.

## Task 2 — The write rule and the graph rules

**Modifies** `tcw/store/project.py`, `tcw/cli.py`, `tests/test_upstream_projects.py`.

- `read_only_reason(project_id, from_id=None)`: breadth-first from `from_id`
  (default current) over `parent` and `children` edges as declared by each
  visited config; `None` if `project_id` is reached, else
  `"'<id>' is a read-only upstream project here (reached through '<declarer>')"`,
  where `<declarer>` is a loaded config listing `<id>` under `upstream` (the
  first, in load order). Unknown ids return `None` (existence is the caller's
  concern).
- `_validate_reciprocity` (`project.py:706-749`):
  - skip `upstream` edges, and skip configs in `_upstream_only` entirely;
  - where it would report `child '<id>' is not declared` for a parent claim, first
    check whether any loaded config (full or upstream-only) lists `<id>` under
    `upstream`; if so, record a **warning** (new `self._warnings: list[str]`,
    exposed as `warnings()`) with the spec's wording instead of a problem.
- New graph problems in a `_validate_upstreams()` step called from
  `_load_graph` after reciprocity:
  - self-upstream;
  - for each fully loaded config `d` and each id `u` in `d.upstream`:
    `read_only_reason(u, from_id=d.project.id) is None` → problem, with the
    spec's "declare one or the other" wording.
- Duplicate project id (`project.py:411-415`): when either copy was reached
  through an upstream edge, name both declarers, not only both paths.
- `tcw validate` (`tcw/cli.py:~426-440`): print `warnings()` beside the
  unreachable and misdirected warnings, not failing the run.
- Tests (spec criteria 8, 9's first two states in miniature, 10):
  self-upstream is a problem; upstream that is also child, parent, grandparent,
  sibling → problem; two declarers, same folder → fine; different folders →
  duplicate problem naming both declarers; the migration middle state (parent
  claim answered only by an upstream declaration) → warning, exit 0; the reverse
  → today's nonreciprocal failure; `read_only_reason` from a sibling of the
  declarer and from the declarer's parent → read-only; from the upstream itself →
  `None` for itself. The four named reciprocity tests pass unchanged.

## Task 3 — Reading through an upstream, and provisioning it

**Modifies** `tcw/store/fs.py`, `tests/test_upstream_projects.py`.

- `declared_connected_projects` (`fs.py:3900-3934`): include `upstream` in the
  labels it reads, so `tcw provision` obtains an upstream from its `repository`.
- Expect no change in `_extended_component_stores` (`fs.py:1524-1606`) or the
  taxonomy/capabilities `extends_add` paths: they use `registry.get`. If a test
  shows otherwise, fix it there and record it in `outcome.md`.
- Tests (spec criteria 1, 2, 3):
  - one hop: `extends add core`, `taxonomy list`, `taxonomy show core/<term>`,
    `validate` in `app`; the same for capabilities; `validate` in `core` exits 0
    and its output does not contain `app`;
  - through a parent: a package whose parent declares the upstream resolves
    `extends: [core]` and a `core/<term>` reference;
  - reader-only checkout: `path` absent, `repository` a local bare repo;
    `tcw provision` in `app` obtains it, then the one-hop assertions hold; core's
    config has no `connected-projects`;
  - `TCW_PROJECT_CORE` at a copy with a different term → `taxonomy list` shows it.

## Task 4 — Refusing writes from the CLI

**Modifies** `tcw/store/fs.py`, `tcw/work/cli.py`, `tests/test_upstream_projects.py`.

- In `fs.py`, beside `resolve_qualified_work_ref` (`fs.py:534-616`) and
  `qualified_work_ref_problem` (`fs.py:~620`): add
  `qualified_work_ref_read_only(anchor, ref) -> str | None`, returning the
  registry's `read_only_reason` for the qualifier (or `None` for a bare slug), and
  `resolve_qualified_work_ref_for_write(anchor, ref)`, which returns `None` when
  that is non-`None`. The existing function stays the reading form; its internal
  readers (`fs.py:6021`, `6050`, `6188`, `6231` — blocker and initiative
  resolution) keep it.
- `_resolve(slug, label)` in `tcw/work/cli.py` (lines 132-148) gains
  `write: bool = True`; with `write`, it calls the writing form and prints
  `tcw work <label>: <reason>; run this in <id> itself.` Defaulting to `write`
  makes a caller safe unless it opts out.
- Pass `write=False` from `_show` (1123), `_path` (1195), `_lifecycle` (2399) and
  `stage validate`'s branch of `_stage` (2245). Every other caller — `_start`,
  `_submit`, `_rework`, `_complete`, `_edit`, `_drop`, `_delete`, `_scaffold`,
  `_stage` (gate), `_stage_prompt`, `_procedure_prompt` — keeps the default.
- Tests (spec criteria 4's CLI cases, 5, 6's CLI cases): `start`, `edit
  --title`, `stage gate spec`, `procedure prompt`, each on `core/<slug>` from the
  declarer, from its sibling and from its parent → non-zero, message has
  `read-only` and `core`, not `nonreciprocal`, and `git -C core status
  --porcelain` is empty; `show` and `path` succeed; a `tcw://W/core/<slug>` link
  resolves in `tcw validate`.

## Task 5 — Refusing writes from `tcw serve`

**Modifies** `tcw/serve/__init__.py`, `tests/test_upstream_projects.py`.

- `_resolve_work(slug)` (`serve/__init__.py:499-508`) gains `write: bool`; with
  `write` and `--include-descendants`, it checks `qualified_work_ref_read_only`
  and, when set, the handler answers **403** with a JSON body carrying the reason.
- Every mutating route passes `write=True`: `PATCH /api/work/<slug>` (~1219),
  `POST …/actions/<action>` (~996), `PUT` artifacts, plan-stages and sidecars
  (~1373, ~1411, ~1446), `POST …/artifacts/<name>/open`, and both `DELETE`s
  (~1501, ~1518). `GET`s pass `write=False`. The plan lists them by grepping
  every `_resolve_work(` call in the file, and the test enumerates the same set.
- Tests (criteria 4's serve cases, 6's `GET`): start the server in-process as the
  existing serve tests do (`tests/test_serve_descendants.py`), with
  `--include-descendants`; `PATCH` and `POST …/actions/start` on `core%2F<slug>`
  → 403 with `read-only` in the body and core's git status clean; `GET` → 200.

## Task 6 — `delegate` and `tcw work nodes`

**Modifies** `tcw/work/recursion.py`, `tcw/work/cli.py`, `tests/test_upstream_projects.py`.

- `delegate` (`recursion.py:519-579`): before the final `no child node` refusal
  (line 560), if `registry.read_only_reason(child_ref)` is set, raise with it and
  "delegate writes only into child projects".
- `tcw work nodes` (`_nodes`, `work/cli.py:~250-285`): after the existing
  sections, print `upstream (read-only):` with one line per upstream declared by
  the current node or an ancestor — id, declarer, location or `unreachable`.
  Omitted when there are none, so existing output is unchanged.
- Tests (criteria 4's `delegate`, 7): `delegate core …` refused with
  `read-only`; `nodes` from the declarer and from a package below it lists core
  under the new heading; core absent from `list --include-descendants`,
  `validate`'s per-node recursion output, `reconcile` of an epic, and serve's
  board.

## Task 7 — The tracker hint for a project with no parent

**Modifies** `tcw/store/fs.py`, `tests/test_upstream_projects.py`.

- `_resolved_tracker` (`fs.py:6614-6660`): when the merged block has problems,
  the node's own block is non-empty, and the registry has no declared parent for
  the current node, append the spec's "no parent to inherit work.tracker settings
  from" line, beside the existing "declared parent … is not reachable" line.
- Test (criterion 9, third part): a standalone project with only
  `work.tracker.candidate-query` → `validate` exits 1 and shows the new line; with
  a parent that supplies the rest → no line.

## Task 8 — The Proposit shape, end to end

**Modifies** `tests/test_upstream_projects.py`.

- One test builds the Proposit shape — root (orchestration) with child
  `app-repo`; `app-repo` with child `shared` declaring `taxonomy: extends:
  [core]`; `core` a child of the root naming it as parent, holding one term and a
  tracker block with only `candidate-query` inherited from the root — and walks the
  spec's migration steps 1, 2, 4 (tracker block removed) and 5, asserting after
  each: `tcw validate` exit code and warning in each of the four projects, and
  `tcw taxonomy show core/<term>` in `shared`.
- It also asserts the forbidden middle state (step 2 applied before step 1) is
  the "also writable" problem.

**Proves:** criterion 9.

## Task 9 — Documentation Sync

One pass over the finished diff; each trigger evaluated.

- **Configuration-Key-Change** fires (`connected-projects.upstream` is a new
  key): `skills/configure/references/projects.md` — lines 30-40 say every
  connection is declared from both sides; add the `upstream` relation, its
  read-only rule, and the migration relaxation.
- **Guide-Topic-Change** fires: `docs/guide/multi-repo.md` (line 21 "only
  reciprocal registrations", and the connected-projects sections) and
  `docs/guide/taxonomy-and-capabilities.md` (the `extends` sections, 37-54 and
  135-145).
- **Skill-Driven-Component** fires for `skills/work` if its cross-node reference
  (`skills/work/references/cross-node-deltas.md`) describes where `delegate`
  and qualified references reach — checked and updated if so; and for
  `skills/taxonomy` / `skills/capabilities` where they describe `extends`.
- **Public-API** fires: `README.md` where it describes connected projects, and
  `docs/release-notes/upcoming/<slug>.md`.
- **Any-Code-Change**: `docs/changelogs/upcoming/<slug>.md`.
- **Tracker-Change**: fires only for the Task 7 hint — a sentence in
  `docs/guide/jira.md` where it describes inheriting tracker settings from a
  parent.
- **Capabilities and taxonomy**: add the Vocabulary term **upstream project**
  with `tcw taxonomy add`; add `cli/read-from-an-upstream-project` with `tcw
  capabilities add`; edit the seven changed descriptions named in the spec,
  including `docs/capabilities/cli/validate-a-node/description.md:7`; declare
  them in this item's `capabilities.yaml` (`new:` and `changed:`).
- Final grep: no remaining statement that every connection is two-way
  (`grep -rn "both sides\|reciprocal" docs/guide skills README.md`), each hit
  read and either updated or confirmed still true for `parent`/`children`.

## Task 10 — Full suite

Bare `pytest` from the repository root, as CI runs it. **Proves:** criterion 11.

## Verification

Beyond the suite:

- **The real configs.** Copy (never edit) the six Proposit `tcw-config.yaml`
  files into a scratch tree with the same relative layout, add one taxonomy term
  to the copy of core, and apply the spec's migration steps 1–5 by hand to the
  copies. After each step, run `tcw validate` in all six and `tcw taxonomy show
  proposit-core/<term>` in the three packages, and read the output. Also run
  `tcw work nodes` in `proposit-shared`.
- **The public-clone case.** In a scratch clone holding only the `proposit-app`
  copy, with core reachable only by its `repository` entry (a local bare repo),
  run `tcw provision` and then `tcw taxonomy list` in `proposit-shared`.
- **serve by hand.** Start `tcw serve --include-descendants` in the scratch root
  and try a `PATCH` on `proposit-core%2F<slug>` with `curl`; read the 403 body.

## Notes

- Risk ordering: Task 1's loading change touches every command's graph load, so
  it lands first with the whole suite run at its commit, before anything builds
  on it. Task 2's rules are next, for the same reason.
- `resolve_qualified_work_ref`'s internal readers in `fs.py` are left on the
  reading form deliberately: they resolve blockers and initiatives, which is
  reading.
- Worktree: implemented in `.worktrees/<slug>` on `work/<slug>`, run through a
  private virtual environment pinned to the worktree, as the previous item was.
