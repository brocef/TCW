# Plan — Show the tracker's untriaged tickets on `tcw work inbox list`

Seven tasks, then one documentation block. The tree is green at every boundary:
tasks 1 and 2 add capacity nothing calls yet, tasks 3–5 spend it one surface at a
time, and each commits with its own tests.

Riskiest change is **task 5** — `accept` gains a network call and strict mode
stops being a blanket refusal. It is placed last of the code tasks, after the
resolution it depends on exists (task 4) and after the same claim path is already
exercised by `tracker import`'s untouched tests.

---

## Task 1 — The `inbox-query` configuration key

**Modifies** `tcw/store/base.py`
**Modifies** `tests/test_tracker_config.py`, `tests/test_tracker_validate.py`,
`tests/test_tracker_inheritance.py`

1. Add `inbox_query: str = ""` to `TrackerConfig` (`tcw/store/base.py:1042`),
   with a comment saying why it is not `candidate_query` reused.
2. Add `"inbox-query"` to `TRACKER_KEYS` (`:1077`).
3. In `parse_tracker_config` (`:1092`), after `candidate_query` is read: absent →
   `""` and no problem; a non-string or a string that is blank after `.strip()` →
   `work.tracker.inbox-query: expected a non-empty string, got <type>`; otherwise
   the stripped value. Pass it to the `TrackerConfig(...)` construction at the
   foot of the function.

Nothing reads the field yet; this task changes no behavior.

**Proves** criteria 1–5. New tests: `inbox-query` parses and lands on the config;
absent leaves `""` with no problem; `""`, `"   "` and `42` each produce the exact
problem string and return `None` for the whole block; a child inherits a parent's
`inbox-query` and overrides it (extend `tests/test_tracker_inheritance.py`, whose
`COMPLETE`/`QUERY_ONLY` fixtures already model this); a block with `inbox-query`
and no `candidate-query` still fails.

---

## Task 2 — `InboxEntryNotFound`, so not-found is not ambiguity

**Modifies** `tcw/store/base.py`, `tcw/store/fs.py`
**Modifies** `tests/test_work.py`

1. Declare `class InboxEntryNotFound(ValueError)` in `tcw/store/base.py`, beside
   the inbox dataclasses (`InboxEntry`, `:2527`), with a docstring stating the
   contract: *no entry by this reference*, distinct from a reference that matches
   several. Name it in `inbox_show`/`inbox_accept`'s abstract docstrings
   (`:2939`, `:2943`) so it is part of the store contract, not an fs detail.
2. In `tcw/store/fs.py`, raise it at both `no such inbox entry` sites —
   `_resolve_inbox_ref` (`:5699`) and `_inbox_path` (`:5732`). The ambiguity
   raise inside `_resolve_inbox_ref` stays a plain `ValueError`.

It is a `ValueError` subclass, so `_ERRORS` (`tcw/work/cli.py:49`) catches it
unchanged and no caller moves.

**Proves** the precondition for criterion 19, and half of 20. New tests:
`inbox_show("nope")` raises `InboxEntryNotFound`; an ambiguous ref raises
`ValueError` and **not** `InboxEntryNotFound`; both still reach the CLI as today's
exit 1 with today's message.

---

## Task 3 — Two sections on `inbox list`

**Modifies** `tcw/work/cli.py`
**Modifies** `tests/test_tracker_cli.py`

Rewrite `_inbox_list` (`:448`):

1. Read the entries first, then `st.tracker_config()`.
2. When the config is `None` or its `inbox_query` is `""`: print today's
   unindented `ref | kind | title` lines and return 0. When it is `None` **and**
   `st.tracker_problems()` is non-empty, first print one stderr line naming the
   tracker configuration and pointing at `tcw validate`.
3. Otherwise print `raw intake:`, the entries indented two spaces, `  (none)` if
   there are none; a blank line; `tracker tickets:`; then the tracker rows.
4. Put the tracker half in its own function so `_inbox_list` stays readable, and
   have it import `tcw.tracker.jira` **inside** the function, as every other
   tracker path in this file does. Rows are
   `  KEY | status | assignee | summary`, `  (none)` when empty, `(not listed)`
   plus the cause on stderr and a non-zero return on `TrackerError`, and the
   `isLast: false` line on stderr naming `work.tracker.inbox-query`.

