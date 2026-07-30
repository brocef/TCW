# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `WorkStore.locate(slug) -> str | None` (`tcw/store/base.py`) — abstract
  locator for an item's current home, mirroring `artifact_locator`. Adapters
  realize it however fits their backing store (a filesystem: the repo-relative
  folder; a remote tracker: an issue URL or status label); it is presentation
  only and must not be parsed. `FsWorkStore.locate` (`tcw/store/fs.py`) returns
  `path(slug)` relative to `node_root`, `None` for a missing item, and the
  absolute path — rather than raising `ValueError` — for an item outside
  `node_root`.

## Changed

- `tcw work start`, `complete`, `inbox accept`, and `new` (`tcw/work/cli.py`)
  now name the item's new location, resolved through `st.locate()`; the CLI
  holds no `node_root`/`relative_to` knowledge for this. `start` prints
  `started <slug> → docs/work/active/<slug>` (worktree variant:
  `started <slug> → <loc> (worktree <wt>)`), and `complete` appends
  ` → <loc>` — a discard likewise reports its `discarded/` home. `inbox accept`
  and `new` keep their bare-slug stdout and carry the location on stderr
  (`→ now at <loc>` / `→ created at <loc>`). The suffix is omitted when
  `locate` returns `None`; exit codes and gate behavior are unchanged.
- `skills/tcw-work/references/stage-spec.md` — new `Steps` entry: a sweep for
  defects sibling to the reported one is repo-wide by default, or the spec
  states why it was narrowed. Covers the residue the doc guard structurally
  cannot parse (a stale factual claim, a flag named only in prose), and closes
  the failure mode where a scope is inherited from the report or the previous
  stage rather than re-derived.

## Fixed

- `_capability_deltas` (`tcw/work/recursion.py`) — the `tcw work reconcile`
  rollup read only the legacy `{file, heading, from, to}` display list, so a
  sidecar in the canonical `new:`/`changed:` mapping schema always rendered as
  `capabilities.yaml present but not a list — skipped`. Two readers of one file:
  `capability_gate` used `declared_capabilities` while the rollup hand-rolled an
  `isinstance(caps, list)` check, so a sidecar the completion gate accepted was
  reported malformed by the rollup (GitHub #8). The rollup now calls
  `declared_capabilities` too — one reader, `added:` alias inherited for free —
  and renders `<kind> <path>` per declared entry. Three follow-on changes: the
  legacy list is kept as an explicit fallback branch (no producer remains in this
  repo, but `_tasks_for` reads items out of child nodes in other repositories);
  `SidecarError` is caught and rendered as `capabilities.yaml is unreadable: … —
  skipped`, since the rollup spans a whole epic and must not die on one child's
  broken file, while the gate still lets it propagate and fail closed; and the
  no-recognized-keys note no longer claims the file is "not a list", which was a
  false diagnosis once a mapping became the expected shape.

## Internal

- `tests/test_documented_cli_surface.py` — `DOC_FILES` is now derived by
  *exclusion* rather than from a five-root inclusion list. The set comes from
  `git ls-files --cached --others --exclude-standard -- '*.md'` minus the
  `ARCHIVAL` prefixes (`docs/{work,plan,superpowers,changelogs,release-notes}/`,
  each carrying its reason in the source). Coverage goes from 104 files to 133 —
  newly including `AGENTS.md`/`CLAUDE.md`, the 22 `docs/taxonomy/**` bodies, the
  migration guides, and the inbox template — with zero new failures. A new
  documentation tree is now covered the moment the file exists, with no test
  edit. Going through git means `.gitignore` supplies the junk exclusions
  (`node_modules/`, `.venv/`, build output, the gitignored
  `docs/work/completed/`) instead of a second hand-maintained list, and the
  `plugins/tcw` self-symlink stays a single index entry rather than an infinite
  tree. Note `--others`: an untracked, not-yet-staged Markdown draft **is** in
  scope, so a work-in-progress doc naming a nonexistent verb reddens the suite
  before it is committed.
