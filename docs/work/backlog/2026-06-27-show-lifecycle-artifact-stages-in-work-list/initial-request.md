# Initial request — Show lifecycle artifact stages in work list

## Requested outcome

When listing work items, print which lifecycle stages have been completed. The
current list output prints `phase` after status, but that field usually appears
as `-`. Replace or repurpose that visible position with a compact artifact-stage
string derived from lifecycle documents.

## Desired display

Use compact letters such as:

- `R` = `initial-request.md` exists and is nonempty.
- `S` = `spec.md` exists and is nonempty.
- `P` = `plan.md` exists and is nonempty.
- `O` = `outcome.md` exists and is nonempty.

Example:

```
some-slug | backlog | RS | 12 | Title of work item
```

`RSP` means request, spec, and plan documents exist and are nonempty.

## Constraints and non-goals

- Keep output compact and scannable.
- Prefer deriving state from bounded lifecycle artifact names rather than adding
  a new open-ended status field.
- Avoid making filesystem-only assumptions part of the abstract store interface
  unless they have a clear abstract analog.
- Planning should stop before implementation; do not run `tcw work start` yet.

## Decisions already made

- The work list row already has a position after status; this is the likely home
  for the stage string.
- The old `phase` field is not useful in normal output because it commonly
  prints `-`.
