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
- `tcw work inbox accept <entry>` writes `intake.md` and **stops synthesizing a
  request**. It must keep everything it preserves today: attachments
  (`fs.py:2770`), the `origin`-bearing manifest (`fs.py:2738-2753`), and the
  binary fallback prose (`fs.py:2755`) for an entry whose primary resource is not
  text. `intake.md` therefore carries the manifest and the entry body when there
  is one, and the manifest plus the binary note when there is not — an
  attachments-only entry still produces an `intake.md`. This is a **refactor of**
  `fs.py:2755-2769`, not the deletion an earlier draft called for.
- `delegate` / `escalate` are unchanged — they already deposit intake into an
  inbox and let `accept` ingest it. They are the pattern the other paths adopt.
- `request` reads `intake.md` when it exists. `LifecycleStep.inputs` is
  **descriptive**, rendered by `tcw work lifecycle` and enforced nowhere
  (`cli.py:621-622`), so listing it there does not make it required — but the
  field must read as optional, because a fresh item has no intake and a legacy
  item never will.

**Abstractly, intake is its own concept, not a re-reading of `body`.**
`WorkStore.create(..., body=…)` is an abstract primitive (`base.py:944`); quietly
making the FS adapter write that argument to `intake.md` while a remote adapter
writes it to a description field gives one parameter two meanings. C1 adds an
explicit intake surface to the interface instead, and every caller — CLI and
`serve` (`serve/__init__.py:764-773`) — moves to it deliberately. ✓

### The body surface: one presence rule, and a write contract

Today "present" means two different things: `_read_item` accepts any existing
file (`fs.py:2387`) while `artifacts()` requires non-whitespace content
(`fs.py:2166-2172`). With the fallback added, an empty `initial-request.md`
beside a real `intake.md` would show no body *and* no `R`.

**One canonical resolver**, shared by `_read_item`, `body_path`, the core
revision, `artifacts()`, the JSON projection, and `serve`. Presence is *exists
and non-empty*. Reads resolve `initial-request.md` → `intake.md` → `""`. All
three states are defined, including neither-present, which must return an empty
body rather than raising.

**Writes do not follow the read fallback.** `update_work(body=…)` targets
`initial-request.md` (`fs.py:3156`), including from the web editor
(`serve/__init__.py:984-991`), so on an intake-only item a body edit would either
mutate raw input or silently satisfy the `request` stage. The contract:

- A body write always targets `initial-request.md`. On an intake-only item that
  is a **promotion** — it creates the request — and the CLI and `serve` say so
  rather than doing it silently.
- `intake.md` is **not** writable through the body surface. It is editable only
  as a named artifact, because raw input that quietly changes is not raw input.

**Core revision** currently hashes `state.yaml` plus the request
(`fs.py:2904-2907`). It must hash state plus *which* file the body resolved to
plus its content — otherwise promoting intake to a request with identical text
produces an unchanged revision while the editable resource has changed.

Every stage now reads the prior artifact and writes its own. `intake.md` is an
artifact with no stage; `inbox` is a stage with no artifact. They are the two
ends of the same table, not anomalies.

**The board.** `intake` is appended to `WORK_ARTIFACTS`, preserving the existing
letters exactly as `base.py:777-779` requires, and the renderer prefixes it as a
lowercase `i` so the string still reads chronologically. Decided here rather than
deferred, because acceptance criterion 3 depends on it.

Existing items keep working: they have an `initial-request.md`, so the body
surface resolves to it and nothing changes for them. No backfill: an item that
never had intake should not be given a fabricated one.

### Artifacts are keyed by name, not by stage

`LifecycleStep.produces` becomes a **tuple of artifact names**, because
one-artifact-per-stage was never true: `inbox` produces none (`base.py:598`) and
`verify` produces `refined-outcome.md` *or* `rework.md` (`base.py:619`), today
recorded as prose rather than as names.

Templates attach to entries in `WORK_ARTIFACTS`, which is already the real
artifact registry. A stage with no artifacts has no artifact hook; a stage with
two has one hook per artifact name.

`LifecycleStep.sections` is **not** added. An earlier draft introduced it to give
templates and a required-sections check one source, but the criterion that would
have consumed it was rewritten and nothing else needs it. A structured section
list can be added later by whatever actually requires it.

