# Add the post-mortem skill and its verify-stage trigger

Epic: [Redefine the TCW work lifecycle](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks)

Child 5 of 5. Depends on child 4's stage documents, which it reads.

## Scope

The post-mortem is the reason the lifecycle keeps discrete per-stage artifacts at
all: when something goes wrong late, you can walk back and find which stage first
missed it. That capability has never existed — it was the standing justification
for the artifact spine, and this child finally builds it.

- New `skills/tcw-post-mortem/`, reading the spine backward from
  `refined-outcome.md` (and any `rework.md`) to locate the stage where the
  problem was first missable. `Notes` across the artifacts is the primary trail.
- Writes `post-mortem.md`. **Never changes status.** Legal in `review` or after
  `completed` — the single permitted write into a completed item, which stays
  immutable in every other respect.
- Never a gate: `complete` does not wait on it.
- A `verify`-stage instruction offering it when verification surfaced serious
  unforeseen issues, invoked only on user assent.
- The read-only `tcw-post-mortem` agent (accelerator only; Codex has none).

This child owns the post-mortem **methodology** — how to conduct one. Child 4
owns `post-mortem.md`'s required sections.

## Done when

- A post-mortem can be produced both before and after completion.
- Producing one after completion changes nothing but that single file.
- The `verify` stage offers it on the failure path and never proceeds without
  user assent.

## Notes

Open at planning time: nothing in the lifecycle *decides* when to offer a
post-mortem. Marking it out-of-band names the shape, not the trigger. The
`verify`-stage instruction is the only candidate so far, and this child has to
settle it.
