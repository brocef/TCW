# Spec — Migrate TCW itself to the 1.0.0 lifecycle and write the consumer migration guide

## Capability changes

**None.** Neither deliverable adds, changes, or removes a user capability. The
migration guide documents behavior 1.0.0 already shipped; the configuration
change is this node's own `tcw-config.yaml` and its adjacent prompt files, which
are project content rather than product surface. No ledger records are written by
this item.

## Problem

Two problems, related by the same cause.

**1. 1.0.0 ships a back-compat break with no upgrade document.** The break is
narrow — `_parse_stage` now appends a problem for an empty `prompt:` list, in
both spellings (`_empty_prompt` at `tcw/store/base.py:992-994` for the legacy
bare list, and again for the explicit `prompt:` key; see also the `## Removed`
section of
`docs/changelogs/v1.0.0.md`) — but it is real: a config that validated under
0.21.1 can fail `tcw validate` under 1.0.0. Beyond it sit a dozen behavior
changes that break no config yet quietly change what a consumer's scripts and
agent instructions get back: `tcw work new` now creates an item with `state.yaml`
alone, piped stdin lands in `intake.md` rather than the request, `inbox accept`
writes `intake.md`, the board's `R` letter stopped being universal, and
`tcw work show <epic>` no longer prints the rollup.

`docs/release-notes/v1.0.0.md` covers all of it, at 280 lines, organized around
what is new. A consumer asking "what do I have to change" has to read the whole
thing and infer the answer. The repo's four existing `docs/migration-guide-*.md`
files exist precisely because that inference is the release notes' weakest job.

**2. TCW has never run its own headline feature against itself.** This repo's
`tcw-config.yaml` is nine lines: an `id` and a tag list. It declares no
`work.lifecycle` block at all. So `prompt:`, `pre:`, `artifacts:`, `when:` — the
whole configuration surface 1.0.0 was built to add — has been exercised by tests
and by recorded fixtures, but never by a project with real rules to express.

This repo has real rules, and they are in the wrong place. `AGENTS.md` (80 lines,
with `CLAUDE.md` a symlink to it) carries the abstraction litmus test, the
abstract-spine vocabulary, the implementation rules, and the Claude/Codex parity
requirement — all of them stage-scoped guidance that an agent reads in full at
every stage, whether or not the stage is the one they govern. That is what
`work.lifecycle.stages.<id>.prompt` was designed for.

## Goals

1. Ship `docs/migration-guide-0.21.X-to-1.0.0.md` in the house style of the
   existing four: what breaks first and briefly, then what changed underneath,
   then what is new and optional.
2. Give this repo a real `work.lifecycle` block exercising `prompt:`, stage and
   transition `pre:`, `artifacts:` templates, and `when:`.
3. Bind this repo's actual rules — not demonstration text — so that a rule the
   configuration surface cannot carry is discovered now rather than by the first
   consumer who tries.
4. Remove from `AGENTS.md` every rule that moves, so there is one copy of each.
5. Record what the surface could not carry, as input to the migration guide.

## Non-goals

- Pushing, merging `epic/polymorphic-work-lifecycle`, or publishing to PyPI.
- Changing the 1.0.0 CLI. A defect found while dogfooding is filed as its own
  backlog item; only a defect that makes this item impossible stops the work.
- `generate:` bindings. The fifth kind is deliberately unexercised: this repo has
  no rule whose text depends on the item, and a script written to demonstrate one
  would be the demonstration text goal 3 rules out. Recorded as a gap.
- Retro-fitting the four earlier migration guides to a common template.
- Any change to `tcw/work/prompts/*.md` — the shipped built-ins. This item
  composes with them; it does not edit them.

## Design

### Deliverable 1 — the migration guide

`docs/migration-guide-0.21.X-to-1.0.0.md`, matching the naming of the four
existing files. Structure, in order, because the ordering is the guide's whole
contribution over the release notes:

1. **The one break.** `prompt: []` and the bare `stages.<id>: []`. What to write
   instead (`prompt: [{blob: ""}]` for a deliberate silence, or delete the line),
   and the reassurance that only `tcw validate` complains while everything else
   keeps running.
2. **What changed under you.** Behavior a consumer's scripts or agent
   instructions may rest on, each with the concrete symptom:
   - `tcw work new` writes `state.yaml` only. Any instruction of the form "open
     the file it printed" now names a file that does not exist.
   - Piped stdin goes to `intake.md`; `inbox accept` writes `intake.md`.
   - `tcw work list` column 3: `R` is no longer on every item, and lowercase `i`
     is new. Anything parsing that column changes meaning rather than breaking.
   - `tcw work show <epic>` no longer prints the rollup; the first `reconcile`
     after upgrade moves a legacy in-request rollup to `rollup.md` on its own.
   - `capabilities` in JSON: a YAML set is now a list; a mapping whose keys
     collide once stringified now raises rather than silently dropping a value.
   - The core revision token changes for every existing item on first read after
     upgrade. It is compared within a session and never persisted, so this
     matters only to a caller holding one across the upgrade itself.
