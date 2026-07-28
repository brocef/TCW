# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Clearer guidance when the release check can't reach your remote

The check that decides whether a version can still be folded has to ask your
remote directly — and it now says so, along with why refreshing your local copy
first doesn't substitute for it. Git keeps no local record of which tags it got
from a remote versus which you made yourself, so when the remote is unreachable
the assistant will ask you rather than guess.
