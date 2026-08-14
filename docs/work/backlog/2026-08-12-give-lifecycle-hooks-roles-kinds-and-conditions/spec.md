# Spec — Give lifecycle hooks roles, kinds, and conditions

Child **C3**. The initiative's `spec.md` decides the boundaries; this decides how
C3 is built and settles the questions it left open.

## Problem

`Binding` is `skill` or `command` (`base.py:535-546`), and neither carries
instructions. `skill` names something that has them; `command` names a program to
run. There is no third thing, so a node cannot supply text.

Worse, the two are not even doing what their names suggest. **Stage bindings are
never executed.** `run_pre`/`run_post` handle transitions only (`hooks.py:79-101`),
so a stage `command:` renders through `_directive_text` (`cli.py:673-691`) as
prose telling the agent to run it. A stage binding has always been a *prompt* —
just a very bad one, limited to naming a skill or quoting a command line.

That is what makes this change cheaper than it looks: the role a stage binding
plays today is the role `prompt` names, so giving it that name breaks nothing.

## Goals

1. Roles are named and enforced: `check` runs and may fail, `prompt` resolves to
   text, `artifact` is a template.
2. Text can come from the config, a file, a script, or TCW itself.
3. A binding can depend on the item, with three condition keys and no more.
4. Resolution is a library function C4 and C5 call, not a command.
5. Every existing `tcw-config.yaml` produces byte-identical output.

## Non-goals

- Any new command verb. `tcw work stage` is C4's, `tcw work scaffold` is C5's.
  C3 adds `--phase` to `tcw work lifecycle` and nothing else.
- Making `tcw work lifecycle` execute anything. It stays inert; criterion 12
  is a test, not a hope.
- The content of the built-in prompts. C3 resolves `builtin`; C6 supplies what it
  resolves to. Until C6 lands, `builtin` resolves to nothing for every stage, and
  that is a legal state rather than a failure.
- Sandboxing. The trust model at `hooks.py:11-14` is unchanged and restated.

## Design

### The model

```python
@dataclass(frozen=True)
class Condition:
    tags: tuple[str, ...] = ()          # any-of
    not_tags: tuple[str, ...] = ()      # none-of
    type: str | None = None             # None = unset; "" matches a non-epic

@dataclass(frozen=True)
class Binding:
    kind: str = ""                      # blob|file|generate|builtin|skill|command
    value: str = ""                     # "" for builtin
    when: Condition | None = None

@dataclass
class StageBindings:
    pre: list[Binding] = field(default_factory=list)       # role: check
    prompt: list[Binding] = field(default_factory=list)    # role: prompt

@dataclass
class LifecyclePolicy:
    stages: dict[str, StageBindings]
    transitions: dict[str, TransitionBindings]
    artifacts: dict[str, list[Binding]]                    # role: artifact
    timeout: int = 300
    output_cap: int = 64 * 1024
```

**`Binding` loses its `skill=`/`command=` constructor.** It is replaced by
`kind`+`value`, because a field per kind is how a two-kind model becomes a
six-kind mess. Two assertions in `tests/test_lifecycle_policy.py` construct
bindings that way and are updated; criterion 1's protected test
(`test_declaration_order_is_significant_and_preserved`, lines 77-82) reads only
`.ref` and is untouched. `.ref` survives as a property returning `value`, because
seven call sites read it and renaming them buys nothing.

**`policy.stage(id)` keeps returning the prompt list**, not the `StageBindings`
object. That is not a compatibility hack — it is the accurate reading. Stage
bindings were prompts all along, so the accessor that returned them keeps
returning them, and the new checks arrive through `policy.stage_checks(id)`.
Every existing caller and test keeps working because the meaning did not change.

### Where artifact bindings live

The initiative's role table lists `artifact` in position "stage `artifact`",
written before round 2 moved scaffolding out of stage entry. Once
`tcw work scaffold <artifact>` became the verb, keying templates by stage stopped
making sense: `verify` produces two artifacts and `inbox` produces none, and the
command takes an artifact name.

So artifact bindings are a **top-level map keyed by artifact name**:

```yaml
work:
    lifecycle:
        artifacts:
            spec:
                - blob: "# Spec\n\n## Problem\n"
                  when: { tags: [bug] }
                - builtin: true
```

