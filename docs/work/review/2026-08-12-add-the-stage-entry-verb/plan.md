# Plan — Add the stage-entry verb

## Tasks

### 1. `STAGE_STATUSES` in `base.py`

The table, beside `LIFECYCLE_STEPS`, and its self-consistency test: keys equal
`STAGE_IDS`, every value a subset of `WORK_STATUSES`, and each row asserted
against its expected tuple — including `postmortem` **without** `discarded`,
which is the row the first draft got wrong. — criterion 4

### 2. `tcw work stage <id> [ref]`

Ordering exactly as specced: id → item → legality → checks → resolve → print.
Text buffered and emitted once, after everything that can fail has succeeded.
Errors to stderr, stdout empty, exit 1.
— criteria 1, 3, 5, 5b, 6, 9, 12

### 3. `--no-exec`

`execute=False` through to C3's resolver; checks skipped entirely; the plan
printed to stderr. — criteria 7, 8

### 4. The "writes nothing" checks

Both assertions: a `WorkStore` wrapper that fails the test if any mutating method
is called, and an item-folder manifest compared before and after. Run for every
stage legal on the item. — criterion 2

### 5. The exhaustive legality check

Every pair in `STAGE_IDS` × `WORK_STATUSES` not in the table is rejected by the
command. Driven from the table so it cannot drift. — criteria 4, 5

### 6. Descendant behaviour

A two-node fixture where the descendant's `generate` hook reports its own item
slug, `TCW_NODE_ROOT`, and working directory. — criterion 10

### 7. Documentation Sync

- **`README.md` [Public-API]** — the verb, `--no-exec`, and the stream contract
  in the command table and the lifecycle section.
- **`docs/release-notes/upcoming.md` [Public-API]** — asking TCW what to do at a
  stage, in plain language.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — `STAGE_STATUSES`, the
  verb, the flag.
- **`skills/tcw-work/references/commands.md` + `hooks.md`
  [Skill-Driven-Component]** — the verb alongside `lifecycle`. C7 owns the
  wholesale repointing of the stage documents; C4 makes the command reachable.

### 8. Capability ledger

`work/run-a-lifecycle-stage` is **new** — declared in `capabilities.yaml`
(already written) and flipped by the completion gate. C7 is consolidation-only
and will not do it. — criterion 11

## What could go wrong

- **The exhaustive pair check finds a legal combination the table forbids.** That
  would be the table being wrong, not the test — the point of driving it from the
  Cartesian product rather than from cases someone thought of.
- **`--no-exec` printing partial text reads as the whole prompt.** The plan on
  stderr is the mitigation; criterion 8 pins that it prints *something*, so the
  flag is a dry run rather than a no-op.
