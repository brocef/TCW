# Coordination plan — Make the work lifecycle polymorphic and CLI-driven

An epic's plan is a **coordination plan**: child boundaries, the commands that
create them, the dependency order, and the checkpoints where the epic reconciles.
No code is written against this item; implementation tasks belong to each child's
own `plan.md`.

> Rebuilt after two `codex` / `bllm-review` passes, the requester's intake
> decision, and the requester's scaffold decision. Seven children; C4, C5, and
> C6 are now all parallel behind C3.

## Children

All in this node (`tcw`), all `--initiative` rather than `--parent`: each starts
and completes on its own schedule, and `reconcile` follows the `initiative`
relation.

**Every child owns its own documentation and its own capability delta.** Each one
updates its command documentation, release notes, changelog, driving-skill text,
and ledger entries as it lands. C7 performs only the consolidation that cannot be
expressed earlier.

### C1 — Unify intake

**Delivers** `intake.md` as an artifact and an **abstract intake surface** on
`WorkStore` — not a re-reading of the existing `body` parameter, which would
give one abstract argument two adapter-specific meanings. Plus: `tcw work new`
and `tcw work inbox accept` writing intake instead of synthesizing a request, the
`origin` manifest and binary fallback preserved through a refactor of
`fs.py:2755-2769` rather than its deletion; **one canonical presence resolver**
(exists and non-empty) shared by `_read_item`, `body_path`, `artifacts()`, the
core revision, and `serve`; the body read-fallback and the write/promotion
contract; the core revision hashing which file resolved; and the lowercase `i`
board prefix.

`tcw work new`'s `→ edit:` hint points at `tcw work scaffold intake` (C5) once
that exists. Until then C1 prints the item path — the hint degrades rather than
creating a dependency on a parallel child.

**Why first:** the epic's headline feature — a conditional template for a `bug`
item's request — is impossible while both creation paths write
`initial-request.md` unconditionally. It also has value entirely on its own: it
removes a duplicated template and makes the board's `R` letter mean something.

**Verified by:** acceptance criteria 2, 3, 4, and 4b — a fresh item with neither
artifact, a piped item, and accepted inbox entries of all three shapes (text,
folder, binary-only) with attachments, manifest, and origin intact; the board
prefix and `show` output correct at each point including the both-absent and
empty-request-beside-real-intake cases; and a body edit on an intake-only item
promoting to a request, saying so, and leaving intake byte-identical. Plus a
migration check that existing items, which all have `initial-request.md`, are
untouched.

**Capabilities:** new — `work/capture-raw-intake`; changed —
`work/open-a-work-item`, `work/manage-the-work-inbox`.

### C2 — Work item JSON projection

**Delivers** a versioned DTO with explicitly typed fields and an `artifacts`
map, plus `tcw work show --json`. **Unifies with the projection that already
exists** — `serve/__init__.py:51-66` ships `_jsonable`/`_json_bytes` today, and a
second projection here would be exactly the two-sources drift this epic exists to
remove. Decides and documents the handling of `WorkItem.capabilities` — an opaque
`object` filled from arbitrary YAML, currently squeezed through
`json.dumps(…, default=str)` — and of `body`, which is unbounded.

**Verified by:** criterion 5. The schema-validation test is the point: a test
that merely enumerates dataclass fields would pass for an unusable payload, which
is exactly what review flagged. `serve`'s existing API responses must not change
shape except deliberately.

**Capability:** changed — `work/read-a-work-item`.

**Blocked by:** C1 — the projection must describe the resolved body surface and
the `intake` artifact, and doing that after C1 avoids versioning the DTO twice.

### C3 — Hook roles, kinds, and conditions

**Delivers** the model change: `check` / `prompt` / `artifact` roles; the `blob`,
`file`, `generate`, and `builtin` kinds with the `generate` resource contract and
`file` node-root confinement; the `when:` matcher; parsing, validation, and the
full back-compat table including the preserved grouped rendering; resolution as a
library function. Also `tcw work lifecycle --transition <id> --phase pre|post`
and the Vocabulary term `work-item/lifecycle-hook`. Picks the concrete `generate`
output cap.

**`builtin` is entirely C3's** — both the syntax and the resolution. Splitting it
across C3 and C6 would let C4 and C5 meet valid `builtin` configuration with no
implementation behind it. C6 ships only the content the kind resolves to.

