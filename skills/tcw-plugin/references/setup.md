# Setup — install `tcw` from PyPI

Installs the CLI from PyPI, the same place a non-plugin user gets it, so there is
one artifact and one install spec. (The distribution is `tcw-cli`; `tcw` there is
an unrelated project. The command and the import package are both still `tcw`.)
A separate `pipx install tcw-cli` the user made earlier is not a conflict — it is
the same pipx package, and installing over it replaces it in place.

**This needs network.** There is no offline or air-gapped path: the plugin no
longer installs from its own clone. If PyPI is unreachable, say so plainly rather
than looking for a local source.

Under Claude the `SessionStart` hook already ran this same reconcile, so getting
here means the automatic path did not finish the job. Under Codex there is no
hook, and this is the install path.

1. **Resolve the plugin root.** Prefer `$CLAUDE_PLUGIN_ROOT` if set at runtime.
   Otherwise walk up from this file to the nearest ancestor containing
   `pyproject.toml` — that is the plugin root. Do **not** hardcode a
   `~/.claude/plugins/cache/.../<version>/` path; the first cache segment is the
   marketplace/repo name and the version changes on every update. The script
   still takes this path: it reads the plugin's version from it to decide whether
   anything needs doing, though it no longer installs from it.

2. **Run the reconcile:** `"<plugin-root>"/scripts/session_bootstrap.sh "<plugin-root>"`.
   It `pipx install --force`s `tcw-cli` from PyPI, and skips silently when `pipx`
   is missing, or when the `tcw` already on PATH is not one it may replace — a
   developer's `pip install -e` checkout (never force over one), or anything
   whose owning interpreter it cannot identify, such as a version manager's shim.
   Invoked this way it is passed no sentinel path, so it cannot take the hook's
   "already current" shortcut: it reinstalls rather than no-opping. Success is
   silent too; only a failed install prints.

3. **Verify:** `tcw --version` resolves and prints a version. If it does, stop.

4. **Still missing → `command -v pipx`:**
    - **present →** the install itself failed. The most likely cause is now
      network — check that PyPI is reachable before anything else, then read
      [`doctor.md`](doctor.md) and diagnose from there.
    - **absent (common) →** the script stops here on purpose: picking a Python
      environment is a judgment call that must not happen silently at session
      start. Fallback ladder, in order:
      `python3 -m pip install --user pipx && pipx ensurepath` (then re-run step
      2); or `python3 -m pip install --user tcw-cli`; or a dedicated venv.
      **Never** `pip install` into a managed base interpreter.

5. **Node:** only if the user plans to use `tcw serve`, run `node --version` and
   require 22.12 or newer. Do not install pnpm or run a web build:
   released/plugin package data already contains the Fastify server and React
   client.
