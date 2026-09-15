# Plan — Override where a connected project lives on this machine

Eight tasks. Tasks 1–2 add the pieces Task 3 stands on; Task 3 is the one that
changes resolution and is deliberately isolated behind them. Tasks 4–6 are
reporting and coverage, Task 7 the capability record, Task 8 the documentation
pass. The suite is green at every boundary.

## Task 1 — The variable name, and proof the mapping cannot collide

**Modifies** `tcw/store/project.py`, `tests/conftest.py`,
`tests/test_project_registry.py`.

Add one module-level helper beside `validate_project_id`:

```python
def override_variable(project_id: str) -> str:
    """The environment variable that overrides where `project_id` lives here."""
    return "TCW_PROJECT_" + project_id.upper().replace("-", "_")
```

Nothing calls it yet; it exists so Task 3 and its tests name the mapping in one
place rather than each spelling it out.

Add an autouse fixture to `tests/conftest.py` that deletes every `TCW_PROJECT_*`
key from `os.environ` for the duration of a test. **This is not optional
tidiness.** The suite otherwise reads the developer's shell, and criterion 8 —
"no variable set changes nothing" — is unprovable in a process that cannot say
whether a variable is set. It belongs in `conftest.py` beside the other
suite-wide guards, whose stated purpose is stopping the suite reaching out of
the process.

Add to the existing `test_invalid_or_reserved_project_ids` parametrisation the
two values criterion 10 names, `a_b` and `A-b`, and a docstring saying why they
are there: an id containing an underscore or an uppercase letter would make
`override_variable` non-injective, so the id pattern is what keeps two distinct
projects from mapping to one variable.

**Proves it:** `pytest tests/test_project_registry.py -k project_ids` passes;
a new `test_the_override_variable_name_follows_the_id` asserts
`override_variable("proposit-core") == "TCW_PROJECT_PROPOSIT_CORE"` and
`override_variable("proposit-app-repo") == "TCW_PROJECT_PROPOSIT_APP_REPO"`.

## Task 2 — `overrides()` on the storage-neutral spine

**Modifies** `tcw/store/base.py`.

Add a frozen dataclass beside `UnreachableProject`:

```python
@dataclass(frozen=True)
class ProjectOverride:
    """A locator the caller's environment supplied, in place of the declared one."""
    id: str
    source: str        # what supplied it, for a message: "TCW_PROJECT_FOO"
    locator: Any       # opaque exactly as Project.locator is
```

and a concrete default on `ProjectRegistry`, beside `declared_parent_id`:

```python
def overrides(self) -> list[ProjectOverride]:
    """Locators the caller supplied for this graph, in place of declared ones.

    Empty by default: a store with no such mechanism has none. Not abstract,
    because every existing adapter is correct with the empty answer.
    """
    return []
```

**Why the spine and not the adapter.** The litmus test: *could a non-filesystem
store implement this?* Yes — a tracker-backed registry reads the same variable
and yields a project key rather than a directory. The question "did the caller
override where this project is" is storage-neutral; only the *value* is a path,
and that stays inside `FsProjectRegistry`. `source` is a string rather than a
variable name by type, for the same reason `locator` is `Any`: an adapter that
supplies overrides some other way still has something to name.

The default is concrete, not abstract, so no existing implementation changes and
no test outside this item moves.

**Proves it:** the suite is unchanged and green — this task adds a method nobody
calls yet. `pytest` full run.

## Task 3 — Rule 0 in `_target_path`

**Modifies** `tcw/store/project.py`. **Adds tests to**
`tests/test_project_registry.py`.

`FsProjectRegistry.__init__` gains `self._override_cache: dict[str, Path | None] = {}`
and `self._overrides: list[ProjectOverride] = []`.

`_target_path` consults the override before building its candidate list, and
returns immediately when it answers:

```python
def _target_path(self, source_config, entry):
    override = self._override_path(entry.id)
    if override is not None:
        return override
    ...existing ladder unchanged...
```

`entry.id` is already carried on `ConnectedProject`, so no call site changes.

`_override_path(project_id)` is memoised on `_override_cache` — the reciprocity
walk calls `_target_path` again for every edge, and without the cache each call
re-probes the disk and re-appends to `_overrides`. It resolves as follows:

1. `os.environ.get(override_variable(project_id))`, stripped. Empty or unset →
   `None`. An exported-but-empty variable is the same as no variable; treating
   it as a path names the process's working directory, which is never what
   anyone meant.
2. `Path(value).expanduser()`; if not absolute, resolved against the process's
   working directory, then `.resolve()`. **Deliberately not against the
   declaring config**, unlike a locator: an environment variable is written by
   the shell, and a shell-relative path is what the person exporting it means.
   The docstring says so, because it differs from every other path in this file.
3. The directory does not exist → `None`, and the ladder carries on to the
   `repository` declaration. Absent is not wrong (criterion 4).
4. The directory exists but holds no `tcw-config.yaml` → `self._problem(...)`
   naming the variable and the path, and return the sentinel path anyway so the
   caller does **not** fall through (criterion 5). `_read_config` then records an
   unreachable edge for it, which is the honest description: we were told where
   it is, and it is not a node.
