# Doctor — diagnose & repair the `tcw` install

**Mental model:** Claude Code copies the repo into a version-namespaced cache dir
(the _source of truth_); pipx builds an isolated venv _from_ that dir (a built
copy). `scripts/session_bootstrap.sh` keeps those two reconciled — under Claude
the `SessionStart` hook runs it every session. You are here because that was not
enough: it was skipped, its install failed, or the problem is one the hook
deliberately does not touch (a shadowed, duplicated, or editable install).

1. **Locate `tcw`:** `command -v tcw` → realpath. Find its package source via
   `pipx list --json`, or
   `python3 -c "import importlib.metadata as m; print(m.distribution('tcw').locate_file(''))"`.
   Run that from outside any TCW checkout — a repo's own `tcw.egg-info` will
   answer instead of the installed distribution.

2. **Editable / dev install? Leave it alone.** Read
   `tcw-<ver>.dist-info/direct_url.json`; if `dir_info.editable == true` this is a
   developer's `pip install -e` checkout — **report and don't touch it.** Warn that
   an editable shim on PATH can shadow the pipx-installed `tcw`. (This is the same
   check the bootstrap script makes before it installs anything.)

3. **Active cache version:** list the sibling version dirs under the plugin's cache
   parent and take the highest with **`sort -V`** (lexicographic is wrong: `1.9.0`
   sorts above `1.12.0`).

4. **Reconcile:** if the installed source ≠ the active cache clone (a plugin update
   abandoned the old version dir), run
   `"<active-clone>"/scripts/session_bootstrap.sh "<active-clone>"` — the same code
   path the hook uses. It is silent on success and on every deliberate skip, so
   re-check `tcw`'s source afterwards: if it still points at the old clone, the
   script skipped because its sentinel already matched, and you should run
   `pipx install --force "<active-clone>"` directly. On a `--force` failure
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
