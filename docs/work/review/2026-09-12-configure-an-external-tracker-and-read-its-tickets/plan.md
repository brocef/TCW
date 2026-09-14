# Plan — Configure an external tracker and read its tickets

Nine tasks. The suite is green at every task boundary, and each task is one commit.
Test-first throughout: each task writes its tests, watches them fail for the right
reason, then makes them pass.

**Ordering principle.** The configuration layer lands before anything that reads
it, the HTTP seam and its error taxonomy land before anything that calls out, and
the two commands land last because they are the harness for everything beneath
them. The riskiest piece is the real socket behaviour, and it goes in task 4 where
its infrastructure exists and its tests are already written.

**From task 1 onward this session is changing `tcw/`.** The repository guide then
forbids driving the lifecycle with the `tcw` CLI, because the tool being driven is
the thing under modification. Record anything that would have been a CLI action as
a Markdown note in `docs/work/inbox/` instead, and say so rather than alternating
silently.

## Task 1 — Parse the configuration

Creates: `tests/test_tracker_config.py`.
Modifies: `tcw/store/base.py` — add `TrackerConfig` beside the other frozen config
dataclasses, `parse_tracker_config` beside `parse_documentation_entries`
(`tcw/store/base.py:1590`), and the two concrete `WorkStore` methods
`tracker_config` and `tracker_problems` beside `retention_problems`
(`tcw/store/base.py:2102`).
Modifies: `tcw/store/fs.py` — `FsWorkStore.tracker_config` and
`tracker_problems`, reading through `_work_config` (`tcw/store/fs.py:5051`).

`parse_tracker_config(raw) -> (TrackerConfig | None, list[str])`. Required keys:
`provider` (must equal `jira-cloud`), `base-url`, `candidate-query`,
`credentials.email-env`, `credentials.token-env`, `transitions.claim`. Optional:
`timeout-seconds`, default 15, must be a positive number. Any unknown key at any
level is a problem. Any problem means the returned config is `None` — it fails
closed, and `TrackerConfig` carries no credential value, only the two variable
names.

Proves it: `tests/test_tracker_config.py` covers each required key absent, a
non-mapping where a mapping belongs, an unknown key at both levels, a bad
`provider`, a non-positive `timeout-seconds`, the `strict` key reported as unknown,
and a valid block parsing with the default timeout applied. Plus two the review
made necessary: a config with one problem returns `None` rather than a partial
object, and `TrackerConfig` has no attribute holding a token.

Acceptance criteria reached: 4, 5, 6 in part, 14.

## Task 2 — Surface the problems through validate, and prove the board survives

Modifies: `tcw/validate.py` — add the tracker problems beside the retention lines
at `tcw/validate.py:267`, reading the store method directly rather than through
`check()`.
Creates: `tests/test_tracker_validate.py`.

Reading directly, not through `check()`, is the point: `check()` returns an
undifferentiated problem list, and going around it is what keeps this simple.

Proves it: `tcw validate` exits non-zero and names the missing key for each
required key; `tcw work list` exits zero and prints the board with a malformed
`work.tracker` present. The second assertion is the one that matters, and it is
written as a test rather than trusted, because "a malformed key must not break the
board" is the contract this whole layer exists to keep.

**Also proves the hard non-goal:** a test asserting `tcw validate` completes with
the credential variables unset and `base-url` pointing at an unroutable address,
within one second. That is criterion 7, and it is the guard against anyone later
putting a network call on the completion path.

Acceptance criteria reached: 4, 5, 6, 7.

## Task 3 — The HTTP seam, with no network

Creates: `tcw/tracker/__init__.py`, `tcw/tracker/jira.py`,
`tests/test_tracker_client.py`.
No change to `pyproject.toml`. Checked rather than assumed:
`find_packages(include=["tcw*"])` matches dotted subpackage names, so
`tcw.tracker` is already covered by the existing glob.

`_request(method, path, body=None) -> (status, headers, bytes)` is the only
function that touches `urllib.request`. It builds the basic-authentication header
from the two environment variables named in the config, reading them here and
nowhere else, and passes `timeout` on every call.

Then `myself()`, `search(jql, limit=50)`, `issue(key)`, `transitions(key)` on top
of it. `search` reports truncation explicitly when more rows match than `limit`.

