# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## The first published release since 2.0.2

Versions 2.0.3 and 2.1.0 were tagged but never reached PyPI, so `pip install`
could not see either one. Publication runs only after the test suite passes, and
the suite had been failing on the build machine since 2026-09-11 — not because
anything TCW does was broken, but because of how the suite itself was being
started there. Nothing was wrong with the code in those two versions.

**If you were waiting on anything from 2.0.3 or 2.1.0, it is in this release.**
That includes reading your Jira tickets from the terminal, comma-separated tags,
and the corrupt-file fixes — all of it described in the notes for those two
versions, which are unchanged and still accurate.

The two faults were in the test setup and in test data, so there is no behaviour
change here for anyone installing TCW.
