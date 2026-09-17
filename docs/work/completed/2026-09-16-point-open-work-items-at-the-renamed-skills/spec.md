# Spec: Point open work items at the renamed skills

## Capability changes

None. Only documents under `docs/work/` change; no command, skill or ledger entry
does.

## Problem

Pull request #46 renamed every shipped skill and agent without the `tcw-` prefix
and left `docs/work/` alone. Open items still send readers to paths that no longer
exist. Running the intake's whole-name `git grep` over `docs/work/{backlog,active,blocked,review,inbox}`
on 2026-09-17 finds 50 matches in 21 files outside this item, none in `docs/work/inbox` and none in a `capabilities.yaml` sidecar. The two plan files the
request cites as kind-1 examples are down to one: the sort-and-limit item's
`plan.md` no longer matches, while the timestamp item's `plan.md:246-250` still
does. Kind 2 has no instance in any `capabilities.yaml` sidecar; the only one is
prose, `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root/intake.md:97`,
telling the implementer to declare `skills/tcw-work` under `changed:`. The ledger
path is now `skills/work` (`docs/capabilities/skills/work/`).

## Goals

- Every old name that tells the reader where to go, what to edit or what to
  declare names the current skill, path or capability.
- Every old name that records what something was called, or quotes someone else,
  is unchanged.

## Non-goals

- A guard that stops this recurring (declined by the requester).
- Completed and discarded items, which are records.
- Names outside the rename's set (`tcw-plugin`, `tcw-report`, `tcw-config`,
  `tcw-cli`, item slugs that contain `tcw-…` as part of a longer word).
- Any other staleness in these files that the sweep notices.

## Design

The rule for each match, decided per file:

1. **Rewrite** a name that is an instruction: a path to edit or read, a document
   to follow, a capability path to declare, or a current-state description the
   next stage will act on (including dated audit notes written to steer that
   stage, and `plan.md` task lists).
2. **Leave** a name that is a record: a statement of what something used to be
   called or what became of it ("`skills/tcw-work`'s `cap-f533ba` became
   `skills/work`'s"), the names listed as removed, and text quoted verbatim from
   a third party (a `>`-quoted GitHub issue report).
3. **Wildcard and pattern forms count** (`tcw-commands-*`, `skills/tcw-work-stage-*/`),
   though the intake's expression cannot match them; they are found by a second
   search, `tcw-(commands|extras|work-stage)-(\*|<)`, and judged by rules 1-2.
   *Added at verification, where both the verifier and the reviewer found them.*
4. **An instruction whose target was deleted** under both names is left: there is
   no current name to point at. *Added at verification; the plan had applied it
   without the spec saying so.*
5. **`intake.md` beside an `initial-request.md` is a record** — a verbatim copy of
   the inbox entry, superseded for every later stage — and is left alone. Where
   `intake.md` is an item's only body it is read like `initial-request.md`, rules 1-4
   applying line by line.

Matching is on whole names only, with the intake's regular expression; a rewrite
changes the skill name and nothing else in the line, except for grammar the new
name forces (for example "the `setup` skill").

The per-file verdicts are the plan's task list.

## Acceptance criteria

1. Re-running the intake's `git grep` (extended to `docs/work/inbox`) outside this
   item's own folder returns only lines the plan lists as "leave", each with its
   reason; the wildcard search in rule 3 returns only removed names that rule 2
   keeps.
2. `git diff --stat` for the implementation touches only files under
   `docs/work/backlog/` (and `docs/work/inbox/` if a match is there), and no
   `intake.md` whose folder also holds an `initial-request.md`.
3. `git diff -U0` contains no removed line whose only change is to `tcw-config`,
   `tcw-cli` or an item slug.
4. `tcw validate` passes after the change.

## Risks

- The judgment is per line and can be wrong in either direction; the plan lists
  every verdict so a reviewer can check it without re-deriving it.
- Items change while this runs; the grep is re-run immediately before
  implementing.
