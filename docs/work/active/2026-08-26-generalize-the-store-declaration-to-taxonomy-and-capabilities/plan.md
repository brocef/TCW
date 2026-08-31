# Plan — Generalize the store declaration to taxonomy and capabilities

Ten tasks, each its own commit, in an order chosen so that the CLI this work is
recorded with keeps running at every boundary. The spec's Risks section names
that hazard; this plan is where it is designed around.

## Ordering constraints

Three, and they are the reason the sequence is what it is:

1. **The taxonomy Feature rename lands before any capability names it.**
   `tcw capabilities set` refuses an unresolvable `Feature=`, so the reverse
   order fails closed. Task 1.
2. **`PROVISION_COMPONENTS` widens only after the adapters make the values
   honest.** Child A narrowed it deliberately after review found it accepting
   values it could not serve. Task 6, not before.
3. **The store layer is edited under a CLI that reads the store.** Tasks 3-5
   touch `FsTreeStore.open`, which every `tcw taxonomy` and `tcw capabilities`
   command runs through. Each lands green, and the item's own transitions are
   already taken.

## Tasks

### 1 — Rename the Feature, before anything references it

`configurable-work-store-location` → `configurable-component-store-location`,
description widened to all three trees. Re-point
`work/configure-the-work-store-location` at the new slug. Verify with
`tcw validate` and `tcw capabilities check` that nothing dangles.

_Done when:_ criterion 10. No reference to the old slug survives anywhere in the
repository.

### 2 — Give the tree stores a "usable" predicate, and the provisioner a component-aware one

The spec's central decision, landed on its own so it can be read on its own.

- A per-component store-layout predicate replaces the module-level
  `_is_store_layout` as the provisioner's authority. The work component's answer
  is today's `STORE_LAYOUT` check, unchanged; the tree components' answer is "an
  existing, readable directory".
- `FsStoreProvisioner` consults the component's predicate rather than the
  work-store constant, and the refusal at `tcw/store/fs.py:2604` stops saying
  "work store".

Tests first, and they are about the *difference*: a work declaration whose clone
lacks a status folder is still refused; a taxonomy declaration whose clone
carries a plain directory is accepted.

_Done when:_ the provisioner names no component-specific layout of its own, and
child A's 74 cases still pass.

### 3 — Extract the resolution ladder from `FsWorkStore.open`

Pure refactor, no behaviour change, landed separately so the next task's diff is
readable. `FsWorkStore.open`'s four rules become one shared function parameterized
by config section name and "usable" predicate; `FsWorkStore.open` calls it and
behaves identically.

**The regression net is the acceptance test:** `tests/test_store_provisioning.py`
(74) and `tests/test_external_work_store.py` (82) pass with nothing rewritten. A
change that makes any of them fail is the wrong refactor, not a test to update.

_Done when:_ 156 cases green and the work store's behaviour is byte-identical.

### 4 — Put `FsTreeStore.open` on the ladder

`<component>.path` and `<component>.repository`, resolved by the shared ladder
from task 3.

Rule 4 is the task's real content: with neither key configured, `open` returns
`cls(node_root / "docs" / cls.COMPONENT)` unconditionally, exactly as the current
one line does — no existence check, no new refusal. Write the rule-4 test first
and include the case of a node with **no** `docs/taxonomy/` at all.

_Done when:_ criteria 2, 4 and 6 hold for both tree components.

### 5 — Error surfaces for the tree stores

`StoreNotProvisioned` and `StoreDeclarationError` reach the taxonomy and
capabilities command surfaces the way they reach the work ones, and
`tcw/validate.py` reports all three failure modes per component.

Criteria 1 and 9 are properties over a command surface, so their tests are
parametrized across that surface — `tcw taxonomy list|path`,
`tcw capabilities list|show|drift` — rather than asserted at one call site. This
is the shape child A's fifth review pass established.

_Done when:_ criteria 1 and 9 hold, asserted across the surface.

### 6 — Widen `--component`, and fix the precedence check

- `PROVISION_COMPONENTS` becomes `COMPONENTS`; `--component`'s help stops saying
  "currently: work".
- `run_provision`'s local-store precedence check (`tcw/cli.py:126`) resolves the
  store for the component being provisioned instead of always calling
  `FsWorkStore.open`.

