# Plan — Give lifecycle hooks roles, kinds, and conditions

Tasks in dependency order, one commit each unless noted.

## The ordering constraint

**Task 1 lands before the parser is touched, in its own commit.** Criterion 1
checks three renderings against baselines captured from the *old* binary; a
baseline written during implementation is the implementer recording what the code
now does. Everything else here is convenience.

## Tasks

### 1. Capture the legacy corpus and its baselines

One `tcw-config.yaml` per row of the back-compat table, plus a copy of this
repository's own. For each, record `tcw work lifecycle`, `--directive` for every
stage and transition id, and `--json`. Commit under
`tests/fixtures/lifecycle_baseline/`.

Nothing else changes in this commit. — criterion 1

### 2. `Condition`: parse, validate, match

`Condition` with `matches(item)`, and its parser with every shape rejection
(`tags: bug`, `tags: [1]`, `when: null`, non-string `type`, invalid `type`,
unknown key). No wiring yet.

The truth table is tested here as a unit; criterion 8 wires it into all three
roles later and re-tests it there. — criteria 8, 9

### 3. `Binding` becomes kind+value+when

Replace the `skill`/`command` fields. Keep `.ref`. Update `_parse_binding` to the
six kinds with per-role legality, `builtin: true` validation, and duplicate
detection by `(kind, value, when)`.

Update the two assertions in `tests/test_lifecycle_policy.py` that construct
bindings the old way. — criteria 9, 17

### 4. `StageBindings`, `legacy_prompt`, and the policy shape

`StageBindings`, `LifecyclePolicy.artifacts`, `output_cap`, `policy.stage()`
returning prompts, `policy.stage_checks()`. Parser accepts both the bare list
(`legacy_prompt=True`) and the explicit `pre:`/`prompt:` form, and the top-level
`artifacts:` map validated against `WORK_ARTIFACTS`.

Artifact-list validation: `builtin` last and unconditional, no entry after an
unconditional one, no `command`, no `skill`. — criteria 9, 10

### 5. Rendering: grouped for legacy, and the `--json` superset

`_directive_text` keeps the grouped renderer for `legacy_prompt` lists and gains
declaration-order concatenation for explicit ones. `--json` keeps `bind` meaning
the prompt list; `pre`, `when`, `artifacts`, and `output-cap` appear only when
configured.

**Run task 1's baselines here.** This is where criterion 1 either holds or does
not. — criterion 1

### 6. `--phase`

The flag, its filtering, and both illegal-combination errors. — criterion 12

### 7. The bounded subprocess runner

`tcw/work/generate.py`: `Popen`, own process group, stdin written and closed
tolerating `BrokenPipeError`, stdout and stderr drained concurrently and each
bounded, kill-the-group on cap or timeout, reap, decode UTF-8 with
`errors="replace"`, discard all stdout on non-zero exit.

The riskiest code in the slice. Its criteria — an unbounded generator returning
promptly, a chatty stderr not deadlocking, a grandchild not surviving the
timeout — are written before the implementation.
— criteria 3, 4, 5, 6, 18

### 8. Resolution

`tcw/work/resolve.py`: `Builtins`, `Resolution`, `resolve_prompts`,
`resolve_artifact`, `select_checks`, and `execute=False` as a branch of the same
traversal. `file:` reading with its runtime failure modes. Exact concatenation.
— criteria 2, 7, 13, 14, 15, 16

### 9. Wire conditions into transition checks

`run_bindings` filters through `select_checks`. This is the third role, and the
one criterion 8 exists to stop being forgotten. — criterion 8

### 10. `tcw validate` — the sixteen rejections

Path confinement with symlinks resolved on both sides, plus every other message.
— criterion 9

### 11. The Vocabulary term

`work-item/lifecycle-hook`, declared through `tcw taxonomy`. The initiative's
spec requires it before capability prose leans on the noun.

### 12. Documentation Sync

- **`README.md` [Public-API]** — the lifecycle-binding section gains roles,
  kinds, conditions, and the `generate` contract. The initiative assigns the
  *full rewrite* of §"Binding your own skills and commands to the lifecycle" to
  C7; C3 makes it correct, not final.
- **`docs/release-notes/upcoming.md` [Public-API]** — writing your own stage
  instructions, in plain language.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — the model, the kinds, the
  contract, the validation table, `--phase`.
- **`skills/tcw-work/references/hooks.md` [Skill-Driven-Component]** — this is
  the file that documents bindings. C7 rewrites it around the new model; C3
  updates it enough to not be wrong.

### 13. Capability ledger

Changed: `work/configure-the-work-lifecycle`, `work/inspect-the-lifecycle-contract`.

## What could go wrong

- **The `--json` superset turns out not to be a superset.** If a legacy config
  produces different JSON, criterion 1 fails at task 5 and the payload design is
  wrong, not the fixture. Finding that at task 5 rather than at task 12 is why
  the baselines come first.
- **Task 7 is where the bugs live.** Deadlock and orphaned children do not
  announce themselves; the criteria are written to make them fail loudly, and if
  a test hangs rather than fails, that is the finding.
- **This repository's own config is in the corpus.** If C3 changes its behavior,
  every `tcw` command in this session starts behaving differently — which is the
  cheapest possible place to notice.
