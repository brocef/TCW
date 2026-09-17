# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## TCW no longer offers to cut a version

- **Finishing a work item no longer raises the question of a new version.**
  TCW used to suggest cutting one every time an item completed, and the
  suggestion fired on nearly every completion. It is gone.
- **`version offered` is no longer part of the Definition of Done.** The
  built-in checklist printed by `tcw work complete` now has four lines instead
  of five: tests pass, docs synced, capabilities reconciled, reviewed.
- **Cutting a version still works exactly as before — you ask for it.** Ask to
  cut a version and TCW walks the same steps it always did, including telling
  you when the last release was never published so this work can join it rather
  than becoming a second release stacked on top.
- Your release notes and changelogs are unaffected. They are kept current by the
  documentation step at the end of implementation, which never depended on a
  version being cut.

## Finishing work you did in a separate worktree

- **TCW no longer tells you that you skipped the verify stage when you did not.** If you
  work an item with `tcw work start <slug> --worktree`, everything you do there — sending
  the item for review, taking it back, resolving a blocker — is recorded on that item's own
  branch. Completing it from your main checkout used to read the older copy sitting there
  and could report the wrong thing: a false "the verify stage was skipped", a refusal over
  a blocker you had already resolved, or a complaint that your ticket was in the wrong
  place. Completing now reads the item as your worktree holds it. If that worktree is gone,
  it says so and carries on with the copy it has.
- **Completing now stops if the item's files in your worktree are not committed.** Only
  status changes commit themselves, so an acceptance note or a blocker change you made
  there can still be sitting uncommitted — and merging back carries only what was
  committed, so those files would quietly be left behind. TCW asks you to commit them
  first. If the file is `tracker.yaml`, commit it rather than deleting it: it can hold a
  ticket update that never reached Jira.

## Jira tickets waiting for triage show up in your inbox

- **Set `work.tracker.inbox-query` and `tcw work inbox list` shows your Jira
  tickets waiting for triage** beside the requests in your inbox, in two sections.
  Without the setting, nothing changes.
- **You can read and take a ticket without changing command.** `tcw work inbox
  show <ticket>` prints it with its description, and `tcw work inbox accept
  <ticket>` takes it exactly as `tcw work tracker import` does.
- If an inbox file has the same name as a ticket, the file wins; add `--ticket`
  to get the ticket.
- If Jira cannot be reached, you still see your inbox requests.
- Under strict mode, with `inbox-query` set, accepting a ticket from the inbox is
  allowed; accepting an inbox file is still refused.

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

## Breaking change: the skills and agents lost their `tcw-` prefix

Every skill the plugin ships is already addressed through the plugin's own name,
and then repeated it: the work skill was invoked as `/tcw:tcw-work` under Claude
and `$tcw:tcw-work` under Codex. The second `tcw` distinguished nothing — it was
four more characters to type and a stutter to read in a list of skills.

The prefix is gone. The same skill is now `/tcw:work` and `$tcw:work`.

**The old names stop working.** Neither Claude Code nor Codex offers a way to
keep an old skill name pointing at a renamed one, so there is no deprecation
period: after you update the plugin, typing `/tcw:tcw-work` will not find
anything. The full list is below so you can find whichever one your fingers
know.

The groupings stay. `commands-` still marks the four everyday workflow skills and
`extras-` the three optional ones, so they still sort together when you are
scanning for one.

### Skills

| Type this now                       | Instead of                              |
| ----------------------------------- | --------------------------------------- |
| `work`                              | `tcw-work`                              |
| `work-stage`                        | `tcw-work-stage`                        |
| `work-create`                       | `tcw-work-create`                       |
| `capabilities`                      | `tcw-capabilities`                      |
| `taxonomy`                          | `tcw-taxonomy`                          |
| `setup`                             | `tcw-setup`                             |
| `configure`                         | `tcw-configure`                         |
| `post-mortem`                       | `tcw-post-mortem`                       |
| `commands-plan-work`                | `tcw-commands-plan-work`                |
| `commands-drive-work-to-completion` | `tcw-commands-drive-work-to-completion` |
| `commands-verify-work`              | `tcw-commands-verify-work`              |
| `commands-process-inbox`            | `tcw-commands-process-inbox`            |
| `extras-autonomous-work`            | `tcw-extras-autonomous-work`            |
| `extras-triage-issues`              | `tcw-extras-triage-issues`              |
| `extras-report`                     | `tcw-extras-report`                     |