Keys are validated against `WORK_ARTIFACTS`. This is the initiative's intent
("templates attach to entries in `WORK_ARTIFACTS`, which is already the real
artifact registry") expressed in the config, and it is recorded here as a
decision C3 made rather than one it inherited.

### The config shape

```yaml
work:
    lifecycle:
        timeout: 300
        output-cap: 65536
        stages:
            spec:
                pre:
                    - command: ./bin/spec-ready.sh
                prompt:
                    - builtin: true
                    - blob: "In this repo, specs name their rejected options."
                    - file: docs/spec-guide.md
                    - generate: ./bin/spec-prompt.py
                      when: { tags: [bug] }
        transitions:
            complete:
                pre: [{ command: pytest -q }]
        artifacts:
            spec:
                - builtin: true
```

A **bare list** under `stages.<id>` still parses, as `prompt:`. That is the
legacy shape and the whole back-compat story rests on it.

### Roles and legal kinds

| Role       | Position                              | Legal kinds                                    | Semantics                                  |
| ---------- | ------------------------------------- | ---------------------------------------------- | ------------------------------------------ |
| `check`    | `stages.<id>.pre`, `transitions.<id>.pre`/`post` | `command`, `skill`                  | Runs. Exit code matters. Output → stderr.  |
| `prompt`   | `stages.<id>.prompt`                  | `blob`, `file`, `generate`, `builtin`, `skill` | Resolves to text. **All** matches concatenate, in declaration order. |
| `artifact` | `artifacts.<name>`                    | `blob`, `file`, `generate`, `builtin`          | Resolves to text. **First** match wins.    |

`skill` is legal in a check position because it already is — `run_bindings`
reports it to stderr without running it (`hooks.py:54-58`) and the initiative's
back-compat table requires that unchanged. It is legal in a prompt position
because that is what a legacy stage binding becomes. It is illegal in an artifact
position: a skill name is not a template.

`command` in a prompt or artifact position is a validation error naming
`generate`. This is the one kind whose misuse is likely and whose correct
alternative has a name.

### The kinds

- **`blob:`** — the text, inline. Used verbatim.
- **`file:`** — a node-relative path. Normalized and confined to the node root; a
  path escaping it is a **validation** error, not a read. A non-existent path is
  also a validation error, so `tcw validate` catches a typo rather than a stage
  run failing later.
- **`generate:`** — a shell command. Contract below.
- **`builtin: true`** — TCW's shipped default for this stage or artifact. The
  value is the literal `true`; any other value is an error. In a `prompt` list it
  composes with everything else, so `{builtin: true}` first then a node's own
  binding yields both, in that order. In an `artifact` list first-match-wins
  makes it a **fallback**, so it must be **last** and **unconditional**;
  `tcw validate` rejects it anywhere else.
- **`skill:`** — resolves to the same sentence `_directive_text` renders today.
  Documented as the weakest kind: it is a name, not instructions.
- **`command:`** — check role only.

### The `generate` contract

Enforced, not aspirational:

- **stdin** — a JSON object `{"item": <C2's DTO>, "hook": {"role", "kind", "id",
  "phase"}}`. `id` is the stage or artifact name; `phase` is `"prompt"`,
  `"artifact"`, `"pre"`, or `"post"`.
- **The `body` is capped at 64 KiB**, replaced by its first 64 KiB when longer,
  and a sibling key `"body_truncated": true` says so. This is the debt C2's
  amendment assigned to C3. It is a *different* document from what `serve`
  returns by exactly this field, and the flag is what keeps that honest — a hook
  that cares can check it rather than silently reasoning about a truncated
  request.
- **Environment** — the four existing `TCW_*` variables, plus `TCW_HOOK_ROLE`,
  `TCW_HOOK_KIND`, `TCW_HOOK_ID`, and `TCW_HOOK_PHASE`, so a one-line script
  needs no JSON parser.
- **Timeout** — the existing `work.lifecycle.timeout`. Exceeding it fails the
  command; it does not truncate.
- **Output cap** — `work.lifecycle.output-cap`, default **64 KiB**. Exceeding it
  fails the command with a message naming the cap. Reading is bounded rather than
  buffered unbounded, so a runaway script cannot exhaust memory before the check.
- **Encoding** — stdout is decoded UTF-8 with `errors="replace"`. Stated because
  the alternative — failing on one bad byte in an otherwise fine prompt — trades
  a usable result for a purity nobody asked for.
- **Non-zero exit discards everything.** All stdout is dropped, the command
  fails, and the exit code is named. A script that writes half a prompt and then
  dies contributes nothing rather than something plausible.

`generate` hooks must be **side-effect-free**: resolution can re-run (C5's
resolve-then-write discards resolved output on a failed write), so a generator
that posts to an external system posts twice. Documented rather than cached —
a cached bundle is state to invalidate.

### Conditions

```yaml
when:
    tags: [bug, regression] # any of
    not_tags: [spike] # none of
    type: epic # validated; "" matches a non-epic
```

Keys are ANDed. A list value means any-of. `tags`/`not_tags` match against the
item's tags. `type` is compared exactly against `item.type`, and its value is
validated against the known set (`""` and `"epic"`) so a typo fails at
`tcw validate` rather than silently never matching.

`when:` on a binding with no item to match against — resolution called without an
item, which is what an artifact template for a brand-new item would need — treats
a conditional binding as **not matching**. Stated so it is not discovered.

### Resolution, as a library

```python
def resolve_prompts(policy, stage_id, item, node_root, builtins) -> ResolvedText
def resolve_artifact(policy, artifact, item, node_root, builtins) -> ResolvedText
```

Both live in `tcw/work/resolve.py`. They return the concatenated text plus the
list of what ran, so `--no-exec` (C4) can print the plan without executing and
share one code path with the real thing. `builtins` is a mapping name → text,
supplied by the caller; C6 fills it, C3 ships it empty.

**Resolution never writes.** It reads files, runs generators, and returns text.
Everything that writes is C5's.

### `--phase`

`tcw work lifecycle --transition complete --phase pre --directive` reports only
the `pre` bindings. `--phase` accepts `pre` and `post` for a transition, and
`pre` and `prompt` for a stage. `--phase post` on a stage is an **error naming
the reason** — stages have no `post` — rather than empty output, because silence
reads as "nothing configured".

### Back-compat, every legacy row

| Legacy shape                                        | Today                                   | After                                   |
| --------------------------------------------------- | --------------------------------------- | --------------------------------------- |
| `stages.<id>: [{skill: X}]`                         | Rendered "invoke the X skill"           | `prompt` list, kind `skill`, same text  |
| `stages.<id>: [{command: C}]`                       | Rendered "run \`C\`" — **not executed** | `prompt` list, kind `command`… see below |
| `stages.<id>: [{skill: A},{command: B},{skill: C}]` | Rendered **grouped**: skills then commands | Same grouped rendering               |
| `stages.<id>: []`                                   | Empty; renders nothing                  | Empty `prompt` list, unchanged          |
| `transitions.<id>.pre/post: [{command: C}]`         | Executed                                | `check`, unchanged                      |
| `transitions.<id>.pre/post: [{skill: X}]`           | Reported to stderr, not run             | Unchanged                               |
| `transitions.<id>.pre/post: []`                     | Nothing runs                            | Unchanged                               |

**The `command`-in-a-prompt contradiction, and how it is resolved.** The role
table forbids `command` in a prompt position; the legacy table requires
`stages.<id>: [{command: C}]` to keep working. Both are right, and the resolution
is that the prohibition applies to the **new explicit `prompt:` key** only. A
bare legacy list accepts `command` and renders it exactly as today. Writing
`prompt: [{command: C}]` is an error naming `generate`. This is stated because an
implementation that applied one rule everywhere would break either back-compat or
the validation criterion, and the two tables in the initiative's spec do not say
which.

**Rendering order is preserved, not just parse order.** `_directive_text` groups
all skills ahead of all commands, so a mixed legacy list does *not* render in
declaration order today. Legacy-shaped stage lists therefore keep the existing
grouped renderer; declaration-order concatenation applies to the new `prompt:`
form. A list is "legacy-shaped" when it arrived as a bare list rather than under
`prompt:`, and the policy records which, because the two render differently and
nothing else can tell them apart afterwards.

## Acceptance criteria

The initiative's criteria 1, 6, 7, 12, 13, and 15 are the requirement.

1. **Legacy corpus, byte-identical.** One `tcw-config.yaml` per row of the
   back-compat table, each asserted to produce the same `tcw work lifecycle`
   output — full, `--directive`, and `--json` — as a baseline **captured from the
   CLI before the parser is touched** and committed in its own commit.
   `test_declaration_order_is_significant_and_preserved` passes unmodified.
2. **`generate` gets the projection and its own metadata.** A hook script that
   dumps its stdin shows `item.schema`, the item's slug, and a `hook` object
   naming role, kind, id, and phase. Its stdout becomes the prompt.
3. **A `generate` hook exiting non-zero after writing to stdout contributes
   nothing**, and the command fails naming the exit code. Asserted on the
   resolved text, not only on the exit status — an implementation that returns
   the partial text *and* fails would pass a status-only check.
4. **The output cap fails rather than truncating.** A script emitting one byte
   over the cap fails with a message naming the cap; the resolved text is not the
   truncated prefix. A script emitting exactly the cap succeeds.
5. **The timeout fails rather than truncating**, with the existing message shape.
6. **The `body` on stdin is capped at 64 KiB and says so.** An item with a
   larger body yields `body` of exactly 64 KiB and `body_truncated: true`; a
   small one yields the whole body and `body_truncated: false`. This is the debt
   C2's amendment assigned here, so it is asserted rather than assumed.
7. **The `when:` truth table, exhaustively**: each key alone; AND across keys;
   any-of within a list; `not_tags` exclusion; `type: epic` and `type: ""` and
   `""` matching a non-epic; overlapping matches; no match; and no item at all.
8. **`tcw validate` rejects each of these, naming the offending key**: an unknown
   role key under a stage; `command` under `prompt:`; `skill` under `artifacts`;
   an unknown `when:` key; an invalid `type` value; a `file` path that does not
   exist; a `file` path escaping the node root; `builtin` in an artifact list
   that is not last; a conditional `builtin` in an artifact list; and an artifact
   entry made unreachable by a preceding unconditional match. Ten rejections,
   each a separate assertion on the message.
9. **`tcw work lifecycle` still executes nothing.** A `generate` and a `command`
   binding that each write a sentinel file, configured on every stage and
   transition id, leave no sentinel after running `lifecycle` in all its forms.
10. **`--phase`**: `--transition complete --phase pre --directive` reports only
    `pre`; `--phase post` on a stage errors naming the reason; `--phase prompt`
    on a transition errors likewise.
11. **`file:` confinement** is enforced at validation, and resolution of a
    confined path reads it verbatim.
12. **`builtin` with an empty registry resolves to nothing and is not an error** —
    the state C3 ships in, before C6.
13. **First-match-wins for artifacts, all-match-concatenates for prompts**, each
    asserted with a conditional binding that matches and one that does not.

## Risks

- **This rewrites the path every existing config takes.** The mitigation is
  criterion 1's captured baselines and the fact that C3 adds no new verb, so a
  regression surfaces in the existing suite. Running the new parser against this
  repository's own `tcw-config.yaml` is the check that covers shapes the corpus
  did not think of.
- **The `command`-in-prompt resolution is a wart.** One key accepts a kind
  another rejects, forever, because the legacy shape cannot be renamed. The
  alternative is breaking configs or dropping criterion 15; this is the least bad
  and it is documented in both directions.
- **`generate` widens the blast radius of a hostile config.** The posture is
  unchanged in principle — `tcw work start` already runs config shell — but the
  frequency rises once agents run stage entry routinely. `--no-exec` (C4) and
  `lifecycle` staying inert (criterion 9) are the mitigations; consent prompts
  are not, per the initiative's decision.
- **The `body` cap changes what a hook sees versus what the API returns.** Two
  documents differing in one field is a real inconsistency; `body_truncated`
  makes it detectable rather than silent. The alternative — an unbounded body on
  a pipe — is what C2's amendment rejected.
- **`builtin` resolving to nothing is indistinguishable from "not configured"**
  until C6 lands. Accepted for the window between C3 and C6; criterion 12 pins it
  as intended rather than accidental.
