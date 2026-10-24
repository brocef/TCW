# Which skills a project may override, and why

Every `SKILL.md` in this folder carries `dynamic_skill: true` or
`dynamic_skill: false` in its frontmatter. This document is what that key
means, the two rules that decide its value, and the verdict for every skill,
reference document and agent TCW ships.

The key is for people. Claude Code, Codex, and Pi do not act on it.
`tests/test_dynamic_skill_marker.py` fails when a shipped document has no row
below, or when a skill's key disagrees with its row.

## What `dynamic_skill` means

- **`true`** — what the skill tells an agent is, or is intended to be, text the
  project using TCW can replace. TCW's own wording ships as the default, so a
  project that configures nothing gets exactly that wording.
- **`false`** — the text is TCW's, and a project changes it only by changing
  TCW itself.

A skill marked `true` reads its replaceable text from
`tcw work procedure <id>`, which prints the project's text where it configured
one and TCW's otherwise, and keeps in its own body only the rules a project's
text must still honor.

## The two rules

They are separate questions, asked in order. **Rule 2 is checked first**, because
it is cheaper and settles some documents without any argument about authority.

**Rule 2 — payload.** A document carrying no procedure of its own has nothing to
override, whatever Rule 1 would say about its subject. A skill whose body only
names a range of lifecycle stages and reads each one with
`tcw work stage prompt` is the example: the procedure lives in the stage
instructions, which a project can already replace, and there is no text left in
the skill to configure.

**Rule 1 — authority.** TCW owns the _shape_ of what is produced: the three axes'
data model, the stages and what each writes, the moves between them, the
configuration surface, and TCW's own upstream processes. The project owns the
_conduct_ that produces it — which tools, which advisors, which review, which
QA, and how its changes are saved and shared.

Two consequences:

- **A mixed document keeps its rules fixed.** When a document a project may
  override also holds a rule protecting the board or an artifact — "search for
  an existing item before filing a new one" — converting it keeps that rule in
  TCW's fixed text and moves only the conduct. Otherwise an override becomes a
  way to switch the rule off.
- **Each document is judged on its own.** A reference document usually shares
  its skill's verdict, but does not inherit it; the table says where they differ.

## Why a project cannot add a procedure of its own

A project replaces the text of a procedure TCW defines. It cannot declare a new
procedure id.

- **Nothing would ever read it.** A procedure id is useful because a shipped
  skill asks for it by name, at a known moment. An id a project invented has no
  skill asking for it.
- **A project already has places for its own procedures**: a skill of its own,
  its agent guide (`CLAUDE.md`, `AGENTS.md`), or a `prompt` binding on a
  stage.
