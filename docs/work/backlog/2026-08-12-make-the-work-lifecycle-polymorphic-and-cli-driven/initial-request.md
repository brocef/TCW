# Make the work lifecycle polymorphic and CLI-driven

## Product changes

TCW stops being one opinionated way to run a work item and becomes the
_framework_ for running one. The stages, transitions, and artifacts stay fixed;
what an agent is told to **do** at each stage becomes the node's to choose —
written inline in `tcw-config.yaml`, kept in a plain file, or produced by a
script that TCW calls. A node that configures nothing still gets a good default,
delivered by the CLI rather than by a skill.

## Technical changes

Formalize what a lifecycle hook _is_ by splitting it by role — shell checks that
gate, one artifact factory, and prompt producers that return text — and add hook
kinds that can resolve to text without an agent's cooperation (`file`, `blob`,
`generate`). Add a conditional matcher so a binding can depend on the item, an
abstract JSON projection of a work item that both `tcw work show --json` and
`generate` hooks consume, an explicit stage-entry command that runs the sequence,
and artifact templates.

## Meta changes

Moves the default stage instructions out of `skills/tcw-work/references/` and
into the CLI, which is the layer CLAUDE.md says a guarantee belongs in. Extends
`skills/tcw-work/references/hooks.md`, the limited version of this that exists
today.

---

## Requested outcome

> I want to turn the whole TCW work lifecycle into a polymorphic process, of
> sorts. […] I want the TCW work system to be the framework for how agents go
> about organizing, planning, and executing work but the exact details on how to
> do each stage of the lifecycle is fully extensible. The extensibility of the
> system should allow for a variety of approaches. The simplest approach is to
> write in custom strings for the prompt instructions for a given stage and a
> highly extensible approach would be to use a full `generate` hook where we
> basically call an external system (script) in order to resolve the next system
> state.

The requester also asked that every idea below be treated as a candidate
implementation rather than a decision — "my word is not gospel."

## What was asked for

1. **Hook kinds beyond `skill` and `command`.** Add `file` (read a text file, its
   contents are the instructions), `blob` (the instructions written inline in
   YAML), and `generate` (run a script, hand it the work item as JSON plus which
   hook is firing, treat its stdout as the instructions).
2. **Conditional bindings.** A binding may depend on the item's characteristics —
   a `feature`-tagged item gets brainstorming instructions at `request`, a
   `bug`-tagged one gets debugging instructions.
3. **Artifact factories.** Every lifecycle artifact (`initial-request.md`,
   `spec.md`, …) gets a CLI command that creates it from a template, and the
   template is overridable. Combined with (2): a `bug` item's request template
   carries a "steps to reproduce" section; a feature's carries UI/UX references.
   _The requester explicitly left open when in the lifecycle this fires._
4. **Roles, named.** Today's `work.lifecycle.<stage>` bindings produce
   instructions for the agent and today's transition `pre`/`post` bindings run
   programs, but nothing in the model says so. Name the distinction. The
   requester's proposed ordering, per stage: pre-stage shell hooks → the one
   artifact-generation hook → prompt-generating hooks → _(the agent or human does
   the stage)_ → _(a transition is initiated)_ → post-stage shell hooks, which
   abort on failure → the transition is performed. Shell-hook stdout/stderr is
   readable by the agent but is never a prompt; only the prompt-generating hooks
   produce one.
5. **Reach all of it through the CLI**, including
   `tcw work lifecycle --transition <id> --phase pre|post --directive`, which
   does not exist yet.
6. **`tcw work show --json`** — a JSON representation of a work item and its
   metadata.
7. **Default stage instructions** shipped with TCW, used when a node overrides
   nothing. Loosely based on [obra/superpowers], condensed to something
   lightweight and generally useful.

## Decisions taken at request time

Put to the requester before this was written, and answered:

- **The CLI owns the default stage instructions.** They become data the `tcw` CLI
  emits; `skills/tcw-work/references/stage-*.md` shrink to thin routers pointing
  at it. Rejected: leaving the defaults in the skill, and generating one from the
  other with a drift test.
