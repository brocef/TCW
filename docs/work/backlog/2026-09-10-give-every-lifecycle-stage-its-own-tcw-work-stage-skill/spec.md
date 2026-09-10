# Give every lifecycle stage its own `tcw-work-<stage>` skill

## Capability changes

**Changed:** `work/run-a-lifecycle-stage` (`cap-f42255`, `Supported`).

Its final paragraph, at `docs/capabilities/work/run-a-lifecycle-stage/description.md:95`,
says a Claude user takes both halves of a stage in one read through
`tcw-work-stage`. After this item there are six ways in, not one: the generic
skill and five stage-specific ones. The paragraph has to describe both, and to
keep saying the part that matters — that the skill reads with `prompt` and
therefore runs no gate.

No new capability. Nothing becomes possible that was impossible; the same
composed read gets a shorter way to ask for it. No taxonomy change either — the
capability's `Feature: configurable-work-lifecycle` still describes it.

## Problem

`tcw-work-stage` takes `arguments: [stage, item]`
(`skills/tcw-work-stage/SKILL.md:5`). Both have to be supplied, in order, for
the skill to compose anything.

The stage argument is the one the invoker already knows for certain — they are
reaching for the skill precisely because they are about to work `spec`, or
`plan`. Restating it buys nothing. Worse, it makes the skill's own name say
nothing about what it is for: `tcw-work-stage` is a shape, not a task, so the
description has to carry the entire burden of explaining when to reach for it.

Because the stage argument comes first, the item argument cannot be dropped
either, even though the CLI underneath is perfectly happy without it. This is
ground truth, not inference — invoking the skill with only `verify` was tried
against this tree, and the injected command ran as
`tcw work stage prompt verify`, printing the stage instructions with `<slug>`
placeholders where an item reference would go. An omitted argument interpolates
to the empty string, not to a literal `$item`.

So the current shape charges two arguments for a skill whose underlying commands
need at most one.

## Goals

1. Invoking a stage names the stage: `/tcw:tcw-work-spec`, not
   `/tcw:tcw-work-stage spec <item>`.
2. The work item reference is the only argument, and it is optional.
3. `tcw-work-stage` survives unchanged, for a caller holding the stage id as
   data rather than as knowledge.
4. Everything that keeps `tcw-work-stage` honest today — the gate warning, the
   `|| true` guards, the declared `allowed-tools` — keeps all six skills honest,
   enforced by tests rather than by care.

## Non-goals

- **No change to the `tcw` CLI.** Not to `tcw work stage gate`, not to
  `tcw work stage prompt`, not to what either emits. This item is packaging.
- **No change to the stage documents** under
  `skills/tcw-work/references/lifecycle/`, and none to the `tcw-work` skill's
  own routing.
- **No skill for `inbox` or `postmortem`.** `inbox` runs before an item exists
  and takes no work item reference on either verb, so a stage-specific skill for
  it would wrap a two-argument command in a zero-argument skill and add nothing.
  `postmortem` already has `tcw-post-mortem`, with a read-only agent behind it;
  a second skill for the same stage would compete with it for the model's
  attention. Five skills, not seven.
- **No generated files.** No template, no build step, no script that writes
  `SKILL.md` files. Five small documents are cheaper to read than a generator
  plus its output.
- **Nothing about how a stage is worked.** The methodology stays where it is,
  in the CLI's resolved prompt and in the stage document.

## Design

### The five new skills

One folder each, one file each:

```
skills/tcw-work-request/SKILL.md
skills/tcw-work-spec/SKILL.md
skills/tcw-work-plan/SKILL.md
skills/tcw-work-implement/SKILL.md
skills/tcw-work-verify/SKILL.md
```

Each is `skills/tcw-work-stage/SKILL.md` with the stage written in literally
instead of interpolated, and one argument instead of two:

- `name: tcw-work-<stage>`.
- `arguments: [item]`, so `$item` is the only substitution.
- `allowed-tools: Bash(tcw *), Bash(cat *)` — unchanged, and load-bearing: an
  injected command that is not pre-approved aborts the whole invocation and the
  model is shown nothing at all.
- Two injected commands, each ending `|| true`:
  `` !`cat "${CLAUDE_PLUGIN_ROOT}/skills/tcw-work/references/lifecycle/stage-<stage>.md" || true` ``
  and `` !`tcw work stage prompt <stage> $item || true` ``.
- The gate warning in prose, naming
  `tcw work stage gate <stage> $item`, and the manual-fallback fence beneath it.

`description` and `when_to_use` are written per stage rather than templated,
because they are the only part that does a different job in each file: they are
what the model matches against, and five descriptions that differ only by a word
would compete rather than discriminate. Each one names TCW and the work item
explicitly, so a prompt about planning, implementing, or verifying something
unrelated does not pull a TCW skill in.

### Why the item argument may be omitted

`tcw work stage prompt <stage>` with no reference is a supported call — the
`run-a-lifecycle-stage` capability states it, `arguments: [item]` interpolates an
absent argument to the empty string, and both were confirmed against this tree.
`cat` of the stage document never needed an item. So the skill invoked bare
still delivers both halves; only the item-specific parts of the prompt degrade to
`<slug>` placeholders.

The gate is the one thing that genuinely needs the reference, and the gate is not
run by the skill. The warning already says so, which is why omitting the item is
safe rather than merely tolerated.

### Why the generic skill stays

