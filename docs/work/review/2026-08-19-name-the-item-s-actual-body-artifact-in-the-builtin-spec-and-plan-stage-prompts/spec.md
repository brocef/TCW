# Spec: name the item's actual body artifact in the stage prompts

## Capability changes

Planned ledger deltas only; nothing is written at this stage. All three are
**wording**; no status changes, no new capability, no taxonomy change.

| Capability                        | Delta                                                                                                                                                                                          |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `work/run-a-lifecycle-stage`      | State that a stage's prompt names the item's own body artifact — the request when the `request` stage has written one, the raw intake otherwise — rather than a fixed filename.                   |
| `plugin/triage-github-issues`     | The description claims an accepted issue's **`initial-request.md`** records the issue number, URL, and the reporter's words (`docs/capabilities/plugin/triage-github-issues/description.md:2`). Acceptance writes **`intake.md`** (`tcw/store/fs.py:3029-3047`). Correct the artifact named. |
| `work/complete-a-work-item`       | The description sends closeout to `initial-request.md` for the `## Origin` (`docs/capabilities/work/complete-a-work-item/description.md:20`). On an item filed correctly the `## Origin` is in `intake.md`. Point at the item's body rather than a fixed filename. |

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
stdin to `intake`, not to `body` (`tcw/work/cli.py:223`). `tcw work inbox accept`
likewise files the entry as `intake.md` (`tcw/store/fs.py:3029-3047`). An item
created either way carries `intake.md` alone.

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

The sweep covered `tcw/`, `skills/`, `commands/`, `agents/`, `docs/`, and
`README.md`; every occurrence of `initial-request` was classified. Rows 14–17
were added after review — see `## Notes`.

| #  | Location                                             | Defect                                                                                       |
| -- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 1  | `tcw/work/prompts/spec.md:6`                         | Names `initial-request.md` only; `## References` rule wrong on intake-only. **Primary.**      |
| 2  | `tcw/work/prompts/plan.md:6`                         | Names `initial-request.md` only. **Primary.**                                                 |
| 3  | `tcw/work/prompts/postmortem.md:6-8`                 | The spine "read backwards" ends at `initial-request.md`; `intake.md` — the actual earliest artifact on an intake-only item — is not in it. |
| 4  | `tcw/store/base.py:726,731,748`                      | `LIFECYCLE_STEPS` `inputs` for `spec`, `plan`, `postmortem` list `initial-request.md` and not `intake.md`. Its own docstring (`tcw/store/base.py:687-693`) says the stage documents must agree with it; after 1–3 they would not. Rendered by `tcw work lifecycle` (`tcw/work/cli.py:664-665`) and shipped in `--json` (`tcw/work/cli.py:1034`). |
| 5  | `skills/tcw-work/references/stage-spec.md:8-10`      | `## Inputs` says `initial-request.md`.                                                        |
| 6  | `skills/tcw-work/references/stage-plan.md:8-10`      | `## Inputs` says `initial-request.md`, `spec.md`.                                             |
| 7  | `skills/tcw-work/references/stage-postmortem.md:8-11` | Spine list omits `intake.md`.                                                                |
| 8  | `skills/tcw-triage-issues/SKILL.md:130-165`          | §5 tells the triager to write `initial-request.md` at acceptance and *then* run the `request` stage over it. Backwards on 1.0.0: acceptance produces `intake.md`, and `request` is what turns it into `initial-request.md`. Following it produces an item that displays `R` without the `request` stage having run — exactly what 1.0.0's creation change removed. |
| 9  | `skills/tcw-triage-issues/SKILL.md:213-214`          | "read `initial-request.md`'s `## Origin`" — on a correctly filed item the `## Origin` is in `intake.md`. |
| 10 | `skills/tcw-work/references/transitions.md:98-99`    | Same `## Origin` lookup, same defect.                                                         |
| 11 | `agents/tcw-post-mortem.md:17-19`                    | Spine list omits `intake.md`.                                                                 |
| 12 | `agents/tcw-backlog-auditor.md:19-21`                | "whichever exist" list omits `intake.md`, so an intake-only item reads as having no body.      |
| 13 | `commands/tcw-process-inbox.md:13-15`                | "shape each new item's `initial-request.md` into an actual request" — after `inbox accept` the item has `intake.md`; `initial-request.md` is the output, not the input. |
| 14 | `skills/tcw-post-mortem/SKILL.md:19-21`              | The canonical spine, of which row 11 is only the agent mirror. Same omission; fixing the mirror alone leaves the cross-harness procedure inconsistent. |
| 15 | `skills/tcw-work/references/audit-backlog.md:8-9`    | The canonical artifact list, of which row 12 is the agent mirror. Same omission.               |
| 16 | `docs/capabilities/plugin/triage-github-issues/description.md:2` | A standing capability claim that acceptance writes `initial-request.md`. It writes `intake.md`. |
| 17 | `docs/capabilities/work/complete-a-work-item/description.md:20`  | A standing capability claim that closeout finds `## Origin` in `initial-request.md`.            |

