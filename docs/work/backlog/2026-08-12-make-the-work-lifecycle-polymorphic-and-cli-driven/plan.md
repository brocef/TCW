# Coordination plan — Make the work lifecycle polymorphic and CLI-driven

An epic's plan is a **coordination plan**: child boundaries, the commands that
create them, the dependency order, and the checkpoints where the epic reconciles.
No code is written against this item; every implementation task belongs to a
child's own `plan.md`.

## Children

Six children, all in this node (`tcw`), all `--initiative` rather than
`--parent`: each starts and completes on its own schedule, and `reconcile`
follows the `initiative` relation.

### C1 — Work item JSON projection

**Delivers** one projection function (`WorkItem` + `artifacts()` → dict) and
`tcw work show --json`.

**Why first:** it is the payload a `generate` hook receives, so C2 cannot define
`generate` without it. It is also the only child that ships user-visible value
with nothing else in place.

**Verified by:** `tcw work show <ref> --json` parses as JSON and carries every
`WorkItem` field plus an `artifacts` name→presence map; a test asserts the
projection covers every field of the dataclass, so a field added later fails the
test rather than silently vanishing from the payload.

**Capability:** changed — `work/read-a-work-item`.

### C2 — Hook roles, kinds, and conditions

**Delivers** the model change: `check` / `prompt` / `artifact` roles; the
`blob`, `file`, `generate`, and `builtin` kinds; the `when:` matcher; parsing,
validation, and back-compat in `parse_lifecycle_policy`; resolution as a library
function the CLI calls. Also `tcw work lifecycle --transition <id> --phase
pre|post` and the new Vocabulary term `work-item/lifecycle-hook`.

**No new command surface except `--phase`.** C2 makes resolution *possible*; C3
makes it *reachable*. Splitting them keeps the parser/validator change reviewable
on its own.

**Verified by:** round-trip tests per kind; a bare-list stage binding parsing as
`prompt`; `tcw validate` rejecting each illegal shape by name (unknown role key,
`command` in a prompt position, `skill` in a check position, unknown `when:` key,
missing `file` path); and the inertness test from criterion 8 — bind a command
that writes a sentinel, run `lifecycle` for every id, assert no sentinel.

**Capabilities:** changed — `work/configure-the-work-lifecycle`,
`work/inspect-the-lifecycle-contract`.

**Blocked by:** C1.

### C3 — The stage verb

**Delivers** `tcw work stage <id> [ref]` running pre-checks → artifact hook →
prompt hooks, and `tcw work stage <id> --done [ref]` running post-checks. Stdout
carries prompt text and nothing else; every check's output goes to stderr.

**Verified by:** a failing `pre` check exiting non-zero with neither the artifact
hook nor any prompt hook having run; stdout containing exactly the resolved
prompt with a check bound that writes to both streams; the tag-conditional case
from acceptance criterion 4; and `--done` reporting itself as `[judgment]` for
`request` / `spec` / `plan`.

**Capability:** new — `work/run-a-lifecycle-stage`.

**Blocked by:** C2.

### C4 — Artifact templates

**Delivers** `sections` on `LifecycleStep`, built-in templates rendered from it,
the artifact hook wired into C3's sequence, and the two hardcoded
`initial-request.md` templates (`fs.py:2757`, `fs.py:3016`) collapsed into one
shared constant. Also decides, explicitly and in writing, whether `tcw serve`
applies templates — they are pure text rendering rather than shell, so the
"serve runs no hooks" rule does not settle it by itself.

**Verified by:** exactly one definition of the request template in the tree, used
by both `tcw work new` and `tcw work inbox accept`; the artifact hook refusing to
overwrite an existing artifact; and a test that each stage document's stated
required sections match `LifecycleStep.sections` — the drift guard acceptance
criterion 13 asks for.

**Capability:** new — `work/customize-lifecycle-artifact-templates`.

**Blocked by:** C3.

### C5 — Built-in stage prompts

**Delivers** `tcw/work/prompts/<stage>.md` as package data, resolution of the
`builtin` kind, and packaging so the files ship in the wheel. Content is
condensed from [obra/superpowers] — the spirit, not the volume.

**Verified by:** `tcw work stage spec` with nothing configured printing the
built-in text; `{builtin: true}` composed with a node binding printing both in
declaration order; and an installed-wheel test proving the prompt files are
actually packaged rather than only present in the source tree.

**Blocked by:** C2. **Parallel with C3** — do not chain them. C5 needs
resolution, not the verb.

### C6 — Skill and documentation rewrite

**Delivers** `skills/tcw-work/references/stage-*.md` reduced to routers pointing
at `tcw work stage <id>`; `references/hooks.md` rewritten around roles, kinds,
and conditions; `SKILL.md`'s "Always" section repointed from
`tcw work lifecycle --stage` to the stage verb; README §"Binding your own skills
and commands to the lifecycle" rewritten; and the capability ledger flipped for
every delta the initiative declared.

**The routers must not restate what the built-in prompts say.** A stale `tcw`
serving old prompts to a fresh skill should read as an old-but-coherent answer,
not a contradiction — that is the version-skew risk from the spec, and this is
where it is either created or avoided.

**Verified by:** every stage document naming the CLI as the source of its
instructions rather than carrying them; `tcw capabilities check` and
`tcw capabilities drift` clean; `tcw validate` clean.

**Blocked by:** C4, C5.

## Delegation commands