### Stage entry never writes; scaffolding is explicit

Artifact presence is the lifecycle's progress signal — it is what `tcw work list`
renders and what "find your place" reads. C1 exists precisely because a
pre-seeded `initial-request.md` made `R` meaningless. An artifact hook that wrote
a templated `spec.md` at stage entry would re-create that defect for every other
artifact: running `tcw work stage spec` merely to *read the instructions* would
light up `S` before any spec existed.

So the factory is kept, and separated from the real artifact by **filename**:

- `tcw work scaffold <artifact> [ref]` resolves the artifact hook and writes
  `<artifact>.draft.md` — `spec.draft.md`, `plan.draft.md`. It refuses when the
  real artifact already exists.
- `artifacts()` looks up `<name>.md` from `WORK_ARTIFACTS` and never sees a
  draft, so presence stays honest with no new machinery: no content hashing, no
  in-file marker, no adapter-visible draft state.
- Drafts are a **bounded derived namespace** — exactly one per `WORK_ARTIFACTS`
  entry — not an open folder glob. Any store can hold "the draft of artifact N"
  as a named resource. ✓

**`intake`'s built-in template is empty**, and deliberately so: intake has no
prescribed structure, because it is whatever someone supplied. So
`tcw work scaffold intake` produces an empty `intake.draft.md` — a file to type
into — and every artifact keeps the same rule with no carve-out.

That also answers C1's open question about what replaces `tcw work new`'s
`→ edit:` hint. `tcw work new` no longer leaves a file behind, and
`tcw work scaffold intake` is exactly the affordance that used to provide: give
me a path to open and write my request into.
- The agent authors `<artifact>.md` from the draft. C5 decides whether a landed
  artifact removes its draft, and states which.

This also resolves `verify`. Its artifact is chosen by a verdict reached *after*
verification — `refined-outcome.md` on acceptance, `rework.md` on rejection
(`base.py:619`) — which no entry-time factory could pick. Scaffolding is a
separate, later command, so the verdict is known when it runs.

### The order of operations

Stages and transitions each get their own sequence; they are not one sequence.

**Entering a stage** — `tcw work stage <id> [ref]`:

1. Stage/status legality is checked (below). Illegal → exit non-zero, nothing runs.
2. `pre` checks run. Non-zero exit stops everything. `[gated]`
3. Prompt bindings are resolved — files read, `generate` scripts run, conditions
   evaluated.
4. Prompt text is concatenated to **stdout**.

**Nothing is written.** Stage entry is read-only with respect to the item, which
is what makes it safe to run for its instructions alone.

`tcw work scaffold` is the only writing verb, and it resolves fully before
writing: if resolution fails, nothing is written and a retry is clean. If the
*write itself* fails after resolution succeeded, it exits non-zero, reports to
stderr, and writes nothing to stdout. `generate` hooks may re-run on retry, so
they must be documented as needing to be side-effect-free; TCW does not cache a
resolved bundle to avoid it.

Check output goes to **stderr**, as today (`hooks.py:66-69`). Only step 4 writes
to stdout, so `tcw work stage spec` on stdout is exactly the prompt.

`--no-exec` resolves and prints what *would* run — every command, every
`generate` script — and executes nothing. It is how you read an unfamiliar
repository's lifecycle before triggering it.

### Where a stage is legal

The stage verb mutates nothing, but `scaffold` does, and neither should accept a
nonsensical combination — `implement` while the item sits in `backlog`, or `spec`
after it completed. Each stage declares the statuses it is legal in, `postmortem`
explicitly excepted as out-of-band (legal in `review` and after completion,
never changing status — `base.py:620-626`). Checked before any hook runs.

### Exit checks, and the stages that have none

**There is no stage `post` and no `--done`.** Exit checks belong on the *next*
stage's `pre`, and on the following transition's `pre`. This covers most stages
with one check family instead of two, and every check fires at a moment that
actually happens.

It does **not** cover everything, and the earlier claim that it did was wrong:

- **`postmortem` has no successor.** It is out-of-band and terminal. It gets
  `pre` checks and no exit gate. Stated, not papered over.
- **`verify` branches.** Its exit gate is whichever transition follows —
  `complete`'s `pre` on acceptance, `rework`'s on rejection — and `complete` is
  legal directly from `active` (`base.py:455`), so `implement`'s exit gate is
  `submit`'s `pre` *or* `complete`'s.
