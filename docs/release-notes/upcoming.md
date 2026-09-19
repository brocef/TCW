# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## One config file per project

A TCW project used to be able to hold three config files: `tcw-config.yaml`, and
a second one tucked inside each of the taxonomy and capabilities folders. Those
two are gone. Everything a project configures now lives in `tcw-config.yaml`.

Between them, those files held a single setting — `extends`, the list of other
projects whose terms or capabilities you inherit. It is now `taxonomy.extends`
and `capabilities.extends`, sitting beside the `path` and `repository` settings
those components already had.

**If you have never set up inheritance, there is nothing to do.** The old files
only existed once you ran `tcw taxonomy extends add` or `tcw capabilities
extends`, so most projects never had them.

**If you have, please read
[the migration guide](../migration-guide-2.X-to-3.0.0.md).** An old file is now
ignored rather than reported, so a project that upgrades without moving the
setting quietly stops inheriting — the sign is `tcw taxonomy list` showing only
your own terms. Moving one line fixes it.

Two things change along with it. Inheritance now belongs to the project rather
than to the folder, so two projects sharing one taxonomy folder can inherit
differently — and a shared folder no longer forces its choices on everyone
reading it. And `tcw taxonomy extends add` now rewrites `tcw-config.yaml`, which
drops any comments in that file, exactly as `tcw work tags add` always has.
