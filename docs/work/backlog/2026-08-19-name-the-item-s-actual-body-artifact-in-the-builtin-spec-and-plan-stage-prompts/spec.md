# Spec: name the item's actual body artifact in the stage prompts

## Capability changes

Planned ledger deltas only; nothing is written at this stage.

| Capability                     | Delta                                                                                                                                                                                                    |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `work/run-a-lifecycle-stage`   | **Wording.** Add a paragraph stating that a stage's prompt names the item's own body artifact — the request when the `request` stage has written one, the raw intake otherwise — rather than a fixed filename. Status stays `Supported`; this is a refinement of behavior the capability already claims. |

No new capability, no status change, no taxonomy change. The `## References`
degradation and the skills sweep are internal correctness, not new user-facing
verbs.

## Problem

`tcw work stage spec <slug>` and `tcw work stage plan <slug>` open by naming
`initial-request.md` as their input, unconditionally:

- `tcw/work/prompts/spec.md:6` — "**Inputs.** `initial-request.md` and its
  `## References` …"
- `tcw/work/prompts/plan.md:6` — "**Inputs.** `initial-request.md` and
  `spec.md`."

On 1.0.0 that file is frequently absent. `create_work` writes
`initial-request.md` only when a `body` was supplied and `intake.md` only when
raw input was (`tcw/store/fs.py:3350-3355`), and `tcw work new` routes piped
stdin to `intake`, not to `body` (`tcw/work/cli.py:223`). An item created from a
pipe or from `tcw work inbox accept` therefore carries `intake.md` alone.

Two consequences, both load-bearing:

1. The prompt names a file that does not exist, and names no other. The stage
   prompt is the only place the agent is told what to read, so it is not
   cosmetic.
2. The `spec` prompt's `## References` rule is wrong in the same breath. It
   says that with neither a `## References` section nor an "asked; none
   provided" note, "nobody asked". On an intake-only item neither can exist *by
   construction* — the `request` stage never ran — so the prompt asserts a
   conclusion about the requester from the absence of a stage.

The read-resolution rule the prompt should be following already exists and is
already documented: `_BODY_ORDER = ("initial-request", "intake")`
(`tcw/store/fs.py:536`), used by `_resolve_body` (`tcw/store/fs.py:2254-2264`),
which is what `tcw work show` and the `R`/`i` board letters report. The
`spec`/`plan` prompts are the only readers of the item body that do not follow
it.

`tcw work stage` already has the data needed to follow it: it passes
`artifacts=st.artifacts(bare)` into `resolve_prompts`
(`tcw/work/cli.py:797-802`), where it currently feeds only the `generate` hook
payload.

### Sibling defects — repo-wide sweep

The sweep was repo-wide (`tcw/`, `skills/`, `commands/`, `agents/`, `docs/`,
`README.md`). Every occurrence of `initial-request` was classified; these carry
the same assumption:

