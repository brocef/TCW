# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Replacing TCW's own procedures

- **Your project can now replace the text of ten of TCW's procedures**, the way
  it could already add to a stage's instructions. They cover working items
  unattended, triaging GitHub issues, keeping documentation in sync, running a
  post-mortem, filing a work item, auditing the backlog, consolidating plans,
  splitting an item, delegating a stage, and searching the board.
- New command: `tcw work procedure prompt <procedure> [<item>]` prints one,
  composed with your project's own text. With nothing configured it prints
  exactly what TCW ships today.
- New setting: `work.procedures` in `tcw-config.yaml`, beside
  `work.lifecycle`. `tcw validate` checks it.
- The skills themselves do not read from the command yet; that comes next.
- **The `tcw-work-create` and `documentation-sync` skills now read from it.** A
  project's own text for `create-work` or `documentation-sync` is what an agent
  using those skills follows. Two things stay TCW's: filing a work item still
  searches for existing work first and ends in exactly one outcome, and
  documentation sync still takes its entries from `tcw work docs`.
  `documentation-sync` keeps working in a project that does not use TCW.

## Getting a stage's instructions

- **The `tcw-work-stage` skill now checks how it was called.** If it is invoked
  without a stage, with a stage that does not exist, or with a work item that
  cannot be found, the first thing the agent sees is a short error saying how
  the skill should be called and what was wrong, instead of a page with broken
  sections.
- **Under Codex, the skill says to run its commands yourself.** Codex does not
  run the commands a skill embeds, so when the check is run there it starts
  with a note saying so.
- **Agents are sent to `tcw-work-stage` for how to do a stage.** The `tcw-work`
  skill and the planning, verifying, inbox, drive-to-completion, post-mortem and
  issue-triage skills now point at `tcw-work-stage`, which delivers a stage's
  instructions together with your project's own additions to them. Before, an
  agent could read TCW's stage document on its own and miss your project's
  instructions.
- New command: `tcw work stage validate <stage> [<item>]`, the check the skill
  runs.
