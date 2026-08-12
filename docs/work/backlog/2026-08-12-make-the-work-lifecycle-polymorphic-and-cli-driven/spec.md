# Spec — Make the work lifecycle polymorphic and CLI-driven

An **overview spec**. Child boundaries and ordering are decided here;
implementation detail belongs in each child's own spec.

## Capability changes

Planned ledger deltas for the initiative. Each is declared and reconciled by the
**child** that ships it, in that child's `capabilities.yaml` — not here.

| Delta       | Capability                                    | Child |
| ----------- | --------------------------------------------- | ----- |
| **Changed** | `work/read-a-work-item`                       | C1    |
| **Changed** | `work/configure-the-work-lifecycle`           | C2    |
| **Changed** | `work/inspect-the-lifecycle-contract`         | C2    |
| **New**     | `work/run-a-lifecycle-stage`                  | C3    |
| **New**     | `work/customize-lifecycle-artifact-templates` | C4    |

Taxonomy: the Feature `configurable-work-lifecycle` already exists and covers
this initiative; no new Feature is needed. The Vocabulary has
`work-item/lifecycle-stage` and `work-item/transition` but **no term for a
binding/hook**, which is the noun this entire epic is about. C2 should add one
(`work-item/lifecycle-hook`) before writing capability prose that leans on it.

## Problem

TCW's lifecycle is a fixed contract with a fixed methodology welded to it.

The contract is genuinely good: seven stages, five transitions, one artifact per
stage, a machine-readable table (`tcw/store/base.py:594-652`) that is the single
source of truth for what each step is for. That part should not change.

What is welded is everything *inside* a stage:

1. **The instructions live in a skill, not the tool.** What an agent should
   actually do at `spec` is `skills/tcw-work/references/stage-spec.md` — a file
   the plugin ships and a node cannot override. A node with its own methodology
   has nowhere to put it.
2. **Bindings cannot carry instructions.** `Binding` is `skill` or `command`
   (`base.py:530-546`). `command` output goes to stderr as diagnostics; `skill`
   is printed as a name for the agent to act on and is *the only binding kind
   that cannot resolve to text on its own* (`tcw/work/hooks.py:54-58`). So there
   is no way to say "here are the instructions for this stage" — only "here is
   the name of something that has them".
3. **Bindings are unconditional.** Every item at a stage gets the same binding. A
   `bug` and a `feature` are the same work to the lifecycle.
4. **Artifact creation is unspecified and already duplicated.** Only
   `initial-request.md` gets a template, and that template is hardcoded **twice**
   in the filesystem adapter — `fs.py:3016` (empty sections) and `fs.py:2757`
   (the same sections seeded `TBD`) — and the two have already drifted. The other
   six artifacts have no template at all; the agent writes them from the skill
   doc.
5. **The roles are not named.** `work.lifecycle.stages.<id>` bindings exist to
   instruct an agent, and `transitions.<id>.pre/post` bindings exist to run
   programs. Nothing in the type system, the config schema, or the validator says
   so. They are the same `Binding` in two positions.
6. **Nothing fires at stage entry.** `tcw work lifecycle` deliberately runs
   nothing (`cli.py:654-721`), so a per-stage check — "don't implement on trunk"
   — has no trigger. Transitions are the only execution point, and three of the
   seven stages (`request`, `spec`, `plan`) have **no transition between them**.

## Goals

1. A node can supply the instructions for any stage as literal text, as a file,
   or from a script it owns — with no skill and no plugin involved.
2. Bindings can depend on the item: a `bug` gets different instructions and a
   different artifact template than a `feature`.
3. Every artifact has a template; templates are overridable; the built-in ones
   derive from the same table that already declares what a stage produces.
4. A node that configures nothing gets a good default, **from the CLI**, so
   Claude and Codex receive byte-identical instructions.
5. Hook roles are named and enforced: a check runs and may fail, a prompt
   resolves to text, an artifact factory writes one file.
6. All of it is reachable through `tcw`. Nothing depends on Claude's context
   injection, hooks, or slash commands.
7. Existing `tcw-config.yaml` files keep working unchanged.

## Non-goals

