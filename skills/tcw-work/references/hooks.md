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

A bare list under a stage id still means `prompt:`. It is the one place
`command:` is accepted in a prompt position — the explicit `prompt:` key rejects
it and points at `generate:` — because the legacy shape predates the distinction
and cannot be renamed.

## The three verbs

`tcw work lifecycle [work-ref]` reports every id, its contract, and its bindings.
**This command is the contract**: it reads identically under Claude and Codex,
runs nothing, and changes nothing. Consult it before performing a stage.
`--stage <id> --directive` is sugar for Claude's dynamic
context injection and **never the path**: Codex receives no injection, so nothing
may depend on it.

`tcw work stage begin <id> <slug>` runs the stage's `pre` checks and prints the
resolved prompt on stdout. **It writes nothing** — no artifact, no draft, no
status change — so it is safe to run purely to find out what to do.

`tcw work scaffold <artifact> <slug>` writes `<artifact>.draft.md` from that
artifact's template. **A draft is not the artifact.** `spec.draft.md` is a file
to type into; the stage still has to write `spec.md`, and until it does, the
board, `--json`, and `tcw serve` all report the artifact absent. Do not treat a
draft as the document, and do not rename one into place without reading it.

Their flags, and what each one refuses and why, are in `--help` and in the
refusal message itself. Read those there rather than here.

## What runs, and what does not

A transition's `pre` checks are `[gated]` — a non-zero exit aborts the move
before anything is written. Its `post` checks are `[auto]`: a failure there never
rolls back.

A check carrying a `when:` runs only when it matches — and a check that cannot be
evaluated, because no item was resolved, does **not** run.

The `item` a `generate:` hook reads on stdin carries its `body` capped at 64 KiB
— a separate limit from the output cap — and `hook.body_truncated` says when it
was cut.

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
