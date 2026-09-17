As a user or agent, I read the documents my project expects to move with a
change, and what to write in each, without opening a configuration file and
parsing prose.

**At a lifecycle stage the entries arrive inline.** `tcw work stage prompt plan` and
`tcw work stage prompt implement` render them into the stage's instructions, so
planning names a documentation task for every trigger expected to fire and
implementation answers each fired trigger over the finished diff — see
[Run a lifecycle stage](tcw://C/work/run-a-lifecycle-stage). Where a project has
declared nothing, the same span falls back to its own text unchanged, so a
project that configured nothing gets byte-identical instructions rather than a
blank where its entries would have been.

**`tcw work docs` is the verb for every caller that is not resolving a stage
prompt.** The gate itself runs at two points, both stages, but the entries are
also read outside the lifecycle entirely — the `documentation-sync` skill asks
for them before any stage is resolved, and the local web app reads the same
answer. It prints each entry's path, trigger, and description, and writes
nothing. It also answers for an item that is already closed, where
`tcw work stage gate implement` is correctly refused: the reading verb checks
nothing, so it responds with a note on stderr and exit 0.

`--json` adds `source`, and that field is the point of it: `config` means the
entries are declared and authoritative, so no Markdown needs reading;
`agent-guide` means the project declared nothing and the older
`## Documentation Sync` convention applies. A caller branches on that instead of
guessing. With no entries declared, stdout stays empty and the explanation goes
to stderr, so a pipeline receives no rows rather than a sentence pretending to
be one.

A file declared under two triggers comes back as two entries — two rows in the
table, two objects in `entries` — each printed beside the trigger that
distinguishes it. Declaring them is
[Declare which documents track which changes](tcw://C/work/declare-which-documents-track-which-changes).
