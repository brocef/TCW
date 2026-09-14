# Plan — Claim an external tracker ticket and bind it to a work item

Builds `spec.md` as revised at `4701bc7c`. Criterion numbers below are that
spec's. Every task is one commit, and the full suite (`python -m pytest -q`) is
green at each commit boundary.

**Where the work happens.** `tcw work start <slug> --worktree`, then follow the
project guide's worktree instructions: re-point the editable install at the
worktree (`pip install -e <worktree> --no-deps`) and run pytest and the CLI from
the worktree root. Restore it (`pip install -e /Users/brian/Projects/TCW`) before
completing. While `tcw/` is being edited, record any side findings as Markdown in
`docs/work/inbox/` rather than through the `tcw` CLI, per the guide.

**Order, and why.** The sidecar and binding rules come first because they are pure
and every later task reads them. The client writes come next, still with no
decision logic. The claim sequence — the riskiest code, and the one the review
found three defects in on paper — is task 4, isolated in its own module with its
own stateful fake, before any command calls it. Commands follow, then the one
inbox note, then documentation, then the ledger.

## Task 1 — Register the `tracker.yaml` sidecar

Modifies:

- `tcw/store/base.py` — add the `tracker.yaml` entry to `WORK_SIDECARS` (line
  1928) exactly as spec Design part 2 shows, with a comment in the style of the
  `rollup.md` entry saying a command writes it and edit surfaces must not offer
  to.

Creates:

- `tests/test_tracker_binding.py` — first two tests:
  - `write_sidecar` then `read_sidecar` of a `tracker.yaml` mapping round-trips,
    and a YAML list is refused with `ValueError` (the existing `yaml_mapping` rule).
  - `GET /api/work/<slug>/sidecars` through the serve test client reports
    `tracker.yaml` with `generated: true`. Reuse the server setup that
    `tests/test_serve_write.py` uses around its `rollup.md` assertion (line 170).

Proves it: criterion 17. `python -m pytest tests/test_tracker_binding.py
tests/test_serve_write.py tests/test_store_editor.py -q`, then the full suite.

## Task 2 — Binding rules in `tcw/tracker/intake.py`

Creates `tcw/tracker/intake.py` with the pure half of the module. No client, no
network.

- `validate_part(value) -> str` — `[a-z0-9][a-z0-9-]*`, default `default`; raises
  `ValueError` naming the value.
- `read_binding(content: str | None)` — returns one of three frozen dataclasses,
  `Unbound`, `Bound(provider, project, part, ticket_id, ticket_key, ticket_url)`
  or `Malformed(reason)`, by exactly the five rules in spec Design part 2
  "Reading a binding".
- `binding_document(*, provider, project, part, ticket_id, ticket_key,
  ticket_url, account_id, account_name, bound, unlinked) -> str` — YAML text with
  the keys in the spec's order, `schema: 1`, `unlinked` carried as given.
- `unlink_document(existing: dict, *, reason, today) -> str` — moves `provider`,
  `project`, `part`, `ticket`, `claimed-by`, `bound` into a new `unlinked` entry
  with `unlinked-on` and `reason`; keeps `schema` and prior `unlinked` entries.
- `find_binding(store, *, project, provider, ticket_id, part) -> str | None` —
  iterates `store.query()`, skips items whose status is in `RESOLVED_STATUSES`,
  reads `store.read_sidecar(slug, "tracker.yaml")`. Returns the one matching slug
  or `None`. Raises `BindingProblem` (a `ValueError` subclass) naming the slug for
  any `Malformed` binding it meets, and naming both slugs when two match.

`project` is passed in as a string. This module imports nothing from
`tcw.store.fs`.

Adds to `tests/test_tracker_binding.py`, against a real `FsWorkStore` in a
`git init`ed temporary node (the `node` fixture shape in
`tests/test_tracker_cli.py:57-74`):

- each of the five reading rules, including `ticket: TCWCLAIM-6` → `Malformed`
  and an unlinked document → `Unbound`;
- `validate_part` accepts `api`, `default`; refuses `API`, `-x`, `a b`, `""`;
- `find_binding` finds a match by `(project, provider, ticket_id, part)` and
  misses on each field differing; ignores a match on a `completed` item; raises
  naming the slug for a YAML-list binding on a `backlog` item; raises naming both
  slugs for two matches; ignores both of those on `completed` items;