**No new command surface except `--phase`.** C3 makes resolution possible; C4 and
C5 make it reachable. Splitting them keeps the parser and validator change
reviewable on its own.

**Verified by:** criteria 1, 6, 7, 12, 13, and 15 — the legacy-config corpus, the
`generate` contract including the non-zero-exit discard, the exhaustive `when:`
truth table, `lifecycle` inertness, and every validation rejection by name.

**Capabilities:** changed — `work/configure-the-work-lifecycle`,
`work/inspect-the-lifecycle-contract`.

**Blocked by:** C2.

### C4 — The stage verb

**Delivers** `tcw work stage <id> [ref]` running legality → pre-checks → resolve
→ print prompt, plus `--no-exec`. Stdout carries prompt text and nothing else,
and the command **writes nothing at all**.

**Verified by:** criteria 8, 9, and 16. The clause worth building first is that
running the verb for any stage leaves the item folder byte-identical — that is
what makes it safe to run purely for its instructions, and it is the property
round-2 review found the earlier design had lost.

**Capability:** new — `work/run-a-lifecycle-stage`.

**Blocked by:** C3.

### C5 — Artifact scaffolding

**Delivers** `LifecycleStep.produces` as a tuple of artifact names,
`tcw work scaffold <artifact> [ref]` writing `<artifact>.draft.md`, built-in
templates keyed by artifact name, and the stage/status legality table both this
and C4 consult. Decides explicitly whether `tcw serve` offers scaffolding, and
whether landing an artifact removes its draft.

**Verified by:** criteria 11 and 17 — a draft written with exact resolved
content, `spec.md` not created, the board unchanged, a refusal when the real
artifact exists, and a built-in template for every `WORK_ARTIFACTS` name.

**Capability:** new — `work/customize-lifecycle-artifact-templates`.

**Blocked by:** C3 only. **Parallel with C4.** Once stage entry stopped writing,
scaffolding needed nothing from the stage verb — the dependency earlier drafts
defended twice turned out to be neither sequencing nor technical.

### C6 — Built-in stage prompts

**Delivers** `tcw/work/prompts/<stage>.md` as package data and wheel packaging.
Content condensed from [obra/superpowers]. The `builtin` kind itself is C3's.

**Verified by:** criterion 14 tested **against C3's resolution library** rather
than through `tcw work stage`, since C6 may land before C4 and a child cannot
verify itself with a command another child introduces — plus an installed-wheel
test proving the prompts are packaged rather than merely present in the source
tree. The end-to-end check belongs to **checkpoint 4**.

**Blocked by:** C3. **Parallel with C4 and C5** — do not chain them.

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

**Blocked by:** C4, C5, C6.

### C8 — Backlog and upstream-issue audit

**Delivers** no code. A full pass over this repo's own `docs/work` backlog and
the open GitHub issues on the TCW repository, reconciling both against the design
this epic shipped: items retitled or rescoped where the new model changed what
they mean, closed or discarded where the model made them moot, and filed where it
created a gap.

A design change this size invalidates work items in three ways, and each needs a
different action:

