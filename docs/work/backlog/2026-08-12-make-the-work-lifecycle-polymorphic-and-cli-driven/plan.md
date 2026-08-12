# Coordination plan — Make the work lifecycle polymorphic and CLI-driven

An epic's plan is a **coordination plan**: child boundaries, the commands that
create them, the dependency order, and the checkpoints where the epic reconciles.
No code is written against this item; implementation tasks belong to each child's
own `plan.md`.

> Rebuilt after the `codex` / `bllm-review` pass and the requester's intake
> decision. Seven children, not six; C1 is new and everything shifted.

## Children

All in this node (`tcw`), all `--initiative` rather than `--parent`: each starts
and completes on its own schedule, and `reconcile` follows the `initiative`
relation.

**Every child owns its own documentation and its own capability delta.** Each one
updates its command documentation, release notes, changelog, driving-skill text,
and ledger entries as it lands. C7 performs only the consolidation that cannot be
expressed earlier.

### C1 — Unify intake

**Delivers** `intake.md` as an artifact; `tcw work new` and `tcw work inbox
accept` writing intake instead of synthesizing a request; the body surface
resolving request-then-intake; `request` gaining `inputs=("intake.md",)`; and
`fs.py:2755-2769` deleted outright. Decides and records the `WORK_ARTIFACTS`
ordering question and the replacement for `tcw work new`'s `→ edit:` hint.

**Why first:** the epic's headline feature — a conditional template for a `bug`
item's request — is impossible while both creation paths write
`initial-request.md` unconditionally. It also has value entirely on its own: it
removes a duplicated template and makes the board's `R` letter mean something.

**Verified by:** acceptance criteria 2, 3, and 4 — a fresh item with no artifacts,
a piped item with intake only, an accepted inbox entry with intake only, and the
board letters and `show` output correct at each point. Plus a migration check
that existing items, which all have `initial-request.md`, are untouched.

**Capabilities:** new — `work/capture-raw-intake`; changed —
`work/open-a-work-item`, `work/manage-the-work-inbox`.

### C2 — Work item JSON projection

**Delivers** a versioned DTO with explicitly typed fields and an `artifacts`
map, plus `tcw work show --json`. Decides and documents the handling of
`WorkItem.capabilities` — an opaque `object` filled from arbitrary YAML — and of
`body`, which is unbounded.

**Verified by:** criterion 5. The schema-validation test is the point: a test
that merely enumerates dataclass fields would pass for an unusable payload, which
is exactly what review flagged.

**Capability:** changed — `work/read-a-work-item`.

**Blocked by:** C1 — the projection must describe the resolved body surface and
the `intake` artifact, and doing that after C1 avoids versioning the DTO twice.

### C3 — Hook roles, kinds, and conditions

**Delivers** the model change: `check` / `prompt` / `artifact` roles; the `blob`,
`file`, `generate`, and `builtin` kinds with the `generate` resource contract and
`file` node-root confinement; the `when:` matcher; parsing, validation, and the
four-row back-compat table; resolution as a library function. Also
`tcw work lifecycle --transition <id> --phase pre|post` and the Vocabulary term
`work-item/lifecycle-hook`. Picks the concrete `generate` output cap.

**No new command surface except `--phase`.** C3 makes resolution possible; C4
makes it reachable. Splitting them keeps the parser and validator change
reviewable on its own.

**Verified by:** criteria 1, 6, 7, 12, 13, and 15 — the legacy-config corpus, the
`generate` contract including the non-zero-exit discard, the exhaustive `when:`
truth table, `lifecycle` inertness, and every validation rejection by name.

**Capabilities:** changed — `work/configure-the-work-lifecycle`,
`work/inspect-the-lifecycle-contract`.

**Blocked by:** C2.

### C4 — The stage verb

**Delivers** `tcw work stage <id> [ref]` running pre-checks → resolve everything
→ write → print prompt, plus `--no-exec`. Stdout carries prompt text and nothing
else.

**Verified by:** criteria 8, 9, 10, and 16. Criterion 10 is the one worth
building first — a prompt hook failing after an artifact hook resolved must leave
nothing written, and the retry must then succeed.

