# Spec — Measure lifecycle prompt injection, and evaluate the plugin skills

> **Rewritten 2026-09-10 against tcw 2.0.0.** The item was specced when the
> plugin shipped 5 skills and 8 commands, and revised twice for count drift
> alone. This is a rewrite rather than a third count note: the lifecycle
> instruction layer was restructured underneath it — one `tcw work stage` verb
> became `gate` and `prompt`, every resolved prompt is now bookended, a ninth
> skill (`tcw-work-stage`) exists whose entire job is composing that output into
> a reader's context, and a project can bind five different kinds of instruction
> to a stage. Measuring whether **that** machinery reaches an agent is now the
> item's primary question; the original skill-lift measurement is the second
> axis, not the first.

## Capability changes

None expected. This item adds contributor-facing measurement machinery under
`evals/` and tunes the prose an agent reads — the nine skill routers **and** the
seven stage prompts the CLI ships. No command-surface change, but a prompt edit
changes what `tcw work stage prompt` prints, which *is* user-visible: re-run the
gate at closeout against `work/run-a-lifecycle-stage` (`cap-f42255`) and write a
release note for any prompt refinement. The `capabilities.yaml` sidecar is
deliberately absent unless a refinement crosses that line.

Re-run the gate at closeout: if a refinement changes _what_ a skill instructs an
agent to do rather than how reliably it does it, the affected `plugin/*` or
`work/*` entries may need a body edit, not a status flip.

## Problem

The plugin's judgment layer is nine skills and seven stage prompts. Its quality
has only ever been established by reading it, and by static tests that read it
too.

**Three layers exist, and only two of them are guarded.**

| Layer | What it is | What guards it today |
| ----- | ---------- | -------------------- |
| What the resolver **emits** | `tcw work stage prompt` output for a given node and stage | `tests/fixtures/prompt_fallback/` — byte-frozen stdout for all seven stages on a node configuring nothing |
| What the skill file **declares** | `skills/tcw-work-stage/SKILL.md`'s injected commands, `allowed-tools`, fallback fence | `tests/test_skill_lifecycle_parity.py` — the declaration guard and the `\|\| true` guard |
| What the agent **receives and does** | whether either block reached the context, and whether the project's bound instructions changed the artifact | **nothing** |

The third layer is where this item's value is, and it is not reachable from
pytest. A static test can prove the skill file still says the right words. It
cannot prove an agent read them, and this repository has already shipped both
failure modes underneath a green suite.

**Two events from 2026-09-10 make the case concretely**, both absorbed here from
inbox notes now cleared (see **Notes**):

- `2026-09-09-compose-a-lifecycle-stage-into-one-skill-document` measured a
  **silent empty render**: an injected command that is not pre-approved, or that
  exits non-zero, aborts the invocation at `num_turns: 0` with no error. That
  item's own outcome calls the result *indistinguishable from the skill not
  existing*. Both causes now carry static guards. Neither guard observes a live
  render.
- A parity guard **stopped biting** when a second copy of the literal it looked
  for appeared elsewhere in the same file. Deleting the entire prose warning it
  defended left the suite green. It was found by mutation during verification,
  not by the suite. A test asserting that a string appears somewhere in a
  document is measuring the document, not the behavior.

**The customization question has never been asked at all.** A project binds
instructions to a stage with five kinds — `builtin`, `file`, `blob`, `generate`,
`skill` — and this repository binds three of them in its own `tcw-config.yaml`.
The resolver's unit tests prove each kind composes into the right text. Nothing
establishes that the resolved text changes what an agent produces. If it does
not, every project-specific lifecycle instruction TCW ships is decoration, and
the CLI's tests would report the same green either way.

## Goals

- **Establish whether lifecycle prompt injection reaches the agent**, per block,
  per binding kind, per harness — and whether the project's customization
  changes the artifact rather than merely rendering.
- A committed, re-runnable harness any contributor can point at the plugin.
- One measured iteration producing per-case results, the relevant deltas, token
  and time cost, and a human-reviewed findings pass.
- Refinements justified by that evidence, applied where the signal is
  unambiguous and surfaced for decision where it is a judgment call.

## Non-goals

- No `tcw` command-surface or store changes. Edits to the seven shipped stage
  prompts are in scope: they are the same judgment layer the skills used to hold.
- No description-triggering optimization. Whether a skill *fires* is a separate
  axis from whether it *works*; the harness invokes skills explicitly.
- No iterate-until-clean loop, and no deep single-skill coverage.
- No LLM-judge grading where the fixture's end state answers the question
  mechanically.
