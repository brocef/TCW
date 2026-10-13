As a user, I run `tcw validate` to check the current project: its
`tcw-config.yaml`, its connections to other projects, the YAML and `tcw://` links
in its stores, its taxonomy and capabilities ledger (what `tcw taxonomy check`
and `tcw capabilities check` did before 3.0), and its work items. It checks this
project only; a reference into another project is checked by resolving it. It
takes no path, and nothing it does reaches the network.

**Findings are the product, so they go to standard output**, one per line, as
`<severity>: <where>: <message>`, where `<where>` is a file (with `:<line>` when
known) or an item slug. A clean run prints nothing on standard output. Standard
error carries a closing count, such as `2 errors, 1 warning, 0 unresolved`, and
notes such as a `TCW_PROJECT_<ID>` override in effect.

There are three severities, and only one fails the run:

- `error` — malformed YAML, a broken `tcw://` link, an `item.yaml` that cannot be
  read, a taxonomy or capabilities problem (including a capability record that
  still carries the retired `Planning doc` or `Tracker` field), or a
  configuration problem. Any error makes `tcw validate` exit 1.
- `warning` — for example a parent or blocker that names no item, an item whose
  latest verdict round is invalid, or a stage ahead of its artifacts. The run
  still exits 0.
- `unresolved` — something declared that cannot be checked from here: a project
  that is not on this machine, or a reference into one. The run still exits 0.

**Connections between projects.** Missing or invalid IDs, malformed entries
under `projects:`, mismatched IDs, a parent and child that do not name each
other, and cycles are errors, with guidance on how to fix them. A parent/child
connection is declared on both sides; an `upstream` connection is declared only
by the reader and needs no counterpart. An upstream is never validated as part
of the reader: only its own config is read, and problems in its connections are
its own. A project declared as its own upstream, or declared upstream while also
reachable as family, is an error. A former child still naming a parent that now
reads it as an upstream is a warning, so neither project is blocked mid-change.
The 2.x key `connected-projects` is an error naming
`docs/migration-guide-2.8-to-3.0.0.md`.

**Stores.** Validation tells a store's three failure modes apart: a
`<component>.path` that is simply wrong, a store declared in another repository
but not yet provisioned here (naming the declared remote and `tcw provision`),
and a malformed `repository` block (naming the configuration key). The last is
reported even when no local store can be opened to report it through. A store
that cannot be opened is one finding beside the others rather than the end of
the run, so one unprovisioned store does not hide the rest. A `<component>.path`
that names a folder holding no store, in a project that also declares a home
repository it has not obtained, is two findings, not one; a configured path that
simply does not exist stays silent when a home repository is declared, because
that is the ordinary state of a checkout holding only the code. A taxonomy or
capabilities `config.yaml` or `.config.yaml` left over from before 2.5.0 is
reported once for each store that has one.

**Work items.** Every item is checked: an `item.yaml` that cannot be read is an
error naming the file and the key, and the other checks still run over the items
that can be read. An item whose stage is not in the stage table, or is disabled
in this project, is reported. While an item is still being worked, its
`capabilities.yaml` is checked for paths that cannot be right. A work store
shared with another project in this repository, which would mix their items, is
an error.

**Jira mode.** When the project keeps its work items in Jira, plain
`tcw validate` checks only what is on this machine. `tcw validate --remote` also
checks the project against Jira itself — its workflow, its fields, and the
stages and links of its items — and only reads. A Jira that cannot be reached is
exit 5. In a project that keeps its items in files, `--remote` is a usage error
(exit 2).
