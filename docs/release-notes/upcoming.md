# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## TCW now works from inside a git worktree

If your project registers a parent or a child in `tcw-config.yaml` using a
relative path, and you checked the project out into a git worktree, nothing
worked. Not `tcw work list`, not `tcw validate`, not even commands that only
read:

```
tcw: .../example-server/.worktrees/tcw-config.yaml: registered target has no tcw-config.yaml
```

The path in your config was written from where the project normally sits. A
worktree puts it somewhere else, so the path pointed at a directory that isn't
there. TCW now works out where the path was written from and follows it to the
right place. All of it works from a worktree now, and you get the same project
graph you'd get from the normal checkout.

The project you're working on is still the **worktree** — your work items,
capabilities and taxonomy are the ones you have checked out, and a new item
lands there, not in the other copy.

If you keep several projects inside one repository, that keeps working exactly
as before: a project sitting next to yours in the same checkout is still the
copy on your branch, not the one on the main checkout's branch. And if your
project isn't in a git repository at all, nothing about it changes.

## Completing a worktree item from inside that worktree now refuses

`tcw work complete` on an item you started with `--worktree` used to report
success when run from inside the worktree — while doing nothing. The branch was
never merged into your main checkout and the worktree was never removed. Nothing
was lost, but you were told the item was finished when it wasn't.

It now refuses and tells you where to run it:

```
tcw work complete: my-item cannot be completed from inside its own worktree —
the merge-back and teardown act on the primary checkout. Re-run from /path/to/project.
```

Running it from the main checkout is unchanged. So is completing from some other
worktree that isn't the item's own.

## Commands that move a work item now tell you where it went

Starting, completing, accepting, or creating an item moves it into a different
folder, and until now nothing said which one — so it was easy to go looking for
a started item where it used to be instead of where it now is.

Those four commands now name the item's new home, as a path relative to the
project root:

- `tcw work start my-item` → `started my-item → docs/work/active/my-item`
- `tcw work complete my-item …` → `completed my-item (done) → docs/work/completed/my-item`
- `tcw work inbox accept request.md` → `→ now at docs/work/backlog/my-item`
- `tcw work new "My item"` → `→ created at docs/work/backlog/my-item`

`inbox accept` and `new` still print just the item's name on their normal
output, so anything scripted around them keeps working — the location goes to
the side channel, alongside the hints they already print. Starting with
`--worktree` still reports the worktree, now with the folder as well. Nothing
else about these commands changed.

## `tcw taxonomy list` no longer shows terms under the wrong parent

If one of your top-level terms was a longer version of another — a feature named
`Event Reporting` sitting alongside a term named `Event` — the listing put it
between `Event` and `Event`'s children, and indented those children underneath
it. They looked like they belonged to `Event Reporting`. They never did.

Before, and after:

```
event  [V] (local)                    event  [V] (local)
event-reporting  [F] (local)            log-batch  [V] (local)
  log-batch  [V] (local)                stat  [V] (local)
  stat  [V] (local)                   event-reporting  [F] (local)
```

Only the listing was wrong — the stored taxonomy was always correct, which is
why `tcw taxonomy check` never complained. Naming a feature after the term it
operates on is a pattern TCW actively encourages, so this was easy to hit; TCW's
own taxonomy had it. Terms inherited from another project are still listed after
your own, now grouped by the project they come from.

## Epic summaries now list the capabilities an item declares

When you ran `tcw work reconcile` on an epic, its **Capability deltas** section
would say a child item's capability file was "present but not a list — skipped",
even when the file was written exactly as documented and every other command
accepted it. The summary was reading an older format; the file was fine.

It now lists what each item actually declares:

```
**Capability deltas:**
- child-a/2026-01-01-slice: new billing/download-invoice
- child-a/2026-01-01-slice: changed auth/delete-account
```

If a capability file genuinely cannot be read, the summary now says so and names
the problem, instead of describing it as the wrong shape — and one unreadable
file no longer stops the rest of the summary from being produced.

## Adding a feature now checks its `--vocab` links straight away

`tcw taxonomy add … --kind feature --vocab <ref>` used to accept whatever you
gave it. A misspelled term, a term that didn't exist yet, or a ref that pointed
at another feature was written into the entry and reported back as success — you
only found out at the next `tcw taxonomy check`, possibly hundreds of entries
later.

It now checks the link as you add it, and refuses the entry rather than storing
a broken one:

```
$ tcw taxonomy add "Search" --kind feature --vocab quesry
tcw taxonomy add: vocabulary ref 'quesry' does not resolve
```

The same applies to a feature added with no `--vocab` at all, and to one whose
ref names a feature where a vocabulary term belongs. Nothing is written when the
command refuses — no half-created folder to clean up.

**This is a behavior change worth knowing about if you script TCW.** A bootstrap
that piped a batch of `add` commands and only checked at the end used to run to
completion and report the problems afterwards; it now stops at the first bad
ref. The practical consequence: **add your vocabulary before the features that
name it.**

## `--vocab` accepts a term's short name when it's unambiguous

If you have exactly one term whose last path segment is `invoice`, you can now
write `--vocab invoice` instead of `--vocab billing/invoice`. TCW stores the full
path for you, so the entry reads the same as if you had typed it out.

If two terms share that last segment, it tells you which ones and asks you to
pick:

```
$ tcw taxonomy add "Search" --kind feature --vocab zeta
tcw taxonomy add: vocabulary ref 'zeta' is ambiguous: alpha/zeta, beta/zeta
```

This shorthand is for `--vocab` only. `tcw taxonomy show` and `tcw taxonomy rm`
still want the full path — which is exactly why what gets stored is the path.

## Taxonomy paths can no longer reach outside your taxonomy

`tcw taxonomy rm ../capabilities/thing/do-it` used to do what it says: delete
`docs/capabilities/thing/` — a folder that is not a term and not part of your
taxonomy at all. `tcw taxonomy show` would likewise read files from anywhere
under your project. The local web app reached the same code with whatever a
request contained.

A taxonomy path now addresses a term inside `docs/taxonomy/` and nothing else.
One that tries to climb out simply matches no term:

```
$ tcw taxonomy rm ../capabilities/thing/do-it
tcw taxonomy rm: no such term: ../capabilities/thing/do-it
```

If a ref like that is already sitting in one of your entries, `tcw taxonomy
check` reports it as a dangling ref, the same as any other ref that goes
nowhere.
