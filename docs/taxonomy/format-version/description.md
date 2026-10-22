The version of TCW whose file format a `tcw-*.yaml` file follows, recorded in
the file itself as `tcw-version`, written as text (`tcw-version: 4.0.0`). It is
set when TCW creates the file and changed only by a migration, never by an
ordinary edit. TCW reads a file whose format version is 4.0 or later and, with
major and minor numbers compared as a pair, no newer than the running TCW; the
patch number never matters. It refuses a file with none (read as a TCW 3.x
file), a version not written as text, one older than 4.0, or one newer than the
running TCW, naming what to do. It describes the file, not the project's configuration, so it is never
merged between configuration layers or shown as a setting.
