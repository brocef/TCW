# Plan — Scaffold lifecycle artifacts from templates

Eight tasks, linear. The suite is green at every one of the eight commit
boundaries; where that forced a split, the task says so.

## Tasks

### 1. `produces_note`, and the renderers move to it

Add `LifecycleStep.produces_note: str = ""` beside `produces`
(`tcw/store/base.py:683`), populated on every row in `LIFECYCLE_STEPS` with the
prose `produces` carries today — verbatim, including `verify`'s
`"refined-outcome.md (accepted) or rework.md (rejected)"` and `inbox`'s `""`.
Repoint the two renderers: the `produces:` line in `_lifecycle_lines`
(`tcw/work/cli.py:670-671`) and the `"produces"` key in `--json`
(`cli.py:915`). **`produces` itself is untouched here** and stays a string.

This task exists as its own commit for one reason: it is the only place a
baseline can legitimately break. All eleven fixtures in
`tests/fixtures/lifecycle_baseline/` and `tests/test_lifecycle_hooks.py:277`
must pass **unmodified** across it, which is exactly the assertion that the
`--json` payload and the human render did not move. Every later task is then
free of them.

— criterion 12

### 2. `produces` becomes a tuple

Change the field to `tuple[str, ...]` of extensionless artifact names — `()`,
`("initial-request",)`, `("spec",)`, `("plan",)`, `("outcome",)`,
`("refined-outcome", "rework")`, `("post-mortem",)` — and add the two tests:

- **The drift invariant**, per step over `LIFECYCLE_STEPS`: the `<name>.md`
  filenames appearing in `produces_note` equal `{f"{n}.md" for n in produces}`,
  including `inbox`'s empty pair. This is what stops the two fields describing
  the same fact differently. — criterion 11
- **The tuple's shape**: `verify`'s is exactly `("refined-outcome", "rework")`,
  every step's is a tuple, and the union over all steps equals the set of
  artifact names any stage produces. — criterion 10

Also in this commit, `tests/test_skill_lifecycle_parity.py:85-93` must move —
`artifacts_in(step.produces)` regexes a string and raises on a tuple, so leaving
it for a later task leaves the tree red. Tighten it to convert names to
filenames (`{f"{n}.md" for n in step.produces}`) rather than substring-matching
the extensionless names, and fold in `test_verify_names_both_of_its_outcomes`
(`:114-116`), which then only restates the table. The assertion is the **subset**
direction — `{f"{n}.md" for n in step.produces} <= artifacts_in(produce_section)`
— per the settled criterion 13; see § Notes for why equality was dropped.
— criterion 13

`produces` is deliberately **not** added to `--json`; nothing in the payload
changes in this commit either, so the baselines are a live check a second time.

### 3. `write_draft` on the store

One method on the `WorkStore` ABC beside `write_artifact`
(`tcw/store/base.py:1468`):

```
write_draft(slug, artifact, content, *, force: bool = False) -> str   # the locator
```

`FsWorkStore` implements it (`tcw/store/fs.py`, beside `write_artifact` at
`:3512`): unknown artifact name → `ValueError` naming the legal set, the same
shape `write_artifact` uses; the draft is `<artifact>.draft.md` in the item
folder, the **only** place that literal appears; presence is decided by the
canonical `_present` rule (`fs.py:2217-2221`), not `.exists()`; present and not
`force` → raise carrying the locator in the message; write through
`_atomic_write` (`fs.py:715-727`) then `_stage(p)`; return the locator.

No `read_draft` — nothing reads a draft, and the presence check and the write
are one call.

Tests at store level: writes the file, refuses a present draft leaving it
byte-identical, `force=True` overwrites, an **empty** draft is not present and
is overwritten with no flag, an unknown name raises.

— criterion 9 (the store half), and the mechanics criterion 4 rests on

### 4. Built-in artifact templates

`ARTIFACT_TEMPLATES: dict[str, str]` in a new `tcw/work/templates.py` — a
module-level map of Python strings, not package data. C6 is shipping
`tcw/work/prompts/` as package data for stage prompts; artifact templates need
no wheel work, and a plain dict gives criterion 5's "exactly one definition in
the codebase" for free.

One entry per `WORK_ARTIFACTS` name (eight), each a headings-and-prompts
skeleton derived from the matching stage document's `Produce` section
(`skills/tcw-work/references/stage-*.md`) so the built-in agrees with what the
lifecycle already asks for. `intake`'s is `""`.

