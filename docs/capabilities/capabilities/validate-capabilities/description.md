As a user, I run `tcw capabilities check` to validate cross-reference identifiers, the locked metadata vocabulary and required-when fields, role/condition slugs, every `Subject:` ref against the taxonomy store, and every `Feature:` ref as a registered taxonomy feature.

It also flags a `.config.yaml` left at the root of the ledger from before 2.5.0,
which is no longer read: the message names the file and tells me to move any
`extends` I still need into `capabilities.extends` in `tcw-config.yaml` and then
delete the file. An override that points at `<project>/<id>` for a project this
one does not inherit from says that the project is not declared in
`capabilities.extends`, rather than only that the name is unknown.
