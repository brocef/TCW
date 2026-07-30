# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `worktree_anchors(directory)` (`tcw/store/project.py`) — returns
  `(current worktree top, main worktree root)` when `directory` sits in a
  *linked* git worktree, else `None`: git absent, not a repository, the primary
  checkout, a **bare** main repo, or any git failure. Never raises. One
  `git rev-parse --path-format=absolute --show-toplevel --git-common-dir` yields
  both values; the bare case is discriminated by the common dir not being named
  `.git`, whose parent is not a worktree at all. Cached in an unbounded
  module-level dict keyed by resolved directory — a CLI invocation never outlives
  the process, and the probe is ~8 ms against six registry opens for
  `tcw work list -i` on a three-node graph. It lives in `project.py` rather than
  beside `git_root` in `fs.py` because `fs.py` imports `project.py`, so the
  reverse import would be circular.
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

- `FsProjectRegistry._target_path` (`tcw/store/project.py`) — a relative
  `connected-projects` locator was resolved against `source_config.parent`, the
  directory of the config declaring it. Inside a linked git worktree that
  directory is the worktree, not the checkout the locator was authored against,
  so every relative locator was off by the worktree's nesting depth and *every*
  command failed — including read-only ones, because `find_node`
  (`tcw/store/fs.py`) calls `require_valid()` before returning anything.
  Two rules, both private to the filesystem adapter (`ProjectRegistry` exposes no
  path-resolution operation, so there is nothing here for a remote adapter to
  implement):
    - **Rule 1, re-anchor only on escape.** For a relative locator whose source
      config is inside the current worktree: compute the naive target; keep it if
      it still lies inside the worktree; otherwise re-resolve against
      `main_root / source_dir.relative_to(current_toplevel)`. The narrowness is
      load-bearing — the originally proposed fix (re-anchor *every* relative
      locator) regresses multi-project-in-one-repo, which works today, into
      `duplicate project id 'sub-a'` plus a non-reciprocal root.
    - **Rule 2, collapse the worktree's own identity.** The current node has two
      config paths on disk, `<worktree>/tcw-config.yaml` and its counterpart
      `<main>/<rel>/tcw-config.yaml`; the parent's locator names the second, so
      the graph would hold two configs under one ID and fail reciprocity. That
      one path is aliased onto the worktree copy. Exactly one pair, only while
      the probe reports a linked worktree — a wider alias would mask genuine
      duplicate-ID errors. Applies to **absolute** locators too: an absolute
      parent locator names the counterpart just as readily, and a fully-absolute
      two-node graph was broken inside a worktree at HEAD for that reason.
  `_target_path` becomes an instance method (five call sites) so the probe runs
  once per registry. Unchanged outside a worktree and unchanged for a node in no
  git repository at all — verified as byte-identical output, measured before and
  after.
- `_complete` (`tcw/work/cli.py`) — completing a `--worktree` item from inside
  that item's own worktree exited 0 having done nothing. `st.node_root` is the
  worktree, so `merge_worktree(st.node_root, branch)` merged the work branch into
  itself and `remove_worktree` looked for `<worktree>/.worktrees/<slug>`, missed,
  and swallowed the miss as "already absent" (`tcw/store/fs.py`) — the command
  claimed a completion that never happened, leaving the primary checkout
  unmerged and the worktree standing. It now refuses with a non-zero exit naming
  the primary checkout. Refusing rather than supporting it is the whole fix:
  `git worktree remove` deletes the worktree you are standing in. Detection
  compares the probe's worktree top against *this* item's own worktree path, so
  completing from an unrelated worktree is untouched.
- `_list` (`tcw/taxonomy/cli.py`) — `tcw taxonomy list` sorted on the joined path
  string (`t.qualified`) while deriving indentation independently from
  `t.slug.count("/")`, so the two disagreed. `-` (0x2D) sorts before `/` (0x2F),
  which put any root slug that is a hyphen-extension of another root
  (`event-reporting` vs `event`) *between* that root and its children, where it
  inherited their indentation and appeared to own them (GitHub #11). The sort key
  is now `(origin != "local", origin, tuple(slug.split("/")))`: comparing segment
  tuples makes a parent's key a strict prefix of its children's, so the traversal
  is a true depth-first pre-order and the existing depth expression is correct
  for every row. `origin` is a distinct key component because each `extends`
  alias is a separate store with its own slug namespace, so inherited trees group
  per origin instead of splicing into the local one. Data was never affected —
  `taxonomy check` and `validate` both passed throughout — only the rendering.
  **This repo's own taxonomy exhibited it**: `status` and `subject` rendered
  under `capability-feature-association` instead of `capability`.
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

- `tests/test_environment_hardness.py` — a fourth environment, **linked git
  worktree**, alongside the three the module docstring already described. New
  factories `two_node_graph` / `worktree_node` / `monorepo_worktree`; ten tests
  covering every command exiting 0 inside the worktree, the registered parent,
  an empty `check()`, the current node being the worktree (and writes landing
  there), the absolute-locator graph, the monorepo-inside-a-worktree layout that
  must *not* be re-anchored, the non-git graph that must not change, and both
  sides of the `complete` refusal. `tests/test_project_registry.py` gains five
  `worktree_anchors` cases including the bare main repo and a forced
  `FileNotFoundError`. No existing test body was modified.
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
