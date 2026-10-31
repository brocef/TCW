---
name: work
description: Drives the `tcw work` change-tracking CLI — the Work axis of TCW (Taxonomy · Capabilities · Work). Use when planning, implementing, reviewing or testing a tcw work item; resuming one across sessions; deciding on an arrival in the inbox; splitting an item into child items; or making an epic's part in another project. Does not reimplement the CLI.
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

Every item is named by its **full identifier**, `<project>.work/<id-path>`:
the ID of the project that owns it, its work store, and its id-path, the path
of its folder in that store, such as `app.work/2026-10-24-epic/2026-10-24-part`
for a part kept inside its epic's folder. `<slug>` below is the nickname
TCW's help uses for that name. In the item's own project the id-path alone is
enough; the `tcw://` address and a tracker key are accepted too, as
[Addressing an item](references/commands.md#addressing-an-item) lists. Output
always prints the full identifier: report it in full, since an id-path from
another project names nothing here.

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
   comments, newest first; given another project's full identifier, it reads
   that item from its own project. `tcw work list` lists this project's
   unfinished items; `tcw work list --mine` those assigned to you.
   `--scope` widens a listing to related projects: `own`, the default, is
   this project alone; `down` adds every project below it (its children and
   theirs); `up` adds its ancestors (its parents and theirs); `all` adds both,
   the whole family seen from here, though never a sibling. `--project <id>`
   then keeps one covered project's own items. A covered project that cannot
   be read is left out with a warning, not an error.
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
  a blanket yes on decisions that deserve thought. It names every item by its
  full identifier, and a change it recommends to another project's item is
  written to run in the project that owns it, starting
  `tcw -C tcw://<id>.path/`.
- **Epics are parents.** An item with children is an epic; add a part with
  `tcw work new "<title>" --parent <slug>`, which puts the part's folder
  inside the epic's folder (`--flat` keeps it at the top of the work folder
  instead). `--parent`, not the folder, is what makes it a part. `tcw work list --parent <slug>` lists
  this project's parts, and `--scope down` adds the parts in projects below.
- **Moving and renaming keep nested items together.**
  `tcw work move <slug> --into <id-path>` puts an item's folder inside
  another (`--top` brings it back out), and `tcw work rename <slug> <new-name>`
  changes the words after the date; the items nested in the folder go with
  it. A move changes only the folder: the `parent` field still decides whose
  part it is, so set it with `tcw work edit <slug> --parent <epic>` when that
  changes too. Both print one `<old> -> <new>` line per changed identifier
  and rewrite references in this project only: pass those lines on to the
  owners of any other project that names the items, where `tcw validate`
  reports the old names.
- **A part for another project is made in that project**, with
  `tcw -C <folder> work new "<title>" --parent <full id>`. `<folder>` is the
  folder `tcw project path <id>` prints, or the address `tcw://<id>.path/`.
  The part's folder is made at the top of that project's work folder, since
  the epic's folder is not there, and a `not nested:` line says so. A blocker in
  another project is recorded on the blocked item, in the blocked item's own
  project: `tcw work edit <slug> --blocked-by <full id>`. `tcw project list`
  names this project and the projects it is connected to, its parents and
  children (the configure skill's reference on projects explains them). The
  plan prompt's step 6 gives the order for an epic's parts.

## Another project's exit codes

- **Exit 1, `check the spelling`:** a full identifier or address names a
  project ID that nothing here knows. Check the ID against `tcw project list`.
- **Exit 3, `belongs to project`:** a command that changes an item, a
  taxonomy entry or a capability runs only in the project that owns it. The
  message ends `run the command there:` followed by `tcw -C <folder>`, with
  the owning project's folder, and an ellipsis (`…`) that stands for the
  command just refused. When the
  user's request covers that project, run the same command again with
  `tcw -C <folder>` written before it. When the message says
  instead that the project is not on this machine, report it.
- **Exit 5, `is not on this machine`:** the command had to read a related
  project that is not here. The message says where TCW looked and which
  manifest entry to add (a manifest is the file in `.tcw/` that says where
  each related project's folder is); report which project the command needs
  and pass that on. `tcw project provision <id>` fetches it when a manifest
  entry gives its repository. Where the fetched copy may go is limited.
  This project's own two manifests (`.tcw/tcw-manifest.yaml` and
  `.tcw/tcw-manifest.local.yaml`) may place it anywhere. Any other manifest
  may place it only in a folder directly inside the folder that holds the
  repository of that manifest's owner (the project whose `.tcw/` holds the
  manifest), and not in a folder whose name starts with `.`. Even that is
  refused when the folder holding the owner's repository is the home folder,
  a folder above it, or a hidden folder below it. There are two ways past a
  refusal: run `tcw -C <folder> project provision <id>`, where `<folder>` is
  the owner's folder; or add an entry for the project, with a `repository`
  as well as a `path`, to this project's own manifests or to the owner's
  `.tcw/tcw-manifest.local.yaml`. The guide on related projects,
  `docs/guide/multi-repo.md` in the TCW repository, gives the cases this
  leaves out.
- **Exit 7, `inherits its`:** something this project inherits through a
  parent link is not available here, because that parent is not on this
  machine or its own parent links cannot be read. Report which project the
  command needs and pass on how to fetch it. When the message names a
  configuration setting (`work.tags`, `work.jira`), report which project it
  comes from and its two remedies: fetch that project, or leave `config` out
  of that parent's `inherit` list in `.tcw/tcw-config.yaml`, so the setting
  stops coming from it.
- **Exit 1, `is a TCW 3.x project`:** the folder holds a project made by TCW
  3.x, which every command refuses until `tcw migrate` moves it over. Moving
  a project over rewrites its files, so it is the user's decision: pass the
  message on, offer `tcw migrate --dry-run` to show what would change, and
  name the migration guide, `docs/migration-guide-3.X-to-4.0.0.md` in the TCW
  repository
  (https://github.com/brocef/TCW/blob/main/docs/migration-guide-3.X-to-4.0.0.md).

On exits 1, 5 and 7, do not retry: the same command fails the same way until
something on this machine changes.

## Read on demand

- [`commands.md`](references/commands.md) — every command, what it prints, piping text in, addressing items
- [`tags.md`](references/tags.md) — the project's tag registry
- Turning an idea into a work item without duplicating tracked work → the `work-create` skill
- **Only when the user asks for it** — reviewing every unfinished item for stale, duplicate or misplaced work: `tcw work procedure audit-backlog` · answering a described question about the board as a table: `tcw work procedure search`. Each prints this project's text, or TCW's own; the rules above hold whatever it says.
- "Which stage could have caught this?" → the postmortem stage: `tcw work stage prompt postmortem <slug>`
- Stage bindings, hooks and every configuration key → the configure skill
