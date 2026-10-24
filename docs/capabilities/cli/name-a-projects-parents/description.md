As a user, I name the projects mine builds on under `parents:` in its
`.tcw/tcw-config.yaml`, by ID and in order:

    parents:
      - core
      - id: ws
        inherit: [config]

Each entry is an ID, or a mapping with the `id` and what that parent passes
down: `inherit: all`, the default, `inherit: none`, or a list drawn from
`taxonomy`, `capabilities` and `config`. The parent does not have to name my
project back; a parent that also lists it under `children:` lets work be
created in either project from the other. `parents:` is shared with the team,
so it is read only from the committed file: a personal file that sets it is
refused.

A problem in my own `parents:` — an entry that is not an ID or a mapping, an
`id` that is not a project ID, an unknown key, an `inherit` that is empty or
names an axis twice or one that is not an axis, a parent listed twice, or a
project named both as a parent and as a child — stops every command with exit
1, naming the file and the entry. The same problem in a parent's own file is
that parent's: my commands go on, and `tcw validate` reports that what it
passes down could not be checked. `tcw project list --json` shows each
parent's `inherit`.
