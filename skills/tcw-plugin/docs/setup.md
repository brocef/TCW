# Setup — install `tcw` from the plugin clone

Run when `tcw` is not yet on PATH. Installs the CLI from the plugin's *own clone*
so there is one source of truth — **don't also `pip install tcw` separately.**

1. **Resolve the plugin clone root.** Prefer `$CLAUDE_PLUGIN_ROOT` if set at
   runtime. Otherwise walk up from this file to the nearest ancestor containing
   `pyproject.toml` — that is the clone root. Do **not** hardcode a
   `~/.claude/plugins/cache/.../<version>/` path; the first cache segment is the
   marketplace/repo name and the version changes on every update.

2. **Check `pipx`** (`command -v pipx`):
   - **present →** `pipx install "<clone-root>"`. pipx owns its own venv, which
     sidesteps PEP 668 ("externally-managed-environment").
   - **absent (common) →** fallback ladder, in order:
     `python3 -m pip install --user pipx && pipx ensurepath` (then retry the pipx
     install); or `python3 -m pip install --user "<clone-root>"`; or a dedicated
     venv. **Never** `pip install` into a managed base interpreter.

3. **Verify:** `tcw --version` resolves and prints a version.

4. **Warn:** if a separate `pip install tcw` also exists, the two can drift —
   recommend keeping only the pipx install, then run `/tcw-doctor`.
