# Plan — Emit new location when CLI commands move a TCW object

Small, single-context change: one CLI helper, three call sites, test updates,
docs. No staged plan. Approach **A** from the spec (reuse `st.path()`; no
interface change). Verification command: `pytest tests/test_work.py -q`.

## Phase 1 — CLI helper + wire into the three handlers

File: `tcw/work/cli.py`.

1. Add a module-level helper near the other `_`-helpers:

   ```python
   def _rel_location(st, slug: str) -> str | None:
       """Repo-relative home of `slug` for transition messages, or None.
       Resolves through the store's locator; never raises. Falls back to the
       absolute path if the item lives outside node_root.
       # ponytail: FS-only via st.path(). Promote WorkStore.locate() -> str|None
       # (mirroring artifact_locator) when a non-FS adapter needs this.
       """
       p = st.path(slug)
       if p is None:
           return None
       try:
           return str(p.relative_to(st.node_root))
       except ValueError:
           return str(p)
   ```

2. `_start` (`:444`): after a successful non-worktree start, build the location
   and augment stdout. Keep `_complete_hint` on stderr unchanged.
   - non-worktree (`:455`): `started {args.slug}` → append ` → {loc}` when `loc`.
   - worktree (`:468`): keep the worktree note, add the location:
     `started {args.slug} → {loc} (worktree {wt})` (append the `→ {loc}` before
     the worktree segment; if `loc` is None, keep today's line).
   - Resolve `loc = _rel_location(st, bare)` (use the resolved `st`/`bare`, not
     `args.slug`, for lookup; keep `args.slug` in the verb text so qualified
     slugs still read correctly — matches the `:1497` test).

3. `_complete` (`:561`): after `st.complete(...)` succeeds (`:609`), before/at the
   `completed …` print (`:613`):
   `completed {args.slug} ({args.resolution})` → append ` → {loc}` when `loc`.
   Resolve `loc` **before** worktree teardown is irrelevant (folder already
   moved by `complete`); `st.path(bare)` now returns the `completed/` dir.

4. `_inbox_accept` (`:259`): keep `print(item.slug)` on stdout (scriptable).
   After it, add a stderr hint mirroring `_new`'s `→ edit:` line:
   `print(f"→ now at {loc}", file=sys.stderr)` when `loc` is not None, with
   `loc = _rel_location(st, item.slug)`.

Wording invariant: slug + repo-relative destination via `_rel_location`. Arrows
as above; adjust only if a test or readability demands.

**Cross-node (qualified slug) note:** for `tcw work start project-a/slug`, `st`
is the resolved sub-node store, so `_rel_location` returns a path relative to
*that node's* root (`docs/work/active/slug`), not `project-a/docs/work/...`. The
qualified slug in the verb already names the node, so the node-relative location
is unambiguous and the message reads `started project-a/slug → docs/work/active/slug`.
# ponytail: node-relative is fine; add CWD-relative only if the cross-node case
# proves confusing in practice.

## Phase 2 — Tests

File: `tests/test_work.py`.

1. `:880` (`test_cli_new_and_start_emit_next_step_hints`): replace the exact
   `== f"started {slug}"` with an assertion that stdout starts with
   `started {slug}` and contains `docs/work/active/{slug}` (the new location).
2. Add a focused test (or extend an existing complete/inbox test) asserting:
   - `complete` stdout contains `docs/work/completed/{slug}`.
   - `inbox accept` stdout is the bare slug and **stderr** contains
     `docs/work/backlog/{slug}`.
3. `:1497` uses `in` and already survives — leave unless the surrounding block
   also needs the location asserted (optional).
4. Add a direct unit test of `_rel_location` for the guards: returns None when
   `path()` is None, and returns the absolute string (no raise) when the path is
   outside `node_root`. This is the one non-trivial branch — cover it here rather
   than trying to provoke it through the CLI.

## Phase 3 — Documentation sync

Run the `documentation-sync` skill; expected to fire:

- `docs/changelogs/upcoming.md` [Any-Code-Change] — add a Changed entry
  (transition commands now report the item's new location) with the HEAD hash
  range. **Will fire.**
- `docs/release-notes/upcoming.md` [Public-API] — plain-language note that
  `start`/`complete`/`inbox accept` now tell you where the item moved. **Will
  fire.**
- `README.md` [Public-API] — grep for quoted transition output; update only if it
  shows the old `started <slug>` form. Likely no change.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — grep for quoted
  transition output; update only if it drifts. Likely no change.

## Parallelization / dependencies

Phase 1 → Phase 2 (tests assert Phase 1's output). Phase 3 independent of 1–2
content but done last so hashes are final. No cross-item dependencies.

## Closeout reminders

- No capability reconciliation needed (no `capabilities.yaml` delta).
- Version bump is a user closeout decision; the user-visible output change is a
  minor-bump candidate.
