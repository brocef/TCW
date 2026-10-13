As a user, I run `tcw validate`, and as part of its checks it validates the taxonomy: extends entries, taxonomy kinds, feature vocabulary refs, and every relatesTo and subject reference — flagging cycles, duplicate aliases, alias/term collisions, dangling or ambiguous refs, and feature refs that do not point at vocabulary. Each problem is an `error: <where>: <message>` line on standard output, and any error makes `tcw validate` exit 1. There is no separate taxonomy check command.

It also flags a `config.yaml` left at the root of the taxonomy from before 2.5.0,
which is no longer read, telling me to move any `extends` I still need into
`taxonomy.extends` in `tcw-config.yaml` and then delete the file.
