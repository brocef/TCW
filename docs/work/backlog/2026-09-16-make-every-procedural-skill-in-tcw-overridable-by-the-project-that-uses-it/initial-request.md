# Make every procedural skill in TCW overridable by the project that uses it

## The initiative

TCW composes a lifecycle stage's instructions at read time. `builtin: true` is
TCW's own text and a project adds its own with `file:` or `skill:` entries under
`work.lifecycle.stages.<id>.prompt`, so the skill carries the reasoning and the
project carries the facts. `skills/tcw-work-stage/SKILL.md` is where that reaches
its cleanest form: the file is almost empty of instruction, and its body is two
injected commands that fetch the stage document and the project's resolved
prompt.

**Nothing outside lifecycle stages composes.** Every other procedure TCW ships is
fixed prose, and some of it encodes one maintainer's personal working practice as
a requirement on everybody.

`skills/tcw-extras-autonomous-work/SKILL.md` is the case that prompted this. It
describes how to work TCW items unattended and mandates: exactly two named AI
advisors — the Codex CLI with its exact invocation, and an Opus subagent through
Claude Code's `Agent` tool; `SendMessage`; a standing claim that "Codex is the
reliable half"; `adversarial-code-reviewer`, an agent TCW does not ship and which
occurs nowhere else in the repository; one git closeout, "merge the feature
branch into main **locally**. Never `git push`"; and one version policy, "Never
cut one. Accumulate into `upcoming.md`". The advisor count is load-bearing rather
than illustrative — the adjudication rule reads "not a majority (there is no
majority of two)". None of it is declared in frontmatter, so a reader cannot see
that the skill needs a second AI CLI installed and authenticated, although
`tcw-setup` and `tcw-extras-triage-issues` both declare their own requirements.

The requester's position: these are their own requirements for autonomous work
and they are reasonable, but they should not be imposed on every TCW user.
Another project's advisor might be a different AI, or another Claude agent
pointed at a particular skill or agent definition, or a person.

It also contradicts TCW's own doctrine, in
`skills/tcw-work/references/procedures/delegation.md` — "Delegable means
permitted, never required", "**No behavior depends on it**", and, of the three
shipped agents, "all three are **accelerators only**. Every document they serve
stands alone without them."

## What the initiative must deliver

1. A stated test separating what a project may override from what it may not,
   written where the next author will find it.
2. A classification of every shipped skill, reference document and agent against
   that test.
3. A composition mechanism for procedures that are not lifecycle stages.
4. The conversion of everything the classification marks overridable, with
   today's text becoming the default.
5. A way for a reader to tell the two kinds apart without consulting the
   classification.

## The test

The requester could not reduce this to one sentence and supplied examples
instead. Two rules were drawn out of those examples in chat on 2026-09-16 and
agreed; they are separate questions, which is why one sentence kept failing.

**Rule 1 — authority.** TCW owns the *shape* of what is produced: the three axes'
data model, the artifacts, the transitions, the configuration surface, and TCW's
own upstream processes. The project owns the *conduct* that produces it — which
tools, which advisors, which review, which QA, which git workflow.

**Rule 2 — payload.** A skill carrying no procedure of its own has nothing to
override, whatever Rule 1 would say about its subject. This is why the four
`tcw-commands-*` skills are excluded: they are shorthand for running a range of
lifecycle stages, and once the routing item lands, all of their substance is an
invocation of `tcw-work-stage`, which is already dynamic. That is not a claim of
authority over their subject — it is the observation that there is no text there
to configure.

## Classification given by the requester

**Fixed under Rule 1.** `skills/tcw-taxonomy/SKILL.md`,
`skills/tcw-work/SKILL.md` and `skills/tcw-capabilities/SKILL.md`, because they
describe the fundamentals of the three axes and using TCW means adhering to the
design patterns and structure they entail. `skills/tcw-configure/*`, because the
configuration surface is fixed — a user cannot override how the `tcw` CLI works,
short of a PR or a fork. `skills/tcw-extras-report/SKILL.md`, because how to
report issues to TCW is for the TCW maintainers alone to decide.
`skills/tcw-setup/SKILL.md`, because installing and repairing the CLI is TCW's
own authority.

**Fixed under Rule 2.** `skills/tcw-commands-process-inbox` (`inbox`, `request`),
`skills/tcw-commands-plan-work` (`request`, `spec`, `plan`),
`skills/tcw-commands-drive-work-to-completion` (every stage through `verify`) and
`skills/tcw-commands-verify-work` (`verify`).

**Overridable.** `skills/tcw-extras-autonomous-work/SKILL.md`;
`skills/tcw-extras-triage-issues/SKILL.md`;
`skills/tcw-work/references/procedures/*` — all five, with their current contents
as the defaults; `skills/documentation-sync/SKILL.md`;
`skills/tcw-post-mortem/SKILL.md`; `skills/tcw-work-create/SKILL.md`.

`skills/tcw-work-stage/SKILL.md` is already the case to imitate. Strictly its
files are not mutable — they are a template around the real prompt, delivered by
dynamic context injection.