- Changing the stage or transition **set**, or the two-ladder model.
- Making `tcw work lifecycle` execute anything. It stays inert; every skill and
  stage document depends on that.
- A boolean expression language in configuration. Decided at request time.
- Sandboxing hooks. The trust model is unchanged and stated plainly.
- Making `tcw serve` run hooks.
- Building a remote store adapter.

## Design

### The order of operations

The requester's proposed ordering, corrected for the two-ladder problem. Stages
and transitions each get their own sequence; they are not one sequence.

**Entering a stage** — `tcw work stage <id> [ref]`:

1. `pre` checks run. Non-zero exit stops everything; nothing further runs. `[gated]`
2. The **artifact hook** runs — at most one per stage. It creates the stage's
   artifact **only if absent**; it never overwrites.
3. **Prompt hooks** resolve, in declaration order, and their text is concatenated
   to **stdout**.

Everything a check writes goes to **stderr**, as it does today
(`hooks.py:66-69`). Only step 3 writes to stdout. That separation is the
contract: `tcw work stage spec` on stdout is exactly the prompt and nothing else.

**Leaving a stage** — `tcw work stage <id> --done [ref]` runs the stage's `post`
checks and exits non-zero on failure. For `implement` this can be made to matter,
because `submit` follows it; for `request`, `spec`, and `plan` **nothing enforces
it** — they are all inside `backlog` with no transition between them. This is
`[judgment]`, and must be documented as `[judgment]`. Claiming otherwise would be
the same false promise the `[gated]`/`[judgment]` convention exists to prevent.

**Transitions** keep today's semantics exactly: `pre` before anything is written,
`post` after, never rolling back.

### Hook roles

A binding's **role** determines what it is and which kinds are legal.

| Role       | Positions                                  | Legal kinds                                | Semantics                                            |
| ---------- | ------------------------------------------ | ------------------------------------------ | ---------------------------------------------------- |
| `check`    | stage `pre`/`post`, transition `pre`/`post` | `command`                                  | Runs. Exit code matters. Output → stderr.            |
| `prompt`   | stage `prompt`                             | `blob`, `file`, `generate`, `builtin`, `skill` | Resolves to text. All matches concatenate.       |
| `artifact` | stage `artifact`                           | `blob`, `file`, `generate`, `builtin`      | Resolves to text; written as the artifact. First match wins. |

The kinds:

- **`blob`** — the text, inline in YAML.
- **`file`** — a node-relative path; its contents are the text.
- **`generate`** — a shell command. The item JSON (see below) goes in on
  **stdin**; **stdout** is the text. Non-zero exit is an error, not empty text.
- **`builtin`** — TCW's shipped default for this stage. Exists so composition is
  explicit: if a stage declares any prompt bindings, only those run, and a node
  that wants the default *plus* its own writes `{builtin: true}` first. One rule,
  no "extend vs. replace" flag.
- **`skill`** — retained for compatibility, `prompt` only, and documented as
  weakest: it is the one kind TCW cannot resolve to text.
- **`command`** — retained, `check` only. `command` in a prompt position is a
  validation error naming `generate` as the intended kind.

### Conditions

An optional `when:` on any binding. Keys are ANDed; a list value means "any of".
A binding whose `when:` does not match is skipped.

```yaml
when:
    tags: [bug, regression] # item carries any of these
    not_tags: [spike] # item carries none of these
    type: epic # "" matches a non-epic
```

Three keys. Deliberately not extensible in this epic: status is largely implied
by the stage, and artifact presence is what the stage ladder already encodes.
Anything harder is a `generate` hook, which receives the whole item and can
decide with real code. C2's spec re-checks this before locking it.

### Configuration shape

```yaml
work:
    lifecycle:
        stages:
            spec:
                pre: [{ command: "tcw validate" }]
                artifact: [{ when: { tags: [bug] }, file: .tcw/spec-bug.md }, { builtin: true }]
                prompt:
                    - { builtin: true }
                    - { when: { tags: [bug] }, file: docs/method/debugging.md }
                    - { blob: "Always link the reporting issue." }
                post: [{ command: "scripts/check-spec-sections.sh" }]
        transitions:
            complete:
                pre: [{ command: "pytest -q" }]
```

