# Make every procedural skill in TCW overridable by the project that uses it

## The initiative

TCW composes a lifecycle stage's instructions at read time: `builtin: true` is
TCW's own text, and a project adds its own with `file:` or `skill:` entries under
`work.lifecycle.stages.<id>.prompt`. The skill carries the reasoning; the project
carries the facts. `skills/tcw-work-stage/SKILL.md` is the architectural template
for this — the file itself is nearly empty of instruction, and its body is two
injected commands that fetch the stage document and the project's resolved
prompt.

**That composition stops at lifecycle stages.** Every other procedure TCW ships
is fixed prose, and several of them encode one maintainer's personal working
practice as a requirement on everybody.

The exemplar is `skills/tcw-extras-autonomous-work/SKILL.md`. It describes a
procedure for working TCW items unattended, and mandates: exactly two named AI
advisors — the Codex CLI with its exact invocation (line 22) and an Opus subagent
via Claude Code's `Agent` tool (line 26); `SendMessage` (line 38); a claim that
"Codex is the reliable half" (line 40); an agent TCW does not ship,
`adversarial-code-reviewer` (line 49, its only occurrence in the repository); one
git closeout, "merge the feature branch into main **locally**. Never `git push`"
(line 55); and one version policy, "Never cut one. Accumulate into `upcoming.md`"
(line 54). The adjudication rule is built on the advisor count — "not a majority
(there is no majority of two)" (line 32) — so the number is load-bearing prose
rather than an example. None of it is declared: the skill carries neither
`allowed-tools:` nor `compatibility:` frontmatter, although `tcw-setup` and
`tcw-extras-triage-issues` both declare theirs, so its hardest dependency — a
second AI CLI, installed, on PATH and authenticated — is invisible to a reader
deciding whether the skill applies to them.

These are the requester's own requirements for autonomous work and they are
reasonable ones. They should not be imposed on every TCW user. Another project's
advisor might be a different AI, or another Claude agent constrained to a
particular skill or agent definition, or a human.

This also contradicts TCW's own stated doctrine, in
`skills/tcw-work/references/procedures/delegation.md`: "Delegable means
permitted, never required", "**No behavior depends on it**", and, of the three
shipped agents, "all three are **accelerators only**. Every document they serve
stands alone without them."

## What the initiative must deliver

1. **A stated test** separating skills a project may override from those it may
   not, written down where the next author will find it.
2. **A classification** of every shipped skill, reference document and agent
   against that test.
3. **A composition mechanism** for procedures that are not lifecycle stages —
   the generalization of `work.lifecycle.stages.<id>.prompt` — such that a
   project that has configured nothing keeps today's behaviour, because today's
   text becomes the `builtin` default.
4. **The conversion** of each skill the classification marks overridable.
5. **A frontmatter marker** so a reader can tell the two kinds apart without
   consulting the classification.

## The test, as the requester states it

Two rules do the work. One sentence kept failing because they are separate
questions.

**Rule 1 — authority.** TCW owns the *shape* of what is produced: the three axes'
data model, the artifacts, the transitions, the configuration surface, and TCW's
own upstream processes. The project owns the *conduct* that produces it — which
tools, which advisors, which review, which QA, which git workflow.

**Rule 2 — payload.** A skill that carries no procedure of its own has nothing to
override, whatever Rule 1 would say about its subject. This covers the four
`tcw-commands-*` skills: they are shorthand for running a range of lifecycle
stages, and once
`2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`
lands, all of their substance is an invocation of `tcw-work-stage`, which is
already dynamic. Excluding them is not a claim of authority over their subject;
it is the observation that there is no text there to configure.

## Classification, as the requester gave it

