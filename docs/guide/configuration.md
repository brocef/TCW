# Configuration

`tcw-config.yaml` is a file in your own repository, trusted exactly as much as
any other file there — this is not a sandbox. It carries the project ID, store
locations, connected projects, the tag set, lifecycle bindings, and the
documentation entries.

See also [The Work component](work.md) and
[Working across repositories](multi-repo.md).

## Binding your own skills and commands to the lifecycle

The lifecycle has named **stages** (each producing one document) and named
**transitions** (each moving status). A node can bind its own agent skills or
shell commands to any of them:

```yaml
# tcw-config.yaml
work:
    lifecycle:
        stages:
            spec: [{ skill: superpowers:brainstorming }]
        transitions:
            complete:
                pre: [{ command: "pytest -q" }]
```

A binding declares **what it is for** and **where its text or command comes
from** — never a bare string, because guessing which one was meant is a class of
bug bought for nothing. `tcw validate` rejects an unknown id, a malformed shape,
a blank or duplicated reference, a kind used in the wrong position, and a
condition with an unknown key or an impossible value.

**Three roles.** A `pre:` binding is a **check** — it runs, and a non-zero exit
matters. A `prompt:` binding resolves to **text an agent reads**; every match is
concatenated in the order you wrote them. An entry under `artifacts:` is a
**template** for one of the lifecycle documents; the first match wins, so a
`builtin` fallback belongs last.

**Six kinds.** `blob:` is text written inline. `file:` is a path in your node —
normalized and confined to it, so a typo cannot quietly read something else.
`generate:` is a script you own, under the contract below. `builtin: true` is
TCW's own default for that stage or artifact — TCW ships instructions for each of
the six lifecycle stages (`inbox` runs before an item exists, so it has none) and
a template for each lifecycle document, and **a stage you have configured nothing
for resolves to them**. `skill:` names an agent skill, which is a name rather than
instructions and is the weakest option. `command:` is for checks.

```yaml
work:
    lifecycle:
        stages:
            spec:
                pre: [{ command: "./bin/ready.sh" }]
                prompt:
                    - builtin: true
                    - blob: "In this repo, specs name their rejected options."
                    - generate: ./bin/spec-prompt.py
                      when: { tags: [bug] }
        artifacts:
            spec:
                - blob: "# Spec\n\n## Repro\n"
                  when: { tags: [bug] }
                - builtin: true
```

**Conditions.** Any binding may carry `when:` with `tags:` (any of), `not_tags:`
(none of), and `type:` — so a bug gets different instructions and a different
template than a feature. Three keys, deliberately; anything harder belongs in a
`generate:` script, which decides in real code.

**The `generate:` contract**, enforced rather than hoped for: stdin is
`{"item": …, "hook": …}` where `item` is the same document
`tcw work show --json` prints; the script's environment carries `TCW_HOOK_ROLE`,
`TCW_HOOK_KIND`, `TCW_HOOK_ID`, and `TCW_HOOK_PHASE` so a one-liner needs no JSON
parser; output is capped (`work.lifecycle.output-cap`, 64 KiB by default) and the
timeout applies; and a script that **exits non-zero contributes nothing at all**,
so half a prompt never reaches your agent. Generators re-run on every
resolution — including every scaffold retry and under `--force` — so write them
side-effect-free.

Your existing configuration keeps working exactly as it did: a bare list under a
stage id is still valid, still means "prompt", and still renders identically.
One exception, and it is the only one: an **empty** prompt list is now rejected
by `tcw validate`, in both spellings — `prompt: []` and a bare
`stages.<id>: []`. It never said anything, and now that an unconfigured stage
falls back to TCW's own instructions it reads as an opt-out it is not. A stage
that should genuinely say nothing binds `{blob: ""}`.

**Checking a stage may run** is `tcw work stage gate <id> <ref>`. It checks the
status legality and runs the stage's `pre` bindings, and that is all it does: it
prints no instructions, so success is exit 0 with nothing on stdout and a line on
stderr naming the verb that does print. The one exception to the reference is
`inbox`: it runs before an item exists, so it is `tcw work stage gate inbox` with
nothing after it, and passing a work item is refused rather than interpreted.

**Reading a stage's instructions** is `tcw work stage prompt <id> [<ref>]`. This
is the only verb that prints them. It checks no status legality and runs no `pre`
bindings — so you can find out what the `plan` stage asks for on an item whose
spec is not written yet, which `gate` correctly refuses. With nothing configured
it prints TCW's own instructions for that stage, so it is useful before you have
written any lifecycle configuration at all. The reference is optional: without one
the instructions resolve generically, with one they resolve for that item, and a
`<project-id>/<slug>` qualifier reads that node's configuration. If the stage is
not legal for the item's status it still prints, and says so on stderr, leaving
stdout to carry the instructions alone.

Because `prompt` gates nothing, what it prints says so: every resolved prompt is
wrapped in a line naming the `gate` command for that stage and a closing section
saying what to do once the stage's output is written. Your own `prompt:` bindings
are wrapped too — overriding what a stage says is not overriding where the
lifecycle goes next.