**Capability:** new — `work/run-a-lifecycle-stage`.

**Blocked by:** C3.

### C5 — Artifact templates

**Delivers** `LifecycleStep.produces` as a tuple of artifact names, `sections`,
built-in templates keyed by artifact name, and the artifact hook wired into C4's
sequence. Decides explicitly whether `tcw serve` applies templates, and whether a
template needing hook context could render broken there.

**Verified by:** criteria 11 and 17 — creation with exact resolved content,
existing artifacts left byte-identical, and exactly one definition of each
built-in template.

**Capability:** new — `work/customize-lifecycle-artifact-templates`.

**Blocked by:** C4. This dependency is **technical**, not sequencing: after C1
the request artifact is created by the `request` stage, so the stage verb is the
firing point.

### C6 — Built-in stage prompts

**Delivers** `tcw/work/prompts/<stage>.md` as package data, `builtin` kind
resolution, and wheel packaging. Content condensed from [obra/superpowers].

**Verified by:** criterion 14, tested **against C3's resolution library** rather
than through `tcw work stage` — C6 lands before C4 may, and a child cannot verify
itself with a command another child introduces. The end-to-end check belongs to
checkpoint 3. Plus an installed-wheel test proving the prompts are packaged
rather than merely present in the source tree.

**Blocked by:** C3. **Parallel with C4** — do not chain them.

### C7 — Skill and documentation rewrite

**Delivers** `skills/tcw-work/references/stage-*.md` reduced to routers;
`references/hooks.md` rewritten around roles, kinds, and conditions; `SKILL.md`'s
"Always" section repointed from `tcw work lifecycle --stage` to the stage verb;
and README §"Binding your own skills and commands to the lifecycle"
(`README.md:587-622`) rewritten as one coherent section.

**Only consolidation.** Each of C1–C6 has already updated its own command docs,
changelog, release notes, and ledger. C7 does not flip other children's
capability deltas.

**The routers must not restate what the built-in prompts say** — that is
criterion 18, and it is what keeps CLI/plugin version skew readable as an old
answer rather than a contradiction.

**Verified by:** criterion 18; `tcw capabilities check`, `tcw capabilities
drift`, and `tcw validate` all clean.

**Blocked by:** C5, C6.

## Delegation commands

Run at the start of coordination, after the epic is started.

```bash
EPIC=2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven

tcw work new "Unify raw intake into a single artifact" \
    --initiative "$EPIC" --priority 78 --effort medium --complexity high \
    --tag work --tag cli
tcw work new "Project a work item as JSON" \
    --initiative "$EPIC" --priority 76 --effort low --complexity medium \
    --tag work --tag cli
tcw work new "Give lifecycle hooks roles, kinds, and conditions" \
    --initiative "$EPIC" --priority 74 --effort high --complexity very-high \
    --tag work --tag cli
tcw work new "Add the stage-entry verb" \
    --initiative "$EPIC" --priority 72 --effort medium --complexity high \
    --tag work --tag cli
tcw work new "Template the lifecycle artifacts" \
    --initiative "$EPIC" --priority 68 --effort medium --complexity medium \
    --tag work --tag cli
tcw work new "Ship built-in stage prompts with the CLI" \
    --initiative "$EPIC" --priority 70 --effort medium --complexity medium \
    --tag work --tag cli --tag docs
tcw work new "Repoint the work skill and docs at the CLI" \
    --initiative "$EPIC" --priority 66 --effort medium --complexity medium \
    --tag work --tag skills --tag docs
```

Then record the order as blockers — `--initiative` carries no dependency
relation, so without this every child reads as workable at once:

```bash
tcw work edit <C2> --blocked-by <C1>
tcw work edit <C3> --blocked-by <C2>
tcw work edit <C4> --blocked-by <C3>
tcw work edit <C6> --blocked-by <C3>
tcw work edit <C5> --blocked-by <C4>
tcw work edit <C7> --blocked-by <C5>
tcw work edit <C7> --blocked-by <C6>
```

