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
  substituted. Any other `{…}` is a problem `tcw validate` reports offline. So is a
  `link` without `comments: true`, or a value that is not text starting `https://`
  or `http://`.

There is no `{branch}` placeholder. `start --worktree` delivers before the worktree
exists (`cli.py:996` runs before `add_worktree` at `cli.py:1047`). A project whose
branches are published can write the branch name into its template itself.

A tracker block with problems reads as no tracker, as today. An older `tcw` reports
the two new keys as unknown, so its moves are recorded as `pending` until it is
upgraded. The release notes say so.

### 2. What is posted, and when

After `deliver` returns, for `start`, `submit`, `rework`, `complete` and `discard`,
with `comments: true`, on a bound item whose binding is on the configured site. The
comment is sent even when the status step was `held` or `none`. When the status
step is `pending` or `conflicting`, the comment is not sent but recorded as owed
(§ 4), because the ticket did not follow.

The ticket is read fresh (`read_ticket`, `tcw/tracker/intake.py:267`). The comment
is posted only when the ticket is assigned to the authenticated account. This is
checked even when the status step said `current`, because `assess_move` answers
`current` before it checks the assignee (`sync.py:100-102`). A ticket assigned to
someone else, or to nobody, gets no comment. That includes the discard of an
unclaimed ticket: TCW does not claim a ticket to announce abandoning it. The
command prints one line saying so and records nothing, since such a record could
never clear.

The text is fixed, short and plain:

```
TCW: "<title>" (part <part>) <started | went to review | went back to work | was completed | was discarded as <resolution>>.
<link, when configured>
tcw-event: <project>/<slug>/<event id>
```

The part clause appears only when the part is not `default`. The comment carries no
account name and no credential. It is posted as a Jira document through
`POST /rest/api/3/issue/{id}/comment`, with the link as a link mark. It is not sent
as v2 wiki markup, where square brackets become link syntax and the marker would not
read back as written.

### 3. The event id, and not posting twice

Each move is given an event id when it is delivered: the move and the UTC time to
the second, for example `submit-20260915T101500Z`. A fresh move posts without
looking for an earlier copy of itself, because it cannot have posted before. A
submit, rework, submit sequence therefore posts three comments, as it should.

The id is kept only when the comment is owed. Before `sync` posts an owed comment,
it reads the newest page of the ticket's comments (`orderBy=-created`, one page of
up to 100). If a comment written by the authenticated account carries the owed
event id, the comment is delivered and the debt is cleared without posting. This
covers a post that landed but whose answer was lost: that attempt recorded the
debt, and the retry finds the marker. When the marker is not on that page, the
comment is posted, because a duplicate is better than a lost comment.

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
  goes ahead, and the note is lost. A lost note must not keep a folder that
  `work.retain` says to remove. A status failure still keeps it, as today.

### 5. Commands

- **Lifecycle commands** exit 1 when a comment is owed, with one line: "`<slug>`
  moved to `<status>` and was committed; `<key>` did not get its progress comment
  (`<state>`): `<reason>`. Run `tcw work tracker sync <slug>`." A skipped comment on
  a ticket assigned elsewhere prints a `→` line and exits 0, as `held` does.
- **`tcw work tracker sync <slug> | --all`.** `--all` also selects items with a
  `comment` record. For an item with one, `sync` first runs the status delivery as
  today, then the owed comment once the status step is `current`, `none` or `held`.
  Exit 1 while either stays owed. The owner rule is unchanged.
- **`show`** prints `tracker comment: <state> after <move> (<at>): <reason>`. A
  board row's ticket segment gains `comment <state>` when one is owed.
- **Strict mode** does not refuse while a comment is owed. Only `sync` does.

### 6. Where things go (the abstraction test)

| Thing | Layer | Why |
| ----- | ----- | --- |
| `comments`, `link` | store interface (config) | Plain facts any store answers; parsed in `tcw/store/base.py` beside `statuses`. |
| `Bound.comment`, `WorkItem.tracker.comment` | model | The binding's own state; any store can hold it. |
| Posting, reading comments, the marker | `tcw/tracker/` | Tracker calls composed with store reads, beside `deliver`. |
| Comment calls | `JiraClient` | Two new operations: add a comment, list the newest comments. |

## Acceptance criteria

All against the fake tracker in `tests/tracker_fake.py`, which gains comment
storage, the two endpoints, and comment authors.

1. With `comments` absent or `false`, every test in `tests/test_tracker_sync.py` and
   `tests/test_tracker_strict.py` passes unedited, and a bound item's full
   lifecycle makes no comment request.
2. With `comments: true`, a bound item taken through `start`, `submit`, `rework`,
   `submit` and `complete --resolution done` leaves five comments, in order, by the
   authenticated account. Each names the item's title and the move, and each ends in
   a distinct `tcw-event:` line. No `tracker.yaml` is left with a `comment` key.
3. A discard with `wontfix` posts "was discarded as wontfix" on a ticket assigned
   to the account. On a ticket assigned to nobody it posts nothing, exits as the
   status step decides, and writes no `comment` key.
4. With `link: https://example.test/w/{project}/{slug}`, the comment carries that
   URL with the values substituted and percent-encoded. `tcw validate` names the
   key for `link: https://x/{branch}`, for a `link` without `comments: true`, and
   for `comments: "yes"`, and `tcw work list` still runs.
5. The part clause appears for a part other than `default` and not for `default`.
   With two parts on one ticket, a move of one part that is `held` still posts that
   part's comment.
6. With the fake tracker down during `submit`, the item is in `review`, the command
   exits 1 naming `tcw work tracker sync`, `show` prints a `tracker comment: pending`
   line, and `show --json` validates against `WORK_ITEM_SCHEMA` with
   `tracker.comment.state == "pending"`. After the fake comes back,
   `tcw work tracker sync --all` posts exactly one comment, clears the key, and
   exits 0.
7. If a post lands but its answer is lost (the fake applies the post, then raises
   unavailable), a following `sync` posts nothing new and clears the key. The
   ticket has exactly one comment with that event id.
8. If a comment carrying the owed event id was written by another account, `sync`
   still posts.
9. When the ticket is reassigned to another account after `start`, `submit` moves no
   status (conflicting, as today), posts no comment, and records a `comment` owed
   as conflicting. When the ticket is reassigned back, `sync` delivers both.
10. With strict mode on and a `comment` owed but no `sync` record, `submit` is not
    refused on account of the comment.
11. A comment that fails on an item that auto-deletion removes writes no record,
    and the item is removed. A status failure on such an item still keeps it
    (existing behaviour).
12. `unlink` moves an owed `comment` into the `unlinked` entry, and the item reads as
    unbound.
13. No comment, record or output contains the sentinel token (epic criterion 8), and
    no comment contains the item's `spec.md`, `plan.md` or `outcome.md` text. The
    check writes a sentinel phrase into each of those files and greps the fake's
    comment bodies for it.
14. `tcw validate` and `tcw capabilities check` exit 0.
    `work/synchronize-external-tracker-work` reads its final text.

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
- **Sibling sweep.** Every outbound write in `tcw/tracker/` goes through
  `JiraClient._request` (`jira.py:129`), so the credential rule and the timeout
  test cover the two new operations without new plumbing.
