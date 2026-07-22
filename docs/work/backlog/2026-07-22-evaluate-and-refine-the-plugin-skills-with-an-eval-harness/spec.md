# Spec — Evaluate and refine the plugin skills with an eval harness

## Capability changes

None. This item adds contributor-facing measurement machinery under `evals/`
and tunes skill prose. No `tcw` CLI surface changes, so nothing a user can do
changes. The `capabilities.yaml` sidecar is deliberately absent.

Re-run the gate at closeout: if a refinement changes *what* a skill instructs an
agent to do rather than how reliably it does it, the affected `plugin/*` or
`work/*` entries may need a body edit (not a status flip).

## Problem

The five skills are the plugin's judgment layer — the thing the README calls the
counterpart to the CLI's mechanism. Their quality has only ever been established
by reading them. Nobody knows whether an agent holding `tcw-work` actually
outperforms one holding only `tcw --help`, which parts of the prose carry the
weight, or which skill is weakest. Every refinement to date has been a guess
validated by a second guess.

## Goals

- A committed, re-runnable harness that measures each skill against a no-skill
  baseline on realistic prompts.
- One measured iteration producing: per-eval pass rates, the with/without delta,
  token and time cost, and a human-reviewed findings pass.
- Skill refinements justified by that evidence, applied where the signal is
  unambiguous and surfaced for decision where it is a judgment call.
- README command-list drift fixed.

## Non-goals

- No `tcw` CLI or store changes.
- No description-triggering optimization (whether skills *fire* is a separate
  axis from whether they *work*).
- No iterate-until-clean loop, and no deep single-skill coverage.
- No LLM-judge grading where the fixture's end state answers the question
  mechanically.

## Current-state findings

### Run isolation — resolved empirically

The blocking design question was how to run a with-skill and a baseline arm that
differ *only* in whether the tcw skills are reachable. Six probes:

| Mechanism | Result |
| --- | --- |
| `--disallowed-tools Skill` | Kills all skills — clean baseline, but no matching with-skill arm |
| `--plugin-dir <repo>` | Also loads the other 8 globally-enabled plugins |
| `--settings '{"enabledPlugins":{"tcw@tcw":true}}'` | Merges additively; foreign plugins remain |
| `--disallowed-tools 'Skill(ns:*)'` | No namespace scoping |
| `CLAUDE_CONFIG_DIR=<clean>` | `Not logged in` — keychain auth is config-dir-keyed |
| `--bare` | Clean, but refuses OAuth; needs `ANTHROPIC_API_KEY` |
| **`--settings` with explicit `false` per plugin** | **Works — suppresses each plugin and its hooks** |

The last row is the runner. Both arms pass the same explicit-`false` map for
every foreign plugin and differ only in `"tcw@tcw": true|false`.

**Hooks were the bigger contaminant, not the skill listing.** SessionStart hooks
*do* fire under `claude -p` (verified). Two inject unconditionally:

- `superpowers` (`hooks/session-start`) injects `using-superpowers/SKILL.md`
  verbatim — the "if there is even a 1% chance a skill might apply you
  ABSOLUTELY MUST invoke the skill" directive. This is **asymmetric**: it
  pressures the with-skill arm toward reaching for `tcw-work` while giving the
  baseline arm nothing to reach for, inflating apparent skill value.
- `ponytail` (`hooks/ponytail-activate.js`) injects its ruleset at the
  configured intensity and writes `~/.claude/.ponytail-active`.

Explicit `false` suppresses both. Verified residue in both arms: Claude Code's
built-in skills (`deep-research`, `dataviz`, `run`, …), the user's own
`~/.claude/settings.json` hooks, and `~/.claude/CLAUDE.md`. All present
identically in both arms — constants, not confounds. Documented, not fixed;
removing them would need `--bare` and an API key, which buys little here.

### Fixture machinery already exists

`tests/test_skill_flow.py` already builds a throwaway git repo (`repo()`), calls
`tcw.store.fs.init`, and drives the full lifecycle handshake through
`tcw.cli.main`. The eval seeder should follow that pattern rather than invent
one. That file is also the existing CLI-level regression for the same handshake
the skills teach — the eval harness measures the *judgment* layer that pytest
structurally cannot reach.

### The skills are mechanically gradeable

Most of what these skills get right is visible in the fixture's end state rather
than in prose: which folder an item lives in, whether `tcw work start` preceded
the first code edit (git log ordering), whether each lifecycle artifact got its
own commit, whether a capability reads `Supported`, whether `tcw validate`
exits 0. Grading should be a script reading the fixture repo, with an LLM
grader reserved only for prose-quality assertions.

### Known drift