Proves it: tests substitute `_request` and assert each operation's path, method and
body. One test asserts every operation passes a non-`None` timeout — written by
listing the operations and checking each, so a sixth operation added later without
a timeout fails this test.

Acceptance criteria reached: none completely; this is the floor for 8 and 9.

## Task 4 — The error taxonomy and the real socket

Modifies: `tcw/tracker/jira.py` — `TrackerError` and the six subclasses, and the
status-to-exception mapping inside `_request`.
Modifies: `tests/test_tracker_client.py`.

The six: `TrackerAuthError` (401), `TrackerPermissionError` (403),
`TrackerNotFound` (404), `TrackerRequestInvalid` (400),
`TrackerRateLimited` (429, carrying `Retry-After`), `TrackerUnavailable` (5xx,
connection failure, timeout).

**The riskiest test in the item goes here**, now that the seam exists and the
stubbed tests are written: a real `socket` bound to a loopback port that accepts a
connection and never writes, asserting `TrackerUnavailable` is raised within the
configured timeout. This is the one place a genuine `urllib` mistake cannot hide
behind a stub, which is why it is a real socket and not a mock.

Proves it: one test per status, and the socket test. Plus a negative test that no
module in `tcw/tracker/` contains the string "already claimed" or "conflict" in any
exception name or message — the experiment found three different 400 bodies for the
same condition, one blaming permissions, and this test is what keeps a future
change from inferring a claim from a 400.

Acceptance criteria reached: 8 in part, 9.

## Task 5 — Claimability from the ticket

Modifies: `tcw/tracker/jira.py` — a pure function taking the configured claim
transition name, the ticket's current status, and the transitions the ticket
offers, returning one of `claimable` / `not-claimable`, and one of `exclusive` /
`not-exclusive` / `not-determined`, plus a misconfiguration verdict.
Creates: `tests/test_tracker_claimability.py`.

Pure, taking data rather than a client, so it is tested without any HTTP at all.
The rules:

1. Claimable when the configured name is among the offered transitions.
2. Exclusivity is answerable **only** when the ticket's current status equals the
   status the claim transition leads to. Otherwise `not-determined`.
3. In the landing status: offered means `not-exclusive`, absent means `exclusive`.
4. When the configured name matches no offered transition and the ticket is in a
   status from which the claim should be possible, that is a misconfiguration; the
   verdict names the configured value and lists the offered names.
5. When the configured name matches more than one offered transition, refuse and
   say so rather than choosing.

Proves it: one test per rule, and one per fixture shape using the transition lists
already recorded in the epic's `jira-claim-experiment.md` as literals. Those
literals are real measured responses, which is why they are worth using instead of
invented data.

Acceptance criteria reached: 11 and 13 in part; the live halves come in task 8.

## Task 6 — The commands

Modifies: `tcw/work/cli.py` — a `tracker` subparser group beside `tombstone`
(`tcw/work/cli.py:1891`), with `list` and `show`; add `"tracker"` to `SUBCOMMANDS`
(`tcw/work/cli.py:39`).
Creates: `tests/test_tracker_cli.py`.

`list` prints key, status, assignee, summary per row. `show` prints the ticket's
content, assignee, status, and the claimability report from task 5, using the word
**exclusive** for the workflow property and **claimable** for the ticket's current
state. Never the same word for both.

With no tracker configured, both exit non-zero naming `work.tracker`.

Each of the six error causes gets its own message and exit 1, per the spec's table.
The message names the environment variable for an auth failure and the timeout for
an unavailable tracker, and no message contains a credential value.

Proves it: `tests/test_tracker_cli.py` with `_request` substituted — one test per
error cause asserting the distinct message, the unconfigured case, and a
happy-path `list` and `show`. Plus the secret test: set the token variable to a
sentinel, exercise every command and every error branch, and assert the sentinel
appears in no captured stdout, no captured stderr, and no file under the work
store.

Acceptance criteria reached: 3, 8, 10.

## Task 7 — The unconfigured-project baseline

Creates: `tests/test_tracker_absent.py`.

Builds a fixture node with `python evals/seed_fixture.py`, runs `tcw work list`,
`tcw work show <the fixture's item>` and `tcw validate` against it with no
`work.tracker` key, and compares stdout, stderr and exit code **stream by stream**
against the expected values recorded from this item's branch point.