Classified as **not** defects, deliberately:

- `skills/tcw-work/SKILL.md:30,43` — "no `initial-request.md` → `request`" is
  correct under 1.0.0.
- `skills/tcw-work/references/commands.md:41-46,73-77` — already states the body
  surface and the write rule correctly. This is the wording rows 5–17 align to.
- `README.md:933-955`; `skills/tcw-work/references/stage-request.md`,
  `epic-deltas.md`, `decompose.md` — each names `initial-request.md` as the
  `request` stage's own output, which is right.
- `docs/capabilities/work/reconcile-an-epic-rollup/description.md:9` — a
  statement about what an *older release* wrote. Historical, and true.
- `docs/capabilities/work/retitle-a-work-item/description.md:4` — "the H1 of
  `initial-request.md` is left alone" is narrow in the same way, but it is the
  subject of a separate backlog item,
  `2026-08-19-derive-an-accepted-inbox-item-s-title-from-the-entry-s-h1-and-strip-the-date-prefix`.
  Left to its owner rather than fixed twice.
- `skills/tcw-work/references/consolidate-plans.md:54` — writes
  `initial-request.md` directly from a migrated planning document. That source
  is an authored planning artifact, not raw arrival, so writing the request
  rather than an intake is defensible, and the same step already fast-forwards
  `spec.md`/`plan.md` on the same reasoning. Recorded so the omission is a
  decision rather than a miss.

## Goals

1. The `spec` and `plan` prompts name the body artifact the item actually has,
   resolved by the same rule `tcw work show` uses.
2. The `spec` prompt's `## References` instruction degrades correctly on an
   intake-only item: no false "nobody asked" conclusion, and a positive
   instruction about what to read instead.
3. The prompts stay honest when neither artifact is present.
4. The `postmortem` spine and the `LIFECYCLE_STEPS` `inputs` agree with 1–3.
5. Rows 5–17 of the sweep table are corrected.
6. The resolution rule is stated once, in the storage-abstract layer, so the
   filesystem adapter and the prompt resolver cannot disagree about it.
7. `{{tcw:documentation}}` rendering is byte-identical before and after.

## Non-goals

- **Changing item creation.** 1.0.0's decision not to write an unconditional
  `initial-request.md` stands.
- **A general conditional/templating language for prompts.** One resolved value
  substituted into a span. No `if`/`else`, no loops, no expressions, no nesting.
- **Adding `body-surface` or `intake` to the taxonomy.** The concept is real and
  currently unregistered, but registering vocabulary is not this bug's job.
- **`consolidate-plans.md` and `retitle-a-work-item`** — see the classification
  above.
- **`tcw serve`.** It resolves no stage prompts; nothing there reads this text.
- **Retrofitting existing items.** Only the instructions change.

## Design

