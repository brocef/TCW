# A `skill:` prompt binding is never validated, and a typo resolves silently

Found while building the eval harness
(`2026-07-22-evaluate-and-refine-the-plugin-skills-with-an-eval-harness`).
Filed rather than fixed: that item's spec lists "no `tcw` command-surface or
store changes" as a non-goal, and fixing this means editing `tcw/`.

## What happens

`_resolve_one` (`tcw/work/resolve.py:193`) resolves a `skill` binding to the
literal string `Invoke the <name> skill.` and never checks that the named skill
exists. Nothing else checks either.

Reproduced on a scratch node whose `tcw-config.yaml` binds a skill that exists
nowhere on disk or in any plugin:

```
$ grep -A1 'verify:' tcw-config.yaml
        prompt:
        - skill: eval-verify-marker

$ find . -iname '*eval-verify-marker*'          # nothing

$ tcw validate; echo $?
0

$ tcw work stage prompt verify <slug> | grep 'Invoke the'
Invoke the eval-verify-marker skill.
```

So a project can mistype a skill name, `tcw validate` stays green, and every
agent reaching that stage is told to invoke something that does not exist.

## Why it matters more than a typo usually would

The other four prompt kinds all fail loudly on a bad value. A `file` binding
naming a missing path raises, and a `generate` binding whose script fails turns
into a `ResolveError` that exits 1 with no stdout. `skill` is the only kind that
takes an unusable value and resolves as though nothing were wrong.

It is also the kind whose effect is hardest to observe: the resolved text looks
correct in isolation, and only the agent's failure to find the skill reveals it.

## What it is not

Not a request to inline the skill's body. Resolving to a pointer is the right
design under the harness-compatibility rule, since a Codex reader and a Claude
reader both get the same sentence.

## Possible shapes, in rough order of cost

1. `tcw validate` warns when a `skill` binding names something not present in
   any known skill source. Needs a way to enumerate skills, which may not exist.
2. The resolved text names the binding's origin, so a reader who cannot find the
   skill can at least see which config declared it.
3. Documented as intended, and `skill` bindings are declared unvalidatable.

Option 1 is the one that matches how the other kinds behave; option 3 is honest
if enumeration is genuinely out of reach.
