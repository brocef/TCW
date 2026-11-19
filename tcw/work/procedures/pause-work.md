## Reach a coherent resting point

Finish the edit in hand or back it out; start nothing new. Coherent means the
files parse and the change makes sense to a reader. It does not mean the work
is complete or the tests pass: reaching for passing tests is how a pause takes
ten minutes while the user is already gone.

## What a handoff holds

Write whatever an agent would need to resume the work you were doing, for a
reader with no memory of this session, who may be on another machine with
nothing but a fresh copy of the project. You have been working the item; you
know what mattered. At least:

- the stage the item is at, and how far through it you got;
- where the unfinished work is, so someone else can find it;
- what you were about to do next, and why;
- anything you learned that is not yet written in the item's documents, such
  as a test that fails and what you think the cause is;
- what you decided and what is still open.

Name other items by their full identifier, `<project>.work/<id-path>` (the
owning project's ID, then the item's folder path in its work store), written as
plain text, never as a link of the form `tcw://`: `tcw validate` reports every
such link that resolves to nothing as an error, and a handoff stays in the item
after the work it describes has moved on.

## Where a handoff goes

Keep each handoff where a fresh session, possibly on another machine, can find
it. Where the project's instructions or the user's say where, do that;
otherwise judge from the project and how its work is kept. TCW offers these
places, by the stage the item is at:

- **The stage has a folder:** the file `tcw work path <slug> <stage> --handoff`
  prints. Never compose the path; each call names a new file, and the newest
  one is what resuming reads. A file on this disk reaches another machine
  only once it is saved somewhere that machine can fetch it from: do that
  the way the project shares its files, where the project's practice and the
  user's instructions allow it, and otherwise say that the handoff is on this
  machine only.
- **The backend keeps the stage** (`tcw work path` exits 3 for it; in Jira,
  request and qa): a comment posted with `tcw work comment <slug>`, the text
  on stdin, whose first line is `Handoff`.
- **The item is at inbox, or there is no item:** write nothing. What resuming
  needs goes in the report instead.

Handoffs are never deleted: a later one supersedes an earlier one by being
newer.

With nothing unfinished and nothing held only in your head, there is nothing to
hand off: say so in the report instead of writing one.
