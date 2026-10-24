As a user or agent, I read one of TCW's procedures — how to work items unattended, triage issues, sync documentation, file a work item, audit the board, search the board, or pause work — with `tcw work procedure <id> [<slug>]`, and get it composed with whatever my project has configured for it.

The ids are `unattended-work`, `triage-issues`, `documentation-sync`, `create-work`, `audit-backlog`, `search` and `pause-work`. They name what the procedure does, not the skill that carries it, so renaming a skill never breaks my configuration.

**With nothing configured, I get TCW's own text.** A procedure my project configures under `work.procedures` replaces it, and `inherit: true` in my list puts TCW's text back wherever I place it. TCW's own text carries passages for each backend, and only the passage for my project's backend prints, so a project that keeps its work in Jira is not told to write files Jira keeps. Outside any TCW project, the command prints TCW's own text, so a skill that also runs outside one can rely on it.

The work item is optional. Without one, `when:` conditions never match and a `generate:` script receives no item. With one, conditions test that item's tags, a script receives its record, and an item named by another project's full identifier reads the owning project's configuration. If every binding I configured carries a `when:` that did not match, nothing prints, and a note on stderr says so.

The `audit-backlog` procedure covers my project and every project below it: it starts from `tcw work list --scope down --json`, names each item by its full identifier, and reports a project marked unavailable as not audited, with its reason, never as clean.

The text goes to stdout alone. Errors go to stderr with nothing on stdout — an unknown procedure id (a usage error, exit 2, naming the known ones), an item that does not exist (exit 4), or a `file:` binding that can no longer be read. `--no-exec` lists what would resolve on stderr and runs nothing. Nothing is ever written.

When my personal configuration files changed the list being composed, a `note:` line on standard error names them, so I can tell my own additions from the team's.