`documentation-sync` is unchanged — it never carried the prefix, and it is the
shape the others have moved to.

### Agents

The three read-only agents are renamed for the same reason. `post-mortem` names
both a skill and an agent, as it did before.

| Now               | Instead of            |
| ----------------- | --------------------- |
| `verifier`        | `tcw-verifier`        |
| `backlog-auditor` | `tcw-backlog-auditor` |
| `post-mortem`     | `tcw-post-mortem`     |

### What this does not break

**Your project's configuration.** A skill name reaches TCW only if you named one
in a lifecycle hook in your `tcw-config.yaml`. If you did — an entry reading
`skill: tcw:tcw-work` or similar — update it to the new name. Nothing else in a
configuration file refers to a skill, so for most projects there is nothing to
change. `tcw validate` does not check skill names, so it will not find an old
one for you: search `tcw-config.yaml` for `skill:` values that start with `tcw-`
or `tcw:tcw-`.

**Your work items, taxonomy or capabilities.** Nothing about your own project's
content is touched.

If your own `AGENTS.md` or `CLAUDE.md` tells contributors to "use the `tcw-work`
skill", that sentence now points at a skill that is not there. It will not break
anything, but it is worth a search-and-replace the next time you are in the file.

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

## Making an existing item an epic

- `tcw work edit <item> --type epic` turns an item into an epic, so an item that
  grew into an initiative no longer has to be re-created under a new name.
  `--type ""` makes an epic an ordinary item again.
- Making an epic ordinary is refused while any item still names it as its
  initiative, and when this checkout cannot see every project its children might
  live in.
- Under strict tracker mode, changing an item's type is refused, because epics
  are not tied to tickets. Create epics with `tcw work new --epic` there.

## The web app no longer accepts edits to generated files

- The local web app already hid the edit button for `rollup.md` and
  `tracker.yaml`, which TCW commands write. Its server now refuses a save to
  either one too, and says which command writes it.

## Codex setup instructions are complete

- Under Codex, the `setup` skill now gives the exact command that installs `tcw`,
  and the skills that fall back to reading a file from the plugin say where the
  plugin's folder is.

## `tcw taxonomy rm` refuses instead of deleting too much

- **This changes what an existing command does.** `tcw taxonomy rm admin` used to
  delete `admin` and every term nested under it, and removed a term other terms
  still pointed at with only a warning. It now refuses both, names the terms in
  the way, and deletes nothing — the same as `tcw capabilities rm`. Remove the
  nested terms, or repoint the references, first.
- Capabilities that name the term in `Subject` or `Feature` are not checked;
  `tcw capabilities check` still reports those.

## Getting a stage's instructions

- **The `work-stage` skill now checks how it was called.** If it is invoked
  without a stage, with a stage that does not exist, or with a work item that
  cannot be found, the first thing the agent sees is a short error saying how
  the skill should be called and what was wrong, instead of a page with broken
  sections.
- **Under Codex, the skill says to run its commands yourself.** Codex does not
  run the commands a skill embeds, so when the check is run there it starts
  with a note saying so.
- **Agents are sent to `work-stage` for how to do a stage.** The `work`
  skill and the planning, verifying, inbox, drive-to-completion, post-mortem and
  issue-triage skills now point at `work-stage`, which delivers a stage's
  instructions together with your project's own additions to them. Before, an
  agent could read TCW's stage document on its own and miss your project's
  instructions.
- New command: `tcw work stage validate <stage> [<item>]`, the check the skill
  runs.
