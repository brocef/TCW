# Setup — install `tcw` from the plugin clone

Installs the CLI from the plugin's _own clone_ so there is one source of truth —
**don't also `pip install tcw` separately.**

Under Claude the `SessionStart` hook already ran this same reconcile, so getting
here means the automatic path did not finish the job. Under Codex there is no
hook, and this is the install path.

1. **Resolve the plugin clone root.** Prefer `$CLAUDE_PLUGIN_ROOT` if set at
   runtime. Otherwise walk up from this file to the nearest ancestor containing
   `pyproject.toml` — that is the clone root. Do **not** hardcode a
   `~/.claude/plugins/cache/.../<version>/` path; the first cache segment is the
   marketplace/repo name and the version changes on every update.

2. **Run the reconcile:** `"<clone-root>"/scripts/session_bootstrap.sh "<clone-root>"`.
   It `pipx install --force`s the clone, and skips silently when `tcw` is already
   current, when the resolved `tcw` is a developer's `pip install -e` checkout
   (never force over one), or when `pipx` is missing. Success is silent too; only
   a failed install prints.

3. **Verify:** `tcw --version` resolves and prints a version. If it does, stop.

4. **Still missing → `command -v pipx`:**
    - **present →** the install itself failed; read
      [`doctor.md`](doctor.md) and diagnose from there.
    - **absent (common) →** the script stops here on purpose: picking a Python
      environment is a judgment call that must not happen silently at session
      start. Fallback ladder, in order:
      `python3 -m pip install --user pipx && pipx ensurepath` (then re-run step
      2); or `python3 -m pip install --user "<clone-root>"`; or a dedicated venv.
      **Never** `pip install` into a managed base interpreter.

5. **Node:** only if the user plans to use `tcw serve`, run `node --version` and
   require 22.12 or newer. Do not install pnpm or run a web build:
   released/plugin package data already contains the Fastify server and React
   client.

6. **Warn:** if a separate `pip install tcw` also exists, the two can drift —
   recommend keeping only the pipx install, then run `/tcw-doctor`.
