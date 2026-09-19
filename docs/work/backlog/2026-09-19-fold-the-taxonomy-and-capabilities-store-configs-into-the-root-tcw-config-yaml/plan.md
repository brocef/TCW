# Plan — Fold the taxonomy and capabilities store configs into the root tcw-config.yaml

> Second draft, against `spec.md`'s second draft. Task 1 no longer invents a
> non-git fallback, task 2's `_node_reserved` edit is reversed, and task 5's
> second half now asserts a refusal instead of a write.

Twelve tasks. Tasks 1–9 are code and tests, ordered so `pytest` is green at
every commit boundary. Tasks 10–12 are the documentation block, one pass at the
end.

The ordering principle: **the shared write helper moves up before anything
depends on it** (task 1), **the read path flips before the write path**
(tasks 2–3, because a write with no reader cannot be asserted), and **the two
cases that carry the spec's named risks get tasks of their own** (task 5) rather
than riding on a default-layout test.

## Task 1 — Hoist the node-config accessors onto `FsTreeStore`

**Files:** `tcw/store/fs.py`

`FsWorkStore` already inherits `FsTreeStore` (`tcw/store/fs.py:3644`) and
overrides only `__init__`, so this is a move, not a new mixin.

1. Move `_config_path` and `_config` (`tcw/store/fs.py:5246-5254`) from
   `FsWorkStore` up to `FsTreeStore`, bodies unchanged. `FsTreeStore.__init__`
   stores `node_root` **unresolved** (`tcw/store/fs.py:1573`) where
   `FsWorkStore` resolves it (`tcw/store/fs.py:3671`), so `_config_path` must
   work with an unresolved path — it already does, being a plain join.
2. Extract the staging half of `_write_tags` (`tcw/store/fs.py:5675-5686`) into
   one `FsTreeStore` method:

   ```python
   def _write_node_config(self, config: dict) -> None:
       """Write the node sentinel and stage it in the *node's* repository."""
   ```

   It reproduces the existing behavior exactly: stage against
   `git_root(config_path.parent)` via `_write_staged(payload, stage_root=...)`,
   and fall back to `_atomic_write_all` when that is `None`. **Do not add a
   caller-side `_require_repository`, and do not remove the one already in
   `_write_tags`** — the fallback is reachable only when the store is in a
   repository and the node is not, and the guard that makes a non-git node
   refuse stays where it is. See task 5.
3. Rewrite `_write_tags` to call `_write_node_config`, keeping
   `self._require_repository()` as its first statement.

**Proves it:** `pytest tests/test_work_tags.py tests/test_non_git_writes.py`
passes unchanged. The second file is the one that catches an accidental
relaxation of the repository guard.

## Task 2 — Read `extends` from the node config

**Files:** `tcw/store/fs.py`

1. Delete `CONFIG_NAME` from `FsTaxonomyStore` (`tcw/store/fs.py:1864`) and
   `FsCapabilitiesStore` (`tcw/store/fs.py:2357`), and the class attribute and
   its use in `FsTreeStore` (`tcw/store/fs.py:1560`, `1575`).
2. In `FsTreeStore.__init__`, set `self.config` to the component's section of
   the node config. It must match `resolve_store` on all three points spec
   Rule 2 names: read through `load_config` (not `load_yaml`), take
   `config.get(self.COMPONENT)`, and normalize a present-but-not-a-mapping
   section to `{}` exactly as `tcw/store/fs.py:3276-3278` does.
3. Update all six `_extends_ids(self.config, self.root / self.CONFIG_NAME)` call
   sites (`tcw/store/fs.py:1878`, `2079`, `2101`, `2371`, `2809`, `2829`) to
   pass a label naming the key — `f"{self._config_path()}: {self.COMPONENT}.extends"` —
   rather than a bare path, per spec Rule 4.
4. **Leave `_node_reserved` (`tcw/store/fs.py:1785-1790`) per-store.** Replace
   the `if self.CONFIG_NAME` branch with a separate class attribute holding the
   store's own former filename — `config.yaml` on `FsTaxonomyStore`,
   `.config.yaml` on `FsCapabilitiesStore` — so each store keeps reserving
   exactly what it reserves today. Comment that it is retained to hold the
   attachment surface still now that nothing writes the file. **Giving both
   stores both names would be a silent regression**: `config.yaml` inside a
   capability folder is an attachment today and must stay one.

