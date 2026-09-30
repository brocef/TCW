# Spec — Say where a dated amendment to an item's request belongs

## Capability changes

- **changed:** `work/capture-raw-intake` — says where a later amendment goes:
  the request, never the intake.

## Problem

An amendment is anything that changes what an item asks for after the item was
written up: a decision made later, a clarification, a new constraint. Nothing
tells an agent where to put one. The one rule that exists contradicts the rest
of the documentation:

- `tcw/work/procedures/create-work.md` ("Append only what is new") appends new
  information under a dated `## Added <YYYY-MM-DD>` heading "to
  `initial-request.md` if it exists, otherwise `intake.md`".
- The `work` skill (`skills/work/references/commands.md`, "The body surface")
  and the guide (`docs/guide/work.md`, "Editing a body, and how it promotes an
  intake") say `intake.md` is raw input that is never quietly edited.

It is also incomplete. That rule lives only in the procedure for filing new
work, so an agent recording a decision against an existing item never meets
it. And appending to the request is not enough once the item has a spec:
`implement` reads the spec, plan and rework notes, and `verify` reads the spec
and outcome (`tcw/work/prompts/implement.md`, `verify.md`). Neither reads the
request, so an amendment recorded only there never reaches the work.

## Goals

1. One rule, stated identically wherever an agent looks: an amendment is
   appended to `initial-request.md` under `## Added <YYYY-MM-DD>` with its
   source, and nothing already there is rewritten.
2. An item with only `intake.md` gets its request written first, with the
   amendment folded in or under its own dated heading. The intake stays
   byte-identical.
3. Once a spec or plan exists, the amendment must reach the document that
   later stages read. In backlog or active, revise the spec (and the plan),
   or say in the appended section why neither changes. In review, record it
   in `rework.md` and send the item back.
4. Re-running the `request` stage on an item that already has dated `## Added`
   sections keeps them.
5. `create-work.md` stops sending item amendments to `intake.md`. Its clause
   for inbox entries, which become `intake.md` only when accepted, stays.

## Non-goals

- No `amendments.md` file and no `tcw work note` command. Both advisors judged
  that a new file every stage, prompt, the web app's document tabs and `show`
  would have to learn costs more than it gives, since `show` and the web app's
  request tab already display an appended section.
- No change to tracker sync. A ticket's description is written once, from the
  body, when the ticket is created (`_item_body` in `tcw/work/cli.py`), so an
  amendment does not reach an existing ticket. That is noted in the docs, not
  changed.
- No code change. The web app's body editor already promotes an intake-only
  item. It is not the request stage, so it is mentioned but not recommended
  for amendments.

## Design

The rule is one short paragraph, "Amending a request", placed:

- in `skills/work/references/commands.md` after "The body surface";
- in `docs/guide/work.md` next to "Editing a body, and how it promotes an
  intake";
- in `tcw/work/procedures/create-work.md`, which replaces its "otherwise
  `intake.md`" clause with a pointer to the rule (the inbox-entry clause stays);
- as one sentence in `skills/work/SKILL.md`, pointing to the paragraph;
- in `tcw/work/prompts/request.md`, the stage's own text: "If
  `initial-request.md` already exists, keep its `## Added` sections."

It also goes into the capability description `work/capture-raw-intake`.

Litmus: this changes documentation only. Any store holding a request document
can take an appended section.

## Acceptance criteria

1. `grep -rn "otherwise \`intake.md\`"` over `tcw/work/procedures/` finds
   nothing about item amendments; the inbox-entry clause remains.
2. The paragraph appears in `commands.md`, the guide and `create-work.md`
   and says the same four things: where (goal 1), intake-only items (goal 2),
   spec or plan present (goal 3), and that the ticket is not updated.
3. `skills/work/SKILL.md` names the file to use, in one sentence.
4. `tcw/work/prompts/request.md` tells a re-run to keep `## Added` sections.
5. `tcw validate`, `tcw capabilities check` and the documentation-surface tests
   pass; the full suite passes as CI runs it.

## Risks

- **Three copies of one rule can drift.** Mitigated by stating it in full in
  the work skill and the guide, and having the procedure point to it rather
  than restate every clause.

## Notes

- Advisors: Opus, and Sonnet in place of Codex (at its usage limit until
  2026-10-03). Both chose documentation only (option A), writing the request
  first on an intake-only item (A1), over a new file or a new command.
  - Opus added goal 3: implement and verify never read the request, which
    also covers active and review items. It cited `tcw/work/recursion.py`,
    which removed an earlier release's habit of writing a request nobody had
    written, as precedent against creating one mechanically.
  - Sonnet added goal 4.
