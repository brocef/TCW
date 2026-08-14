# Spec — Give lifecycle hooks roles, kinds, and conditions

Child **C3**. The initiative's `spec.md` decides the boundaries; this decides how
C3 is built and settles what it left open.

> Rewritten after adversarial review by `codex` and `bllm-review`, which found
> the first draft not ready to implement. Six things it asserted were false or
> unrepresentable; one was a contradiction inside the *epic's* spec, amended
> there. See `## Review corrections`.

## Problem

`Binding` is `skill` or `command` (`base.py:535-546`), and neither carries
instructions. `skill` names something that has them; `command` names a program to
run. There is no third thing, so a node cannot supply text.

Worse, the two are not doing what their names suggest. **Stage bindings are never
executed.** `run_pre`/`run_post` handle transitions only (`hooks.py:79-101`), so a
stage `command:` renders through `_directive_text` (`cli.py:673-691`) as prose
telling the agent to run it. A stage binding has always been a *prompt* — a bad
one, limited to naming a skill or quoting a command line.

That is what makes this cheaper than it looks: the role a stage binding plays
today is the role `prompt` names, so giving it that name breaks nothing.

## Goals

1. Roles are named and enforced: `check` runs and may fail, `prompt` resolves to
   text, `artifact` is a template.
2. Text can come from the config, a file, a script, or TCW itself.
3. A binding can depend on the item, with three condition keys and no more.
4. Resolution is a library function C4 and C5 call, with a plan mode that
   executes nothing.
5. Every existing `tcw-config.yaml` produces byte-identical output.

## Non-goals

- Any new command verb. `tcw work stage` is C4's, `tcw work scaffold` is C5's.
  C3 adds `--phase` to `tcw work lifecycle` and nothing else.
- Making `tcw work lifecycle` execute anything.
- The *content* of the built-ins. C3 resolves `builtin`; C6 supplies stage prompt
  text and C5 supplies artifact templates. C3 ships both registries empty.
- Sandboxing. The trust model at `hooks.py:11-14` is unchanged and restated.
- The stage/status legality table. The initiative assigns it to C5, which C4
  consumes; C3 neither defines nor needs it.

## Design

### The model

```python
@dataclass(frozen=True)
class Condition:
    tags: tuple[str, ...] = ()          # any-of
    not_tags: tuple[str, ...] = ()      # none-of
    type: str | None = None             # None = unset; "" matches a non-epic

    def matches(self, item) -> bool     # item is None → False (see below)

@dataclass(frozen=True)
class Binding:
    kind: str = ""                      # blob|file|generate|builtin|skill|command
    value: str = ""                     # "" for builtin
    when: Condition | None = None

@dataclass
class StageBindings:
    pre: list[Binding] = field(default_factory=list)      # role: check
    prompt: list[Binding] = field(default_factory=list)   # role: prompt
    legacy_prompt: bool = False         # the prompts arrived as a bare list

@dataclass
class LifecyclePolicy:
    stages: dict[str, StageBindings] = field(default_factory=dict)
    transitions: dict[str, TransitionBindings] = field(default_factory=dict)
    artifacts: dict[str, list[Binding]] = field(default_factory=dict)
    timeout: int = 300
    output_cap: int = 64 * 1024
```

**`legacy_prompt` is a real field, not an implementation detail.** The first
draft said "the policy records which form was used" and then showed a model with
nowhere to record it. It has to survive directive rendering, human rendering,
`--json`, and any copy of the policy, because a bare list and an explicit
`prompt:` list are otherwise indistinguishable after parsing and they render
differently. A private side table would satisfy a test and break equality and
serialization.

**`Binding` loses its `skill=`/`command=` constructor**, replaced by
`kind`+`value`: a field per kind is how a two-kind model becomes a six-kind mess.
`.ref` survives as a property returning `value` — seven call sites read it and
renaming them buys nothing. Two assertions in `tests/test_lifecycle_policy.py`
construct bindings the old way and are updated; criterion 1's protected test
(lines 77-82) reads only `.ref` and is untouched. The only non-test construction
sites are the two inside `_parse_binding` itself.

**`policy.stage(id)` keeps returning the prompt list**, and that is the accurate
reading rather than a compatibility hack: stage bindings were prompts all along.
Checks arrive through a new `policy.stage_checks(id)`.

