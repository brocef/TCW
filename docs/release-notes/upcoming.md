# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Work items can now sit in review

There is a new status between "being worked on" and "done": **review**. It means
the work is implemented and is waiting for someone to accept it.

```sh
tcw work submit my-item     # active → review
tcw work rework my-item     # review → active, if it didn't pass
```

An item in review is **not finished**. It still blocks anything that depends on
it, and it still keeps its epic open — because a review can reject the work and
send it back. `rework` is the only way to move backwards; nothing ever comes
back out of completed or discarded.

**Review is optional.** A small change can go straight from active to completed
exactly as before. `tcw work complete` will print a one-line note that the
review step was skipped and then complete normally — it does not ask you to
confirm anything extra, and it does not fail.

### One rule worth knowing

If a review rejected the work, `tcw work rework` will refuse while
`refined-outcome.md` is still there. That document says the work was checked and
accepted, which is no longer true. Delete it — and write down what still needs
doing in `rework.md` — and the command will go through. TCW deliberately does
not delete the file for you.

## Record the pull request on a work item

```sh
tcw work edit my-item --pr https://github.com/you/repo/pull/42
```

Shown by `tcw work show`. Nothing depends on it yet; it is there so an item can
carry the link to the branch or PR its code lives on.

## Upgrading

**Existing projects need no migration.** Nothing changes status, and no files
are rewritten. Your projects were set up with four status folders; the `review`
folder is created the first time something moves into it.

**One thing to check: you can no longer name a project `review`.** Project IDs
can't collide with a status name, and `review` is now a status. If you have a
project using that ID, rename it before upgrading — otherwise `tcw validate`
will report the collision.

## Smaller things

- The "phase" field is gone. It was displayed on `tcw work show` and in epic
  rollup tables, but nothing ever set it, so it was always blank. Existing items
  are unaffected.
- Items in review appear on the board directly under active work.
