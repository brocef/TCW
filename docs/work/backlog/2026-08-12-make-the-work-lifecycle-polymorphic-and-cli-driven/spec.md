# Spec — Make the work lifecycle polymorphic and CLI-driven

An **overview spec**. Child boundaries and ordering are decided here;
implementation detail belongs in each child's own spec.

> Revised after adversarial review by `codex` and `bllm-review`. Findings that
> changed the design are recorded in `## Review corrections`.

## Capability changes

Planned ledger deltas for the initiative. Each is declared **and reconciled** by
the child that ships it, in that child's own `capabilities.yaml`. No child flips
another child's delta.

| Delta       | Capability                                    | Child |
| ----------- | --------------------------------------------- | ----- |
| **New**     | `work/capture-raw-intake`                     | C1    |
| **Changed** | `work/open-a-work-item`                       | C1    |
| **Changed** | `work/manage-the-work-inbox`                  | C1    |
| **Changed** | `work/read-a-work-item`                       | C2    |
| **Changed** | `work/configure-the-work-lifecycle`           | C3    |
| **Changed** | `work/inspect-the-lifecycle-contract`         | C3    |
| **New**     | `work/run-a-lifecycle-stage`                  | C4    |
| **New**     | `work/customize-lifecycle-artifact-templates` | C5    |

Taxonomy: the Feature `configurable-work-lifecycle` already exists and covers
this initiative. The Vocabulary has `work-item/lifecycle-stage` and
`work-item/transition` but **no term for a binding/hook**, which is the noun this
epic is about. C3 adds `work-item/lifecycle-hook` before writing capability prose
that leans on it.

## Problem

TCW's lifecycle is a fixed contract with a fixed methodology welded to it.

The contract is genuinely good: seven stages, five transitions, and a
machine-readable table (`base.py:594-652`) that is the single source of truth for
what each step is for. That part should not change.

What is welded is everything *inside* a stage:

1. **The instructions live in a skill, not the tool.** What an agent should do at
   `spec` is `skills/tcw-work/references/stage-spec.md` — a file the plugin ships
   and a node cannot override. A node with its own methodology has nowhere to put
   it.
2. **Bindings cannot carry instructions.** `Binding` is `skill` or `command`
   (`base.py:530-546`). `skill` is the only kind that cannot resolve to text on
   its own (`hooks.py:54-58`). So there is no way to say "here are the
   instructions for this stage" — only "here is the name of something that has
   them".
3. **Bindings are unconditional.** A `bug` and a `feature` are the same work to
   the lifecycle.
4. **Intake is handled three different ways, and one of them is wrong.**
   `tcw work delegate` and `escalate` deposit raw text into an inbox
   (`recursion.py:231-251`) and let `accept` ingest it. `tcw work inbox accept`
   ingests an entry, but *synthesizes a request document* while doing it
   (`fs.py:2755-2769`). `tcw work new` with piped stdin synthesizes one too
   (`fs.py:3016`). Those last two hardcode the same three-heading skeleton in two
   places, disagreeing on whether to seed `TBD`; only `accept`'s extra
   `## Inbox contents` section is a deliberate difference.
5. **`initial-request.md` is created before its own stage runs**, by both
   creation paths, unconditionally. Two consequences:
   - The `request` stage is the only stage that fills in a file rather than
     creating one, and the only stage with no `inputs` in `LIFECYCLE_STEPS`.
   - `artifacts()` counts an artifact present only when non-empty
     (`fs.py:2166-2172`), and the seeded skeleton is non-empty — so **every item
     shows `R`** in `tcw work list`. One of the seven letters in the stage string
     carries no information.
6. **The roles are not named.** Stage bindings exist to instruct an agent;
   transition `pre`/`post` bindings exist to run programs. Nothing in the types,
   the schema, or the validator says so — they are the same `Binding` in two
   positions. In fact **stage bindings are never executed at all**: `run_pre` and
   `run_post` handle transitions only, so a stage `command:` today renders
   through `_directive_text` (`cli.py:648`) as prose telling the agent to run it.