**Fixed — Rule 1 (TCW's own authority):**

- `skills/tcw-taxonomy/SKILL.md`, `skills/tcw-work/SKILL.md`,
  `skills/tcw-capabilities/SKILL.md` — these describe the fundamentals of the
  three axes. Using TCW means adhering to the design patterns and structure they
  entail.
- `skills/tcw-configure/*` — how to configure TCW. The configuration surface is
  fixed: a user cannot override how the `tcw` CLI works, short of a PR or a fork.
- `skills/tcw-extras-report/SKILL.md` — how to report issues to TCW. The TCW
  maintainers alone decide that.
- `skills/tcw-setup/SKILL.md` — installing and repairing the CLI is TCW's own
  authority.

**Fixed — Rule 2 (no payload):**

- `skills/tcw-commands-process-inbox` (`inbox`, `request`),
  `skills/tcw-commands-plan-work` (`request`, `spec`, `plan`),
  `skills/tcw-commands-drive-work-to-completion` (every stage through `verify`),
  `skills/tcw-commands-verify-work` (`verify`).

**Overridable:**

- `skills/tcw-extras-autonomous-work/SKILL.md` — the exemplar.
- `skills/tcw-extras-triage-issues/SKILL.md`.
- `skills/tcw-work/references/procedures/*` — all five
  (`audit-backlog.md`, `consolidate-plans.md`, `decompose.md`, `delegation.md`,
  `search.md`), with their current contents as the defaults.
- `skills/documentation-sync/SKILL.md`.
- `skills/tcw-post-mortem/SKILL.md`.
- `skills/tcw-work-create/SKILL.md`.

`skills/tcw-work-stage/SKILL.md` is already the core mutability case and the
pattern the rest should follow. Strictly its files are not themselves mutable —
they are a template around the real prompt, delivered by dynamic context
injection (the `` !`command` `` syntax).

## The frontmatter marker

The requester proposes a field in each skill's YAML frontmatter — something like
`dynamic_skill: true/false` — signalling whether the skill is intended to be
dynamic. It is understood that no AI harness consumes an invented key; its value
is to a human reader. The exact key name, whether `tcw validate` should enforce
it, and whether it should instead be derived from the presence of a composition
point are for `spec`.

## Sequencing

**This initiative assumes
`2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`
is done and merged**, and is recorded as blocked by it. Plan against the
post-merge state of the tree. Three things it lands are load-bearing here:

- `skills/tcw-work/SKILL.md` routes agents to the `tcw-work-stage` skill rather
  than naming stage documents, and the four `tcw-commands-*` skills invoke it —
  which is what empties them under Rule 2.
- `tcw work stage validate` establishes the shape of a verb that guards a skill
  invocation and adapts its output to the harness.
- Harness detection (process tree, environment-variable fallback) and the notice
  "Your AI agent harness does not support dynamic context injection. You will
  need to manually run all commands with !`command` to interpret this skill."
  Any skill converted to injection needs exactly that fallback, so it should be
  reused rather than reinvented.

## Constraints

- **A project that has configured nothing must behave exactly as it does today.**
  Today's prose becomes the `builtin` default for every converted procedure.
- **Prefer extending the existing composition mechanism to inventing a second
  one.** Two ways to say "compose a prompt" is the drift this initiative exists
  to remove.
- **The abstraction litmus test governs**, per `docs/lifecycle/abstraction.md`.
- Child items must be shaped so each can land independently; ordering between
  them is recorded with `--blocked-by`, never implied by prose.

## Out of scope

- The version-cut half of the same principle, tracked as
  `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`.
  If it has landed by the time a child touches `documentation-sync`, reuse its
  config rather than adding a second way to say the same thing.
- Renaming skills or agents —
  `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`.
- Writing missing Codex paths into `tcw-setup` and `tcw-work-stage` —
  `2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability`.
  That item fixes the same violation class with the opposite remedy, so the two
  must agree on which skills get which treatment.
- The Proposit workspace's own `autonomous-work-proposit` skill, which is a
  sibling copy of the exemplar in a different repository.

## Origin

Raised in chat on 2026-09-15, after reading `tcw-extras-autonomous-work` and
noticing it requires Codex reviews. Described by the requester as "a violation of
the polymorphic and generic behavior that we've been building out recently with
the dynamic context injection and dynamic prompts for the lifecycle stages", with
the ask to re-evaluate all comparable commands and procedures "to make sure that
they are indeed overridable by the individual project maintainers so that we
don't require certain technologies or steps or procedures like we do here".

Supersedes
`2026-09-15-let-a-project-override-the-tools-and-procedures-tcw-s-own-skills-mandate`,
filed the same day for the narrower version of this before the scope was
expanded.

## References

- `skills/tcw-work/references/procedures/delegation.md` — the doctrine this
  violates, in TCW's own words; the stated test should be derived from it.
- `skills/tcw-work-stage/SKILL.md` — the architectural template: a fixed file
  whose payload is injected.
- `skills/tcw-configure/references/work.md` — the existing composition mechanism
  and its binding kinds, plus the `work.trunk-branch` and
  `work.publish-transitions` keys that the exemplar's closeout rule bypasses.
- `2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`
  — the blocker; its `spec.md` carries the harness-detection design and the
  per-skill routing verdicts.
- `2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage`
  — the mirror-image question, worth reading before the classification: it holds
  off on shipping this repo's own invention to every TCW user because "a rule
  that ships to every TCW user should have been used in anger first".

Blocked by 2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments: this initiative plans against the tree that item leaves behind, and Rule 2's exclusion of the four command skills only holds once it has emptied them.
