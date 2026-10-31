## `tcw migrate` brings a TCW 3.x project to 4.0

TCW 4.0 refuses a project still in the 3.x format and names one command to
run: `tcw migrate`. Run in the project's folder, it converts the project in
place:

- the configuration moves into `.tcw/`, with `projects:` and `extends`
  turned into parent links and manifest entries;
- every term, capability and work item gets its 4.0 state file, and the
  capability ids TCW 3 used are kept in `.tcw/tcw-migration.yaml`, so
  references to them still resolve; keep that file, and keep it in a
  library other projects read;
- files TCW 3 kept loose beside an object move into its `resources/`
  folder, and links to them are rewritten;
- an override moves to the path of the capability it overrides;
- references and links get the project that owns what they point at;
- in a project that keeps its work in Jira, each ticket's `TCW Item` is
  rewritten to the 4.0 form, and only that field.

`tcw migrate --dry-run` lists every change, ticket edits included, and
writes nothing. `tcw migrate --no-jira` converts the files and leaves the
tickets for a later run. Nothing is written until the whole plan is known
to be possible; a problem that stops it is listed with how to fix it. The
report also lists what needs your attention and what TCW 4.0 will read
differently from TCW 3.

If a run is stopped partway, run `tcw migrate` again: it finishes what was
started. Until it has finished, do not commit the files. Commit or back up
before a real run.

In a family of projects, migrate each one, parents first; each run names
the related projects still in the 3.x format and the command to migrate
each. Everyone working on a project upgrades together; when someone else
has already migrated and committed, your own `tcw migrate` converts what
is still yours: your personal settings and, for a project TCW 3 cloned
for you, an entry pointing at that clone.

TCW 4.0 does not let the shared files name a related project by an
absolute path (or one starting with `~`), since such a path is only right
on one machine. When the TCW 3 configuration did, the person who migrates
gets that path in their own `.tcw/tcw-manifest.local.yaml`, which is not
committed, and the run lists it under "needs attention" (A14). Everyone
else adds their own entry to their own `.tcw/tcw-manifest.local.yaml`;
their `tcw migrate` cannot do it for them, because the path is no longer
in any shared file.
