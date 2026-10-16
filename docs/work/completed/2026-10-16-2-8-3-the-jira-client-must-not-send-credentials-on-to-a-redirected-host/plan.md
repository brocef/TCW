# Plan — 2.8.3: the Jira client must not send credentials on to a redirected host

This plan follows `spec.md`. Work happens in the worktree
`.worktrees/2026-10-16-2-8-3-the-jira-client-must-not-send-credentials-on-to-a-redirected-host`
on branch `work/2026-10-16-2-8-3-the-jira-client-must-not-send-credentials-on-to-a-redirected-host`,
made from `main`. Tests run in a private virtual environment with the worktree
installed editable, never a re-pointed shared install. The board on `main` is
edited by hand.

## Task 1 — the fix

`tcw/tracker/jira.py`, `_request`: replace `add_header("Authorization", …)`
with `add_unredirected_header`, with a comment saying why.

## Task 2 — the test

`tests/test_tracker_client.py`:

- New test: two `http.server.HTTPServer` instances on `127.0.0.1`. The first
  (the configured `base_url`) answers 302 with a `Location` on
  `localhost:<other port>`; the second answers `{}`. Assert the first saw a
  `Basic` authorization header, the second was reached, and it saw none.
- The existing header test reads `request.headers`, which does not include
  unredirected headers; switch it to `request.header_items()`.
- Mutation check: revert to `add_header`, confirm the new test fails because
  the second server received the credentials, restore.

## Task 3 — documentation

`docs/changelogs/upcoming/<slug>.md` (`## Fixed`) and
`docs/release-notes/upcoming/<slug>.md` (`## Fixes`). No other documentation
entry fires: no command, option, skill or configuration key changes.

## Task 4 — verification and commit

Run the full suite with bare `pytest` from the worktree. One commit on the work
branch. No version cut, tag, merge or push.
