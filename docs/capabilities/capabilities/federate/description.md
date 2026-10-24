As a user, I run `tcw capabilities extends add <project-id>` to explicitly
inherit capabilities from an ancestor, and
`tcw capabilities extends rm <project-id>` to stop. The source project ID is the
inherited namespace, and `capabilities.extends` in `tcw-config.yaml` stores the
list of project IDs. Inheritance is a property of the project, not of the
ledger, so two projects whose `capabilities.path` resolves to the same folder
may inherit differently. Capability inheritance remains independent from
taxonomy inheritance, and a parent link alone does not make capabilities
inherited: the ancestor must also be listed in `capabilities.extends`. Legacy
alias-to-path maps fail closed. Adding or removing a project changes only the `capabilities.extends`
lines of `tcw-config.yaml`, keeping my comments and formatting; a file it cannot
edit that way is refused with the exact edit to make by hand, never rewritten. The file
is named on standard error and left for me to commit.

Until `extends` is replaced, it may name only an ancestor whose parent links
pass `capabilities` down to this project: a parent, or a project further up, reached
through links whose `inherit` includes `capabilities` (see [Name a project's
parents](tcw://C/cli/name-a-projects-parents)). Any other project — a child, a
sibling, a parent with `inherit: none`, or one this project does not name at
all — is refused, by `tcw capabilities extends add` with exit 2 and the file left
unchanged, and when read, with a message saying to name it under `parents:`
with an `inherit` that includes `capabilities`. When such an ancestor, or a project
between it and this one, is not on this machine or its parents cannot be read,
a command that reads the capabilities stops with exit 7, naming the project and how
to fetch it, and `tcw validate` reports it as could not be checked.