**Not classified by the requester, and left for `spec` to resolve against the
two rules:** the three files under `agents/`; the seven stage documents under
`skills/tcw-work/references/lifecycle/`; the other documents under
`skills/tcw-work/references/` (`commands.md`, `cross-node-deltas.md`,
`epic-deltas.md`, `hooks.md`, `tags.md`, `transitions.md`); and the reference
directories belonging to skills already classified —
`documentation-sync/references/`, `tcw-setup/references/`,
`tcw-work-create/references/`. Where a skill is overridable, whether its
references travel with it is part of the same question.

## The marker

The requester proposes a field in each skill's YAML frontmatter — something like
`dynamic_skill: true/false` — signalling whether a skill is intended to be
dynamic, and states plainly that no AI harness consumes an invented key: its
value is to a human reader. The key's name, whether `tcw validate` should enforce
it, and whether the signal should instead be derived from the presence of a
composition point are open for `spec`.

## Constraints

- **This is planned against a tree that does not exist yet.** The requester's
  instruction is to write the plan assuming
  `2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`
  is done and merged; it is recorded as a blocker. Three of the things it lands
  are load-bearing here: `tcw-work/SKILL.md` routing agents to `tcw-work-stage`
  and the four command skills invoking it, which is what empties them under
  Rule 2; `tcw work stage validate`, as the shape of a verb guarding a skill
  invocation; and harness detection with its notice to a harness that cannot run
  injected commands, which every converted skill will need.
- **A project that has configured nothing must behave exactly as it does today.**
- **Prefer extending the existing composition mechanism to inventing a second
  one.** Two ways to say "compose a prompt" is the drift this initiative exists
  to remove.
- The abstraction litmus test governs, per `docs/lifecycle/abstraction.md`.
- Children must be shaped so each can land independently, with ordering recorded
  as blockers rather than implied by prose.

## Out of scope

- The version-cut half of the same principle —
  `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`.
  If it lands first, a child touching `documentation-sync` reuses its config
  rather than adding a second way to say the same thing.
- Renaming skills or agents —
  `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`.
- Writing missing Codex paths into `tcw-setup` and `tcw-work-stage` —
  `2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability`.
  It treats the same violation class with the opposite remedy, so the two must
  agree on which skills get which treatment.
- The Proposit workspace's `autonomous-work-proposit`, a sibling copy of the
  exemplar in another repository.

## Notes

- Reference material: asked on 2026-09-15; none provided. The requester
  considers the repository sufficient, the same answer recorded on
  `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`.
- Answers given in chat and not otherwise visible in this document:
  - the initiative is an epic with children, chosen over one item and over two
    sequenced items, because the mechanism alone is comparable in size to the
    routing item;
  - of the four skills the requester's examples left unsaid,
    `documentation-sync`, `tcw-post-mortem` and `tcw-work-create` are
    overridable and `tcw-setup` is not;
  - asked what should become of the exemplar's advisor pair, the requester first
    chose to remove the named tools entirely, with the roster coming from the
    project. That was answered before the scope widened, and it collided with
    the constraint that a project configuring nothing behaves as it does today:
    a skill shipping no roster would leave an unattended run with no advisors at
    all. Put back to the requester on 2026-09-16, who resolved it the other way
    — **today's text ships as the `builtin` default**. So the skill body stops
    mandating anything, the Codex and Opus roster moves into TCW's shipped
    default where a project can replace it, and behaviour is preserved
    everywhere. The consequence to carry into `spec`: TCW still ships an
    opinionated default naming a third-party CLI, and that is accepted. What
    changes is that it is a default rather than a requirement.
- Inference, not the requester's words: the two rules are this session's
  articulation of examples the requester supplied, agreed in chat but not
  authored by them; the list of documents left unclassified is this session's,
  from reading the tree.
- The narrower item
  `2026-09-15-let-a-project-override-the-tools-and-procedures-tcw-s-own-skills-mandate`
  was filed for this on 2026-09-15 and discarded as superseded when the scope
  widened. Its body is the ancestor of this one.
- Promoting that item rather than replacing it was not possible:
  `tcw work edit` has no `--type`, which is
  `2026-09-15-let-tcw-work-edit-change-an-item-s-type-to-or-from-epic`. The item
  was one commit old with no artifacts beyond `intake.md`, so it was recreated
  rather than edited by hand.

## References

- `skills/tcw-work/references/procedures/delegation.md` — the doctrine this
  violates, in TCW's own words; the stated test should be derived from it.
- `skills/tcw-work-stage/SKILL.md` — the architectural template: a fixed file
  whose payload is injected.
- `skills/tcw-configure/references/work.md` — the existing composition mechanism
  and its binding kinds, and the `work.trunk-branch` and
  `work.publish-transitions` keys the exemplar's closeout rule bypasses.
- `2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`
  — the blocker; its `spec.md` carries the harness-detection design and the
  per-skill routing verdicts this initiative inherits.
- `2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage`
  — the mirror-image question, worth reading before the classification: it holds
  off on shipping this repo's own invention to every TCW user because "a rule
  that ships to every TCW user should have been used in anger first".