| # | Location                                          | Defect                                                                                       |
| - | ------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 1 | `tcw/work/prompts/spec.md:6`                      | Names `initial-request.md` only; `## References` rule wrong on intake-only. **Primary.**      |
| 2 | `tcw/work/prompts/plan.md:6`                      | Names `initial-request.md` only. **Primary.**                                                 |
| 3 | `tcw/work/prompts/postmortem.md:6-8`              | The spine "read backwards" ends at `initial-request.md`; `intake.md` — the actual earliest artifact on an intake-only item — is not in it. |
| 4 | `tcw/store/base.py:726,731,748`                   | `LIFECYCLE_STEPS` `inputs` for `spec`, `plan`, `postmortem` list `initial-request.md` and not `intake.md`. Its own docstring (`tcw/store/base.py:687-693`) says the stage documents must agree with it; after 1–3 they would not. Rendered by `tcw work lifecycle` (`tcw/work/cli.py:664-665`) and shipped in `--json` (`tcw/work/cli.py:1034`). |
| 5 | `skills/tcw-work/references/stage-spec.md:8-10`   | `## Inputs` says `initial-request.md`.                                                        |
| 6 | `skills/tcw-work/references/stage-plan.md:8-10`   | `## Inputs` says `initial-request.md`, `spec.md`.                                             |
| 7 | `skills/tcw-work/references/stage-postmortem.md:8-11` | Spine list omits `intake.md`.                                                             |
| 8 | `skills/tcw-triage-issues/SKILL.md:130-165`       | §5 tells the triager to write `initial-request.md` at acceptance and *then* run the `request` stage over it. Backwards on 1.0.0: acceptance produces `intake.md`, and `request` is what turns it into `initial-request.md`. Following it produces an item that displays `R` without the `request` stage having run — exactly what 1.0.0's creation change removed. |
| 9 | `skills/tcw-triage-issues/SKILL.md:213-214`       | "read `initial-request.md`'s `## Origin`" — on a correctly filed item the `## Origin` is in `intake.md`. |
| 10 | `skills/tcw-work/references/transitions.md:98-99` | Same `## Origin` lookup, same defect.                                                        |
| 11 | `agents/tcw-post-mortem.md:17-19`                 | Spine list omits `intake.md`.                                                                |
| 12 | `agents/tcw-backlog-auditor.md:19-21`             | "whichever exist" list omits `intake.md`, so an intake-only item reads as having no body.     |
| 13 | `commands/tcw-process-inbox.md:13-15`             | "shape each new item's `initial-request.md` into an actual request" — after `inbox accept` the item has `intake.md`; `initial-request.md` is the output, not the input. |

