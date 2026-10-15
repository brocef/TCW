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

Use bare slugs for other items, never links of the form `tcw://`: `tcw validate`
reports every such link that resolves to nothing, and a handoff stays in the
item after the work it describes has moved on.

With nothing unfinished and nothing held only in your head, there is nothing to
hand off: say so in the report instead of writing one.
