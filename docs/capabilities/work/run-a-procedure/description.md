As a user or agent, I read one of TCW's procedures — how to work items unattended, triage issues, sync documentation, run a post-mortem, file a work item, audit the backlog, consolidate plans, decompose an item, delegate a stage, or search the board — with `tcw work procedure prompt <id> [<ref>]`, and get it composed with whatever my project has configured for it.

The ids are `unattended-work`, `triage-issues`, `documentation-sync`, `post-mortem`, `create-work`, `audit-backlog`, `consolidate-plans`, `decompose`, `delegation` and `search`. They name what the procedure does, not the skill that carries it, so renaming a skill never breaks my configuration.

**With nothing configured, I get TCW's own text** — today the same words the matching skill or reference document ships. A procedure my project configures replaces it, and `builtin: true` in my list puts TCW's text back wherever I place it.

The work item reference is optional. Without one, `when:` conditions never match and a `generate:` script receives no item. With one, conditions test that item's tags and type, a script receives it as JSON, and a `<project-id>/<slug>` reference reads the owning project's configuration. If every binding I configured carries a `when:` that did not match, nothing prints, and a note on stderr says so — and, when I gave no item, says that a condition never matches without one.

The text goes to stdout alone, with no header or footer: a procedure has no gate to remind me of and no next stage to point at. Errors go to stderr with nothing on stdout — an unknown procedure id (naming the known ones), an item that does not exist, or a `file:` binding that can no longer be read. `--no-exec` lists what would resolve on stderr and runs nothing. Nothing is ever written.

There is no `gate` for a procedure: it has no status it belongs to.
