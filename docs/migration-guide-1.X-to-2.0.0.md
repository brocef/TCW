# Migrating from 1.x to 2.0.0

Version 2.0.0 has **exactly one break**: `tcw work stage` is now two commands
instead of one. Nothing about your `tcw-config.yaml`, your work items, or your
store changes. If you never type `tcw work stage` and never wrote it into an
agent guide or a script, there is nothing to do.

**One thing to check if you bound hooks to the `inbox` stage.** Those bindings
were unreachable in 1.x, because the stage verb refused `inbox` outright, so a
`pre:` binding there had never run. `tcw work stage gate inbox` now runs it. If
you wrote one expecting it to be inert, it no longer is. A conditioned one still
cannot fire — there is no item to condition on at the inbox stage — and
`tcw work stage gate inbox --no-exec` now names those rather than omitting them.

## The break: `tcw work stage <id> <slug>` is now two verbs

`tcw work stage` used to answer two different questions with one command: *may
this item enter this stage* (a gate) and *what does this stage ask for* (the
instructions). You could not ask the second without paying for the first — on a
project with a `pre:` check bound to a stage, asking what that stage involves ran
the check, the check refused because its input was not written yet, and you were
told nothing at all.

The two questions are now two verbs, and each does one job.

| Verb | Answers | stdout |
| --- | --- | --- |
| `tcw work stage gate <id> <ref>` | may this run? status legality, then the stage's `pre` bindings | **nothing** |
| `tcw work stage prompt <id> [<ref>]` | what does it ask for? the instructions | the instructions |

**Your old call becomes both, in that order:**

```sh
# 1.x
tcw work stage spec my-item

# 2.0.0
tcw work stage gate spec my-item && tcw work stage prompt spec my-item
```

If all you ever did with the output was read it, `prompt` alone is what you want.
If you were relying on the refusal — a CI step, a hook, a script that checks an
item is ready — `gate` alone is what you want, and its exit code is now the whole
answer.

| Before | After |
| --- | --- |
| `tcw work stage spec my-item` | `tcw work stage prompt spec my-item` (to read) · `tcw work stage gate spec my-item` (to check) |
| *(nothing — `inbox` had no working 1.x spelling)* | `tcw work stage prompt inbox` · `tcw work stage gate inbox` |
| `tcw work stage plan my-item --no-exec` | `tcw work stage gate plan my-item --no-exec` · `tcw work stage prompt plan my-item --no-exec` |

The `inbox` row has no "Before": in 1.x the slug was a required positional, so
`tcw work stage inbox` was an argparse usage error and the form *with* a slug was
refused by the stage handler. There is no 1.x call to search for and migrate —
the row is there because the instructions are new, not because the command moved.

The old form is not accepted and does not silently do anything. It reports both
commands and exits 2:

```
$ tcw work stage spec my-item
tcw work stage: 'spec' is not a subcommand; run `tcw work stage gate spec my-item`
to check the stage and run its checks, or `tcw work stage prompt spec my-item` for
its instructions
```

**Check for it:**

```sh
grep -rn 'tcw work stage \(inbox\|request\|spec\|plan\|implement\|verify\|postmortem\)' .
```

Everything that matches and is not already followed by `gate` or `prompt` needs a
verb inserted. In practice that is your agent guide (`AGENTS.md` or `CLAUDE.md`),
any slash commands or skills you wrote, CI steps, and any `pre:` or `post:` hook
script that shells out to `tcw`.

## What each verb does that the other does not

**`gate` prints no instructions at all.** Success is exit 0 with empty stdout and
one line on stderr naming `prompt`. If you pipe it expecting text, you get
nothing — that is the contract, not a failure. It runs no transition, writes no
artifact, and changes no field; the exit code is the answer.

**`prompt` runs no check at all.** No status legality, no `pre` bindings. That is
what makes it answerable for a stage the item is not ready for, which is exactly
when you want to ask. It still resolves `file:` and `generate:` bindings, because
that is how the text is produced: the guarantee is that TCW runs no check of its
own, not that no process starts.

The work item reference is optional on `prompt` and changes what resolves:

- **Without one**, `when:` conditions never match, a `generate:` hook receives a
  null item, and the body token falls back to its no-body text.
- **With one**, all three resolve against that item — and a
  `<project-id>/<slug>` qualifier reads *that* node's configuration, not the one
  you are standing in.

If the stage is not legal for the item, `prompt` prints the instructions anyway
and says so on **stderr**, leaving stdout carrying the instructions alone and the
exit code 0.

`--no-exec` is on both and each reports only its own half: `gate` lists the `pre`
checks it would run, `prompt` lists the bindings it would resolve and marks the
ones a `when:` condition skipped. Neither prints anything on stdout under the
flag, so a dry run can never be mistaken for the instructions.

## What is new in the text itself

Because `prompt` gates nothing, **what it prints now says so.** Every resolved
prompt is wrapped in two generated sections:

- a line at the top naming the `gate` command for that stage, so a reader who
  arrived at the instructions without running it is told;
- a closing section saying what to do once the stage's output is written — the
  next stage, or the transition that has to happen first.

Your own `prompt:` bindings are wrapped too. Overriding what a stage *says* is
not overriding where the lifecycle goes next. A stage that resolves to **nothing**
stays silent and is not wrapped — a header and footer around an empty middle
would read as a stage that failed to resolve.

**Silencing a stage now works the way it always read.** `prompt: [{blob: ""}]`
means "this stage says nothing": the stage resolves to nothing, prints nothing,
and gets no bookend. In 1.x that spelling was refused as a blank string even
though four separate documents described it as the way — so if you tried it and
gave up, try it again. An empty list is still refused, and for the unchanged
reason: after parsing it cannot be told apart from never writing the key.

**If you have a byte-comparison against stage output, it will move.** That is the
only place this release changes text rather than commands.

## What you don't have to do

- **Nothing to your configuration.** The `pre:` and `prompt:` keys under
  `work.lifecycle.stages` are unchanged, and are what the two verbs are named
  after.
- **Nothing to your work items, store, or history.** No data migration, no
  reconcile, no re-init.
- **Nothing about `tcw work scaffold`, the transition verbs, or any other
  command.** They are untouched.
