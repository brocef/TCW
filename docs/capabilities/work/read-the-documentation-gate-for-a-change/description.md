As a user or agent, I read the documents my project expects to move with a
change, and what to write in each, without opening a configuration file and
parsing prose.

**At a lifecycle stage the entries arrive inline.** `tcw work stage begin plan` and
`tcw work stage begin implement` render them into the stage's instructions, so
planning names a documentation task for every trigger expected to fire and
implementation answers each fired trigger over the finished diff — see
[Run a lifecycle stage](tcw://C/work/run-a-lifecycle-stage). Where a project has
declared nothing, the same span falls back to its own text unchanged, so a
project that configured nothing gets byte-identical instructions rather than a
blank where its entries would have been.

**`tcw work docs` is the verb for the times there is no stage to hang off.** The
gate runs at three points and only two of them are stages: the third is the
version offer *after* an item completes, when `tcw work stage begin implement` is
correctly refused because the item is closed. It prints each entry's path,
trigger, and description, and writes nothing.

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
