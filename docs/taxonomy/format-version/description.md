The version of TCW whose file format a `tcw-*.yaml` file follows, recorded in
the file itself as `tcw-version`, written as text (`tcw-version: 4.0.0`). It is
set when TCW creates the file and changed only by a migration, never by an
ordinary edit. TCW reads a file whose format version has the same major number
as the running TCW and a minor number no greater than its own; it refuses a file
with none (a TCW 3.x file), an older major version, or a newer one, naming what
to do. It describes the file, not the project's configuration, so it is never
merged between configuration layers or shown as a setting.