### 1. One statement of the body-resolution order (`tcw/store/base.py`)

Promote `_BODY_ORDER` out of the filesystem adapter:

```python
# The read-resolution order for an item's body surface: the written-up request
# wins when present, the raw intake is the fallback. Abstract because every
# adapter answers "what is this item's body?" and must answer it the same way.
BODY_ORDER = ("initial-request", "intake")
```

`tcw/store/fs.py` imports it and drops its private copy; `fs._resolve_body` is
otherwise unchanged.

**Litmus test.** *Could a non-filesystem store implement this?* Yes — it is an
ordering over two names in the existing `WORK_ARTIFACTS` set
(`tcw/store/base.py:1214`), applied to the `list[Artifact]` that
`WorkStore.artifacts` requires every adapter to return
(`tcw/store/base.py:1409-1421`), each carrying `name` and `present`
(`tcw/store/base.py:1297-1301`). No path, no file, no `stat`.

### 2. A `{{tcw:body}}` span (`tcw/work/resolve.py`)

**Inline substitution, deliberately *not* the documentation walk.**
`substitute_documentation` (`tcw/work/resolve.py:236-287`) is a *block*
replacement: on a match it always appends `"\n" + indent` after the rendered
text and conditionally eats a following space
(`tcw/work/resolve.py:271-283`), because what it substitutes is a multi-line
bullet list that must not run into the prose after it. Reusing that walk for a
one-token inline value would render

```markdown
**Inputs.** `intake.md`
. On an ...
```

so the body span gets its own replacement policy: the span, open token through
close token, is replaced by the resolved value **in place**, with no inserted
newline, no indent, and no following-space adjustment.

- Token pair: `{{tcw:body}}` … `{{/tcw:body}}`.
- Resolved value: the first name in `BODY_ORDER` whose `Artifact.present` is
  true, rendered as `` `<name>.md` `` — `` `initial-request.md` `` or
  `` `intake.md` ``.
- With neither present, the span becomes its own inner text, unchanged.
- An unterminated open token is left **verbatim**, matching
  `substitute_documentation` and the behavior pinned at
  `tests/test_documentation_prompt.py:77`.
- **Nesting is unsupported.** The two token pairs are substituted
  independently, documentation first; a prompt that nests one inside the other
  is user error and is not given defined behavior.

Shared code is limited to what is genuinely identical — locating an
open/close pair and computing the fallback slice. The replacement policy stays
per-token. If factoring that out cannot be done without changing
`substitute_documentation`'s output, it is not factored out: goal 7 wins over
tidiness, and two twelve-line loops are cheaper than a regression in shipped
prompt rendering.

Substitution happens in `resolve_prompts` over the joined text
(`tcw/work/resolve.py:338`), beside the documentation call and for the same
reason stated there — a project's own `file:`/`blob:` prompt can use the token
too. `resolve_prompts` already receives `artifacts`; no signature change.

### 3. Prompt rewrites

`tcw/work/prompts/spec.md` — the `**Inputs.**` paragraph becomes, in substance:

> **Inputs.** {{tcw:body}}the item's body artifact{{/tcw:body}}. On an
> `initial-request.md`, `## References` is the starting set for research, not
> the limit of it; with neither that section nor an "asked; none provided" note
> in `## Notes`, nobody asked — research from scratch rather than reading
> silence as "there was nothing to point at". On an `intake.md` the `request`
> stage has not run, so there is no such section and no conclusion to draw from
> its absence: read the intake as the request, as filed. Repository discovery is
> unrestricted; a spec written without reading the code it changes is a guess.

`tcw/work/prompts/plan.md` — `**Inputs.** {{tcw:body}}the item's body
artifact{{/tcw:body}} and `spec.md`. Repository discovery is unrestricted.`

`tcw/work/prompts/postmortem.md` — the spine gains its earliest element: after
`spec.md`, "the body the item started from — `initial-request.md`, or the
`intake.md` beneath it when the `request` stage never ran."

