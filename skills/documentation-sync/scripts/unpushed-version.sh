#!/usr/bin/env bash
# Is the project's most recent version tag still local-only?
#
# Answers the gate for option 5 of documentation-sync's version options: work
# since an unpublished release can be folded into it instead of stacking a
# second version on top. Run from anywhere inside the repo.
#
#   usage: unpushed-version.sh [tag-glob]     (default glob: v*)
#
# Exit codes:
#   0  FOLDABLE     — tag exists, is unpublished, and has commits after it
#   1  NOT-FOLDABLE — no tag, tag already published, or nothing to fold
#   2  UNKNOWN      — could not reach the remote; ask the user before acting
#
# Read the exit code, not the prose. Every path prints one STATUS: line first.

set -uo pipefail

glob="${1:-v*}"

say() { printf '%s\n%s\n' "STATUS: $1" "$2"; }

git rev-parse --git-dir >/dev/null 2>&1 || {
  say "NOT-FOLDABLE" "Not inside a git repository."
  exit 1
}

tag=$(git describe --tags --abbrev=0 --match "$glob" 2>/dev/null) || true
if [ -z "$tag" ]; then
  say "NOT-FOLDABLE" "No tag matching '$glob' is reachable from HEAD — nothing has been cut yet."
  exit 1
fi

# Every remote, not just the default one: a tag pushed to any of them is
# published, and picking one remote would report FOLDABLE for the others.
remotes=$(git remote)
published="no"
unreachable=""
why=""

for remote in $remotes; do
  if ! ls_remote=$(GIT_TERMINAL_PROMPT=0 git ls-remote --tags "$remote" "refs/tags/$tag" 2>&1); then
    # Note it and keep going: a definitive "published" on any other remote is a
    # better answer than UNKNOWN, and only a clean sweep can justify FOLDABLE.
    unreachable="$unreachable $remote"
    why="$why
  $remote: $ls_remote"
    continue
  fi
  if [ -n "$ls_remote" ]; then
    published="yes (tag present on '$remote')"
    break
  fi
done

# The tag itself is unpushed, but its commit may already have ridden out on a
# remote branch — the release content is public even if the label is not. This
# reads cached remote-tracking refs, so a recent `git fetch` sharpens it; it can
# only add certainty, never remove it. The per-remote `ls-remote` above stays the
# authoritative check and cannot be replaced by any amount of fetching: fetched
# tags are indistinguishable from local ones in refs/tags/.
if [ "$published" = "no" ] && [ -n "$(git branch -r --contains "$tag" 2>/dev/null)" ]; then
  published="yes (commit already on a remote branch)"
fi

if [ "$published" != "no" ]; then
  say "NOT-FOLDABLE" "$tag is published — $published. Rewriting a tag others may have fetched is off the table; cut a new version instead."
  exit 1
fi

# No remote said "published", but some could not be asked — that is not proof.
if [ -n "$unreachable" ]; then
  say "UNKNOWN" "Could not reach remote(s) to check whether $tag was pushed:$why

Do not fold on a guess — ask the user whether $tag has been published.
Running 'git fetch' first does not help: fetched tags land in the same
refs/tags/ namespace as locally-created ones, so no local ref distinguishes a
published tag from an unpushed one. Only the remote can answer."
  exit 2
fi

behind=$(git rev-list --count "$tag..HEAD" 2>/dev/null || echo 0)
if [ "$behind" -eq 0 ]; then
  say "NOT-FOLDABLE" "$tag is unpublished, but HEAD is at the tag — there is nothing since it to fold in."
  exit 1
fi

say "FOLDABLE" "$tag is unpublished (absent from: ${remotes:-no remotes configured}) and has $behind commit(s) after it:

$(git log --oneline "$tag..HEAD")

Offer to fold that work into $tag rather than cutting a new version — unless it
is too large for $tag to carry honestly, in which case recommend a fresh bump.
Procedure: references/cut-version.md → 'Folding into an unpushed version'."
exit 0
