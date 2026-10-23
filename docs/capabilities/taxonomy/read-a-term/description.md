As a user, I run `tcw taxonomy show <path>` to read an entry's qualified path, name, kind, origin, feature vocabulary refs, relatesTo links, attachments, and its description. An inherited entry is named with its project's prefix (`shared/invoice`). `--json` prints `{"schema": 1, "term": {...}}` with the same fields. A path that matches no entry exits 4, and a bare path that matches entries in more than one inherited taxonomy is a usage error (exit 2) asking me to add the prefix.

Since TCW 4.0 an object is named by its full identifier,
`<project>.<namespace>/<id-path>`: commands print it, and accept it, its
`tcw://` address, or the id-path alone for an object of the project I am in.
A work item can also be named by its tracker key, bare or as
`<project>.work/<KEY>`.
