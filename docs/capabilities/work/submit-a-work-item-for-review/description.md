As a user, I run `tcw work submit <slug>` to move an item from active into review, signalling that implementation is done and acceptance is pending.
The item is not resolved while it sits in review: it still blocks whatever depends on it, and it still holds its initiative epic open, because verification can reject the work.
When the item has a tracker ticket bound to it, submitting is refused before the item moves unless the ticket is assigned to me: a claim gates work (`work/synchronize-external-tracker-work`).
Review is optional — a small change may complete straight from active, and the tool then prints a note that the verify stage was skipped rather than refusing.

TCW commits the status move itself, scoped to the item's own folders so unrelated edits in my working tree are never swept in. I turn that off with `work.auto-commit-transitions: false` in `tcw-config.yaml`, and `work.trunk-branch` adds an advisory warning when I transition from some other branch.
