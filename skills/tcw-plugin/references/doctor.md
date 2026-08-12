# Doctor — diagnose & repair the `tcw` install

**Mental model:** `tcw` is the published `tcw-cli` distribution on PyPI, and pipx
builds an isolated venv from it. `scripts/session_bootstrap.sh` installs it when
a plugin update changes the plugin's version — under Claude the `SessionStart`
hook runs it every session. You are here because that was not enough: it was
skipped, its install failed (network, most likely — there is no offline
fallback), or the problem is one the hook deliberately does not touch (a
shadowed, duplicated, or editable install).

The plugin's own clone is **not** an install source. Never repair by installing
from a cache directory.

1. **Locate `tcw`:** `command -v tcw` → realpath → `head -1` for its shebang.
   `#!/…/bin/python…` names the interpreter that owns this install, and that
   environment's `lib/python*/site-packages/` is where its metadata lives. A
   non-Python shebang (`#!/usr/bin/env bash`) is a version manager's shim and
   names no owner — fall back to `pipx list --json`, and say plainly if that does
   not answer either. **Never let the `python3` on PATH answer for another
   environment's install:** for a pipx or venv install it is a different
   interpreter and reports no such distribution, which reads as "not editable"
   and is how a dev checkout gets clobbered.

2. **Editable / dev install? Leave it alone.** In that environment's
   site-packages, read `tcw_cli-<ver>.dist-info/direct_url.json` — or
   `tcw-<ver>.dist-info/` for a checkout predating the rename to the `tcw-cli`
   distribution; check both names before concluding there is no install. A miss
   here is not a benign "not found": it reads as "not editable" and is how a dev
   checkout gets clobbered. If
   `dir_info.editable == true` this is a developer's `pip install -e` checkout —
   **report and don't touch it.** Warn that an editable shim on PATH can shadow
   the pipx-installed `tcw`. If step 1 could not identify the owning environment,
   treat the install as untouchable for the same reason. (The bootstrap script
   makes the same call before installing anything, and an install it cannot
   identify is one it must not replace.)

3. **Missing, or present but not ours?** That is the whole question — there is no
   plugin-cache version to compare against, because nothing is installed from a
   clone. Step 2 has already settled "not ours". For a **missing** `tcw`, run
   `"<plugin-root>"/scripts/session_bootstrap.sh "<plugin-root>"` — the same code
   path the hook uses. Passing no sentinel path means it cannot take the hook's
   "already current" shortcut, but it is still silent on success and on its other
   skips: `pipx` missing, or a `tcw` on PATH it may not replace. So re-check
   afterwards: if `tcw` is still missing the script skipped, and — only once step
   2 has cleared the way — `pipx install --force tcw-cli` is the direct fix. On a
   failure (permissions, conflicts, **no network**) report and stop with
   manual-fix guidance — do not silently retry.

4. **Behind the latest release?** Report it; do not treat it as breakage. The
   installed CLI floats: the bootstrap resolves whatever PyPI had when the
   plugin last changed version, so a newer `tcw-cli` published since then is
   expected and is **not** required to equal the plugin's version. Compare
   `tcw --version` against `pipx list` / PyPI only to inform the user, and name
   `pipx upgrade tcw-cli` as the way to move forward. This is also where a
   plugin release that briefly outran its own PyPI upload becomes visible — the
   same upgrade resolves it.

5. **For `tcw serve` failures only:** run `node --version` and require 22.12 or
   newer. A missing/old-Node message is a runtime prerequisite failure; a
   "packaged web assets are missing" message means the TCW installation is
   incomplete and should be reinstalled. pnpm and `node_modules` are not part of
   installed-runtime diagnosis.

6. **Stale `tcw` pipx package alongside `tcw-cli`?** `pipx list` may show both,
   left over from an install made before the distribution was renamed. It is
   inert — pipx will not let it reclaim the `tcw` app link while `tcw-cli` owns
   it ("Not modifying"). Its install spec is a local path, so an upgrade of *it*
   resolves from that path rather than from PyPI's unrelated `tcw` project;
   `tcw-cli`, the one that matters, resolves from PyPI. Report the leftover as
   clutter the user may remove with `pipx uninstall tcw`; do not remove it for
   them.

7. **Report:** PATH status, install kind (pipx / editable / plain pip / missing),
   installed version and whether a newer `tcw-cli` exists, the action taken, and
   (only for serve diagnosis) the Node prerequisite result.