- `binding_document` → `read_binding` gives `Bound` with the same values;
  `unlink_document` → `read_binding` gives `Unbound`, and a second
  `unlink_document` after re-binding keeps two history entries.

Proves it: the binding half of criterion 13 at unit level.
`python -m pytest tests/test_tracker_binding.py -q`.

## Task 3 — Jira client writes

Modifies `tcw/tracker/jira.py`:

- `issue(key)` — quote the key with `urllib.parse.quote(key, safe="")` in the
  path (line 214).
- `apply_transition(issue_id, transition_id) -> None` —
  `POST /rest/api/3/issue/{issue_id}/transitions`, body
  `{"transition": {"id": transition_id}}`, via `_json`.
- `assign(issue_id, account_id) -> None` —
  `PUT /rest/api/3/issue/{issue_id}/assignee`, body `{"accountId": account_id}`.
- `description(issue_id) -> str` —
  `GET /rest/api/2/issue/{issue_id}?fields=description`; returns the string, or
  `""` when it is `null` or not a string.
- Module and class docstrings: drop "read-only"; say the writes exist for the
  claim and that a write's response is never interpreted beyond success or its
  error type.

Modifies `tests/test_tracker_client.py`:

- **Adds** three entries to `OPERATIONS` (line 172). This is the list
  `test_every_operation_is_accounted_for_here` requires to name every public
  operation, so the addition is what that test exists to force. It adds lines and
  removes none; record it in `outcome.md` all the same, since the epic's
  criterion 1 check reads `tests/` diffs.
- New tests, using the file's existing `Recorder`: each write sends the method,
  path and body above; `issue("a/b")` requests `/rest/api/3/issue/a%2Fb`;
  `description` returns the string, and `""` for `null`.

Proves it: `python -m pytest tests/test_tracker_client.py -q`, including
`test_every_operation_passes_an_explicit_timeout` over the three new operations.

## Task 4 — The claim sequence

Adds to `tcw/tracker/intake.py`:

