# Add `tcw work methodology` to resolve a stage's skill binding

Epic: [Redefine the TCW work lifecycle](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks)

Child 3 of 5. Depends on child 2's policy model. **Must land before child 4** — a
stage document that does not know where its methodology comes from cannot be
written.

## Scope

TCW's stage documents specify the **contract** (purpose, inputs, the artifact
produced, how it exits) but not the **methodology** (how you actually arrive at a
spec, a plan, an implementation). Methodology varies by team, so a stage document
must point at one rather than contain it.

The whole mechanism is one command:

```
$ tcw work methodology spec
superpowers:brainstorming
```

- Resolution: configured binding → shipped default.
- Report which one applied.
- Unresolved prints nothing and exits 0; the stage proceeds on TCW's guidance.
- An unknown stage id exits non-zero.
- Ship a default binding per stage, or none where TCW has no opinion.

The payoff is that every stage document carries one harness-neutral step — *run
`tcw work methodology <stage>` and invoke the skill it names* — reading
identically under Claude and Codex. Dynamic context injection drops to optional
sugar rather than the primary path with a Codex fallback beside it.

## Explicitly out of scope

Deliberately the smallest thing that establishes the concept. Not included: a
repo-local `docs/work/lifecycle/<stage>.md` override, the three-tier
`bare-wins-local` order, a `reset` path, any definition of what a methodology
*document* must contain, and any build step baking methodology into generated
files (already rejected — plugin files are replaced on update, and Claude
namespaces plugin skills so a project cannot shadow one).

Each can slot in ahead of the configured binding later without changing this
command's contract.

## Done when

- The command resolves a configured binding, then a shipped default, then prints
  nothing — and reports which applied.
- An unknown stage exits non-zero.
- A node with no configuration behaves exactly as it does today.

## Notes

A down payment, not the final design. Its contract — "name the skill for this
stage" — is chosen to survive the deferred work, but that is an untested bet.
