# Spec — Emit new location when CLI commands move a TCW object

## Capability changes

None. This refines the **output** of existing work-transition commands; it adds
no user capability, changes no command's semantics, and touches no
`capabilities.yaml`. The tcw-capabilities planning gate is therefore a no-op for
this item (no product-layer delta beyond message wording).

## Problem

Work-transition commands report *that* a transition happened but not *where the
item now lives*:

| command | current stdout |
| --- | --- |
| `tcw work start <slug>` | `started <slug>` |
| `tcw work complete <slug> …` | `completed <slug> (<resolution>)` |
| `tcw work inbox accept <entry>` | `<slug>` (bare) |

Because the destination folder is never named, agents (and people) keep looking
for a started item in `backlog/` instead of `active/`, or for an accepted item in
`inbox/` instead of `backlog/`.

## Goals

- After a command relocates a work item, the output names the item's **new
  location** so the reader can go straight to it.
- Consistent phrasing across the relocating commands, keeping the slug in the
  message so existing habits/greps still match.
- Location string is obtained **through the store**, not by hardcoding
  `docs/work/<status>/<slug>` string-building in the command handler.

## Non-goals

- Changing any transition's semantics, gates, or exit codes.
- Reworking the CLI onto a shared output/formatter helper (none exists today; not
  needed for this change).
- Touching the taxonomy or capabilities axes (their status is an in-place field
  edit, not a folder move — the confusion doesn't arise there).
- Rewording `delegate`/`escalate`/`new`, which already print a realized path.

## Constraints

- **Abstraction litmus (prime directive).** The message value is a filesystem
  path, but it must be resolved *through the store's locator*, never by
  concatenating `docs/work/<status>/<slug>` in the CLI. See the design decision
  below for how this stays litmus-clean.
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
- `path()` is FS-only (returns a `Path`); the abstract interface has no
  item-location accessor. The abstract `artifact_locator(slug, name) -> str|None`
  (`base.py:633`) is the nearest existing "openable handle" pattern.

Out of scope, confirmed: `drop` deletes (no destination); `delegate`/`escalate`
already `print(doc)` (the realized inbox `Path`); `new` already prints
`→ edit: {body}` on stderr; `capabilities set --status` is an in-place field
edit (path unchanged); taxonomy has no transitions.

## Proposed behavior

After a successful relocation, resolve the item's new home via `st.path(bare)`,
render it repo-relative (`relative_to(st.node_root)`), and surface it on the
command's existing human-facing stream:

- **`start`** (stdout is prose → augment):
  `started <slug> → docs/work/active/<slug>`
  worktree variant keeps the worktree note:
  `started <slug> → docs/work/active/<slug> (worktree <wt>)`
- **`complete`** (stdout is prose → augment):
  `completed <slug> (<resolution>) → docs/work/completed/<slug>`
- **`inbox accept`** (stdout is a scriptable bare slug → keep it, add stderr
  hint, mirroring `_new`'s `→ edit:` line):
  stdout: `<slug>` (unchanged) · stderr: `→ now at docs/work/backlog/<slug>`

Exact arrow/verb wording is a small choice settled in `plan.md`; the invariant is
*slug + repo-relative destination, resolved through `st.path()`*.

A tiny shared CLI helper (e.g. `_rel_location(st, slug) -> str | None`) formats
`st.path(slug)` repo-relative once, so the three call sites don't repeat the
`relative_to` dance. It degrades gracefully and **never raises**: if `path()`
returns `None` the suffix is skipped; if the path is not under `st.node_root`
(`relative_to` would raise `ValueError`), fall back to the absolute path string
rather than crashing the command.

## Design decision — how to resolve the location (the judgment call)

**Recommended (A): reuse the existing FS locator in the CLI.** Call
`st.path(bare).relative_to(st.node_root)` in the three handlers. No interface
change.

- Litmus-clean because it resolves *through the store's declared locator*
  (`path()`) rather than hardcoding the `docs/work/<status>/` layout, and it adds
  **nothing** to the abstract `WorkStore` interface. The CLI is already
  FS-adapter-bound (it uses `.node_root`/`.root`/`.body_path` throughout), so no
  new model coupling is introduced.
- Smallest diff; consistent with how `_new` already surfaces `body_path`.
- Ceiling: a future non-FS CLI (JiraWorkStore) would need its own location
  rendering. That is exactly when promoting an abstract locator pays for itself —
  do it then, not speculatively.

**Alternative (B): promote an abstract `locate(slug) -> str | None` to
`WorkStore`.** FS realizes it as the repo-relative folder; a remote store could
realize it as an issue URL / status label. Mirrors the existing
`artifact_locator` pattern and lets other consumers (`tcw serve`) share the
concept.

- More portable, but adds an interface method + adapter impl no current consumer
  needs. YAGNI until a second adapter or a second consumer appears.

Recommendation: **A now, B as the documented upgrade path** (leave a
`ponytail:`-style note at the helper naming `locate()` as the promotion point).
**This is the open decision for your review.**

## Acceptance criteria

- `tcw work start`, `tcw work complete`, and `tcw work inbox accept` each name
  the item's new repo-relative location in their output.
- The location is obtained via `st.path()`, not string-built from status.
- `inbox accept` / `new` stdout remains a bare slug; their location text is on
  stderr. `start` / `complete` stdout stays a single prose line, now including
  the location.
- `--worktree` start still reports the worktree and now also the active-folder
  location.
- If `st.path()` returns `None` (shouldn't happen post-transition), the command
  still succeeds and simply omits the location suffix; if the path is not under
  `node_root`, it falls back to the absolute path (never raises `ValueError`).
- Existing exit codes and gate behavior unchanged.

## Risks / dependencies

- **Test churn:** `tests/test_work.py:880` asserts
  `start_out.out.strip() == f"started {slug}"` and `:1497` asserts
  `f"started project-a/{slug}" in out.out`. These and any `completed …` / inbox
  assertions must be updated to the new format. Low risk, mechanical.
- No dependency on other work items.

## Documentation Sync (triggers expected to fire)

- `docs/changelogs/upcoming.md` [Any-Code-Change] — **will fire.**
- `docs/release-notes/upcoming.md` [Public-API] — **will fire** (user-visible
  output change).
- `README.md` [Public-API] — only if it quotes the old transition output; verify
  during plan (likely no change).
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — verify whether it quotes
  transition output; update only if it drifts (likely no change).