**Back-compat:** today's bare list — `stages: {spec: [{skill: …}]}` — parses as
`prompt:`. That is the only compat rule needed, and it is exact: today's stage
bindings are prompt bindings that were never named as such.

### The item JSON projection

One function, `WorkItem` + `artifacts()` → dict. Two consumers:

- `tcw work show --json` emits it directly.
- A `generate` hook receives `{"item": <projection>, "hook": {…}}` on stdin,
  where `hook` names the role, the kind (`stage`/`transition`), the id, and the
  phase (`pre`/`post`/null). The same facts also go into the environment
  alongside today's four `TCW_*` variables, so a one-line script does not need a
  JSON parser.

**Litmus test.** Every field is already abstract: `WorkItem` (`base.py:829-850`)
is store-independent, and `artifacts()` (`base.py:958`) is an existing abstract
method returning name-plus-presence. No folder is listed and no path is embedded.
A remote adapter produces this projection as easily as the FS one. ✓

### Artifact templates

`LifecycleStep` gains a `sections: tuple[str, ...]` field. The built-in template
for a stage is rendered from it, which means:

- The template and the "required sections" prose have **one** source, which is
  the drift `LIFECYCLE_STEPS` already exists to prevent (`base.py:573-581`).
- The two hardcoded `initial-request.md` templates (`fs.py:2757`, `fs.py:3016`)
  collapse into one shared constant, fixing an existing bug.
- `tcw work stage <id> --done` can check that the required sections are present.

Rendering is a pure string operation in the shared layer; writing goes through
the existing abstract `write_artifact`. Hook **execution** stays in
`tcw/work/hooks.py`, outside the store, for the reason already recorded there
(`hooks.py:1-19`). ✓

### Default prompts

Shipped as package data (`tcw/work/prompts/<stage>.md`), resolved by the
`builtin` kind and used when a stage binds no prompt. Condensed from
[obra/superpowers] — the spirit, not the volume. Their content is C5's job.

`skills/tcw-work/references/stage-*.md` then shrink to routers: run
`tcw work stage <id>`, follow what it prints. TCW-specific judgment the CLI
should not carry (delegability, epic deltas, `[gated]`/`[judgment]` markers)
stays in the skill; the *methodology* moves to the CLI.

## Child boundaries and ordering

| ID  | Child                                 | Delivers                                                                                                  | Blocked by |
| --- | ------------------------------------- | --------------------------------------------------------------------------------------------------------- | ---------- |
| C1  | Work item JSON projection             | The shared projection + `tcw work show --json`.                                                           | —          |
| C2  | Hook roles, kinds, and conditions     | `check`/`prompt`/`artifact` roles; `blob`/`file`/`generate`/`builtin` kinds; `when:`; parse, validate, back-compat; resolution as a library; `tcw work lifecycle --phase`; new Vocabulary term. | C1         |
| C3  | The stage verb                        | `tcw work stage <id> [--done]` — pre → artifact → prompt, and `--done` post checks.                       | C2         |
| C4  | Artifact templates                    | `sections` on `LifecycleStep`; built-in templates; the duplicate `initial-request.md` templates collapsed. | C3         |
| C5  | Built-in stage prompts                | `tcw/work/prompts/*.md` and their resolution.                                                             | C2         |
| C6  | Skill and documentation rewrite       | Stage docs become routers; `hooks.md` rewritten; README; capability ledger.                               | C4, C5     |

Order: C1 → C2 → {C3, C5} → C4 → C6. C3 and C5 are genuinely parallel once C2
lands; do not chain them.

C1 and C2 are the only children with no user-visible value on their own, and C1
is the exception — `show --json` ships alone. Each of C3, C4, C5 is independently
useful, which is what makes this an epic rather than one phased item.

## Acceptance criteria

For the initiative as a whole. Each child's spec derives its own.

1. A `tcw-config.yaml` valid before this epic parses unchanged afterwards, with
   identical behavior. A bare-list stage binding is read as a `prompt` binding.
