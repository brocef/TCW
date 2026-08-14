# Lifecycle bindings

A node may bind its own agent skills or shell commands to any stage or transition
id, in `tcw-config.yaml`:

```yaml
work:
    lifecycle:
        stages:
            spec: [{ skill: superpowers:brainstorming }]
        transitions:
            complete:
                pre: [{ command: "pytest -q" }]
```

A binding declares one **kind** explicitly — a bare string is rejected, never
guessed at. Declaration order is significant. `tcw validate` rejects unknown ids,
malformed shapes, blank or duplicated references, a kind used in a position that
does not allow it, and a malformed `when:`.

## Roles, kinds, and conditions

| Role       | Where                                            | Kinds                                    | How they combine |
| ---------- | ------------------------------------------------ | ---------------------------------------- | ---------------- |
| `check`    | `stages.<id>.pre`, `transitions.<id>.pre`/`post` | `command`, `skill`                       | Run in order; first failure stops. |
| `prompt`   | `stages.<id>.prompt`, or a bare stage list       | `blob`, `file`, `generate`, `builtin`, `skill` | **All** matches, concatenated in declaration order. |
| `artifact` | `artifacts.<name>`                               | `blob`, `file`, `generate`, `builtin`    | **First** match wins; `builtin` is the fallback and goes last. |

`blob:` is inline text · `file:` is a node-relative path, confined to the node ·
`generate:` is a script that receives the item as JSON on stdin and prints the
text · `builtin: true` is TCW's own default · `skill:` is a name, not
instructions, and is the weakest kind.

Any binding may carry `when: {tags: […], not_tags: […], type: …}` — keys ANDed, a
list meaning any-of. Three keys by decision; anything harder is a `generate:`
script.

```yaml
work:
    lifecycle:
        stages:
            spec:
                pre: [{ command: "./bin/ready.sh" }]
                prompt:
                    - builtin: true
                    - generate: ./bin/spec-prompt.py
                      when: { tags: [bug] }
        artifacts:
            spec: [{ builtin: true }]
```

**A bare list under a stage id is still valid** and still means `prompt:`. It is
the one place `command:` is accepted in a prompt position — the explicit
`prompt:` key rejects it and points at `generate:` — because the legacy shape
predates the distinction and cannot be renamed.

## Finding what is bound

```
tcw work lifecycle [work-ref]        # every id, its contract, and its bindings
tcw work lifecycle --json            # the same, machine-readable
```

**This command is the contract.** It reads identically under Claude and Codex,
runs nothing, and changes nothing. Consult it before performing a stage.

`tcw work lifecycle --stage <id> --directive` emits one ready-to-follow
instruction line, or nothing when unbound. It exists for Claude's dynamic context
injection and is **sugar over the command above, never the path** — Codex
receives no injection, so nothing may depend on it.

`--phase pre|prompt` narrows a stage and `--phase pre|post` narrows a transition.
A stage has no `post`: its exit checks belong on the next stage's `pre`, and
asking for one is an error rather than empty output.

## What runs, and what does not

TCW runs `command:` bindings around transitions:

- `pre` runs **before anything is written**. A non-zero exit aborts the
  transition; the item does not move and no field is set. `[gated]`
- `post` runs after. A failure **never rolls back** — the move and its commit
  have happened. TCW reports it and exits non-zero, and the item stays where it
  went. `[auto]`

Commands run through the shell, from the node root, with `TCW_SLUG`,
`TCW_STATUS`, `TCW_TRANSITION`, and `TCW_NODE_ROOT` in the environment, under a
300-second default timeout (`work.lifecycle.timeout`).

A check carrying a `when:` runs only when it matches — and a check that cannot be
evaluated, because no item was resolved, does **not** run.

`generate:` hooks additionally receive `{"item": …, "hook": …}` on stdin — `item`
is the document `tcw work show --json` prints, with its `body` capped at 64 KiB
and `hook.body_truncated` saying so — plus `TCW_HOOK_ROLE`, `TCW_HOOK_KIND`,
`TCW_HOOK_ID`, and `TCW_HOOK_PHASE`. Output is capped
(`work.lifecycle.output-cap`, 64 KiB by default) and a **non-zero exit discards
everything the script printed**, so half a prompt never reaches you. Resolution
can re-run, so a generator must be side-effect-free.

**`skill:` bindings are named, never executed** — TCW cannot invoke a skill; you
can. Invoking it is `[judgment]`: nothing enforces it.

## Two limits worth knowing

**A configured-but-missing skill cannot fail closed everywhere.** Codex cannot
enumerate skills to confirm one exists. Report it and stop; never proceed as
though it ran, and never build anything that depends on such a check firing.

**`tcw serve` runs no hooks.** A transition made from the web app performs and
commits the move but skips every binding — a `pre` hook that would block it does
not block it there.

`tcw-config.yaml` is a file in the user's own repository and is trusted exactly
as much as any other file there. This is not a sandbox.
