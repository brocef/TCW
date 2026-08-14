# Plan — Ship built-in stage prompts with the CLI

Seven tasks, linear. The suite is green at every one of the seven commit
boundaries; §Ordering says why the order is this one and not the obvious one.

## Ordering

The floor is inert while the registry is empty (`builtins.get(sid, "")` → `""` →
`_join` drops it), and `tcw work stage` passes `Builtins()` regardless. That
gives three independent switches — **content**, **floor**, **wiring** — and any
of the six orders is green. The order below is chosen so that each commit is
reviewable on its own terms:

1. **Content before machinery.** Task 1 is ~200 lines of prose and no code. It is
   the part a human reads rather than a test, and it deserves a diff a reviewer
   can read without a loader change in it. It is trivially green — nothing yet
   asserts anything about the files.
2. **Loader before floor.** Criterion 5 asserts the floor returns *the shipped
   text*, so the floor's test wants the real registry, not a fabricated one.
3. **Wiring last of the three.** `cli.py:801` is the switch that changes what a
   user sees; putting it after the floor makes criterion 9 one commit's
   assertion rather than a property that half-existed for two commits.
4. **The `prompt: []` rejection after the floor** (task 5). It is independent of
   all three switches and could land anywhere, but it exists *because* the floor
   makes `prompt: []` ambiguous, and a reviewer reading the commits in order
   should meet the ambiguity before the fix for it.

## Tasks

### 1. The six prompt files, and the packaging that ships them

`tcw/work/prompts/<stage>.md` for `request`, `spec`, `plan`, `implement`,
`verify`, `postmortem`. No `__init__.py`, no `MANIFEST.in`. Plus one line in
`pyproject.toml` beside the existing `"tcw.serve"` entry (`pyproject.toml:27-28`):

```toml
"tcw.work" = ["prompts/*.md"]
```

Each file is condensed from its named source document —
`skills/tcw-work/references/stage-<id>.md` — against the spec's §5 table, which
is the contract and not a summary of it. Per file, the source and the three
imports:

| File | Source | Superpowers import |
| --- | --- | --- |
| `request.md` | `stage-request.md` (70 lines) | none |
| `spec.md` | `stage-spec.md` (70 lines) | none |
| `plan.md` | `stage-plan.md` (68 lines) | `writing-plans` — exact files per task, no placeholders, self-review against the spec |
| `implement.md` | `stage-implement.md` (77 lines) | `test-driven-development` (failing test first, watched fail), `systematic-debugging` (root cause before fix), `verification-before-completion` (no claim without fresh output) |
| `verify.md` | `stage-verify.md` (77 lines) | `verification-before-completion` |
| `postmortem.md` | `stage-postmortem.md` (66 lines) | none |

Three rules that apply to all six, taken from the spec and not re-decided here:

- Every clause in that stage's **"Moves into the prompt"** cell appears; nothing
  from its "Stays in the skill" cell does. That cell is C7's criterion-18
  contract, so an extra clause here is a defect and not a bonus.
- **Step 1 of every source document — "Run `tcw work lifecycle --stage <id>` and
  honor any binding it reports" — is dropped.** It is circular inside a prompt
  that *is* what that reports (spec §Notes).
