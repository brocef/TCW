#!/bin/sh
# Commit this work item's files after TCW moves it to a new stage.
# An opt-in example: TCW itself never changes git state.
set -eu
cd "$TCW_ITEM_PATH"
git add -A -- .
if git diff --cached --quiet -- .; then
    exit 0   # nothing to commit: normal in Jira mode, where a move may change no file
fi
git commit --quiet -m "Move $TCW_SLUG to $TCW_STAGE" -- .
