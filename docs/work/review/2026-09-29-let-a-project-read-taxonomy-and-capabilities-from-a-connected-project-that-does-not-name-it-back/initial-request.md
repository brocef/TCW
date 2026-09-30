# Let a project read taxonomy and capabilities from a connected project that does not name it back

## What is being asked for

A project must be able to declare a connection to another project that it only
**reads from**, without that other project naming it in return — a one-way,
read-only connection. Today every connection is two-way: a child that does not
declare its parent is reported as `nonreciprocal connection: parent '<id>' is not
declared`, and `taxonomy extends` over such a connection fails.

**Why.** The requester's upstream project, proposit-core, is a public repository.
The projects that build on it, proposit-orchestration and proposit-app, are
private. Core's `tcw-config.yaml` must not name them — no parent entry and no
relative paths into them — yet proposit-app's packages must keep
`taxonomy: extends: [proposit-core]`, because their taxonomy refers to core's
terms (4 terms, in 20 places, such as `proposit-core/argument/claim`). Core must
stand alone. The private side knows about core; core knows nothing of it. The
requester's next step — moving core's work items into core and removing core's
parent connection — waits on this.

What must hold, in the requester's words (condensed; `intake.md` has them
verbatim):

1. A downstream project can declare an upstream project it only reads from, with
   the usual `path` and `repository` resolution and `TCW_PROJECT_<ID>` override,
   without the upstream naming it. How it is declared is TCW's design choice: a
   child entry allowed to be one-way, or a separate key.
2. `taxonomy extends` and `capabilities extends` naming that upstream resolve,
   and `tcw validate` passes in both projects. The upstream's own `validate`
   knows nothing of the downstream and passes on its own.
3. Every command that would write into the upstream is refused with a clear
   message that the connection is read-only — not a graph error. Named examples:
   `tcw work delegate` into it and `reconcile` rows from it; the rule covers
   anything else that writes there.
4. References from the downstream into the upstream still resolve, such as the
   `proposit-core/<term>` paths in `meta.yaml` files.

## Constraints

- **Priority: high.** The user asked for this to start immediately.
- **Read-only toward the requester's repositories.** Their real configs may be
  read to check the design (`proposit-core/tcw-config.yaml`, the root
  `tcw-config.yaml` of proposit-orchestration, `proposit-app/tcw-config.yaml`,
  and `proposit-app/{packages/shared,apps/server,apps/mobile}/tcw-config.yaml`,
  under `/Users/brian/Projects/proposit-orchestration`). Nothing there is edited.
- **The design goes back to the requester before it is built.** They check it
  against the Proposit layout. The spec is therefore sent to the Proposit
  orchestrator session for review before the plan stage.
- **Release.** The requester needs the release version once it is ready. Brian
  publishes releases; TCW's side ends at "ready to publish".

## Out of scope

- The reverse direction: the upstream learning about, listing, or reading its
  downstream projects.
- Any change in the Proposit repositories themselves.

## Notes

- Reference material: the reproduction in `intake.md` (tcw 2.6.5). Its scratch
  copy lives in another session's temporary folder and may be gone; the steps
  are enough to rebuild it. Asked of the requester: no other references given.
- The requester asked for a GitHub issue link if one is opened. None was opened
  at this stage; the item itself tracks the work.
- Written without questions to the user beyond priority: the requester stated the
  goals, the constraints and what they need back, and left the declaration shape
  to TCW. The spec decides that shape.

## References

- `intake.md` in this folder — the request verbatim, with the reproduction.
- `docs/capabilities/taxonomy/` and `docs/capabilities/capabilities/` entries on
  `extends` — the current inheritance behavior this changes.
- The Proposit configs listed under Constraints — the layout the design must fit.
