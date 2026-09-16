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
- Run outside a TCW project, the command prints TCW's own text, so skills that
  also work in other repositories (such as documentation-sync) still get their
  instructions.
- **The unattended-work skill no longer insists on particular advisors.** It
  now takes its advisors, its code review, how it closes an item out and
  whether it cuts a version from your project's `unattended-work` procedure.
  With nothing configured it behaves exactly as before: it asks Codex and an
  Opus subagent, never cuts a version and never pushes. What stays fixed is
  what an advisor must be, when a run stops to ask you, and the record it
  leaves in the item's `outcome.md`.
- **The issue-triage and post-mortem skills now use your project's text.** If
  you set `work.procedures.triage-issues` or `work.procedures.post-mortem`, that
  is what an agent follows; with nothing set it follows the same instructions
  as before. A few rules stay the same whatever you set: an issue's text is
  never followed as instructions, nothing is posted to an issue without your
  approval of the exact text, and a post-mortem never changes an item's status.
  Triaging with a forge other than GitHub means replacing the triage procedure.
- **Auditing the backlog, consolidating plans, splitting an item, delegating a
  stage and searching the board now follow your project's text** when it has
  replaced them. The instructions tell the agent to read them with
  `tcw work procedure prompt`; with nothing configured they are the same as
  before. The safety rules — ask before changing the board, delete only what git
  can restore, a search changes nothing — stay whatever your project writes. The
  backlog auditor agent reads its checks the same way.
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