- **Made moot.** The item describes a problem the new model no longer has →
  `tcw work discard`, with the reason naming the child that removed it. The
  known candidates:
  `2026-08-12-teach-the-remaining-readers-to-tell-a-vanished-item-from-an-absent-one`
  (C1's canonical presence resolver is exactly this fix, applied once at the
  source) and
  `2026-08-11-roll-back-or-reorder-the-pre-move-set-field-writes-on-a-lost-transition`
  (re-check against C1's write/promotion contract).
- **Rescoped.** The item still names a real gap, but against the old surface →
  edit the request/spec in place.
  `2026-07-22-evaluate-and-refine-the-plugin-skills-with-an-eval-harness` is the
  clearest: after C6 and C7 the thing under evaluation is largely the CLI's
  built-in prompts, not skill prose. `2026-08-04-supplement-filesystem-tcw-work-…`
  and the three `remote/*` adapter items now inherit an abstract intake surface
  and a versioned DTO they were written without.
- **Newly possible or newly needed.** Gaps this epic opens rather than closes —
  file them as new items rather than smuggling them into C7's closeout.

Upstream GitHub issues get the same three-way treatment: comment and close what
this epic resolved, edit what it rescoped, open what it exposed. **Close nothing
without saying which child resolved it** — an issue closed silently reads to the
reporter as ignored.

**Runs on the `tcw-audit-work-backlog` skill**, one item at a time, with the
`tcw:tcw-backlog-auditor` agent doing the read-only verification per item. The
audit is a real work item rather than a closeout checklist because it changes
tracked state and the user approves each action.

**Verified by:** no acceptance criterion — this child ships no behavior the suite
can assert. Its `verify` stage is the user confirming each disposition. `tcw
validate` clean afterwards.

**Blocked by:** C7. Last, deliberately: auditing the backlog against a design
that is still half-landed produces dispositions that are wrong by the time the
epic finishes.

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
tcw work new "Scaffold lifecycle artifacts from templates" \
    --initiative "$EPIC" --priority 71 --effort medium --complexity medium \
    --tag work --tag cli
tcw work new "Ship built-in stage prompts with the CLI" \
    --initiative "$EPIC" --priority 70 --effort medium --complexity medium \
    --tag work --tag cli --tag docs
tcw work new "Repoint the work skill and docs at the CLI" \
    --initiative "$EPIC" --priority 66 --effort medium --complexity medium \
    --tag work --tag skills --tag docs
tcw work new "Audit the backlog and upstream issues against the new lifecycle" \
    --initiative "$EPIC" --priority 64 --effort medium --complexity low \
    --tag work --tag docs
```

Then record the order as blockers — `--initiative` carries no dependency
relation, so without this every child reads as workable at once:

```bash
tcw work edit <C2> --blocked-by <C1>
tcw work edit <C3> --blocked-by <C2>
tcw work edit <C4> --blocked-by <C3>
tcw work edit <C5> --blocked-by <C3>
tcw work edit <C6> --blocked-by <C3>
tcw work edit <C7> --blocked-by <C4>
tcw work edit <C7> --blocked-by <C5>
tcw work edit <C7> --blocked-by <C6>
tcw work edit <C8> --blocked-by <C7>
```

C4, C5, and C6 all hang off C3 and none blocks another. Chaining any pair would
be a false blocker the tool then enforces.

## Dependency order

```
                   ┌──▶ C4 ──┐
C1 ──▶ C2 ──▶ C3 ──┼──▶ C5 ──┼──▶ C7 ──▶ C8
                   └──▶ C6 ──┘
```

Critical path: C1 → C2 → C3 → (widest of C4/C5/C6) → C7 → C8. The three middle
children are fully parallel, so the epic's wall-clock is bounded by C3 plus the
longest single one of them.

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
   level. If C5 has also landed, exercise `scaffold` here too; it does not gate
   this checkpoint.
5. **After C7, before closeout** — the epic's feature work is done and the design
   is final, which is the precondition C8 needs. Run the audit here, then a final
   reconcile: every child resolved, every child's ledger entries flipped by that
   child, `tcw validate` clean, and the backlog and upstream issues reconciled
   against what actually shipped rather than against what this plan predicted.

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
- **`skills/tcw-work/SKILL.md` [Skill-Driven-Component]** — fires for C1, C4, and
  C5 in passing (the lifecycle they drive changes), and wholesale for C7. C1
  updates `references/stage-request.md:18-19`, which states that
  `initial-request.md` "is the always-present body and overview surface, so it is
  never absent" — a claim C1 makes false, and the exact sentence that encoded the
  old model. Fixing it belongs to C1, not C7.

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
  retitling or deleting them if the boundaries move. They have already moved
  twice.
- Priorities descend with dependency order (78 → 64), all under the epic's 80.
  C4, C5, and C6 sit adjacent (72/71/70) because they are genuinely parallel;
  the ordering between them is a tiebreak for the board, not a dependency.
- C1 and C2 both ship value alone. If the epic stalls after C2, unified intake
  and `tcw work show --json` are still real improvements.
- **Two rounds of review reshaped this plan.** Round 1 found the headline feature
  impossible without intake unification, which produced C1. Round 2 found that
  writing artifacts at stage entry would re-create for every other artifact the
  exact defect C1 fixes for the request — which produced the scaffold verb, and
  freed C5 from C4 as a side effect.

[obra/superpowers]: https://github.com/obra/superpowers