**Why the constructor and not `resolve_store`:** `tcw/validate.py:172-174`
constructs a store by calling `_open_at` directly, bypassing `resolve_store`
entirely, so a threaded section would arrive empty there and that store would
resolve no inheritance at all. Spec Rule 2 carries the full reasoning.

**Proves it:** new tests in `tests/test_taxonomy.py` and
`tests/test_capabilities_federation.py` — declare `taxonomy: {extends: [base]}`
(resp. `capabilities:`) in the node's `tcw-config.yaml`, write **no** store
config file, assert the inherited entries list (spec criteria 1, 2). Plus one
asserting a string-valued `taxonomy:` section yields "no configuration" rather
than an `AttributeError`.

**Expected red first:** existing fixtures that write the old files will fail
here. Task 6 fixes them; the two land in one commit — see Notes.

## Task 3 — Write `extends` to the node config

**Files:** `tcw/store/fs.py`

Rewrite `extends_add` / `extends_remove` on both tree stores
(`tcw/store/fs.py:2076-2110`, `2806-2839`). Each one:

1. Keeps `self._require_repository()` as its first statement
   (`tcw/store/fs.py:2077`, `2807`) and every existing validation, in the same
   order with the same messages — the registry lookup, the self-extend refusal,
   the `has no docs/<component>/` check, the duplicate and not-present refusals.
2. Reads the whole node config with `self._config()`, takes or creates the
   component's section as a mapping, sets `section["extends"] = extends` (or
   pops the key when the list is empty, matching today at
   `tcw/store/fs.py:2106-2108`), writes the section back, and calls
   `_write_node_config`.
3. Keeps updating `self.config["extends"]` in memory, for the reason the
   existing comment gives (`tcw/store/fs.py:2092-2093`): a second add/rm in the
   same process must see the first.

Delete the `cfg = self.root / …` lines and their `_write_staged` calls.

**Proves it:** one test per component for spec criterion 3 — after
`extends_add("base")`, `tcw-config.yaml` holds `taxonomy.extends == ["base"]`,
nothing exists at `docs/taxonomy/config.yaml`, and `id`, `work.tags` and
`taxonomy.path` are equal **in parsed value** (not bytes — the file is
re-rendered); after `extends_remove("base")` the key is gone.

## Task 4 — Fix the messages that name a store config file

**Files:** `tcw/taxonomy/cli.py`, `tcw/store/fs.py`

1. Replace the success line of `_extends_add` (`tcw/taxonomy/cli.py:157-158`),
   which hard-codes `docs/taxonomy/config.yaml`:

   ```python
   print(f"Extends project '{args.project_id}' (taxonomy.extends in "
         "tcw-config.yaml). Run `tcw taxonomy check`.")
   ```

   `tcw capabilities extends` prints no path (`tcw/capabilities/cli.py:160-165`)
   and needs none.
2. `_extends_ids`'s fourth refusal, `validate_project_id(v)`
   (`tcw/store/fs.py:1244`), raises naming no path at all. Wrap it so it names
   the key path like the other three (`tcw/store/fs.py:1238-1246`), which task 2
   step 3 already repointed.

**Proves it:** a test asserting the `extends add` output contains
`tcw-config.yaml` and contains neither old filename — including in a fixture
where `taxonomy.path` points elsewhere, which is the already-shipped bug that
line carries (spec sweep finding 1, criterion 8). Plus one asserting each of the
four `_extends_ids` refusals names `taxonomy.extends` (criterion 7).

## Task 5 — The two cases that carry the risk

**Files:** `tests/test_store_provisioning.py`, `tests/test_non_git_writes.py`

No source change. Two fixtures, separated from the ordinary tests because each
guards something that fails silently.

1. **Two repositories.** A node in repository A whose `taxonomy.path` points at
   a tree inside a **separate** git repository B. `extends_add("base")` exits 0;
   A's index holds a staged `tcw-config.yaml`; B's `git status --porcelain` is
   empty (spec criterion 4). `tests/test_store_provisioning.py` already builds
   multi-repository fixtures, including the one at line 2030.