- `ClaimOutcome` — frozen dataclass: `claimed: bool`, `row: str` (`"1e"`, `"3a"`,
  … — the spec's row ids, so tests assert rows rather than message text),
  `message: str` (the fixed first line), `detail: str`, and on success
  `issue_id`, `key`, `url`, `summary`, `status`, `account_id`, `account_name`,
  `transitioned: bool`.
- `read_ticket(client, key)` — `issue`, `transitions`, `myself`, returning the
  values step 1 needs. Split out so import can run the lookup between reading and
  claiming.
- `claim(client, ticket) -> ClaimOutcome` — spec Design part 1, steps 1–3,
  exactly: the six step-1 rows, step 2's four transition results with assign only
  after **applied**, and the six step-3 rows. Landing status from
  `assess(...).landing_status`; *landed* uses `claim._normalize` and
  `statusCategory.key != "done"`. `stop` errors propagate as the `TrackerError`
  they are, so the CLI prints C1's message.

Creates `tests/tracker_fake.py`, a stateful fake tracker shared by tasks 4–6:

- holds issues (id, key, summary, status name and category, assignee, description)
  and a workflow: a mapping of status → offered transitions, one **directed**
  (claim offered only from `To Do`, like `TCWCLAIM`) and one **global** (every
  transition from every status, like `TCWTEST`);
- serves `myself` per account, chosen by the value of the configured email
  variable at call time, so two nodes with different `credentials.email-env`
  names are two accounts;
- applies `POST …/transitions` (204, or 400 when not offered) and
  `PUT …/assignee` (204);
- records every request with its method and account;
- takes per-request hooks: `before(method, path_fragment, fn)` runs `fn` before
  answering, and `fail(method, path_fragment, exception)` raises instead. Hooks
  are how the race orders in criterion 6 and the failures in criteria 8 and 9 are
  produced deterministically, without threads;
- installs itself with `monkeypatch.setattr(jira.JiraClient, "_request", …)`,
  as `tests/test_tracker_cli.py:92-101` does.

Creates `tests/test_tracker_claim.py`, one test per row and per criterion, each
asserting `row`, `claimed`, and the recorded write requests:

- criterion 2 shape at claim level: unassigned ready ticket → `3a`, two writes,
  transition before assign;
- criterion 3: pre-assigned → transition only;
- criterion 4: pre-assigned, transition refused by hook, ticket unmoved → `3c`;
- criterion 5: `1b` and `1a`, no writes;
- `1c` with two offered transitions of the claim's name;
- `1e` and `1f`, no writes; `1f`'s message contains no form of "assign";
- criterion 7: refused, unmoved, unassigned → `3d`; the 400 body only in `detail`;
- criterion 8: assign fails with `TrackerPermissionError` → `3e`, message
  contains "assign it to yourself"; then assign by hand in the fake and claim
  again → `1e`;
- criterion 9: transition raises `TrackerUnavailable` after the fake applies it —
  pre-assigned → `3a`; unassigned → `3f`;
- read-back raises → not claimed, message says the result is unknown;
- `stop`: `TrackerPermissionError` on the transition propagates, no read-back
  request recorded;
- criterion 6, orders (a), (b), (c), with accounts A and B on the directed
  workflow: B's outcome is `1b`, `3d`, `3b` respectively, and B sends no assign
  in any of them;
- the global workflow: a ready ticket claims as `3a`; a second claim by a second
  account after the first completes is `1b`.

Proves it: `python -m pytest tests/test_tracker_claim.py -q`. **Mutation check,
each run red once and reverted**: assign before transition (order (b)/(c) tests
go red); drop the `landed` test from `3a` (criterion 4 test goes red); add
"assign it to yourself" to `1f` (its test goes red). Record the three in
`outcome.md`.

## Task 5 — `tcw work tracker import`

Modifies `tcw/work/cli.py`:

- the `tracker` group's help text (line 1981): drop "(read-only)";
- `import` subparser: `ticket`, `--part`, `--title`;
- `_tracker_import(args)`, following spec Design part 3 steps 1–7 in order:
  `_tracker_client("import")`; `validate_part`; empty `--title` refused;
  `read_ticket`; `find_binding` with `project` from
  `FsProjectRegistry.open(st.node_root).current.id` (the CLI already imports the
  filesystem layer; `intake.py` does not); the two already-bound outcomes;
  `claim`; `create_work(title, intake=…)`; `write_sidecar(…, revision="")`;
  `drop` on failure, and the drop-also-failed message naming
  `tcw work drop <slug> --confirm`; slug on stdout, summary on stderr.
- `_intake_text(outcome, description, today)` — the Markdown in spec Design
  part 3, description from `client.description(issue_id)`.

`BindingProblem`, `ValueError`, `StaleRevision` and `TrackerError` are caught and
printed as `tcw work tracker import: <message>`, exit 1. Refusal messages keep the
fixed first line and the `detail:` line from `ClaimOutcome`.

Creates `tests/test_tracker_import.py`, CLI in-process via the `_run` shape in
`tests/test_tracker_cli.py:77-89`, with the task 4 fake:

- criterion 1: no tracker → exit 1, one line naming `work.tracker`, no item;
- criterion 2: full check of the created item, `intake.md`, `tracker.yaml` keys
  and values, no `owner`, no `initial-request.md`, two writes in order;
- criterion 5 through the CLI: `1b` exits 1, no item;
- criterion 6 through the CLI: nodes A and B, same fake, orders (a)–(c) via hooks
  that run B's `main([...])` inside A's request — one item across both nodes, B
  exits 1 with no assign recorded;
- criterion 10: same part twice → one item, same slug, "already bound", no write
  on the second; `--part api` then `--part web` on the directed workflow → two
  items, second run no write;
- criterion 11: `write_sidecar` raises → no item left; `write_sidecar` and
  `drop` both raise → message names the slug and `tcw work drop`; `create_work`
  raises → message says claimed; re-run in each case → one bound item, no write,
  "not claimed by this run";
- criterion 12: hand-written binding, ticket assigned to another account → exit
  1 naming slug and assignee, no write;
- criterion 13: YAML-list binding and string-`ticket` binding on a `backlog`
  item → exit 1 naming it; two items holding the key → exit 1 naming both; the
  same on `completed` items → import proceeds;
- `--part "A B"` and `--title ""` → exit 1 with no request recorded at all;
- criterion 16, import paths: with the token variable set to the file's
  `SENTINEL`, run every test above's command again under one parametrized test
  and assert the sentinel is absent from stdout, stderr, and every file under
  `st.root`.

Proves it: `python -m pytest tests/test_tracker_import.py tests/test_tracker_cli.py
tests/test_tracker_absent.py -q`.

## Task 6 — `tcw work tracker link` and `unlink`

Modifies `tcw/work/cli.py`:

- `link` subparser: `slug`, `ticket`, `--part`. `_tracker_link` per spec Design
  part 4: resolve the bare slug with `st.get` (no `_resolve`); refuse resolved,
  bound, or malformed; `read_ticket`; `find_binding`; `claim`; write with the
  revision read in step 1 or `""`, carrying `unlinked`.
- `unlink` subparser: `slug`, `--reason` (required). `_tracker_unlink` per part 5,
  using `_store()` directly — **not** `_tracker_client`, so it works with no
  tracker configured — and `unlink_document`, written with the read revision.
  Prints that the ticket is unchanged in the tracker.

Creates `tests/test_tracker_link.py`:

- criterion 1, link path: no tracker configured → `link` exits 1 with one line
  naming `work.tracker`, nothing written;
- criterion 14: unbound `backlog` item + ready ticket → claimed and bound;
  `intake.md` and `initial-request.md` byte-identical before and after; bound item,
  `completed` item, key held by another item → exit 1, no write request, every file
  under the item folder byte-identical;
- criterion 13, link paths: malformed binding on the item, and on another item →
  exit 1 naming it;
- criterion 15: no `--reason` (argparse exit 2 counts as refusal; assert non-zero
  and nothing changed); unbound item; `completed` item → exit 1, nothing changed.
  Bound item with the `work.tracker` block removed from config and the fake
  recording → exit 0, zero requests, document has no `ticket` and one `unlinked`
  entry with `reason` and `unlinked-on`. Then restore the config, `link` the same
  item to a second ticket → succeeds, `unlinked` still has that entry;
- criterion 16, link and unlink paths: sentinel absent from output and files.

Proves it: `python -m pytest tests/test_tracker_link.py -q`, then the full suite.

## Task 7 — File the generated-sidecar gap

Creates `docs/work/inbox/serve-accepts-writes-to-generated-sidecars.md`: `PUT
/api/work/<slug>/sidecars/<name>` accepts any `WORK_SIDECARS` name
(`tcw/serve/__init__.py:1281-1305`) and `generated` is only reported
(`tcw/serve/__init__.py:646`), so `rollup.md` and now `tracker.yaml` can be
overwritten through the API although the client hides the button. Names the epic's
Risk 1 as where this was found, and that the fix is a refusal in the server, not in
this item.

Proves it: the file exists, with both citations re-checked at the commit it lands
in.

## Task 8 — Documentation Sync

One pass over the finished diff, after tasks 1–7, per `tcw work docs`. Every
configured entry's trigger fires, as the epic plan's table predicted for C2.

| Entry | Trigger | Fires because | What to write |
| ----- | ------- | ------------- | ------------- |
| `README.md` | Public-API | three new commands | In the tracker section (lines 364-405): `import`, `link`, `unlink` in the command block; one short paragraph on who may claim, that import creates a backlog item with the ticket in its intake, and that the item's `request` stage still runs. Keep the two stated guarantees true: no tracker → nothing changes; `tcw validate` never contacts the tracker. |
| `docs/release-notes/upcoming.md` | Public-API | same | Plain language: you can now take a Jira ticket from the terminal and get a work item bound to it; running it again does not duplicate; a wrong binding can be removed with a reason. Say that on a workflow that lets anyone start a ticket from any status, two people can both take one — TCW does not stop that. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | code changed | Added: the three commands, `tracker.yaml` sidecar (generated), `JiraClient.apply_transition` / `assign` / `description`, `tcw/tracker/intake.py`. Changed: `JiraClient.issue` quotes its key. |
| `skills/<component>/SKILL.md` → `tcw-work` | Skill-Driven-Component | CLI surface and model changed | `skills/tcw-work/references/commands.md` "Reading an external tracker" (line 83): rename to cover taking tickets; add the three rows to its table; the claim rules, already-bound behavior, `--part`, the binding sidecar being command-written, and that `unlink` never touches the tracker. `skills/tcw-work/SKILL.md` itself: re-read; it points at `commands.md` for every command, so change it only if that pointer no longer describes the reference. |

Not a configured entry, but required: `docs/guide/work.md` "Reading an external
tracker" (line 605) is the prose home `tests/test_documented_cli_surface.py:258-260`
names for work commands. Extend it in the same pass with the same content as
`commands.md`, in guide prose.

**Coordinate with `2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`,
planned at the same time.** It edits the same sections of `README.md`,
`commands.md` and `docs/changelogs/upcoming.md`. Whichever lands second rebases its
edits onto the other's; neither absorbs the other.

Proves it: `python -m pytest tests/test_documented_cli_surface.py -q` passes (every
`tcw` invocation written in the docs exists), and a read of each diff against the
table above.

## Task 9 — Ledger

- Write `description.md` for `work/manage-external-tracker-intake`
  (`tcw capabilities path` resolves the store): what import, link and unlink do,
  who may claim, that the binding is not proof of a claim, and the two limits the
  user accepted — a workflow that lets anyone start a ticket from any status, and
  two runs by one account.
- `tcw capabilities set work/manage-external-tracker-intake --status Supported`.

Run this from the primary checkout after the worktree's code is merged, with the
editable install restored, since it drives the `tcw` CLI.

Proves it: criterion 19. `tcw capabilities show work/manage-external-tracker-intake`
prints `Status: Supported`; `tcw capabilities check` and `tcw validate` exit 0.

## Verification

What the suite cannot settle.

1. **[live] criteria 11 and 18.** Against `proposit.atlassian.net`, fixture
   projects `TCWCLAIM` and `TCWTEST` only. **These write to Jira**: they create
   tickets (C1's outcome records every `TCWCLAIM` ticket as already claimed, so a
   ready one has to be made) and move and assign them. Confirm with the user before
   running, then:
   - create an unassigned `To Do` ticket in each project with a short description;
   - criterion 18: `tcw work tracker import` each; check status, assignee, the bound
     item and its intake;
   - criterion 11: in `TCWCLAIM`, move a second new ticket to `In Progress` and
     assign it to yourself by hand, then import it; expect "not claimed by this run";
   - `unlink` one of the items, then `link` it back.
   Record commands and results in `outcome.md`. Drop the local items afterwards
   unless the user wants them kept.
2. **The epic plan's Verification item 2** — two developers, two machines, one Jira
   project. Criterion 6 proves the decision logic with a fake. The real check needs
   a second Jira account; ask the user whether one exists. If not, `outcome.md`
   records it as not verified, for the epic's checkpoint 2.
3. **The epic plan's Verification item 4** — one ticket filed by someone without a
   checkout, imported end to end. Needs a person other than the developer; ask the
   user at `verify`. Recorded as not verified otherwise.
4. **Epic criterion 1, re-checked** with the epic plan's task 9 command against
   this item's branch point. The only expected `tests/` change to an existing file is
   the added `OPERATIONS` lines (task 3), which remove nothing.
5. **Message wording.** Read every refusal message the tests produce, once, for
   plain language and for not implying a cause the tracker did not state.

## Notes

- **Nothing blocks this item.** Its only blocker, C1, is completed. The sibling
  inheritance item touches the same documentation but no code this plan changes;
  it is not a blocker in either direction, so no `--blocked-by` is recorded.
- **Tests use a stateful fake rather than replay fixtures.** C1 captured scrubbed
  live responses for its reads. The claim's value is in sequences and races no
  single captured response shows, so the fake is the instrument; the live checks
  in Verification cover realism.
- **Row ids in `ClaimOutcome`** exist so tests assert decisions, not wording, and
  so wording can be improved at Verification item 5 without touching tests.
- **The epic's checkpoint 2** comes when this item completes. Its outcome must
  carry, for that checkpoint: criterion 6's narrowing, Verification items 2 and 3,
  and the two limits the user accepted.
