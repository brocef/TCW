#!/usr/bin/env bash
# Provision a Claude Code *remote* session working on this repository: install
# this checkout's `tcw` CLI and its dev extras, then install the `tcw` plugin
# from this checkout.
#
#   remote_session_setup.sh [--force]
#
# Session start is the only automatic caller, and only in a remote container
# (`CLAUDE_CODE_REMOTE=true`). `--force` runs it anywhere, which is how a Codex
# agent or a human provisions the same environment by hand — nothing here is
# reachable only through the Claude hook.
#
# This is *not* the published install path. `scripts/session_bootstrap.sh` is,
# and it installs the released `tcw-cli` from PyPI for a user; this installs the
# working tree for a contributor, the way .github/workflows/test.yml does. The
# two do not collide in either firing order: the bootstrap declines to replace a
# `tcw` whose interpreter reports an editable install, which is exactly what
# this leaves behind.
#
# Every path exits 0 — a session must start even when provisioning cannot — and
# only a failure prints. It prints to stdout because SessionStart adds stdout to
# the agent's context, while stderr becomes a transcript notice nobody reads.
set -u

force=0
case "${1:-}" in
    --force) force=1 ;;
    "") ;;
    *)
        echo "tcw: remote_session_setup.sh: unknown argument '${1}' (only --force is accepted)"
        exit 0
        ;;
esac

# 1. Gate. A local session provisions itself however its developer prefers;
#    picking for them at session start is not this script's call.
if [ "$force" -ne 1 ] && [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
    exit 0
fi

# 2. The checkout. $CLAUDE_PROJECT_DIR is set by the harness; the fallback is
#    what makes a hand run need no environment at all.
root="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$root" ]; then
    root="$(cd "$(dirname "$0")/.." && pwd)"
fi
[ -f "$root/pyproject.toml" ] || exit 0

# 3. Is this checkout already the installed `tcw`, dev extras and all?
#
#    The sys.path filter is load-bearing: a session's cwd is this repository, so
#    an unfiltered `import tcw` finds `./tcw/` whether or not anything is
#    installed — the same trap scripts/session_bootstrap.sh documents. With cwd
#    stripped, a `tcw` resolving inside $root can only be the editable install.
already_installed() {
    command -v tcw >/dev/null 2>&1 || return 1
    python3 - "$root" >/dev/null 2>&1 <<'PY'
import os, sys

sys.path = [p for p in sys.path if p not in ("", ".", os.getcwd())]
try:
    import tcw
    import pytest  # noqa: F401  — the [dev] extra, not the package
    import jsonschema  # noqa: F401
except Exception:
    sys.exit(1)
root = os.path.realpath(sys.argv[1]) + os.sep
sys.exit(0 if os.path.realpath(tcw.__file__).startswith(root) else 1)
PY
}

# 4. Install the checkout, dev extras included, so `tcw` and `pytest` both work
#    — the provisioning .github/workflows/test.yml performs. The retry covers an
#    image whose interpreter is marked externally managed: the container is
#    disposable and single-purpose, so installing into it is the right answer
#    there, unlike on a user's machine.
if ! already_installed; then
    if ! python3 -m pip install -e "${root}[dev]" >/dev/null 2>&1 &&
        ! python3 -m pip install -e "${root}[dev]" --break-system-packages >/dev/null 2>&1; then
        echo "tcw: 'pip install -e ${root}[dev]' failed — the tcw CLI and pytest are not available in this session."
    fi
fi

# 5. An install that landed in a user base outside PATH is installed and
#    unusable. $CLAUDE_ENV_FILE is the harness's own channel for fixing that.
if ! command -v tcw >/dev/null 2>&1 && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    userbin="$(python3 -m site --user-base 2>/dev/null)/bin"
    if [ -x "$userbin/tcw" ]; then
        echo "export PATH=\"$userbin:\$PATH\"" >>"$CLAUDE_ENV_FILE"
    fi
fi

# 6. The plugin, sourced from this checkout rather than from brocef/TCW, for the
#    same reason the Python install is editable: a session editing skills/ should
#    be running those skills. Both commands are idempotent and report the
#    already-done case as success.
#
#    User scope, never `--scope project`: the project scope writes the
#    marketplace into the repository's own .claude/settings.json, and a session
#    start has no business dirtying the working tree.
if command -v claude >/dev/null 2>&1; then
    if ! claude plugin marketplace add "$root" >/dev/null 2>&1; then
        echo "tcw: 'claude plugin marketplace add $root' failed — the tcw plugin is not installed in this session."
    elif ! claude plugin install tcw@tcw -y >/dev/null 2>&1; then
        echo "tcw: 'claude plugin install tcw@tcw' failed — the tcw plugin is not installed in this session."
    fi
else
    echo "tcw: no 'claude' on PATH — the tcw plugin was not installed (the tcw CLI is unaffected)."
fi

exit 0