C4 and C6 both hang off C3 and neither blocks the other. Chaining them would be a
false blocker the tool then enforces.

## Dependency order

```
C1 ──▶ C2 ──▶ C3 ──┬──▶ C4 ──▶ C5 ──┬──▶ C7
                   └──▶ C6 ──────────┘
```

Critical path: C1 → C2 → C3 → C4 → C5 → C7. C6 has slack equal to C4 + C5.

Risk placement: C3 is the riskiest child — it rewrites the parser every existing
`tcw-config.yaml` goes through — and it lands with no new command surface, so a
regression shows up in the existing suite rather than in a new feature nobody is
exercising. C1 is the most user-visible and comes first, alone, where a bug
report is easy to attribute.

## Rollup checkpoints

`tcw work reconcile $EPIC` before each, per `epic-deltas.md`:

1. **After C1** — the only checkpoint that gates on user-visible behavior. Run a
   real `tcw work new`, a real `inbox accept`, and check the board reads
   correctly before anything is built on top.
2. **After C2** — confirm the DTO is what C3 should build `generate` around.
   Cheapest point to change the payload; after C3 it is a config-visible
   contract.
3. **After C3** — the decision point for the epic. If the `when:` matcher or the
   role/kind table came out different from the spec, C4/C5/C6's specs are stale
   and get revised before they start rather than during.
4. **After C4 and C6 both land** — the first point where a user gets the whole
   feature end to end with nothing configured. This is where C6's built-in
   prompts get their real exercise, since C6 could only test them at library
   level.
5. **Before closeout** — final reconcile; every child resolved, every child's
   ledger entries flipped by that child, `tcw validate` clean.

## Documentation Sync

Evaluated for the initiative. Each child re-evaluates for its own diff at its
`implement` gate; this is the epic-level prediction.

- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — fires for C1–C6, per
  child as it lands.
- **`docs/release-notes/upcoming.md` [Public-API]** — fires for C1–C6, per child.
  **C1's entry needs the most care:** `tcw work new` no longer leaves a file to
  edit, which is the change most likely to surprise an existing user.
- **`README.md` [Public-API]** — fires for C1–C5. Each child adds its own
  commands and flags to the command table as it lands; **C7 owns the §"Binding
  your own skills and commands to the lifecycle" rewrite**, because that section
  describes one coherent model and four partial rewrites would be worse than one
  at the end.
- **`skills/tcw-work/SKILL.md` [Skill-Driven-Component]** — fires for C1 and C4
  in passing (the lifecycle they drive changes), and wholesale for C7. C1 updates
  `references/stage-request.md`'s claim that `initial-request.md` "is never
  absent" — which C1 makes false — rather than leaving it for C7.

No epic-level documentation task: C7 *is* one, and it is already a child.

## Verification

What the suite cannot check:

- **That the built-in prompts are good instructions.** No test asserts that. C6's
  `verify` stage needs a human reading them, and ideally a real work item planned
  end to end against them at checkpoint 4.
- **That the routers and the built-in prompts do not contradict each other.** A
  test asserts the CLI is named as the source; it cannot assert the router's
  summary is faithful. C7's `verify` stage.
- **That C1 does not break someone's muscle memory.** The regression tests cover
  the store; they do not cover a user typing `tcw work new` and expecting a file.
  Worth exercising by hand before C1 completes.
- **That existing `tcw-config.yaml` files really are unaffected.** The corpus
  covers the shapes we thought of. Running C3's build against this repo's own
  config is the check that covers the ones we did not.

## Notes

- **The children are not created yet, deliberately.** The boundaries are what
  this plan asks the user to review, and creating them before that review means
  retitling or deleting them if the boundaries move.
- Priorities descend with dependency order (78 → 66), all under the epic's 80.
  C6 sits at 70, above C5 at 68, because it is unblocked earlier.
- C1 and C2 both ship value alone. If the epic stalls after C2, unified intake
  and `tcw work show --json` are still real improvements.
- The first draft of this plan had six children and put intake handling nowhere.
  Review found the headline feature impossible without it; C1 is the result.

[obra/superpowers]: https://github.com/obra/superpowers
