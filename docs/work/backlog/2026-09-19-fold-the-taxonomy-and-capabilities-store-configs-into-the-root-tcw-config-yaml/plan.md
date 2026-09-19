# Plan — Fold the taxonomy and capabilities store configs into the root tcw-config.yaml

Eleven tasks. Tasks 1–8 are code and tests, ordered so `pytest` is green at
every commit boundary. Tasks 9–11 are the documentation block, scheduled as one
pass at the end.

The ordering principle: **the shared write helper moves up before anything
depends on it** (task 1), **the read path flips before the write path** (tasks
2–3, because a write with no reader cannot be asserted), and **the
two-repository case gets its own task** (task 5) rather than riding on a
same-repo test, because that is the spec's named risk.

## Task 1 — Move the node-config accessors onto `FsTreeStore`

**Files:** `tcw/store/fs.py`

Move `_config_path` and `_config` (`tcw/store/fs.py:5246-5252`) from
`FsWorkStore` up to `FsTreeStore`, unchanged in body. Add one sibling helper on
`FsTreeStore` that does the node-repository write — the staging half of
`_write_tags` (`tcw/store/fs.py:5657-5686`), extracted so both the tag registry
and the two `extends` writers call one implementation:

```python
def _write_node_config(self, config: dict) -> None:
    """Write the node sentinel and stage it in the *node's* repository."""
```

It must reproduce `_write_tags`'s two behaviors exactly: stage against
`git_root(config_path.parent)` via `_write_staged(payload, stage_root=...)`, and
fall back to `_atomic_write_all` when that is `None` so a node outside git
writes rather than fails. Rewrite `_write_tags` to call it, keeping
`_require_repository()` where it already is.

**Proves it:** `pytest tests/test_work_tags.py` passes unchanged — the refactor
is behavior-preserving, and that file is the existing coverage for the extracted
code. No new test here; tasks 3–5 are what exercise the new caller.

**Why first:** every later task calls this, and doing it alone keeps the
refactor diff separable from the behavior change.

## Task 2 — Read `extends` from the node config

**Files:** `tcw/store/fs.py`

1. Delete `CONFIG_NAME` from `FsTaxonomyStore` (`tcw/store/fs.py:1864`) and
   `FsCapabilitiesStore` (`tcw/store/fs.py:2357`), and the `CONFIG_NAME`
   class attribute and its use in `FsTreeStore.__init__`
   (`tcw/store/fs.py:1560`, `1575`).
2. In `FsTreeStore.__init__`, set `self.config` to the component's section of
   the node config: read `node_root / SENTINEL` through `load_config`, take
   `config.get(self.COMPONENT)`, and use `{}` when it is absent or not a
   mapping. Absent file already yields `{}` from `load_yaml`, so a store opened
   in a directory with no config still constructs.
3. Update all six `_extends_ids(self.config, self.root / self.CONFIG_NAME)`
   call sites (`tcw/store/fs.py:1878`, `2079`, `2101`, `2371`, `2809`, `2829`)
   to pass `self._config_path()` as the path used in error messages.
4. In `FsTreeStore._node_reserved` (`tcw/store/fs.py:1785-1790`), replace the
   `if self.CONFIG_NAME` branch with the two literals
   `{"config.yaml", ".config.yaml"}`, and comment that they are kept so the
   attachment surface does not change now that nothing writes them.

**Decision, resolving the spec's open question:** re-read in the constructor;
do **not** thread the section down from `resolve_store`. `FsTreeStore.__init__`
is reached directly from tests and from `_extended_component_stores`, which
builds a sibling project's store, so a parameter would have to be supplied
correctly at every one of those call sites or silently default to "no
inheritance". Re-reading is one `load_config` of a small file, already cached by
the OS, and `resolve_store` (`tcw/store/fs.py:3274`) has already proved the file
parses by the time any store is constructed through it.

**Proves it:** a new test in `tests/test_taxonomy.py` and one in
`tests/test_capabilities_federation.py`: write `taxonomy: {extends: [base]}`
(resp. `capabilities: {extends: [base]}`) into the node's `tcw-config.yaml`,
write **no** store config file, and assert `tcw taxonomy list` / `tcw capabilities list`
shows the inherited entries. These are spec criteria 1 and 2.

**Expected red first:** the existing federation tests that write the old files
directly will fail at this point. That is correct and task 6 fixes them; this
task and task 6 land in one commit if the suite must be green at the boundary —
see Notes.

## Task 3 — Write `extends` to the node config

**Files:** `tcw/store/fs.py`

