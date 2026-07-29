---
description: Diagnose the tcw CLI install — is `tcw` on PATH, is it pipx/editable/missing, does it match the active plugin-cache version — and re-point it if a plugin update left it stale.
allowed-tools: Bash(tcw *), Bash(command -v *), Bash(pipx *), Bash(python3 *)
disable-model-invocation: true
---

Read `skills/tcw-plugin/references/doctor.md` in this plugin and follow it: locate `tcw`
and its package source, detect an editable (`pip install -e`) dev install and leave
it alone, find the active cache version (sibling-dir scan with `sort -V`), and if the
installed copy is stale re-run the reconcile the `SessionStart` hook runs,
`"<active-clone>"/scripts/session_bootstrap.sh "<active-clone>"`. It is silent on
success and on every skip, so re-check `tcw`'s source afterwards — still pointing at
the old clone means it skipped on a matching sentinel, and `pipx install --force
"<active-clone>"` is then the direct fix.

Report PATH status, install kind (pipx / editable / plain pip / missing), installed
vs active version, and the action taken; on a `--force` failure, report and stop
with manual-fix guidance — do not silently retry.
