# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## TCW's skills, reorganized

The plugin's skills have new names and a clearer split, and there are no slash
commands any more. If you used the old names, here is where everything went.

- **Setting TCW up is the `tcw-setup` skill.** It replaces `tcw-plugin`, and
  covers installing or repairing `tcw`, starting TCW in a repository, getting a
  project that is set up elsewhere working on a new machine, and writing a first
  taxonomy or capabilities ledger from your code.
- **Changing TCW's configuration is the `tcw-configure` skill.** Ask it to set up
  or change documentation entries, lifecycle bindings, the Definition of Done, a
  tracker, where stores live, or connected and inherited projects.
- **There are no slash commands.** The everyday workflows are skills you ask for
  by name: `tcw-commands-plan-work`, `tcw-commands-drive-work-to-completion`,
  `tcw-commands-verify-work` and `tcw-commands-process-inbox`. For searching the
  board, auditing the backlog, or consolidating plans, ask the `tcw-work` skill.
  For a post-mortem, use the `tcw-post-mortem` skill. To cut a version, ask the
  `documentation-sync` skill.
- **The five per-stage skills are gone.** `tcw-work-stage` takes the stage and
  the work item, and works the same in Codex.
- **Three optional skills were renamed** so their names say they are optional:
  `autonomous-work` is now `tcw-extras-autonomous-work`, `tcw-triage-issues` is
  now `tcw-extras-triage-issues`, and `tcw-report` is now `tcw-extras-report`.