- Sub-skill names do not appear. The prompt states the obligation
  ("evaluate every Documentation Sync entry in `AGENTS.md` against the finished
  diff"); the skill names what discharges it.

**One task, not six.** The set-equality assertion in task 2 is over
`set(STAGE_IDS) - {"inbox"}`, so a per-file commit would be red until the sixth —
and six commits of prose with no code between them buy nothing a single reviewed
diff does not.

— no criterion alone; the substrate for 1, 2, 5, 6, 7, 8, 9

### 2. `shipped_builtins()` and the tests that bound it

One cached function in `tcw/work/resolve.py`, beside the `Builtins` it fills:

- reads `importlib.resources.files("tcw.work") / "prompts" / f"{sid}.md"` for
  each `sid` in `sorted(set(STAGE_IDS) - {"inbox"})` — the derivation, never a
  literal list, so adding a stage to `STAGE_IDS` without its file fails here
- a missing file, or one that is empty after `strip()`, raises `ResolveError`
  naming the stage **and** the package path. Not a quiet `""`: a broken install
  saying nothing is exactly what criterion 14 exists to catch
- returns **one** `Builtins` carrying both registries: `stage_prompts` from the
  six files, `artifact_templates` from C5's `ARTIFACT_TEMPLATES`
  (`tcw/work/templates.py`, C5's, landing ahead of this item). C5's dict stays the single
  definition its criterion 5 requires; only the *construction* moves here. See
  §Notes — this is the coordination item, and C6 absorbs it because C5 landed
  first
- `@functools.cache`, so six small reads happen at most once per process

Matches `tcw/serve/runtime.py:18`, the only package-data reader in the codebase;
not a path composed from `__file__`, which breaks under a zipimport-style
install.

Tests, in a new `tests/test_shipped_prompts.py`:

- `set(shipped_builtins().stage_prompts) == set(STAGE_IDS) - {"inbox"}`, and
  `"inbox" not in` it — asserted as that derivation — criteria 1, 3 (registry half)
- each value non-empty after `strip()` and ≥ 15 non-blank lines — criterion 2
- each value ≤ 40 lines (`len(text.splitlines())`) — criterion 8. Read through
  the loader, not by globbing the source tree, so it holds in an installed tree
- **the installed wheel.** `pip wheel --no-deps --no-build-isolation -w
  <tmp_path> <repo>`, then `zipfile.ZipFile`: the set of members matching
  `tcw/work/prompts/*.md` equals the same six ids, and each member's decoded
  content is non-empty. Reading the zip rather than installing it is what proves
  the content survives zipimport. Default suite, **no marker** — measured below
  — criterion 7
- **the condensation guards**, two greps over the six texts, both cheap and both
  catching a real regression rather than a style: no text contains
  `tcw work lifecycle --stage` (the dead step), and none contains
  `tcw-verifier`, `documentation-sync`, or `tcw-capabilities` (the three sub-skill
  names §5 assigns to the skill) — partial cover of §5; the rest is Verification

No test in this file invokes `tcw work stage` — criterion 4.

— criteria 1, 2, 3 (registry half), 4, 7, 8

### 3. The floor in `resolve_prompts`

In `resolve_prompts` (`resolve.py:189-209`), before the loop: when
`policy.stage(stage_id)` is empty, resolve as if it were `[Binding(builtin)]` —
one synthesized binding, appended to `res.plan` as a real `PlanEntry("builtin",
…, matched=True, executed=False)` so `tcw work stage --no-exec` reports the
built-in it is about to print instead of printing a plan with nothing in it.

**The condition is on the binding list, not on the resolved text.** A stage whose
only binding carries a `when:` that did not match resolves to nothing, *not* to
the built-in — the node configured that stage, and §3's "a stage the node
configures wins outright" is the rule. `tests/test_resolve.py:61-68` is the
existing case and it keeps its current answer.

Not in `LifecyclePolicy.stage()` and not in `cli.py`'s `_stage`, for the two
reasons §3 gives.

Tests, added to `tests/test_resolve.py`:

- a `LifecyclePolicy()` configuring nothing, over all six stages, returns the
  shipped text for each — criterion 5 (the floor half)
- `prompt: [{blob: "X"}]` returns `"X"` alone, the built-in absent — criterion 5
  (the "wins outright" half)
- `prompt: [{builtin: true}, {blob: "X"}]` returns shipped-text + `"\n\n"` + `"X"`,
  byte-for-byte, per `_join` — criterion 6
- a stage bound only by a non-matching `when:` returns `""` — the boundary above,
  pinned so a later reading cannot widen the floor by accident

`tests/test_resolve.py:179-186` (`builtin` with an empty registry resolves to
nothing) passes **unmodified** — it passes `Builtins()` explicitly. So does every
other existing case in the file — criterion 10.

— criteria 5, 6

### 4. `tcw work stage` passes the shipped builtins

`cli.py:801`: `Builtins()` → `shipped_builtins()`, inside the existing
`try:`/`except ResolveError` block so a broken install exits 1 with the loader's
message on stderr and nothing on stdout, matching every other failure this verb
has.

Tests, added to `tests/test_stage_verb.py`:

- on a node with **no `work.lifecycle` key**, `tcw work stage <id> <ref>` exits 0
  and stdout equals the shipped text for each of the six stages — criterion 9
- `tcw work stage inbox <ref>` still exits 1, stdout empty, "runs before an item
  exists" on stderr — re-asserted rather than assumed — criterion 3 (verb half)

No existing test in the file changes. Verified before planning: nothing asserts
empty stdout for a *legal* stage on an unconfigured node —
`test_every_illegal_pair_is_rejected_and_every_legal_one_accepted`
(`test_stage_verb.py:109-110`) asserts it only on the `not legal` branch, and
every prompt-text test configures its stage explicitly — criterion 10.

— criteria 3 (verb half), 9

### 5. `prompt: []` is a validation error, in both spellings

In `_parse_stage` (`base.py:954-984`), the one place both spellings arrive.

- the legacy bare list (`:965-968`): `isinstance(raw, list) and not raw` →
  append a problem
- the explicit key (`:982-984`): `raw.get("prompt") is not None` already
  distinguishes written-but-empty from absent, which is the fact resolution
  loses; empty → append a problem

One message, naming the stage and saying what to write instead — a stage that
should say nothing binds `{blob: ""}`. Nothing in the model changes: no field on
`StageBindings`, no change to `LifecyclePolicy`. `raw["pre"]` is untouched.

Tests, added to `tests/test_lifecycle_validation.py`:

- `{"stages": {"spec": []}}` → one problem naming `spec` and `blob` — the legacy
  spelling
- `{"stages": {"spec": {"prompt": []}}}` → the same — the explicit spelling
- `{"stages": {"spec": {"pre": []}}}` → **no problem**, asserted so the check
  cannot overreach into a different key
- a non-empty list in either spelling still clean
- resolution is separate: a policy parsed from `{"stages": {"spec": []}}` still
  returns the built-in through `resolve_prompts`, because the parser's problem
  list is advisory and `FsWorkStore.lifecycle_policy` discards it (`fs.py:2639`)

**The legacy corpus.** `tests/fixtures/lifecycle_baseline/stage_empty.config.yaml`
is literally `stages: {spec: []}`, and `everything.config.yaml` carries
`implement: []` — the configs that validated before this change and must now
fail. Their recorded baselines stay **byte-identical and unedited**:
`test_lifecycle_baseline.py` replays only `tcw work lifecycle`, which reads the
policy through `lifecycle_policy()` and discards problems. No test anywhere runs
`tcw validate` over those fixtures (grepped). So the corpus needs no new fixture
— it needs the assertion that closes the loop, added to
`tests/test_lifecycle_validation.py`: load `stage_empty.config.yaml` from the
corpus directory by path and assert `parse_lifecycle_policy` now reports the
problem, and that its baseline `tcw work lifecycle` render is still the one on
disk. That is what pins the break to a config that demonstrably existed before
it, rather than to one written to fail.

— criterion 13

### 6. Documentation Sync

All four CLAUDE.md entries evaluated; three fire, one is a recorded no-edit. One
pass over the finished diff, at the end.

- **`README.md` [Public-API]** — fires. Two edits, both already located:
  `README.md:637` ("`builtin: true` is TCW's own default for that stage or
  artifact") must say TCW *ships* defaults for the six lifecycle stages and that
  an unconfigured stage resolves to them; the `tcw work stage` paragraph
  (`README.md:676-683`) must say that with nothing configured it prints TCW's own
  instructions. Also `README.md:672-673` ("Your existing configuration keeps
  working exactly as it did") is now false for one spelling and needs the
  `prompt: []` carve-out. **C5 owns the drafts paragraph in the same section and
  C7 owns §"Binding your own skills and commands to the lifecycle" — do not
  touch either.**
- **`docs/release-notes/upcoming.md` [Public-API]** — fires. §"Asking TCW what to
  do at a stage" (`:89`) already claims the instructions are "TCW's own by
  default", which is false today; C6 makes it true and adds which six stages ship
  defaults, that `inbox` does not, and that configuring a stage replaces them
  while `builtin: true` composes them back. Plus the **upgrade sentence** for the
  one back-compat break, which also corrects `:131` ("A stage id with a plain
  list …"): `prompt: []` and a bare `stages.<id>: []` are now validation errors,
  and a stage that should say nothing binds `{blob: ""}`.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — fires. *Added*: the six
  prompt files as package data, `shipped_builtins()`, the `"tcw.work"`
  package-data key, the unconfigured-stage floor in `resolve_prompts`, the wheel
  test. *Changed*: `tcw work stage` passes the shipped builtins; an unconfigured
  stage resolves to the built-in. *Removed*: `prompt: []` as a legal spelling,
  both forms.
- **`skills/tcw-work/**` [Skill-Driven-Component]** — **fires, and the answer is
  no edit.** The epic assigns "stage docs → routers" and "`hooks.md` rewritten"
  to C7; editing them here means editing them twice. Nothing becomes *wrong* —
  `hooks.md:31` already says "`builtin: true` is TCW's own default", which C6
  makes true, and the six stage documents stay accurate while becoming redundant,
  which is the state C7 resolves. Recorded here rather than silently skipped, and
  restated in `outcome.md`.

— criterion 11

### 7. Capability ledger

`work/run-a-lifecycle-stage` (`cap-f42255`) is **revised, not created** — status
stays `Supported`, so this item's `capabilities.yaml` uses `changed:` and not
`new:` (`base.py:112-122`; the completion gate at `recursion.py:59-64` only
requires a `changed:` entry to resolve, where a `new:` one must also be off
`Missing`). Seeded at plan; the prose edit lands during `implement`.

The revision, from `spec.md` §"Capability changes": with nothing configured for a
stage, TCW prints its own instructions for that stage — the six lifecycle stages
it ships defaults for, `inbox` excluded. A stage the project configures replaces
them; `builtin: true` in that stage's `prompt:` list puts them back and composes
them with the project's own.

`work/configure-the-work-lifecycle` (`cap-b9711e`) is **not** edited: it already
promises `builtin: true` composes rather than replaces, and C6 makes that
sentence true rather than changing what it claims. `tcw capabilities check` and
`tcw capabilities drift` clean afterwards.

— criterion 12

## Verification

What the suite cannot check, and someone has to look at:

- **The six prompts are worth reading at every stage entry.** Set equality, 15
  lines, and 40 lines prove they exist and are bounded. Nothing proves
  `implement.md` is instructions rather than headings. Read all six against their
  source documents with the §5 table open, cell by cell — that table is the only
  control on what was dropped, and a missing clause is invisible to every test
  here.
- **40 lines is tight for `verify` and `implement`.** Their "Moves into the
  prompt" cells carry ~12 clauses each. If a prompt cannot hold its cell in 40
  lines, the honest answers are to tighten the prose or to escalate the ceiling —
  **not** to move a clause into the "stays in the skill" column, which would
  silently hand C7 a contract nobody agreed to.
- **The prompts read as instructions to an agent with no plugin installed.** The
  whole item exists for the Codex user driving `tcw` directly. A dangling
  reference — a skill name, a `references/` path, a board letter — is a defect
  the length tests cannot see. Read one prompt as if the plugin did not exist.
- **The wheel test needs `pip` and `setuptools` in the environment.** With
  `--no-build-isolation` there is no network fetch, but a stripped CI image
  without `setuptools` fails the test rather than skipping it. Deliberate — a
  silent skip on the one criterion that checks packaging is worse than a red.
- **sdist parity is untested**, per the spec's Risks. `pip install` from an sdist
  is the exotic-platform path; setuptools includes `package-data` in sdists and
  `tcw.serve` has shipped that way for several releases. Named, not asserted.
- **Every commit boundary is green, not just the last.** Run the full suite at
  each of the seven, and specifically `tests/test_lifecycle_baseline.py` (eleven
  cases + this repo's own node) at task 5, which is the one task that can move a
  baseline.
- **`tcw work stage` on this repo, by hand, for all six stages** after task 4 —
  the demonstration criterion 9 automates, run once against the real node whose
  `tcw-config.yaml` has no `work.lifecycle` key at all.

## Notes

- **C5 lands first, so C6 absorbs the consolidation.** C5's plan (task 4) puts
  `ARTIFACT_TEMPLATES` in a new `tcw/work/templates.py` and (task 5) calls
  `resolve_artifact` with an inline `Builtins(artifact_templates=ARTIFACT_TEMPLATES)`
  at the `tcw work scaffold` call site. That is a **second construction site**,
  which this item's spec §Notes ("Coordination with C5") rules out: two places
  building two different `Builtins` is how `spec`'s prompt and `spec`'s template
  end up resolved from different places. C6 is the one that can fix it, because
  C6 is the one introducing the function.

  So task 2 does two things rather than one: `shipped_builtins()` returns a
  `Builtins` carrying **both** registries, and the `scaffold` call site is
  repointed to it — an import and one argument. **`tcw/work/templates.py` and
  `ARTIFACT_TEMPLATES` are not moved, renamed, or edited**; C5's dict remains the
  single definition its criterion 5 asserts, and C5's own tests over it keep
  passing untouched. Task 2's set-equality test gains a one-line companion:
  `shipped_builtins().artifact_templates is ARTIFACT_TEMPLATES` (or equals it),
  which is what stops a third construction site appearing later.

  C5's plan note "leave the bare `Builtins()` at `cli.py:801` alone —
  `stage_prompts` is C6's" is honoured: task 4 replaces it.
- **The floor's plan entry is a real entry, not a hidden one.** `--no-exec` prints
  `res.plan` to stderr (`cli.py:812-816`); a floor that resolves text while
  contributing no entry would make the dry run understate what the real run
  prints, which is the one thing `--no-exec` exists to prevent.
- **The `prompt: []` break is one-directional and contained.** `stages.<id>.pre`,
  `transitions.<id>.pre`, and `transitions.<id>.post` all keep accepting `[]`;
  `transition_empty.config.yaml` in the corpus is `pre: []` / `post: []` and stays
  clean. Task 5's third test is what stops a later tidy-up from generalizing the
  check to "any empty binding list".
