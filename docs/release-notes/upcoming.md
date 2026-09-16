# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Your Jira tickets keep up with your work in more of the ordinary cases

**You can say which transition a move should use.** Lots of Jira workflows have two
ways to reach `Done` — one for finished work, one for abandoned work. TCW would not
guess between them, so completing or discarding an item could never reach the
ticket. Now you can name the transition for each move, and name a different one for
each kind of discard so the ticket ends with the right resolution. Anything you do
not name keeps working exactly as before. Upgrade every copy of TCW on the project
before you use this: version 2.3.0 and earlier treat the whole tracker setup as
broken when they see these settings.

**Linking a ticket to work already under way no longer leaves it stuck.** Before, the
ticket stayed where it was for good and every later move was reported as a conflict
that blamed you for moving it. Now linking leaves the ticket alone unless you ask,
warns you when it does not match the item, and while it stays that way later moves
say plainly that it was linked without its status synced. Add `--sync-status` to `tcw work tracker
link` to bring the ticket up to date: TCW claims it and moves it to where the item
is — directly when your workflow allows, otherwise one step at a time through the
statuses you mapped. It never moves a ticket backwards and never touches one already
closed. A ticket stuck this way from an earlier version is fixed by unlinking it and
linking it again with `--sync-status`.

**Moving a ticket part of the way by hand is no longer treated as interference.** If
a move failed to reach Jira and you moved the ticket yourself to the next status
along, TCW now finishes the journey instead of reporting that somebody moved it.

**Discarding work whose ticket nobody is assigned now closes the ticket.** Teams
whose queue hands out unassigned tickets were left with every such ticket open and
unresolved. A discard can now close one — and says why on the ticket. Every other
kind of move still leaves an unassigned ticket alone, and a ticket somebody else is
assigned is never touched.

**`tcw work tracker sync <slug>` no longer reports success when it did nothing.**
Naming an item somebody else started, while something is still owed on it, now fails,
tells you what is owed, and tells you how to run it as them or take the item over.

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