**Proves** criteria 6–13. Reuse `tests/test_tracker_cli.py`'s `node` fixture,
`_responses` transport double and `SENTINEL`; add an `inbox list` section
exercising: no tracker (exact stdout, unchanged), tracker without `inbox-query`
(exact stdout, and the transport double asserts **zero** requests), the two-section
output, the JQL actually sent is `inbox-query`'s, both `(none)` cases, truncation,
and one `TrackerError` proving the raw-intake section survived and the exit is
non-zero.

---

## Task 4 — Resolve a ref: store first, tracker second

**Modifies** `tcw/work/cli.py`
**Modifies** `tests/test_tracker_cli.py`

1. Add `--ticket` (`action="store_true"`) to both the `inbox show` and
   `inbox accept` parsers (`:2576`, `:2579`), and widen `ENTRY_HELP` (`:2564`) to
   say a ticket key is accepted when `work.tracker.inbox-query` is declared.
2. Add one resolution helper used by both commands. With `--ticket`, it skips the
   store. Otherwise it tries the store, and on `InboxEntryNotFound` — that type
   alone — falls through to the tracker when a config with a non-empty
   `inbox_query` exists. Neither `--ticket` nor a fall-through happens when no
   `inbox-query` is declared, in which case today's message is what the user sees.
3. `_inbox_show` (`:457`) on a ticket prints what `_tracker_show` (`:1900`)
   prints — key, status, summary, assignee, `claimable`, `workflow`, `note` —
   then the description from `client.description(...)`. Factor the shared body out
   of `_tracker_show` rather than copying it; `tcw work tracker show`'s output
   must not change.
4. When neither half resolves, one message naming both: no raw entry by that
   reference, and no such ticket.

**Proves** criteria 14, 15, 18, 19, 20. New tests: a raw entry resolves with zero
tracker requests even with `inbox-query` set; an unknown ref resolves as a ticket
and prints the ticket plus its description; an entry named `EX-482.md` shadows
ticket `EX-482`, and `--ticket EX-482` reaches the ticket anyway; an ambiguous ref
raises ambiguity and makes no tracker request; the neither-resolves message names
both, and names only the entry when no `inbox-query` is declared.

---

## Task 5 — `inbox accept <ticket>`, and strict mode

**Modifies** `tcw/work/cli.py`
**Modifies** `tests/test_tracker_cli.py`, `tests/test_tracker_strict.py`

1. Give `_tracker_import` (`:1976`) a `label` parameter defaulting to
   `"tracker import"`, and route every `tcw work tracker import: …` message in it
   through that label. No other behavior changes; `tracker import`'s own tests
   must pass unedited, which is what proves that.
2. Add `--part` to the `inbox accept` parser, described as `tracker import`'s is.
3. `_inbox_accept` (`:486`): resolve first (task 4). A ticket delegates to
   `_tracker_import` with `label="inbox accept"`; a raw entry continues into
   `st.inbox_accept`.
4. Move the strict refusal (`:490`) to the raw-entry branch only. A ticket is not
   refused for being strict — accepting one *is* claiming a ticket — and
   `_tracker_import`'s own strict check (`:2037`) then applies unchanged.