2. **No repository — the refusal stands.** `tests/test_non_git_writes.py`
   already lists all four `extends` commands among those that must exit 1 and
   change nothing (`tests/test_non_git_writes.py:424-431`). **That file must
   pass unedited.** Confirm by running it; if it needs an edit to pass, the
   implementation has relaxed a contract it was not asked to relax, and that is
   a stop-and-report, not a fix-the-test (spec criterion 5).

**Proves it:** spec criteria 4 and 5.

## Task 6 — Migrate the test fixtures

**Files:** `tests/test_capabilities_federation.py` (10 sites),
`tests/test_environment_hardness.py` (4), `tests/test_taxonomy.py` (2),
`tests/test_multiproject.py` (1), `tests/test_store_provisioning.py` (1),
`tests/test_serve.py` (1)

Every fixture that writes `docs/taxonomy/config.yaml` or
`docs/capabilities/.config.yaml` to declare inheritance writes the node-config
key instead — 19 sites, and **only these six files**. A plain grep over `tests/`
returns four more that are *not* store configs and must be left alone:
`test_lifecycle_baseline.py:49`, `test_lifecycle_validation.py:324-328` and
`tests/fixtures/lifecycle_baseline/capture.py:93` name a lifecycle corpus file
called `<case>.config.yaml`, and `test_store_editor.py:1595` is an
`_atomic_write_all` test with an arbitrary temp filename.

**One site inverts rather than moves.** `tests/test_taxonomy.py:758` asserts
`(consumer / "docs/taxonomy/config.yaml").exists()` — it checks that
`extends add` *created* the store file. Its replacement asserts the opposite:
the key is in `tcw-config.yaml` and no file was created under the store. Add one small helper in the test support module
each file already uses rather than repeating a YAML read-modify-write; a fixture
rewritten by hand at two dozen sites is where a silently-passing test comes from
(spec risk 3).

**One site keeps its intent explicitly.**
`tests/test_capabilities_federation.py:441-452` writes `.config.yaml` *without*
going through `extends_add` on purpose — its docstring says the config was
"authored on a machine that had the sibling, then cloned somewhere that does
not". Its replacement must still hand-write the node config key rather than call
`extends_add`, and the docstring must be updated to say so, not deleted.

**Proves it:** the full suite green. Run the named files first, then `pytest`
whole.

## Task 7 — Old files go inert

**Files:** `tcw/store/fs.py`

1. Remove `"config.yaml"` and `".config.yaml"` from `OWNED_YAML_NAMES`
   (`tcw/store/fs.py:1154`) and rewrite the sentence above it that names them
   (`tcw/store/fs.py:1138-1139`), including its stale claim that the work store
   writes a `config.yaml` — it never has (`tcw/store/fs.py:3673`; spec sweep
   finding 3).
2. Delete `_TAX_RESERVED` (`tcw/store/fs.py:1841`) — defined, never read (spec
   sweep finding 2).
3. Remove the config parse from each tree store's `check()`
   (`tcw/store/fs.py:2169-2173`, `2863-2867`) and the now-unused local.

**Do not touch `tcw/validate.py`'s YAML scan.** A malformed leftover must stay
reportable: the scan walks every `*.yaml` under the store roots
(`tcw/validate.py:296-301`) independently of `OWNED_YAML_NAMES`, and only the
mapping-shape check at `tcw/validate.py:304` is gated on that set. That is the
intended outcome, not an oversight.

**Proves it:** a test placing a **well-formed** `extends:\n  - base` at
`docs/taxonomy/config.yaml` (and `docs/capabilities/.config.yaml`) in a node
declaring no `extends`: `list` shows no inherited entries, `check()` and
`tcw validate` say nothing about the file, and it is unmodified afterwards. A
second test placing a **malformed** one and asserting `tcw validate` still
reports it (spec criterion 6, both halves).

## Task 8 — Guard the attachment surface, both sides

**Files:** `tests/test_taxonomy.py`, `tests/test_capabilities.py`

Spec criterion 12, which has two halves that move in opposite directions:

1. A `config.yaml` inside a **term** folder is still **not** among that term's
   attachments.
2. A `config.yaml` inside a **capability** folder still **is** among that
   capability's attachments.

