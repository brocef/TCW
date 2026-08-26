# Plan — Declare a component store's home repository so a fresh checkout can provision it

_Coordination plan for an **epic**. The epic implements nothing itself; its
`implement` stage is dispatch, blocker maintenance, reconciliation, and answering
escalations. Every task below is a coordination action, not a code change._

Epic slug: `2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it`

## Child tasks

Three children, in the boundaries the spec fixed. Each is planned and specced on
its own; this plan settles only what each one owns, what it must not touch, and
what proves it done at the initiative level.

### Child A — Declare and provision the work store's home repository

**Owns.** The config vocabulary (a `repository` block beside `work.path`), the
resolution precedence, the provisioning verb, the materialization target, and
every error surface that currently swallows a missing store.

**Files it is expected to create or modify** — named here so child B and child C
can be planned against a known seam, and to be re-decided in child A's own plan
if its spec moves the seam:

- `tcw/store/fs.py` — `FsWorkStore.open` (2429-2459), `find_node` (147-161),
  `_has_work_store` (194-201)
- `tcw/store/base.py` — the abstract availability/provision operation
- `tcw/cli.py` — the new top-level verb's subparser (beside `init` at 139 and
  `validate` at 146)
- `tcw/validate.py` — the declared-but-unprovisioned report (145-148)
- a new `tests/test_store_provisioning.py`; `tests/test_external_work_store.py`
  extended, not rewritten

**Must not touch.** `FsTreeStore.open` (child B). Anything that writes to a
remote (child C).

**Done when.** Spec acceptance criteria 1, 2, 3, 5, 6, 7, 9 and 10 hold for the
work store.

```sh
tcw work new "Declare and provision the work store's home repository" \
    --initiative 2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it \
    --tag remote --tag work --tag cli \
    --priority 60 --effort high --complexity high
```

### Child B — Generalize the declaration to taxonomy and capabilities

**Owns.** Lifting `FsTreeStore.open`'s hard-coded `node_root/docs/<component>`
(`tcw/store/fs.py:1023-1025`) onto the same configured-locator + declaration
mechanism child A builds, so all three trees resolve identically; the matching
`tcw init` flags; the validation and `tcw <component> path` surfaces; and the
Feature-naming decision the spec left open (rename
`configurable-work-store-location`, or keep it and add a sibling).

**Files it is expected to create or modify.** `tcw/store/fs.py`
(`FsTreeStore.open`, `FsTaxonomyStore`, `FsCapabilitiesStore`), `tcw/cli.py`
(`--work-path` at 143 grows companions), `tcw/validate.py`,
`docs/taxonomy/` (the Feature decision), and the shared provisioning tests.

**Must not touch.** The provisioning verb's own contract — it consumes what child
A defines.

**Done when.** Spec acceptance criterion 4 holds: criteria 1-3 reproduce for a
declared taxonomy store and a declared capabilities store.

```sh
tcw work new "Generalize the store declaration to taxonomy and capabilities" \
    --initiative 2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it \
    --tag remote --tag taxonomy --tag capabilities --tag cli \
    --priority 40 --effort high --complexity high
```

### Child C — Keep a provisioned store in step with its remote across writes

**Owns.** Refreshing from the remote before a transition and publishing after it;
the failure, divergence, and conflict semantics that introduces; whether
publication blocks or is best-effort; and the way to turn it off.

**Files it is expected to create or modify.** `tcw/store/base.py` (publication as
a store property, per the spec's litmus table), `tcw/store/fs.py` (the git
plumbing behind `_effect_transition`), `tcw/work/cli.py` (what the user is told
when publication fails), and a new test module for the failure modes.

**Must not touch.** The provisioning verb, the config schema, or
`FsTreeStore.open`.

**Done when.** Spec acceptance criterion 8 holds, and criterion 6's carve-out is
exactly this child's publish step and nothing wider.

```sh
tcw work new "Publish provisioned-store writes to their remote" \
    --initiative 2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it \
    --tag remote --tag work \
    --priority 35 --effort high --complexity very-high
```

## Dependency order

