As a user, I run `tcw capabilities show <path>` to read a capability: its qualified path, name, origin, metadata fields and body. An inherited capability is named with its project's prefix (`shared/web/login`). `--json` prints `{"schema": 1, "capability": {...}}` with the same content. A path that matches no capability exits 4, and a bare path that matches capabilities in more than one inherited project is a usage error (exit 2) asking me to add the prefix.

Since TCW 4.0 an object is named by its full identifier,
`<project>.<namespace>/<id-path>`: commands print it, and accept it, its
`tcw://` address, or the id-path alone for an object of the project I am in.
A work item can also be named by its tracker key, bare or as
`<project>.work/<KEY>`.
