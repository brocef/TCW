# Spec — Ask every new work item to say why it is worth doing

## Capability changes

None. This is project configuration and text; TCW's behavior is unchanged.

## Problem

This project's `create-work` procedure is TCW's built-in text alone:
`tcw-config.yaml` has no `work.procedures` entry. The body that text asks for
(`tcw work new`'s intake) has three parts:

- the idea;
- `## Origin`;
- `## References`.

Nothing asks the writer to argue for the work. The user wants every new item
to justify itself: the impact of not doing it, the benefit of doing it, and
similar points.

## Goals

1. `tcw work procedure prompt create-work` prints TCW's text unchanged,
   followed by this project's instruction.
2. That instruction requires a `## Why` section in every item or raw inbox
   entry the procedure creates, placed after the idea and before
   `## Origin`. The section covers:
   - **without it:** what happens if nobody does the work;
   - **with it:** what gets better, and for whom;
   - **cost and risk:** roughly how big the change is, and what it could
     break;
   - **alternatives,** when there are any.
3. The instruction says to write only what the writer has evidence for, and
   to write "unknown" rather than invent a benefit. It says what each run
   mode does when the writer cannot answer "without it".
4. Appending to an existing item touches its `## Why` only when the new
   information changes the case for doing the work.

## Non-goals

- **Checking for the section in `tcw validate` or a gate.** This is text
  guidance only.
- **Changing TCW's built-in `create-work` text.** Other projects keep it as
  it is.
- **Asking the `request` or `spec` stages to carry the section forward.**
  The spec's Problem section already argues the case.

## Design

- Add `work.procedures.create-work` to `tcw-config.yaml` with two bindings:
  `builtin: true`, then `file: docs/procedures/create-work.md`.
- Write the instruction in that file.

## Acceptance criteria

1. `tcw validate` passes.
2. `tcw work procedure prompt create-work` prints the built-in text first
   and the new section last.
3. The printed text covers Goals 2 to 4.

## Risks

- Intake notes get longer. That is the point, and the "unknown" rule keeps
  the section from being padded.