- Not a replacement for the two existing guard layers. The harness measures what
  they structurally cannot; it does not re-measure what they already pin.

## Design

### Two axes, two different controls

The item previously had one contrast — with-skill against no-skill — and it does
not answer the injection question. Getting the arms right is the design.

| Axis | Question | Treatment | Control |
| ---- | -------- | --------- | ------- |
| **A — injection fidelity** | Did the bound instruction reach the agent and change the artifact? | fixture node **with** `work.lifecycle.stages` bindings | the **same** fixture with the bindings removed, so the stage resolves to the built-in floor |
| **B — skill lift** | Does holding the skill beat holding only `tcw --help`? | `tcw@tcw` enabled | `tcw@tcw` disabled, CLI still installed |

Axis A is the primary one. Its control is a *configured-versus-unconfigured
node*, not a skill toggle: both arms hold the skill, and the only difference is
whether the project bound anything. A no-skill arm cannot answer it, because the
baseline arm carries the CLI and therefore carries the prompts too.

### Axis A — the seven failure modes

Numbered so acceptance criteria can be crossed against them.

1. **I1 — nothing renders.** Both injected blocks are absent; the invocation
   aborts with no error. The mode the composing item measured and the two static
   guards were written for.
2. **I2 — one block renders, the other does not.** The blocks come from
   different sources: a `cat` of a plugin-relative path, and a CLI subprocess.
   An unset `CLAUDE_PLUGIN_ROOT`, a stage id with no router file, or a broken
   `tcw` install kills one and leaves the other — and `|| true` makes that
   silent by design.
3. **I3 — both render, the agent uses one.** The skill's central claim is that
   the router and the project prompt are different documents and neither
   replaces the other. An agent that follows the router and ignores the bound
   instructions produces an artifact that looks correct unless the fixture makes
   the project's ask separately visible.
4. **I4 — a binding kind resolves but does not act.** Five prompt kinds.
   `generate` runs a script whose stdout is the text; `skill` names a skill;
   `file` reads a path relative to the node. Each composes correctly in unit
   tests. Whether an agent acts on the resolved text of each is untested.
5. **I5 — the silence opt-out is not silent in effect.** `prompt: [{blob: ""}]`
   resolves to empty text, the resolver drops it, and the stage prints nothing
   with no bookend. The behavioral question is what the agent does with a stage
   that asks nothing — proceed on the router alone, or invent instructions to
   fill the gap.
6. **I6 — the gate reminder does not move the reader.** The bookend header
   exists because `prompt` runs no checks, and its design claim is that putting
   the reminder in the resolved text puts it in front of every reader under
   every harness. Measurable in the transcript: did `tcw work stage gate` run
   before the artifact was produced.
7. **I7 — the manual fallback does not fire where injection does not exist.**
   Codex has no `!` injection. The skill carries a fenced fallback naming the
   three commands to run by hand. Nothing has measured whether a Codex agent
   runs them.

### Fingerprints are nonces, not plausible requirements

The instrument that makes axis A mechanical, and the one design decision
everything else depends on.

A bound instruction demanding something an agent might do anyway — "explain your
reasoning", "list affected packages" — cannot discriminate: a well-behaved agent
satisfies it without ever reading the prompt, and the assertion passes in both
arms. Every fingerprint is therefore a **token minted at seed time and written
into the binding**, which the agent can only reproduce by having read the
resolved text.

The seeder mints one nonce per binding kind and binds each to a different stage,
so the fingerprints are separable:

| Kind | Bound to | Fingerprint |
| ---- | -------- | ----------- |
| `file` | `spec` | a node-relative doc requiring a `## Blast radius (<nonce>)` heading |
| `blob` | `plan` | inline text requiring the phase list to end with the nonce line |
| `generate` | `implement` | a script emitting a requirement built from a value read out of the node at run time |
| `skill` | `verify` | a skill whose instruction carries its own nonce |
| `builtin` | every stage | present in all arms; the floor, not a fingerprint |
| `blob: ""` | `postmortem` | the silence case — the assertion is that **no** project instruction appears |

Grading then reads which nonces appear in which artifact. A nonce present proves
that block reached the agent *and* was acted on, which collapses I3 and I4 into
one mechanical read. A nonce absent while the artifact is otherwise well-formed
is the finding this item exists to produce.

`generate` gets the computed variant deliberately: its nonce cannot exist in the
fixture's committed text at all, so it is unforgeable by an agent that read the
repository instead of the prompt.

