# Refined outcome — Give lifecycle hooks roles, kinds, and conditions

## The acceptance decision, stated accurately

**Closed on the requester's standing instruction to drive the whole initiative
through without stopping per slice, with verification deferred to the end.** Not
a per-item acceptance — the same decision that closed C1 and C2.

C3's implementation is complete and its criteria are met; its acceptance is
pending until the initiative is verified as a whole.

## Evidence at closure

1442 Python tests (baseline 1346), 52 web unit tests, `tcw validate` OK,
`tcw capabilities check` OK, `tcw capabilities drift` clean.

The check worth naming is criterion 1: eleven captured recordings of
`tcw work lifecycle` — one per row of the back-compat table plus **this
repository's own configuration** — taken from the CLI at `6e6c2af`, before the
parser was touched, and replayed against the rewritten one. Full output,
`--directive` for every stage and transition, and `--json`. All byte-identical.

That is the criterion that matters most for the riskiest slice in the
initiative, and it is the one the implementer could not have written into
agreement with the implementation.

## What is riskier here than in C1 or C2

**The subprocess runner.** `tcw/work/generate.py` is threads, pipes, process
groups, and signals — the three failure modes it guards against (unbounded
memory, deadlock, orphaned children) do not announce themselves, and one of them
(`SIGPIPE` on a chatty stderr) actually occurred and was caught by the criterion
written for it. The tests bound wall-clock so a hang fails rather than hangs, but
this is the code in the initiative most deserving of an independent read.

**Two amendments to the epic's spec now stand.** C2 moved the `body` cap to C3;
C3 corrected the epic's role table where it contradicted its own back-compat
table. Both are recorded in the epic's `spec.md`. A verifier should confirm the
epic still says what its children implemented.

**`builtin` resolves to nothing** until C5 and C6 fill the registries. Criterion
16 pins that as intended, but between now and then it is indistinguishable from
"not configured".

## Deferred, deliberately

- **The stage/status legality table** belongs to C5, and C4 consumes it. C3
  neither defines nor needs it.
- **`--no-exec`** is C4's flag; C3 ships the `execute=False` parameter it will
  call.
- **The README's lifecycle section** is correct but not final — the initiative
  assigns its full rewrite to C7.

## Closeout choices

- **Version:** deferred to the end of the initiative, with C1's and C2's.
- **Merge/PR route:** deferred with it; all slices land on
  `epic/polymorphic-work-lifecycle`.
- **Follow-up items:** none from C3.