Tests: `set(ARTIFACT_TEMPLATES) == set(WORK_ARTIFACTS)` — exact equality, not
"at least one" — and `ARTIFACT_TEMPLATES["intake"] == ""` asserted explicitly.

— criteria 5, 6 (the registry half)

### 5. `tcw work scaffold <artifact> <ref>`

The verb, in `tcw/work/cli.py` with `pscf` beside `pstg` (`cli.py:1300-1310`):
`<artifact>` and `<ref>` both required positionals, plus `--force`. Ordering
exactly as the spec's Design lists it:

1. artifact not in `WORK_ARTIFACTS` → exit 1 naming the legal names
2. item missing or ambiguous → exit 1
3. the real artifact present per `artifacts()` → exit 1 naming it
4. legality: build the stage-for-artifact map by inverting `produces` over
   `LIFECYCLE_STEPS`, look the stage up in `STAGE_STATUSES`
   (`base.py:769-777`), and refuse a status not listed. `intake` is produced by
   no stage — **no lookup, no `KeyError`, legal in every status**
5. resolve through `resolve_artifact` with
   `Builtins(artifact_templates=ARTIFACT_TEMPLATES)`, `execute=True`
6. **fallback**: if no `PlanEntry` in `Resolution.plan` has `matched=True`, no
   binding won and the text is the built-in. A binding that won and resolved to
   empty text keeps its empty text
7. `store.write_draft(...)` — the CLI composes no path and contains no
   `.draft.md` literal
8. the locator on stdout, alone

`ResolveError` → exit 1, stderr, **nothing on stdout**. A `write_draft` failure
after successful resolution → same. Leave the bare `Builtins()` at `cli.py:801`
alone; `stage_prompts` is C6's.

Tests: byte-for-byte draft content and locator-only stdout (1); parametrized
over every `WORK_ARTIFACTS` name that `<name>.md` stays absent and `tcw work
list`'s string is unchanged (2); refusal with a real artifact present **and**
non-refusal when it holds only whitespace (3); refusal on a present draft
leaving it byte-identical, `--force` overwriting, an empty draft not refusing
(4); `scaffold intake` writing an empty draft rather than refusing (6);
parametrized over all of `WORK_ARTIFACTS` on a node with no
`work.lifecycle.artifacts:` key, each draft byte-equal to its built-in (7);
resolve-then-write across four failing kinds — `generate` non-zero exit,
timeout, output-cap, and `file` at a deleted path — each writing no draft and
each succeeding on retry after the fault is fixed, plus an unwritable target
giving exit non-zero, stderr, empty stdout (8); a monkeypatched `write_draft`
recording the call and a grep of the CLI module for `.draft.md` and for a
composed `store.path(...)` draft path (9); `scaffold outcome` on a `backlog`
item exiting non-zero having written nothing and `scaffold intake` succeeding in
every status (15); a `blob` template `when: {tags: [bug]}` above a `builtin`
fallback checked both ways (16).

— criteria 1, 2, 3, 4, 6, 7, 8, 9, 15, 16

### 6. No surface reports a draft

Test-only, and its own task because it spans four surfaces including `serve`,
which C5 changes not at all — the point is that the property already holds and
survives. With **every** draft present and no real artifact: `tcw work list`'s
string unchanged, `artifacts()` all absent, `tcw work show --json`'s `artifacts`
map all `false`, and `serve`'s detail response (`tcw/serve/__init__.py:659`,
which iterates `WORK_ARTIFACTS` through `read_artifact`) listing none of them as
present.

`serve` is not given a scaffolding route, per the spec's decision.

— criterion 14

### 7. Documentation Sync

All four CLAUDE.md entries fire. One pass over the finished diff, at the end:

- **`README.md` [Public-API]** — the `tcw work scaffold` lines in the work
  command block (`README.md:764-773`, beside C4's `tcw work stage` lines,
  including `--force`), and the drafts paragraph in §"Reading a stage's
  instructions" (`README.md:676`): what a draft is, that it is never the
  artifact, the two refusals, and that `generate` templates re-run on retry and
  under `--force` so generators must be side-effect-free. **C7 owns §"Binding
  your own skills and commands to the lifecycle" — do not touch it.**
- **`docs/release-notes/upcoming.md` [Public-API]** — a starting point for a
  lifecycle document, and why `spec.draft.md` is not `spec.md`. Plain language,
  no module names.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — Added: the verb,
  `write_draft`, the built-in template registry. Changed: `produces` →
  `tuple[str, ...]` with `produces_note` carrying the prose and `--json`
  unchanged.