`tcw-work-stage` is what a caller uses when the stage id is a value it computed
rather than a fact it knows — a loop over `STAGE_IDS`, a skill that dispatches,
a user who wants `inbox` or `postmortem` composed the same way. Deleting it
would remove the only route to those two stages' composed read.

### Harness compatibility

`arguments:` and `` !`cmd` `` are Claude-only and inert under Codex, so a Codex
reader gets the static body with `$item` unsubstituted and no injected blocks —
exactly what `tcw-work-stage` already gives them today. That is acceptable
because no requirement rests on the injection: the two commands the manual
fallback fence names are `tcw` CLI commands, identical under both harnesses. The
fence is therefore not decoration and has to appear in all five files.

### The abstraction litmus test

Not engaged. No store operation is added, changed, or removed; no item, status,
transition, reference, or query is touched. The change is entirely in how a
Claude harness is handed instructions the CLI already prints.

### What else has to move

| File | Why |
| --- | --- |
| `tests/test_plugin_manifests.py` | `NUMBER_WORDS` stops at 12. The skill count goes 9 → 14, so `test_the_codex_description_counts_the_skills_it_ships` raises `KeyError: 14` before it can assert anything. |
| `.codex-plugin/plugin.json` | Its `longDescription` must say "fourteen skills" and name each of the five, or the same test fails on the count and the enumeration. |
| `README.md:270` | Says "Seven skills" over a seven-row table that already omits `tcw-work-stage` and `tcw-post-mortem`. Nothing tests it. |
| `skills/tcw-work/references/commands.md:31` | The one row describing the composed read names only `tcw-work-stage <id> <item>`. |
| `docs/capabilities/work/run-a-lifecycle-stage/description.md:95` | The capability delta above. |
| `tests/test_skill_lifecycle_parity.py` | The four `STAGE_SKILL` tests each check one hard-coded file. They become parametrized over all six composing skills, plus one new test fixing the expected set. |

## Acceptance criteria

1. `skills/tcw-work-<stage>/SKILL.md` exists for exactly
   `request`, `spec`, `plan`, `implement`, `verify` — no more, no fewer — and a
   test derives that set from `STAGE_IDS` minus `{inbox, postmortem}` rather
   than from a second hand-written list.
2. Each of the five declares `arguments: [item]` and does **not** declare a
   stage argument.
3. Each of the five names its own stage literally in both injected commands, and
   the `cat` target resolves to a file that exists in the tree (the existing
   template-resolution test, widened).
4. Each of the five contains the literal `tcw work stage gate <stage> $item`
   **outside** any fenced block, with fenced blocks stripped before the
   assertion — the same guard that already protects `tcw-work-stage`, for the
   same reason.
5. Every injected command in all six composing skills ends with `|| true`, and
   every one of the six declares both `Bash(tcw *)` and `Bash(cat *)` in
   `allowed-tools`.
6. `skills/tcw-work-stage/SKILL.md` is unchanged by this item: `git diff` over
   the item's commits touches no line of it.
7. `pytest` is green, including
   `test_the_codex_description_counts_the_skills_it_ships`, which requires
   `.codex-plugin/plugin.json` to say "fourteen skills" and to name all fourteen
   by directory name.
8. `tcw capabilities check` and `tcw validate` exit zero, and
   `docs/capabilities/work/run-a-lifecycle-stage/description.md` describes the
   per-stage skills alongside the generic one, still stating that the composed
   read runs no gate.
9. `README.md`'s skills section states a count matching `skills/*/SKILL.md` and
   its table accounts for the composing skills.
10. Invoking `/tcw:tcw-work-spec` with no argument renders both blocks, with the
    prompt half showing `<slug>` placeholders; invoking it with an item
    reference renders both blocks with that reference substituted throughout.
    Checked by hand, recorded in `outcome.md` — no test can drive a Claude skill
    invocation.

## Risks

- **Five more skill descriptions in every session's context, used or not.** This
  is the cost of the change and it was accepted deliberately when the set was
  cut from seven to five. Mitigation is wording, not count: each description
  leads with TCW and the work item so it does not match a generic prompt about
  specs or plans.
- **Name collision with the slash commands.** `tcw-work-plan` sits beside the
  existing `/tcw-plan-work`, and `tcw-work-verify` beside `/tcw-verify-work`.
  They do different jobs — the command drives a range of stages, the skill
  composes one stage's instructions — and the names are near-anagrams. Each
  skill's `when_to_use` should say what it is *not*, the way `tcw-report` and
  `tcw-triage-issues` already do for each other.
- **Six near-identical files drift.** Accepted, with the mitigation being that
  every property worth keeping is parametrized over all six rather than checked
  on one. A test that checks only `tcw-work-stage` after this item is a test
  that has stopped biting for five files.
- **The Codex `longDescription` becomes a fourteen-item sentence.** It is
  already a long one. Grouping the five under one clause — "and five
  stage-specific shortcuts, `tcw-work-request` through `tcw-work-verify`" — will
  not satisfy the test, which looks for each directory name as a substring; all
  five names have to appear literally.

## Notes

Two facts in this spec came from running the skill against this tree rather than
from reading its source, because nothing in the repository records them:
`$stage` and `$item` do interpolate inside a plugin skill, and an omitted
argument becomes the empty string rather than a literal. Both were observed in
this session. If a future harness changes either, criterion 10 is what catches
it, and it is a manual check for exactly that reason.
