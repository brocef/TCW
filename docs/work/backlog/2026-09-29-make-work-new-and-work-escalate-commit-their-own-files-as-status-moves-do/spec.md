# Spec — Make work new and work escalate commit their own files, as status moves do

## Capability changes

- **changed:** `work/open-a-work-item` — `tcw work new` commits the item it
  created.
- **changed:** `work/manage-the-work-inbox` — `tcw work inbox accept` commits
  the item it created, and the removal of the entry it came from.
- **changed:** `work/escalate-a-request-to-the-parent-node` and
  `work/delegate-a-request-to-a-child-node` — the request is committed in the
  receiving project's repository.

## Problem

Status moves commit their own change, scoped to the item's folders, unless
`work.auto-commit-transitions: false`. So do several other store writes: a
claim or takeover, a tombstone, a removal. Creation does not, and it leaves
two different states:

- `tcw work new` and `tcw work inbox accept` **stage** the item's files
  (`create_work` and `inbox_accept` in `tcw/store/fs.py`, through
  `_write_staged`);
- `tcw work escalate` and `tcw work delegate` leave the request **untracked**
  (`_inbox_write` in `tcw/work/recursion.py`).

The `work` skill says TCW commits its own transitions, and agents read that as
covering creation. The creation then gets folded into the next commit, usually
the request artifact, which is meant to be committed on its own. In a store
several sessions share, staged files left by one session are swept into
another session's commit.

## Goals

1. With `work.auto-commit-transitions` true (the default), each creation
   command makes one commit of exactly the paths it wrote:
   - `tcw work new`: the item folder, including a tracker binding written when
     `work.tracker.create.on-new` files it. Message
     `tcw work: new <slug>`.
   - `tcw work inbox accept`: the item folder and the removed entry. Message
     `tcw work: <entry> → <slug>`.
   - `tcw work escalate` / `delegate`: the one new inbox file, staged then
     committed in the **receiving** project's repository, and governed by that
     project's switch. Message
     `tcw work: request from <project-id> → inbox/<name>`.
2. The commit happens in the command, after every write it makes (item,
   tracker binding, owed-ticket record), not inside the store's create method.
   That keeps fixture helpers that call `create` commit-free and gives one
   commit per command.
3. A failed commit never loses or hides the creation. The command prints what
   it printed before (the slug, or the entry path), then a line on stderr:
   created, committing it failed, commit it yourself, with git's message.
   **Exit 0**: re-running a creation would make a duplicate, unlike a
   transition, whose re-run is refused.
4. With the switch false, nothing is committed, and every creation command
   leaves its files **staged**. `escalate` and `delegate` now stage too, so all
   four commands leave the same state.
5. A creation publishes only as the project's other store writes already do
   (`work.publish-transitions`, for a provisioned store): `new` and `accept`
   do. `escalate` and `delegate` never push the other project's repository.
6. The web app's creation (POST) commits the same way. A refused commit is
   still a success for the browser, since the item exists, as `_transition_ok`
   already treats transitions.

## Non-goals

- **`tcw work edit`** and other field writes stay staged-only. An agent
  batches those with its artifact commit.
- **`tcw work scaffold`**: its own item,
  `2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git`.
- **No new configuration key.** The existing switch already covers commits
  that are not status moves (claim, tombstone, removal). Its documentation is
  reworded to say it covers what TCW writes on its own, creation included.

## Design

- A helper in `tcw/work/cli.py`, `_commit_creation(st, message, paths)`:
  - skips when `st.auto_commit_transitions()` is false;
  - stages the paths (`git_stage`, which drops ignored ones);
  - commits them with `git_commit_result(st.store_git_root, …)`, scoped;
  - returns the error, if any.
  It mirrors `_own_locally`'s existing scoped commit.
- `_new` calls it after `_ticket_on_filing`, `_inbox_accept` after the
  accept, and `_escalate` and `_delegate` with the destination store opened on
  the written file's project.
- `_inbox_write` stages the file it writes (goal 4), under the existing
  `_require_repository` guard.
- In the web app, `POST` creation calls the same helper after
  `_owe_ticket_if_configured`, and catches a commit error as a warning.
- The comment in `_complete` that says "only transitions commit themselves" is
  corrected.

Litmus: committing is the filesystem adapter's way of recording a write. A
tracker-backed store records a creation by creating the record, and has
nothing to commit.

## Acceptance criteria

1. In a scratch repository, `echo body | tcw work new "First thing"`:
   `git status --short` is clean afterwards; HEAD moved by one commit
   `tcw work: new <slug>` touching only the item folder. An unrelated staged
   file elsewhere is still staged and not in that commit.
2. `tcw work inbox accept <entry>`: one commit holding the new item and the
   entry's removal.
3. `tcw work escalate "X"` from a child: the parent's repository has one new
   commit with the inbox file, and the child's repository is unchanged.
   `delegate` does the same in the child.
4. With `work.auto-commit-transitions: false`: no commits, and each command's
   files are staged, `escalate`'s included.
5. With a pre-commit hook that rejects commits: `new` exits 0, prints the slug,
   warns that committing failed, and the files are staged.
6. `new` with `create.on-new` and a fake tracker: the binding file is in the
   same commit.
7. Web app `POST` of a new item: committed; with a rejecting hook, still 201
   (or today's success code) with the item.
8. Existing tests pass, updated only where they counted commits or asserted
   staged-only creation. The full suite passes as CI runs it.

## Risks

- **Commit counts change** for anyone scripting around `new`. Intended, and
  the switch turns it off.
- **Committing in another project's repository** may run that project's hooks.
  A refusal is reported and the file is left staged, never lost.

## Notes

- Advisors: Opus, and Sonnet in place of Codex (at its usage limit until
  2026-10-03). Both chose to commit on creation under the existing switch, and
  to leave `edit` and `scaffold` alone.
  - Sonnet wanted exit 1 on a failed commit, matching transitions. Opus wanted
    exit 0, because re-running `new` duplicates. Took Opus's argument.
  - Opus also located the commit after the tracker write, found
    `tracker import`'s rollback, which would otherwise leave a committed item
    and a staged deletion, and noted fixtures calling `create`.
  - Both raised escalate/delegate staging when the switch is off, and the web
    app's success handling.
