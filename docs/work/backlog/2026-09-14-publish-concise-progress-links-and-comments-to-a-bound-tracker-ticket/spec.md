# Spec — Publish concise progress links and comments to a bound tracker ticket

## Capability changes

Planned deltas only.

| Capability | Delta | Why |
| ---------- | ----- | --- |
| `work/synchronize-external-tracker-work` | changed | Its last sentence says progress links and comments are separate work; this item is that work. |
| `work/require-tracker-backed-work` | unchanged, on purpose | A comment that did not post authorizes nothing and blocks nothing (§ 5). |

## Problem

The tracker bridge epic's goal 4 asks that "tracker status and concise progress
links stay current as the TCW lifecycle advances". The status half has shipped. A
bound item's `start`, `submit`, `rework`, `complete` and discard move its ticket to
the mapped status: `deliver` in `tcw/tracker/sync.py:151` is called from
`_deliver_after` in `tcw/work/cli.py:889`. A ticket reader still learns only a status
name. Several things are invisible to them:

- which part of the work moved, when a ticket is shared by several items;
- why work was abandoned, since a discard carries a resolution nobody sees;
- where to follow the work.

If a status is unmapped, the reader sees nothing at all: `deliver` returns `none`
before it even reads the ticket (`sync.py:211`).

The epic's request is specific about what may go outward: "Only stable links and
short summaries are written back", never `spec.md`, `plan.md`, `outcome.md`,
capability prose, diffs or code references. It is equally specific that a retried
event must "not duplicate comments or transitions" (epic criterion 6).

## Goals

1. When enabled, each lifecycle move of a bound item posts one short plain-text
   comment on its ticket. The comment names the item, the part when it is not
   `default`, and what happened (for a discard, the resolution). It also carries a
   link when the project configures one.
2. A link is built only from a template the project writes. TCW invents no URL.
3. A comment that could not be posted leaves the local move in place, makes the
   command exit 1, is recorded, and is posted by `tcw work tracker sync`.
4. TCW's own retries do not post a comment twice, even when an earlier attempt
   landed but its answer was lost.
5. Nothing changes for a project that does not turn comments on, and nothing is
   loaded or sent for an unbound item or a node with no tracker.

## Non-goals

- Copying any lifecycle artifact, capability text, diff or code reference.
- Reading, editing or deleting other people's comments. TCW lists a ticket's
  comments only to find its own marker (§ 3), and it ignores every comment written
  by another account. The request's out-of-scope line is honoured in that sense.
- Folding the comment into the transition call. Jira allows it, but a transition
  screen with no comment field refuses the combined call. That would tie the status
  move to the note, so the two stay separate calls.
- A comment for anything other than a lifecycle move.
- Exactly-once delivery against concurrent runs, or against someone deleting
  TCW's comment. See § Risks.
- Showing comment debt in the web app. `show`, `show --json` and `list` carry it.
- Branch or review links TCW would have to discover. TCW pushes no branches, and
  `work.repository` (`RepositoryDeclaration`, `tcw/store/base.py:1363`) says where
  a store comes from, not a page a reader can open.

## Design

### 1. Configuration

Two new optional keys under `work.tracker`, added to `TRACKER_KEYS`
(`tcw/store/base.py:1046`):

- `comments`: a boolean, default `false`. Comments are visible to people outside
  the repository and may notify them, so a project that mapped statuses has not
  thereby agreed to comments. The key is independent of `statuses`. A `submit`
  with no `review` status mapped still posts, because the comment is then the only
  trace of the move.