The second is the one that regresses if `_node_reserved` is made to hold both
names on both stores. Write it even though it asserts unchanged behavior; it is
the only thing standing between the change and a silent loss.

**Proves it:** both assertions pass, and the second fails if task 2 step 4 is
done the other way.

## Task 9 — Guard the remaining federation behavior

**Files:** `tests/test_capabilities_federation.py`, `tests/test_taxonomy.py`

1. Transitivity: A extends B, B extends C, each declaring its own
   `taxonomy.extends` in its own `tcw-config.yaml`; `list` in A resolves both
   `B/` and `C/` terms, and a cycle is still reported by `check` (spec
   criterion 9).
2. Two nodes whose `taxonomy.path` points at the **same** folder, declaring
   different `taxonomy.extends`, each resolve their own ancestors (spec
   criterion 10) — the check that Goal 2 landed.
3. The newly reachable state from the spec's "Two consequences" section: A and B
   share a folder and A declares `extends: [B]`. Today this errors on the
   self-extend guard (`tcw/store/fs.py:1339`); afterwards it resolves, with the
   shared terms appearing once locally and once under `B/`. Assert the new
   behavior so it is a decision on record rather than an accident.

**Proves it:** three tests; item 2 fails if `self.config` is ever re-pointed at
the store folder.

## Documentation Sync

Evaluated against `tcw work docs`. One pass over the finished diff, after task 9.

| Entry | Trigger | Fires? |
| --- | --- | --- |
| `README.md` | Public-API | **Evaluate** — task 10 |
| `docs/guide/jira.md` | Tracker-Change | No — nothing about the tracker changes |
| `docs/release-notes/upcoming.md` | Public-API | **Yes** — task 11 |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **Yes** — task 11 |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | **Evaluate** — task 10 |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | **Yes** — task 10 |

### Task 10 — The configuration, guide and skill documents

**Files:** `skills/configure/references/projects.md`,
`skills/configure/references/stores.md`,
`docs/guide/taxonomy-and-capabilities.md`, `docs/guide/multi-repo.md`,
`docs/guide/linking-and-validation.md`, `README.md`,
`skills/taxonomy/SKILL.md`, `skills/capabilities/SKILL.md`

Required rewrites — each says something that becomes false:

- `skills/configure/references/projects.md:88-97` — the `extends` bullet says
  the lists live in the store files and "Neither lives in `tcw-config.yaml`".
  Replace with the two keys, and state that inheritance belongs to the project,
  so two projects sharing one store folder may inherit differently.
- `skills/configure/references/stores.md` — add `extends` to the per-component
  keys shown beside `path` and `repository`, pointing at `projects.md`.
- `docs/guide/taxonomy-and-capabilities.md:50-51` — "writes the registered
  source ID to the `extends` list in `config.yaml`".
- `docs/guide/multi-repo.md:170-174` — the YAML block captioned
  `# docs/taxonomy/config.yaml`.
- `docs/guide/linking-and-validation.md:56-57` — lists "a store's
  `config.yaml`" among the records that must be a mapping. **Factually false
  after task 7**, since that is exactly what leaves `OWNED_YAML_NAMES`.

Evaluate, expect no change, and say so in `outcome.md`:

- `README.md` — its four `extends` mentions (303, 311, 362, 371) are CLI rows
  and examples; the command surface is unchanged and README names no config
  file. Confirm by grepping it.
