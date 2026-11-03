## Fixes

- **Migrating a project with child projects now gets their terms right.** In
  an item's `capabilities.yaml`, an entry under `taxonomy:` that starts with
  a child project's ID, such as `b/turn`, now becomes that child's term,
  `b.taxonomy/turn`, the same way the capability entries beside it already
  became the child's capabilities. TCW 4.0.0 wrote it as a term inside the
  migrating project, `a.taxonomy/b/turn`. When the migrating project keeps
  no taxonomy, `tcw validate` reports that as an error; when it keeps one,
  nothing reports it until the item finishes. If the migrating project's own taxonomy really has a term at
  that path, the entry still names it. If the child's ID is also a folder of
  that taxonomy (or of one it inherits) but the term is not there, the
  migration stops and asks you to write the entry yourself, offering the
  full name for each meaning.

  **If you already migrated with 4.0.0**, change each such line by hand from
  `<project>.taxonomy/<child-id>/<term>` to `<child-id>.taxonomy/<term>`,
  unless your project's own taxonomy has a term at that path: those lines
  are already right. If your taxonomy has a folder named like the child but
  no term at that path, decide which one you meant, as the migration now
  asks. To find them, search the item folders, for example
  `grep -rnF 'a.taxonomy/b/' docs/work/*/capabilities.yaml` for a project `a`
  with a child `b` (use the folder your work items are kept in, if it is
  not `docs/work`). Do not rely on `tcw validate --remote` to find them all:
  it skips items that are `completed` or `discarded`, and items whose ticket
  is at a status no stage uses. Lines in finished items are history, and
  are worth fixing only to keep things consistent. A migration that 4.0.0
  started and did not finish keeps 4.0.0's conversion when you resume it,
  so fix those lines the same way afterwards.

- **The migration guide now says which check reads an item's
  `capabilities.yaml` in a project whose work is in Jira.** There, plain
  `tcw validate` does not check the terms and capabilities those files
  declare; `tcw validate --remote` does, once the tickets are converted.
