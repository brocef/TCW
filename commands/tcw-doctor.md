---
description: Diagnose the tcw CLI install — is `tcw` on PATH, is it pipx/editable/missing, is it behind the latest published release — and install or refresh it if it is missing or out of date.
allowed-tools: Bash(tcw *), Bash(command -v *), Bash(realpath *), Bash(ls *), Bash(sort *), Bash(head *), Bash(pipx *), Bash(python3 *), Bash(node --version), Bash(*/scripts/session_bootstrap.sh *), Read
disable-model-invocation: true
---

Read `skills/tcw-plugin/references/doctor.md` in this plugin and follow it: locate `tcw`
and its package source, detect an editable (`pip install -e`) dev install and leave
it alone, and if `tcw` is missing re-run the reconcile the `SessionStart` hook runs,
`"<plugin-root>"/scripts/session_bootstrap.sh "<plugin-root>"`. It is silent on
success and on every skip, so re-check afterwards — still missing means it skipped,
and `pipx install --force tcw-cli` is then the direct fix, but only once the install
has been cleared as neither editable nor unidentifiable. The CLI comes from PyPI, not
from the plugin's clone; never repair by installing from a cache directory.

Report PATH status, install kind (pipx / editable / plain pip / missing), the installed
version and whether a newer `tcw-cli` has been published (`pipx upgrade tcw-cli` is the
fix — the installed version is not required to match the plugin's), and the action taken.
On an install failure, report and stop with manual-fix guidance — do not silently retry.