7. **Nothing fires at stage entry.** `tcw work lifecycle` deliberately runs
   nothing (`cli.py:654-721`), so a per-stage check has no trigger. Transitions
   are the only execution point, and three of the seven stages (`request`,
   `spec`, `plan`) have **no transition between them** — the only edges out of
   `backlog` are `→active` and `→discarded` (`base.py:452-462`).

## Goals

1. A node can supply the instructions for any stage as literal text, as a file,
   or from a script it owns — no skill, no plugin.
2. Bindings can depend on the item: a `bug` gets different instructions and a
   different artifact template than a `feature`.
3. **One intake path.** Raw input — piped, delegated, or dropped in the inbox —
   is stored as raw input, and turning it into a request is the `request`
   stage's job, done once, in one place.
4. Every artifact has a template; templates are overridable; the built-in ones
   derive from the same table that declares what each stage produces.
5. A node that configures nothing gets a good default **from the CLI**, so Claude
   and Codex receive byte-identical instructions.
6. Hook roles are named and enforced: a check runs and may fail, a prompt
   resolves to text, an artifact factory writes one file.
7. All of it reachable through `tcw`. Nothing depends on Claude's context
   injection, hooks, or slash commands.
8. Existing `tcw-config.yaml` files keep working, with stated semantics for every
   legacy shape.

## Non-goals

- Changing the stage or transition **set**, or the two-ladder model.
- Making `tcw work lifecycle` execute anything.
- A boolean expression language in configuration.
- Sandboxing hooks. The trust model is unchanged and stated plainly.
- Making `tcw serve` run shell.
- Building a remote store adapter.

## Design

### Intake, unified

`intake.md` becomes an artifact: the raw, unprocessed input an item started from.

- `tcw work new "<title>"` with piped stdin writes `intake.md` and **no**
  `initial-request.md`. With no stdin, it writes neither.
- `tcw work inbox accept <entry>` writes `intake.md` from the entry body, keeps
  attachments where it already puts them, and **stops synthesizing a request**.
  `fs.py:2755-2769` is deleted rather than refactored.
- `delegate` / `escalate` are unchanged — they already deposit intake into an
  inbox and let `accept` ingest it. They are the pattern the other paths adopt.
- `request` gains `inputs=("intake.md",)` and produces `initial-request.md` like
  any other stage produces its artifact.

**The body surface resolves** to `initial-request.md` when present, falling back
to `intake.md`. So `tcw work new <<< "…"` stays immediately useful, `show` and
the board still work for triage, and once `request` runs the polished request
takes over. Abstractly this is "the description, else the originating text",
which any tracker can answer. ✓

Every stage now reads the prior artifact and writes its own. `intake.md` is an
artifact with no stage; `inbox` is a stage with no artifact. They are the two
ends of the same table, not anomalies.

Existing items keep working: they have an `initial-request.md`, so the body
surface resolves to it and nothing changes for them. C1 owns deciding whether
any backfill is warranted (probably not).

### Artifacts are keyed by name, not by stage

`LifecycleStep.produces` becomes a **tuple of artifact names**, because
one-artifact-per-stage was never true: `inbox` produces none (`base.py:598`) and
`verify` produces `refined-outcome.md` *or* `rework.md` (`base.py:619`), today
recorded as prose rather than as names.

Templates and `sections` attach to entries in `WORK_ARTIFACTS`, which is already
the real artifact registry. A stage with no artifacts simply has no artifact
hook; a stage with two has one hook per artifact name.

### The order of operations

Stages and transitions each get their own sequence; they are not one sequence.

**Entering a stage** — `tcw work stage <id> [ref]`:

1. `pre` checks run. Non-zero exit stops everything. `[gated]`
2. Every artifact and prompt binding is **resolved** — files read, `generate`
   scripts run, conditions evaluated. Nothing is written yet.
3. Only if every resolution succeeded: the artifact is written, if absent.
4. Prompt text is concatenated to **stdout**.