- **`rework` loops back into `implement`**, so `implement`'s `pre` checks run
  again on the second pass. That is intended — a check worth running before the
  first attempt is worth running before the second — and is stated so nobody
  implements a first-time-only gate.

**Transitions** keep today's semantics exactly: `pre` before anything is written,
`post` after, never rolling back.

### Hook roles

| Role       | Positions                             | Legal kinds                                    | Semantics                                      |
| ---------- | ------------------------------------- | ---------------------------------------------- | ---------------------------------------------- |
| `check`    | stage `pre`, transition `pre`/`post`   | `command`, `skill` (reported, never run)       | Runs. Exit code matters. Output → stderr.      |
| `prompt`   | stage `prompt`                         | `blob`, `file`, `generate`, `builtin`, `skill` | Resolves to text. **All** matches concatenate. |
| `artifact` | stage `artifact`, consumed by `scaffold` | `blob`, `file`, `generate`, `builtin`        | Resolves to text. **First** match wins.        |

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

### Back-compat, every legacy shape

Stage bindings are never executed today, which makes this cheaper than it looks:

| Legacy shape                                    | Today                                               | After                                     |
| ----------------------------------------------- | --------------------------------------------------- | ----------------------------------------- |
| `stages.<id>: [{skill: X}]`                     | Rendered "invoke the X skill"                       | `prompt` binding, kind `skill`, same text |
| `stages.<id>: [{command: C}]`                   | Rendered "run `C`" (`cli.py:648`) — **not executed** | `prompt` binding emitting the same line   |
| `stages.<id>: [{skill: A},{command: B},{skill: C}]` | Rendered **grouped**: skills, then commands     | Same grouped rendering — see below        |
| `stages.<id>: []`                               | Empty; directive renders nothing                    | Empty `prompt` list, unchanged            |
| `transitions.<id>.pre/post: [{command: C}]`     | Executed                                            | `check` binding, unchanged                |
| `transitions.<id>.pre/post: [{skill: X}]`       | Reported to stderr, not run (`hooks.py:54-58`)      | Reported to stderr, unchanged             |
| `transitions.<id>.pre/post: []`                 | Empty; nothing runs                                 | Unchanged                                 |

An earlier draft listed `transitions.<id>.skill: X` as a legacy shape. **It was
never valid** — `transitions.<id>` rejects any key but `pre` and `post`
(`base.py:761-764`). That row is removed rather than supported.

**Rendering order is preserved, not just parse order.** `_directive_text`
(`cli.py:642-649`) groups all skills ahead of all commands, so a mixed list does
*not* render in declaration order today. A naive conversion to declaration-order
composition would change output that criterion 1 requires to be byte-identical.
Legacy-shaped stage lists therefore keep the existing grouped renderer; the
declaration-order rule applies to the new `prompt:` form.

Every row preserves observable behavior. A bare list under `stages.<id>` parses
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

**One already exists, and C2 must unify with it rather than add a second.**
`tcw/serve/__init__.py:51-66` has `_jsonable`/`_json_bytes` — an `asdict()` dump
finished with `json.dumps(…, default=str)` — and the web API ships it today. A
new, separate projection for `tcw work show --json` would create exactly the
two-sources drift this epic exists to remove.

That also relocates the JSON-safety problem: `default=str` is already how the
opaque `capabilities` blob gets past `json.dumps`, lossily, in production. C2 is
not introducing the risk; it is deciding whether to keep that behavior or replace
it, and saying which.

The result is a **versioned DTO**, not a dataclass dump: an explicit `schema`
version, explicitly typed and normalized fields, and an `artifacts` map of name →
presence built on the canonical presence rule. Consumed by `tcw work show
--json`, by `serve`, and — under an `item` key — by `generate` hooks on stdin,
alongside a `hook` object naming role, kind, id, and phase. The same facts go
into the environment beside today's four `TCW_*` variables so a one-line script
needs no JSON parser.

`WorkItem.capabilities` is an opaque `object` (`base.py:843`) filled from
arbitrary YAML (`fs.py:2366-2372`), so it can hold values with no JSON
equivalent. C2 decides explicitly whether to normalize or exclude it, and states
which.