- **`skills/tcw-work/references/commands.md` + `hooks.md`
  [Skill-Driven-Component]** — the row beside `tcw work stage`
  (`commands.md:26`), and in `hooks.md:79-93` how an `artifacts:` binding is
  actually reached, which today documents a binding with no verb behind it.
  `SKILL.md` itself is a thin router that carries no command surface; it changes
  only if the stage/artifact table at `SKILL.md:29-35` needs the draft
  distinction, which is a judgment call at the gate, not a promise here.

Plus the guard criterion 17 asks for: a test that `tcw work scaffold` appears in
the README work command block and in `commands.md`. Note that this guard does
**not** exist today —`tests/test_documented_cli_surface.py` runs the *opposite*
direction (documented verbs must exist), so this is a new assertion, not a
pattern `tcw work stage` already has. Smallest home for it is a positive test
alongside the existing negative one.

— criterion 17

### 8. Capability ledger

`work/customize-lifecycle-artifact-templates` is **new** — declared in this
item's `capabilities.yaml` (seeded at plan), written under
`docs/capabilities/work/` during `implement` with `Subject:`
`work-item/lifecycle-hook` and `work-item/lifecycle-stage`, and flipped by the
completion gate. `tcw capabilities check` and `tcw capabilities drift` clean
afterwards. C7 is consolidation-only and will not do it.

— criterion 18

## Verification

What the suite cannot check, and someone has to look at:

- **The eight templates are worth typing into.** Set equality proves they exist;
  nothing proves a `spec` template is a useful skeleton rather than a heading
  dump. Read all eight, and scaffold one item's full set to see them in place.
- **The draft/artifact distinction reads as obvious.** The whole design rests on
  a user never confusing `spec.draft.md` with `spec.md`. That is a wording
  judgment on the README and release-note text, not an assertion.
- **The refusal messages name something openable.** Criterion 4 pins that the
  locator appears; whether the message tells you what to do next (type into it,
  or `--force`) is a read.
- **Two simultaneous `scaffold` runs race.** A stated limit, not guarded and not
  tested. `_atomic_write` keeps the file untorn; the loser's content wins.
- **`read_artifact` still disagrees with the presence rule** (`fs.py:3478` vs
  `fs.py:2217-2221`). C5 routes around it. It needs a backlog entry at C8, which
  no test will remind anyone about.
- **Every commit boundary is green, not just the last one.** Run the suite at
  each of the eight, and specifically the eleven baselines at tasks 1 and 2.

## Notes

- **Criterion 13 was exact-set equality, and it did not hold. Now settled as
  subset.** Planning ran the assertion against the shipped documents:
  `stage-inbox.md`'s `Produce` names `intake.md`, `stage-request.md`'s names
  `intake.md` and `rollup.md`, `stage-plan.md`'s names `epic-deltas.md` — all
  three legitimately, as prose about what *isn't* produced or as a cross
  reference. `artifacts_in(Produce section) == {f"{n}.md" for n in produces}`
  fails 3 of 7 stages on an unmodified tree, and neither intersecting with
  `WORK_ARTIFACTS` nor restricting to the first paragraph rescues it. The
  coordinating session dropped the "no extra" direction (commit `6ee69bb`)
  rather than edit prose C7 owns: the subset direction is what catches the real
  defect — substring-matching, which let `"spec"` match `specification` — and
  the discarded direction guarded against a documentation error nobody has made.
  C7 may tighten it if its reduction makes equality achievable. **Task 2 is
  unblocked.**
- **The draft-presence refusal happens at write time, not before resolution.**
  The spec's ordered list puts it at step 4 and the Design section puts the
  check inside `write_draft` with no `read_draft` to do it earlier. Both cannot
  be literally true. The Design section wins — it is the one that reasons about
  it — so a `generate` template runs before the refusal is issued. Nothing
  observable changes (exit code, message, and the draft's bytes are all as
  criterion 4 specifies), and the spec's own Risks already accept that
  generators re-run and must be side-effect-free.
- **Task 3 strengthens C4's test for free.**
  `tests/test_stage_verb.py:193-217` collects mutators by prefix off `dir(WorkStore)`,
  so `write_draft` joins the guarded set with no edit — and `tcw work stage`
  still calls none of them.
- **Tasks 3 and 4 are genuinely independent** (the store method needs no
  templates; the registry needs no store). One agent implements, so they are
  sequenced anyway; either order works, and 3-then-4 puts the interface change
  in the smaller, earlier commit.