Resolve-then-write (steps 2-3) is deliberate. Writing the artifact before
resolving prompts would let a failed prompt hook leave a written artifact behind
that the next attempt then refuses to overwrite — a retry that can never succeed.

Check output goes to **stderr**, as today (`hooks.py:66-69`). Only step 4 writes
to stdout, so `tcw work stage spec` on stdout is exactly the prompt.

`--no-exec` resolves and prints what *would* run — every command, every
`generate` script — and executes nothing. It is how you read an unfamiliar
repository's lifecycle before triggering it.

**There is no stage `post` and no `--done`.** Exit checks belong on the *next*
stage's `pre`, and on the following transition's `pre` for the stages a
transition follows. That covers every stage with one check family instead of two,
and every check fires at a moment that actually happens. A stage `post` for
`request`/`spec`/`plan` could never be more than advisory, and an advisory gate
that looks like a gate is worse than no gate.

**Transitions** keep today's semantics exactly: `pre` before anything is written,
`post` after, never rolling back.

### Hook roles

| Role       | Positions                            | Legal kinds                                    | Semantics                                        |
| ---------- | ------------------------------------ | ---------------------------------------------- | ------------------------------------------------ |
| `check`    | stage `pre`, transition `pre`/`post`  | `command`                                      | Runs. Exit code matters. Output → stderr.        |
| `prompt`   | stage `prompt`                        | `blob`, `file`, `generate`, `builtin`, `skill` | Resolves to text. **All** matches concatenate.   |
| `artifact` | stage `artifact`                      | `blob`, `file`, `generate`, `builtin`          | Resolves to text. **First** match wins.          |

- **`blob`** — the text, inline in YAML.
- **`file`** — a node-relative path. Normalized and confined to the node root; a
  path escaping it is a validation error, not a read. This is a footgun guard,
  not a sandbox: the config is trusted, but a typo that quietly reads an
  unrelated file into a prompt is worth refusing.
- **`generate`** — a shell command. The item JSON goes in on **stdin**, stdout is
  the text. Contract, enforced rather than aspirational: the existing
  `work.lifecycle.timeout` applies; output is capped (a small number of KiB, C3
  picks it) and captured with a bound rather than buffered unbounded; stdout is
  decoded as UTF-8 with a stated policy for invalid bytes; **all stdout is
  discarded on non-zero exit**, so a script failing midway cannot leak a partial
  prompt.
- **`builtin`** — TCW's shipped default. Role-dependent by necessity: in a
  `prompt` list it composes, so `{builtin: true}` first then a node's own binding
  yields both. In an `artifact` list first-match-wins makes it a *fallback*, so
  it must be the **last** entry and unconditional; `tcw validate` rejects it
  anywhere else, and rejects entries made unreachable by a preceding
  unconditional match.
- **`skill`** — `prompt` only, retained for compatibility, documented as weakest:
  it resolves to "invoke the X skill", which is a name rather than instructions.
- **`command`** — `check` only. In a prompt position it is a validation error
  naming `generate`.

### Back-compat, all four legacy shapes

Stage bindings are never executed today, which makes this cheaper than it looks:

| Legacy shape                     | Today                                              | After                                     |
| -------------------------------- | -------------------------------------------------- | ----------------------------------------- |
| `stages.<id>: [{skill: X}]`      | Reported as "invoke the X skill"                   | `prompt` binding, kind `skill`, same text |
| `stages.<id>: [{command: C}]`    | Rendered as "run `C`" (`cli.py:648`) — not executed | `prompt` binding emitting the same line   |
| `transitions.<id>.pre/post: [{command: C}]` | Executed                                | `check` binding, unchanged                |
| `transitions.<id>.skill: X`      | Reported to stderr (`hooks.py:56`)                 | Reported to stderr, unchanged             |

Every one preserves observable behavior. A bare list under `stages.<id>` parses
as `prompt:`. `tests/test_lifecycle_policy.py:77-82` — which asserts a stage list
mixing `skill` and `command` parses — must still pass unmodified.

### Conditions

An optional `when:` on any binding. Keys ANDed; a list value means "any of".

