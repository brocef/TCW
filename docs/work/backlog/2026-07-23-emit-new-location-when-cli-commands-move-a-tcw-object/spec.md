# Spec — Emit new location when CLI commands move a TCW object

## Capability changes

None. This refines the **output** of existing work-transition commands; it adds
no user capability, changes no command's semantics, and touches no
`capabilities.yaml`. The tcw-capabilities planning gate is therefore a no-op for
this item (no product-layer delta beyond message wording).

## Problem

Commands that place or relocate a work item report *that* it happened but not
*where the item now lives* (in a form you can go straight to):

| command | current output |
| --- | --- |
| `tcw work start <slug>` | `started <slug>` (stdout) |
| `tcw work complete <slug> …` | `completed <slug> (<resolution>)` (stdout) |
| `tcw work inbox accept <entry>` | `<slug>` (stdout, bare) |
| `tcw work new "<title>"` | `<slug>` (stdout) + `→ edit: <abs>/initial-request.md` (stderr) |

Because the item's folder is never named as a repo-relative path, agents (and
people) keep looking for a started item in `backlog/` instead of `active/`, an
accepted item in `inbox/` instead of `backlog/`, or a freshly created item they
can't yet see. `new` does print a path, but it's the absolute *file* to edit, not
the item's folder home.

## Goals

- After a command places or relocates a work item, the output names the item's
  **location** (repo-relative) so the reader can go straight to it.
- Consistent phrasing across the commands, keeping the slug in the message so
  existing habits/greps still match.
- Location string is obtained **through the store** (an abstract locator), not by
  hardcoding `docs/work/<status>/<slug>` string-building in the command handler.

## Non-goals

- Changing any transition's semantics, gates, or exit codes.
- Reworking the CLI onto a shared output/formatter helper (none exists today; not
  needed for this change).
