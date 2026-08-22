As a user, I list the documents that must move with my code in
`tcw-config.yaml` under `work.documentation`, so the lifecycle can put them in
front of whoever is doing the work instead of hoping they go looking. Each entry
is three required keys — `path`, the document; `trigger`, the named condition
under which it must be updated; and `description`, what to write there.

**One file may carry several entries, as long as their triggers differ.** An
entry is identified by the `(path, trigger)` pair, not by the file alone, so a
long `README.md` whose command reference and validation section move for
different reasons gets one entry per section, each evaluated on its own. Two
entries agreeing on *both* path and trigger are a duplicate, and the problem
names the trigger that collided so I can tell which of two near-identical
entries is the accident.

**`tcw validate` checks their shape, and only their shape.** A blank field, an
absolute path, a path that escapes the node, whitespace inside a trigger, a true
duplicate. It deliberately does not check that `path` exists — an entry
routinely names a file I intend to create, and a placeholder like
`skills/<component>/SKILL.md` that resolves to no file at all is legal — and it
does not police the trigger vocabulary, which is mine to extend past the base
names with anything my project needs.

A problem in one entry does not blank the gate: entries that parse are kept
alongside the problems, so a typo costs me that entry rather than every
document my project tracks.

**Declaring nothing is a supported answer.** A project that configures no
entries keeps the older convention exactly — a `## Documentation Sync` section
in its `CLAUDE.md` or `AGENTS.md` — and nothing about its stage instructions
changes. The configuration form is the recommended one because a heading someone
renames is not a contract, but it is not required.

Reading them back is [Read the documentation gate for a change](tcw://C/work/read-the-documentation-gate-for-a-change).