```yaml
when:
    tags: [bug, regression] # any of these
    not_tags: [spike] # none of these
    type: epic # "" matches a non-epic; validated against known types
```

Three keys. `type` is validated against the known set rather than matched
loosely, so a typo fails rather than silently never matching. Anything harder is
a `generate` hook, which receives the whole item and decides in real code — this
covers conditional artifact selection too, since one unconditional `generate`
artifact hook can pick among templates internally. Additional keys (`parent`,
`initiative`) are a C3 decision, weighed against the cost of supporting each one
forever.

### The item JSON projection

A **versioned DTO**, not a dataclass dump. It carries an explicit `schema`
version, explicitly typed and normalized fields, and an `artifacts` map of name →
presence. Consumed by `tcw work show --json` and, under an `item` key, by
`generate` hooks on stdin — alongside a `hook` object naming role, kind, id, and
phase. The same facts go into the environment beside today's four `TCW_*`
variables so a one-line script needs no JSON parser.

`WorkItem.capabilities` is an opaque `object` (`base.py:843`) filled from
arbitrary YAML (`fs.py:2366-2372`), so it can hold values with no JSON
equivalent. C2 decides explicitly whether to normalize or exclude it, and states
which. `body` is bounded or excluded for the same reason — it can be arbitrarily
large.

**Litmus test.** Every field is abstract: `WorkItem` (`base.py:829-850`) is
store-independent and `artifacts()` (`base.py:958`) is an existing abstract
method. No folder is listed and no path is embedded. ✓

### Default prompts

Shipped as package data (`tcw/work/prompts/<stage>.md`), resolved by the
`builtin` kind and used when a stage binds no prompt. Condensed from
[obra/superpowers] — the spirit, not the volume. Content is C6's job.

`skills/tcw-work/references/stage-*.md` then shrink to routers: run
`tcw work stage <id>`, follow what it prints. TCW-specific judgment the CLI
should not carry (delegability, epic deltas, `[gated]`/`[judgment]` markers)
stays in the skill; the *methodology* moves to the CLI.

## Child boundaries and ordering

| ID  | Child                             | Delivers                                                                                                                                  | Blocked by |
| --- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| C1  | Unify intake                      | `intake.md`; creation paths stop synthesizing requests; body-surface resolution; `request` gains inputs; `fs.py:2755-2769` deleted.        | —          |
| C2  | Work item JSON projection         | The versioned DTO + `tcw work show --json`.                                                                                               | C1         |
| C3  | Hook roles, kinds, and conditions  | Roles; kinds incl. the `generate` contract and `file` confinement; `when:`; parse/validate/back-compat; resolution library; `lifecycle --phase`; new Vocabulary term. | C2         |
| C4  | The stage verb                    | `tcw work stage <id>` — pre → resolve → write → prompt, plus `--no-exec`.                                                                  | C3         |
| C5  | Artifact templates                | `produces` as a tuple; `sections`; templates keyed by artifact name; wired into C4's sequence.                                             | C4         |
| C6  | Built-in stage prompts            | `tcw/work/prompts/*.md`, `builtin` resolution, wheel packaging.                                                                           | C3         |
| C7  | Skill and documentation rewrite   | Stage docs → routers; `hooks.md` rewritten; README lifecycle section; final consolidation only.                                           | C5, C6     |

Order: C1 → C2 → C3 → {C4 → C5, C6} → C7. C4 and C6 are parallel; do not chain
them.

C5's dependency on C4 is now **technical**, not sequencing: after C1 the request
artifact is created by the `request` stage, so the stage verb is genuinely the
firing point for conditional templates.

## Acceptance criteria

1. A `tcw-config.yaml` valid before this epic parses afterwards with identical
   observable behavior, proven by a corpus of legacy config shapes — at minimum
   one per row of the back-compat table — asserting byte-identical resolved
   output against a pre-epic baseline. `tests/test_lifecycle_policy.py:77-82`
   passes unmodified.
