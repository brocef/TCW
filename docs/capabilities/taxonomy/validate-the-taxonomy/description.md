As a user, I run `tcw taxonomy check` to validate extends aliases, taxonomy kinds, feature vocabulary refs, and every relatesTo / subject reference — flagging cycles, duplicate aliases, alias/term collisions, dangling or ambiguous refs, and feature refs that do not point at vocabulary.

It also flags a `config.yaml` left at the root of the taxonomy from before 2.5.0,
which is no longer read, telling me to move any `extends` I still need into
`taxonomy.extends` in `tcw-config.yaml` and then delete the file.
