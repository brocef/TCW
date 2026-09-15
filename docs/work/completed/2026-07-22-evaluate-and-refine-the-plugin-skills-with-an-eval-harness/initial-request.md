# Measure lifecycle prompt injection, and evaluate the plugin skills with an eval harness

Two requests, fifteen months apart, recorded in the order they were made. The
second reframes the first rather than replacing it: the same instrument answers
both, and the July ask is still wanted.

---

# Request 2 — 2026-09-10

## What was asked

> One of the key things I want to evaluate is whether or not the lifecycle
> prompt injection is successful, and to see whether or not the customized
> prompts are correctly used by agents.

Said alongside two supporting asks: that the item is old and should be rewritten
against the latest state of the plugin, and that a work-inbox note be processed
with its eval-relevant parts absorbed here.

## Why now

The lifecycle instruction layer was rebuilt after request 1 was written. One
`tcw work stage` verb became `gate` and `prompt`; every resolved prompt is
wrapped in a gate header and a next-step footer; a skill (`tcw-work-stage`) now
exists whose whole job is composing a stage's router and its resolved project
instructions into one read; and a project binds one of five instruction kinds to
a stage. None of that existed when the original ask was framed, and none of it
has ever been measured end to end.

The requester's concern is **not** whether the CLI emits the right text — that
is already frozen byte-for-byte in the suite. It is whether the text arrives in
front of an agent, and whether a project that customizes it gets different
behavior for having done so. If it does not, every project-specific lifecycle
instruction TCW ships is decoration.

## Decisions taken at this stage

Asked and answered on 2026-09-10:

- **Both axes, injection first.** The item covers the injection measurement
  *and* the original skill-lift measurement, with the shared instrument built
  once. Injection fidelity is the deliverable that must land; skill lift extends
  it. Rejected: splitting skill lift to a follow-up, and dropping it.
- **Both harnesses, Codex allowed to fail closed.** Codex is the only harness
  where the manual fallback is the live path, so it stays in scope. If a clean
  matched pair cannot be established there, that is recorded as an explicit
  unsupported result rather than reported as cross-harness evidence.
- **Contributor-local only.** The eval run is documented and run by hand; it
  never enters CI. A pytest guard keeps the fixture from rotting. Rejected: a
  CI-runnable mode, which would need a pinned settings map and an API key.

## Constraints

- The instrument must be able to return "customization does nothing." That is a
  legitimate finding and the reason the measurement is worth taking; it must not
  be softened into a list of refinements.
- What is measured is derived from the shipped surface rather than described
  alongside it. A hand-kept list of what to cover drifts, and this repository
  has already shipped one that undercounted itself.

## Out of scope

- Changing the `tcw` command surface or the store.
- Optimizing whether skills *fire*. That is a separate axis from whether they
  work.

---

# Request 1 — 2026-07-22

> Preserved as written. Its counts are of their time: the plugin then shipped 5
> skills and 8 commands, and now ships 9 skills, 13 commands and 7 stage
> prompts. Its "Known drift to fold in" section was resolved on 2026-07-28 and
> has been removed. Its open questions are answered under **Notes**.

## Product changes

None expected at planning time. This item builds contributor-facing measurement
machinery and tunes skill wording; it does not add, remove, or change a user
capability. Refinements that emerge from the eval results could touch documented
skill behavior (the `plugin/*` and `work/*` capability entries) — re-run the
capabilities gate at closeout if any refinement changes what a user can do
rather than how reliably the agent does it.

## Technical changes

Add a committed eval harness under `evals/`: a fixture seeder, a test set, and a
grading script. Run one measured iteration and apply the refinements it
justifies.

## Meta changes

Establishes eval-driven iteration as the way this repo evolves its skill layer,
replacing "read it and it looks right" with a repeatable measurement.

## Requested outcome

The plugin's skills and commands have never had their quality measured — only
reviewed by reading. Two coupled asks:

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

- **Coverage: every skill, thin** (one or two test cases each) rather than deep
  coverage of `tcw-work` alone. Accepted trade-off: this tells us which skill is
  weakest more than it tells us why, and a later iteration can go deep on
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
  another's mutations and the arms start identical.
- The harness must not reinvent fixture machinery.
- Skill edits must generalize. The eval set is a handful of prompts; fixes that
  only satisfy those prompts make the skills worse in the field, not better.
- The skills cross-reference each other ("REQUIRED SUB-SKILL"), so the
  with-skill arm must expose all of them, matching how they are really
  installed.

## Non-goals

- No remote-store changes and no change to the `tcw` command surface. Since the
  lifecycle methodology began shipping *inside* the binary as
  `tcw/work/prompts/*.md`, editing a shipped prompt is an in-scope refinement —
  it is prose, not mechanism. Unlike a skill edit it ships in the wheel and
  earns a release note.
- No description-triggering optimization loop.
- No iterate-until-clean refinement loop, and no deep single-skill coverage.

---

## References

Asked for; none supplied beyond what the session found in the repository. These
four are the ones identified, each recorded with why it matters:

- `tests/test_skill_flow.py` — builds a throwaway git repo, calls
  `tcw.store.fs.init`, and drives the lifecycle handshake through
  `tcw.cli.main`. The fixture pattern the seeder should follow rather than
  inventing one, and the CLI-level regression for the same handshake the skills
  teach.
- `tests/fixtures/prompt_fallback/` — byte-frozen `tcw work stage prompt` output
  for all seven stages on a node that configures nothing. It is the control arm
  of the injection measurement already sitting in the suite, and it establishes
  that what the resolver *emits* is a solved problem.
- `tests/test_skill_lifecycle_parity.py` — guards that the composing skill
  declares the commands it injects and that each ends in a fallback. It bounds
  what the eval must still discover, and one of its guards is the worked example
  of a static assertion that stopped measuring anything.
- `tests/test_plugin_manifests.py` — the authoring-drift guard, including the
  skill count and enumeration checks. The genre of check the harness's coverage
  gate belongs to.
- <https://agentskills.io/skill-creation/evaluating-skills.md> — the methodology
  request 1 names, and the source of the with/without framing.

## Notes

**Request 1's open questions are all answered**, in `spec.md` rather than here:
which scenarios exercise each skill, how `tcw-plugin`'s install/repair path is
handled (it is not — declared an explicit exclusion, since simulating a broken
install in a subagent's environment is unsafe and would measure the simulation),
whether the seeder is pytest-guarded (yes), and what grades mechanically versus
by judgment (mechanically, wherever the fixture's end state answers it).

**Absorbed from the work inbox, 2026-09-10.** One entry,
`2026-09-10-untested-skill-guards-and-the-blob-silencing-advice.md`, was
processed into this item rather than becoming an item of its own: its defects
were already fixed and shipped in 2.0.0, verified at HEAD before the entry was
removed, and what remained in it was evidence about measurement. That evidence
is recorded in `spec.md`. A companion entry from the same round,
`2026-09-10-verification-findings-on-the-stage-verb-branch.md`, is equally
resolved and was left in the inbox pending the requester's word.

**Inference, not stated by the requester.** That the injection measurement needs
a configured-versus-unconfigured node as its control, rather than the
skill-toggle contrast request 1 assumed, is the session's reading of the ask and
not something the requester said. It is argued in `spec.md`; if it is wrong, the
axis is wrong.
