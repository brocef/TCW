As a user, I inherit the capabilities of every parent whose `inherit` includes
`capabilities`, named under `parents:` in my project's `.tcw/tcw-config.yaml`
(see [Name a project's parents](tcw://C/cli/name-a-projects-parents)), through
every level: a parent's own parents pass their capabilities down too, as far as
each link's `inherit` allows, without my listing them. Capability inheritance
is decided separately from taxonomy inheritance, by each link's `inherit`, and
nothing else makes capabilities inherited. TCW 4.0 removed the separate list of
inherited projects that the `capabilities:` section used to hold, and the
commands that edited it; a list of that kind left in my own
`.tcw/tcw-config.yaml` is an error naming `parents:`, and every
`tcw capabilities` command exits 1 until I name its projects under `parents:`
and delete it. A parent that keeps no capabilities ledger adds nothing and is
not an error. Inheritance is a property of the project, not of the ledger, so
two projects whose `capabilities.path` resolves to the same folder may inherit
differently.

An inherited capability is read by its path like one of my own, once per path,
combined from the projects that have a capability there, and its full
identifier names the project it belongs to. To change one, I override it (see
[Override an inherited capability](tcw://C/capabilities/override-inherited)).
Opening my ledger reads no other project: inherited capabilities are read only
when a command needs them. When a parent, or a project between it and mine, is
not on this machine or its parents cannot be read, a command that needs the
inherited capabilities stops with exit 7, naming the project and how to fetch
it; one that reads only my own capabilities still works, and `tcw validate`
reports the inherited capabilities as could not be checked.
