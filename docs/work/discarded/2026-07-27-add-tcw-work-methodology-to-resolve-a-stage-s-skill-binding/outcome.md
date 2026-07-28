# Outcome — superseded, not built

This child was scoped to add `tcw work methodology <stage>`. Child 2b resolved
both halves of it, and the second half should never have shipped.

## 1. The command already exists, under another name

Child 3's stated value, quoted from the epic spec:

> every stage document can then carry one harness-neutral step — run
> `tcw work methodology <stage>` and invoke the skill it names — reading
> identically under Claude and Codex

Child 2b shipped `tcw work lifecycle`, which does exactly that:

```
$ tcw work lifecycle --stage spec --directive
For this stage, invoke the superpowers:brainstorming skill.
```

Human and `--json` modes report the same binding alongside the stage's objective,
inputs, produced artifact, and gates. It reads identically under both harnesses,
it never executes anything, and it is already the instruction the `tcw-work`
skill gives.

Shipping a second command that answers the same question is precisely the defect
this initiative exists to remove: two surfaces describing one thing, free to
drift apart.

## 2. The remaining half contradicts the epic's own non-goals

The only part of child 3 not covered by `tcw work lifecycle` is the fallback:

> Resolution: configured binding → **shipped default**.
> Ship a default binding per stage, or none where TCW has no opinion.

A shipped default means TCW naming a particular methodology skill for a
particular stage. The epic spec's non-goals list, first item:

> - Built-in methodology presets, or custom prompt bodies.

Child 3 would have shipped the thing its own parent forbids. That was not visible
when the child was written — it became visible once `tcw work lifecycle` existed
and the fallback was the only distinguishing feature left.

## What is genuinely lost

Nothing that was wanted. A node with no binding for a stage gets no instruction,
and the stage proceeds on TCW's own guidance — which was child 3's specified
behavior for the unresolved case anyway (`prints nothing and exits 0`).

## What child 4 inherits

The harness-neutral step for every stage document is:

> Run `tcw work lifecycle --stage <id>` and honor any binding it reports.

That is one command, no fallback chain, no second concept. The `--directive`
form is Claude-only sugar over it, never the path.

## Notes

The deferrals recorded against child 3 — a repo-local
`docs/work/lifecycle/<stage>.md` override, three-tier `bare-wins-local`
resolution, `reset`, and any definition of what a methodology *document* must
contain — remain deferred, and now slot in ahead of the configured binding in
`tcw work lifecycle` rather than in a command of their own.
