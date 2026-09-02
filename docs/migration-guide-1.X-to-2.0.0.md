# Migrating from 1.x to 2.0.0

Version 2.0.0 has **exactly one break**, and it is a rename you can apply with a
search and replace. Nothing about your `tcw-config.yaml`, your work items, your
store, or your hooks changes. If you never type `tcw work stage` and never wrote
it into an agent guide or a script, there is nothing to do.

## The one break: `tcw work stage <id> <slug>` is now `tcw work stage begin`

`tcw work stage` used to answer two different questions with one command: *may
this item enter this stage* (a gate) and *what does this stage ask for* (the
instructions). You could not ask the second without paying for the first — on a
project with a `pre:` check bound to a stage, asking what that stage involves ran
the check and then refused, printing nothing.

The two questions are now two verbs.

| Before | After |
| --- | --- |
| `tcw work stage spec my-item` | `tcw work stage begin spec my-item` |
| `tcw work stage inbox` | `tcw work stage begin inbox` |
| `tcw work stage plan my-item --no-exec` | `tcw work stage begin plan my-item --no-exec` |

`begin` behaves **exactly** as `tcw work stage` did in 1.x — same order, same
gates, same output, same exit codes. The rename is the whole change.

The old form is not accepted, and does not silently do anything. It reports the
command to run instead and exits 2:

```
$ tcw work stage spec my-item
tcw work stage: 'spec' is not a subcommand; run `tcw work stage begin spec my-item`
to enter the stage, or `tcw work stage prompt spec` to read its instructions
without entering it
```

**Check for it:**

```sh
grep -rn 'tcw work stage \(inbox\|request\|spec\|plan\|implement\|verify\|postmortem\)' .
```

Everything that matches and is not already followed by `begin` or `prompt` needs
the verb inserted. In practice that is your agent guide (`AGENTS.md` or
`CLAUDE.md`), any slash commands or skills you wrote, CI steps, and any `pre:`
or `post:` hook script that shells out to `tcw`.

## What's new, and optional

**`tcw work stage prompt <id> [<slug>]`** prints a stage's instructions without
entering the stage. It runs **no** legality check and **no** `pre` bindings, so
it answers "what does this stage ask for?" on an item the stage is not legal for
— which is the case `begin` correctly refuses.

```sh
tcw work stage prompt plan               # what does the plan stage ask for?
tcw work stage prompt plan my-item       # the same, resolved for that item
```

The work item is optional and changes what the item-dependent parts resolve to:

- **Without one**, `when:` conditions never match, a `generate:` hook receives a
  null item, and the body token falls back to its no-body text. You get the
  stage's generic instructions.
- **With one**, conditions match against that item's tags, `generate:` receives
  the real item, and the body resolves — and a `<project-id>/<slug>` qualifier
  reads *that* node's configuration, not the one you are standing in.

It still resolves `file:` and `generate:` bindings, because that is how the text
is produced at all. The guarantee is that TCW runs no check of its own, not that
no process starts: a `generate:` script's own side effects remain that script's
business.

If the stage is not legal for the item's status, `prompt` prints the
instructions anyway and says so on **stderr**, leaving stdout carrying the
instructions alone and the exit code 0. Worth knowing, because the built-in
instructions for `verify` and `implement` name state-changing commands
(`tcw work submit`, `tcw work complete`, `tcw work start`) — reading them for an
item that is not ready is fine, following them is not.

## What you don't have to do

- **Nothing to your configuration.** The `pre:` and `prompt:` keys under
  `work.lifecycle.stages` are unchanged, and are what the two new verbs are
  named after.
- **Nothing to your work items, store, or history.** No data migration, no
  reconcile, no re-init.
- **Nothing to adopt `prompt`.** It is an addition. Not using it costs you
  nothing you had.
- **Nothing about `tcw work scaffold`, the transition verbs, or any other
  command.** They are untouched.