3. **Upgrade ordering.** The CLI and the agent plugin version independently. A
   plugin cache holding the 0.21.1 `tcw-work` skill against a 1.0.0 CLI still
   directs readers to `tcw work lifecycle --stage <id>`, which reports bindings
   and resolves no `builtin` — so on an unconfigured node it says nothing, which
   is exactly the case 1.0.0 fixed. Observed in this session; see `## Notes`.
4. **New and optional.** `tcw work stage`, `tcw work scaffold`,
   `tcw work show --json`, and the lifecycle configuration surface — each in a
   sentence or two, pointing at the release notes rather than restating them.
5. **What you don't have to do.** Existing items are untouched; a bare list under
   a stage id still means `prompt` and still renders identically; `pre: []`
   remains legal in both the stage and transition positions.

### Deliverable 2 — this repo's lifecycle configuration

**Where the prompt text lives.** New directory `docs/lifecycle/`, holding the
prose moved out of `AGENTS.md`, one file per concern rather than one per stage,
so a concern governing two stages is bound twice and written once:

| File                              | Content moved from `AGENTS.md`                                                            | Bound to            |
| --------------------------------- | ----------------------------------------------------------------------------------------- | ------------------- |
| `docs/lifecycle/abstraction.md`   | "Prime directive: the abstraction litmus test" + "Abstract spine, filesystem leverage"      | `spec`, `plan`      |
| `docs/lifecycle/harness.md`       | "Harness compatibility (Claude and Codex)"                                                  | `spec`, `implement` |
| `docs/lifecycle/implementation.md`| "Implementation rules", plus the `tcw work start`-is-the-first-commit rule                  | `implement`         |

`abstraction.md` binds to `plan` as well as `spec` because the litmus test is a
question asked of an operation, and a plan is where operations get named. The
same file, two bindings — which is the composition `prompt:` exists to allow, and
the reason these are three files rather than three stage-shaped ones.

**The block:**

```yaml
work:
    lifecycle:
        stages:
            spec:
                prompt:
                    - builtin: true
                    - file: docs/lifecycle/abstraction.md
                    - file: docs/lifecycle/harness.md
            plan:
                pre:
                    - command: "python scripts/require_artifact.py spec"
                prompt:
                    - builtin: true
                    - file: docs/lifecycle/abstraction.md
            implement:
                prompt:
                    - builtin: true
                    - file: docs/lifecycle/implementation.md
                    - file: docs/lifecycle/harness.md
        artifacts:
            spec:
                - file: docs/lifecycle/templates/spec-bug.md
                  when: { tags: [bug] }
                - file: docs/lifecycle/templates/spec.md
            plan:
                - file: docs/lifecycle/templates/plan.md
        transitions:
            complete:
                pre:
                    - command: "tcw validate"
```

`builtin: true` leads every `prompt:` list, so TCW's own instructions are
composed with rather than replaced.

**The two `pre:` checks are deliberately of different kinds**, because the
surface treats them differently and this repo should demonstrate both:

- The `complete` **transition** check is *enforcing*. `run_pre` is called before
  the store is touched (`tcw/work/cli.py:1215-1216`) and a non-zero exit aborts
  the move. `tcw validate` is the right command here: it exits 0 in 0.9s on this
  repo today, so it costs nothing on the happy path. `pytest -q` was considered
  and rejected — the full suite takes 417 seconds (measured, see `## Notes`), and
  a gate that slow gets routed around rather than obeyed.
- The `plan` **stage** check is *advisory*. Stage checks run only from
  `tcw work stage` (`tcw/work/cli.py:793-799`); `tcw work scaffold` resolves
  templates without running them, and no transition consults them. So it can
  guard a rule without being able to enforce it, which is the correct strength
  for "you should have written the spec first".

**`scripts/require_artifact.py`** is the plan gate's check: it reads `TCW_SLUG`
from the hook environment (`tcw/work/hooks.py`, `hook_env`), shells out to
`tcw work show "$TCW_SLUG" --json`, and exits non-zero when the named artifact is
absent from the `artifacts` map. It reads the artifact map rather than composing
a store path, which is the litmus test applied to the check itself — a check that
did `$TCW_NODE_ROOT/docs/work/.../spec.md` would be exactly the filesystem
hardcoding `reconcile` was fixed to stop doing in this same release.