Classified as **not** defects, deliberately: `skills/tcw-work/SKILL.md:30,43`
(the "no `initial-request.md` → `request`" rule is correct under 1.0.0);
`skills/tcw-work/references/commands.md:41-46,73-77` (already states the body
surface and the write rule correctly — it is the wording the fix aligns to);
`README.md:933-955`; `skills/tcw-work/references/stage-request.md`,
`epic-deltas.md`, `decompose.md`, `audit-backlog.md` (all name
`initial-request.md` as the `request` stage's own output, which is right).

`skills/tcw-work/references/consolidate-plans.md:54` is a **judgment call left
alone**: it writes `initial-request.md` directly from a migrated planning
document. That source is an authored planning artifact, not raw arrival, so
writing the request rather than an intake is defensible, and the same step
already fast-forwards `spec.md`/`plan.md` on the same reasoning. Recorded here
so the omission is a decision rather than a miss.

## Goals

1. The `spec` and `plan` prompts name the body artifact the item actually has,
   resolved by the same rule `tcw work show` uses.
2. The `spec` prompt's `## References` instruction degrades correctly on an
   intake-only item: no false "nobody asked" conclusion.
3. The prompts stay honest when neither artifact is present.
4. The `postmortem` spine and the `LIFECYCLE_STEPS` `inputs` agree with 1 and 2.
5. Rows 5–13 of the sweep table are corrected in the shipped plugin.
6. The resolution rule is stated once, in the storage-abstract layer, so the
   filesystem adapter and the prompt resolver cannot disagree about it.

## Non-goals

- **Changing item creation.** 1.0.0's decision not to write an unconditional
  `initial-request.md` stands.
- **A general conditional/templating language for prompts.** One resolved value
  substituted into a span, matching the shape already shipped for
  `{{tcw:documentation}}`. No `if`/`else`, no loops, no expressions.
- **Adding `body-surface` or `intake` to the taxonomy.** The concept is real and
  currently unregistered, but registering vocabulary is not this bug's job.
  Noted for the backlog.
- **`consolidate-plans.md`** — see the classification above.
- **`tcw serve`.** It resolves no stage prompts; nothing there reads this text.

## Design

### 1. One statement of the body-resolution order (`tcw/store/base.py`)

Promote `_BODY_ORDER` out of the filesystem adapter:

```python
# The read-resolution order for an item's body surface: the written-up request
# wins when present, the raw intake is the fallback. Abstract because every
# adapter answers "what is this item's body?" and must answer it the same way.
BODY_ORDER = ("initial-request", "intake")
```

`tcw/store/fs.py` imports it and drops its private copy;
`fs._resolve_body` is otherwise unchanged.

**Litmus test.** *Could a non-filesystem store implement this?* Yes — it is an
ordering over two names in the existing `WORK_ARTIFACTS` set, applied to the
`Artifact.present` map every adapter must already produce
(`tcw/store/base.py:1409-1421`). No path, no file, no `stat`.

### 2. A `{{tcw:body}}` span (`tcw/work/resolve.py`)

Generalize the existing span machinery rather than adding a second mechanism.
`substitute_documentation` (`tcw/work/resolve.py:236-287`) already implements
*replace the span, or fall back to its own inner text*, including the
indentation and trailing-space handling. The body span reuses that walk:

- Token pair: `{{tcw:body}}` … `{{/tcw:body}}`.
- Resolved value: the **first name in `BODY_ORDER` whose `Artifact.present` is
  true**, rendered as its artifact label — `` `initial-request.md` `` or
  `` `intake.md` ``.
- With neither present, the span becomes its own inner text, unchanged —
  byte-identical to today's behavior by construction, exactly as the
  documentation span is defined.
- An unterminated open token is left verbatim, same as today.

The shared walk is factored to take (open token, close token, replacement-or-
`None`); `substitute_documentation` and `substitute_body` both call it, so the
indentation and blank-line rules cannot drift apart. Substitution happens in
`resolve_prompts` over the joined text (`tcw/work/resolve.py:338`), beside the
documentation call and for the same reason stated there — a project's own
`file:`/`blob:` prompt can use the token too.

`resolve_prompts` already receives `artifacts`; no signature change.

### 3. Prompt rewrites

`tcw/work/prompts/spec.md` — the `**Inputs.**` paragraph becomes:

> **Inputs.** {{tcw:body}}the item's body artifact{{/tcw:body}}. On an
> `initial-request.md`, `## References` is the starting set for research, not
> the limit of it; with neither that section nor an "asked; none provided" note
> in `## Notes`, nobody asked — research from scratch rather than reading
> silence as "there was nothing to point at". On an `intake.md` the `request`
> stage has not run, so there is no such section and no conclusion to draw from
> its absence: the intake is the request, read as filed. Repository discovery is
> unrestricted; a spec written without reading the code it changes is a guess.

`tcw/work/prompts/plan.md` — `**Inputs.** {{tcw:body}}the item's body
artifact{{/tcw:body}} and `spec.md`. Repository discovery is unrestricted.`

`tcw/work/prompts/postmortem.md` — the spine gains its earliest element:
"… `spec.md`, then the body the item started from — `initial-request.md`, or
the `intake.md` beneath it when the `request` stage never ran."

Exact wording is the implementer's, subject to the acceptance criteria below.
The 50-line ceiling (`tests/test_shipped_prompts.py:39-50`) is a hard
constraint: `spec.md` is at 48 lines today, so the rewrite must not add net
lines — which is the reason for a substituted value rather than spelled-out
branches.

### 4. `LIFECYCLE_STEPS` inputs (`tcw/store/base.py`)

`spec`, `plan`, and `postmortem` gain `intake.md` in `inputs`. This changes
byte-exact output of `tcw work lifecycle` and its `--json`, so the fixtures in
`tests/fixtures/lifecycle_baseline/` are **regenerated deliberately**, by re-running the
corpus capture script the fixtures were made with,
`python tests/fixtures/lifecycle_baseline/capture.py <outdir>`
(`tests/fixtures/lifecycle_baseline/capture.py:1-11`). The
baseline exists to catch accidental drift; this is an intended model change, and
the regenerated fixture is reviewed as part of the diff rather than accepted
blind.

### 5. Skills, commands, and agents (rows 5–13)

Text-only. The shipped plugin has no substitution engine, so each states the
rule in prose and points at
`skills/tcw-work/references/commands.md` "The body surface", which already
carries it. Row 8 is the substantive one: §5 of `tcw-triage-issues` is rewritten
so acceptance files the reporter's words as **`intake.md`** (which is what
`tcw work inbox accept` and a piped `tcw work new` already do) and the
`request` stage is what turns it into `initial-request.md`. Rows 9–10 look the
`## Origin` up on the item's body rather than on a fixed filename.

