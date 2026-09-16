# Compose a procedure's instructions from project bindings the way a stage's are composed

Child 2 of
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
The epic's `initial-request.md`, `spec.md` and `plan.md` are the requester's
agreed position; this request narrows them to this child.

## What is wanted

A way for a project to replace the text of a TCW procedure that is not a
lifecycle stage, reusing the machinery that already composes stage prompts: the
same binding kinds, the same `when:` conditions, the same `builtin` floor so a
project that configures nothing gets TCW's shipped text, and the same resolver.

Configuration lives under `work.procedures` in `tcw-config.yaml`, beside
`work.lifecycle` rather than inside it.

### The command

Agreed with the requester on 2026-09-16:

```
tcw work procedure prompt <id> [slug]
```

- It mirrors `tcw work stage prompt <stage> [slug]`, so the two places a skill
  gets its instructions from read the same way.
- **The work item is optional**, and exists so a project can vary a procedure by
  item. With a slug, the item reaches the bindings exactly as it does for a
  stage prompt: a `when:` condition can match on its tags or type, and a
  `generate:` script receives it as JSON on standard input. The requester's
  example is a script that returns a different procedure depending on the item.
- There is no `procedure gate` and no `procedure validate`. A procedure is not
  tied to an item's status, so there is nothing to gate, and a converted skill
  always serves the same procedure id, so there is no id for a caller to get
  wrong. Add either only when something needs it.

### Procedure ids

Short ids that do not depend on skill names — for example `autonomous-work`, not
`tcw-extras-autonomous-work`. Projects type these ids into `tcw-config.yaml`, and
`2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names` plans
to rename skills; ids tied to skill names would break every project's
configuration when that lands. The exact id list is for `spec`, from the epic's
classification.

## Constraints

- A project that has configured nothing behaves exactly as it does today.
- One binding grammar: `Binding`, its kinds and `when:` are reused; only the id
  space, the config key and the command are new.
- Bindings are read, never run as checks — as for stage prompts.
- The abstraction litmus test governs (`docs/lifecycle/abstraction.md`).
- Anything required belongs in the `tcw` CLI, not in context injection alone
  (`docs/lifecycle/harness.md`).
- Work happens in a git worktree (requester's instruction for this run). This
  item changes `tcw/`, so its tests and CLI runs must use the worktree's code
  without re-pointing the shared editable install, which other sessions use.

## Out of scope

- Converting any skill to use the mechanism (children 3–6).
- The rules document and the `dynamic_skill` marker (child 1).
- Letting a project add procedure ids of its own.

## Notes

- Reference material: asked on 2026-09-16; none provided beyond what the epic
  already cites.
- Behaviour already in the code that `spec` must decide about, not a request:
  with no item, a `when:` condition never matches (`tcw/store/base.py`,
  `matches`). So `tcw work procedure prompt <id>` without a slug skips every
  conditional binding — and if a procedure's only bindings are conditional, it
  resolves to nothing rather than to TCW's default, which is how stage prompts
  behave today.
- The epic reserves the ledger deltas `added: work/run-a-procedure`,
  `work/configure-procedures` and `changed: work/configure-the-work-lifecycle`.