**Amended by C2: `body` is carried in full, and the cap moves to C3.** This
paragraph previously required `body` to be "bounded or excluded — it can be
arbitrarily large". That is not available to a single shared projection:
`serve`'s core editor seeds its draft from `item.body` (`app.tsx:403`), so
excluding the field breaks the web editor, and truncating it means a body
silently cut and then saved back — data loss presenting as a successful save,
which is the defect class C1 spent a rework round closing. The size concern is
real but it belongs where the size actually costs something: **C3 bounds the
`body` it puts on a `generate` hook's stdin**, at the boundary it owns. Recorded
here rather than resolved inside C2, because a child quietly overruling its epic
is how a spec stops being the source of truth.

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

| ID  | Child                             | Delivers                                                                                                                                                                       | Blocked by |
| --- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| C1  | Unify intake                      | `intake.md`; an abstract intake surface; creation paths stop synthesizing requests; the canonical presence rule; body read-fallback and write/promotion contract; core revision; board prefix. | —          |
| C2  | Work item JSON projection         | The versioned DTO + `tcw work show --json`, **unified with `serve`'s existing `_jsonable`**.                                                                                   | C1         |
| C3  | Hook roles, kinds, and conditions  | Roles; kinds incl. the `generate` contract and `file` confinement; `when:`; parse/validate/back-compat; **the full `builtin` syntax and resolution library**; `lifecycle --phase`; new Vocabulary term. | C2         |
| C4  | The stage verb                    | `tcw work stage <id>` — legality → pre → resolve → prompt, plus `--no-exec`. Writes nothing.                                                                                   | C3         |
| C5  | Artifact scaffolding              | `produces` as a tuple; `tcw work scaffold <artifact>`; `<artifact>.draft.md`; templates keyed by artifact name. **(The stage/status legality table moved to C4 — see below.)**   | C3         |
| C6  | Built-in stage prompts            | `tcw/work/prompts/*.md` content and wheel packaging, **plus the floor that makes them reachable** — see the amendment below. The `builtin` kind itself is still C3's.          | C3         |
| C7  | Skill and documentation rewrite   | Stage docs → routers; `hooks.md` rewritten; README lifecycle section; final consolidation only.                                                                                | C4, C5, C6 |
| C8  | Backlog and upstream-issue audit  | No code. This repo's own backlog and the TCW GitHub issues reconciled against the shipped design — discarded, rescoped, or newly filed.                                         | C7         |

Order: C1 → C2 → C3 → {C4, C5, C6} → C7 → C8. C4, C5, and C6 are all parallel
once C3 lands; do not chain them.

**C8 carries no acceptance criterion.** It ships no behavior, so the criteria
below cover C1–C7 only; C8's correctness is the user approving each disposition.
It is last because a backlog audited against a half-landed design produces
dispositions that are stale by the time the epic closes.

**C5 no longer depends on C4.** Scaffolding is its own verb, so it needs C3's
resolution library and nothing from the stage verb — the dependency that earlier
drafts justified first as sequencing and then as technical turns out to be
neither, once entry stopped writing.

**Amended by C4: the stage/status legality table belongs to C4, and C5 consumes
it.** This spec assigned it to C5 with both consulting it, which leaves the two
parallel children racing for the same contract data. C4 is the one that cannot
function without it — criterion 9 is C4's — so C4 defines
`STAGE_STATUSES` beside `LIFECYCLE_STEPS` and C5 reads it. Recorded here rather
than as a deviation inside C4, because a child overruling its epic quietly is
how the epic stops being the source of truth.

**`builtin` belongs entirely to C3.** An earlier draft split its syntax into C3
and its resolution into C6, which left C4 able to meet valid `builtin`
configuration with no implementation behind it. C6 supplies packaged content —
and, per the amendment below, the one condition that makes it reachable.

**Amendment: C6 owns the floor.** This spec scoped C6 to "content and wheel
packaging only", and criterion 14 asks for built-in instructions **with nothing
configured**. Against the shipped code those two cannot both hold. Verified on
this repo, which configures no `work.lifecycle` key at all:

```
$ tcw work stage spec 2026-08-12-ship-built-in-stage-prompts-with-the-cli
$ echo $?
0
```

