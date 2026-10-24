#!/bin/sh
# Commit this work item's files after TCW moves it to a new stage.
# An opt-in example: TCW itself never changes git state.
set -eu
cd "$TCW_ITEM_PATH"
# Items nested in this one's folder are theirs to commit, so each folder
# below holding tcw-work-item.yaml is left out. The search skips what TCW
# never looks in for items: hidden folders, resources/, comments/ and the
# stage folders, whose names are the stages of STAGES in tcw/work/model.py.
# A folder it cannot read stops the hook before anything is staged.
found=$(find . \( -type d ! -path . \( -name '.*' -o -name resources \
    -o -name comments -o -name inbox -o -name request -o -name spec \
    -o -name plan -o -name implement -o -name review -o -name qa \
    -o -name completed -o -name discarded -o -name postmortem \) -prune \) \
    -o \( -type f -name tcw-work-item.yaml ! -path ./tcw-work-item.yaml -print \))
set -- .
while IFS= read -r state; do
    if [ -n "$state" ]; then
        set -- "$@" ":(exclude)${state%/tcw-work-item.yaml}"
    fi
done <<FOUND
$found
FOUND
git add -A -- "$@"
if git diff --cached --quiet -- "$@"; then
    exit 0   # nothing to commit: normal in Jira mode, where a move may change no file
fi
git commit --quiet -m "Move $TCW_SLUG to $TCW_STAGE" -- "$@"