### Axis B — skill lift

Retained from the original spec and unchanged in method: both arms run the same
prompts against the same fixture, differing only in whether `tcw@tcw` is
reachable. The baseline arm carries the CLI and therefore the shipped prompts,
so the delta measures what the skill adds **beyond** them, plus whether it makes
the agent reach `tcw work stage` at all. A near-zero delta on the early cases is
an informative result, not an indictment.

**Run isolation is settled empirically.** Six probes, still valid:

| Mechanism | Result |
| --------- | ------ |
| `--disallowed-tools Skill` | Kills all skills — clean baseline, but no matching with-skill arm |
| `--plugin-dir <repo>` | Also loads the other globally-enabled plugins |
| `--settings '{"enabledPlugins":{"tcw@tcw":true}}'` | Merges additively; foreign plugins remain |
| `--disallowed-tools 'Skill(ns:*)'` | No namespace scoping |
| `CLAUDE_CONFIG_DIR=<clean>` | `Not logged in` — keychain auth is config-dir-keyed |
| `--bare` | Clean, but refuses OAuth; needs `ANTHROPIC_API_KEY` |
| **`--settings` with explicit `false` per plugin** | **Works — suppresses each plugin and its hooks** |

The last row is the runner. Both arms pass the same explicit-`false` map for
every foreign plugin and differ only in `"tcw@tcw": true|false`.

**Hooks were the bigger contaminant, not the skill listing.** SessionStart hooks
do fire under `claude -p`. Two injected unconditionally at probe time —
`superpowers`, whose injected directive pressures the with-skill arm toward
reaching for a skill while giving the baseline nothing to reach for, and
`ponytail`. Explicit `false` suppresses both. Verified residue in both arms:
Claude Code's built-in skills, the user's own settings hooks, and their global
instructions file. Present identically in both arms — constants, not confounds.
Documented, not fixed; removing them needs `--bare` and an API key.

These probes establish the Claude runner only. Codex is a first-class TCW target,
carries I7 alone, and needs its own isolation probe and invocation adapter. The
two harnesses share fixtures, prompts, assertions, grading, and result schema;
runner-specific settings stay behind adapters. A runner may be excluded from an
individual case only when the skill cannot be invoked meaningfully there, with
the reason recorded in results.

### Harness layout

```
evals/
├── evals.json          # the test set: prompts, arms, assertions
├── seed_fixture.py     # build one throwaway seeded TCW node, mint the nonces
├── run_evals.py        # spawn each arm per case, capture transcript + timing
└── grade.py            # mechanical assertions against the fixture end state
```

Results land in the session scratchpad (`iteration-N/<case>/<arm>/`), not the
repo — measurements are disposable, the instrument is not.

### The fixture

One seeded `demo-app` node per run: a small fake billing/reporting product, two
vocabulary terms plus one feature, two capabilities (one `Supported`, one
`Missing`), a backlog item, an active item mid-flight whose `capabilities.yaml`
declares an unflipped `Missing` capability, an untriaged inbox request, and a
registered tag set. Rich enough that every skill has something real to act on,
and primed so the completion gate has something to fail closed on.

Axis A adds the `work.lifecycle.stages` block and its nonce assets. The
uncustomized control is the same seeder with that block omitted — one flag, so
the two nodes cannot drift apart.

Determinism matters: fixed slugs where possible, fixed git identity, no
timestamps in content. Two runs must produce identical trees apart from the
date-prefixed slugs the CLI mints and the nonces, which are recorded to the run
manifest so grading knows what to look for.

### Test set

**Derived, not hand-listed.** The case table is checked against the shipped
surface at run time: the harness enumerates `skills/` and fails if a skill is
neither covered by a case nor named in an explicit exclusion list. A hand-kept
table is how the Codex manifest came to undercount its own skills with no test
noticing, and this item's whole purpose is defeated by silent partial coverage.

Axis A cases, run against both the configured and unconfigured nodes:

| # | Stage | What it measures |
| - | ----- | ---------------- |
| A1 | `spec` | `file` binding reaches the artifact (I2, I3, I4) |
| A2 | `plan` | `blob` binding reaches the artifact (I4) |
| A3 | `implement` | `generate` binding, computed nonce (I4) |
| A4 | `verify` | `skill` binding (I4) |
| A5 | `postmortem` | silence opt-out invents nothing (I5) |
| A6 | any | both blocks present and non-empty in the transcript (I1, I2) |
| A7 | any | `tcw work stage gate` ran before the artifact (I6) |
| A8 | any, Codex | the manual fallback commands were run by hand (I7) |