Exact wording is the implementer's, subject to the acceptance criteria. The
50-line ceiling (`tests/test_shipped_prompts.py:39-50`) is a hard constraint:
`spec.md` is at 48 lines today, so the rewrite must not add net lines — which is
the reason for a substituted value rather than spelled-out branches. If it will
not fit, cut an existing clause; do **not** raise the ceiling.

Naming an artifact as `` `<name>.md` `` is a rendering convention introduced by
the resolver, not a field on `Artifact`. It matches what every existing prompt
and `LifecycleStep.produces_note` already do.

### 4. `LIFECYCLE_STEPS` inputs (`tcw/store/base.py`)

`spec`, `plan`, and `postmortem` gain `intake.md` in `inputs`.

**The interpretation, stated so the implementer is not blocked on it:** `inputs`
is the set of artifacts a stage **may** read — a superset, not a checklist. The
resolved prompt naming exactly one of `initial-request.md` / `intake.md` agrees
with an `inputs` list containing both. This is already how `implement` reads
(`rework.md` is listed and is usually absent).

This changes byte-exact output of `tcw work lifecycle` and its `--json`, so the
fixtures in `tests/fixtures/lifecycle_baseline/` are **regenerated
deliberately**, with `python tests/fixtures/lifecycle_baseline/capture.py
<outdir>` (`tests/fixtures/lifecycle_baseline/capture.py:1-11`). The baseline
exists to catch accidental drift; this is an intended model change, and the
regenerated diff is reviewed as part of the change rather than accepted blind.
No in-tree code consumes `inputs` beyond the renderer and the `--json`
serializer — checked by grep across `tcw/`, `tests/`, `scripts/` — so nothing
else breaks on the extra element.

### 5. Skills, commands, agents, and capability descriptions (rows 5–17)

Text-only. The shipped plugin has no substitution engine, so each states the
rule in prose and points at `skills/tcw-work/references/commands.md` "The body
surface", which already carries it.

Row 8 is the substantive one: §5 of `tcw-triage-issues` is rewritten so
acceptance files the reporter's words as **`intake.md`** — which is what
`tcw work inbox accept` and a piped `tcw work new` already do — and the
`request` stage is what turns it into `initial-request.md`. Rows 9, 10, and 17
look the `## Origin` up on the item's body rather than on a fixed filename.
Rows 14–15 are corrected together with their agent mirrors (11–12) so the
canonical procedure and its accelerator cannot disagree.

## Acceptance criteria

Criteria 1–8 are **automated tests added by this change**, not manual checks;
9–11 are review gates run at `implement`.

1. `substitute_body` unit tests: with both artifacts present it yields
   `` `initial-request.md` ``; with only `intake` present, `` `intake.md` ``;
   with neither, the span's inner text verbatim; with an unterminated open
   token, the input verbatim.
2. Inline placement: substituting a span embedded mid-sentence
   (`**Inputs.** {{tcw:body}}x{{/tcw:body}}. On an …`) inserts no newline and
   no indent — the rendered line reads `` **Inputs.** `intake.md`. On an … ``.
3. `substitute_documentation`'s output is byte-identical to its pre-change
   output for every span shape already pinned in
   `tests/test_documentation_prompt.py`, which passes unmodified.
4. End-to-end, on an item with `intake.md` and no `initial-request.md`:
   `tcw work stage spec <slug>` and `tcw work stage plan <slug>` each print
   `intake.md` in the `**Inputs.**` paragraph and do not print
   `initial-request.md` there. Checkable today against the sibling item
   `2026-08-19-derive-an-accepted-inbox-item-s-title-…`, which is intake-only.
5. End-to-end, on an item with `initial-request.md`: both stages print
   `initial-request.md` there, whether or not `intake.md` also exists.