**`policy.stages` changes type**, from `dict[str, list[Binding]]` to
`dict[str, StageBindings]`, and that is a real break for anyone indexing it
directly. In this tree nothing does: every in-tree read is either `policy.stage()`
(`cli.py:711`) or a comparison against `{}` (`test_lifecycle_policy.py:59`, `:281`,
`:306`). Stated precisely because the first draft claimed "every existing caller
and test keeps working" about an attribute whose type it was changing.

### Where artifact bindings live

The initiative's role table lists `artifact` in position "stage `artifact`",
written before round 2 moved scaffolding out of stage entry. Once
`tcw work scaffold <artifact>` became the verb, keying templates by stage stopped
making sense: `verify` produces two artifacts and `inbox` produces none, and the
command takes an artifact name.

So artifact bindings are a **top-level map keyed by artifact name**, validated
against `WORK_ARTIFACTS`:

```yaml
work:
    lifecycle:
        artifacts:
            spec:
                - blob: "# Spec\n\n## Problem\n"
                  when: { tags: [bug] }
                - builtin: true
```

This is the initiative's stated intent ("templates attach to entries in
`WORK_ARTIFACTS`, which is already the real artifact registry") expressed in
config, recorded as C3's decision rather than as something inherited.

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

A **bare list** under `stages.<id>` still parses, as `prompt:` with
`legacy_prompt = True`.

### Roles and legal kinds

| Role       | Position                                         | Legal kinds                                    | Semantics                                  |
| ---------- | ------------------------------------------------ | ---------------------------------------------- | ------------------------------------------ |
| `check`    | `stages.<id>.pre`, `transitions.<id>.pre`/`post` | `command`, `skill` (reported, never run)       | Runs. Exit code matters. Output → stderr.  |
| `prompt`   | `stages.<id>.prompt`, or a bare stage list       | `blob`, `file`, `generate`, `builtin`, `skill` | Resolves to text. **All** matches concatenate. |
| `artifact` | `artifacts.<name>`                               | `blob`, `file`, `generate`, `builtin`          | Resolves to text. **First** match wins.    |

The epic's role table said `check` accepted `command` only, while its own
back-compat table required `transitions.<id>.pre/post: [{skill: X}]` to keep
being reported to stderr. That is a contradiction inside the epic, not a choice
C3 gets to make quietly; **the epic's role table is amended** in the same commit
as this spec.

`command` in a prompt or artifact position is a validation error naming
`generate`. See the exception below.

### The `command`-in-a-prompt exception, stated as narrowly as it is real

The prohibition applies to the **explicit `prompt:` key** and to `artifacts.<name>`.
A **bare legacy list** accepts `command` and renders it exactly as today.

Both rules are load-bearing and neither can be dropped: applying the prohibition
everywhere breaks configs the back-compat table promises, and dropping it fails
epic criterion 15. The parser can always tell the two apart because
`legacy_prompt` records it, which is a second reason that field is not optional.

This is a wart with no expiry date, and it is written down in both directions so
nobody later "fixes" one half.

### The kinds

- **`blob:`** — the text, inline, used verbatim.
- **`file:`** — a node-relative path. **Node-local by declaration**: `file:` is a
  CLI/filesystem source kind and is deliberately not part of any abstract store
  contract, because a remote policy store can hold a named prompt resource but
  cannot honor an arbitrary local path. Validation resolves the path with
  symlinks followed (`Path.resolve()`) on **both** sides and requires the result
  to be inside the resolved node root — a symlink inside the root pointing out of
  it is rejected, which a lexical `..` check would miss. A non-existent path is a
  validation error too, so `tcw validate` catches a typo. At resolution time a
  file that has since disappeared, or that cannot be read, fails the command
  naming the path and the reason rather than raising a traceback.
- **`generate:`** — a shell command. Contract below.
- **`builtin: true`** — the value must be the literal boolean `true`; anything
  else is a validation error naming the key. It parses to `kind="builtin",
  value=""`, so `Binding.value` stays a `str` — the first draft's model would
  have stored YAML's `True` in a `str` field. In a `prompt` list it composes; in
  an `artifact` list, first-match-wins makes it a **fallback**, so it must be
  **last** and **unconditional**.
- **`skill:`** — resolves to the same sentence `_directive_text` renders today.
  Documented as the weakest kind: a name, not instructions.
- **`command:`** — check role, plus the legacy exception above.

### The `generate` contract

**stdin** is a JSON object:

```json
{
  "item": { "schema": 1, "...": "C2's DTO, unmodified in shape" },
  "hook": { "role": "prompt", "kind": "generate", "id": "spec",
            "phase": "prompt", "body_truncated": false }
}
```

**`body_truncated` lives in `hook`, not in `item`.** C2's `WORK_ITEM_SCHEMA` is
closed (`additionalProperties: false`), so a sibling key beside `body` would make
the document fail its own schema — the first draft put it there and would have
broken the contract C2 shipped. The item stays a valid DTO; only its `body` is
shorter.

**The body cap is 64 KiB of UTF-8 bytes, cut at a character boundary.** Slicing
64 KiB *characters* caps nothing on multi-byte text, and slicing bytes blindly
produces invalid UTF-8 that breaks the JSON the hook is about to parse. The
implementation encodes, slices, and drops any trailing partial sequence. This is
the debt the epic's amendment assigned to C3.

**Environment** — today's four `TCW_*` variables plus `TCW_HOOK_ROLE`,
`TCW_HOOK_KIND`, `TCW_HOOK_ID`, `TCW_HOOK_PHASE`, so a one-line script needs no
JSON parser.

**Execution** is `Popen`, not `subprocess.run(capture_output=True)`. That is a
requirement, not a preference: `run` buffers all output before returning, so an
output cap checked afterwards is a cap on the *result* and not on memory, and a
generator emitting unbounded output exhausts memory before any check fires. The
implementation:

- starts the child in its own process group, so a `shell=True` pipeline's
  children die with it;
- writes stdin and closes it, tolerating `BrokenPipeError` from a script that
  exits without reading — that is the script's business, not a crash;
- drains **stdout and stderr concurrently**, each bounded, because reading only
  stdout deadlocks when a chatty script fills the stderr pipe;
- kills the process group as soon as stdout exceeds the cap, and again on
  timeout, then reaps it.

**Output cap** — `work.lifecycle.output-cap`, default 64 KiB, counted in **raw
bytes** before decoding. One byte over fails the command with a message naming
the cap; exactly the cap succeeds.

**Timeout** — the existing `work.lifecycle.timeout`, covering stdin writing and
post-kill draining, not just the child's runtime.

**stderr** — capped at the same limit and forwarded to TCW's stderr, exactly as
`run_bindings` does for checks today. Not swallowed: a generator's diagnostics
are how its author debugs it.

**Encoding** — stdout decoded UTF-8 with `errors="replace"`. Failing on one bad
byte in an otherwise fine prompt trades a usable result for a purity nobody
asked for.

**Non-zero exit discards everything.** All captured stdout is dropped, the
command fails, and the exit code is named. Nothing partial reaches the resolved
text *or* TCW's stdout.

`generate` hooks must be **side-effect-free**: resolution can re-run, so a
generator that posts to an external system posts twice. Documented rather than
prevented — TCW does not sandbox, and a cached resolution bundle is state to
invalidate.

### Conditions

```yaml
when:
    tags: [bug, regression] # any of
    not_tags: [spike] # none of
    type: epic # validated; "" matches a non-epic
```

Keys are ANDed; a list value means any-of. `type` is compared exactly against
`item.type` and validated against the known set (`""` and `"epic"`), so a typo
fails at `tcw validate` rather than silently never matching.

**Value shapes are validated, not assumed.** `tags`/`not_tags` must be a list of
non-blank strings — a bare `tags: bug` is an error naming the list form, and
`tags: [1]` is an error naming the element. `type` must be a string. `when: null`
and `when: []` are errors. The first draft validated the `type` *value* and left
every other shape to crash at match time.

**Conditions apply in all three roles**, including checks. A `when:` on a
transition `pre` binding decides whether that check runs at all. The first draft
described conditions only for prompts and artifacts, which would have shipped a
key that silently did nothing in the third position.

**No item to match against** — resolution called without one — treats a
conditional binding as **not matching**, and an unconditional one as matching.
Stated so it is not discovered.

### Resolution, as a library

```python
def resolve_prompts(policy, stage_id, item, node_root, builtins, *,
                    execute=True) -> Resolution
def resolve_artifact(policy, artifact, item, node_root, builtins, *,
                     execute=True) -> Resolution
def select_checks(bindings, item) -> list[Binding]
```

in `tcw/work/resolve.py`. `Resolution` carries the text and the ordered plan —
every binding considered, whether it matched, and for `generate` the exact
command line.

