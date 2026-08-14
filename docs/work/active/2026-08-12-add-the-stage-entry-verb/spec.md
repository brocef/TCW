# Spec — Add the stage-entry verb

Child **C4**. The initiative's `spec.md` decides the boundaries; this decides how
C4 is built.

> Revised after adversarial review by `codex` and `bllm-review`. One row of the
> legality table was wrong, one ordering requirement was impossible as written,
> one acceptance criterion tested a filesystem where the property is abstract,
> and the capability delta was missing entirely. See `## Review corrections`.

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
3. **Check stage/status legality.** Illegal → exit 1, **before any hook runs** —
   no check, no generator, no prompt-file read. Not "before any read": deciding
   legality *requires* reading the item, since its status is what is being
   judged. The epic's own wording is the implementable one.
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
    "postmortem": ("review", "completed"),
}
```

`verify` includes `active` because `complete` moves from `review | active`, so an
item can be verified without having been submitted.

**`postmortem` does not include `discarded`.** The first draft had it, and the
lifecycle contract does not: `postmortem`'s own objective says "legal in review
or after completion", and `completed` means *shipped* while `discarded` means
*closed without shipping* — two deliberately distinct terminal outcomes. A
post-mortem on work nobody did is not the out-of-band review this stage is.

**The table's ownership is settled by amending the epic, not by a note here.**
The initiative assigned it to C5 with C4 consuming. C4 is the one that cannot
function without it — criterion 9 of the epic is C4's — so the epic's spec is
amended in the same commit as this one to assign it to C4, with C5 consuming.
Recording a "deviation" inside a child while the epic says otherwise is how a
spec stops being the source of truth; this is the third such amendment and each
one is in the epic.

### Streams

- **stdout**: the resolved prompt text, and nothing else. Printed once, at the
  end, after everything that could fail has succeeded.
- **stderr**: every check's stdout and stderr (C3's `run_bindings` already does
  this), every error message, and `--no-exec`'s plan.

The plan goes to **stderr**, deliberately: `--no-exec` is a diagnostic, and a
caller piping stdout should get an empty prompt when nothing was executed rather
than a plan they might mistake for one.

### `--no-exec`, and how it refines the epic

The epic says `--no-exec` "resolves and prints what *would* run — every command,
every `generate` script — and executes nothing". Two refinements, recorded
because the difference is visible to a user:

- **`pre` checks are skipped**, not resolved-then-skipped. A check is the most
  obviously running thing there is, and "executes nothing" has to include it.
- **`file:` bindings are not read either.** C3's resolver refuses to
  (`resolve.py`, the `execute=False` branch), because a file read is observable
  and "what would happen" must not make any of it happen. So `--no-exec` shows
  you the *shape* of an unfamiliar lifecycle — every source, in order, with each
  generator's exact command line — rather than its full text.

It passes `execute=False` to C3's resolver and prints, to stderr:

- each `pre` check that would run, in order, after condition filtering;
- each prompt binding, its kind, whether its condition matched, and for a
  `generate` the exact command line.

stdout still receives the text that resolved without executing — the `blob` and
`builtin` parts — because that is genuinely what the command would print from the
sources that do not run. `file` and `generate` contribute nothing, which the plan
says.

### What "writes nothing" means, and how it is checked

**Two assertions, because the property is abstract and the fixture is not.**

The portable one: stage entry calls **no mutating method on `WorkStore`**. That
is the property a Jira-backed adapter would have to honour, and it is what stops
an implementation from calling an abstract mutator that happens to be a no-op on
the filesystem.

The adapter one: **the item's folder is byte-identical before and after**, as a
manifest of names, sizes, and contents. That catches anything that writes without
going through the store at all.

The first draft had only the second, which review correctly called a filesystem
test for an abstract property.

The one thing that legitimately changes state is a `generate` script the node
configured — the node's own code doing what the node told it to. The checks
therefore use a stage with no generators, and a separate assertion covers the
generator case: with `--no-exec`, even that does not run.

## Acceptance criteria

The initiative's criteria 8, 9, and 16 are the requirement.

1. **stdout is only prompt text.** With a stage whose `pre` check prints to both
   its stdout and its stderr, `tcw work stage`'s stdout is exactly the resolved
   prompt and both check streams are on stderr.
2. **Running it writes nothing**, for **every** stage legal on the item, verified
   two ways: no mutating `WorkStore` method is called (the portable property),
   and the item folder is byte-identical before and after (the adapter one).
3. **A failing `pre` check exits non-zero with no prompt resolved**: stdout is
   empty, and a `generate` prompt binding on the same stage did not run
   (sentinel).
4. **The legality table is asserted exhaustively, both ways.** Its key set equals
   `STAGE_IDS`; every value is a subset of `WORK_STATUSES`; every row equals its
   expected tuple exactly; and **every pair in the Cartesian product of
   `STAGE_IDS` × `WORK_STATUSES` that is not in the table is rejected** by the
   command. Special-casing the two illegal pairs someone thought to test is
   exactly what this closes.
5. **An illegal status exits non-zero before anything runs**: `implement` from
   `backlog` and `spec` on a completed item, each with a sentinel-writing `pre`
   check and a sentinel-writing `generate` prompt, leave no sentinel.
5b. **The non-obvious rows are asserted by name**: `verify` from `active` as well
    as `review`, `postmortem` in `review` and `completed`, and `postmortem`
    **rejected in `discarded`** — the row the first draft got wrong.
6. **`tcw work stage inbox` is rejected naming the reason**, rather than printing
   nothing — silence would read as "no instructions configured".
7. **`--no-exec` executes nothing**: a `pre` check and a `generate` prompt that
   each write a sentinel leave no sentinel, and the plan on stderr names both.
8. **`--no-exec` still prints what resolved without running** — the `blob` part
   on stdout — so the flag is a dry run rather than a no-op.
9. **Every error path leaves stdout empty and exits non-zero**: unknown stage,
   unknown item, ambiguous item, illegal status, failing check, and a failing
   generator.
10. **A qualified descendant ref** uses the descendant throughout, not just for
    its policy: a `generate` hook on the descendant observes the descendant's
    item slug, its `TCW_NODE_ROOT`, and its working directory. Asserting only
    that distinctive prompt text appeared would pass an implementation that
    resolved the right policy against the wrong item.
11. **The capability delta is declared and reconciled.** `work/run-a-lifecycle-stage`
    is **new**, declared in this item's `capabilities.yaml` and flipped by its
    completion gate. The epic assigns it here and C7 is consolidation-only, so
    nothing else will do it.
12. **A late failure still leaves stdout empty.** A stage whose first prompt
    binding resolves and whose second `generate` fails prints nothing on stdout —
    the text is buffered and emitted only after everything that could fail has
    succeeded.

## Review corrections

Findings checked against the code before being accepted.

**Accepted:**

- `postmortem` in `discarded` was wrong (codex). Verified at `base.py:717-723`
  and `440-444`: the stage says "review or after completion", and the two
  terminal statuses are deliberately distinct.
- Taking C5's table with a note was an unauthorized boundary change (codex). The
  **epic** is amended instead.
- "Before any read" is impossible — legality needs the item's status (codex).
  Reworded to the epic's own "before any hook runs".
- The capability delta was missing entirely (codex). C7 is consolidation-only
  and would not have flipped it. Criterion 11 added.
- AC2 tested a filesystem for an abstract property (codex). Now two assertions:
  no store mutator, plus FS byte-identity.
- AC4/AC5 admitted every untested illegal pair (codex). Now the full Cartesian
  product.
- AC10 would pass on the right policy against the wrong item (codex). Now the
  hook observes item, cwd, and environment.
- `--no-exec` skipping `file:` reads is a refinement of the epic's wording
  (codex). Recorded rather than left implicit.
- The legality table's *values* were unvalidated (bllm). Criterion 4 asserts
  every status exists.
- A late failure leaking stdout (bllm). Criterion 12.

**Rejected:**

- *No timeout or resource bound on checks and generators* (bllm). Both exist:
  `run_bindings` applies `policy.timeout`, and `run_generate` enforces the
  timeout and the output cap. C4 inherits them.
- *A malformed condition could fail at resolve time* (bllm). Conditions are
  parsed and validated at config load; `Condition.matches` is set operations on
  tuples and has no failure path.
- *Redact secrets from resolved prompts* (bllm). `tcw work show` prints the body
  today; no new boundary is crossed, and this is a serialization item's problem
  even less than it was C2's.

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
