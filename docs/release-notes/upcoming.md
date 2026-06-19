# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## New Features

- **Set up a project** — `tcw init` scaffolds the taxonomy, capabilities, and
  work doc trees inside your git repo (name specific components to scaffold just
  those).
- **Describe your domain (`tcw taxonomy`)** — list, add, show, remove, search,
  and check the nouns your app deals with, and reuse terms across namespaces.
- **Describe what users can do (`tcw capabilities`)** — list, add, show, search,
  and check user-story capabilities, with checks that they point at real
  taxonomy terms.
- **Track changes (`tcw work`)** — create work items and move them through their
  lifecycle (start, complete, drop) with a guided state machine and a
  definition-of-done gate. Blocker relationships are recorded in the item's
  data (not as a separate status), so the board stays simple while still
  tracking what an item depends on.
- **Blocker management from the CLI** — `tcw work edit <slug> --blocked-by
  <refs> --blocks <refs> --unblocked-by <refs>` adds or removes blocking links
  between items. `tcw work new` also accepts `--blocked-by` so blockers can be
  set at creation time.
- **Force past blockers** — `tcw work start --force` and `tcw work complete
  --force` let you override unresolved blockers when you need to.
- **Ordered board** — `tcw work list` now outputs items in topological order
  (blockers before the items they block) and annotates each blocked item with
  its unresolved blockers.