```sh
tcw work stage gate plan "$slug"       # may it run? checks only, prints nothing
tcw work stage prompt plan             # what does the plan stage ask for?
```

The shipped instructions include a short self-review pass at the stages where one
earns its place — `spec`, `plan`, and `implement`. The `spec` and `plan` instructions name
the item's **own** body artifact rather than a fixed filename: `initial-request.md`
once the `request` stage has written one, and the `intake.md` it arrived as
otherwise, resolved exactly the way `tcw work show` resolves a body.

`prompt` puts the instructions on **stdout, alone**, so you can pipe them. Its
own diagnostics — the note about an illegal stage, the `--no-exec` plan — go to
stderr, and any failure prints nothing on stdout at all, so a pipeline gets the
whole instruction or none of it. `gate` puts nothing on stdout ever, including
whatever a `pre` check writes to its own.

**Neither writes anything**: no document, no draft, no status change. Running
either purely to find out where you stand is safe, which is the point. Between
them they run two things you configured — `gate` your `pre` checks, `prompt` your
`generate` scripts — and `--no-exec` on each skips even those, printing what
would have run instead. That is how you read an unfamiliar repository's lifecycle
before triggering any part of it.

**Starting the document itself** is `tcw work scaffold <artifact> <ref>`. It
resolves that artifact's template — yours if you configured one under
`artifacts:`, TCW's own otherwise — and writes it to `<artifact>.draft.md`,
printing the draft's path on stdout and nothing else.

A draft is **a file to type into, never the document**. `spec.draft.md` is not
`spec.md`: the board still shows the spec as unwritten, `tcw work show --json`
still reports it absent, and the local web app does not list it. Writing the real
document is your job, and until you do it nothing claims you have.

Two things it refuses, both so nothing you have is destroyed. It refuses once the
real artifact exists, because a draft beside a finished document only competes
with it. And it refuses a draft that already has something in it — run it twice
out of habit and your half-written spec survives. `--force` replaces one
deliberately. An _empty_ draft is regenerated with no flag, which is why
`tcw work scaffold intake` — whose template is empty on purpose — works like
everything else.

Nothing is written until the whole template has resolved, so a failed `generate:`
script leaves no file behind and fixing it and running again is clean.

`pre` hooks run **before** anything is written: a non-zero exit aborts the
transition and the item does not move. `post` hooks run after, and a failure
there **never rolls back** — the move already happened, so `tcw` reports it and
exits non-zero while the item stays where it went. Commands run through the shell
with the node root as the working directory and `TCW_SLUG`, `TCW_STATUS`,
`TCW_TRANSITION`, and `TCW_NODE_ROOT` in the environment, with a 300-second
default timeout (`work.lifecycle.timeout`).

Skill bindings are **reported, never run** — `tcw` cannot invoke a skill, only
your agent can. Run `tcw work lifecycle` to see what is bound.

## Declaring which documents track which changes

A project can list the documents that must move with code, so the lifecycle can
put them in front of the agent instead of hoping it goes looking:

```yaml
# tcw-config.yaml
work:
    documentation:
        - path: README.md
          trigger: Public-API
          description: >-
              Public-facing overview and CLI usage. Update when the public
              surface or user-facing behavior changes.
        - path: docs/changelogs/upcoming.md
          trigger: Any-Code-Change
          description: Developer changelog; technical, grouped by category.
```

Three keys per entry, all required. `tcw validate` checks their shape — a blank
field, an absolute path, a path escaping the node, whitespace inside a trigger,
and the same path declared twice under the _same_ trigger. It deliberately does
**not** check that `path` exists (an entry routinely names a file you intend to
create) or that `trigger` is one of the common names (the vocabulary is yours to
extend).

One file may appear in several entries as long as their triggers differ, which
is how a large document whose sections answer to different changes is expressed
— a `README.md` entry under `Public-CLI-API` for its command reference, and a
second `README.md` entry under `Validation-Rules` for the section listing what
the validator rejects. Each trigger is evaluated on its own, so a change that
touches only one of them updates only that entry's material.

`tcw work docs` prints them, `--json` adds `source`, which is `config` when you
have declared entries and `agent-guide` when you have not:

```bash
tcw work docs                          # path, trigger, and what to write
tcw work docs --json                   # {"schema", "source", "entries"}
```

`tcw work stage prompt plan` and `tcw work stage prompt implement` include the
entries inline,
so the documentation gate is part of the stage's instructions rather than a
convention an agent has to remember. **A project that declares nothing is
unaffected** — those stages print exactly what they printed before, and the
`documentation-sync` skill falls back to reading a `## Documentation Sync`
section from your agent guide.

Two things worth knowing: `tcw-config.yaml` is a file in your own repository and
is trusted exactly as much as any other file there — this is not a sandbox. And
`tcw serve` does **not** run hooks, so a `pre` hook that would block a transition
does not block it from the web app.