- **A new explicit stage verb fires the stage-phase hooks.** `tcw work lifecycle`
  stays read-only. Rejected: folding stage checks into transitions, and making
  `lifecycle` itself execute.
- **Conditions are a fixed matcher plus `generate`.** A small `when:` clause over
  known item fields, with anything harder delegated to a `generate` hook.
  Rejected: a boolean expression language in YAML, and dropping `when:` entirely.
- **This is an epic with child items**, not one large item. Rejected: a single
  phased item, and a two-item machinery/content split.

## Constraints

- **The two ladders are load-bearing.** A stage produces an artifact; a
  transition moves status; nothing is both (`tcw/store/base.py:510-527`). Three
  stages — `request`, `spec`, `plan` — run entirely inside `backlog` with **no
  transition between them**, so the requester's step 6 ("post-stage hooks fire;
  if any fail the transition is aborted") has nothing to attach to for those
  three. Whatever ships must say honestly which checks are `[gated]` and which
  are `[judgment]`.
- **`tcw work lifecycle` is currently guaranteed to run nothing and change
  nothing**, and both the skill and the stage documents rely on that. Adding
  execution to it would break a guarantee already depended on.
- **Both harnesses stay first-class.** Anything that must be guaranteed belongs
  in the CLI, which behaves identically under Claude and Codex.
- **The abstraction litmus test applies.** Hook execution deliberately lives
  outside the store (`tcw/work/hooks.py:1-19`) and should stay there. The item
  JSON must be an abstract projection — item fields plus artifact presence — not
  a folder listing, since a remote adapter has to be able to produce it.
- **Existing configuration must keep working.** `work.lifecycle.stages` /
  `.transitions` and the `skill:` and `command:` binding kinds are public API; a
  user's `tcw-config.yaml` keys on them.
- **`tcw serve` runs no hooks** and should not start running them from an HTTP
  handler. Whatever the web app does about templates has to be decided
  deliberately rather than inherited.

## References

- [obra/superpowers] — the model for the default stage instructions. Take the
  spirit, not the volume: the requester asked for something condensed and
  lightweight.
- `skills/tcw-work/references/hooks.md` — the limited version of this that ships
  today, and the document this work replaces.
- `tcw/store/base.py:510-772` — `Binding`, `TransitionBindings`,
  `LifecyclePolicy`, `LIFECYCLE_STEPS`, and `parse_lifecycle_policy`. The
  `LIFECYCLE_STEPS` table is described in-code as the single source of truth for
  what each stage produces, which is what artifact templates risk duplicating.
- `tcw/work/hooks.py` — execution, and the reasoning for why it is not in the
  store.
- `tcw/work/cli.py:615-721` — `tcw work lifecycle`, `_directive_text`, and the
  `--directive` surface the new `--phase` flag extends.
- `README.md:587-622` — the user-facing description of bindings today.

## Non-goals

- Changing the stage or transition **set**. The seven stages and five transitions
  stay as they are; this is about what happens inside them.
- Making a remote store adapter real. The litmus test still applies to every new
  operation, but `JiraWorkStore` stays unbuilt.
- Sandboxing hooks. `tcw-config.yaml` is trusted exactly as much as any other
  file in the user's repository, and adding executable-by-default hook kinds does
  not change that posture — but it does raise the stakes, and the spec should say
  so plainly rather than quietly.

## Notes

- Filed 2026-08-12 from a `/tcw-plan-work` request.
- The requester flagged a worry that naming a skill in a prompt may not be enough
  to make an agent invoke it on every harness. Worth checking rather than
  assuming: Claude Code exposes a `Skill` tool that takes a name, and Codex
  reads skills too. The stronger argument for the new kinds is different and
  survives regardless — `file`, `blob`, and `generate` all resolve to text that
  TCW can hand over directly, and `skill` is the only kind that cannot.
- Priority 80 and effort/complexity `very-high`: this is the largest open item
  and it changes the layer every other work item runs through.

[obra/superpowers]: https://github.com/obra/superpowers
