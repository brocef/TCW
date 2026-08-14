# Spec — Add the stage-entry verb

Child **C4**. The initiative's `spec.md` decides the boundaries; this decides how
C4 is built.

## Problem

C3 made a node's own stage instructions expressible and resolvable. Nothing
invokes the resolver. `tcw work lifecycle` deliberately does not — it is inert by
criterion, and resolving would mean running `generate` scripts during a command
whose whole contract is that it runs nothing.

So the instructions exist and are unreachable.

## Goals

1. One command that turns "I am at stage X on item Y" into the text to follow.
2. It is safe to run for its instructions alone: it writes nothing.
3. stdout is the prompt, so it composes with a pipe.
4. `--no-exec` shows what would run without running it.

## Non-goals

- Writing anything. `tcw work scaffold` is C5's and is the only writing verb.
- Executing stage bindings that are not checks. A `prompt` binding resolves; it
  does not run except as `generate`, which C3 owns.
- Changing status. Stage entry is not a transition; the two ladders stay
  separate.
- The built-in prompt *content*. C6's.

## Design

### The order of operations

`tcw work stage <id> [ref]`:

1. **Resolve the id.** Unknown stage → exit 1 naming the legal ids. `inbox` →
   exit 1 naming the reason (it runs before an item exists).
2. **Resolve the item.** Missing or ambiguous → exit 1, as every other verb.
3. **Check stage/status legality.** Illegal → exit 1, **before any check, any
   generator, and any read**.
4. **Run the stage's `pre` checks**, condition-filtered through C3's `select`.
   Non-zero exit → exit 1; nothing further runs. `[gated]`
5. **Resolve the prompt bindings.**
6. **Print the text on stdout.**

Every failure exits non-zero with **nothing on stdout**. An agent piping this
gets empty input rather than a fragment, which is the same rule
`tcw work show --json` follows.

### Stage/status legality

A table beside `LIFECYCLE_STEPS` in `base.py`, because it is contract data about
the lifecycle rather than machinery belonging to a verb:

```python
STAGE_STATUSES: dict[str, tuple[str, ...]] = {
    "inbox":      (),                       # no item exists yet
    "request":    ("backlog",),
    "spec":       ("backlog",),
    "plan":       ("backlog",),
    "implement":  ("active",),
    "verify":     ("review", "active"),
    "postmortem": ("review", "completed", "discarded"),
}
```

`verify` includes `active` because `complete` is legal directly from `active`
(`base.py:455`), so an item can be verified without having been submitted.
`postmortem` is out-of-band and terminal: legal in `review` and after completion,
never changing status.

**The initiative assigns this table to C5, with C4 consuming it.** C4 and C5 are
parallel and C4 landed first, so C4 defines it and C5 consumes. Recorded as a
deviation rather than done quietly; the table's *location* is the part worth
agreeing on, and `base.py` beside the steps it describes is where a second
consumer will look for it.

### Streams

- **stdout**: the resolved prompt text, and nothing else. Printed once, at the
  end, after everything that could fail has succeeded.
- **stderr**: every check's stdout and stderr (C3's `run_bindings` already does
  this), every error message, and `--no-exec`'s plan.

The plan goes to **stderr**, deliberately: `--no-exec` is a diagnostic, and a
caller piping stdout should get an empty prompt when nothing was executed rather
than a plan they might mistake for one.

### `--no-exec`

Passes `execute=False` to C3's resolver and skips the `pre` checks entirely — the
flag means "run nothing", and a check is the most obviously running thing there
is. It prints, to stderr:

- each `pre` check that would run, in order, after condition filtering;
- each prompt binding, its kind, whether its condition matched, and for a
  `generate` the exact command line.

stdout still receives the text that resolved without executing — the `blob` and
`builtin` parts — because that is genuinely what the command would print from the
sources that do not run. `file` and `generate` contribute nothing, which the plan
says.

### What "writes nothing" means, and how it is checked

Not "does not call `write_artifact`" — **the item's folder is byte-identical
before and after**, compared as a manifest of names, sizes, and contents. That is
the property; anything narrower is a check on the mechanism the implementer had
in mind.

The one thing that legitimately changes state is a `generate` script the node
configured, which is the node's own code doing what the node told it to. The
check therefore uses a stage with no generators, and a separate assertion covers
the generator case: with `--no-exec`, even that does not run.

## Acceptance criteria

The initiative's criteria 8, 9, and 16 are the requirement.

1. **stdout is only prompt text.** With a stage whose `pre` check prints to both
   its stdout and its stderr, `tcw work stage`'s stdout is exactly the resolved
   prompt and both check streams are on stderr.
2. **Running it writes nothing**, for **every** stage legal on the item, verified
   by comparing a manifest of the item folder — names, sizes, and bytes — before
   and after. Not by asserting a method was not called.
3. **A failing `pre` check exits non-zero with no prompt resolved**: stdout is
   empty, and a `generate` prompt binding on the same stage did not run
   (sentinel).
4. **An illegal status exits non-zero before anything runs**: `implement` from
   `backlog` and `spec` on a completed item, each with a sentinel-writing `pre`
   check and a sentinel-writing `generate` prompt, leave no sentinel.
5. **`postmortem` is legal in `review` and after completion**, and `verify` is
   legal from `active` as well as `review` — asserted, because both are the
   non-obvious rows and a table written from the happy path gets them wrong.
6. **`tcw work stage inbox` is rejected naming the reason**, rather than printing
   nothing — silence would read as "no instructions configured".
7. **`--no-exec` executes nothing**: a `pre` check and a `generate` prompt that
   each write a sentinel leave no sentinel, and the plan on stderr names both.
8. **`--no-exec` still prints what resolved without running** — the `blob` part
   on stdout — so the flag is a dry run rather than a no-op.
9. **Every error path leaves stdout empty and exits non-zero**: unknown stage,
   unknown item, ambiguous item, illegal status, failing check, and a failing
   generator.
10. **A qualified descendant ref** resolves against the owning node's policy, as
    every other work verb does.

## Risks

- **The legality table is a second source of truth about the lifecycle.**
  `LIFECYCLE_STEPS` already describes each stage; this adds where each is legal.
  Keeping them adjacent is the mitigation, and a test asserts the table's key set
  equals `STAGE_IDS` so a new stage cannot be added without deciding.
- **`--no-exec` printing partial text to stdout could be mistaken for the real
  prompt.** The plan on stderr says what was skipped. The alternative — printing
  nothing — makes the flag useless for its actual purpose, which is reading an
  unfamiliar repository.
- **Stage entry running `pre` checks makes it not-quite-free.** A check is
  configured shell, so `tcw work stage` runs node code by design. `--no-exec` is
  the escape, and the README says so.
