# Outcome: harden tracker binding reads and Jira response parsing

## What shipped

- **Code** — `60935e86`:
  - `FsWorkStore.read_sidecar` raises `OSError` when the name holds something
    other than a regular file (folder, pipe, dangling link); `None` still means
    absent. The abstract docstring says so.
  - `binding_of` turns read errors into `unreadable_binding`, so `link`,
    `unlink`, `sync` and progress refuse it as they refuse any malformed
    binding; `ever_bound` already counted `OSError` as bound, so strict `drop`
    now refuses. `tracker sync <slug>` names a malformed binding instead of
    calling it unbound. The web sidecar route answers such a file with 400.
  - `JiraClient`: `_json` requires a mapping; `_mapping`, `_entries` and
    `_check_issue` check every list and nested object read downstream in
    `search`, `issue`, `transitions`, `recent_comments` and `description`,
    raising `TrackerError` naming the path; null stays absent.
    `_document_text` ignores a `content` that is not a list.
  - `tracker link` refuses an item waiting for deletion before any tracker
    call; `complete`'s merge-back hint lists every staged file in the merged
    repository's index; `ClaimOutcome.account_id/account_name` removed.
- **Review fold-in** — `15bf99ee`, `7cd96323`: single-item `create` and the
  filing hook run the sweep's board check (`_unreadable_sidecars`, now counting
  any unusable binding) inside `_create_one`, so another item's unreadable
  binding can no longer let a ticket be made and then not bound; `find_binding`
  no longer points at `unlink`; the redundant create guard and an unreachable
  check removed; the hint says git *may* refuse; a TCW-raised reason reaches the
  user and the web route never echoes a server path.
- **Docs**: `skills/work/references/commands.md` (link's refusals), changelog,
  release notes.

## Tests

- `tests/test_tracker_hardening.py` (26) and two in `tests/test_tracker_cli.py`.
  All 25 original tests failed on the parent commit (the reviewer ran them
  there too); each fold-in test failed on the commit before it.
- Tracker and serve files: 1257 passed after the first fold-in; the new and CLI
  files 110 after the last. Full suite: see `refined-outcome.md`.
- Hands-on with the worktree's `tcw`: a folder `tracker.yaml` → `unlink`
  refuses "not a readable text file: tracker.yaml is not a regular file",
  exit 1; the web sidecar route → `400 tracker.yaml is not a regular file`.

## What the plan or spec got wrong

- The intake's named-pipe hang was already gone: `is_file()` skipped the pipe,
  which is exactly why a folder read as unbound.
- Goal 4 guarded `create` against pending deletion, but `_create_one` already
  refused every resolved item; the guard was dropped at review.
- The spec did not foresee that an unreadable binding elsewhere now blocks
  `create` and filing for every item (as it already blocked `link` and
  `import`); caught at review, and both now refuse before making a ticket.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | Checked, no | — |
| `docs/guide/jira.md` | Checked, no | Its unreadable-binding and merge text still holds. |
| `docs/guide/<topic>.md` | Checked, no | — |
| `docs/release-notes/upcoming.md` | Yes | Two lines. |
| `docs/changelogs/upcoming.md` | Yes | Fixed entries and a Removed entry. |
| `skills/<component>/SKILL.md` | Checked, no | `commands.md` reference updated instead. |
| `skills/configure/references/` | No | — |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Where to fix the binding reads?** Both advisors: `read_sidecar` raising, since
  "exists but cannot be read" is a condition any store has. Opus: catch once in
  `binding_of`, not at every re-read. Chose both.
- **Jira shapes: one generic check or per operation?** Both: the top level in
  `_json`, plus per-operation list, entry and nested checks; Codex listed the
  operations and nested levels I had missed. Taken.
- **Which follow-ups?** Both: include pending-deletion, dead fields and the
  merge-back hint; keep the two documented limits. Opus: the guard in
  `link`/`create`, not the shared helper `sync` uses; Codex: read the index of the
  repository actually merged. Taken.
- **Code review** round 1: NOT DONE — the create/bind gap, a misplaced
  changelog heading, redundant checks; round 2: NOT DONE — the same gap through
  filing; round 3: DONE. Left for later, as the reviewer split them: quoted
  non-ASCII paths and `diff.relative` in the merge-back list; a non-mapping
  `create_issue` answer losing the "it may exist" warning; the filing path's
  "(creating it did not succeed)" placeholder.
- **Verify** (tcw:verifier): criteria 1-4 met by hand and in tests (a folder
  `tracker.yaml` through `link`/`unlink`/`sync`/strict `drop`/`show`/the web
  route; 11 extra wrong shapes; a pending-deletion `link` against an
  unreachable tracker; a real merge-back blocked by another item's staged file).
  Fixed at verify: `create`'s closed-item message pointed at `link`, which now
  refuses a pending deletion. Two older leftovers it found (a non-string status
  name crashes `tracker show`; strict `drop`'s "is, or was, bound" wording)
  added to the follow-up. Decision: accept.
- **Merging main** conflicted in the web sidecar route with the
  `capabilities.yaml` item's UTF-8 branch; both kept, `OSError` first.