Nothing printed. Two reasons, neither a defect in the child that shipped it:
`LifecyclePolicy.stage()` returns `[]` for a stage the node never configured
(`base.py:641-650`), so `resolve_prompts` iterates nothing whatever the registry
holds; and `tcw work stage` passes the empty default `Builtins()`
(`cli.py:800-803`), so even an explicit `builtin: true` resolves to `""`. C3's
`Builtins` docstring says "C6 fills `stage_prompts`" and C4 wired the only value
that existed at the time. This is a seam the epic did not cost, not a regression.

So **C6 additionally delivers**: the floor in `resolve_prompts` (a stage with no
prompt bindings resolves as if it bound `[{builtin: true}]`), the argument at
`cli.py:801`, and — because the floor makes `prompt: []` indistinguishable from
an absent key — a `tcw validate` rejection of an empty prompt list in both
spellings, which is the requester's decision and the epic's one deliberate
back-compat break. The floor is inert while the registry is empty, so no existing
C3 or C4 test changes.

Recorded here rather than inside C6, for the same reason the C4 amendment above
is: a child overruling its epic quietly is how the epic stops being the source of
truth. **Criterion 14 stands as written** — this amendment names who makes it
satisfiable, and adds that `tcw validate` must reject `prompt: []`.

## Acceptance criteria

1. A `tcw-config.yaml` valid before this epic parses afterwards with identical
   observable behavior, proven by a corpus of legacy config shapes — at minimum
   one per row of the back-compat table — asserting byte-identical resolved
   output against a pre-epic baseline. `tests/test_lifecycle_policy.py:77-82`
   passes unmodified.
2. `tcw work new "t"` with no stdin creates **no** `initial-request.md` and no
   `intake.md`; with piped stdin it creates `intake.md` whose content equals the
   decoded stdin text under a stated encoding-and-errors policy — `_stdin_body`
   decodes rather than reading bytes and swallows read errors as empty
   (`cli.py:90-96`), so "exactly the piped bytes" was not a promise this
   interface can keep. `tcw work inbox accept` creates `intake.md` for a text
   entry, a folder entry, **and** a binary-only entry, preserving attachments,
   the `origin`-bearing manifest, and the binary fallback prose in every case.
   All three are tested. No code path synthesizes a request document.
3. `tcw work list` shows `R` only for items whose `request` stage has run, and
   the lowercase `i` prefix for items with intake — verified on a fresh item
   (neither), an intake-only item (`i`), a post-`request` item (`iR`), and a
   legacy item with a request and no intake (`R`).
4. `tcw work show` displays the intake on an intake-only item, the request once
   `request` has run, and an empty body — without raising — on an item with
   neither. An empty `initial-request.md` beside a non-empty `intake.md` displays
   the intake, because one presence rule governs both the body surface and the
   board.
4b. Editing the body of an intake-only item writes `initial-request.md`, reports
    that it promoted the item, and leaves `intake.md` byte-identical. This holds
    through `tcw work edit` and through `serve`'s PATCH path
    (`serve/__init__.py:984-991`). Promoting intake to a request whose text is
    identical still changes the core revision.
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
   check's stdout and stderr goes to stderr. Running it for any stage writes
   nothing: no artifact, no draft, no state change — verified by comparing the
   item folder before and after.
9. A failing stage `pre` check exits non-zero with no prompt resolved, and a
   stage run in an illegal status (`implement` from `backlog`, `spec` after
   completion) exits non-zero **before** any check, generator, or write runs.
   `postmortem` is legal in `review` and after completion.
10. `tcw work scaffold <artifact>` resolves fully before writing: when a hook
    fails, nothing is written and a retry succeeds. When the *write* fails after
    resolution succeeded, it exits non-zero, reports to stderr, and writes
    nothing to stdout.
11. `tcw work scaffold spec` writes `spec.draft.md` with exactly the resolved
    content, does not create `spec.md`, and **does not change** what
    `tcw work list` shows for that item — an implementation that writes nothing
    fails the first clause, and one that writes `spec.md` fails the third. It
    refuses when `spec.md` already exists.
12. `tcw work lifecycle` still executes nothing — a bound command writing a
    sentinel file, run for every stage and transition id, leaves no sentinel.
