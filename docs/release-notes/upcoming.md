# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixes

- **A broken `extends` setting is reported as itself.** Taxonomy and
  capabilities commands in a project whose `extends` names a project TCW cannot
  reach used to say there was no project here and suggest `tcw init`, which
  would have created a second, empty store. They now say what is wrong with
  `extends`.
