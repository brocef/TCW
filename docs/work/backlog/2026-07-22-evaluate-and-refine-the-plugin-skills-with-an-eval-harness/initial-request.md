# Evaluate and refine the plugin skills with an eval harness

## Product changes

None expected at planning time. This item builds contributor-facing measurement
machinery and tunes skill wording; it does not add, remove, or change a user
capability. Refinements that emerge from the eval results could touch documented
skill behavior (the `plugin/*` and `work/*` capability entries) — re-run the
capabilities gate at closeout if any refinement changes what a user can do
rather than how reliably the agent does it.

## Technical changes

Add a committed eval harness under `evals/`: a fixture seeder, an `evals.json`
test set covering all five skills, and a grading script. Run one measured
iteration (with-skill vs. baseline) and apply the refinements it justifies.

## Meta changes

Establishes eval-driven iteration as the way this repo evolves its skill layer,
replacing "read it and it looks right" with a repeatable measurement.

---

## Requested outcome

The plugin ships five skills (`tcw-work`, `tcw-capabilities`, `tcw-taxonomy`,
`tcw-plugin`, `tcw-report`) and eight commands, and their quality has never been
measured — only reviewed by reading. Two coupled asks:

1. **Measure.** Stand up an evaluation harness following the eval-driven
   iteration methodology at
   <https://agentskills.io/skill-creation/evaluating-skills.md>: a test set of
   realistic prompts, each run twice (once with the skills available, once
   without) against an isolated fixture, then graded against assertions,
   aggregated into a benchmark, and reviewed by a human.
2. **Refine.** Use that first measurement to improve the skills, rather than
   guessing at improvements unmeasured.

The methodology's own framing is the reason for the with/without split: a skill
that changes nothing versus baseline is not earning its context budget, and only
a baseline comparison can show that.

## Decisions already made

- **Coverage: all five skills, thin** (one or two test cases each) rather than
  deep coverage of `tcw-work` alone. Accepted trade-off: this tells us which
  skill is weakest more than it tells us why, and iteration 2 can go deep on
  whichever skill the numbers indict.
- **Fixture: a synthetic throwaway repo**, seeded per run — never the TCW repo
  itself. These skills mutate `docs/work/`, so runs must not touch real
  dogfooded state or contaminate each other.
- **Harness home: committed to `evals/`**, so the measurement is repeatable
  across releases and anyone can re-run it. Accepted cost: the seeder drives the
  `tcw` CLI, so CLI surface changes can rot it.
- **Loop depth: one measured iteration.** Build, run, grade, human review, apply
  the clear fixes, report the judgment calls. Not an iterate-until-clean loop.

## Constraints

- Runs must be isolated: a fresh seeded git repo per run, so no run sees
  another's mutations and the with-skill and baseline arms start identical.
- The harness must not reinvent fixture machinery. `tests/test_skill_flow.py`
  already builds throwaway git repos and drives the CLI end-to-end; the seeder
  should follow that pattern and reuse `tcw.store.fs.init`.
- Skill edits must generalize. The eval set is a handful of prompts; fixes that
  only satisfy those prompts make the skills worse in the field, not better.
- The five skills cross-reference each other ("REQUIRED SUB-SKILL"), so the
  with-skill arm must expose all five, matching how they are really installed.

## Non-goals

- No remote-store or CLI behavior changes. This item measures and tunes the
  judgment layer; mechanism stays in the binary.
- No description-triggering optimization loop. Whether skills *fire* is a
  separate axis from whether they *work*; defer it.
- No iterate-until-clean refinement loop, and no deep single-skill coverage.

## Known drift to fold in

`README.md`'s install section lists six commands, but `commands/` contains
eight — `/tcw-audit-work-backlog` and `/tcw-consolidate-plans` are unlisted.
Small, already confirmed, and in the same blast radius as the skill-layer
documentation this item touches.

## Open questions for spec

- Which specific scenarios best exercise each skill, given only one or two test
  cases per skill? The cross-axis scenario (a product change that must walk
  taxonomy → capabilities → work) may be worth more than any single-skill case.
- How is `tcw-plugin`'s install/repair path exercised without a genuinely broken
  `tcw` install, which is unsafe to simulate in a subagent's environment?
- Should the fixture seeder be guarded by the existing pytest suite, or left to
  rot loudly on first re-run? (Deferred at intake; decide in spec.)
- What grades mechanically versus what needs human judgment? Much of what these
  skills get right is checkable from the fixture's end state (item status,
  commit shape, ledger values), which is cheaper and more reliable than an LLM
  judge.