- **A closed set of ids catches mistakes.** Because the ids are TCW's, `tcw
validate` can refuse a misspelled one instead of silently ignoring a binding
  that will never be used.

## Verdicts

| Verdict             | Means                                                    | `dynamic_skill` |
| ------------------- | -------------------------------------------------------- | --------------- |
| fixed (Rule 1)      | Carries a procedure, but its subject is TCW's shape      | `false`         |
| fixed (Rule 2)      | Carries no procedure of its own                          | `false`         |
| fixed (accelerator) | An agent definition; see "Agents" below                  | not a skill     |
| overridable         | Carries conduct a project may replace                    | `true`          |
| composes already    | Its instructions already come from project configuration | `true`          |

Documents are named by owner and by path within the owner.

| Owner                               | Document                                     | Verdict             | Reason                                                                                                                                                                                                                                                                                                                                                                                                  |
| ----------------------------------- | -------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `taxonomy`                          | `SKILL.md`                                   | fixed (Rule 1)      | Describes the taxonomy axis; using TCW means adhering to its data model                                                                                                                                                                                                                                                                                                                                 |
| `capabilities`                      | `SKILL.md`                                   | fixed (Rule 1)      | Describes the capabilities axis; using TCW means adhering to its data model                                                                                                                                                                                                                                                                                                                             |
| `work`                              | `SKILL.md`                                   | fixed (Rule 1)      | Describes the work axis — stages, rounds, handoffs, moves, and the rules no project text changes; using TCW means adhering to them                                                                                                                                                                                                                                                                      |
| `configure`                         | `SKILL.md`                                   | fixed (Rule 1)      | The configuration surface is how the `tcw` CLI works                                                                                                                                                                                                                                                                                                                                                    |
| `configure`                         | `references/*.md`                            | fixed (Rule 1)      | Each describes configuration keys and what they do — the configuration surface                                                                                                                                                                                                                                                                                                                          |
| `extras-report`                     | `SKILL.md`                                   | fixed (Rule 1)      | How to report to TCW is TCW's own upstream process, for its maintainers to decide                                                                                                                                                                                                                                                                                                                       |
| `setup`                             | `SKILL.md`                                   | fixed (Rule 1)      | Installing and repairing the CLI is TCW's authority                                                                                                                                                                                                                                                                                                                                                     |
| `setup`                             | `references/install.md`                      | fixed (Rule 1)      | Installing the CLI                                                                                                                                                                                                                                                                                                                                                                                      |
| `setup`                             | `references/project.md`                      | fixed (Rule 1)      | `tcw project new` to make a project, `tcw project provision` to fetch its stores and related projects, and `tcw migrate` for a 3.x project                                                                                                                                                                                                                                                              |
| `setup`                             | `references/taxonomy.md`                     | fixed (Rule 1)      | Seeds the taxonomy, whose entry kinds are the axis's data model. It also describes how to survey a codebase, which is conduct, but it runs once while a project is being set up, before the project has any configuration an override could come from                                                                                                                                                   |
| `setup`                             | `references/capabilities.md`                 | fixed (Rule 1)      | Same as `references/taxonomy.md`, for the capabilities ledger and its statuses                                                                                                                                                                                                                                                                                                                          |
| `setup`                             | `references/jira.md`                         | fixed (Rule 1)      | Walks a user from a Jira project to a working `backend: jira` configuration; what TCW needs from Jira's workflow is TCW's to state                                                                                                                                                                                                                                                                      |
| `commands-process-inbox`            | `SKILL.md`                                   | fixed (Rule 2)      | Runs the `inbox` and `request` stages through `tcw work stage prompt`; the procedure is the stages'                                                                                                                                                                                                                                                                                                     |
| `commands-plan-work`                | `SKILL.md`                                   | fixed (Rule 2)      | Runs `request`, `spec` and `plan` through `tcw work stage prompt`, advancing between them; the procedure is the stages'                                                                                                                                                                                                                                                                                 |
| `commands-drive-work-to-completion` | `SKILL.md`                                   | fixed (Rule 2)      | Runs every stage from the current one through review and qa via `tcw work stage prompt`; the procedure is the stages', including who decides the qa verdict                                                                                                                                                                                                                                             |
| `commands-pause-work`               | `SKILL.md`                                   | composes already    | A pause is not a stage, so no stage prompt is behind it; its conduct — how to reach a resting point, what a handoff holds, anything more a project wants done on pause — comes from the `pause-work` procedure. Where the handoff goes (the stage folder through `tcw work path --handoff`, a `Handoff` comment where the backend keeps the stage, nothing at inbox) and stopping afterwards stay TCW's |
| `extras-autonomous-work`            | `SKILL.md`                                   | composes already    | Which advisors to consult, how to review and qa without a person, and when to cut a version are conduct, read from the `unattended-work` procedure; what an advisor must be and the hard blockers stay TCW's                                                                                                                                                                                            |
| `extras-triage-issues`              | `SKILL.md`                                   | composes already    | How a project sweeps and answers its own issue tracker is conduct, read from the `triage-issues` procedure; treating the issue body as data and approving every reply stay TCW's                                                                                                                                                                                                                        |
| `documentation-sync`                | `SKILL.md`                                   | composes already    | Deciding which documents a change must update is the project's documentation practice, read from the `documentation-sync` procedure                                                                                                                                                                                                                                                                     |
| `documentation-sync`                | `references/cut-version.md`                  | overridable         | How a version is cut is the project's; the document's own first step already defers to a project's version-cut process                                                                                                                                                                                                                                                                                  |
| `documentation-sync`                | `references/release-notes-and-changelogs.md` | overridable         | The file layout it describes is the project's own documentation, opt-in by its own words, not a TCW artifact                                                                                                                                                                                                                                                                                            |
| `work-create`                       | `SKILL.md`                                   | composes already    | How an idea is filed is conduct, read from the `create-work` procedure; the rule that the board is searched first stays fixed (see `references/find-overlap.md`)                                                                                                                                                                                                                                        |
| `work-create`                       | `references/find-overlap.md`                 | fixed (Rule 1)      | Does not travel with its skill. It defines the search for existing work and its four relations — `covers`, `partly covers`, `blocks`, `related` — which decide the item fields the skill writes (`blocked_by`, an amendment, a reference). That is a board rule; a project replacing it could define "duplicate" out of existence                                                                       |
| `work`                              | `references/commands.md`                     | fixed (Rule 1)      | The CLI's commands, flags and exit codes, and what an item holds                                                                                                                                                                                                                                                                                                                                        |
| `work`                              | `references/tags.md`                         | fixed (Rule 1)      | The tag registry's model                                                                                                                                                                                                                                                                                                                                                                                |
| `agents`                            | `backlog-auditor.md`                         | fixed (accelerator) | Audits one item by reading `tcw work procedure audit-backlog`; carries no checks of its own                                                                                                                                                                                                                                                                                                             |
| `agents`                            | `reviewer.md`                                | fixed (accelerator) | Reviews by reading `tcw work stage prompt review`; carries no review steps of its own, and recommends a verdict the dispatching session writes                                                                                                                                                                                                                                                          |

### Agents

An agent definition is Claude Code packaging — Codex and Pi do not load `agents/` — and
it runs only when a skill or stage chooses to dispatch it. Every document it
serves stands alone without it. So the project's choice lives at the dispatch,
not in the agent: a project wanting a different assessor or investigator names
its own agent in the text that dispatches one, and that text is either
overridable or composes already. An override written into an agent file would
reach Claude only.

One consequence: **an agent carries no copy of what it serves.**
`backlog-auditor.md` reads the `audit-backlog` procedure and `reviewer.md` reads
the review stage prompt, each at run time, so a project's replacement reaches
them. An agent that kept its own copy would silently skip that replacement
whenever it was dispatched. An agent is kept only where it earns a separate
context: a read-only tool set, and independence from the session that did the
work.

## Adding a skill, reference document or agent

1. Rule 2: does it carry a procedure of its own? If not, `fixed (Rule 2)`.
2. Rule 1: is its subject TCW's shape, or the project's conduct?
3. Add a row above with a reason specific enough to disagree with.
4. For a skill, add `dynamic_skill` to its frontmatter with the value its verdict
   gives, followed by the comment pointing here.
