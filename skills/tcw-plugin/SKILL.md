---
name: tcw-plugin
description: Use when installing or repairing the `tcw` CLI that ships with this plugin — after installing the tcw plugin, when `tcw` is missing from PATH, or when a plugin update may have left the installed `tcw` stale. Drives `pipx`; it is the single source of the init/doctor procedure (the `/tcw-init` and `/tcw-doctor` commands are thin pointers here, and Codex — which has no slash commands — runs this skill directly).
---

# Installing & repairing the `tcw` CLI from the plugin

The plugin ships the **skills**. `tcw` itself is a Python package (entry point
`tcw = tcw.cli:main`, one dep: PyYAML, Python ≥ 3.11). This skill bootstraps the
CLI from the plugin's **own clone** so there is one source of truth.

**Mental model:** Claude Code copies the repo into a version-namespaced cache dir
(the *source of truth*); `pipx` builds an isolated venv *from* that dir (a built
copy). They are reconciled by `doctor`, not identical — "no drift" is what doctor
enforces, not a property of the layout.

## Setup (`/tcw-init`)

1. **Resolve the plugin clone root.** Prefer `$CLAUDE_PLUGIN_ROOT` if set at
   runtime. Otherwise, walk up from this skill file to the nearest ancestor
   containing `pyproject.toml` — that directory is the clone root. Do **not**
   reconstruct a hardcoded `~/.claude/plugins/cache/.../<version>/` path; the
   first cache segment is the *marketplace/repo* name (e.g. `TCW`), not the
   plugin name, and the version changes on every update.

2. **Check `pipx`.** `command -v pipx`.
   - **Present →** `pipx install "<clone-root>"`. pipx owns its own venv, which
     sidesteps PEP 668 ("externally-managed-environment").
   - **Absent →** this is common. Offer the fallback ladder, in order:
     `python3 -m pip install --user pipx && pipx ensurepath` (then retry pipx
     install); or `python3 -m pip install --user "<clone-root>"`; or a dedicated
     venv. **Never** `pip install` into a managed base interpreter.

3. **Verify:** `tcw --version` resolves and prints a version.

4. **Warn:** if the user also ran a separate `pip install tcw`, they now have two
   copies that can drift — recommend they keep only the pipx install. Run
   `/tcw-doctor` to confirm.

## Doctor (`/tcw-doctor`)

Diagnose the installed `tcw` against the active plugin clone.

1. **Locate `tcw`:** `command -v tcw` → realpath. Find its package source via
   `pipx list --json` (the venv's install spec) or
   `python3 -c "import importlib.metadata as m; print(m.distribution('tcw').locate_file(''))"`.

2. **Editable / dev install? Leave it alone.** Read
   `tcw-<ver>.dist-info/direct_url.json`; if `dir_info.editable == true`, this is
   a developer's `pip install -e` checkout — **report and do not touch it.** Warn
   that an editable shim on PATH may shadow the pipx-installed `tcw`.

3. **Find the active cache version.** List the sibling version dirs under the
   plugin's cache parent and take the highest with **`sort -V`** (lexicographic
   sort is wrong: `1.9.0` sorts above `1.12.0`).

4. **Reconcile.** If the installed source ≠ the active cache clone, the install is
   stale (a plugin update abandoned the old version dir):
   `pipx install --force "<active-clone>"`. If `--force` fails (permissions,
   dependency conflict, no network), **report the error and stop** with
   manual-fix guidance — do not silently retry.

5. **Report** PATH status, install kind (pipx / editable / plain pip / missing),
   installed vs active version, and the action taken.
