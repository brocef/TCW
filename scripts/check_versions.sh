#!/usr/bin/env bash
# Warn when the `tcw` CLI on PATH and this plugin's skills come from different
# releases.
#
#   check_versions.sh [plugin-root]
#
# The plugin root defaults to the folder above this script's own, so it needs no
# harness variable: the SessionStart hook runs it through session_bootstrap.sh
# under Claude, and every skill tells an agent under any other harness to run it.
#
# It lives in the plugin rather than in the CLI on purpose. The CLI cannot know
# which skills an agent loaded, and a check built into the CLI would be missing
# exactly when the CLI is the older side. `tcw --version` is the one question
# every release of the CLI can answer.
#
# Warn only: every path exits 0. It prints to stdout, because SessionStart adds
# stdout to the agent's context, and says nothing when the versions match or
# when it cannot find out — a missing or broken CLI is the setup skill's job.
# It must run under macOS's bash 3.2, which has no `timeout` command.

# Nothing goes to stderr, including bash's own notices about the stopped job.
exec 2>/dev/null

root="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# 1. The skills' version. Both harnesses' manifests carry it and a test keeps
#    them equal; the only "version" key in either is the top-level one.
skills=""
for manifest in "$root/.claude-plugin/plugin.json" "$root/.codex-plugin/plugin.json"; do
    [ -f "$manifest" ] || continue
    skills="$(sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([0-9]*\.[0-9]*\.[0-9]*\)".*/\1/p' "$manifest" | head -n 1)"
    [ -n "$skills" ] && break
done
[ -n "$skills" ] || exit 0

command -v tcw >/dev/null || exit 0

# 2. The CLI's version, with a 3-second deadline. The output is captured with
#    command substitution rather than a temporary file, because Codex's
#    read-only sandbox refuses every file write. Inside it, `set -m` puts the
#    background command in a process group of its own, so stopping the group
#    also stops anything it started (a version manager's shim runs the real
#    `tcw` as a child) and closes the output pipe the substitution waits on.
output="$(
    set -m
    tcw --version </dev/null &
    pid=$!
    rounds=0
    while kill -0 "$pid" 2>/dev/null; do
        if [ "$rounds" -ge 30 ]; then
            # TERM first, then KILL: a `tcw` that ignores TERM would keep the
            # output pipe open, and the substitution waits for as long as it runs.
            kill -TERM -- "-$pid"
            sleep 0.2
            kill -KILL -- "-$pid"
            exit 1
        fi
        sleep 0.1
        rounds=$((rounds + 1))
    done
    wait "$pid"
)" || exit 0

pattern='^tcw ([0-9]+)\.([0-9]+)\.([0-9]+)$'
line="${output%%$'\n'*}"
[[ $line =~ $pattern ]] || exit 0
a1="${BASH_REMATCH[1]}" a2="${BASH_REMATCH[2]}" a3="${BASH_REMATCH[3]}"
cli="$a1.$a2.$a3"
[ "$cli" = "$skills" ] && exit 0

# 3. Which side is behind decides the advice. Compared part by part as
#    numbers, so 2.10.0 is newer than 2.9.0.
#    No here-strings: bash 3.2 backs them with a temporary file.
[[ "tcw $skills" =~ $pattern ]] || exit 0
b1="${BASH_REMATCH[1]}" b2="${BASH_REMATCH[2]}" b3="${BASH_REMATCH[3]}"
newer=0
if [ "$a1" -ne "$b1" ]; then
    [ "$a1" -gt "$b1" ] && newer=1
elif [ "$a2" -ne "$b2" ]; then
    [ "$a2" -gt "$b2" ] && newer=1
elif [ "$a3" -gt "$b3" ]; then
    newer=1
fi

echo "tcw: the \`tcw\` CLI on your PATH is $cli, but the tcw plugin skills loaded in this session are from $skills. They come from different releases, so the skills may describe commands or behavior this CLI does not have, or lack ones it does."
if [ "$newer" = 1 ]; then
    echo "To bring them into line, update the plugin and restart the session:"
    echo "  Claude Code: claude plugin update tcw@tcw   (add --scope project if you installed it for one project)"
    echo "  Codex: codex plugin marketplace upgrade tcw, then codex plugin add tcw@tcw"
    echo "Or, if you installed the CLI with pipx, match it to the skills instead: pipx install --force tcw-cli==$skills"
else
    echo "To bring them into line, upgrade the CLI: pipx upgrade tcw-cli (for a development checkout, update the checkout instead)."
    echo "If that does not reach $skills, that release is not on PyPI yet; the warning will clear once it is."
fi
exit 0