13. `tcw work lifecycle --transition complete --phase pre --directive` reports
    only the `pre` bindings. `--phase` accepts `pre` and `post` for a transition
    and `pre` only for a stage, since stages no longer have a `post`; `--phase
    post` on a stage is an error naming the reason rather than empty output.
14. **(Amended — see "Amendment: C6 owns the floor" below.)** With nothing
    configured, `tcw work stage <id>` prints built-in instructions
    for each of `request`, `spec`, `plan`, `implement`, `verify`, and
    `postmortem` — enumerated, and asserted as **exact set equality** against the
    shipped registry so neither an empty file nor a missing stage passes.
    `inbox` ships none, because it runs before an item exists — and
    `tcw work stage inbox` therefore has no item to resolve against and is
    rejected with that reason, rather than printing nothing. `{builtin: true}`
    composed with a node binding prints both in declaration order.
15. `tcw validate` rejects, each naming the offending key: an unknown role key;
    `command` in a prompt position; `skill` in a check position; an unknown
    `when:` key; an invalid `type` value; a `file` path that does not exist or
    escapes the node root; a `builtin` artifact binding that is not last or is
    conditional; and an artifact entry made unreachable by a preceding
    unconditional match.
16. `--no-exec` prints every command and `generate` script that would run and
    executes none — verified by the sentinel technique from criterion 12.
17. A built-in template exists for **every** name in `WORK_ARTIFACTS`, asserted
    as exact set equality rather than as "at least one", and each has exactly one
    definition in the codebase. `intake`'s is **empty**, asserted explicitly so
    nobody helpfully adds headings to it later, and `tcw work scaffold intake`
    creates an empty `intake.draft.md` rather than refusing.
18. Every stage document in `skills/tcw-work/references/` routes to the CLI for
    its instructions rather than restating them — and **still carries** the
    TCW-specific judgment the CLI does not: the stage's delegability, its
    `[gated]`/`[judgment]` markers, and its epic deltas. Tested as both
    directions, so a near-empty router that merely names the command fails.

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
- **`tcw serve` diverges further.** It runs no hooks, so nothing scaffolds from
  the web app. C5 decides explicitly whether scaffolding — pure text rendering
  for `blob`/`file`/`builtin`, but shell for `generate` — is offered there, and
  whether the safe subset is worth the split. "Serve runs no hooks" answers a
  question about shell and does not settle the non-shell kinds by itself.
- **`generate` hooks re-run on retry.** Resolve-then-write means a failed write
  discards resolved output, so the next attempt re-executes every generator. TCW
  does not cache a resolved bundle to prevent this — that would be state to
  invalidate — so generators must be documented as needing to be side-effect-
  free. A generator that posts to an external system will post twice.
- **Drafts can go stale.** `spec.draft.md` sits beside `spec.md` with no
  guarantee they agree, and a draft left behind after the artifact lands is
  clutter that reads as unfinished work. C5 decides whether landing an artifact
  removes its draft.
- **Plugin/CLI version skew.** A stale `tcw` serves stale instructions to a fresh
  skill. The routers must not restate what the prompts say (criterion 18), so
  skew reads as an old-but-coherent answer rather than a contradiction.
- **Scope creep into a config language.** `when:` has three keys by decision.
  Each key added later must be validated, documented, and supported forever;
  `generate` exists so that pressure has somewhere to go.

## Review corrections

Changes made after two adversarial `codex` / `bllm-review` passes, recorded so
the reasoning is not lost.

### Round 2

- **Stage entry wrote the artifact, re-creating the exact defect C1 exists to
  fix** (codex R2-1). Writing a templated `spec.md` at entry would light up `S`
  on the board before any spec existed. Resolved by the requester's decision:
  stage entry writes nothing, and `tcw work scaffold` writes `<artifact>.draft.md`
  — a distinct filename `artifacts()` never sees, so presence stays honest with
  no content hashing, no in-file marker, and no adapter-visible draft state. The
  repair I had considered — presence as "differs from the scaffold" — was
  rejected because comparing against the scaffold means re-running the factory at
  read time, so a `generate` hook would execute shell during `tcw work list`.
- **`verify` could not use an entry-time factory** (codex R2-2), since its
  artifact is chosen by a verdict reached after the stage. Dissolved by the same
  change: scaffolding is a separate, later command.
