# Refined outcome

Accepted 2026-10-16: the owner chose to fix this in 2.8.3 as well as 3.0. Verified by the test, its mutation and the full suite below.

- `tcw/tracker/jira.py` `JiraClient._request` adds the basic-authentication
  header with `add_unredirected_header` instead of `add_header`. urllib's
  `HTTPRedirectHandler.redirect_request` copies every `add_header` header onto
  the redirected request whatever its host, so the email and API token went
  with any redirect. It is the only place in 2.8.x that sends credentials
  (`grep` for `urlopen` and `Authorization` over `tcw/`).
- New test `tests/test_tracker_client.py::test_a_redirect_to_another_host_does_not_carry_the_credentials`:
  two local servers, the first answers 302 to the second under another host
  name and port; the first sees `Basic …`, the second sees no
  `Authorization`. The existing header test reads `header_items()`, since
  `headers` leaves out unredirected headers.
- Mutation: back to `add_header` → the new test fails; restored → 50 passed.
- Full suite with bare `pytest` from the worktree (private venv first on
  `PATH`): 5232 passed, 3 skipped.
- The same fix is in the 3.0 code on the pre-freeze clean-up branch
  (`tcw/work/jira/client.py`).
