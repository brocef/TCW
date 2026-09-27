# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixes

- **An epic can span packages behind a folder that has no board of its own.**
  `tcw work delegate` reaches them, and `tcw work reconcile` lists every slice,
  however deep — as the guide already said.
- **An item started before it was specified or planned can still be.** The
  `spec` and `plan` stages now run for an active item, and `tcw work start` and
  the `implement` gate warn when either document is missing, naming the command
  to write it. To make `implement` refuse instead, bind a check to it in
  `tcw-config.yaml`.
- **Tracker commands no longer mistake an unreadable ticket binding for none.**
  `link`, `unlink`, `sync` and a strict `drop` now refuse and say the file cannot
  be read, and an unexpected answer from Jira is reported instead of crashing.
- **`tcw work complete` names every staged file that stops its merge.**
- **Strict mode no longer lets through a move the ticket cannot follow.** If your
  workflow has no transition to where the item is going, `submit`, `rework` and
  `complete` now refuse up front instead of moving the item and leaving it stuck.
- **`tcw` works from any project inside a linked git worktree.** In a repository
  holding several projects, running from one of its packages in a worktree used
  to report every other project as a duplicate.

- **A name containing `*`, `?` or `[` means only itself.** Saving a capability
  named `a*` used to stage your unsaved changes to a capability named `abc` as
  well, so the next commit took them along.
- **One damaged `capabilities.yaml` no longer hides the whole board.** A file
  that is not plain text, a folder with that name, or a small file of nested
  YAML references used to stop `tcw work list` or leave `show --json` running
  forever. The item now lists normally, and completing it is refused with the
  reason until the file is fixed.

- **Re-running `tcw work init` or `tcw init` leaves your `work.path` exactly as you wrote it.**
  It used to rewrite `~/store` as the full path to your own home folder, which
  broke the setting for everyone else sharing the file.
- **The web app tells a save that lost a race apart from any other refused
  save.** Only a save made against an out-of-date copy now shows "Stale write
  detected"; any other refusal shows the server's own reason, which names the
  command to run instead.
- **A refused `tcw work edit` now changes nothing.** If one part of the command
  is refused (an unregistered tag, a blocker that would make items wait on each
  other in a loop), none of it is applied. Before, the blockers were saved and
  only then was the command refused.
- **The web app no longer lets you save an item as blocking itself**, or a
  blocker that would make items wait on each other in a loop.
- **A broken `extends` setting is reported as itself.** Taxonomy and
  capabilities commands in a project whose `extends` names a project TCW cannot
  reach used to say there was no project here and suggest `tcw init`, which
  would have created a second, empty store. They now say what is wrong with
  `extends`.

## Fixes

- **`tcw validate` checks a taxonomy or capabilities ledger wherever it lives.**
  A ledger moved out of `docs/` with a `path` setting, or kept in another
  repository, was never checked by `tcw validate`; it now is. Capabilities are
  also checked against a moved taxonomy, so a capability naming a term that does
  not exist is caught there too. If a taxonomy is configured but cannot be found
  (for example, declared in another repository that is not set up on this
  machine), setting a capability's Subject or Feature now says so instead of
  skipping the check, and `tcw capabilities check` reports that those references
  could not be checked whenever a capability has one.
- **`tcw validate` lists a `taxonomy.path` that points nowhere** instead of
  stopping with an internal error.

## Fixes

- **Recovering an interrupted start works.** If `tcw` stopped partway through
  starting an item, the advice to run `tcw work start <slug> --take-over` only
  repeated the same error. It now finishes the start. The web app shows such
  items above the work list with a **Recover** button.

## Fixes

- **Tag conditions in lifecycle settings work the way tags do everywhere else.**
  `when: { tags: [CLI] }` now matches items tagged `cli`; before, it silently
  never matched. If you used a differently spelled tag under `not_tags`, those
  items are now excluded as you intended. `tcw validate` reports a condition tag
  that is not registered, or several tags written as one (`"cli,docs"`).
- **`tcw validate` names a bad key instead of crashing** when a settings key is
  an unquoted number.
- **`tcw work list --tags` says when the tag you asked for is not registered**,
  so an empty list is not mistaken for "nothing has that tag".
- **A `skill:` setting that cannot be a skill name, such as one with spaces in
  it, is reported by `tcw validate` and ignored** until it is fixed, like any
  other malformed setting.
- **`tcw taxonomy rm` will not remove a term a capability still uses.** It lists
  the capabilities that name the term, the same way it already lists other terms
  that do.
- **`tcw taxonomy rm` no longer says "Removed" for a term that is still there.**
  A file under the term that Git does not track — a child term you never added,
  say — is named and the removal refused before anything changes. Files your
  operating system leaves in folders, such as `.DS_Store`, are cleaned up with
  the term.
- **`tcw validate` catches a wrong path in a work item's `capabilities.yaml`
  while the item is still being worked**, naming the file and line, instead of
  leaving it to `tcw work complete`. Finished items are never checked, so old
  records do not make validation noisy.

## New

- **Nest an imported item:** `tcw work tracker import <ticket> --parent <slug>`
  (or `--initiative <epic>`) — the way to build a hierarchy under strict mode.