- **"Next stage's `pre` covers every stage" was false** (codex R2-3, bllm 3).
  `postmortem` is terminal and out-of-band; `verify` branches; `complete` is
  legal directly from `active`. Now stated per stage, including that `postmortem`
  has no exit gate and that a `rework` loop re-runs `implement`'s `pre`.
- **`request.inputs` read as required** (codex R2-4). `inputs` is descriptive and
  enforced nowhere (`cli.py:621-622`); intake is optional and legacy items have
  none.
- **Body writes were undefined** (codex R2-5, found independently). Reads
  fall back; writes always target `initial-request.md` and are an explicit
  promotion. `intake.md` is not writable through the body surface.
- **"Present" meant two different things** (codex R2-6) — `.exists()` in
  `_read_item`, non-empty in `artifacts()`. One canonical resolver now, shared by
  every reader.
- **Inbox acceptance would have lost provenance** (codex R2-7, bllm 2). The
  earlier "delete `fs.py:2755-2769`" was too glib: those lines carry the
  origin-bearing manifest and the binary fallback. Now a refactor, with text,
  folder, and binary-only entries all tested.
- **The stage verb had no status legality contract** (codex R2-8) — `implement`
  from `backlog` was permitted. Now checked before any hook runs.
- **The back-compat table would have changed rendering order** (codex R2-9).
  `_directive_text` groups skills before commands, so declaration-order
  composition could not be byte-identical. Legacy lists keep the grouped
  renderer.
- **The table listed a shape that was never valid** (codex R2-10, bllm 4).
  `transitions.<id>.skill: X` is rejected by `base.py:761-764`. Row removed;
  transition-phase `skill` bindings and empty lists added.
- **The board representation was deferred while a criterion depended on it**
  (codex R2-11). Decided here: appended to `WORK_ARTIFACTS`, rendered as a
  lowercase `i` prefix.
- **Core revision was underspecified for a two-source body** (codex R2-12) — it
  must hash which file resolved, not only its content.
- **Reinterpreting the abstract `body` parameter as `intake.md` failed the litmus
  test** (codex R2-13). C1 adds an explicit abstract intake surface instead.
- **Write-failure behavior was undefined** (codex R2-14, bllm 5) → exit non-zero,
  stderr only, nothing on stdout; generators documented as needing to be
  side-effect-free rather than cached.
- **C3 and C6 both owned `builtin`** (codex R2-15) → entirely C3's; C6 ships
  content.
- **C6 could not land green against its own criterion, and the checkpoint
  reference was off by one** (codex R2-16) → acceptance split, numbering fixed.
- **AC 14/17/18 admitted wrong implementations** (codex R2-17) → exact set
  equality, and routers tested in both directions.
- **AC 2 promised byte preservation through a text interface** (codex R2-18) →
  decoded text with a stated encoding policy.
- **`LifecycleStep.sections` had no consumer** (codex R2-19) → cut.
- **The body surface was undefined when both files are absent** (bllm 1) → an
  explicit third rung returning `""`.
- **A second JSON projection would have been built** (found independently) —
  `serve` already ships `_jsonable`/`_json_bytes` (`serve/__init__.py:51-66`).
  C2 unifies with it; `default=str` is the existing answer to the `capabilities`
  problem, to be kept or replaced deliberately.
- **Not accepted:** bllm's "latest artifact wins the board letter" — the board
  renders every present artifact as a letter string, not one letter; and bllm's
  "DAG is clean, no over-engineering" verdict, which round-2 codex contradicted
  with specific evidence on both counts.

### Round 1

- **One artifact per stage was false.** `produces` is now a tuple and artifacts
  are keyed by name (codex F1).
- **Conditional request templates were impossible as first specced** — both
  creation paths wrote `initial-request.md` unconditionally, so a create-if-absent
  hook could never fire (codex F3). Resolved by C1's intake unification, which
  the requester proposed and which subsumes the finding.
- **Back-compat covered one shape of several**, and an existing test asserted a
  shape the draft matrix forbade (codex F2). The fix is cheap because stage
  bindings are never executed today. (Round 2 corrected the table again.)
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
- **C5→C4 was an artificial dependency** (bllm). Round 2 removed it entirely:
  once stage entry stopped writing, scaffolding needed nothing from the stage
  verb.
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