This is criterion 1, and it is last among the code tasks because it is the
regression net for all six before it. It is a fixture node rather than this
repository because this item's own artifacts and its capability flip change what
`validate` scans and what the board prints, so the live repository cannot produce a
stable baseline.

Acceptance criteria reached: 1.

## Task 8 — The three live checks, then recorded as replay fixtures

Creates: `tests/fixtures/tracker/*.json` — the captured responses.
Modifies: `tests/test_tracker_claimability.py` and `tests/test_tracker_cli.py` to
replay them.

Run by hand against the two Atlassian fixtures, using `~/.claude/bin/jira` or the
built client:

1. `tracker show` on a conforming-fixture ticket in the landing status reports
   **exclusive**; the same on the non-conforming fixture reports **not exclusive**;
   a ticket outside the landing status reports **not determined**.
2. `tracker list` prints one row per ticket the query selects; `tracker show`
   prints a named ticket's status and assignee.
3. With `transitions.claim` set to a name the workflow does not have, `tracker
   show` reports the misconfiguration and lists the offered names.

Then commit the captured responses and add replay tests, so the site is touched
only by a deliberate re-verification afterwards.

Record the run in `outcome.md`: the date, the two project keys, the ticket keys,
and what each printed.

Acceptance criteria reached: 11, 12, 13.

## Task 9 — Documentation Sync

All four configured entries fire. Scheduled as one block after the code settles,
which is what the stage instructions ask for.

| Entry | Trigger | What this item adds |
| ----- | ------- | ------------------- |
| `README.md` | Public-API | The `work.tracker` configuration block and the two commands, in the CLI usage section. |
| `docs/release-notes/upcoming.md` | Public-API | Plain language: you can point TCW at your Jira site and see your assigned tickets in the terminal, and it will tell you when a ticket's workflow would let two people claim it at once. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | Added: `work.tracker` config, `tcw/tracker/jira.py`, the six-way error taxonomy, `tcw work tracker list`/`show`. Internal: `tracker_config`/`tracker_problems` on `WorkStore`. |
| `skills/tcw-work/references/commands.md` | Skill-Driven-Component | The two commands in the command reference, with the configuration block and the note that neither writes anything. |

Also: `docs/guide/work.md` gains the prose, and `"tcw work tracker"` goes into
`DOCUMENTED_VERBS` (`tests/test_documented_cli_surface.py:246`). That tuple is
explicitly not derived from the CLI, so this is a deliberate addition, and it is the
one existing test this item edits. Criterion 2 permits exactly that and no more.

**Do not cut a version.** The epic batches the version cut across the run and cuts
it when C1 and C2 are both publishable.

## Verification

What the suite cannot settle.

1. **The three live checks.** Task 8. No stub can prove the client works against
   real Jira; only Jira can.
2. **That no secret reaches Jira or a log this repository does not own.**
   Criterion 10's grep covers TCW's own output and store. Read the request
   construction in `_request` by hand and confirm the token appears only in the
   authorization header.
3. **That `tcw work complete` still works offline on a tracker-configured node.**
   Criterion 7 asserts `tcw validate` makes no network call, which is the
   mechanism. Confirm the behaviour end to end by hand: configure a tracker, unset
   the credential variables, disconnect, and complete a throwaway item.
4. **That the claimability wording is not misleading.** Read the two messages side
   by side and confirm a reader cannot mistake "claimable" for "exclusive". A test
   can check the strings are different; only a person can check they are clear.
5. **Team-managed project behaviour.** Unverified, and named as such in the spec.
   Worth one manual check against a team-managed project if one is available; if
   not, say so in `outcome.md` rather than leaving it implied.

## Notes

**Task order is not negotiable between tasks 3 and 4.** The seam has to exist
before the error taxonomy has anywhere to live, and the stubbed tests have to exist
before the real socket test, or a failure in task 4 is ambiguous between the
mapping and the transport.

**The claimability function in task 5 takes data, not a client.** That is what makes
the fixture literals from the experiment usable directly, and it is why task 5
needs no HTTP at all.

**If task 8's live run contradicts task 5's literals**, the literals are what is
wrong, not the live site. Re-record them and say so in `outcome.md`.