- `link`: a URL template with placeholders `{project}` (the binding's TCW project
  id) and `{slug}` (the item's slug). Each value is percent-encoded when
  substituted. Any other `{…}` is a problem `tcw validate` reports offline, and so
  is a value that is not text starting `https://` or `http://`. A `link` with
  comments off does nothing and is not a problem: settings merge from parent nodes
  key by key, and a nearer value cannot remove a farther one (`_lay_tracker_block`,
  `tcw/store/base.py:1283-1287`), so a child turning comments off under a parent
  that sets a `link` must not break its whole tracker block.

  One template that works whatever the item's status: a team that hosts `tcw serve`
  links each item's page, `https://tcw.example.com/work/{slug}`, which is the web
  app's own address for an item (`pathFor`, `web/client/src/ui/route-utils.ts:35`).
  A link into a Git host's file tree would break at the next move, because the
  item's folder is named by its status.

There is no `{branch}` placeholder. `start --worktree` delivers before the worktree
exists (`cli.py:996` runs before `add_worktree` at `cli.py:1047`). A project whose
branches are published can write the branch name into its template itself.

A tracker block with problems reads as no tracker, as today. An older `tcw` reports
the two new keys as unknown and treats the whole block as broken
(`tcw/store/base.py:1081-1082`). Its status moves are recorded as `pending` through
`record_unsent` and get no comment. Under strict mode it refuses every gated
command, and its `pending` records then make the new `tcw` refuse until `sync`
runs. The release notes say all of this: a team upgrades every copy before setting
either key.

### 2. What is posted, and when

After `deliver` returns, for `start`, `submit`, `rework`, `complete` and `discard`,
with `comments: true`, on a bound item whose binding is on the configured site.
**The status result decides first, then the assignee:**

- **Status `pending` or `conflicting`.** The ticket did not follow, whoever holds
  it. The comment is not sent and is recorded as owed (§ 4) with the same state.
  It goes out when `sync` later brings the status through.
- **Status `current`, `none` or `held`.** The ticket is read fresh (`read_ticket`,
  `tcw/tracker/intake.py:267`). This is a second read after `deliver`'s, which is
  accepted as the cost of keeping the two steps apart.
  - If the ticket is assigned to the authenticated account, the comment is posted.
    The assignee is checked even when the status said `current`, because
    `assess_move` answers `current` before it checks the assignee
    (`sync.py:100-102`).
  - If it is assigned to someone else or to nobody, no comment is posted. The
    command prints one `→` line and records nothing, since such a record could never
    clear. This includes the discard of an unclaimed ticket whose discard status is
    unmapped: TCW does not claim a ticket to announce abandoning it.

With a mapped discard status, the discard of an unclaimed ticket is already
`conflicting` today (`assess_move`, `sync.py:102`), so its comment is owed with it.

Whichever branch runs, **the newest move decides**: a comment posted, or skipped
because the ticket is not the account's, also removes any older owed comment.

The text is fixed, short and plain:

```
TCW: "<title>" (part <part>) <started | went to review | went back to work | was completed | was discarded as <resolution>>.
<link, when configured>
tcw-event: <event id>
```

The part clause appears only when the part is not `default`. The comment carries no
account name and no credential. It is posted as a Jira document through
`POST /rest/api/3/issue/{id}/comment`, with the link as a link mark. It is not sent
as v2 wiki markup, where square brackets become link syntax and the marker would not
read back as written. The marker is found by joining the document's text nodes.

### 3. The event id, and not posting twice

Each move gets an event id when it is delivered: the move, then eight random hex
characters, for example `submit-3f9a1c2e`. The random part is there because an
agent can run `submit`, `rework` and `submit` within one second, and a time-based id
would then match an earlier comment and swallow the later one.

A fresh move posts without looking for an earlier copy of itself, because it
cannot have posted before, so a submit, rework, submit sequence posts three comments.
The id is created before the post and saved only when the post fails. Before `sync`
posts an owed comment, it reads the newest page of the ticket's comments
(`orderBy=-created`, one page of up to 100). If a comment written by the
authenticated account carries the owed event id, the comment counts as delivered
and the debt is cleared without posting. That covers a post that landed but whose
answer was lost: the failed attempt saved the id, and the retry finds it. When the
marker is not on that page, the comment is posted, because a duplicate is better
than a lost comment.

### 4. The record

A new optional key in `tracker.yaml`, beside `sync` and separate from it:

```yaml
comment:
  move: submit
  event: submit-20260915T101500Z
  state: pending        # or conflicting
  reason: <why it did not post>
  at: <UTC time>
```

It is kept separate from `sync` for four reasons:

- strict mode refuses any mutation while `sync` is set (`binding_refusal`,
  `sync.py:318`), and a note must not lock the item;
- `sync.state` has no honest value for a status that did arrive;
- `_sync_record` rebuilds only its known fields (`base.py:420`);
- `deliver`'s `finish` rewrites or clears the whole `sync` record
  (`sync.py:184-205`).

`Bound` gains `comment`, validated like `sync`: a malformed one becomes
`{"problem": …}` and never unbinds the item. `WorkItem.tracker` and
`WORK_ITEM_SCHEMA` gain a required nullable `comment`, closed like `sync`, and the
web client's `TTrackerBinding` type follows. `unlink` moves `comment` into the
unlinked history with the rest (`_BINDING_KEYS`, `intake.py:180`).

- **One owed comment at a time.** A later move's comment replaces an earlier owed
  one, because the earlier note is out of date. This is coalescing, chosen on
  purpose: the ticket reader wants where the work is, not a backlog of past moves.
- **States.** `pending` covers an unreachable tracker, a rate limit, or missing or
  rejected credentials. `conflicting` covers everything else, including a ticket
  now assigned elsewhere while a status record is also owed.
- **Clearing.** A successful post, or the marker found, removes the key.
- **Auto-deletion.** An item about to be removed takes no record (`finish` at
  `sync.py:190`). A comment that failed on such an item is reported, the removal
  goes ahead, the note is lost, and `complete` exits 1. A lost note must not keep a
  folder that `work.retain` says to remove. A status failure still keeps it, as
  today (`cli.py:2417`). The status result and the comment result therefore reach
  `_complete` separately.
- **Comments turned off.** `sync` removes an owed comment without posting it, and
  prints that it did.
- **A malformed record** reads as `{"problem": …}` in `show` and `--json`. `sync`
  removes it with a printed line, since it is only a note.
- **Worktree merge-back.** The hint at `cli.py:2362`, which explains a staged
  `tracker.yaml`, also names an owed comment.

### 5. Commands

- **Lifecycle commands** exit 1 when a comment is owed, with one line: "`<slug>`
  moved to `<status>` and was committed; `<key>` did not get its progress comment
  (`<state>`): `<reason>`. Run `tcw work tracker sync <slug>`." A skipped comment on
  a ticket assigned elsewhere prints a `→` line and exits 0, as `held` does.
- **`tcw work tracker sync <slug> | --all`.** `--all` also selects items with a
  `comment` record, and its help text says so.
  - **With a `sync` record:** the status delivery runs as today. The owed comment
    follows once the status step is `current`, `none` or `held`, and the ticket is
    the account's.
  - **With only a `comment` record:** the status step is skipped. Today's
    check-only path would call a ticket someone has since moved on "conflicting"
    for ever (`sync.py:268-271`). The comment is posted when a fresh read shows the
    ticket is assigned to the account; otherwise it stays owed as `conflicting`.
  - Exit 1 while either stays owed. The owner rule is unchanged.
- **`show`** prints `tracker comment: <state> after <move> (<at>): <reason>`. A
  board row's ticket segment gains `comment <state>` when one is owed.
- **Strict mode** does not refuse while a comment is owed; only a `sync` record
  makes it refuse.
- **`tcw serve`** moves post no comment, as they deliver no status (an existing,
  stated limit).

### 6. Where things go (the abstraction test)

| Thing | Layer | Why |
| ----- | ----- | --- |
| `comments`, `link` | store interface (config) | Plain facts any store answers; parsed in `tcw/store/base.py` beside `statuses`. |
| `Bound.comment`, `WorkItem.tracker.comment` | model | The binding's own state; any store can hold it. |
| Posting, reading comments, the marker | `tcw/tracker/` | Tracker calls composed with store reads, beside `deliver`. |
| Comment calls | `JiraClient` | Two new operations: add a comment, list the newest comments. |

## Acceptance criteria

All against the fake tracker in `tests/tracker_fake.py`. The fake gains comment
storage, the two endpoints and comment authors, and each criterion gets a named test.

1. With `comments` absent or `false`, every test in `tests/test_tracker_sync.py` and
   `tests/test_tracker_strict.py` passes unedited, and a bound item's full lifecycle
   makes no comment request.
2. With `comments: true`, take a bound item through `start`, `submit`, `rework`,
   `submit` and `complete --resolution done`, all within the same second. The ticket
   then has five comments, in order, by the authenticated account. Each names the
   item's title and the move, the five `tcw-event:` ids are distinct, and no
   `tracker.yaml` is left with a `comment` key.
3. On a ticket assigned to the account, a discard with `wontfix` posts "was
   discarded as wontfix". With `discarded` unmapped and the ticket assigned to
   nobody, a discard posts nothing, exits 0 and writes no `comment` key.
4. With `link: https://example.test/w/{project}/{slug}`, the comment carries that
   URL with the values substituted and percent-encoded. `tcw validate` names the key
   for `link: https://x/{branch}`, for `link: ftp://x`, and for `comments: "yes"`,
   and `tcw work list` still runs. A `link` with comments off is not a problem.
5. A child node that inherits `comments: true` and a `link` from its parent, and
   sets `comments: false` itself, has a tracker config with no problems and posts no
   comment.
6. The part clause appears for a part other than `default` and not for `default`.
   With two parts on one ticket, a move of one part whose status is `held` still
   posts that part's comment.
7. **The status arrives but the comment does not.** The fake refuses only the comment
   post, as unavailable and without landing. The item is in `review`, the ticket is
   in `In Review`, the command exits 1 naming `tcw work tracker sync`, and `show`
   prints a `tracker comment: pending` line. `show --json` validates against
   `WORK_ITEM_SCHEMA` with `tracker.comment.state == "pending"` and
   `tracker.sync == null`. Then someone moves the ticket on to `Done` by hand, and
   `tcw work tracker sync --all` posts exactly one comment, clears the key and exits
   0.
8. With the fake down during `submit`, both a `sync` record and a `comment` record
   are written. When the fake is back, `sync` moves the ticket, posts one comment,
   clears both, and exits 0.
9. When a post lands but its answer is lost (the fake applies it, then raises
   unavailable), the following `sync` posts nothing new and clears the key, and the
   ticket has exactly one comment with that event id.
10. When a comment carrying the owed event id was written by another account, `sync`
    still posts.
11. After `start`, the ticket is reassigned to another account. `submit` then moves
    no status (conflicting, as today), posts no comment, and records a `comment` owed
    as conflicting. After it is reassigned back, `sync` delivers both.
12. An owed comment followed by a later move whose comment posts leaves one
    `comment` key at most, for the later move only. The earlier comment is never
    posted.
13. With `comments` turned off, `sync` removes an owed comment without posting and
    exits 0. A malformed `comment` record reads as a problem in `--json`, and `sync`
    removes it.
14. With strict mode on and a `comment` owed but no `sync` record, `submit` is not
    refused on account of the comment.
15. When the comment fails on an item that auto-deletion removes, no record is
    written, the item is removed, and `complete` exits 1. A status failure on such an
    item still keeps it (existing behaviour).
16. `unlink` moves an owed `comment` into the `unlinked` entry, and the item reads as
    unbound.
17. No comment, record or output contains the sentinel token (epic criterion 8). No
    comment contains text from the item's `spec.md`, `plan.md` or `outcome.md`: the
    test writes a sentinel phrase into each and greps the fake's comment bodies.
18. `tcw validate` and `tcw capabilities check` exit 0.
    `work/synchronize-external-tracker-work` ends with the paragraph in § Capability
    text below, in place of its last sentence.

## Capability text

The final paragraph of `work/synchronize-external-tracker-work`, replacing
"Progress links and comments on the ticket are a separate piece of work.":

> With `comments: true` under `work.tracker`, each move also posts a short comment on
> the ticket saying what happened to which item — and, with a `link` template, where
> to follow it — but only when the ticket is assigned to me; no lifecycle document
> is ever copied. A comment that did not post is recorded and sent by `tcw work
> tracker sync`, which first looks for it on the ticket so a post that landed
> without an answer is not repeated. Limits I accept: a later move's comment
> replaces one still owed, two runs at once or a deleted comment can still produce a
> repeat, and comments are not posted for moves made in `tcw serve`.

## Risks

1. **Nothing here is proven against real Jira.** No live access or credential exists
   in this run. Three things are taken from Jira's published REST contract rather
   than observed: the v3 comment document shape, that `orderBy=-created` is
   honoured, and the `author.accountId` field. If `orderBy` were ignored, the worst
   case is a repeated comment on a retry, never a lost one. The first real use
   should confirm those three, as the claim experiment did for claims.
2. **Duplicates are not impossible.** Two concurrent runs, a marker someone deleted
   or edited, or more than 100 comments since the lost post can each produce a
   second comment. "Not twice" holds for TCW's own sequential retries. This is
   stated in the capability.
3. **Coalescing drops notes.** If `submit`'s comment is owed and `rework` happens
   before `sync`, only the rework comment is sent. Accepted, as § 4 explains.
4. **A crash between the commit and the post** leaves no record, as for status
   (the existing limit). That move gets no comment.
5. **Titles go outward.** An item's title is written into the ticket. Titles are
   short and chosen by the author, and imported items take theirs from the ticket
   itself. A project that keeps titles private leaves `comments` off.
6. **Comment permission is separate in Jira.** A project that can transition but not
   comment gets `conflicting` comment debt on every move until `comments` is turned
   off. The message names the 403.
7. **Customer-visible comments.** On a Jira Service Management project, a comment
   added through the platform API may be visible to customers. This is not verified.
   The capability and the configuration reference say to leave `comments` off there
   unless titles may be seen.
8. **Existing tests change.** `tests/test_tracker_surface.py:46` pins the bound
   `tracker` value and gains `"comment": None`. `OPERATIONS` in
   `tests/test_tracker_client.py` (checked by
   `test_every_operation_is_accounted_for_here`, line 233) gains the two new
   operations, which also puts them under the timeout test.

## Notes

- **Advisors (2026-09-15).** Codex and an Opus subagent answered the same five
  questions.
  - Opt-in, one template: both agreed. `{branch}` was dropped on Opus's finding
    that it is empty at start.
  - Event ids that differ for repeated moves: Codex. Checking for a marker only on
    retries, and counting only the account's own comments: Opus.
  - A separate `comment` key rather than a field in `sync`: Opus, for the
    strict-mode lock. Codex preferred extending `sync` and letting strict mode gate
    on it; not taken, because a missing note authorizes nothing.
  - One owed comment, replaced by later moves: Opus. Codex preferred an ordered
    queue, or else stating coalescing plainly; coalescing is stated here.
  - Skipping a ticket that is not the account's: both. A held part still posts:
    both.
  - v3 document rather than v2 wiki markup: Opus.
  - Whether anything should stop the run: both said no, provided duplicate
    avoidance is bounded and stated, as here.
- **Spec review (2026-09-15).** The adversarial spec reviewer returned NOT READY,
  with four blocking findings, all accepted:
  - the assignee-versus-status order was undefined, and criteria 3 and 11
    contradicted each other;
  - a child could not turn comments off under an inherited `link`;
  - comment debt with no `sync` record could never clear under the check-only path;
  - second-resolution event ids could swallow a comment.

  Its should-fix items were also accepted:
  - `_complete`'s auto-delete reads the two results separately;
  - the merge hint names the new record;
  - the note about an older `tcw` is corrected;
  - the unspecified record states are now covered;
  - the capability text is written out;
  - a new criterion covers a delivered status with a failed comment;
  - a concrete template is named;
  - the existing test edits are listed.

  "Post once, best effort, no record" was the smaller version it offered. It was
  rejected, because the request's "`sync` retries" promise is part of goal 4.
- **Sibling sweep.** Every outbound write in `tcw/tracker/` goes through
  `JiraClient._request` (`jira.py:129`), so the credential rule and the timeout
  test cover the two new operations without new plumbing.
