# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixes

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
