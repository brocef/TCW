# Repoint the work skill and docs at the CLI

Child **C7** of `2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`.
The consolidation child: **C1–C6 have each already updated their own command
docs, changelog, release notes, and ledger entries.** C7 performs only what
could not be expressed earlier.

## Product changes

The CLI now answers "what do I do at this stage?" itself. `tcw work stage <id>
<ref>` prints TCW's own instructions on a node that has configured nothing, and
`tcw work scaffold <artifact> <ref>` writes a starting draft from a template.
The skill and the README still describe a world where the skill was the only
place that knowledge lived.

So: **the documentation stops being the source and starts pointing at the
source.** A reader following either one should end up running the verb, not
reading a second copy of what the verb prints.

## Technical changes

Four surfaces:

1. `skills/tcw-work/references/stage-*.md` — seven documents, 66–77 lines each,
   reduced to routers.
2. `skills/tcw-work/references/hooks.md` — 159 lines, rewritten around the roles,
   kinds, and conditions C3 shipped.
3. `skills/tcw-work/SKILL.md` — its "Always" section still says to run
   `tcw work lifecycle --stage`; that is now the wrong verb.
4. `README.md` §"Binding your own skills and commands to the lifecycle" — one
   coherent rewrite. The epic reserved this for C7 deliberately, because four
   partial rewrites by four children would have been worse than one at the end.

## Meta changes

None. C8 audits the backlog afterwards; C7 does not.

## Constraints

Decided by the requester at this stage, so `spec` is not re-litigating them:

1. **Target 40–50 lines per stage router**, down from today's 66–77. A further
   condensation than they have had, but not a bare pointer.

2. **Constraint 1 and criterion 18 are in tension, and `spec` must resolve it
   explicitly.** Criterion 18 says the routers must not restate what the
   built-in prompts say. The prompts now carry the methodology for six of the
   seven stages — so at 40–50 lines a router is *almost entirely* the material
   C6 assigned to the skill: delegability, `[gated]`/`[judgment]` notation, epic
   and cross-node deltas, sub-skill names, and store mechanics. The spec should
   say, per stage, what fills those 40–50 lines without restating the prompt. If
   a stage genuinely has less than 40 lines of skill-only judgment, **say so and
   let it be shorter** — padding a router to hit a target is the one outcome
   worse than a long one.

3. **`inbox` is the exception.** No prompt ships for it, because it runs before
   an item exists, so `stage-inbox.md` keeps carrying its own methodology.
   Reducing it the way the other six are reduced would strand it.

4. **C7 fixes the `work/configure-the-work-lifecycle` contradiction.** Its
   record promises "Everything I configured before this still works and still
   prints the same thing. A stage id with a plain list under it means what it
   always meant." C6 made a bare `stages.<id>: []` a `tcw validate` problem. C6
   surfaced this rather than overwriting it, which was correct; C7 owns the fix
   because it is already rewriting the documentation of the same model.

5. **The prompt line ceiling was raised from 40 to 50 at C6's verify stage**
   (`ab86012`), so there is headroom to move a clause into the CLI where the
   Codex user needs it. It is headroom, not an invitation: the reason for the
   raise was to stop the ceiling deciding the CLI/skill seam, not to move the
   stage documents wholesale into the CLI.

## References

- `tcw/work/prompts/*.md` — the six shipped prompts. These are what criterion 18
  is checked against; a router must not restate them.
- **C6's spec §5**, in
  `docs/work/completed/2026-08-12-ship-built-in-stage-prompts-with-the-cli/spec.md`
  — the per-stage "Moves into the prompt / Stays in the skill / Deliberately
  lost" table, written explicitly as C7's contract. The right-hand columns are
  what the routers are *for*.
- `/Users/brian/.claude/plugins/cache/claude-plugins-official/superpowers/6.3.0/skills/writing-skills`
  — skill-authoring guidance. **The requester asked for a `writing-specs` skill;
  no such skill exists** in either installed superpowers version (6.2.0 or
  6.3.0). `writing-skills` is the nearest and the more relevant one, since this
  item is a skill rewrite. `writing-plans` also exists if the plan stage wants
  it.
- `CLAUDE.md` §"Skill authoring (progressive disclosure)", which names
  `tcw-plugin` and `tcw-work` as the pattern a router should follow.
- `tests/test_skill_lifecycle_parity.py` — the existing guards, including the
  `SKILL.md` line budget whose stated rule on breach is "extract, don't grow".

## Notes

- `SKILL.md`'s body is currently **at** its 60-line budget, so the "Always"
  section repoint has to fit by replacement, not addition.
- C5's outcome flagged that it deliberately left `SKILL.md:29-35`'s stage/artifact
  table alone for want of budget, and that C7 owns the router and can revisit it
  with room to spend.
