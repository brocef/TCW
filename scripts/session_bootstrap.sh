#!/usr/bin/env bash
# Install or refresh the `tcw` CLI from PyPI (the `tcw-cli` distribution).
#
#   session_bootstrap.sh [plugin-root] [sentinel-path]
#
# The plugin root is read for the plugin's version, not installed from.
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

# The `tcw` on PATH belongs to whichever interpreter its shebang names — ask that
# one, never the PATH `python3`. They are routinely different: a version
# manager's `python3` answers for whatever version is currently active, and a
# `pipx install -e` or a venv install lives outside it entirely. Getting this
# wrong is not a false alarm; it force-installs over someone's dev checkout,
# silently, every session, until the versions happen to match.
tcw_interpreter() {
    local app py
    app="$(command -v tcw)" || return 1
    IFS= read -r py <"$app" 2>/dev/null || return 1
    py="${py#\#!}"
    py="${py%% *}"
    case "$py" in
        /*/python | /*/python[0-9.]*) printf '%s\n' "$py" ;;
        # No absolute Python shebang: a version manager's shim
        # (`#!/usr/bin/env bash`), a wrapper, a binary. We cannot identify who
        # owns this `tcw`, so it is not ours to replace.
        *) return 1 ;;
    esac
}

# A developer's `pip install -e` checkout — report-and-don't-touch, per
# skills/tcw-plugin/references/doctor.md. The sys.path filter is load-bearing: a
# session's cwd is usually the project, and a `tcw.egg-info` sitting in a TCW
# checkout would otherwise answer this question instead of the real dist-info,
# turning the guard into a force-install over the dev setup.
#
# Two names, newest first. The distribution is `tcw-cli` on PyPI (`tcw` was
# taken); a checkout that predates that rename still reports `tcw`. Looking up
# only one name means a miss reads as "not editable" — which is not a false
# alarm, it force-installs over the developer's checkout, silently, every
# session. First name found decides, so the current name always wins.
tcw_is_editable() {
    "$1" - >/dev/null 2>&1 <<'PY'
import json, os, sys
sys.path = [p for p in sys.path if p not in ("", ".", os.getcwd())]
from importlib.metadata import PackageNotFoundError, distribution
for name in ("tcw-cli", "tcw"):
    try:
        raw = distribution(name).read_text("direct_url.json") or "{}"
    except PackageNotFoundError:
        continue
    sys.exit(0 if json.loads(raw).get("dir_info", {}).get("editable") else 1)
sys.exit(1)
PY
}

# 1. No plugin root: nothing tells us which plugin version we would be
#    installing for, so there is nothing to reconcile.
[ -n "$root" ] && [ -f "$root/tcw/__init__.py" ] || exit 0

# 2. Steady state: the plugin has not changed since we last installed, and `tcw`
#    is on PATH. The sentinel is a trigger token for a plugin-version change and
#    nothing more — it is *not* evidence about which `tcw-cli` PyPI resolved to,
#    which floats. `pipx upgrade tcw-cli` is how a user moves ahead of this.
#    Cheapest check first, so the every-session cost is one `cmp` and one
#    `command -v` — no interpreter starts, and no network.
if [ -n "$sentinel" ] && [ -f "$sentinel" ] &&
    cmp -s "$sentinel" "$root/tcw/__init__.py" &&
    command -v tcw >/dev/null 2>&1; then
    exit 0
fi

# 3. Only replace a `tcw` whose own interpreter reports a plain, non-editable
#    install. Anything else already on PATH belongs to someone else.
if command -v tcw >/dev/null 2>&1; then
    py="$(tcw_interpreter)" || exit 0
    tcw_is_editable "$py" && exit 0
fi

# 4. Choosing a pipx bootstrap is a judgment call about someone's Python
#    environment; it does not happen silently at session start.
command -v pipx >/dev/null 2>&1 || exit 0

# 5. Install the published CLI, then record which plugin version asked for it. A
#    failure leaves the sentinel stale, so the next session retries with no state
#    to clean up. One line on failure, and it does not try to tell a network
#    outage from a missing release — that is what the doctor is for.
if pipx install --force tcw-cli >/dev/null 2>&1; then
    if [ -n "$sentinel" ]; then
        mkdir -p "$(dirname "$sentinel")" 2>/dev/null &&
            cp "$root/tcw/__init__.py" "$sentinel"
    fi
else
    echo "tcw: automatic install of tcw-cli from PyPI failed (offline?) — run /tcw-doctor (Codex: the tcw-plugin skill) to diagnose."
fi
exit 0