- `skills/taxonomy/SKILL.md`, `skills/capabilities/SKILL.md` — neither names a
  store config file, and `skills/capabilities/SKILL.md:25` ("`extends` resolves
  against your project, not against wherever the tree sits") becomes more
  literally true. The entry's own description sends configuration wording to
  `configure`, not to the component skill.

**Leave historical documents alone**, per spec Non-goals:
`docs/migration-guide-0.12.X-to-0.13.0.md`, `docs/plan/phase-2-taxonomy.md`,
`docs/plan/phase-3-capabilities.md`, and every shipped changelog and release
note. They record what was true then.

Also update both capability descriptions, which name the old files verbatim —
`taxonomy/federate-shared-vocabulary` and `capabilities/federate`.

**Proves it:** `grep -rn 'config\.yaml' docs/ skills/ README.md | grep -v 'tcw-config'`
returns only the new migration guide and the historical documents named above
(spec criteria 8, 14).

### Task 11 — Migration guide, release notes, changelog

**Files:** `docs/migration-guide-2.X-to-3.0.0.md` (new),
`docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`

`docs/migration-guide-1.X-to-2.0.0.md` is the closest model: it opens by naming
the break and who is unaffected. The guide must state:

1. The break: neither old file is read. A project that never ran
   `tcw taxonomy extends add` or `tcw capabilities extends` has nothing to do —
   which is most projects.
2. What to do: move `extends:` into `taxonomy.extends` / `capabilities.extends`,
   then delete the old file. Show before and after. Note that re-running
   `tcw taxonomy extends add <id>` writes the new key for you.
3. That **nothing warns**. An unmigrated project resolves no inherited entries;
   `tcw taxonomy list` showing only local terms is the symptom.
4. That `tcw taxonomy extends add` **re-renders `tcw-config.yaml`**, dropping
   comments and custom formatting — already true of `tcw work tags add`, now
   true of two more verbs.
5. Both consequences from the spec's "Two consequences of per-project
   inheritance": a shared store folder may now be composed with itself under two
   namespaces where it previously errored, and inside a linked worktree
   `extends` can differ by branch when `<component>.path` escapes the worktree.

Version `3.0.0`: current is `2.4.0` (`pyproject.toml`, `tcw/__init__.py`) and
this removes a supported configuration location. Release notes get the
plain-language version; the changelog a `Removed`/`Changed` pair naming the keys.

**Do not cut the version.** That is a human step.

**Proves it:** the guide exists and covers all five points; both `upcoming.md`
files carry an entry (spec criterion 13).

### Task 12 — Final gate

**Files:** none

`pytest` and `tcw validate` in the primary checkout, both clean (spec criterion
15). Re-run task 10's grep, and spec criterion 11's:
`grep -rn 'config\.yaml' tcw/ --include=*.py | grep -v 'tcw-config'` — expected
**exactly two** matches, the per-store `_node_reserved` literals, plus at most
one comment line justifying them.

## Verification

What the suite cannot check, to be done by hand at `verify`:

1. **The two-repository fixture is really two repositories.** Read it and
   confirm `git init` ran twice and `git_root()` of the two paths differ. A
   single-repo fixture would make task 5.1 assert nothing.
2. **`tests/test_non_git_writes.py` was not edited.** `git diff` it against the
   base. Task 5.2's whole value is that the file passes untouched; an edit there
   is the failure mode, not the fix.
3. **The migration guide works as instructions.** Follow it literally against a
   scratch project holding an old `config.yaml`: does doing what it says restore
   inheritance? No test can ask this.
4. **Task 6 did not neuter a test.** Spot-check three rewritten fixtures by
   breaking the source they cover and confirming they go red — in particular
   `tests/test_capabilities_federation.py:441-452`, whose point is that it
   bypasses `extends_add`.
5. **`tcw validate` on a node holding a well-formed leftover** reports nothing
   new — run it by hand, because "reports no problem naming the file" is easy to
   satisfy by reporting a differently worded problem.

## Notes

- **Tasks 2 and 6 land in one commit.** Task 2 flips the read path, which makes
  every existing fixture that writes an old file fail; task 6 is what fixes
  them. Two tasks because they are two kinds of work; one commit because the
  rule is that the suite is green at every *commit* boundary. Tasks 1, 3, 4, 5,
  7, 8, 9 each commit alone.
- **A gap in this project's own documentation entries, found while planning.**
  Three files that must change in task 10 —
  `docs/guide/taxonomy-and-capabilities.md`, `docs/guide/multi-repo.md`,
  `docs/guide/linking-and-validation.md` — are covered by no entry in
  `work.documentation`; only `docs/guide/jira.md` has one. They are in task 10
  because they would otherwise be wrong, not because a trigger caught them.
  Worth raising at `verify` as a small follow-up to the configuration.
- **Sweep finding 4 is folded into task 1.** `_write_tags`'s docstring claims a
  non-git fallback its own code refutes; it is the direct cause of one of the
  spec's corrections, so it is fixed while that method is being edited rather
  than filed separately.
- **No blockers.** Nothing on the board touches these files, and `extends` is
  independent of the tracker and lifecycle work in flight.
