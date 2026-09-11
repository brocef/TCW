# Request — Refine the plugin skills and lifecycle prompts against the eval findings

## Why this is its own item, and why it is blocked

Task 12 of
`2026-07-22-evaluate-and-refine-the-plugin-skills-with-an-eval-harness` is the
act-on-it half of the eval work. It is separated from the measuring half because
**nothing here can start until there are findings**, and a refinement made
without them is justified by expectation rather than evidence.

Blocked by `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds`. Do not
start it early. The closeout of the parent item declined to apply refinements for
exactly this reason, and that judgement is recorded in its `refined-outcome.md`.

## How a finding routes to a fix

The parent plan's task 12 carries the routing. Its two rules, and the caveat that
matters more than either:

- **A nonce that never arrives** points at the injection layer — the six
  composing skills, the resolver, or the binding schema — and earns a pytest
  guard rather than a wording change.
- **A nonce that arrives and is ignored** points at prose, in `bookend` or in the
  stage routers. The agent read it and did not act.
- **Neither implication is safe on its own.** A missing nonce does not uniquely
  implicate the injection layer, and a delivered-but-ignored nonce does not
  uniquely implicate prose. The routing is a hypothesis to test before editing,
  not a diagnosis to act on.

**Read the provenance field first.** `grade.py` reports every nonce as
`injected`, `fallback` or `unknown`. A run that is mostly `fallback` means the
agent ran `tcw work stage prompt` by hand and the injection layer may have done
nothing — a finding about reach, not about prose, and it would route the fix to
entirely the wrong layer.

## Three standing constraints, from the parent plan

1. A refinement must be justifiable from the skill's own purpose, not merely from
   a failing case. Fixes that only satisfy the eval's prompts get rejected.
2. Deletion is a legitimate outcome where a transcript shows wasted work.
3. Prefer "do X because Y causes Z" over an all-caps MUST.

## The composing skill is six files, not one

`skills/tcw-work-stage/SKILL.md` plus five near-identical `tcw-work-stage-*`
files. An injection-layer fix applied to one leaves five unfixed, and the parity
guards in `tests/test_skill_lifecycle_parity.py` are parametrised over all six —
so a partial fix turns the suite red rather than shipping quietly. That is the
good outcome; do not work around it by narrowing the guard.

## Documentation and versioning

A refinement to any of the seven shipped stage prompts changes what
`tcw work stage prompt` emits, which is user-visible: it needs a release note and
a changelog entry, and it ships in the wheel. So does any change to how a binding
resolves. The parent item earned neither, because it changed no shipped surface.

Re-run the capability gate at closeout. The parent spec named two entries in the
blast radius — `work/run-a-lifecycle-stage` (`cap-f42255`) and
`work/configure-the-work-lifecycle` (`cap-b9711e`), both `Supported`. If a
refinement changes *what* a skill instructs an agent to do rather than how
reliably it does it, those need a body edit rather than a status flip.

## Out of scope

- Anything the run itself covers. This item starts where the findings report
  ends.
- `2026-09-11-validate-a-skill-prompt-binding-names-something-that-exists`,
  which is a real injection-layer defect already found and filed separately. It
  does not need a run to justify it and should not wait on one.
