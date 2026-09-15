# Tracker client operations trust the shape of Jira's response

Found by the code review of
`2026-09-14-publish-concise-progress-links-and-comments-to-a-bound-tracker-ticket`.
It needs its own change.

`JiraClient.recent_comments`, `transitions`, `search` and `issue`
(`tcw/tracker/jira.py`) all assume that a response which parsed as JSON has the
expected shape. A payload that is a list, or an entry in it that is not a mapping,
raises `AttributeError`. That error is not a `TrackerError`, so it escapes the
commands' handling of tracker errors and prints a traceback instead of a pending or
conflicting result.

**Suggested fix:** check the shape in `_json`, or in each operation. A response of
the wrong shape should raise `TrackerError` ("the tracker returned a response of an
unexpected shape for <path>"), and one test should cover each operation, as the
explicit-timeout test does.