5. Otherwise append `ProjectOverride(project_id, name, root)` to `self._overrides`
   and return the sentinel path.

Note what step 5 does **not** do: it does not read the config to check the id.
An override naming the wrong node is caught where every other wrong target is
caught — `_read_config`'s existing `declared_id != project_id` branch, which
already emits a message naming both the expected key and the found id
(criterion 6). Re-checking here would parse the same YAML twice and print two
messages for one cause. The override is recorded before the id is known so that
`tcw validate` prints the override line *beside* the mismatch, which is what
stops the mismatch reading as a path nobody wrote (Task 4 orders the output to
make that true).

`FsProjectRegistry.overrides()` calls `_load_graph()` then returns
`list(self._overrides)` — overrides are discovered by walking, so an unwalked
graph has none to report. A variable naming a project no config declares is
never consulted and never listed; it is not in effect.

**Rule 0 is first, and that is the load-bearing decision.** The motivating case
is a declared locator that resolves to the *wrong existing node*, so any rung
below rule 1 cannot reach it.

**Proves it**, as new tests in `tests/test_project_registry.py`:

- `test_an_override_beats_a_locator_that_resolves_elsewhere` — two valid sibling
  nodes, the config's locator pointing at the wrong one, the variable at the
  right one; `registry.get(id).locator` is the override and `require_valid()`
  passes. This is criterion 1, and it must assert against a locator that
  *resolves*, not merely one that is absent.
- `test_an_override_at_an_absent_path_falls_through_to_the_declaration` —
  criterion 4: `check()` empty, the `repository` rung answers, `unreachable()`
  matches the no-variable run.
- `test_an_override_at_a_directory_that_is_not_a_node_is_a_problem` — criterion
  5: `check()` holds one entry naming both the variable and the path,
  `require_valid()` raises, and the declaration is **not** consulted.
- `test_an_override_naming_the_wrong_node_names_both_ids` — criterion 6.
- `test_an_empty_override_variable_is_the_same_as_none` — the step-1 guard.
- `test_the_override_is_probed_once_per_project` — monkeypatch `os.environ` with
  a counting mapping, or count `Path.is_dir` calls, and assert the reciprocity
  walk does not re-probe. Guards the memoisation, which is the thing most likely
  to be dropped by a later edit and least likely to fail visibly.

## Task 4 — `tcw validate` says which overrides are in effect

**Modifies** `tcw/cli.py` (`_cmd_validate`). **Adds a test to**
`tests/cli/` alongside the existing validate tests.

Print one line per override **before** `registry.check()` is consulted:

```python
for override in registry.overrides():
    print(f"connected project '{override.id}' is overridden by "
          f"{override.source} to {override.locator}", file=sys.stderr)
```

Ordering matters and is the whole reason this is not appended beside
`misdirected()` as the spec first suggested: `_cmd_validate` returns 1 from
inside the problem block, so anything printed after it never appears on the run
where a wrong override is the thing being diagnosed. Overrides are context for
everything below them, so they go first.

Not counted among the problem total, and not fatal — same register as
`unreachable()` and `misdirected()`.

**Proves it:** a CLI test asserting that with one override set, `tcw validate`
exits 0 on an otherwise clean graph, prints exactly one override line, and its
"N problem(s)" total is absent (criterion 9); and a second asserting the
override line is present on the failing run where the override names the wrong
node.

## Task 5 — Provisioning honours the same override

**Modifies** nothing in `tcw/` if the assertion below holds. **Adds tests to**
`tests/test_project_registry.py` or the provisioning test module.

`_provision_nodes` decides whether to fetch through `resolved_outside`, which
asks `starting_registry.get(project_id)` — so an override applied in graph
loading is honoured by provisioning without provisioning knowing it exists. That
is the design claim behind criterion 11, and it is a claim, not a fact, until a
test runs.

Write the test first and find out. **If it fails, this task is where the reason
is diagnosed and fixed, and the fix is reported rather than absorbed** — a
provisioning path that needs its own override lookup would mean the rung is in
the wrong place, which is a spec question, not an implementation one.

**Proves it:**
- `test_an_overridden_project_is_never_fetched` — criterion 2: a project whose
  override resolves is reported available and creates no cache directory under
  the test's `XDG_CACHE_HOME`.
- `test_one_variable_set_serves_both_session_shapes` — criterion 7, as the two
  halves of one test: with every directory present, no cache entries; with the
  same variables set and only one directory present, the others provision
  normally. This is the criterion that justifies absent-is-not-wrong, so it is
  the one that must not be skipped.
- `test_the_override_is_honoured_by_every_command` — criterion 11: assert the
  same overridden graph resolves for `tcw work list`, `tcw validate`, and
  `tcw taxonomy list`. One assertion per command, through the CLI, because the
  claim is precisely that this is not per-command.

## Task 6 — With no variable set, nothing changed

**Adds a test to** `tests/test_project_registry.py`.

