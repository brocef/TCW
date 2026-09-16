# State the two rules for an overridable skill and mark every skill with its verdict

Child 1 of the epic
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Read that epic's `spec.md` (Design → "The test, stated once", "The marker") and
`plan.md` (task 1, "File ownership") before specifying.

## What to deliver

1. **A rules document under `skills/`** stating the two rules, reachable from a
   shipped skill so a future skill author meets it without being told:
   - **Rule 1 — authority.** TCW owns the *shape* of what is produced: the three
     axes' data model, the artifacts, the transitions, the configuration surface,
     and TCW's own upstream processes. The project owns the *conduct* that
     produces it — which tools, which advisors, which review, which QA, which git
     workflow.
   - **Rule 2 — payload.** A skill carrying no procedure of its own has nothing
     to override, whatever Rule 1 says about its subject. Checked first.

   It should also say why a project overrides a procedure's *text* but cannot add
   a procedure id of its own (the epic spec's "A second id space invites a third"
   risk).
2. **A verdict with a reason for every shipped skill, reference document and
   agent.** The requester's classification:
   - Fixed under Rule 1: `tcw-taxonomy`, `tcw-work`, `tcw-capabilities`,
     `tcw-configure/*`, `tcw-extras-report`, `tcw-setup`.
   - Fixed under Rule 2: the four `tcw-commands-*` skills.
   - Overridable: `tcw-extras-autonomous-work`, `tcw-extras-triage-issues`,
     `tcw-work/references/procedures/*` (all five), `documentation-sync`,
     `tcw-post-mortem`, `tcw-work-create`.
   - `tcw-work-stage` gets its own verdict and reason: it composes already.

   Left for this item to resolve against the two rules: `agents/*` (three);
   `skills/tcw-work/references/lifecycle/*` (the stage documents); the other six
   files under `skills/tcw-work/references/` (`commands.md`,
   `cross-node-deltas.md`, `epic-deltas.md`, `hooks.md`, `tags.md`,
   `transitions.md`); and the `references/` directories of already-classified
   skills (`documentation-sync`, `tcw-setup`, `tcw-work-create`) — including
   whether an overridable skill's references travel with it.
3. **A frontmatter marker on every `skills/*/SKILL.md`**, proposed as
   `dynamic_skill: true|false`. Inert to both harnesses; for a human reader. A
   test fails if a skill lacks it or if its value disagrees with the rules
   document's classification. Decide the key name and whether `tcw validate` also
   reports it, and say why.

## Constraints

- **Frontmatter only.** This child edits every `SKILL.md`'s frontmatter and no
  body; children 3–6 own the bodies and must not touch the marker.
- Confirm no test enumerates permitted `SKILL.md` frontmatter keys before adding
  one (an unverified assumption in the epic spec's Notes).
- The classification is a judgment. The user reviews the verdicts before the
  conversion children start, because every later child inherits them.

## Acceptance criteria carried from the epic

Epic criteria 1, 2 and 3.

## Origin

Opened by the epic's `implement` stage (plan task 1) on 2026-09-16.