**`execute=False` is the plan mode C4's `--no-exec` needs, and it runs nothing.**
It is the same traversal with one branch, so the plan cannot disagree with what
would really happen — deriving "what would run" from a `Resolution` produced by
actually running is not a dry run, it is a report. Under `execute=False` a
`generate` entry contributes no text and appears in the plan with its command;
`file` entries are not read either.

`select_checks` exists because C4 needs condition filtering for stage checks and
the existing transition path needs the same rule; one function so the two cannot
diverge.

**Two built-in registries, not one.** `builtins` is
`Builtins(stage_prompts: Mapping[str, str], artifact_templates: Mapping[str, str])`.
Stage ids and artifact names overlap — `spec` and `plan` are both — so a single
map cannot hold `spec`'s prompt and `spec`'s template at once. C6 fills
`stage_prompts`; C5 fills `artifact_templates`; C3 ships both empty.

**Prompt concatenation is exact**: each resolved text is stripped of trailing
whitespace and the results are joined with `"\n\n"`. "Concatenate" is not a
byte-level contract, and criterion 1 is a byte-level requirement.

**Resolution never writes.** Everything that writes is C5's — including the
draft artifact, which C5 should reach through a named store resource rather than
by composing `<artifact>.draft.md` onto a path.

### `--phase`

`--phase` accepts `pre`/`post` for a transition and `pre`/`prompt` for a stage.
`--phase post` on a stage is an **error naming the reason** — stages have no
`post` — rather than empty output, because silence reads as "nothing configured".
`--phase prompt` on a transition errors likewise.

### What `--json` emits, and why criterion 1 still holds

`tcw work lifecycle --json` currently emits, per stage,
`"bindings": {"bind": [{kind: ref}, …]}` (`cli.py:750`).

**`bind` keeps its exact meaning and content: the stage's prompt list.** New keys
appear only when the corresponding feature is configured — `pre` when a stage has
checks, `when` inside a binding that has a condition, `artifacts` and
`output-cap` at the top level when set. A legacy config configures none of them,
so its `--json` output is byte-identical, and so are its `--directive` and human
renderings.

This is the same superset discipline C2 applied to `serve`, and it is what makes
criterion 1's byte-identical promise honest rather than something achieved by
freezing a fixture while the public representation stops being able to describe
the model.

### Back-compat, every legacy row

| Legacy shape                                        | Today                                      | After                                    |
| --------------------------------------------------- | ------------------------------------------ | ---------------------------------------- |
| `stages.<id>: [{skill: X}]`                         | "invoke the X skill"                       | `prompt`, kind `skill`, same text        |
| `stages.<id>: [{command: C}]`                       | "run \`C\`" — **not executed**             | `prompt`, kind `command`, same text      |
| `stages.<id>: [{skill: A},{command: B},{skill: C}]` | **Grouped**: skills then commands          | Same grouped rendering                   |
| `stages.<id>: []`                                   | Renders nothing                            | Empty prompt list, unchanged             |
| `transitions.<id>.pre/post: [{command: C}]`         | Executed                                   | `check`, unchanged                       |
| `transitions.<id>.pre/post: [{skill: X}]`           | Reported to stderr, not run                | Unchanged                                |
| `transitions.<id>.pre/post: []`                     | Nothing runs                               | Unchanged                                |

`_directive_text` groups all skills ahead of all commands, so a mixed legacy list
does *not* render in declaration order today. Legacy lists keep the grouped
renderer; declaration-order concatenation applies to the explicit `prompt:` form.

**Duplicate detection moves to `(kind, value, when)`.** Today
`_parse_binding_list` rejects the same `ref` twice (`base.py:700`). With
conditions, the same script under two different conditions is the obvious way to
express "this prompt for bugs, that one for features", and rejecting it would
make the feature unusable. A legacy config has no conditions, so nothing it could
express changes meaning.

## Acceptance criteria

The initiative's criteria 1, 6, 7, 12, 13, and 15 are the requirement. Each of
these was written by asking what implementation could pass it while the property
is false.

1. **Legacy corpus, byte-identical, all three renderings.** One config per row of
   the back-compat table, plus this repository's own `tcw-config.yaml`, asserted
   against baselines **captured from the CLI before the parser is touched** and
   committed in their own commit. Full output, `--directive`, and `--json`.
   `test_declaration_order_is_significant_and_preserved` passes unmodified, and
   a populated `policy.stages` is read directly in at least one test so the
   attribute's new type is exercised rather than only its empty form.
