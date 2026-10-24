# Frozen copies used by the migration tests

`repo-tcw-config-3x.yaml` is this repository's own root `tcw-config.yaml` at
commit `e309b806`, the commit TCW-116's implementation started from, with one
change: its `work.jira.site` reads `https://example.invalid`, so the copy names
no real Jira site. Everything else, its anchors, aliases and `not_tags` key
included, is byte for byte the same.

The migration tests read this copy, never the repository's root file, because
the repository's own migration deletes that file (TCW-116 Design 8.4).
