# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `scripts/session_bootstrap.sh` (mode 755) — the whole install/refresh reconcile
  for the `tcw` CLI, in one executable:
  `session_bootstrap.sh [clone-root] [sentinel-path]`, defaulting to
  `$CLAUDE_PLUGIN_ROOT` and `$CLAUDE_PLUGIN_DATA/installed-version`. The explicit
  arguments are what let a Codex agent run the identical code path with neither
  variable set. Check order, each exiting 0: unresolvable clone root → sentinel
  matches the clone's `tcw/__init__.py` *and* `tcw` is on PATH → editable
  (`direct_url.json` → `dir_info.editable`) install → `pipx` absent → otherwise
  `pipx install --force`, then copy `tcw/__init__.py` to the sentinel. The
  sentinel is written only after a successful install, so a failure leaves it
  stale and the next session retries with no state to clean up. Silent on success
  and on every deliberate skip — including the pipx-missing skip, which the spec's
  Non-goals described as "reports and stops"; that contradicted the silent-skip
  rule and silence won, with `references/setup.md` carrying the compensating flow
  (run the script → verify `tcw --version` → only then check `command -v pipx`
  yourself and take the ladder). Only a failed install prints, one line to
  **stdout with exit 0** — `SessionStart` adds stdout to the agent's context,
  while an exit-2 stderr becomes a transcript notice the agent never sees:
  `tcw: automatic install from <clone-root> failed — run /tcw-doctor (Codex: the
  tcw-plugin skill) to diagnose.` The Codex parenthetical is deliberate; the line
  is read by an agent under either harness and Codex has no slash commands. The
  editable probe strips `""`/`"."`/cwd from `sys.path` before reading
  the distribution metadata: a session's cwd is usually the project, and a
  `tcw.egg-info` in a TCW checkout would otherwise answer instead of the real
  dist-info, inverting the guard into a force-install over the dev setup.
- `hooks/hooks.json` — one `SessionStart` command hook invoking
  `"${CLAUDE_PLUGIN_ROOT}"/scripts/session_bootstrap.sh`. `SessionStart` cannot
  block startup and its command timeout is 600s, so a slow first install delays
  nothing.
- `tests/test_session_bootstrap.py` — the script's behavior under a fake `pipx`
  shim prepended to `PATH`, one test per acceptance criterion (steady state,
  editable install, pipx absent, failing pipx, successful install then silent
  re-run). Hermetic: no test invokes real pipx or touches the developer's install.
- `test_hooks_manifest_wires_one_executable_session_start_script` in
  `tests/test_plugin_manifests.py` — asserts the manifest's `hooks` path resolves,
  that exactly one `SessionStart` command is registered, and that the referenced
  script exists and is executable. `claude plugin validate` catches a broken path;
  nothing else catches a lost executable bit, which fails silently at runtime.
- `tcw work edit <slug> --title "<title>"` — retitle an existing work item.
  `update_work` already accepted `title` and `tcw serve` already drove it that
  way; `_edit` now passes it through, so the CLI is no longer the one surface
  that cannot rename an item. The slug is not recomputed, so existing references
  keep resolving.
- `_nonempty` argparse validator in `tcw/work/cli.py`. `--title ""` (or
  whitespace) is rejected at the parser with exit 2. Without it, `_provided`
  passes the empty string to `update_work`, which writes `state["title"] = ""` —
  a titleless item, which `create_work` explicitly refuses to create.

## Changed

- `.claude-plugin/plugin.json` declares `"hooks": "./hooks/hooks.json"`. The root
  location is auto-discovered, but the manifest already lists `skills` and
  `commands` explicitly, so the key matches the file's convention.
- `skills/tcw-plugin/references/setup.md` and `references/doctor.md` both
  delegate the reconcile to `scripts/session_bootstrap.sh "<clone-root>"` instead
  of restating its steps, keeping only the judgment the script does not encode:
  setup keeps the pipx-missing fallback ladder (`pip install --user pipx`, `pip
  --user`, a dedicated venv), doctor keeps install-kind classification, the
  `sort -V` cache-version scan, and Node/`tcw serve` diagnosis. Doctor also now
  notes that the script is silent on skips, so its source must be re-checked
  afterwards — a sentinel that already matches makes the script a no-op, and
  `pipx install --force` is then the direct fix. This is what makes the behavior
  identical under both harnesses rather than a Claude-only bonus; treat a
  regression here as functional, not cosmetic.
- `skills/tcw-plugin/SKILL.md` — frontmatter `description` and the
  "Installing & repairing" router describe an automatic install with the script
  as the manual entry point, and name only `/tcw-doctor`.
- `commands/tcw-doctor.md` — the router's one-line summary said the procedure
  ends in `pipx install --force`; it now names the bootstrap script, the silent-on-
  skip re-check, and `--force` as the fallback when the script skipped on a
  matching sentinel. Thin router still: the procedure stays in `doctor.md`.