2. `tcw work new "t"` with no stdin creates **no** `initial-request.md` and no
   `intake.md`; with piped stdin it creates `intake.md` containing exactly the
   piped bytes and no `initial-request.md`. `tcw work inbox accept` creates
   `intake.md` and no `initial-request.md`. No code path synthesizes a request
   document.
3. `tcw work list` shows `R` only for items whose `request` stage has run, and
   `I` for items with intake — verified on a fresh item, an intake-only item, and
   a post-`request` item.
4. `tcw work show` on an intake-only item displays the intake; after `request`
   runs it displays the request.
5. `tcw work show <ref> --json` emits an object with an explicit `schema`
   version, each documented field at its documented JSON type, and an `artifacts`
   name→presence map. A test asserts the emitted document validates against the
   declared schema — **not** that it enumerates dataclass fields — and that an
   item whose `capabilities` blob holds a non-JSON-native YAML value still emits
   valid JSON.
6. A `generate` prompt hook receives that projection under `item` plus a `hook`
   object naming role, kind, id, and phase; its stdout becomes the printed
   prompt. A script exiting non-zero after writing to stdout contributes
   **nothing**. A script exceeding the output cap or the timeout fails the
   command rather than truncating silently.
7. The `when:` truth table is tested exhaustively: each key alone, AND across
   keys, any-of within a list, `not_tags` exclusion, `type` including `""`,
   overlapping matches, no-match, and an invalid `type` value rejected by
   `tcw validate`.
8. `tcw work stage <id>` prints **only** resolved prompt text on stdout; every
   check's stdout and stderr goes to stderr.
9. A failing stage `pre` check exits non-zero with no artifact written and no
   prompt resolved.
10. When a prompt hook fails *after* an artifact hook resolved successfully, no
    artifact is written and re-running the command succeeds — the resolve-then-
    write property, tested as a retry rather than as a single failure.
11. The artifact hook creates the artifact with exactly the resolved content when
    absent, and leaves an existing artifact byte-identical when present. An
    implementation that never writes anything fails this.
12. `tcw work lifecycle` still executes nothing — a bound command writing a
    sentinel file, run for every stage and transition id, leaves no sentinel.
13. `tcw work lifecycle --transition complete --phase pre --directive` reports
    only the `pre` bindings.
14. With nothing configured, `tcw work stage <id>` prints built-in instructions
    for **every** stage id that has them, and `{builtin: true}` composed with a
    node binding prints both in declaration order.
15. `tcw validate` rejects, each naming the offending key: an unknown role key;
    `command` in a prompt position; `skill` in a check position; an unknown
    `when:` key; an invalid `type` value; a `file` path that does not exist or
    escapes the node root; a `builtin` artifact binding that is not last or is
    conditional; and an artifact entry made unreachable by a preceding
    unconditional match.
16. `--no-exec` prints every command and `generate` script that would run and
    executes none — verified by the sentinel technique from criterion 12.
17. Exactly one definition of each built-in artifact template exists in the
    codebase.
18. Every stage document in `skills/tcw-work/references/` routes to the CLI for
    its instructions rather than restating them, verified by a test asserting the
    routers reference the command and do **not** duplicate section prose.

## Risks

- **`generate` widens the blast radius of a hostile `tcw-config.yaml`.** The
  posture is unchanged in principle — `tcw work start` already runs config shell
  today (`cli.py:511`) under a trust model stated deliberately at
  `hooks.py:11-14`. What changes is frequency: the rewritten skill has agents
  invoking `tcw work stage` routinely. Mitigations: `--no-exec` (criterion 16),
  `tcw work lifecycle` staying inert (criterion 12), and the README saying so
  plainly. **Not** mitigated by consent prompts or command validation — the first
  reverses a decided position, the second is not achievable for arbitrary shell.
- **C1 is a behavior change users will notice.** `tcw work new` stops printing an
  `→ edit:` path to a file that exists. C1 owns the replacement hint and the
  release-note wording; this is the most user-visible change in the epic and the
  one most likely to generate a bug report if it lands quietly.
- **The board's stage-letter string changes meaning.** Adding `intake` to
  `WORK_ARTIFACTS` shifts the display, and `base.py:777-779` warns that the
  tuple's order drives it. Appending keeps existing letters stable at the cost of
  `I` appearing after the letters for later stages. C1 decides and records which.
