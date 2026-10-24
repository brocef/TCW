---
name: work
description: Drives the `tcw work` change-tracking CLI — the Work axis of TCW (Taxonomy · Capabilities · Work). Use when planning, implementing, reviewing or testing a tcw work item; resuming one across sessions; deciding on an arrival in the inbox; splitting an item into child items; or filing work into another project. Does not reimplement the CLI.
when_to_use: Use when starting, continuing, triaging, planning, implementing, reviewing, testing or splitting tcw work items — when a user asks to plan work, drive work to completion, decide on inbox arrivals, move an item to its next stage, resume an item across sessions, break a large item into child items (`tcw work new --parent`), or make a part in another project (`tcw -C <folder> work new --parent`). Also when searching the board, auditing unfinished work, or asking which stage could have caught a problem.
allowed-tools: Bash(tcw *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

# Driving `tcw work`

`tcw work` tracks each change as an item that moves through stages. This skill
is the **judgment** on top of it. Name `tcw …` commands; never compose a path
into the work store, and never edit the store by hand where a command exists —
see [`commands.md`](references/commands.md).

Work is the last layer in `Vocabulary → Features → Capabilities → Work`; an item
may change any earlier one. For a change users will notice, check those layers
in order first. **REQUIRED SUB-SKILL: Use the `capabilities` skill.**

## Stages

An item is at exactly one stage. Each stage's instructions come from
**`tcw work stage prompt <stage> <slug>`**: TCW's own text for that stage,
composed with this project's, and the same under every harness. Read it before
working a stage, and follow it; this skill does not repeat it.

| Stage        | Writes, through `tcw work path <slug> <stage>`                                                                                                  |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `inbox`      | nothing: an arrival is accepted, split or turned away                                                                                           |
| `request`    | the request: what to build, for any reader                                                                                                      |
| `spec`       | the spec, `capabilities.yaml` in the item's folder, and a `QA plan` comment                                                                     |
| `plan`       | the plan                                                                                                                                        |
| `implement`  | the code, the records, and one round (`--next`) with no verdict                                                                                 |
| `review`     | one round with `verdict` and `judges` front matter                                                                                              |
| `qa`         | one round with `verdict` and `judges` (with `decided-by` when a person decides); where the backend keeps qa, findings in a comment and no round |
| `postmortem` | a side stage on any item that was not discarded; never moves it                                                                                 |

`completed` and `discarded` end an item. **`tcw work advance <slug>`** moves an
item to its next enabled stage once the stage's output is written; the gates run
on the move, and `--dry-run` says whether it would pass. A rejected review or qa
round sends it back to implement. `--to <stage>` moves elsewhere (backwards
needs no force); `tcw work discard <slug> --reason "<why>"` abandons it.
**`judges`** in a round is the number of the newest implement round it judged,
so a verdict on older work counts for nothing.

Some backends keep a stage themselves (in Jira, request and qa happen on the
ticket): the stage has no folder, and a person decides whether the item moves
on. When that person tells you in the conversation to move it, or gives you
the qa verdict, move it with `tcw work advance` as the stage prompt says; a
move made that way runs the checks and hooks bound to it, and one made by
hand in Jira does not. A question or an implied yes is not that instruction,
and without it you stop. The configure skill's Jira reference covers that setup.

## Finding your place

1. `tcw work show <slug>` prints the item's stage, its request, and its
   comments, newest first. `tcw work list` lists unfinished items;
   `tcw work list --mine` those assigned to you.
2. Read the newest handoff for that stage: the newest `handoff-*.md` in the
   folder `tcw work path <slug> <stage>` prints, or, where the backend keeps
   the stage, the newest comment whose first line is `Handoff`. It describes
   the work when it was written; check for anything newer before trusting it.
   Handoffs are never deleted; the newest wins.
3. `tcw work stage prompt <stage> <slug>`, and work the stage.

The inbox is different: it is about arrivals, not one item, so it has no
handoff to read. Run `tcw work stage prompt inbox`, with no slug, and work
every arrival it names.

## Rules no project text changes

- **Stages may go to a subagent; moves never do.** `tcw work advance` and
  `tcw work discard` run the gates once, in the session that holds the user.
  Request is not dispatched, because it asks the user. Qa is not dispatched
  where a person decides its verdict: where the backend keeps qa, or where the
  project's qa prompt says so. With TCW's own qa text on the filesystem, the
  agent records the verdict, so qa may be dispatched like review. A subagent
  is permitted, never required: a session that cannot dispatch runs the same
  stage itself.
- **Search is read-only.** No move, no `tcw work edit`, no file written. A
  search that changed the board would make its own result untrustworthy.
- **An audit asks before changing the board, grouped by kind**: one approval
  for tag edits, one for blockers, one for discards, naming each discard
  inside its group. Asking per item is unusable; asking once for everything is
  a blanket yes on decisions that deserve thought.
- **Epics are parents.** An item with children is an epic; add one with
  `tcw work new "<title>" --parent <slug>`, and `tcw work list --parent <slug>`
  lists them.
- **A part for another project is made in that project**, with
  `tcw -C <folder> work new "<title>" --parent <full id>`, where `<folder>`
  is that project's folder or `tcw://<id>.path/`; `tcw project list` names
  the projects this one declares under `projects:` (the configure skill's
  reference on projects explains the key). The plan prompt's step 6 gives the
  order for an epic's parts.

## Another project's exit codes

- Reading a project nothing declares exits 4; one declared but not on this
  machine exits 5.
- The `--project` option of `tcw work new` and the `--blocks` option of
  `tcw work edit` are removed in TCW 4: each exits 2 and names the command to
  run instead.
- A change to another project's item, term or capability exits 3 and names
  its folder: run it there, with `tcw -C <folder>`.

On exit 5, or exit 3 for an absent project, report it and pass on the
instruction its message gives (the manifest entry to add or correct, or the
command that fetches the project); do not retry.

## Read on demand

- [`commands.md`](references/commands.md) — every command, what it prints, piping text in, addressing items
- [`tags.md`](references/tags.md) — the project's tag registry
- Turning an idea into a work item without duplicating tracked work → the `work-create` skill
- **Only when the user asks for it** — reviewing every unfinished item for stale, duplicate or misplaced work: `tcw work procedure audit-backlog` · answering a described question about the board as a table: `tcw work procedure search`. Each prints this project's text, or TCW's own; the rules above hold whatever it says.
- "Which stage could have caught this?" → the postmortem stage: `tcw work stage prompt postmortem <slug>`
- Stage bindings, hooks and every configuration key → the configure skill