`README.md`'s install section lists six commands; `commands/` contains eight.
`/tcw-audit-work-backlog` and `/tcw-consolidate-plans` are unlisted. Both carry
`disable-model-invocation: true` except `tcw-audit-work-backlog`, which does
not — worth confirming that asymmetry is intentional while in there.

## Proposed behavior

### Harness layout

```
evals/
├── evals.json          # the test set: prompts, expected outputs, assertions
├── seed_fixture.py     # build one throwaway seeded TCW node
├── run_evals.py        # spawn both arms per eval, capture outputs + timing
└── grade.py            # mechanical assertions against the fixture end state
```

Results land in the session scratchpad (`iteration-N/<eval>/{with_skill,baseline}/`),
not the repo — measurements are disposable, the instrument is not.

### The fixture

One seeded `demo-app` node per run: a small fake billing/reporting product, two
vocabulary terms plus one feature, two capabilities (one `Supported`, one
`Missing`), a backlog item, an active item mid-flight whose `capabilities.yaml`
declares an unflipped `Missing` capability, an untriaged inbox request, and a
registered tag set. Rich enough that every skill has something real to act on,
and deliberately primed so the completion gate has something to fail closed on.

### Test set — thin across all five

Seven cases. One integration case matters more than any single-skill case,
because the chain `Vocabulary → Features → Capabilities → Work` is the thing the
skills coordinate and the thing most likely to be dropped.

| # | Skill | Scenario |
| --- | --- | --- |
| 1 | tcw-work | Feature request in chat → item created, planned, `start` before first code edit, per-stage commits |
| 2 | tcw-work | Inbox triage of the raw `slow-login.md` request → accepted with sensible title and tags |
| 3 | tcw-capabilities | Close out the mid-flight item → ledger flipped `Missing → Supported`, then `complete`, without `--force` |
| 4 | tcw-taxonomy | Register loose domain language → correct Vocabulary vs Feature split, `--vocab` links, `check` clean |
| 5 | tcw-plugin | Orientation: "which axis does this belong in, and where do I start?" |
| 6 | tcw-report | "`tcw work complete` threw a traceback" → GitHub issue skeleton, **not** a local work item |
| 7 | cross-axis | Product change requiring a new term, a new capability, and a work item, in the right order |

Case 6 is the sharpest negative test in the set: the natural wrong answer
(logging it as local work) is exactly what `tcw-report` exists to prevent.

`tcw-plugin`'s install/repair path is deliberately **not** tested — simulating a
broken `tcw` install inside a subagent's environment is unsafe and would measure
the simulation more than the skill. Case 5 covers its orientation half; the
repair half stays unmeasured, and the findings report must say so rather than
imply full coverage.

### Grading

Per-eval assertions, each mechanically checkable from the fixture repo:
item status and location, `git log` ordering and commit granularity, capability
status and fields, `tcw validate` exit code, and absence of hand-edits under
`docs/work/` where a command existed. Assertions that pass in both arms get
removed as non-discriminating; assertions failing in both get investigated as
broken before iteration 2.

## Acceptance criteria

- `evals/` holds a harness any contributor can run to reproduce the numbers.
- `iteration-1/benchmark.json` reports pass rate, time, and tokens per arm with
  the delta, plus a per-eval breakdown.
- Both arms verified isolated: no foreign plugin skills, no injected SessionStart
  directives.
- A findings report naming, per skill, what the evidence supports — including
  where the skill showed **no** measurable lift, which is a real result.
- Refinements applied where unambiguous; judgment calls surfaced, not silently
  applied.
- README lists all eight commands.
- `pytest` green.

## Risks

- **Overfitting to seven prompts.** The stated mitigation is a rule, not a hope:
  a refinement must be justifiable from the skill's purpose, not merely from a
  failing case. Fixes that only satisfy these prompts get rejected.
- **Non-discriminating assertions inflating the delta.** Anything passing in both
  arms is removed before the numbers are reported.
- **Single run per eval means no stddev.** With n=1 the benchmark's variance
  fields are meaningless; report raw counts and the delta, and treat a
  single-case swing as a lead rather than a finding.
- **Seeder rots on CLI drift.** Guarded by a pytest case (below).
- **Cost.** 14 `claude -p` runs, each driving a real lifecycle. Bounded by
  `--max-turns` and by keeping the fixture small.

## Dependencies and related work

- `tests/test_skill_flow.py` — the fixture pattern to reuse.
- `tests/test_plugin_manifests.py` — the existing authoring-drift guard; the
  README command-list check is the same genre and belongs beside it.
- No blockers. No other active item touches `skills/` (the active web-client
  item is confined to `web/`).