- **`tcw serve` diverges further.** It runs no hooks, so a web-created artifact
  gets no template. C5 decides explicitly whether template rendering — pure text,
  not shell — applies in `serve`, and whether a template needing hook context
  could render broken there. "Serve runs no hooks" answers a question about
  shell and does not settle this by itself.
- **Plugin/CLI version skew.** A stale `tcw` serves stale instructions to a fresh
  skill. The routers must not restate what the prompts say (criterion 18), so
  skew reads as an old-but-coherent answer rather than a contradiction.
- **Scope creep into a config language.** `when:` has three keys by decision.
  Each key added later must be validated, documented, and supported forever;
  `generate` exists so that pressure has somewhere to go.

## Review corrections

Changes made after the `codex` / `bllm-review` pass, recorded so the reasoning is
not lost.

- **One artifact per stage was false.** `produces` is now a tuple and artifacts
  are keyed by name (codex F1).
- **Conditional request templates were impossible as first specced** — both
  creation paths wrote `initial-request.md` unconditionally, so a create-if-absent
  hook could never fire (codex F3). Resolved by C1's intake unification, which
  the requester proposed and which subsumes the finding.
- **Back-compat covered one shape of four**, and an existing test asserted a
  shape the draft matrix forbade (codex F2). Now a four-row table; the fix is
  cheap because stage bindings are never executed today.
- **The artifact write was not atomic with prompt resolution** (codex F4) →
  resolve-then-write, criterion 10.
- **`generate` had no resource contract** (codex F5, bllm) → timeout, output cap,
  encoding policy, and stdout discarded on non-zero exit, in Design and
  criterion 6.
- **The JSON projection was not JSON-safe** (codex F7) → versioned DTO, explicit
  `capabilities` and `body` decisions, schema-validation test rather than
  field enumeration.
- **`builtin` had two meanings** (codex F8) → stated per role, with validation
  rules for the artifact case rather than a new keyword.
- **C5 could not verify itself** (codex F10) → dependencies rebuilt.
- **C6 flipping every capability contradicted the spec** (codex F11) → each child
  reconciles its own.
- **Weak acceptance criteria** (codex F12, bllm) → rewritten; the old criterion
  13 contradicted the router requirement and is now criterion 18.
- **Stage `post`/`--done` cut** (codex F13, requester's decision) → exit checks
  move to the next stage's `pre`.
- **`file` path traversal unguarded** (bllm) → normalization and node-root
  confinement, criterion 15.
- **AC 12 contradicted first-match-wins** (bllm) → replaced by explicit
  unreachable-entry validation.
- **C4→C3 was an artificial dependency** (bllm). It is now technical: after C1
  the stage verb really is the firing point for request templates.
- **"Already drifted" overstated the duplicate templates.** The `## Inbox
  contents` difference is deliberate; only `TBD`-vs-empty is unexplained. Both
  disappear with C1.
- **Not accepted:** validating `command` strings against injection (bllm) — not
  achievable for arbitrary shell and contrary to the stated trust model; consent
  prompts for `generate` (codex F6) — reverses a decided posture, replaced by
  `--no-exec`; that `generate` cannot serve conditional artifact selection
  (codex F9) — one unconditional `generate` hook picks among templates
  internally.

## Notes

- The requester's original ordering had post-stage hooks aborting a transition.
  Preserved where true (transition `pre`), and cut where it could only have been
  advisory.
- The `skill` binding kind survives because it is public API, not because it is
  good. The argument for demoting it is structural: `blob`, `file`, `generate`,
  and `builtin` all resolve to text TCW can hand over; `skill` cannot.
- C1 was not in the first draft of this spec. It exists because review found the
  headline feature impossible without it, and because the requester recognized
  that piped input to `tcw work new` is shorthand for intake plus creation plus
  ingestion — which `delegate` and `escalate` already do correctly.

[obra/superpowers]: https://github.com/obra/superpowers
