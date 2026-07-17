# Spec: Drop/reset a local capability override to re-inherit upstream

Follow-up to `2026-07-15-capabilities-set-rejects-inherited-capability-paths-…`
(GitHub #3), which added the override-*write* path but no way to drop one.

## Capability changes

- **New:** `capabilities/reset-an-override` (seeded `Missing`, Planning doc → this
  item) — a user drops a local override and re-inherits the upstream capability
  verbatim, without hand-deleting the override folder. Relates to the existing
  `capabilities/override-inherited`. Recorded in this item's `capabilities.yaml`.

## Problem

`tcw capabilities set <inherited-path>` materializes a **local override** — a
folder whose `meta.yaml` carries `overrides: <alias>/<id>` plus the changed
fields/body (`FsCapabilitiesStore._write_target`, `_apply_override`). There is no
command to remove that override and revert to the upstream value:

- `remove` refuses anything not `origin == "local"` (`fs.py:1062`), and an
  overridden path resolves to `origin == <alias>` (inherited) — so `remove` won't
  touch it.
- The only revert today is hand-deleting the override folder — the exact
  "hand-edit the store" problem #3 set out to remove, one level down.

## Goal

A first-class command to drop a local override:

```
tcw capabilities reset <path>
```

removes the local override folder for `<path>` and re-inherits the upstream
capability. Fail-closed and never touches the upstream node.

## Decisions (locked)

- **Verb:** a new `reset` (not `remove --override`). `remove` means "delete a local
  capability"; overriding/reverting is a distinct federation action. (Request's lean.)
- **Whole-override only:** `reset` drops the entire override folder. Field-level
  revert is already expressible (`set <path> --field K=<value>`, or a YAML null via
  the web/`fields` API to clear one inherited field). No partial-reset flag in v1.
- **Refuse clearly** when there's nothing to drop, distinguishing the two cases:
  - `<path>` is a **standalone local capability** (no `overrides`) → error: "is a
    local capability, not an override — use `remove`".
  - `<path>` **inherits verbatim** (no local override) → error: "no local override
    at '<path>' to reset (it inherits '<qualified>' verbatim)".
- **Abstraction litmus (passes):** dropping a local delta keyed by the upstream id
  is store-implementable (a Jira/graph adapter deletes its own delta record) → the
  operation belongs on the `CapabilitiesStore` interface, beside `remove`/`set`.

## Proposed behavior

### Store interface (`tcw/store/base.py`)

Add abstract `reset(self, identifier: str) -> None` to `CapabilitiesStore`,
documented as: drop the local override at `identifier`, re-inheriting upstream;
raise `ValueError` when there is no override; never mutate an extended store.

### FS adapter (`tcw/store/fs.py` — `FsCapabilitiesStore`)

```python
def reset(self, identifier: str) -> None:
    if self.get_local(identifier) is not None:      # standalone local, not an override
        raise ValueError(f"'{identifier}' is a local capability, not an override "
                         f"(use `remove` to delete it)")
    cap = self.get(identifier)                       # federated; may raise AmbiguousRef
    if cap is None:
        raise ValueError(f"no such capability: {identifier}")
    ov = self._override_index().get(cap.id) or \
         self._override_index().get(f"{cap.origin}/{cap.id}")
    if ov is None:
        raise ValueError(f"no local override at '{identifier}' to reset "
                         f"(it inherits '{cap.qualified}' verbatim)")
    self._rm(ov[0])                                  # remove only the local override folder
```

Reuses the exact override-resolution keys `_write_target` uses (`cap.id` and the
alias-qualified `<origin>/<id>`), so `reset` finds whatever folder `set`
materialized regardless of its placement. `_rm` (git-aware remove) only ever
targets the local override folder — upstream is untouched.

### CLI (`tcw/capabilities/cli.py`)

`tcw capabilities reset <path>` — a new subparser mirroring `remove`'s shape; maps
`ValueError`/`AmbiguousRef`/`RefError` to a non-zero exit with the store's message.
On success print `reset <path>` (and, optionally, the re-inherited status).

### Web

Out of scope (no web control for override lifecycle exists yet). CLI + store only.

## Affected surfaces

- `tcw/store/base.py` — `CapabilitiesStore.reset` (abstract).
- `tcw/store/fs.py` — `FsCapabilitiesStore.reset`.
- `tcw/capabilities/cli.py` — `reset` subcommand.
- `docs/capabilities/capabilities/reset-an-override/` — new capability (add at plan/impl).

## Acceptance criteria

1. Given a federated capability with a local override (created via `set`),
   `tcw capabilities reset <path>` removes the override folder; `show <path>` then
   reports the upstream value with `origin == <alias>` and no local delta.
2. `reset` on a **standalone local** capability exits non-zero with the
   "use `remove`" message and changes nothing.
3. `reset` on an inherited path with **no** override exits non-zero with the
   "inherits verbatim" message and changes nothing.
4. `reset` on an unknown/ambiguous path errors like the sibling commands.
5. The upstream (extended) node is never modified by `reset` (verified by hashing
   the upstream tree before/after in a test).
6. Existing tests pass; new tests cover 1–5 over a two-node federated `tmp_path`
   fixture (mirror the existing capabilities-federation tests).

## Risks / open items

- The override folder may sit at `<path>` or the alias-qualified `<origin>/<path>`
  (per `_write_target`); resolving via `_override_index` by upstream id (not by
  folder path) handles both. Covered by criterion 1 + a placement variant test.
- No web surface — intentional; the override lifecycle is CLI-only today.

## Documentation sync (expected)

- `README.md` [Public-API] — new `tcw capabilities reset` command.
- `docs/release-notes/upcoming.md` — user-facing revert-an-override note.
- `docs/changelogs/upcoming.md` — Added: `reset` (interface + FS + CLI).
- `skills/tcw-capabilities/SKILL.md` [Skill-Driven-Component] — the override
  lifecycle gains a drop step; quick-reference row.
