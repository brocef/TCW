Alter an inherited capability without touching its source:
`tcw capabilities set <path> --status <S>` / `--field K=V` on the inherited
path, or on the inherited capability's full identifier, writes my project's own
capability at the same path, holding only the fields I changed: no name, no
`id`, and no `overrides:` pointer. An override is simply my own capability at a
path I also inherit one at, and nothing in its files says it is one. It is
combined with the original field by field: a field it sets replaces the
original's, one set to `null` clears it, and one it leaves out keeps the
original's; a list field such as `Subject`, `prependedDocs` or `appendedDocs`
is replaced whole. The body is composed as `prependedDocs` (the override's
list, or else the original's), then the override's `description.md` when it
has text, or else the original's description, then `appendedDocs` (likewise).
`show` prints an `overrides:` line, and each record carries `overrides`, the
full identifier of the capability overridden. The project the capability is
inherited from is never modified. `tcw capabilities add` at an inherited path
is refused and names `tcw capabilities set`, since it would write a full copy.
An override is not moved or renamed away from its original's path, and a move
or rename that would make one is refused
([Rename or move a capability](tcw://C/capabilities/rename-or-move-a-capability)).

The override is files and nothing else: each file written is named on standard
error, and nothing is staged or committed. A write that fails part-way removes
the override folder it had just made, rather than leaving an empty one behind;
an override that already existed keeps what the write put in it.
