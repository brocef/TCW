## Taxonomy and capabilities come from your parents

A project now takes its parents' taxonomy and capabilities through its parent
links, every level up, from each parent whose `inherit` includes them. The
`extends` settings and the `tcw taxonomy extends` and `tcw capabilities
extends` commands are gone. A project whose `.tcw/tcw-config.yaml` still holds
`taxonomy.extends` or `capabilities.extends` is told what to write instead,
and its taxonomy and capabilities commands stop until the key is deleted.

## Changing one inherited entry

To change one entry you inherit, put your own entry at the same path, holding
only what you change; everything else still comes from the parent. `tcw
capabilities set` on an inherited capability does this for you, and so does
`tcw taxonomy add` at a path you inherit. `show`, the JSON records and the web
app say which entry yours overrides. `tcw capabilities reset` and `rm` take
yours away again, and the inherited entry shows through.

An entry of your own that overrides nothing must be complete: a name, a
description file and, for a capability, a status. So a leftover change whose
original moved or was removed is reported by `tcw validate` instead of
quietly standing alone.

When two parents that are not related to each other both have an entry at
one path, the one later in the load order is used, whole, and `tcw validate`
and the listings warn about it until you decide with a complete entry of your
own.

## A parent that is not here

With a parent missing, your own entries can still be listed (`--local`) and
shown, marked as partial, and `tcw validate` says what it could not check.
The commands that need what the parent passes down stop with exit code 7.

## Smaller changes

- Capabilities no longer carry a `cap-` id. A capability is named by its
  path; `tcw validate` reports an `id: cap-…` line left in a capability's
  file.
- Editing a capability's body in the web app changes only that capability's
  own description, so attached documents and an inherited description are no
  longer copied into it.