2. `tcw work show <ref> --json` emits an object containing every `WorkItem`
   field and an `artifacts` map of name → presence, and it parses as JSON.
3. A `generate` prompt hook receives that same projection on stdin under an
   `item` key, plus a `hook` object naming role, kind, id, and phase, and its
   stdout is what `tcw work stage` prints.
4. With `prompt: [{when: {tags: [bug]}, blob: "B"}, {when: {tags: [feature]}, blob: "F"}]`
   bound to `spec`, `tcw work stage spec <bug-item>` prints `B` and not `F`, and
   the reverse for a `feature`-tagged item.
5. `tcw work stage <id>` prints **only** resolved prompt text on stdout; every
   check's stdout and stderr goes to stderr.
6. A failing stage `pre` check exits non-zero, and neither the artifact hook nor
   any prompt hook has run.
7. The artifact hook does not overwrite an artifact that already exists.
8. `tcw work lifecycle` still executes nothing — verified by a test that binds a
   command writing a sentinel file and asserts the file is absent after
   `lifecycle` runs, for every stage and transition id.
9. `tcw work lifecycle --transition complete --phase pre --directive` reports
   only the `pre` bindings.
10. With nothing configured, `tcw work stage spec` prints TCW's built-in spec
    instructions, and `{builtin: true}` composed with a node's own binding prints
    both, in declaration order.
11. Exactly one definition of the `initial-request.md` template exists in the
    codebase, and `tcw work new` and `tcw work inbox accept` both use it.
12. `tcw validate` rejects: an unknown role key, an illegal role/kind pair
    (`command` in a prompt position, `skill` in a check position), an unknown
    `when:` key, more than one matching `artifact` binding declared as if all
    applied, and a `file` binding whose path does not exist — each naming the
    offending key.
13. Every stage document in `skills/tcw-work/references/` and the CLI agree on
    that stage's required sections, verified by a test rather than by review.

## Risks

- **`generate` widens the blast radius of a hostile `tcw-config.yaml`.** The
  trust model is unchanged in principle — `command:` already runs shell — but it
  is now reachable from a verb that reads as informational. Mitigations: the
  stage verb is an explicit invocation, `tcw work lifecycle` stays inert
  (criterion 8), and the README says so plainly rather than burying it.
- **`tcw serve` diverges further.** It runs no hooks, so a web-created artifact
  gets no template and a web transition skips every check. This epic makes that
  gap wider and more visible. C4 must decide explicitly whether artifact
  templates — which are pure text rendering, not shell — are safe to apply in
  `serve`, and record the decision either way.
- **Plugin/CLI version skew.** Moving the default prompts into the CLI means a
  stale `tcw` serves stale instructions to a fresh skill. The router docs must
  not restate what the prompts say, or the skew becomes a contradiction rather
  than an old-but-coherent answer.
- **Unbounded `generate` output.** A script can return anything. Cap resolved
  prompt text (`serve` already caps request bodies at 1 MiB; something far
  smaller is right here) and fail loudly rather than flooding a context window.
- **`--done` is unenforceable for three stages and will be read as a gate
  anyway.** Anything that reports it must mark it `[judgment]`. Consider having
  the command itself say so in its output.
- **Scope creep into a config language.** `when:` has three keys by decision, not
  by accident. Each new key added in a child is a key that has to be validated,
  documented, and supported forever; `generate` exists so that pressure has
  somewhere to go.

## Notes

- The requester's original ordering had post-stage hooks aborting a transition.
  That is preserved where it is true (transition `pre`) and marked honestly where
  it is not (`--done` for the three backlog-internal stages), rather than being
  implemented as a promise the tool cannot keep.
- The `skill` binding kind survives because it is public API in users'
  configuration, not because it is good. The argument for demoting it is
  structural rather than harness-specific: `blob`, `file`, `generate`, and
  `builtin` all resolve to text TCW can hand over; `skill` cannot.
- C4 depending on C3 is a sequencing choice, not a technical one — templates need
  a firing point, and C3 is where it lives. If C3 slips, C4's template rendering
  could land ahead of its wiring, but the epic gains nothing from planning for
  that now.

[obra/superpowers]: https://github.com/obra/superpowers
