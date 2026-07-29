#!/usr/bin/env bash
# Install or refresh the `tcw` CLI from the plugin clone.
#
#   session_bootstrap.sh [clone-root] [sentinel-path]
#
# Defaults: $CLAUDE_PLUGIN_ROOT and $CLAUDE_PLUGIN_DATA/installed-version. The
# arguments exist so the tcw-plugin skill can run this under Codex, where
# neither variable is set — nothing here may depend on them.
#
# Every path exits 0, and only a failed install prints. It prints to stdout
# because SessionStart adds stdout to the agent's context, while an exit-2
# stderr becomes a transcript notice the agent never sees.
set -u

root="${1:-${CLAUDE_PLUGIN_ROOT:-}}"
sentinel="${2:-}"
if [ -z "$sentinel" ] && [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
    sentinel="${CLAUDE_PLUGIN_DATA}/installed-version"
fi

# A developer's `pip install -e` checkout — report-and-don't-touch, per
# skills/tcw-plugin/references/doctor.md. The sys.path filter is load-bearing: a
# session's cwd is usually the project, and a `tcw.egg-info` sitting in a TCW
# checkout would otherwise answer this question instead of the real dist-info,
# turning the guard into a force-install over the dev setup.
tcw_is_editable() {
    command -v python3 >/dev/null 2>&1 || return 1
    python3 - >/dev/null 2>&1 <<'PY'
import json, os, sys
sys.path = [p for p in sys.path if p not in ("", ".", os.getcwd())]
from importlib.metadata import distribution
raw = distribution("tcw").read_text("direct_url.json") or "{}"
sys.exit(0 if json.loads(raw).get("dir_info", {}).get("editable") else 1)
PY
}

# 1. Nothing to install from.
[ -n "$root" ] && [ -f "$root/tcw/__init__.py" ] || exit 0

# 2. Steady state: what we installed still matches the clone, and it is on PATH.
#    Cheapest check first, so the every-session cost is one `cmp` and one
#    `command -v` — no interpreter starts.
if [ -n "$sentinel" ] && [ -f "$sentinel" ] &&
    cmp -s "$sentinel" "$root/tcw/__init__.py" &&
    command -v tcw >/dev/null 2>&1; then
    exit 0
fi

# 3. Leave a dev checkout alone.
if command -v tcw >/dev/null 2>&1 && tcw_is_editable; then
    exit 0
fi

# 4. Choosing a pipx bootstrap is a judgment call about someone's Python
#    environment; it does not happen silently at session start.
command -v pipx >/dev/null 2>&1 || exit 0

# 5. Install, then record what was installed. A failure leaves the sentinel
#    stale, so the next session retries with no state to clean up.
if pipx install --force "$root" >/dev/null 2>&1; then
    if [ -n "$sentinel" ]; then
        mkdir -p "$(dirname "$sentinel")" &&
            cp "$root/tcw/__init__.py" "$sentinel"
    fi
else
    echo "tcw: automatic install from $root failed — run /tcw-doctor (Codex: the tcw-plugin skill) to diagnose."
fi
exit 0