## Acceptance criteria

1. On an item with `intake.md` and no `initial-request.md`,
   `tcw work stage spec <slug>` prints `intake.md` and does **not** print
   `initial-request.md` in its `**Inputs.**` paragraph. Checkable today against
   this very item's sibling `2026-08-19-derive-an-accepted-inbox-item-s-title-…`.
2. On an item that has `initial-request.md`, `tcw work stage spec <slug>` prints
   `initial-request.md` in that paragraph — and prints it whether or not
   `intake.md` also exists.
3. Same two checks for `tcw work stage plan <slug>`.
4. On an item with neither artifact, `tcw work stage spec <slug>` exits 0 and
   prints the span's fallback text, naming neither filename as though it
   existed.
5. `tcw work stage spec <slug>` on an intake-only item contains no sentence
   that concludes "nobody asked" from a missing `## References` section.
6. Every prompt in `tcw/work/prompts/` is ≤ 50 lines — i.e.
   `tests/test_shipped_prompts.py` passes unchanged, with no ceiling raise.
7. No `{{tcw:` token survives into any resolved prompt: for each of the six
   stages, `tcw work stage <id> <slug>` output contains neither `{{tcw:` nor
   `{{/tcw:`.
8. `tcw work lifecycle --stage spec`, `--stage plan`, and `--stage postmortem`
   each list `intake.md` among `inputs`, and `tests/test_lifecycle_baseline.py`
   passes against regenerated fixtures.
9. `grep -rn "initial-request" skills/ commands/ agents/` reports no occurrence
   that presents `initial-request.md` as an artifact guaranteed to exist, as the
   raw arrival, or as the `inbox`/triage stage's own output. Rows 5–13 are each
   individually resolved or explicitly re-classified in `outcome.md`.
10. `pytest` passes, and `tcw validate` passes on this node.
11. `tcw capabilities show work/run-a-lifecycle-stage` states the body-artifact
    naming behavior.

## Risks

- **The 50-line prompt ceiling.** `spec.md` has two lines of headroom. If the
  rewrite cannot fit, the correct move is to cut an existing clause, not to
  raise the ceiling — the ceiling is deliberate
  (`tests/test_shipped_prompts.py:40-49`). *Mitigation:* the design substitutes
  one value instead of spelling out both branches, which is net-neutral or
  shorter.
- **Baseline churn.** Regenerating `tests/fixtures/lifecycle_baseline/` touches
  large JSON blobs, where an unintended change hides easily. *Mitigation:* the
  regenerated diff is inspected for `inputs` lines only; any other delta stops
  the task.
- **Two substitution call sites in one function.** Order matters if a
  documentation span ever nested inside a body span. *Mitigation:* neither
  built-in prompt nests them, and the shared walk leaves an unrecognized token
  verbatim rather than consuming it.
- **A project with its own `spec` prompt** keeps its own wording and is
  unaffected — correct, but it also means this fix does not reach a node that
  replaced the builtin. Nothing to do; noted so it is not mistaken for coverage.
- **Row 8's rewrite changes a documented workflow** that produced this repo's
  four most recent items. Existing items are not retrofitted; only the
  instruction changes.

## Notes

- The prompts name artifacts by their `.md` label (`initial-request.md`) rather
  than by the abstract name (`initial-request`). That convention is already
  established by `LifecycleStep.produces_note` and by every existing prompt, so
  it introduces no new filesystem coupling; a remote adapter renders the same
  labels.
- Requester's suggested remediation — "resolve the body artifact the way
  `tcw work show` does and name what it found" — is adopted, and the design
  reaches it by reusing the shipped span mechanism rather than adding one.
- Assumption, not verified against every adapter: `Artifact.present` is
  populated for `intake` by adapters other than the filesystem one. The
  filesystem adapter does (`WORK_ARTIFACTS` includes `intake`,
  `tcw/store/base.py:1214`); there is no second adapter in-tree to check
  against.
- The taxonomy has no term for the body surface or for intake
  (`tcw taxonomy list`). A real gap, deliberately not filled here.