2. **`generate` receives a schema-valid item.** Its stdin is parsed and the
   `item` object is validated against `WORK_ITEM_SCHEMA` — not merely checked for
   a slug — plus a `hook` object naming role, kind, id, phase, and
   `body_truncated`. Its stdout becomes the prompt.
3. **A non-zero exit contributes nothing**, asserted on the **resolved text** and
   on TCW's stdout, not only on the exit status: an implementation that returns
   the partial text and also fails would pass a status-only check.
4. **The cap bounds memory, not just the result.** A generator emitting
   unbounded output (`yes` piped to itself, or an infinite loop) fails with the
   cap message **and returns promptly** — asserted with a wall-clock bound and a
   timeout longer than that bound, so an implementation that buffers until the
   process ends fails the test instead of hanging it. One byte over the cap
   fails; exactly the cap succeeds. Bytes, not characters, proven with
   multi-byte output.
5. **A chatty stderr does not deadlock.** A generator writing more than a pipe
   buffer to stderr and a valid prompt to stdout resolves successfully. This is
   the failure a stdout-only drain produces and no other criterion would catch.
6. **The timeout fails rather than truncating**, and leaves no surviving child:
   a generator that spawns a long-lived grandchild is gone after the timeout.
7. **The body cap is bytes at a character boundary.** An item whose body is
   multi-byte and larger than the cap yields a `body` that is at most 64 KiB
   encoded, decodes cleanly, and comes with `hook.body_truncated == true`; a
   small body yields the whole thing and `false`. The `item` object still
   validates against `WORK_ITEM_SCHEMA` in both cases.
8. **The `when:` truth table, exhaustively, in all three roles**: each key alone;
   AND across keys; any-of; `not_tags`; `type: epic`, `type: ""`, and `""`
   matching a non-epic; overlapping; no match; and no item. Applied to a prompt,
   to an artifact, **and to a transition check** — a matcher unit-tested but
   never wired into checks is exactly the escape this clause closes.
9. **`tcw validate` rejects each of these, naming the offending key**: an unknown
   role key under a stage; `command` under an explicit `prompt:`; `command` under
   `artifacts`; `skill` under `artifacts`; an unknown `when:` key; a non-string
   `type`; an invalid `type` value; `tags` as a bare string; `tags` holding a
   non-string; `when: null`; a `builtin` value that is not `true`; a `file` path
   that does not exist; a `file` path escaping the node root **via a symlink**;
   `builtin` not last in an artifact list; a conditional `builtin` in an artifact
   list; and an artifact entry following an unconditional one. Each a separate
   assertion on the message.
10. **A bare legacy list still accepts `command`** while `prompt: [{command: C}]`
    is rejected — both asserted, in one test, so the exception cannot be
    "simplified" away in either direction.
11. **`tcw work lifecycle` still executes nothing.** A `generate` and a `command`
    binding writing sentinels, configured on **every** stage and transition id,
    leave no sentinel after `lifecycle` in all its forms — plain, `--stage`,
    `--transition`, `--directive`, `--json`, and `--phase`. The sentinel path is
    absolute so the assertion cannot be defeated by the child's cwd.
12. **`--phase`** filters as specified, and both illegal combinations error with
    a message naming the reason.
13. **`execute=False` runs nothing and still plans.** With a `generate` binding
    writing a sentinel, plan mode produces no sentinel, no text from that entry,
    and a plan naming the command. `file` entries are not read either, proven
    with a file whose read would be observable.
14. **First-match-wins for artifacts, all-match-concatenates for prompts**, each
    with a matching and a non-matching conditional binding — and for artifacts, a
    `generate` entry **after** the first match must not execute, asserted by
    sentinel.
15. **Concatenation is exact**: two blobs with trailing whitespace resolve to
    a specific literal string, joined by exactly one blank line.
16. **`builtin` with empty registries resolves to nothing and is not an error**,
    including a prompt list containing only `{builtin: true}`, which resolves to
    the empty string.
17. **Duplicate detection is by `(kind, value, when)`**: the same script twice
    under different conditions parses; twice under identical conditions is
    rejected.
18. **A `generate` script that exits without reading stdin** resolves or fails on
    its own exit code, and never on a `BrokenPipeError` traceback.

## Risks

- **This rewrites the path every existing config takes.** Mitigated by criterion
  1's captured baselines, by C3 adding no new verb, and by including this
  repository's own config in the corpus.
