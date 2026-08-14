# Spec — Ship built-in stage prompts with the CLI

Child **C6** of `2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`.

## Capability changes

The epic's `plan.md` lists no capability delta for C6. **That is wrong**, and the
ledger is the evidence.

`work/run-a-lifecycle-stage` (`cap-f42255`, Supported — C4's, already shipped)
says today:

> TCW checks the stage makes sense for where the item is, runs whatever `pre`
> checks the project configured, resolves the stage's prompt bindings, and prints
> the instructions.

Every clause is about *the project's* configuration. On a node that configures
nothing — which is TCW's own repo; `tcw-config.yaml` has no `work.lifecycle` key
at all — the command exits 0 and prints nothing. Verified by running it:

```
$ tcw work stage spec 2026-08-12-ship-built-in-stage-prompts-with-the-cli
$ echo $?
0
```

C6 changes what a user gets from a command they already have, on a node they have
not touched. That is a user-facing capability change, so:

**Planned delta (no records written at this stage):**

| Capability | Delta |
| --- | --- |
| `work/run-a-lifecycle-stage` | **Revise** (status stays `Supported`). Add: with nothing configured for a stage, TCW prints its own instructions for that stage — the six lifecycle stages it ships defaults for, `inbox` excluded. A stage the project configures replaces them; `builtin: true` in that stage's `prompt:` list puts them back and composes them with the project's own. |

**No other capability changes.** `work/configure-the-work-lifecycle` (`cap-b9711e`)
already promises "`builtin: true` is TCW's own default so I can add to it rather
than replace it" — C6 makes that sentence true rather than changing what it
claims, so its record needs no edit. No capability is created, retired, or
changes status.

## Problem

An agent knows how to run a lifecycle stage only because a *skill* told it. The
methodology lives in `skills/tcw-work/references/stage-*.md`, which is plugin
packaging: a Codex user without the plugin, or anyone driving `tcw` directly,
gets the state machine and none of the judgment for operating it.

C3 built the mechanism and shipped it empty. `Builtins` has two registries
(`resolve.py:29-40`) and its own docstring says "C6 fills `stage_prompts`";
`_resolve_one` returns `builtins.get(hook_id, "")` for a `builtin` binding
(`resolve.py:154-155`); C3's outcome records that "`builtin` resolves to nothing
until C5 and C6 fill the two registries … between now and then it is
indistinguishable from 'not configured'."

Two things are therefore missing, not one:

1. **The content.** No `tcw/work/prompts/` directory exists, and the wheel
   currently contains no `.md` file at all (verified by building one:
   `pip wheel --no-deps --no-build-isolation .` produces 33 members, none ending
   in `.md`).
2. **The floor.** `LifecyclePolicy.stage(sid)` returns `[]` for a stage the node
   never configured (`base.py:641-650`), so `resolve_prompts` iterates nothing
   and returns empty text — *whatever* is in the registry. Filling the registry
   changes nothing for an unconfigured node. And `tcw work stage` passes
   `Builtins()` — the empty default — at `cli.py:800-803`, so even a node that
   writes `builtin: true` explicitly gets nothing.

Criterion 14 is stated as "**with nothing configured**, `tcw work stage <id>`
prints built-in instructions". Content alone does not satisfy it. See `## Notes`.

## Goals

1. TCW ships condensed stage instructions for `request`, `spec`, `plan`,
   `implement`, `verify`, and `postmortem`, as package data that survives into an
   installed wheel.
2. A node that configures nothing gets them. A node that configures a stage's
   prompts replaces them, and `builtin: true` composes them back in.
3. Each prompt is short enough to be read at every stage entry, and stays short —
   enforced, not hoped for.
4. The split between what the CLI carries and what the `tcw-work` skill keeps is
   decided here, per stage, so C7's criterion 18 ("the routers must not restate
   what the prompts say") is a checkable claim rather than an aspiration.

## Non-goals

- **Artifact templates.** `Builtins.artifact_templates` stays empty; that is C5
  and epic criterion 17. C6 touches the `stage_prompts` registry only.
- **Rewriting the skill.** The seven `skills/tcw-work/references/stage-*.md`
  documents and `hooks.md` are not edited here. C7 owns that reduction, and doing
  it twice is waste. See `## Design → Documentation`.
- **New CLI surface.** No new command, no new flag, no new config key.
- **Changing the stage or artifact registries.** `STAGE_IDS`, `LIFECYCLE_STEPS`,
  `STAGE_STATUSES`, and `WORK_ARTIFACTS` are unchanged.
- **A prompt for `inbox`.** It runs before an item exists; `tcw work stage inbox`
  is already refused with that reason (`cli.py:763-769`).
- **sdist parity.** The wheel is the artifact under test. See `## Risks`.

## Design

### 1. Which stages ship a prompt

Derived from the shipped registry, not from the epic. `STAGE_IDS`
(`base.py:522`) is:

```python
("inbox", "request", "spec", "plan", "implement", "verify", "postmortem")
```

and `STAGE_STATUSES` (`base.py:769-777`) gives `inbox` an empty tuple — the one
stage with no status it is legal in, because it runs before an item exists.

**The set is `set(STAGE_IDS) - {"inbox"}` — six stages.** This matches criterion
14's enumeration exactly. It is expressed as that derivation rather than as a
literal list so that adding a stage to `STAGE_IDS` without writing its prompt
fails the suite, which is the failure worth having.

### 2. Where the content lives and how it loads

`tcw/work/prompts/<stage>.md`, one file per stage, six files.

**Packaging:** a `[tool.setuptools.package-data]` entry,
`"tcw.work" = ["prompts/*.md"]`, beside the existing `"tcw.serve"` entry
(`pyproject.toml:27-28`). No `__init__.py` in `prompts/`, no `MANIFEST.in`, no
build-backend change. This is the shape already proven in this repo: `tcw.serve`
is a package, `dist/` is a plain subdirectory of it, and its files reach the
wheel through the same mechanism (verified — `tcw/serve/dist/client/assets/…` is
in the built wheel).

**Loading:** `importlib.resources.files("tcw.work")` traversed to
`prompts/<stage>.md`, matching `tcw/serve/runtime.py:18`, which is the only
package-data reader in the codebase today. Not a path composed from `__file__`:
that assumes an unpacked directory on disk and breaks under a zipimport-style
install, and `Traversable.read_text()` works either way.

**Litmus test.** This is CLI package data — TCW's own shipped text, keyed by
stage id — not store data. No store path is composed, no node folder is read, and
a `JiraWorkStore` would resolve the identical six strings, because the text is
TCW's and not the project's. It belongs where `Builtins` already put it. ✓

**API:** one function in `tcw/work/resolve.py`, beside the `Builtins` it fills,
returning a `Builtins` with `stage_prompts` populated and `artifact_templates`
empty. Cached, so six small reads happen at most once per process. A stage whose
file is missing or empty is a **loud failure naming the stage and the package
path**, not a silently absent prompt — a broken install should say so, and a
quiet empty string is exactly the failure criterion 14 exists to catch.

C5 fills `artifact_templates` by extending this same function rather than adding
a second one; recorded in `## Notes` as a coordination item.

### 3. The floor

`resolve_prompts` (`resolve.py:189-209`) resolves a stage with **no prompt
bindings** as if it bound `[{builtin: true}]`.

Consequences, stated so they are not discovered later:

- A stage the node configures wins outright — the built-in appears only if the
  node writes `builtin: true`. This is the "floor, not a ceiling" the request
  asks for, and it is what the ledger already promises.
- An explicitly empty prompt list (`prompt: []`, or the legacy bare
  `stages.<id>: []`) is indistinguishable from an absent one after parsing —
  `StageBindings` records no "was `prompt:` written" flag — so it also gets the
  built-in. Accepted rather than designed around; see `## Risks`.
- `tcw work lifecycle` is untouched. It reports the policy directly and resolves
  nothing, so an unconfigured stage still reports no bindings there.

**Why `resolve_prompts` and not elsewhere:**

- Not `LifecyclePolicy.stage()` (`base.py:641`): that accessor feeds validation
  and `tcw work lifecycle`'s directive rendering as well, so a synthetic binding
  there would make `lifecycle` report a `builtin` nobody configured, and would
  perturb the back-compat recordings for no gain.
- Not `_stage` in `cli.py`: criterion 14 must be testable against C3's resolution
  library rather than through `tcw work stage` (the request's constraint 4), and
  a floor that only exists inside the verb cannot be. It would also be invisible
  to C7 and to any later caller.

**Blast radius on C3's and C4's existing tests: none.** The floor is inert while
the registry is empty (`Builtins()` still resolves a `builtin` to `""`), so
`tests/test_resolve.py:180-186` and its neighbours are unaffected. Every prompt
assertion in `tests/test_stage_verb.py` configures its stage explicitly
(`test_stage_verb.py:146-157` and the `--no-exec` block), so the floor does not
apply to any of them.

### 4. Wiring the verb

`cli.py:800-803` passes `Builtins()`. It must pass the loaded builtins. One
argument, one line — the only change C6 makes to C4's code.

### 5. The condensation contract

The rule, applied uniformly, then the per-stage table.

**Moves into the CLI prompt** — the methodology any agent needs, plugin or not:
purpose; the inputs to read; the artifact to produce and its required sections;
the handful of steps that change behaviour; the `tcw` commands the stage is
gated on; and the "exit badly" branches that redirect to another stage.

**Stays in the `tcw-work` skill** — five categories, each with a reason:

1. **Delegability** ("this stage is delegable", `tcw-verifier`, `delegation.md`).
   It is a property of the harness the agent runs under, not of the stage.
2. **`[gated]` / `[judgment]` markers.** Skill notation. The *commands* they mark
   (`tcw work start`, `rework`, `--blocked-by`) move to the CLI; the annotation
   does not.
3. **Epic and cross-node deltas.** `type: epic` differences, child boundaries,
   `tcw work reconcile`, rollups. Conditional detail the router loads on demand.
4. **Sub-skill names.** `REQUIRED SUB-SKILL: Use tcw-capabilities`,
   `Use documentation-sync`. **The CLI states the obligation, the skill names the
   thing that discharges it** — a prompt that says "invoke the documentation-sync
   skill" is a dangling reference for a user without the plugin, whereas
   "evaluate every Documentation Sync entry in `AGENTS.md` against the finished
   diff" is actionable for anyone.
5. **Store mechanics and cross-references.** Board letters, `rollup.md`, links to
   other reference documents, `tcw serve` caveats.

**Imported from superpowers** only where TCW's stage documents are silent. Three
places, named here so the implementation does not shop for more:

- `plan` — from `writing-plans`: each task names the exact files it creates or
  modifies; **no placeholders** ("TBD", "add error handling", "similar to Task
  N"); a self-review pass over the finished plan against the spec for coverage
  gaps and inconsistent names. TCW's `stage-plan.md` says tasks name "what it
  changes and how it is verified" and stops there.
- `implement` — from `test-driven-development` and `systematic-debugging`: write
  the failing test and watch it fail before the code; find the root cause before
  the fix. Neither appears anywhere in TCW's stage documents.
- `implement` and `verify` — from `verification-before-completion`: no completion
  claim without output from a command run now. TCW says "the suite is green"
  without saying who proved it.

Nothing else is borrowed. `brainstorming`'s path classification, the plan-header
template, and the execution-handoff menu are superpowers' own workflow, not
TCW's.

**Per stage** (source document → prompt; "drops" are things C7's router may keep,
"loses" are things nobody keeps):

| Stage | Moves into the prompt | Stays in the skill | Deliberately lost |
| --- | --- | --- | --- |
| `request` | Purpose; `intake.md` as input; produce `initial-request.md` with a title and enough that someone resuming cold knows what was wanted, optional `## Notes` and `## References` with a one-line *why* each; ask the user what is unclear; ask for reference material and record "asked; none provided"; write in the requester's terms without specifying a solution; record constraints, deadlines, out-of-scope; commit alone; all three exit-badly branches. | Not delegable, and why; the epic's coordination goal. | Board-letter `R` mechanics and the `reconcile`/`rollup.md` explanation — TCW-internal trivia that changes nothing an agent does. |
| `spec` | Purpose (what, not how); read the request's `## References`, and treat their absence *without* an "asked; none provided" note as "nobody asked"; produce `spec.md` with the seven required sections named; ground every claim about current behaviour in code with file and line; acceptance criteria checkable by someone else; state non-goals; sweep for sibling defects repo-wide or say why narrowed; commit before planning; all three exit-badly branches. | Delegability and its context brief / return contract; the epic's Design-for-child-boundaries substitution; `decompose.md` and `epic-deltas.md` routing; the `tcw-capabilities` skill name (obligation moves, name stays). | Nothing. |
| `plan` | Purpose; inputs; produce `plan.md` with ordered tasks — each naming the exact files it touches and what proves it — a Documentation Sync block scheduled **last**, and a Verification section for what the suite cannot check; order so the suite is green at every commit boundary; isolate the riskiest change; record dependencies as `tcw work edit <slug> --blocked-by <ref>`, not prose; no placeholders; self-review against the spec; commit before `start`; all three exit-badly branches. | Delegability; the epic coordination-plan variant; the `documentation-sync` skill name; the bounded-DAG-of-stage-documents paragraph (router mechanics). | Nothing. |
| `implement` | Purpose; inputs, with `rework.md` as what makes a second pass different; `tcw work start <slug>` **before the first code edit**; work the plan's tasks in order, committing each; failing test first, and watch it fail; root cause before fix; when the code disproves the plan, fix the plan and say so; once every task is done and the suite is green — and not before — evaluate the project's Documentation Sync entries once over the whole diff and commit docs separately; no completion claim without fresh command output; produce `outcome.md` (what shipped task by task with commit refs, the test result, what the plan or spec got wrong); all three exit-badly branches. | Delegability, and that this is where it pays; the two sub-skill names. | The "the version cut is not part of this" aside — the point survives in `verify`, where the cut actually is. |
| `verify` | Purpose (the user's decision, not "tests pass"); inputs — spec, outcome, and the diff; produce **exactly one** of `refined-outcome.md` / `rework.md`, never both, and delete `refined-outcome.md` on the rejection path because `tcw work rework` refuses while it is present; optional `tcw work submit`; assess the diff against the acceptance criteria and run the checks; **present and stop for the user's decision**; write the verdict artifact and commit; `tcw work rework` on rejection, `tcw work complete` on acceptance; offer a post-mortem if serious unforeseen problems surfaced, only on assent; on acceptance, after `complete`, offer a version cut if the change set warrants one — the user's call, never during implementation; all three exit-badly branches. | The `tcw-verifier` agent and the Claude/Codex delegation split; the capability sub-skill name; the mechanics of the version cut (the option menu, the unpushed-tag case, `/tcw-cut-version`). | Nothing. |
| `postmortem` | Purpose (where would this have been cheapest to catch — not blame, not a summary); read the spine backwards, `## Notes` across it as the primary trail; produce `post-mortem.md` with what went wrong, which stage could first have caught it, what would have had to be different, and whether that change is worth making; distinguish "nobody could have known" from "nobody checked"; create follow-up items; **out-of-band** — never changes status, legal in `review` and after `completed`, never a gate, not on a discarded item; both exit-badly branches. | Delegability. | Nothing. |

The right-hand columns are the C7 contract: what is in **"Moves into the prompt"**
is what C7's routers must not restate.

### 6. Length

Each prompt is **at most 40 lines and at least 15 non-blank lines**, asserted by
a test.

A ceiling that is only a review convention erodes: each edit adds two defensible
lines and in a year the prompt is the stage document again, which is the exact
regression this item exists to undo. The floor catches a stub or a truncated
write. Neither number is a quality judgement — that is what review is for.

### 7. Documentation

C6's own Documentation Sync obligations, per `CLAUDE.md`:

- **`README.md`** [Public-API] — two edits. The "Six kinds" paragraph
  (`README.md:633-640`) says "`builtin: true` is TCW's own default for that stage
  or artifact" (`README.md:637`); it must say TCW ships defaults for the six lifecycle stages and
  that an unconfigured stage resolves to them. The `tcw work stage` paragraph
  (`README.md:676-683`) must say that with nothing configured it prints TCW's own
  instructions.
- **`docs/release-notes/upcoming.md`** [Public-API] — the shipped section "Asking
  TCW what to do at a stage" already claims the instructions are "TCW's own by
  default", which is false today. C6 makes it true and adds which six stages ship
  defaults, that `inbox` does not, and that configuring a stage replaces them
  while `builtin: true` composes.
- **`docs/changelogs/upcoming.md`** [Any-Code-Change] — *Added*: the prompt files
  as package data, the loader, the `pyproject` package-data key, the
  unconfigured-stage floor in `resolve_prompts`, and the wheel test. *Changed*:
  `tcw work stage` passes the shipped builtins.
- **`skills/tcw-work/**`** [Skill-Driven-Component] — **no edit.** The trigger
  fires, and the answer is that C7 owns it: the epic assigns "stage docs →
  routers" and "`hooks.md` rewritten" to C7, and editing them here means editing
  them twice. Nothing in the skill becomes *wrong* — `hooks.md:31` already says
  "`builtin: true` is TCW's own default", which C6 makes true; the stage
  documents stay accurate and become redundant, which is precisely the state C7
  resolves. Recorded rather than silently skipped.

## Acceptance criteria

1. **Exact set equality.** The stage-prompt registry the loader returns has key
   set exactly `set(STAGE_IDS) - {"inbox"}`, asserted as set equality against
   that derivation, not as membership of a hand-written list.
2. **Non-empty content.** For each of those six keys the resolved text is
   non-empty after `strip()` and is at least 15 non-blank lines. A file that
   exists and is empty fails.
3. **`inbox` ships none.** `"inbox"` is not a key in the registry, and
   `tcw work stage inbox <ref>` still exits 1 with "runs before an item exists"
   on stdout-empty (unchanged behaviour, re-asserted).
4. **Resolution through C3's library, not through C4's verb.** Criteria 1–2 and 5
   are tested by calling `resolve_prompts` directly with the shipped builtins;
   no test for them invokes `tcw work stage`.
5. **The floor.** With a `LifecyclePolicy` that configures nothing,
   `resolve_prompts(policy, <stage>, item, …, shipped_builtins())` returns the
   shipped text for each of the six stages. With a policy that binds
   `prompt: [{blob: "X"}]` for a stage, it returns `"X"` alone — the built-in
   does not leak in.
6. **Composition.** With `prompt: [{builtin: true}, {blob: "X"}]`, the result is
   the shipped text, then a blank line, then `"X"` — declaration order, per
   `_join` (`resolve.py:177-186`).
7. **Installed-wheel packaging.** A test builds a wheel from the repo
   (`pip wheel --no-deps --no-build-isolation`, no network, measured at 0.8s on
   this machine — fast enough for the default suite, no marker) and asserts the
   set of `tcw/work/prompts/*.md` members inside the `.whl` equals the same six
   stage ids, and that each member's decoded content is non-empty. Reading the
   zip rather than installing it also proves the content survives a
   zipimport-style install. A source-tree-only check does not satisfy this.
8. **Length ceiling.** Each of the six files is at most 40 lines.
9. **End to end, unconfigured.** In a node with no `work.lifecycle` key,
   `tcw work stage <id> <ref>` exits 0 and prints the shipped text on stdout for
   each of the six stages. (Depends on C4, which has already shipped; it is the
   demonstration, not the proof — criteria 1–8 stand without it.)
10. **Nothing regressed.** The existing suite passes unchanged: no edit to
    `tests/test_resolve.py`, `tests/test_stage_verb.py`, or
    `tests/test_lifecycle_*.py` is required to make it green.
11. **Documentation.** The four Documentation Sync items in `## Design → 7` are
    done, including the recorded no-edit decision for `skills/tcw-work/`.
12. **Capability.** `work/run-a-lifecycle-stage` carries the revised wording from
    `## Capability changes`, and `tcw capabilities check` and
    `tcw capabilities drift` are clean.

## Risks

- **The floor is a change to C3's resolution library, which the epic said C6
  would not touch.** Mitigated by scope: one condition in one function, inert
  while the registry is empty, with no existing test edited. Escalated in
  `## Notes` rather than absorbed silently.
- **`prompt: []` stops meaning "nothing".** A node that spelled an opt-out as an
  explicit empty list now gets TCW's default, because parsing cannot tell it from
  an absent key. No such node is known — TCW's own config has no `work.lifecycle`
  at all, and the epic's back-compat table introduced that row to describe
  `tcw work lifecycle`'s directive rendering, which is unchanged. The alternative
  is a new field on `StageBindings` to record whether `prompt:` was written,
  which is model surface bought for a hypothetical user. Documented in the
  release notes instead.
- **Condensation drops something load-bearing.** The per-stage table is the
  control: anything not in a "moves" cell is in a "stays" or "lost" cell, so a
  reviewer can find the omission rather than notice its absence. C7's criterion
  18 re-checks the same seam from the other side.
- **The prompts and the stage documents disagree between C6 and C7.** They will
  overlap in that window by construction. Overlap is not contradiction, and C7 is
  blocked on C6 precisely so the reduction reads the shipped text.
- **sdist parity is untested.** `pip install` from an sdist is the path a user on
  an exotic platform takes. setuptools includes `package-data` in sdists too, and
  the `tcw.serve` precedent has shipped through PyPI for several releases, so the
  wheel check is the one that earns its runtime. Named rather than assumed.
- **Prompt text is duplicated judgement.** Six markdown files now say things
  `CLAUDE.md` and the skill also say. That is the trade the epic chose — the CLI
  must stand alone for a Codex user — and the length ceiling bounds the cost.

## Notes

### Escalation: shipping content alone does not satisfy criterion 14

The epic's child-boundary table says C6 delivers "`tcw/work/prompts/*.md`
**content** and wheel packaging only — the `builtin` kind itself is C3's", and
the request repeats it. Against the shipped code that is not sufficient:

- `LifecyclePolicy.stage()` returns `[]` for an unconfigured stage
  (`base.py:641-650`), so nothing resolves a `builtin` unless the node asked for
  one by name. Criterion 14's "with nothing configured" is unreachable.
- `tcw work stage` constructs `Builtins()` — the empty default — at
  `cli.py:800-803`, so even an explicit `builtin: true` resolves to `""`.

Neither is a defect in C3 or C4: C3's `Builtins` docstring says "C6 fills
`stage_prompts`", and C4 wired the only value that existed when it shipped. They
are the seam the epic did not cost. C6 therefore makes **two code changes it was
not scoped for** — the floor in `resolve_prompts` and the argument at
`cli.py:801` — and this is an **epic amendment**, following the precedent C4 set
("a child overruling its epic quietly is how the epic stops being the source of
truth — so the epic is amended instead"). The coordinating session should amend
the epic's C6 row and criterion 14 before implementation starts.

### C4 has already shipped

The epic treats C4, C5, and C6 as parallel and warns that C6 may land first; the
request's constraint 4 follows from that. C4 is in fact complete
(`docs/work/completed/2026-08-12-add-the-stage-entry-verb/`, and
`work/run-a-lifecycle-stage` is `Supported` in the ledger), so the hazard has
passed. Constraint 4 is kept anyway: a unit test against `resolve_prompts` is the
better test regardless of what has landed, and criterion 14 asks for it.

### Coordination with C5

C6 introduces the function that returns a populated `Builtins`. C5 fills
`artifact_templates` for epic criterion 17 and must **extend that same function**
rather than introduce a second loader — two functions returning two different
`Builtins` is how `spec`'s prompt and `spec`'s template end up resolved from
different places. Whichever lands second inherits the other's shape.

### The stage documents are the source, and one step of them is dead

Step 1 of all six stage documents is "Run `tcw work lifecycle --stage <id>` and
honor any binding it reports". It must **not** appear in a built-in prompt: the
prompt is what that reports, and `tcw work stage` already runs the stage's checks
and resolves its bindings before printing. It is circular inside the prompt and
obsolete outside it. C7 should drop it from the routers too.