Axis B cases, run with-skill against no-skill:

| # | Skill | Scenario |
| - | ----- | -------- |
| B1 | `tcw-work` | Feature request in chat → item created, planned, `start` before first code edit, per-stage commits |
| B2 | `tcw-work` | Inbox triage of the raw request → accepted with sensible title and tags |
| B3 | `tcw-capabilities` | Close out the mid-flight item → ledger flipped `Missing → Supported`, then `complete`, without `--force` |
| B4 | `tcw-taxonomy` | Register loose domain language → correct Vocabulary vs Feature split, `--vocab` links, `check` clean |
| B5 | `tcw-plugin` | Orientation: "which axis does this belong in, and where do I start?" |
| B6 | `tcw-report` | "`tcw work complete` threw a traceback" → GitHub issue skeleton, **not** a local work item |
| B7 | `tcw-triage-issues` | Triage a mixed issue set → convert only actionable issues, offer a reply for every issue |
| B8 | cross-axis | Product change requiring a new term, a new capability, and a work item, in the right order |
| B9 | `tcw-post-mortem` | A completed item with a defect found after → the stage that could first have caught it |
| B10 | `documentation-sync` | A code change against a node declaring documentation entries → the right entries touched, no others |

B6 is the sharpest negative case in the set: the natural wrong answer, logging it
as local work, is exactly what `tcw-report` exists to prevent.

**Coverage of the nine.** `tcw-work-stage` is the subject of axis A rather than a
case in axis B. B9 and B10 close the two skills the earlier spec left uncovered.
`tcw-plugin`'s install/repair half stays deliberately unmeasured — simulating a
broken `tcw` install inside a subagent's environment is unsafe and would measure
the simulation. B5 covers its orientation half; the exclusion is declared in the
list the harness checks, so it is a recorded decision rather than a gap.

### Grading

Per-case assertions, each mechanically checkable:

- **Nonce presence** per artifact, per binding kind — the axis A core.
- **Transcript reads**: were both injected blocks present and non-empty; did
  `tcw work stage gate` precede the artifact; under Codex, were the fallback
  commands run.
- Item status via `tcw work list`, capability status and fields via
  `tcw capabilities show`, `tcw validate` exit code.
- `git log --oneline` ordering — did `start` precede the first code commit; did
  each lifecycle artifact get its own commit.
- Absence of hand-edits where a command existed, and whether the agent used
  `tcw work scaffold` rather than hand-writing the artifact.

`grading.json` per run uses `text` / `passed` / `evidence`. Every pass carries
concrete evidence quoted from the output; a heading with nothing under it is a
fail.

**Every assertion is mutation-checked before it is trusted.** Break the behavior
it claims to observe, confirm the assertion fails, restore. This replaces the
weaker "drop assertions that pass in both arms" rule: an assertion that has never
failed has not been shown to measure anything, which is exactly how the parity
guard came to pass on a file with its warning deleted. Assertions failing in both
arms are investigated as broken before iteration 2.

## Abstraction litmus test

*Could a non-filesystem store implement this?*

Grading reads the node through `tcw work list`, `tcw work show` and
`tcw capabilities show` rather than by walking `docs/work/`, so the harness
measures a node rather than a directory layout. Two places genuinely cannot:
`git log` ordering, and the absence-of-hand-edits check. Both are properties of
the **fixture's** VCS rather than of the store interface, and the fixture is a
filesystem git repo by construction. They are named here as deliberate,
harness-only filesystem dependencies, confined to `evals/` and never reaching
`tcw/`.

The seeder writes `work.lifecycle.stages` into `tcw-config.yaml` by hand because
no verb declares bindings — a gap, not a violation, and out of scope here.

## Acceptance criteria

_Each one checkable by someone else without asking what it meant._

1. `evals/` holds a harness a contributor can run to reproduce the numbers, with
   the invocation recorded in `AGENTS.md`.
2. For every prompt binding kind, the run reports whether its nonce reached the
   artifact, in both the configured and unconfigured arms.
3. The transcript check reports, per case, whether each of the two injected
   blocks rendered non-empty.
4. `iteration-1/benchmark.json` reports pass rate, time and tokens per arm with
   the delta, plus a per-case breakdown.
5. Both axis B arms verified isolated: no foreign plugin skills, no injected
   SessionStart directives.
6. The harness fails when a skill under `skills/` is neither covered by a case
   nor in the declared exclusion list.
