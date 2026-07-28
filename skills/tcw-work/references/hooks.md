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

A binding is `{skill: …}` **or** `{command: …}`, declared explicitly — a bare
string is rejected, never guessed at. Declaration order is significant.
`tcw validate` rejects unknown ids, malformed shapes, blank or duplicated
references, and a binding declaring neither or both keys.

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