Rewrite `extends_add` / `extends_remove` on both tree stores
(`tcw/store/fs.py:2076-2110` and `2809-2838`). Each one now:

1. Keeps `_require_repository()` and every existing validation, in the same
   order and with the same messages — the registry lookup, the self-extend
   refusal, the `has no docs/<component>/` check, the duplicate and
   not-present refusals.
2. Reads the whole node config with `self._config()`, takes or creates the
   component's section as a mapping, sets `section["extends"] = extends` (or
   pops the key when the list is empty, matching today's behavior at
   `tcw/store/fs.py:2106-2108`), writes the section back onto the config, and
   calls `_write_node_config`.
3. Keeps updating `self.config["extends"]` in memory, for the reason the
   existing comment gives (`tcw/store/fs.py:2092-2093`): a second add/rm in the
   same process must see the first.

Delete the `cfg = self.root / "config.yaml"` / `self.root / self.CONFIG_NAME`
lines and their `_write_staged` calls.

**Proves it:** a new test per component asserting spec criterion 3 — after
`extends_add("base")`, `tcw-config.yaml` holds `taxonomy.extends == ["base"]`,
no file exists at `docs/taxonomy/config.yaml`, and pre-existing keys (`id`,
`work.tags`, `taxonomy.path`) still hold their original **values**; after
`extends_remove("base")` the key is gone.

## Task 4 — Fix the messages that name a store config file

**Files:** `tcw/taxonomy/cli.py`

Replace the success line of `_extends_add` (`tcw/taxonomy/cli.py:157-158`),
which hard-codes `docs/taxonomy/config.yaml`. The replacement names the key, not
a path:

```python
print(f"Extends project '{args.project_id}' (taxonomy.extends in "
      "tcw-config.yaml). Run `tcw taxonomy check`.")
```

`tcw capabilities extends` prints no path (`tcw/capabilities/cli.py:160-165`)
and needs no change. `_extends_ids`'s three refusals already interpolate the
`config_path` they are handed, which task 2 step 3 repointed, so they need no
edit here.

**Proves it:** a test asserting the `extends add` output contains
`tcw-config.yaml` and contains neither `docs/taxonomy/config.yaml` nor
`.config.yaml` — including in a fixture where `taxonomy.path` points elsewhere,
which is the already-shipped bug this line carries (spec sweep finding 1, spec
criterion 8).

## Task 5 — The two-repository write, and the no-git node

**Files:** `tests/test_store_provisioning.py`

No source change; this task is the test for task 1's `stage_root` half, isolated
because it is the spec's named risk and the bug `tcw work tags add` already
shipped (`tcw/store/fs.py:5660-5666`).

1. Build a node in repository A whose `taxonomy.path` points at a tree inside a
   **separate** git repository B. Run `extends_add("base")`. Assert it does not
   raise, that A's index holds a staged `tcw-config.yaml`, and that B's
   `git status --porcelain` is empty.
2. Build a node that is not a git repository at all. Assert `extends_add`
   writes the key and does not raise.

`tests/test_store_provisioning.py` is the right home: it already builds
multi-repository fixtures, including the one at line 2030 that writes a
`.config.yaml` by hand.

**Proves it:** spec criteria 4 and 5.

## Task 6 — Migrate the test fixtures

**Files:** `tests/test_capabilities_federation.py`, `tests/test_multiproject.py`,
`tests/test_environment_hardness.py`, `tests/test_serve.py`,
`tests/test_store_provisioning.py`, `tests/test_taxonomy.py`,
`tests/fixtures/lifecycle_baseline/capture.py`

Every fixture that writes `docs/taxonomy/config.yaml` or
`docs/capabilities/.config.yaml` to declare inheritance writes the node-config
key instead. Add one small helper in the test support module each file already
uses rather than repeating the YAML read-modify-write; a fixture rewritten by
hand at twenty-odd sites is where a silently-passing test comes from (spec
risk 3).

**One site keeps its intent explicitly.** `tests/test_capabilities_federation.py:443-451`
writes `.config.yaml` *without* going through `extends_add` on purpose — its
docstring says so — to exercise the read path against a hand-written
declaration. Its replacement must still hand-write the node config key rather
than call `extends_add`, and the docstring must be updated to say that, not
deleted.

**Proves it:** the full suite is green. Run
`pytest tests/test_capabilities_federation.py tests/test_taxonomy.py tests/test_multiproject.py tests/test_environment_hardness.py tests/test_serve.py tests/test_store_provisioning.py`
and then `pytest` whole.

## Task 7 — Old files go inert

**Files:** `tcw/store/fs.py`

