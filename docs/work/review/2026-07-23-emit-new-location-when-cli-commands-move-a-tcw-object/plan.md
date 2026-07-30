# Plan — Emit new location when CLI commands move a TCW object

Approach **B** (spec): add an abstract `WorkStore.locate(slug) -> str | None`,
realize it in `FsWorkStore`, and have the CLI depend only on the abstract method.
Four call sites (`start`, `complete`, `inbox accept`, `new`) plus test updates and
docs. Single context; no staged plan. Verification: `pytest tests/test_work.py -q`
(and `pytest -q` before closeout).

## Phase 1 — Store interface + FS adapter

1. `tcw/store/base.py`, class `WorkStore` — add the abstract method next to
   `artifact_locator` (`:948` — the spec's `:633` was stale):

    ```python
    @abstractmethod
    def locate(self, slug: str) -> str | None:
        """A short, human-readable location for the item's current home, or None
        if the item does not exist. Adapters realize it however fits their backing
        store (a filesystem: the repo-relative folder path; a remote tracker: an
        issue URL or status label). Presentation only — do not parse it."""
    ```

2. `tcw/store/fs.py`, class `FsWorkStore` — implement it near `path` (`:1776` —
   the spec's `:1583` was stale):

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

    No other `WorkStore` subclass exists, so no further adapters need changing.

## Phase 2 — CLI wiring

File: `tcw/work/cli.py`. Each site resolves `loc = st.locate(bare)` (or
`item.slug` where that's what's in hand) and appends only when `loc` is truthy.
The CLI must **not** import/compute `node_root`/`relative_to` for this — it's all
in the adapter now.

(All `cli.py` line numbers below were stale in the spec; the corrected ones are
given.)

1. `_start` (`:473`):
    - non-worktree (`:496`): `started {args.slug}` → `started {args.slug} → {loc}`.
    - worktree (`:530`): `started {args.slug} → {loc} (worktree {wt})`; if `loc`
      is None keep today's `started {args.slug} → worktree {wt}`.
    - Keep `_complete_hint` on stderr unchanged. Use resolved `bare` for
      `locate`, `args.slug` in the verb (qualified slugs read correctly — matches
      `test_work.py:1544`).
2. `_complete` (`:875`): `completed {args.slug} ({args.resolution})` →
   append ` → {loc}` (folder already moved to `completed/` by `st.complete`).
   **Correction:** this one `print` serves both resolutions, so a discard
   reports its `discarded/` home too. Suppressing it there would cost code to
   make the output *less* informative; the spec only ever mentioned `completed`
   because it read the line as completion-only.
3. `_inbox_accept` (`:284`): keep `print(item.slug)` on stdout; add
   `print(f"→ now at {loc}", file=sys.stderr)` when `loc`, with
   `loc = st.locate(item.slug)`.
4. `_new` (`:233`): keep `print(item.slug)` on stdout; add
   `print(f"→ created at {loc}", file=sys.stderr)` when `loc`, alongside the
   existing `→ edit:` / `→ next:` hints. `locate` reports the real folder,
   including `--parent`-nested placement.

Wording invariant: slug + repo-relative location via `st.locate()`.

**Cross-node (qualified slug) note:** for `tcw work start project-a/slug`, `st`
is the resolved sub-node store, so `locate` returns a path relative to _that
node's_ root (`docs/work/active/slug`), not `project-a/docs/work/...`. The
qualified slug in the verb already names the node, so the message reads
`started project-a/slug → docs/work/active/slug` — unambiguous. If the cross-node
case proves confusing in practice, add CWD-relative rendering later.

## Phase 3 — Tests

1. `tests/test_work.py` (there is no `tests/test_fs_*`) — add a unit test for
   `FsWorkStore.locate`: repo-relative path for a backlog/active/completed item;
   `None` for a missing slug; and (monkeypatching `path` to return a `/tmp/...`
   path outside `node_root`) the absolute-string fallback with no raise. This is
   the one non-trivial branch.
2. `test_work.py:927` (`test_cli_new_and_start_emit_next_step_hints`): replace the
   exact `== f"started {slug}"` with: stdout starts with `started {slug}` and
   contains `docs/work/active/{slug}`. Also assert `new`'s stderr now contains
   `docs/work/backlog/{slug}` (the `→ created at` line) — extends the existing
   `:876` stderr assertion.
3. Add/extend a test asserting `complete` stdout contains
   `docs/work/completed/{slug}`, and `inbox accept` stdout is the bare slug while
   **stderr** contains `docs/work/backlog/{slug}`.
4. `test_work.py:1544` uses `in` and survives augmentation — leave as-is.

## Phase 4 — Documentation sync

Run the `documentation-sync` skill; expected:

- `docs/changelogs/upcoming.md` [Any-Code-Change] — **fires.** Added: abstract
  `WorkStore.locate`; Changed: `start`/`complete`/`inbox accept`/`new` now report
  the item's repo-relative location. Include the HEAD hash range.
- `docs/release-notes/upcoming.md` [Public-API] — **fires.** Plain-language note
  that these commands now tell you where the item is.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — grep for quoted
  transition output; update only if it drifts. **Did not fire:** the skill never
  quotes transition output or folder paths.
- `README.md` [Public-API] — grep for quoted transition output; update only if it
  shows the old form. **Correction: it fired.** The plan guessed "likely no
  change", but README documents this exact output surface (the `→ next:` /
  `→ edit:` hints), so leaving it silent about the location line would have made
  the description incomplete.

## Parallelization / dependencies

Phase 1 → Phase 2 (CLI calls the new method) → Phase 3 (tests assert the output).
Phase 4 last so hashes are final. No cross-item dependencies.

## Closeout reminders

- No capability reconciliation (no `capabilities.yaml` delta).
- Version bump is a user closeout decision; the user-visible output change is a
  minor-bump candidate.
