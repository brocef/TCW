As a user, I run `tcw work submit <slug>` to move an item from active into review, signalling that implementation is done and acceptance is pending.
The item is not resolved while it sits in review: it still blocks whatever depends on it, and it still holds its initiative epic open, because verification can reject the work.
Review is optional — a small change may complete straight from active, and the tool then prints a note that the verify stage was skipped rather than refusing.
