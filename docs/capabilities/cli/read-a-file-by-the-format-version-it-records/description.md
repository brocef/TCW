As a user, I can trust that TCW never misreads one of its own files written in a
format it does not know. Every `tcw-*.yaml` file TCW writes records, in a
`tcw-version` key on its first line, the version of the TCW that created it or
last migrated it: `tcw init` writes `tcw-version: 4.0.0` at the top of
`.tcw/tcw-config.yaml`. The line is set when TCW creates the file and changed
only by a migration; `tcw init` giving the file an ID, `tcw work tags` and every
other edit TCW makes leave it as it is. It is information about the file, not a
setting, so `tcw config show` does not print it.

**Before reading a file, TCW checks its version**, and every command stops with
exit 1 when it cannot read it, naming the file and saying what to do:

- **No `tcw-version`**: the file is read as a TCW 3.x file. The message first
  gives the exact line to add as the file's first line, such as
  `tcw-version: 4.0.0`, and then names the command that converts a TCW 3.x
  file to TCW 4.
- **Not a version written as text**, such as an unquoted `4.0`, which YAML reads
  as a number: the message shows the form to write, such as `'4.0.0'`.
- **Older than TCW 4**: the message names the format's version and the
  command that converts it.
- **Newer than the running TCW**, comparing the major and minor numbers: the
  message names both versions and says to upgrade TCW. A newer patch number
  alone never changes a format, so a `4.0.5` file is read by TCW 4.0.3.

The same check applies to the project's personal file, to its two manifests,
`.tcw/tcw-manifest.yaml` and `.tcw/tcw-manifest.local.yaml`, and to the
configuration of a connected project, where a version this TCW cannot read is a
problem with the manifest entry that placed it, and the project is not read. A
manifest with no `tcw-version` is not read as a 3.x file, since TCW 3 had no
manifests: the message gives the line to add. `tcw validate` reports each as an
error.

**A TCW 3.x project is recognised, not misread.** A folder with
`tcw-config.yaml` at its root and no `.tcw/` folder is a 3.x project, and every
command run in or below it, `tcw validate` and `tcw init` included, refuses with
one line naming the folder and the command that converts it to TCW 4, and
writes nothing. `tcw --version`
and `--help` still answer.
