As a user, I name every taxonomy entry, capability and work item the same
way, by its full identifier: `<project>.<namespace>/<id-path>`, such as
`demo.capabilities/cli/x` or `demo.work/2026-10-22-add-login`. It says which
project owns the object, which of the three namespaces it is in, and where it
sits among that store's folders. Every command prints it: lists print one per
line, and `show` starts with `full-id` and `owner`. Every reference TCW
stores is one: a capability's Subject, Feature, Roles, When, Blocked by and
Superseded by, a taxonomy entry's vocabulary and relatesTo, a work item's
parent and blockers, and each entry of an item's `capabilities.yaml`.

Every command that takes an object accepts its full identifier, its
`tcw://` address, and, for an object of the project I am in, its id-path
alone (`cli/x`). A work item can also be named by its tracker key, bare
(`TCW-67`) or as `<project>.work/<KEY>`. Letter case is compared exactly; a
name that differs only in case is not found, and the message names the
spelling on disk. A full identifier may name an object in any project TCW
can locate, not only one this project inherits from: naming is not
inheriting. A project that is named but not on this machine is reported as
could not be checked, and an ID nothing knows as an error that says to check
the spelling.

A value still in a TCW 3.x form (`cli/x` stored in a field, `demo/2026-10-22-x`
as a work item's name) is reported by `tcw validate` as needing
tcw migrate.
