As a user, I run `tcw validate`, and as part of its checks it validates the capabilities ledger: cross-reference identifiers, the locked set of metadata fields and the fields some values require, role and condition slugs, every `Subject:` ref against the taxonomy store, and every `Feature:` ref as a registered taxonomy feature. Each problem is an `error: <where>: <message>` line on standard output, and any error makes `tcw validate` exit 1. There is no separate capabilities check command.

A record still carrying a field 3.0 retired, `Planning doc` or `Tracker`, is an
error whose message names `docs/migration-guide-2.8-to-3.0.0.md`.

It also flags a `.config.yaml` left at the root of the ledger from before 2.5.0,
which is no longer read: the message names the file, says that a project
inherits taxonomy and capabilities from its parents (`parents:` in
`.tcw/tcw-config.yaml`), and tells me to delete the file.

A capability of my project's own that overrides nothing must be complete: a
`name`, a `Status` and a `description.md`, which may be empty. One that lacks
any of them is an error naming each missing part, which is how an override
whose original was moved or removed is caught. Each of my own capabilities,
overrides included, has its field checks run on the capability as my project
sees it, combined with what it inherits, so an override that sets
`Status: Partial` over an original with no `Gaps` is reported here; the
references are checked only where my own capability sets them. An `overrides`
key is an error saying that TCW 4.0 removed it. Two parents that do not inherit
from each other, each with a capability at one path, are a warning, until my
project gives that path a complete capability of its own. When the inherited
capabilities cannot be read, the checks that need them are one could-not-check
finding, and the rest still run. The checks of override pointers, of
inheritance cycles, of a capability's `id` and of a project ID colliding with a
top-level entry are gone.