- Touching the taxonomy or capabilities axes (their status is an in-place field
  edit, not a folder move — the confusion doesn't arise there).
- Rewording `delegate`/`escalate`, which already print the realized inbox `Path`.
- Removing `new`'s existing `→ edit:` file hint — it stays; we *add* the
  repo-relative folder location beside it.

## Constraints

- **Abstraction litmus (prime directive).** The message value is a filesystem
  path, but "where does this item live now" is an abstract, portable concept: a
  remote tracker realizes it as an issue URL or status label. So it belongs on
  the store interface as an abstract locator that each adapter realizes — the CLI
  never concatenates `docs/work/<status>/<slug>` and never touches
  `.node_root`/`relative_to` itself. See the design decision below.
- **Preserve scriptable stdout contracts.** `inbox accept` and `new` print a
  bare slug on stdout (machine-readable); their human hints go to stderr. That
  contract must not break. `start`/`complete` stdout is a **prose sentence**, not
  a machine-readable contract, so augmenting it is deliberate and safe — the only
  fallout is test assertions on the exact string (see Risks). The
  wording change is worth calling out as a user-visible behavior change at
  closeout (candidate for a minor version bump — a closeout decision).

## Current-state findings

CLI is `argparse` + stdlib `print()` — **no shared output helper, no click**
(`tcw/work/cli.py`). Handlers are already typed against the concrete
`FsWorkStore` and freely use `st.path()`, `st.body_path()`, `st.node_root`,
`st.root` (e.g. `_new` at `tcw/work/cli.py:220`, `_start` at `:458`). The CLI is
**not** written against the abstract `WorkStore` interface today.

Relocating commands (all discard the store's return value and print a hand-built
string):

- `_start` — `tcw/work/cli.py:444`; prints `started {slug}` (`:455`) or
  `started {slug} → worktree {wt}` (`:468`). backlog → active.
- `_complete` — `:561`; prints `completed {slug} ({resolution})` (`:613`).
  active → completed (and the scoped backlog-epic → completed case).
- `_inbox_accept` — `:259`; prints `item.slug` only (`:268`). inbox → backlog.

Store facts (`tcw/store/base.py`, `tcw/store/fs.py`):

- `start`/`complete`/`transition` return a `WorkItem` carrying **`status` but no
  path**; `_effect_transition` (`fs.py:2158`) returns `None`.
- `FsWorkStore.path(slug)` (`fs.py:1583`) returns the realized **absolute**
  item directory (or `None`). This is the adapter's declared locator.
- `st.node_root` is the repo root, so
  `st.path(slug).relative_to(st.node_root)` == `docs/work/<status>/<slug>` — the
  exact repo-relative string the message wants.
- `path()` is FS-only (returns a `Path`); the abstract `WorkStore` interface has
  **no item-location accessor** — this is the gap approach B fills. The abstract
  `artifact_locator(slug, name) -> str|None` (`base.py:633`, `@abstractmethod`) is
  the existing "openable handle" pattern to mirror.
- **Only `FsWorkStore` subclasses `WorkStore`** (`fs.py:1539`); no test doubles
  subclass it. So adding a new `@abstractmethod` forces exactly one adapter to
  implement it — no conformance breakage.

Out of scope, confirmed: `drop` deletes (no destination); `delegate`/`escalate`
already `print(doc)` (the realized inbox `Path`); `capabilities set --status` is
an in-place field edit (path unchanged); taxonomy has no transitions.

## Proposed behavior

### New abstract store method (approach B)

Add to `WorkStore` (`tcw/store/base.py`) an abstract locator mirroring
`artifact_locator`:

```python
@abstractmethod
def locate(self, slug: str) -> str | None:
    """A short, human-readable location for the item's current home, or None
    if the item does not exist. Adapters realize it however fits their backing
    store (a filesystem: the repo-relative folder path; a remote tracker: an
    issue URL or status label). Presentation only — do not parse it."""
```

`FsWorkStore.locate` (`tcw/store/fs.py`) realizes it as the repo-relative folder,
degrading gracefully and **never raising**:

```python
def locate(self, slug: str) -> str | None:
    p = self.path(slug)
    if p is None:
        return None
    try:
        return str(p.relative_to(self.node_root))
    except ValueError:
        return str(p)          # item outside node_root: absolute, don't crash
```

The CLI calls `st.locate(bare)` only — it never touches `.node_root` or
`relative_to`. All the path/relative logic lives in the adapter, where the litmus
test says filesystem realization belongs.

### CLI output (resolve via `st.locate(bare)`, surface on the existing stream)

- **`start`** (stdout is prose → augment):
  `started <slug> → docs/work/active/<slug>`
  worktree variant keeps the worktree note:
  `started <slug> → docs/work/active/<slug> (worktree <wt>)`
- **`complete`** (stdout is prose → augment):
  `completed <slug> (<resolution>) → docs/work/completed/<slug>`
- **`inbox accept`** (stdout is a scriptable bare slug → keep it, add stderr
  hint): stdout `<slug>` (unchanged) · stderr `→ now at docs/work/backlog/<slug>`
- **`new`** (stdout is a scriptable bare slug → keep it; add the folder location
  on stderr beside the existing `→ edit:`/`→ next:` hints):
  stdout `<slug>` (unchanged) · stderr `→ created at docs/work/backlog/<slug>`
  (nested `--parent` items land under the parent folder — `locate` reports
  wherever the item actually is).

Exact arrow/verb wording is a small choice settled in `plan.md`; the invariant is
*slug + repo-relative location, resolved through `st.locate()`*.

## Design decision — abstract locator (approach B, chosen)

Add `WorkStore.locate(slug) -> str | None` and realize it in `FsWorkStore`; the
CLI depends only on the abstract method.

- **Litmus-clean.** "Where does this item live now" is a portable concept — a
  Jira adapter answers with an issue URL, a wiki with a page path. It belongs on
  the interface; the FS adapter realizes it as a folder path. The CLI holds no
  filesystem-layout knowledge for this feature.
- Mirrors the existing `artifact_locator` "openable handle" pattern, so it reads
  as a natural extension of the interface rather than a novel abstraction.
- Reusable: `tcw serve` and any future consumer get the same location concept for
  free instead of re-deriving repo-relative paths.
- Cost: one `@abstractmethod` + one adapter impl. Only `FsWorkStore` must satisfy
  it (no other subclasses), so the blast radius is a single method.
- **Abstract, not a concrete `return None` default**, deliberately: a future
  adapter should be *forced* to answer "where does this item live" rather than
  silently inherit "nowhere" — that is the portability guarantee B exists for,
  and it matches `artifact_locator`, which is likewise `@abstractmethod`. The
  cost is one trivial method per new adapter.

Rejected alternative (A): compute `st.path().relative_to(st.node_root)` inline in
the CLI. Smaller diff, but bakes filesystem-layout knowledge into the CLI and
leaves the abstract interface unable to express location — declined in favor of
the portable design.

## Acceptance criteria

- `WorkStore` exposes an abstract `locate(slug) -> str | None`; `FsWorkStore`
  implements it as the repo-relative folder path.
- `tcw work start`, `tcw work complete`, `tcw work inbox accept`, and
  `tcw work new` each name the item's repo-relative location in their output,
  obtained via `st.locate()` (no `relative_to`/`node_root` in the CLI).
- `inbox accept` / `new` stdout remains a bare slug; their location text is on
  stderr. `start` / `complete` stdout stays a single prose line, now including
  the location.
- `--worktree` start still reports the worktree and now also the active-folder
  location.
- `locate` returns `None` for a missing item (command still succeeds, suffix
  omitted) and falls back to the absolute path when the item is outside
  `node_root` (never raises `ValueError`).
- Existing exit codes and gate behavior unchanged.

## Risks / dependencies

- **Test churn:** `tests/test_work.py:880` asserts
  `start_out.out.strip() == f"started {slug}"`, `:876` asserts `new`'s stderr, and
  `:1497` asserts `f"started project-a/{slug}" in out.out`. These and any
  `completed …` / inbox assertions must be updated to the new format. Low risk,
  mechanical.
- Adding an `@abstractmethod` to `WorkStore` would break any other concrete
  subclass — verified there is none but `FsWorkStore`.
- No dependency on other work items.

## Documentation Sync (triggers expected to fire)

- `docs/changelogs/upcoming.md` [Any-Code-Change] — **will fire.**
- `docs/release-notes/upcoming.md` [Public-API] — **will fire** (user-visible
  output change).
- `README.md` [Public-API] — only if it quotes the old transition output; verify
  during plan (likely no change).
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — verify whether it quotes
  transition output; update only if it drifts (likely no change).