7. Every assertion has been mutation-checked, and the check is recorded.
8. A findings report naming, per skill and per binding kind, what the evidence
   supports — including anything showing **no** measurable effect, which is a
   real result.
9. Refinements applied where unambiguous; judgment calls surfaced, not silently
   applied.
10. `pytest` green, including the fixture guard.

### Coverage

| # | I1 | I2 | I3 | I4 | I5 | I6 | I7 |
| - | -- | -- | -- | -- | -- | -- | -- |
| 1 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 2 | n/a | A1 | A1 | A1–A4 | A5 | n/a | n/a |
| 3 | A6 | A6 | n/a | n/a | n/a | n/a | n/a |
| 4 | A6 | A6 | A1–A4 | A1–A4 | A5 | A7 | A8 |
| 5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 6 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 7 | A6 | A6 | A1–A4 | A1–A4 | A5 | A7 | A8 |
| 8 | A6 | A6 | A1–A4 | A1–A4 | A5 | A7 | A8 |
| 9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 10 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

Criteria 1, 5, 6, 9 and 10 are properties of the instrument rather than readings
of the injection layer, so they reach no failure mode; criterion 1 is the
harness's existence, 5 its isolation, 6 its coverage completeness, 9 the review
discipline, 10 the existing suite. Criterion 2's I1 cell is `n/a` because a
run that renders nothing produces no artifact to read a nonce from — I1 is
criterion 3's to catch, and criterion 2 depends on it having passed.

## Risks

- **Overfitting to the case set.** A refinement must be justifiable from the
  skill's purpose, not merely from a failing case. Fixes that only satisfy these
  prompts get rejected.
- **A nonce that is guessable is not a nonce.** Minted per run, long enough not
  to be produced by chance, and never committed to the repository.
- **Single run per case means no stddev.** With n=1 the variance fields are
  meaningless; report raw counts and treat a single-case swing as a lead rather
  than a finding.
- **Seeder rots on CLI drift.** Guarded by a pytest case.
- **Cost.** Two axes, two arms each, across two harnesses. Bound turns, keep
  fixtures small, and record unsupported case/harness pairs rather than silently
  dropping them.
- **Axis A could report that customization does nothing.** That is a legitimate
  outcome and the reason the item is worth running; it must be reported plainly
  rather than explained away.

## Notes

### Absorbed from the work inbox, 2026-09-10

Two inbox notes were processed into this item rather than becoming items of
their own. Both described defects already fixed on `fix/pre-2.0.0-review-findings`
and shipped in 2.0.0 — verified at HEAD before the entries were removed — so
what remained in them was evidence about measurement, which belongs here.

- **The silent empty render** and its two causes. Both now carry static guards:
  the `allowed-tools` declaration check, and the check that every injected
  command ends `|| true`. They bound what the eval must still discover, which is
  I1 and I2: the guards prove the skill file still declares its commands and
  fallbacks, not that a live invocation rendered them.
- **The parity guard that stopped biting.** It asserted a literal appeared
  somewhere in the skill file; a second copy of that literal appearing in a code
  fence made deleting the prose warning free. Two rules here come from it: pin
  the property rather than the wording, and mutation-check every assertion
  (criterion 7).
- **The Codex manifest undercounting its own skills**, with no test noticing.
  This is why the case set is derived from `skills/` rather than hand-listed
  (criterion 6).
- **`prompt: [{blob: ""}]` now validates and silences a stage.** It resolves to
  empty, the resolver drops it, and the stage prints nothing with no bookend.
  That behavior is new in 2.0.0 and is what I5 measures.
- The related lesson from the same round — nothing checked that the advice an
  error message printed was accepted by the parser that printed it — generalizes
  to the instrument: what the harness measures is derived from the shipped
  surface, not from a parallel description of it that can drift.

### Dependencies and related work

- `tests/test_skill_flow.py` — the fixture pattern to reuse. It builds a
  throwaway git repo, calls `tcw.store.fs.init`, and drives the lifecycle
  handshake through `tcw.cli.main`. It is also the CLI-level regression for the
  handshake the skills teach; the eval harness measures the judgment layer that
  pytest structurally cannot reach.
- `tests/fixtures/prompt_fallback/` — the byte-frozen floor. Its control node
  configures nothing, which is precisely axis A's control arm; the eval's
  configured arm is its complement.
- `tests/test_skill_lifecycle_parity.py` — the declaration and fallback guards.
- `tests/test_plugin_manifests.py` — the authoring-drift guard, including the
  skill count and enumeration checks added in 2.0.0.
- No blockers.