6. End-to-end, on an item with neither — constructible with
   `tcw work new "<title>"` and nothing piped, which
   `skills/tcw-work/references/commands.md:41-46` documents as leaving no body
   file — `tcw work stage spec <slug>` exits 0 and prints the fallback text,
   naming neither filename as though it existed.
7. The resolved `spec` prompt on an intake-only item contains an instruction to
   read the intake as the request, **and** contains no sentence drawing a
   conclusion about the requester from a missing `## References` section. Both
   halves asserted; the negative alone would pass on deleting the guidance.
8. No `{{tcw:` or `{{/tcw:` token survives into the resolved `spec` or `plan`
   prompt for a well-formed shipped prompt, on an item in each of the three
   body states. Scoped to those two stages and to well-formed spans — an
   unterminated token in a project's own prompt is required to survive
   (criterion 1) and the other four stages carry no body span.
9. Every prompt in `tcw/work/prompts/` is ≤ 50 lines:
   `tests/test_shipped_prompts.py` passes unmodified, with no ceiling raise.
10. `tcw work lifecycle --stage spec`, `--stage plan`, and `--stage postmortem`
    each list `intake.md` among `inputs`; `tests/test_lifecycle_baseline.py`
    passes against regenerated fixtures whose diff touches `inputs` lines only.
11. Each of sweep rows 5–17 is individually resolved, or re-classified with a
    reason, and `outcome.md` records which — row by row, by number. The closed
    list is the check; a grep whose results need interpreting is not.
12. `pytest` passes (1734 tests green before this change), `tcw validate`
    passes, and `tcw capabilities show` reflects the three wording deltas.

## Risks

- **The 50-line prompt ceiling.** `spec.md` has two lines of headroom. If the
  rewrite cannot fit, cut an existing clause — the ceiling is deliberate
  (`tests/test_shipped_prompts.py:40-49`). *Mitigation:* the design substitutes
  one value instead of spelling out both branches, which is net-neutral.
- **Refactoring `substitute_documentation`.** Its block-replacement behavior is
  subtle and shipped. *Mitigation:* goal 7 and criterion 3 make byte-identity a
  gate; the design authorizes duplicating the loop rather than sharing it.
- **Baseline churn.** Regenerating `tests/fixtures/lifecycle_baseline/` touches
  large JSON blobs where an unintended change hides easily. *Mitigation:*
  criterion 10 restricts the accepted diff to `inputs` lines.
- **A project with its own `spec` prompt** keeps its own wording and is
  unaffected — correct, but this fix does not reach a node that replaced the
  builtin. Nothing to do; noted so it is not mistaken for coverage.
- **Row 8 changes a documented workflow** that produced this repo's four most
  recent items. Existing items are not retrofitted.

## Notes

- **Dual review.** This spec was reviewed by `codex` and by `bllm-review` after
  its first commit. Both independently found the same high-severity design flaw
  — the first draft proposed sharing `substitute_documentation`'s walk, whose
  block-replacement semantics would have broken the inline body token. Design §2
  is rewritten around that. `codex` additionally found sweep rows 14–17, all
  verified against the tree before acceptance. Criteria 6, 7, 8, and 11 were
  tightened from both reviews.
- **One review finding rejected.** `bllm-review` argued criterion 6 (an item
  with neither artifact) is unreachable through the CLI. It is reachable:
  `tcw work new "<title>"` with nothing piped writes no body file, which
  `skills/tcw-work/references/commands.md:41-46` states explicitly. The
  criterion stands, with the construction recipe added.
- Requester's suggested remediation — "resolve the body artifact the way
  `tcw work show` does and name what it found" — is adopted.
- Assumption, not verified against every adapter: `Artifact.present` is
  populated for `intake` by adapters other than the filesystem one. The
  filesystem adapter does (`intake` is in `WORK_ARTIFACTS`,
  `tcw/store/base.py:1214`); there is no second adapter in-tree to check
  against.
- The taxonomy has no term for the body surface or for intake
  (`tcw taxonomy list`). A real gap, deliberately not filled here.