**Proves** criteria 16, 17, 21, 22. New tests: `inbox accept <key>` produces the
same slug, intake and `tracker.yaml` as `tracker import` for the same ticket
(assert the sidecar's parsed content, not its text); a second run prints the same
item and creates no second one; every message on the failure branches says
`tcw work inbox accept`; in `tests/test_tracker_strict.py`, strict + raw entry is
refused in today's words, and strict + ticket key is refused **only** where
`tracker import` is refused.

---

## Task 6 — The two standing guarantees, pinned

**Modifies** `tests/test_tracker_cli.py`, `tests/test_work.py`

1. Every new path and every new error branch runs under the `SENTINEL` token and
   asserts it appears in neither stream — the discipline
   `tests/test_tracker_cli.py`'s module docstring states.
2. A test that runs `inbox list`, `inbox show` and `inbox accept` in a node with
   no `work.tracker` block and asserts no `tcw.tracker*` key is in `sys.modules`
   afterwards. Import it in a subprocess, or snapshot and restore `sys.modules`,
   so an earlier test's import cannot make it pass.

**Proves** criteria 24 and 25. Criterion 23 is proved by `tests/test_tracker_*.py`
passing unedited except where a task above says otherwise.

---

## Task 7 — The capability ledger

**Modifies** `docs/capabilities/work/manage-the-work-inbox/description.md`,
`docs/capabilities/work/inspect-external-tracker-work/description.md`,
`docs/capabilities/work/manage-external-tracker-intake/description.md`,
`docs/capabilities/work/require-tracker-backed-work/description.md`

Each in the ledger's own voice (first person, what a user can do), and each only
where it has stopped being true:

- **manage-the-work-inbox** — the inbox reports raw intake *and*, where the
  project declares `work.tracker.inbox-query`, its tracker's untriaged tickets;
  `show` and `accept` take either; raw intake wins a collision and `--ticket`
  overrides.
- **inspect-external-tracker-work** — `inbox-query` named beside
  `candidate-query`, with what each selects.
- **manage-external-tracker-intake** — `inbox accept <key>` is a second door into
  the same claim, not a second claim.
- **require-tracker-backed-work** — the sentence "`tcw work new` and
  `tcw work inbox accept` refuse and point me at `tcw work tracker import`" now
  holds for a raw entry only.

Run `tcw capabilities check` after. No `tcw capabilities add` or `rm`: nothing is
new and nothing is removed, so `capabilities.yaml` carries `changed:` only.

---

## Documentation Sync

One task, after the code, over the finished diff. All five entries fire.

| Entry                                              | Trigger                  | What it gets                                                                                                                                                                  |
| -------------------------------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`                                        | Public-API               | In "Working from your Jira tickets": `inbox-query` in the config sample, what it selects versus `candidate-query`, the two-section `inbox list`, and that `show`/`accept` take a ticket. In the inbox part of `docs/guide/work.md`'s sibling prose, the precedence rule and `--ticket`. |
| `docs/release-notes/upcoming.md`                   | Public-API               | One entry, plain language: your Jira tickets waiting for triage now show up in `tcw work inbox list`, and you can read and take one without changing command.                     |
| `docs/changelogs/upcoming.md`                      | Any-Code-Change          | Added: `work.tracker.inbox-query`, the `inbox list` section, `--ticket`, `--part` on accept, `InboxEntryNotFound`. Changed: inbox ref resolution order; strict mode's accept refusal now scoped to raw entries. |
| `skills/tcw-work/SKILL.md` + `references/commands.md` | Skill-Driven-Component   | The inbox row in `commands.md`'s table gains the ticket half and the precedence rule. `skills/tcw-commands-process-inbox/SKILL.md` is the skill that drives this loop and gets the same, including that a ticket is accepted by claiming it. |
| `skills/tcw-configure/references/tracker.md`       | Configuration-Key-Change | `inbox-query` in the key list and the sample, that it is optional, that blank is a problem, and that it inherits like every other scalar key.                                      |

Also check `docs/guide/work.md:221`, which lists the inbox commands, and
`README.md:380`, whose config sample is the one users copy.

---

## Verification

Beyond the suite:

- **Against a real Jira site.** The suite replaces `JiraClient._request`
  entirely, so nothing in it proves a JQL string Jira accepts, nor that
  `/search/jql` answers the shape the section reads. Run `tcw work inbox list`
  once against a live site with a real `inbox-query`, and once with a
  deliberately malformed one, and confirm the second surfaces the tracker's own
  refusal rather than a traceback.
- **Read the two sections in a terminal.** Whether the output is legible —
  blank line, indent, section order — is not a thing a test can assert usefully.
  Check with an empty inbox, a full one, and a failing tracker.
- **Collision, by hand.** Create `docs/work/inbox/EX-482.md` in a node whose
  tracker has ticket `EX-482`, and confirm `inbox show EX-482` reads the file and
  `inbox show --ticket EX-482` reads the ticket.
- **`tcw validate`** on a node with `inbox-query`, and on one with a blank one,
  confirming the second names the key and the block reads as unconfigured.

## Notes

- Every acceptance criterion traces to a task: 1–5 → task 1; 6–13 → task 3;
  14, 15, 18, 19, 20 → task 4 (19 needs task 2); 16, 17, 21, 22 → task 5;
  23–25 → task 6. Criteria 1–25 are covered; no task exists without a criterion
  except task 7 and the documentation block, which the ledger and the
  documentation entries require independently.
- No blockers to record: no other item gates this one, and `tcw work list
  --status active` is empty.
- **The CLI is the carrier for all of it.** Nothing here rides a hook, a
  dynamic-context injection, or an agent definition, so a Codex user gets the
  same behavior as a Claude user — the harness rule the spec stage bound.