The precedence test is written **per component**, because a single hard-coded
`FsWorkStore.open` inside a loop over components is precisely the defect child A's
fourth review pass found, and the loop is what makes it invisible.

_Done when:_ criteria 3, 4 and 5 hold.

### 7 — `tcw init --taxonomy-path` / `--capabilities-path`

`init`'s `work_path` parameter generalizes to a per-component mapping; the two
new flags join `--work-path`. The scaffolding difference stays: work gets status
folders, the tree components get the directory.

_Done when:_ a tree store can be scaffolded at a configured location and opened
from it.

### 8 — Declare the four new capabilities

`tcw capabilities add` each, `Feature=configurable-component-store-location` or
`provisioned-component-stores` as appropriate, `Planning doc=` this slug, seeded
`Missing`. Bodies say plainly what the tree stores' weaker "usable" predicate does
and does not promise — the spec's second accepted consequence, written where a
user will meet it rather than only in this item's folder.

_Done when:_ `tcw capabilities check` passes and every new path resolves.

### 9 — Documentation

The block below, as one pass, once tasks 1-8 are done and the suite is green.

### 10 — Full suite, then `outcome.md`

Full run outside the restricted sandbox — the server suites bind loopback sockets
and produce a spurious `PermissionError` cluster inside it. Then `outcome.md`,
including what this plan got wrong.

## Documentation Sync

Evaluated against this node's declared entries (`tcw work docs`; source: config).

| Entry | Trigger | Fires | What it needs |
| --- | --- | --- | --- |
| `README.md` | Public-API | **yes** | The external-store section (README 201-248) currently says provisioning supports the work store and that taxonomy and capabilities remain local. That sentence becomes false; the section widens to all three, including the new `--taxonomy-path` / `--capabilities-path` flags. |
| `docs/release-notes/upcoming.md` | Public-API | **yes** | Plain language: your taxonomy and capability trees can live somewhere else, or in another repository, the same way your work items already can. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **yes** | Grouped Added/Changed. Note the shared ladder as Internal. |
| `skills/tcw-taxonomy/SKILL.md` | Skill-Driven-Component | **yes** | The component gains a configurable and declarable location; the skill must stop implying `docs/taxonomy` is where the tree is. Same guardrail wording as `tcw-work`'s: do not compose a store path from the node root. |
| `skills/tcw-capabilities/SKILL.md` | Skill-Driven-Component | **yes** | Likewise. It already says "locate the filesystem store — `tcw capabilities path`"; that command's behaviour changes. |
| `skills/tcw-work/references/commands.md` | Skill-Driven-Component | **yes** | The `tcw provision` row says `[--component work]`. It grows two values. |

These go to `upcoming.md`, not into `v1.1.0.md`: v1.1.0 is now tagged, so this
item's work belongs to the next version. That is the difference from child A,
whose rework landed while its release was still untagged.

Version choice is offered at `verify`, after acceptance — never during
implementation. Child A's item recorded two premature cuts; this plan does not
make a third.

## Verification

What the suite cannot check, and who checks it:

- **The weak predicate is honestly documented.** A reader compares the tree-store
  capability bodies against what task 2 actually implements, and confirms neither
  claims a guarantee the work store gets and the tree stores do not.
- **The abstraction seam survives the widening.** The store-interface signatures
  are re-read after task 2: no URL, no ref, no clone directory, and no component
  name leaking into an abstract method.
- **Rule 4 really is unchanged.** Not "the tests pass" but a reading of the code
  path a project with no configuration takes, against the one line it replaces.
- **Codex parity.** Every criterion reproduced from a bare shell with no hook and
  no slash command, per `docs/lifecycle/harness.md`.
- **Error text is actionable cold.** The new tree-store messages read by someone
  who has never seen the feature. This is the check that found child A's defect
  after eleven criteria had passed.

## Notes

- Task 3 is a pure refactor with no acceptance criterion of its own. It exists
  because doing tasks 3 and 4 as one commit would bury a behaviour change for
  three components inside a diff that also moves the work store's most-reviewed
  code path.
- No blocker is recorded against child C. The two are genuinely parallel and the
  epic plan says so; adding one would be a lie the tool enforces.
