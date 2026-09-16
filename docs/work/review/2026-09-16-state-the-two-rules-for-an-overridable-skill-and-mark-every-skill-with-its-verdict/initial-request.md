# State the two rules for an overridable skill and mark every skill with its verdict

Child 1 of
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
The epic's `initial-request.md`, `spec.md` and `plan.md` are the requester's
agreed position; this request narrows them to this child and does not restate
them.

## What is wanted

1. **The two rules written down** in a document under `skills/`, reachable from
   a shipped skill so a future skill author meets it without being told it
   exists.
   - **Rule 1 — authority.** TCW owns the *shape* of what is produced: the three
     axes' data model, the artifacts, the transitions, the configuration
     surface, and TCW's own upstream processes. The project owns the *conduct*
     that produces it — which tools, which advisors, which review, which QA,
     which git workflow.
   - **Rule 2 — payload.** A skill carrying no procedure of its own has nothing
     to override, whatever Rule 1 says about its subject.

   The document also says why a project can replace a procedure's text but
   cannot add a procedure of its own.
2. **A verdict, with its reason, for every shipped skill, reference document and
   agent.** The requester has already classified the skills (see the epic's
   request, "Classification given by the requester"). The documents the
   requester left unclassified — `agents/*`, the stage documents under
   `skills/tcw-work/references/lifecycle/`, the six other files under
   `skills/tcw-work/references/`, and the `references/` directories of
   `documentation-sync`, `tcw-setup` and `tcw-work-create` — are for this item to
   decide against the two rules.
3. **A frontmatter key on every `skills/*/SKILL.md` named `dynamic_skill`**, with
   the value `true` or `false`. The requester chose this name on 2026-09-16. It
   is for a human reader; no AI harness reads it. A test fails when a skill
   lacks it or when its value disagrees with the rules document.

## Constraints

- Frontmatter only: this item adds the key to every `SKILL.md` and edits no
  skill body. Children 3–6 own the bodies.
- The verdicts are judgments, and the requester reviews them before any
  conversion child starts, because those children inherit them.
- Work happens in a git worktree (requester's instruction for this run).

## Out of scope

- Converting any skill (children 3–6).
- The procedure composition mechanism (child 2).

## Notes

- Reference material: asked on 2026-09-16; none provided beyond what the epic
  already cites.
- Still open for `spec`: whether `tcw validate` should also report the key, or
  the test alone guards it. The epic spec leans to the test alone, because the
  key governs TCW's own skills rather than a user's project.