**Templates.** `artifacts:` is first-match-wins, not concatenating (README, "the
first match wins, so a `builtin` fallback belongs last"), so a repo template
*replaces* the built-in rather than extending it. `docs/lifecycle/templates/spec.md`
therefore restates the seven sections `tcw/work/templates.py` prescribes and adds
this repo's own. That duplication will drift silently when a future TCW release
changes the built-in skeleton, so it gets a guard: `tests/test_repo_lifecycle.py`
asserts every heading in the built-in `spec` and `plan` templates also appears in
this repo's, and that `lifecycle_policy()` parses this repo's config with no
problems. The `when: { tags: [bug] }` variant adds a `## Reproduction` section,
exercising conditions on a tag this repo already registers.

### What stays in `AGENTS.md`, and why

Removal is the point of the item, but two sections are load-bearing for skills
that read `CLAUDE.md` by name and cannot be moved without breaking them:

- **`## Documentation Sync`.** `skills/documentation-sync/SKILL.md:8` instructs
  the agent to "check the project's `CLAUDE.md` for a `## Documentation Sync`
  section", and its `description` names the same location. Moving the section
  into a stage prompt would make TCW's own repo fail the skill TCW ships. It
  stays; `docs/lifecycle/implementation.md` points at it rather than copying it.
- **`## Versioning`.** `skills/documentation-sync/SKILL.md:117` sends the
  version-cut path to "its `CLAUDE.md` / Versioning section". Same reasoning.

Also staying, for reasons of their own: the header and live-status line, which
orient a reader before any stage; `## Generic instructions`, whose no-co-authoring
rule governs every commit rather than any stage; and the single line establishing
that all work here is tracked by `tcw work`, which is how work begins rather than
something a stage says.

This limit is the item's most interesting result and belongs in the migration
guide: **a project can move its stage-scoped rules into lifecycle prompts, but
not rules that another skill reads out of `CLAUDE.md` by name.**

### The prime directive is cited from source, so it moves rather than vanishes

The abstraction litmus test is not only stage guidance. Six places outside
`AGENTS.md` point at it to explain why something is the way it is:
`README.md:78-79` ("The full rules live in `AGENTS.md`"), `README.md:1210`,
`tcw/store/base.py:3` ("Per AGENTS.md (the litmus test) the model is
storage-abstracted"), `tcw/store/fs.py:6` ("don't pre-abstract — AGENTS.md"),
`docs/plan/phase-5-work.md:177`, and `docs/plan/phase-1-scaffold.md:13`.

Deleting the prose without redirecting them would leave six references pointing
at a section that no longer exists. So the rule is that **the prose moves to a
citable file and every reference follows it** to `docs/lifecycle/abstraction.md`.
`AGENTS.md` keeps exactly one line naming that file and the stages it is bound
to — a pointer is not the prose, and a reader who lands on `AGENTS.md` must not
be left unable to find the prime directive at all.

This is the second finding worth carrying into the migration guide, and it
generalizes past this repo: **a rule that source code cites needs a stable
location, and a stage prompt binding does not by itself provide one.** The
`file:` kind does, which is why all three prompt files are `file:` bindings and
none are `blob:` — inline text in `tcw-config.yaml` would have been unciteable.

`tests/test_documentation_sync_wiring.py:30` also reads `AGENTS.md`, but only to
assert the absence of `skill-cefailures` references; it makes no claim about any
section this item moves, so it is unaffected. Verified, not assumed.

### Ordering

Guide first, configuration second. The guide is written from the release notes,
the changelog, and the code; the migration then either confirms it or produces a
finding the guide has to absorb. Writing them the other way round would let the
migration's conveniences leak into a guide meant for consumers who have none.

## Acceptance criteria

1. `docs/migration-guide-0.21.X-to-1.0.0.md` exists and names the `prompt: []`
   break, both of its spellings, and both replacements (`{blob: ""}` or deletion)
   before it describes any new feature.
2. The guide covers all six items listed under "What changed under you" above.
3. The guide states the upgrade-ordering hazard between the CLI and the agent
   plugin.
4. `tcw validate` exits 0 with the new `work.lifecycle` block in place.
5. `tcw work stage spec <any backlog item>` prints TCW's built-in spec
   instructions **followed by** the text of `docs/lifecycle/abstraction.md` and
   `docs/lifecycle/harness.md`, in that order.
6. `tcw work stage plan <item without a spec>` exits non-zero and prints nothing
   on stdout; the same command on an item that has a spec exits 0.
7. `tcw work scaffold spec <item>` on an item tagged `bug` writes a draft
   containing `## Reproduction`; on an untagged item it does not.
8. `tcw work scaffold plan <item>` writes a draft containing every heading
   `tcw/work/templates.py` prescribes for `plan`.
9. `tcw work lifecycle --json` parses, and reports bindings for `spec`, `plan`,
   `implement`, and the `complete` transition.
10. `AGENTS.md` no longer contains the phrases "abstraction litmus test",
    "Abstract spine", or "Harness compatibility" as section headings, and still
    contains `## Documentation Sync` and `## Versioning`.
10a. No file in the repo references a section of `AGENTS.md` that this item
    removed. Specifically `README.md:78-79`, `README.md:1210`,
    `tcw/store/base.py:3`, `tcw/store/fs.py:6`, `docs/plan/phase-5-work.md:177`,
    and `docs/plan/phase-1-scaffold.md:13` each point at
    `docs/lifecycle/abstraction.md` instead, and `AGENTS.md` retains a one-line
    pointer to it. (Criterion 13 is unaffected: these are docstring comments,
    not code.)
11. `python -m pytest -q tests/test_repo_lifecycle.py` passes.
12. `python -m pytest -q` reports **at least 1581 passed and 0 failed** — the
    baseline measured on this tree at spec time, recorded in `## Notes`. The
    count may exceed 1581 by the tests this item adds; it may not fall below it,
    and no test may fail.
13. No file under `tcw/` is modified by this item.

## Risks

- **Removing prose from `AGENTS.md` weakens agents that never run
  `tcw work stage`.** This is the accepted risk of the requested design, and the
  design's own claim is that `tcw work stage` is harness-neutral. The mitigation
  is that `AGENTS.md` retains a single line naming the command; if that proves
  insufficient in practice, the finding is worth more than the prose was.
- **Template drift.** Mitigated by the heading-comparison test, which catches a
  built-in gaining a section but not one changing its guidance text. Named as a
  known ceiling rather than solved.
- **`scripts/require_artifact.py` shells out to `tcw`.** If `tcw` is not on PATH
  the check fails closed, refusing to print plan instructions. That is the safe
  direction, but it is a new dependency of the plan stage on the CLI being
  installed — acceptable here, since every other step already requires it.
- **The `complete` gate does not fire from the web app.** `tcw serve` runs no
  hooks (README). Completing from the web app therefore skips `tcw validate`.
  Not solvable at this layer; recorded so nobody reads the gate as absolute.

## Notes

- **Observed this session, and the source of criterion 3:** the `tcw-work` skill
  loaded from the plugin cache was `.../cache/tcw/tcw/0.21.1/skills/tcw-work`
  while the installed CLI reported `tcw 1.0.0`. The repo's own
  `skills/tcw-work/SKILL.md` is current; the cached copy is not.
- Verified before writing, not recalled: this repo has no `prompt: []` in any
  spelling, no `work.lifecycle` block, and no legacy in-request rollup — the one
  epic's rollup already lives at
  `docs/work/completed/2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven/rollup.md`.
  So the repo cannot serve as a test of the repair path, only the adoption path.
- `tcw work show --json` returns `artifacts` as a flat `{name: bool}` map, not
  objects with a `present` key. Confirmed by running it; the design of
  `require_artifact.py` depends on it.
- Criteria 4, 5, 6, 7, 8, 9, 11 are executable and will be run at the implement
  stage. Criterion 12's baseline must be captured *before* any change, since the
  suite exceeds two minutes and its current state is unverified.
- **Baseline for criterion 12, measured before any change on `8d9450a`:**
  `python -m pytest -q` → `1581 passed in 416.84s`, exit 0. No failures, no
  skips reported. `tcw validate` → `validate OK` in 0.89s.
- `tests/test_documentation_sync_wiring.py:30` includes `AGENTS.md` in
  `NO_CEFAILURES_ROOTS`; read, and it asserts only that no `skill-cefailures`
  string appears. It does not pin any section heading.
- This spec was reviewed by `codex` before the plan stage. Four findings, all
  verified against the tree and all accepted: the stale-reference problem (now
  its own Design section and criterion 10a), two imprecise line citations (fixed
  above), and criterion 12 being uncheckable without a recorded baseline (fixed
  above). Codex independently confirmed the two load-bearing claims — that
  `prompt:` lists concatenate while `artifacts:` is first-match-wins
  (`tcw/work/resolve.py`), and that stage `pre` checks run only from
  `tcw work stage` (`tcw/work/cli.py:793-800`, `882-887`).
