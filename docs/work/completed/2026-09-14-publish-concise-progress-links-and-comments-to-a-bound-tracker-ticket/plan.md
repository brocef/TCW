# Plan — Publish concise progress links and comments to a bound tracker ticket

Work happens in a worktree (`tcw work start <slug> --worktree`). The editable
install is pointed at it for tests, and restored before the item completes. Every
task leaves the suite green.

## Task 1 — Configuration: `comments` and `link`

**Files:** `tcw/store/base.py`, `tests/test_tracker_comment.py` (new),
`tests/test_tracker_inheritance.py`.

- `TRACKER_KEYS` gains `comments` and `link`. `TrackerConfig` gains
  `comments: bool = False` and `link: str = ""`.
- `parse_tracker_config`:
  - `comments` must be a boolean;
  - `link` must be text starting `https://` or `http://`;
  - every `{name}` in `link` must be `project` or `slug`, found with
    `string.Formatter().parse`, and a malformed brace is a problem too.
- A `link_for(template, project, slug)` helper substitutes values with
  `urllib.parse.quote(value, safe="")`.

**Proves:** criteria 4 (validation half) and 5.

## Task 2 — Client and fake: comments

**Files:** `tcw/tracker/jira.py`, `tests/tracker_fake.py`,
`tests/test_tracker_client.py`.

- `JiraClient.add_comment(issue_id, document)` sends
  `POST /rest/api/3/issue/{id}/comment` with `{"body": document}`.
- `JiraClient.recent_comments(issue_id)` sends
  `GET /rest/api/3/issue/{id}/comment?orderBy=-created&maxResults=100` and returns
  `(author_account_id, text)` pairs. The text is the joined text nodes of the
  document.
- The fake keeps `Ticket.comments` as a list of `(author, body)` and answers both
  endpoints. `fail(..., apply_first=True)` already covers a post that landed but
  whose answer was lost.
- `OPERATIONS` gains both operations, so the timeout test covers them.

**Proves:** the client half of criteria 7, 9 and 10.

## Task 3 — The record: `comment` in the binding

**Files:** `tcw/store/base.py` (`Bound.comment`, `_comment_record`,
`binding_value`), `tcw/tracker/intake.py` (`with_comment_record`, `_BINDING_KEYS`),
`tcw/work/projection.py` (`_TRACKER`), `web/client/src/model/types.ts`,
`tests/test_tracker_surface.py`, `tests/test_tracker_comment.py`.

- `comment: {move, event, state, reason, at}`, where `state` is pending or
  conflicting and `move` is a transition id. A malformed record becomes
  `{"problem": …}` and never unbinds the item.
- The JSON schema gains a required nullable `comment`, and the TypeScript type
  follows. The type change alters no built output, so `tcw/serve/dist` is not
  rebuilt. `pnpm check:build` confirms that.
- `unlink` carries `comment` into the unlinked entry.
- `tests/test_tracker_surface.py`'s pinned dict gains `"comment": None`.

**Proves:** criterion 16 and the schema half of criterion 7.

## Task 4 — Publishing: `tcw/tracker/progress.py`

**Files:** `tcw/tracker/progress.py` (new), `tests/test_tracker_comment.py`.

- `comment_text(item, bound, move, resolution, link)`, `document(text, link)`,
  `new_event(move)` (`f"{move}-{secrets.token_hex(4)}"`).
- `publish(store, slug, client, config, *, move, status_state)` returns
  `Outcome(state, reason, recorded)`:
  - When comments are off, or the binding is absent or on another site: `none`.
  - When `status_state` is pending or conflicting: record the comment owed with
    that state and a new event.
  - Otherwise, read the ticket. If it is not the account's: remove any owed record
    and return `skipped` with a reason. If it is the account's: post. On success,
    remove any owed record and return `current`. On a tracker error, record it
    owed (state from `classify_error`) unless the item is pending deletion.
- `retry(store, slug, client, config)` runs for an item with a `comment` record:
  - Comments off, or a malformed record: remove the record and return `cleared`.
  - Otherwise read the ticket. If it is not the account's: remove the record and
    return `skipped`, per spec § 5. A read error keeps the record, with its state
    from `classify_error`.
  - Otherwise look through `recent_comments` for the owed event by this account.
    If it is found, remove the record. If not, post, then remove the record, or
    keep it on an error.

**Proves:** criteria 2, 3, 6, 9, 10, 12, 13 and 17 at the function level.

## Task 5 — Wiring: lifecycle commands, `sync`, `show`, `list`

**Files:** `tcw/work/cli.py`, `tests/test_tracker_comment.py`.

- `_deliver_after` returns 0, 1 when the status step failed, or 2 when only the
  comment did. Every caller exits `min(delivered, 1)`, and `_complete`'s auto-delete
  keeps the item only on 1. (Changed while implementing: the plan first said a
  tuple, but every caller already used the value as an exit code.)
- `_tracker_sync`: `--all` selects items with `sync` or `comment`.
  - An item with a `sync` record runs `deliver` as now, then `retry` when the
    status step ends `current`, `none` or `held`. While the status step is still
    pending or conflicting, the comment record takes that state and reason.
  - A malformed `sync` record beside an owed comment still sends `sync` down the
    check-only path (an existing edge). The comment waits with it, and that is
    stated in the changelog.
  - An item with only a `comment` record runs `retry` alone.
  - The help text is updated.
- `show` prints `tracker comment: …`, and the board row's ticket segment gains
  `comment <state>`.
- The merge-back hint at `_complete` also fires for a staged `comment` record.

**Proves:** criteria 1, 2, 7, 8, 11, 14, 15, and the command half of 3, 4 and 6.

## Task 6 — Capability

**Files:** `docs/capabilities/work/synchronize-external-tracker-work/description.md`,
the item's `capabilities.yaml`.

**Proves:** criterion 18.

## Documentation Sync

| Entry | Fires | Change |
| ----- | ----- | ------ |
| `README.md` | yes | A "Comments on the ticket" paragraph covering opt-in, what is posted, the link template, `sync`, and the limits. |
| `docs/release-notes/upcoming.md` | yes | A plain entry, and the upgrade note about older copies. |
| `docs/changelogs/upcoming.md` | yes | `comments`, `link`, `TrackerConfig`, `Bound.comment`, the schema, `progress.py`, the two client operations, `_deliver_after`'s new return value. |
| `skills/tcw-work/references/commands.md` | yes | A "Progress comments" block in the tracker section. |
| `skills/tcw-configure/references/tracker.md` | yes | The `comments` and `link` keys, inheritance, the Jira Service Management caution, and the upgrade caution. The `tcw serve` link example and its two limits: a child project is served under its path, not its id (`pathFor`), and an item removed by `work.retain` leaves a dead link. |
| `skills/tcw-work/SKILL.md` | checked | Only if it names tracker sync behaviour; otherwise no change. |

## Verification

1. **Hands-on:** a scratch node with `comments: true` and an unreachable `base-url`.
   `start` on a hand-bound item exits 1 with both the status and the comment owed,
   and `show` prints both lines. No real tracker is contacted.
2. **Bare `pytest` on merged `main`**, then `tcw validate`, `tcw capabilities check`
   and `pnpm check:build`.
3. **Not checkable here:** real Jira's comment document shape, `orderBy`, and
   customer visibility on Service Management projects (spec § Risks 1 and 7).
