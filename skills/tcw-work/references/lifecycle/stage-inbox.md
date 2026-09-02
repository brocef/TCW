# Stage: inbox

## Purpose

Turning a raw drop into a tracked item.
Get your instructions on how to produce the output by running
`tcw work stage begin inbox` — no work item reference, because none exists yet.

A **GitHub issue is the same shape from a different source**: someone else's raw
text, accepted or rejected. The `tcw-triage-issues` skill sweeps a project's open
issues and reuses this stage's judgment for the ones it accepts; what it adds is
GitHub-specific — reaching the issues, and replying to the reporter.

## Inputs

The raw inbox entry. No lifecycle artifact precedes it: this is the stage that
runs first, and the entry is the only thing to read.

## Produce

**No lifecycle artifact.** This stage creates the _item_, and `tcw work inbox
accept` preserves the entry as its `intake.md` rather than writing a request.
An accepted item therefore shows `i` and not `R` in `tcw work list`.

## Steps

1. **Not delegable.** The stage is interactive — deciding what an entry means
   and how to title it is judgment the coordinating session holds. See
   [`delegation.md`](../procedures/delegation.md). — agent `[judgment]`
2. `tcw work inbox accept <entry>` is `[gated]` rather than advice: it consumes
   the entry, creates the item, and refuses one that does not exist. Everything
   the prompt says about titling governs the `--title` you pass it. — agent
   `[gated]`
3. An entry that turns out to be one change with several parts becomes a single
   item; [`decompose.md`](../procedures/decompose.md) is what splits it later,
   at planning time rather than here. — agent `[judgment]`
