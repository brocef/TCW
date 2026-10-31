Converting a project's files, and its Jira tickets, from one format version to
the next, with `tcw migrate`. A migration leaves a record in
`.tcw/tcw-migration.yaml`: every `cap-…` id it removed, with the id-path that
capability has now, every object it moved, and every value it removed that
TCW 4 has no place for.