B and C are genuinely parallel; only A gates them. Recorded as blockers, because
`--initiative` carries no dependency relation and `start` refuses past a blocker:

```sh
tcw work edit <child-B-slug> --blocked-by <child-A-slug>
tcw work edit <child-C-slug> --blocked-by <child-A-slug>
```

No blocker between B and C. Adding one would be a lie the tool enforces.

## Ordering inside child A

Child A writes its own plan, but one ordering constraint is an initiative-level
decision and belongs here: **the taxonomy Feature and Vocabulary term are
registered before any capability names them.** `tcw capabilities set` refuses a
`Feature=` reference that does not resolve, so the reverse order fails closed.

## Rollup checkpoints

`tcw work reconcile 2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it` — the epic's live view. Run it:

1. after the three children exist and their blockers are recorded, to confirm
   **Next** names child A alone;
2. after child A completes, to confirm B and C both read as ready;
3. after each of B and C completes;
4. before closeout, as the final reconcile.

Closeout: an epic cannot complete while an initiative child is open, and once all
three are resolved this epic may complete directly from `backlog` —
`tcw work reconcile 2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it --complete-when-ready`.

## Documentation Sync

Evaluated against this node's declared entries (`tcw work docs`; source: config).
**The epic itself changes no code, so no trigger fires on it.** Predicted per
child, to be scheduled as the final block of that child's own plan:

| Entry                            | Trigger                 | A       | B       | C       | What it needs                                                                                                                              |
| -------------------------------- | ----------------------- | ------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `README.md`                      | Public-API              | fires   | fires   | fires   | The external-store section (README 201-223) gains the repository declaration and the provisioning verb; B widens it past work; C states the publish behavior. |
| `docs/release-notes/upcoming.md` | Public-API              | fires   | fires   | fires   | Plain language: "your work items can live in another repository, and TCW can fetch it".                                                    |
| `docs/changelogs/upcoming.md`    | Any-Code-Change         | fires   | fires   | fires   | Grouped Added/Changed; each child writes its own entries.                                                                                   |
| `skills/<component>/SKILL.md`    | Skill-Driven-Component  | fires   | fires   | fires   | `skills/tcw-work/references/commands.md` § "Claims and external work stores" is where the store-location rules already live; A adds the verb, B adds taxonomy/capabilities, C adds the publish semantics. `skills/tcw-capabilities/SKILL.md` and `skills/tcw-taxonomy/SKILL.md` in B. |

There is no exploratory scope here, so no child gets a bare "re-evaluate
triggers" task in place of the rows above.

## Verification

What the suite cannot check, and who checks it:

- **The reported failure is actually fixed.** After child A lands, reproduce the
  requester's situation end to end: a checkout of a project whose work store
  lives in a second repository, on a machine that has only the first, running the
  provisioning verb and then `tcw work list`. This is a human check, and it is
  the one that decides whether the initiative was worth doing — the requester's
  own cloud session is the honest venue for it.
- **Codex parity.** Every criterion reproduced from a bare shell with no Claude
  hook and no slash command, per `docs/lifecycle/harness.md`. Cannot be asserted
  by a test that itself runs under one harness.
- **The abstraction seam.** A reviewer reads the store-interface signatures child
  A and child C add and confirms none of them mentions a URL, a ref, or a clone
  directory. The spec's litmus table is the checklist; no test can enforce it.
- **The supply-chain posture.** A reviewer confirms nothing outside the
  provisioning verb can cause a fetch from a config-supplied URL, and that the
  verb says which remote it is about to contact before contacting it.
- **Error text is genuinely actionable.** Read the new messages cold: does someone
  who has never seen this feature know what command to run next? Criterion 1 can
  assert a substring; it cannot assert that.

## Notes

- The children are deliberately **not** created at this stage. Dispatch is the
  epic's `implement` stage; the commands above are written out so that stage is
  mechanical rather than a second planning session.
- Child A is scoped to deliver the requester's unblock on its own. If the
  initiative stalls after A, that is an acceptable resting point, and B and C stay
  in the backlog as independently valuable items rather than as debt.