1. Remove `"config.yaml"` and `".config.yaml"` from `OWNED_YAML_NAMES`
   (`tcw/store/fs.py:1154`) and rewrite the sentence above it that names them
   (`tcw/store/fs.py:1138-1139`) — including its stale claim that the work store
   writes a `config.yaml`, which it never has (spec sweep finding 3;
   `FsWorkStore` sets `self.config = {}` at `tcw/store/fs.py:3673`).
2. Delete `_TAX_RESERVED` (`tcw/store/fs.py:1841`) — defined, never read (spec
   sweep finding 2).
3. Remove the config parse from each tree store's `check()`
   (`tcw/store/fs.py:2169-2173` and `2863-2867`), and the now-unused local.

**Proves it:** a new test placing `extends:\n  - base` at
`docs/taxonomy/config.yaml` (and `docs/capabilities/.config.yaml`) in a node
whose `tcw-config.yaml` declares no `extends`, asserting that `list` shows no
inherited entries, that `check()` and `tcw validate` return no problem naming
the file, and that the file is still present and byte-identical afterwards
(spec criterion 6). Plus a test that a `config.yaml` inside a *term* folder is
still absent from that term's attachments (spec criterion 12).

## Task 8 — Guard the remaining behavior

**Files:** `tests/test_capabilities_federation.py`, `tests/test_taxonomy.py`

Tests for the three things the move must not have changed:

1. `taxonomy.extends` holding a mapping is refused with
   `legacy extends map is unsupported`, and the message names
   `tcw-config.yaml`. A non-list, a non-string member and a duplicate ID are
   each refused as before (spec criterion 7).
2. Transitivity: A extends B, B extends C, each declaring its own
   `taxonomy.extends` in its own `tcw-config.yaml`; `list` in A resolves both
   `B/` and `C/` terms, and a cycle is still reported by `check` (spec
   criterion 9).
3. Two nodes whose `taxonomy.path` points at the **same** folder, declaring
   different `taxonomy.extends`, each resolve their own ancestors (spec
   criterion 10) — the check that Goal 2 actually landed.

**Proves it:** these three tests pass, and item 3 fails if `self.config` is ever
re-pointed at the store folder.

## Documentation Sync

Evaluated against `tcw work docs`. One pass over the finished diff, after task 8.

| Entry | Trigger | Fires? |
| --- | --- | --- |
| `README.md` | Public-API | **Evaluate** — task 9 |
| `docs/guide/jira.md` | Tracker-Change | No — nothing about the tracker changes |
| `docs/release-notes/upcoming.md` | Public-API | **Yes** — task 10 |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **Yes** — task 10 |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | **Evaluate** — task 9 |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | **Yes** — task 9 |

### Task 9 — The configuration and skill documents

**Files:** `skills/configure/references/projects.md`,
`skills/configure/references/stores.md`, `README.md`,
`skills/taxonomy/SKILL.md`, `skills/capabilities/SKILL.md`,
`docs/guide/taxonomy-and-capabilities.md`, `docs/guide/multi-repo.md`,
`docs/guide/linking-and-validation.md`

Required rewrites — each of these says something that becomes false:

- `skills/configure/references/projects.md:88-97` — the `extends` bullet says
  the lists live in the store files and "Neither lives in `tcw-config.yaml`".
  Replace with `taxonomy.extends` / `capabilities.extends`, and state the
  shared-store consequence: inheritance belongs to the project, so two projects
  sharing one store folder may inherit differently.
- `skills/configure/references/stores.md` — add `extends` to the per-component
  keys shown beside `path` and `repository`, pointing at `projects.md` for what
  it means.
- `docs/guide/taxonomy-and-capabilities.md:50-51` — "writes the registered
  source ID to the `extends` list in `config.yaml`".
- `docs/guide/multi-repo.md:170-174` — the YAML block is captioned
  `# docs/taxonomy/config.yaml`.
- `docs/guide/linking-and-validation.md:56-57` — lists "a store's
  `config.yaml`" among the records that must be a mapping; that is no longer
  one of them.

Evaluate, expected no change, but check and say so in `outcome.md`:

- `README.md` — its four `extends` mentions (lines 303, 311, 362, 371) are CLI
  rows and examples; the command surface is unchanged and README names no
  config file. Confirm by grepping it for `config.yaml`.
