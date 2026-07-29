# Doctor — diagnose & repair the `tcw` install

**Mental model:** Claude Code copies the repo into a version-namespaced cache dir
(the _source of truth_); pipx builds an isolated venv _from_ that dir (a built
copy). `scripts/session_bootstrap.sh` keeps those two reconciled — under Claude
the `SessionStart` hook runs it every session. You are here because that was not
enough: it was skipped, its install failed, or the problem is one the hook
deliberately does not touch (a shadowed, duplicated, or editable install).

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
   site-packages, read `tcw-<ver>.dist-info/direct_url.json`; if
   `dir_info.editable == true` this is a developer's `pip install -e` checkout —
   **report and don't touch it.** Warn that an editable shim on PATH can shadow
   the pipx-installed `tcw`. If step 1 could not identify the owning environment,
   treat the install as untouchable for the same reason. (The bootstrap script
   makes the same call before installing anything, and an install it cannot
   identify is one it must not replace.)

3. **Active cache version:** list the sibling version dirs under the plugin's cache
   parent and take the highest with **`sort -V`** (lexicographic is wrong: `1.9.0`
   sorts above `1.12.0`).

4. **Reconcile:** if the installed source ≠ the active cache clone (a plugin update
   abandoned the old version dir), run
   `"<active-clone>"/scripts/session_bootstrap.sh "<active-clone>"` — the same code
   path the hook uses. Passing no sentinel path means it cannot take the hook's
   "already current" shortcut, but it is still silent on success and on its other
   skips: `pipx` missing, or a `tcw` on PATH it may not replace (step 2's editable
   case, or one whose owner it cannot identify). So re-check `tcw`'s source
   afterwards: if it still points at the old clone the script skipped, and — only
   once step 2 has cleared this install as neither editable nor unidentifiable —
   `pipx install --force "<active-clone>"` is the direct fix. On a `--force` failure
   (permissions, conflicts, no network) report and stop with manual-fix guidance —
   do not silently retry.

5. **For `tcw serve` failures only:** run `node --version` and require 22.12 or
   newer. A missing/old-Node message is a runtime prerequisite failure; a
   "packaged web assets are missing" message means the TCW installation is
   incomplete and should be reinstalled. pnpm and `node_modules` are not part of
   installed-runtime diagnosis.

6. **Report:** PATH status, install kind (pipx / editable / plain pip / missing),
   installed vs active version, the action taken, and (only for serve diagnosis)
   the Node prerequisite result.