Criterion 8, stated as a regression rather than a byte-comparison against a
released version, which the suite cannot run: build a nested two-node graph with
no `TCW_PROJECT_*` set and assert `check()`, `unreachable()` and `misdirected()`
are all empty and the cache directory was never created. The existing suite
already covers this shape incidentally; this makes it explicit and names the
criterion, so a later change to `_target_path` that breaks the no-override path
fails on a test that says why.

**Proves it:** full `pytest` run green, which — with Task 1's conftest fixture —
is now genuinely independent of the developer's shell.

## Task 7 — The capability record

**Creates** `docs/capabilities/cli/point-tcw-at-a-project-i-already-have/`
(`meta.yaml`, `description.md`) and the work item's `capabilities.yaml` sidecar.

```sh
tcw capabilities add cli/point-tcw-at-a-project-i-already-have \
    "Point TCW at a project I already have" --status Supported
```

then edit the scaffolded `meta.yaml` to carry
`Feature: provisioned-component-stores`, `Subject: [store/home-repository, node, cli]`,
and `Planning doc:` set to this item's slug — matching
`cli/declare-a-connected-projects-home-repository` (`cap-596612`), whose
complement this is.

`description.md` is written in the first person the other capability
descriptions use, and must say the three things a reader needs: that the
statement is made by the environment rather than by a file another machine
reads; that it wins over both the declared locator and the `repository`
declaration; and that naming a project this machine does not have is not an
error, which is what lets one set of variables serve a whole environment.

Write the sidecar `capabilities.yaml` in the item folder with the one `new:`
entry. No existing capability's status changes;
`cli/declare-a-connected-projects-home-repository` keeps its promise verbatim.

**Proves it:** `tcw capabilities check` passes; `tcw capabilities list` shows the
new entry as `Supported`; the DoD's "capabilities reconciled" is answerable.

## Documentation Sync

Evaluated against the four declared entries. Three fire, one does not.

- **`README.md`** — **fires.** User-facing behaviour changes. Add a short block
  to `### Connected projects` (README.md:419), after the "A bare locator string
  stays a locator" paragraph that already explains the ladder, since this adds a
  rung above it. Give the variable name and the mapping rule, the three cases
  (wins / absent is fine / present-and-wrong is refused), and the fact that
  `tcw validate` lists the ones in effect. Name the cloud-session case as the
  motivating one, because it is why a reader would want this.
- **`docs/release-notes/upcoming.md`** — **fires.** One entry, plain language, no
  module names: you can now tell TCW where a connected project actually sits on
  this machine without editing a file the other machines read.
- **`docs/changelogs/upcoming.md`** — **fires.** Under **Added**: the variable and
  its precedence; the `ProjectOverride` type and `ProjectRegistry.overrides()`;
  the `tcw validate` reporting line. Under **Internal**: the conftest fixture
  that clears `TCW_PROJECT_*`.
- **`skills/<component>/SKILL.md`** — **does not fire.** No component's CLI
  surface, model, lifecycle, or guardrails change. The override is read during
  graph loading and no skill teaches an agent to set it. Recorded here as
  evaluated-and-declined rather than omitted, so the next reader does not have
  to re-derive it.

## Verification

What the suite cannot check, to be done by hand before `verify`:

1. **The real reproduction.** Criterion 3 is stated against the Proposit
   workspace in its flat-sibling layout, which this repository's suite has no
   access to. Reproduce the two reported graph problems in a scratch directory
   built to the same shape — three nodes whose configs name a nested layout,
   checked out as flat siblings — confirm `tcw validate` reports them, then
   confirm the override clears them. Record the transcript in `outcome.md`.
   Without this, criterion 3 is untested, and it is the criterion that describes
   the actual bug.
2. **A real Claude Code cloud session**, which is the user's stated reason for
   the work: set the three variables in the environment's configuration, attach
   a subset of the repositories, and confirm the graph resolves with no fetch
   for the ones present and a normal fetch for the ones absent. This is the only
   check of the assumption the spec flags as unestablished — that attached
   repositories are cloned as flat siblings under one base directory. If that
   assumption is wrong, the failure is benign but the feature does not deliver
   what it was asked for, and that must be found here rather than reported as
   done.
3. **The wrong-sibling message**, read as a person. Set
   `TCW_PROJECT_PROPOSIT_APP` to the `proposit-app` directory — which is the node
   `proposit-app-repo`, the crossing the spec's table warns about — and confirm
   the output is enough to find the mistake without reading the source.

## Notes

- The spec's Non-goals hold: no per-machine config file, no `work.path` /
  `taxonomy.path` override, no change to the duplicate-id or reciprocity checks.
  `resolve_store`'s matching gap is left alone and is the first place to look if
  this pattern proves out.
- Two deviations from the spec's Design section, both narrowings, neither
  changing an acceptance criterion. First, the id-mismatch check is left to
  `_read_config` rather than duplicated in the override lookup (Task 3). Second,
  `tcw validate` prints overrides *before* the problem block rather than beside
  `misdirected()` (Task 4), because the spec's placement is unreachable on the
  runs where it matters most.