- `skills/taxonomy/SKILL.md` and `skills/capabilities/SKILL.md` — neither names
  a store config file, and `skills/capabilities/SKILL.md:25`
  ("`extends` resolves against your project, not against wherever the tree
  sits") becomes more literally true, not less. The entry's own description
  sends configuration wording to `configure`, not to the component skill.

Also update both capability descriptions, which name the old files verbatim:
`tcw capabilities show taxonomy/federate-shared-vocabulary` and
`capabilities/federate`.

**Proves it:** `grep -rn 'config\.yaml' docs/ skills/ README.md | grep -v 'tcw-config'` returns
only the new migration guide (spec criteria 8, 14).

### Task 10 — Migration guide, release notes, changelog

**Files:** `docs/migration-guide-2.X-to-3.0.0.md` (new),
`docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`

The guide follows the six existing ones in shape — `docs/migration-guide-1.X-to-2.0.0.md`
is the closest model: it opens by naming the break and who is unaffected. It
must state:

1. The break: `docs/taxonomy/config.yaml` and `docs/capabilities/.config.yaml`
   are no longer read. A project that never ran `tcw taxonomy extends add` or
   `tcw capabilities extends` has nothing to do — which is most projects.
2. What to do: move `extends:` from each file into `taxonomy.extends` /
   `capabilities.extends` in `tcw-config.yaml`, then delete the old file.
   Show both before and after. Note that `tcw taxonomy extends add <id>` run
   again writes the new key for you.
3. That **nothing warns**. An unmigrated project silently resolves no inherited
   entries; `tcw taxonomy list` showing only local terms is the symptom.
4. The shared-store consequence: inheritance now belongs to the project, so a
   store folder shared by two projects no longer imposes its ancestors on both,
   and each project must declare its own.

The version is `3.0.0`: the current version is `2.4.0` (`pyproject.toml`,
`tcw/__init__.py`) and this removes a supported configuration location.
Release notes get the plain-language version, the changelog a `Removed`/
`Changed` pair naming the keys.

**Do not cut the version.** That is a human step; entries accumulate in
`upcoming.md` until asked for.

**Proves it:** the guide exists and covers all four points; both `upcoming.md`
files carry an entry (spec criterion 13).

### Task 11 — Final gate

**Files:** none

Run `pytest` and `tcw validate` in the primary checkout. Both must be clean —
spec criterion 15. Re-run the grep from task 9 and the one from spec
criterion 11 (`grep -rn 'config\.yaml' tcw/ --include=*.py | grep -v 'tcw-config'`,
expected: only the two literals in `_node_reserved`).

## Verification

What the suite cannot check, to be done by hand at `verify`:

1. **The two-repository fixture is really two repositories.** Task 5 passes
   trivially if the fixture accidentally puts both trees in one repo — a staged
   `tcw-config.yaml` would then show up in the "store" repo too and the
   assertion that it is empty would fail, so this one does fail loudly. Confirm
   by reading the fixture that `git init` was called twice and that
   `git_root()` of the two paths differ.
2. **The migration guide is correct as instructions**, not just present. Follow
   it literally against a scratch project that has an old `config.yaml`: does
   doing what it says restore inheritance? No test can ask this.
3. **Task 6 did not neuter a test.** Spot-check three rewritten fixtures by
   breaking the source they cover and confirming they go red. Named in
   particular: the `tests/test_capabilities_federation.py:443-451` site, whose
   whole point is that it bypasses `extends_add`.
4. **`tcw validate` on a node holding a leftover old file** reports nothing
   about that file and nothing new — run it once by hand on a scratch node,
   because "reports no problem naming the file" is easy to satisfy by reporting
   a differently worded problem.

## Notes

- **Tasks 2 and 6 land in one commit.** Task 2 flips the read path, which makes
  every existing fixture that writes an old file fail; task 6 is what fixes
  them. Kept as two tasks because they are two different kinds of work, but the
  suite is only green once both are done, and the plan's rule is that the suite
  is green at every *commit* boundary. Tasks 1, 3, 4, 5, 7, 8 each commit alone.
- **A gap in this project's own documentation entries, found while planning.**
  Three files that must change in task 9 —
  `docs/guide/taxonomy-and-capabilities.md`, `docs/guide/multi-repo.md`,
  `docs/guide/linking-and-validation.md` — are covered by no entry in
  `work.documentation`; only `docs/guide/jira.md` has one. They are in task 9
  because they would otherwise be wrong, not because a trigger caught them.
  Worth raising at `verify` as a small follow-up to the configuration rather
  than a separate item.
- **No blockers.** Nothing on the board touches these files, and `extends` is
  independent of the tracker and lifecycle work currently in flight.
- The spec left the read-path mechanism open; task 2 closes it and gives the
  reason. If the reviewer disagrees, that is a spec question, not a plan one.
