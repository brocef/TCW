As a user, I run `tcw validate`, and as part of its checks it validates the capabilities ledger: cross-reference identifiers, the locked set of metadata fields and the fields some values require, role and condition slugs, every `Subject:` ref against the taxonomy store, and every `Feature:` ref as a registered taxonomy feature. Each problem is an `error: <where>: <message>` line on standard output, and any error makes `tcw validate` exit 1. There is no separate capabilities check command.

A record still carrying a field 3.0 retired, `Planning doc` or `Tracker`, is an
error whose message names `docs/migration-guide-2.8-to-3.0.0.md`.

It also flags a `.config.yaml` left at the root of the ledger from before 2.5.0,
which is no longer read: the message names the file and tells me to move any
`extends` I still need into `capabilities.extends` in `tcw-config.yaml` and then
delete the file. An override that points at `<project>/<id>` for a project this
one does not inherit from says that the project is not declared in
`capabilities.extends`, rather than only that the name is unknown.