- `README.md` — the Claude install snippet drops `/tcw-init` and tells the user to
  start a new session (a hook installed mid-session does not fire until the next
  one); the command inventory, routing note, Codex paragraph, and skills list drop
  it too. Historical `docs/changelogs/v0.2.0.md`, `docs/changelogs/v0.9.0.md`, and
  `docs/release-notes/v0.2.0.md` keep their `/tcw-init` mentions as archive.
- The `tcw work edit` subcommand help now reads "change an item's title,
  estimates, tags, or blocking links". It previously claimed the command changes
  blocking links, which had been incomplete since `--priority`, `--effort`,
  `--complexity`, `--initiative`, and `--tag` were added.
- `FsWorkStore.create` now delegates to `create_work` and returns
  `get_detail(...).item`; its duplicate write path (`_unique_slug`, parent
  resolution, `mkdir`, `write_text`, `dump_yaml`, `_stage`) is deleted. Two
  behavioral deltas follow, both deliberate: an empty title now raises
  `ValueError` where it previously produced a degenerate item, and `priority` is
  omitted from `state.yaml` when unset rather than written as `null` (every
  reader goes through `load_yaml` + `.get()`, so the two are equivalent).
  `tcw/store/base.py` is unchanged — `WorkStore.create` stays declared.

## Fixed

- `_atomic_write_all(pairs)` in `tcw/store/fs.py` — a module-level sibling of
  `_atomic_write` that writes several files as one unit: stage every
  `<path>.tmp`, then `replace` each in turn. A content-production failure
  (ENOSPC, EACCES, a serialization error) can only happen in the staging phase,
  before anything is promoted, so the targets are untouched. A single
  `except BaseException` spans both phases and unlinks every temp, so no `.tmp`
  is left beside a real file and a `KeyboardInterrupt` mid-batch still cleans up.
- `FsTreeStore._write_node` uses the helper and rolls back with
  `shutil.rmtree(..., ignore_errors=True)` when — and only when — it created the
  directory (`existed` captured before `mkdir`). This is the shared helper behind
  every taxonomy and capability add/update, so `add`, `update_term`, and
  `update_capability` all inherit it without being patched individually.
- `FsCapabilitiesStore.update_capability` additionally carries the same rollback
  itself. It `mkdir`s before dispatching, so `_write_node`'s `existed` is already
  `True` by the time it runs, and its other two branches go through `_write_meta`,
  which does not create the directory at all. The guard wraps all three, which is
  what makes fresh-override materialization all-or-nothing.
- `FsCapabilitiesStore.set` — the path `tcw capabilities set` actually uses,
  where `update_capability` is web-editor-only — carries the same guard. It
  materializes a fresh override through `_write_target` and previously wrote
  `meta.yaml` with no rollback, leaving an empty override directory on failure.
  Single-file, so never a partial object; the residue is what changed.
- `_write_node` and `_write_meta` now document that they stage internally, so any
  caller wrapping them in a rollback must key it on whether content landed.
- `FsWorkStore.create_work` wraps its two writes in the same rollback. `mkdir`
  without `exist_ok` proves the directory is ours, so the rmtree is
  unconditional.
- `FsWorkStore.update_work` writes `state.yaml` and the body through the helper.
  The pair list is 1 or 2 entries — the body is still written only when one is
  supplied, so an unchanged body never churns its revision hash.
- No rollback destroys content that landed. In `_write_node` and `create_work`,
  staging (`self._stage`) simply sits outside the rollback, so a git failure
  after both files are written leaves a fully valid object on disk. In
  `update_capability` it cannot: staging happens inside `_write_node`, which the
  guard has to wrap. That rollback therefore keys on whether `meta.yaml` landed
  rather than on who created the directory — a content failure promotes nothing
  and rolls back, a successful write followed by a failed `git add` keeps the
  files and leaves them merely unstaged.
- Known ceilings, carried as `# ponytail:` comments in the code: the promote loop
  is not atomic across files (a process death between two `replace()` calls still
  leaves a partial update; the upgrade is a journal or the whole-directory swap
  `accept_inbox` already uses), and `_write_node`'s `existed` check is TOCTOU-racy
  under concurrent writers — tracked by
  `2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos`.

## Removed

- `commands/tcw-init.md`. The command was a thin router to the setup procedure
  the hook now runs unprompted, so it had no remaining job. `/tcw-doctor` is
  unaffected. An already-installed plugin may keep a stale `/tcw-init` until it is
  reinstalled; it routes to the rewritten `setup.md`, which runs the same script,
  so the worst case is a redundant-but-correct action.

## Internal

- New capability `work/retitle-a-work-item`.
- Backlog maintenance: findings from the 2026-07-28 audit trial folded into
  `2026-07-03-transactional-multi-file-writes-in-the-fs-store`,
  `2026-06-22-concurrency-safe-work-claims-…`, and
  `2026-07-01-transitive-taxonomy-inheritance`. The concurrency item's assumption
  that an external work root is "the only new branching" is corrected in place —
  `FsTreeStore` derives `node_root` from `root`, and `node_root` is what git
  operations, the sentinel reader, and hook cwd key off.
