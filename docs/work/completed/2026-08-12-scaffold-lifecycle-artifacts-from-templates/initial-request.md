# Scaffold lifecycle artifacts from templates

Child **C5** of the initiative
[`2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`][epic].

## Product changes

`tcw work scaffold <artifact> <ref>` writes a starting point for a lifecycle
document: it resolves that artifact's template — TCW's own, or the project's, or
one chosen by a script the project owns — and writes it to
`<artifact>.draft.md`.

**A draft, not the artifact.** `spec.draft.md`, never `spec.md`. That distinction
is the whole design: artifact presence is what the board renders and what "find
your place" reads, so a command that wrote `spec.md` would light up `S` before
any spec existed — exactly the defect C1 spent three verify rounds removing for
the request. A draft is a file to type into; the agent authors the real document
from it.

Every artifact has a template, including `intake`, whose built-in template is
**empty** — intake has no prescribed structure because it is whatever someone
supplied. That answers what replaced `tcw work new`'s old `→ edit:` hint: nothing
synthesizes a request any more, and `tcw work scaffold intake` is the affordance
that used to provide.

## Technical changes

- `LifecycleStep.produces` becomes a **tuple of artifact names**. One artifact
  per stage was never true: `inbox` produces none and `verify` produces
  `refined-outcome.md` *or* `rework.md`, recorded today as prose rather than as
  names.
- Built-in templates keyed by artifact name, filling the `artifact_templates`
  half of C3's `Builtins`.
- **Resolve fully, then write.** If a hook fails, nothing is written and a retry
  is clean. If the write fails after resolution succeeded, exit non-zero, report
  to stderr, and put nothing on stdout.
- Two decisions the initiative left explicitly to this child: whether `tcw serve`
  offers scaffolding, and whether landing an artifact removes its draft.

## Meta changes

**Blocked by C3** for the resolution library, and **not** by C4 — the initiative
removed that dependency once stage entry stopped writing.

C4 landed first and, by an amendment to the epic, now owns the stage/status
legality table. C5 **consumes** `STAGE_STATUSES` rather than defining it.

[epic]: ../../active/2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven/initial-request.md