Run at the start of coordination, after the epic is started. Written out rather
than described so the boundaries survive the gap between this plan and the day
they are created.

```bash
EPIC=2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven

tcw work new "Project a work item as JSON" \
    --initiative "$EPIC" --priority 78 --effort low --complexity low \
    --tag work --tag cli
tcw work new "Give lifecycle hooks roles, kinds, and conditions" \
    --initiative "$EPIC" --priority 76 --effort high --complexity very-high \
    --tag work --tag cli
tcw work new "Add the stage-entry verb" \
    --initiative "$EPIC" --priority 74 --effort medium --complexity high \
    --tag work --tag cli
tcw work new "Template the lifecycle artifacts" \
    --initiative "$EPIC" --priority 70 --effort medium --complexity medium \
    --tag work --tag cli
tcw work new "Ship built-in stage prompts with the CLI" \
    --initiative "$EPIC" --priority 72 --effort medium --complexity medium \
    --tag work --tag cli --tag docs
tcw work new "Repoint the work skill and docs at the CLI" \
    --initiative "$EPIC" --priority 68 --effort medium --complexity medium \
    --tag work --tag skills --tag docs
```

Then record the order as blockers — `--initiative` carries no dependency
relation, so without this every child reads as workable at once:

```bash
tcw work edit <C2> --blocked-by <C1>
tcw work edit <C3> --blocked-by <C2>
tcw work edit <C5> --blocked-by <C2>
tcw work edit <C4> --blocked-by <C3>
tcw work edit <C6> --blocked-by <C4>
tcw work edit <C6> --blocked-by <C5>
```

C3 and C5 both hang off C2 and neither blocks the other. Chaining them would be a
false blocker the tool then enforces.

## Dependency order

```
C1 ──▶ C2 ──┬──▶ C3 ──▶ C4 ──┬──▶ C6
            └──▶ C5 ──────────┘
```

The critical path is C1 → C2 → C3 → C4 → C6; C5 has slack equal to C3 + C4.

Risk placement: C2 is the riskiest child — it rewrites the parser every existing
`tcw-config.yaml` goes through — and it sits behind only C1 and in front of
everything, which is where an isolated change with its own test suite belongs. It
lands with no new command surface, so a regression there shows up in existing
tests rather than in a new feature nobody is exercising yet.

## Rollup checkpoints

`tcw work reconcile $EPIC` before each of these, per `epic-deltas.md`:

1. **After C1** — confirm the projection shape is what C2 should build `generate`
   around. Cheapest point to change the payload; after C2 it is a config-visible
   contract.
2. **After C2** — the decision point for the epic. If the `when:` matcher or the
   role/kind table came out different from the spec, C3/C4/C5's specs are stale
   and get revised before they start rather than during.
3. **After C3 and C5 both land** — the first point where a user gets the whole
   feature end to end with nothing configured. Exercise it against a real item
   before C4 adds templates on top.
4. **Before closeout** — final reconcile; every child resolved, capability ledger
   flipped, `tcw validate` clean.

## Documentation Sync

Evaluated for the initiative. Each child re-evaluates for its own diff at its
`implement` gate; this is the epic-level prediction of which triggers fire and
where the work lands.

- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — fires for C1–C5. Each
  child writes its own entry as it lands; no epic-level task.
- **`docs/release-notes/upcoming.md` [Public-API]** — fires for C1, C2, C3, C4,
  C5. Same: per-child, as each lands.
- **`README.md` [Public-API]** — fires for C1, C2, C3, C4. §"Binding your own
  skills and commands to the lifecycle" (`README.md:587-622`) and the command
  table (`README.md:684`) are **one coherent rewrite**, not four incremental
  edits. Children C1–C4 add their commands to the table; **C6 owns the section
  rewrite** so the README describes the finished model once rather than four
  partial models in sequence.
- **`skills/tcw-work/SKILL.md` [Skill-Driven-Component]** — fires. The lifecycle
  it drives changes shape entirely. **C6 owns it**, including
  `references/hooks.md` and every `references/stage-*.md`.

No epic-level documentation task: C6 *is* the documentation task, and it is
already a child.

## Verification

What the suite cannot check, and what a human must:

- **That the built-in prompts are actually good instructions.** No test can
  assert that. C5's `verify` stage needs a human reading them, and ideally a real
  work item planned end to end against them before C5 completes.
- **That the router docs and the built-in prompts do not contradict each other.**
  A test can assert the CLI is *named* as the source; it cannot assert the
  router's summary is faithful. C6's `verify` stage.
- **That existing `tcw-config.yaml` files really are unaffected.** The compat
  test covers the shapes we think of. Running C2's build against this repo's own
  config, and against a config exercising every legacy shape, is the check that
  covers the ones we did not.

## Notes

- **The children are not created yet, deliberately.** The boundaries are the main
  thing this plan is asking the user to review, and six items created before that
  review is six items to retitle or delete if the boundaries move. Create them at
  the start of coordination, after `tcw work start` on the epic.
- Priorities descend with dependency order (78 → 68) so the board reads in
  workable order, and all sit just under the epic's 80.
- C1's effort is `low` and its value is real on its own; if the epic stalls after
  C1, `tcw work show --json` still shipped.
- C4's `serve` decision is called out as a deliverable rather than left to
  discovery, because "serve runs no hooks" answers a question about *shell* and
  templates are not shell. Deciding it by default is how the two surfaces drift.

[obra/superpowers]: https://github.com/obra/superpowers