- **The `command`-in-prompt exception is permanent.** One key accepts a kind
  another rejects, forever, because the legacy shape cannot be renamed. Criterion
  10 pins both halves so neither gets tidied away.
- **`Popen` with concurrent draining and process-group kill is the most
  error-prone code in this slice**, and its failure modes — deadlock, orphaned
  children, unbounded memory — are ones a naive test does not catch. Criteria 4,
  5, and 6 exist specifically for them.
- **`generate` widens the blast radius of a hostile config.** Unchanged in
  principle; the frequency rises once agents run stage entry routinely.
  `--no-exec` and criterion 11 are the mitigations; consent prompts are not, per
  the initiative's decision.
- **The hook's item differs from the API's by one capped field.**
  `hook.body_truncated` makes that detectable rather than silent. An unbounded
  body on a pipe is what the epic's amendment rejected.
- **`builtin` resolving to nothing is indistinguishable from "not configured"**
  until C5 and C6 land. Accepted for that window; criterion 16 pins it as
  intended rather than accidental. (Review suggested this hides a misspelled
  registry key — it cannot: `builtin: true` has no key to misspell, and the stage
  or artifact name it looks up is already validated against the registry.)

## Review corrections

Both reviews ran against the first draft, before implementation. Findings were
checked against the code before being accepted.

**Accepted and folded in:**

- The `check` role's legal kinds contradicted the epic's own back-compat table
  (codex). Verified at epic `spec.md:301` versus `:339`. The **epic** is amended,
  not worked around.
- `legacy_prompt` provenance was promised in prose and absent from the model
  (both reviews). Now a field, with the reasons it must survive rendering,
  `--json`, and equality.
- `body_truncated` beside `body` would fail C2's closed schema (codex). Verified
  at `projection.py:102`. Moved into the `hook` envelope.
- The body cap must be **bytes at a character boundary** (both). Slicing
  characters caps nothing; slicing bytes blindly breaks the JSON.
- `subprocess.run(capture_output=True)` cannot bound memory (codex). Verified at
  `hooks.py:59`. `Popen`, concurrent drains, process-group kill — and criterion 4
  rewritten so a buffer-then-check implementation fails it.
- stderr was undefined and a stdout-only drain deadlocks (both). Capped,
  forwarded, and criterion 5 added.
- One `builtins` map cannot hold both a `spec` prompt and a `spec` template
  (codex). Split into two registries with an owner each.
- `--json`'s payload had to change and criterion 1 did not say how (codex). `bind`
  keeps its meaning; new keys appear only when configured.
- Conditions were specified for prompts and artifacts but not checks (codex).
  Now all three, with `select_checks` shared, and criterion 8 asserts the third.
- `execute=False` cannot be derived from a post-hoc `Resolution` (codex). It is a
  parameter of the same traversal, with criterion 13.
- Duplicate detection by `ref` alone makes conditional bindings unusable (codex).
  Verified at `base.py:700`. Now `(kind, value, when)`.
- Condition value shapes were unvalidated (bllm) — `tags: bug`, `tags: [1]`,
  `when: null`, non-string `type` all now rejected by name.
- `builtin: true` is a YAML boolean and would not fit `Binding.value: str`
  (bllm). It parses to `value=""`.
- Symlink escape defeats a lexical confinement check (both). Both sides resolved.
- `BrokenPipeError`, `PermissionError`, and a file vanishing after validation
  were undefined (bllm). Each named, with criterion 18 for the first.
- Prompt "concatenation" was not a byte-level contract (codex). Specified, with
  criterion 15.
- Claiming `.stages`' type change preserved "every caller" was too broad (codex).
  Restated precisely, and criterion 1 now reads a populated `.stages`.

**Rejected:**

- *An empty built-in registry hides a misspelled key* (codex). There is no key to
  misspell; the lookup name is a validated stage or artifact id.
- *Artifact reachability validation should catch logically exhaustive earlier
  conditions* — e.g. `type: epic` then `type: ""` (codex). The property is
  restated honestly as syntactically obvious unconditional shadowing rather than
  the criterion being widened. Exhaustiveness analysis over a three-key condition
  language is a solver, and the initiative's spec rejects growing this into a
  config language.
- *A read-only filesystem or `--dry-run` flag for `generate`* (bllm). Sandboxing
  is an explicit non-goal of the initiative; `--no-exec` is the answer and it is
  C4's.
- *Test that a hook reads `body_truncated` and adjusts its output* (bllm). That
  tests the fixture script, not TCW.
