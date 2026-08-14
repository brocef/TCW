# Spec — Repoint the work skill and docs at the CLI

Child **C7** of `2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`.

C7 owns **both sides of the CLI/skill seam**: it reduces the stage routers *and*
edits `tcw/work/prompts/*.md` to add a self-review pass. See the epic spec's
"Amendment: C7 owns both sides of the seam".

## Capability changes

### The declared delta

**Changed — `work/configure-the-work-lifecycle`** (`cap-b9711e`, `Supported`).

Line 6 of `docs/capabilities/work/configure-the-work-lifecycle/description.md`
reads:

> **Everything I configured before this still works and still prints the same
> thing.** A stage id with a plain list under it means what it always meant.

C6 made a bare `stages.<id>: []` — and its explicit spelling `prompt: []` — a
`tcw validate` problem (C6 spec §3a; `base.py:_parse_stage`). The first sentence
is false as an unqualified claim, and the second is false for exactly one plain
list: the empty one.

The fix is a **body edit to that one line**, not a status change and not a new
record. `Status` stays `Supported`; no field changes. `tcw capabilities set`
does not write description prose, so this is an edit to `description.md`
followed by `tcw capabilities check`.

The replacement must keep the part that is true and name the one exception. The
release notes already carry the correct wording
(`docs/release-notes/upcoming.md:161-176`: "nearly all of it", then the
`prompt: []` exception and the `{blob: ""}` opt-out). **The ledger record is the
only place in the tree that *asserts* the false form** — grepping the sentence
across `docs/`, `README.md`, and `skills/` returns four other hits, all of them
work-item archives quoting it in order to name it as the contradiction (C6's
`outcome.md:180` and `refined-outcome.md:62`, the epic's `plan.md:179`, and this
spec). Those are true historical statements and are not edited. So the fix is to
bring the record into line with wording that already exists and was already
reviewed, not to invent new wording.

C7's `capabilities.yaml` (which does not exist yet) therefore reads:

```yaml
changed:
    - work/configure-the-work-lifecycle
```

### Does the self-review pass change a user-facing capability? No.

C6 found that shipping prompt *content* changed `work/run-a-lifecycle-stage`
(`cap-f42255`), contra the epic's "documentation only" prediction. That is not a
precedent for this edit, and the distinction is worth stating because it is the
rule for every future prompt change:

C6 changed the **mechanism** — before C6, `tcw work stage <id>` on an
unconfigured node exited 0 and printed nothing; after C6 it prints TCW's own
instructions. The record had to say so, and does
(`work/run-a-lifecycle-stage`, "With nothing configured for a stage, the
instructions are TCW's own"). C7 changes the **text those instructions
contain**. The record describes what the command does, which stages ship
defaults, where the output goes, and what it refuses; it enumerates no prompt
content. Nothing in it becomes false, and a ledger that tracked prompt wording
would have to be edited on every prompt edit forever.

**Recorded rather than assumed:** if the requester wants the self-review pass
visible in the ledger, the honest place is one clause in
`work/run-a-lifecycle-stage`, not a new capability. This spec does not do it.

### Sibling sweep — every capability record checked against C1–C6

C6 found its contradiction by accident, which suggested nobody had swept. This
one is deliberate. Method: `tcw capabilities list --local-only` (68 records),
then `grep -rn` across all `description.md` for the terms C1–C6 could have
falsified (`initial-request`, `lifecycle`, `stage`, `prompt`, `skill`,
`spec.md`, `plan.md`, `outcome.md`, "request document"), then reading every hit
against the shipped behaviour.

**Result: no second falsified record.** The near-misses, so a later sweep does
not re-litigate them:

- `plugin/triage-github-issues` and `work/complete-a-work-item` both claim an
  accepted issue's `initial-request.md` records the issue under `## Origin`.
  C1 stopped the *tool* from synthesizing a request — but
  `skills/tcw-triage-issues/SKILL.md:135-152` has the **agent** write that file
  after `tcw work new`, and `tcw work new` with no stdin still creates the
  folder. Both records hold.
- `work/retitle-a-work-item` says `initial-request.md`'s heading is left alone.
  Still true; an item that has no such file has no heading to leave alone.
- `web/editing` describes Initial Request / Spec / Plan tabs and does not mention
  intake. The intake and promotion semantics live in `work/capture-raw-intake`,
  which is medium-neutral and already correct. Incomplete-by-design, not false.
- `work/view-the-board` describes the board without enumerating letters, so C1's
  lowercase `i` did not falsify it; `work/capture-raw-intake` carries it.
- `cli/validate-a-node` describes `tcw validate` generically and does not
  enumerate rejections, so C3's and C6's new ones did not falsify it.

**Two ledger gaps found, both out of C7's declared scope, both reported for the
requester's decision** (they are hygiene, not contradictions — `tcw capabilities
check` passes and `tcw capabilities drift` reports none):

1. **The Feature `configurable-work-lifecycle` is linked by zero capabilities.**
   The epic spec's `## Capability changes` says that Feature "already exists and
   covers this initiative". `grep -rl configurable-work-lifecycle
   docs/capabilities/` returns nothing. The four lifecycle capabilities —
   `configure-the-work-lifecycle`, `inspect-the-lifecycle-contract`,
   `run-a-lifecycle-stage`, `customize-lifecycle-artifact-templates` — carry no
   `Feature:` at all, while nine other `work/` records do carry one.
2. **`work/run-a-lifecycle-stage` has no `Subject` and no `Feature`.** Every
   other lifecycle capability carries at least `work-item/lifecycle-stage`. C4
   shipped it unlinked. Separately,
   `work/configure-the-work-lifecycle` — the record that is *about* hooks —
   carries only `work-item/lifecycle-stage`, while C3 added
   `work-item/lifecycle-hook` for exactly that noun and
   `work/customize-lifecycle-artifact-templates` links both.

**Recommendation:** fold both into C7, because C7 is already editing this
record and the whole fix is four `tcw capabilities set --field` calls with no
prose to write. If the requester prefers, they are a clean C8 item instead.
This spec does not assume the answer; acceptance criterion 12 is conditional on
it.

## Problem

The CLI now answers "what do I do at this stage?" itself. `tcw work stage <id>
<slug>` prints TCW's own instructions on a node that has configured nothing
(`cli.py:803-804`, the floor at `resolve.py:241`), and `tcw work scaffold
<artifact> <slug>` writes a starting draft. The skill and the README still
describe a world in which the skill was the only place that knowledge lived.

Concretely, four surfaces are now wrong or duplicated:

1. **The seven stage documents restate the shipped prompts.**
   `skills/tcw-work/references/stage-*.md` are 66–77 lines each (66
   `postmortem`, 67 `inbox`, 68 `plan`, 70 `request` and `spec`, 77 `implement`
   and `verify`). C6's spec §5 table moved their methodology into
   `tcw/work/prompts/*.md` and named the right-hand columns as C7's contract.
   Six of the seven now say, in the skill, what the CLI prints — which is the
   version-skew hazard the epic's Risks name and what acceptance criterion 18
   forbids.
2. **`SKILL.md`'s "Always" section names the wrong verb.** `SKILL.md:52-54` says
   "Run `tcw work lifecycle --stage <id>` before a stage and honor any binding
   it reports". That command reports *bindings*; it does not print instructions
   and never resolves a `builtin` (C6 spec §3, "`tcw work lifecycle` is
   untouched"). On this repo, which configures no `work.lifecycle` key, it
   reports nothing at all — so a Codex agent following `SKILL.md` literally
   learns nothing and never reaches the prompt C6 shipped.
3. **`hooks.md` has grown by accretion, not drifted.** At 159 lines it is the
   largest reference document, and it was written in three passes by three
   children (`205ea7d` C3 roles/kinds, `d7802b1` C4 the stage verb, `8a8f179`
   C5 scaffold). Its content is accurate. Its defect is duplication: sections
   1–5 restate `README.md:605-735` in near-identical prose, and lines 76–118
   restate what `tcw work stage --help` and the CLI's own refusal messages say.
4. **`README.md` §"Binding your own skills and commands to the lifecycle"
   (`README.md:605-735`) is four appended answers, not one section.** C1–C6 each
   corrected the sentences they falsified — C6's outcome §4 records that its
   three located edits were all inside this section, made without touching the
   rest; C5's draft paragraphs (`README.md:698-719`) were added the same way.
   The section is true and reads as sediment.

And one thing that is missing rather than wrong:

5. **TCW has no self-review pass at any stage.** This epic is the argument for
   one. C5's spec shipped criterion 13 asserting an exact-set equality that
   fails 3 of 7 stage documents; C6's spec cited `cli.py:801` when C5's changes
   had already moved it to `:804`. Both were caught at `plan`, by the stage
   after the one that wrote them. Neither shipped, so the cost was a spec
   revision round each — real, bounded, and avoidable.

## Goals

1. A reader following `SKILL.md` or `README.md` ends up **running the verb**,
   not reading a second copy of what the verb prints.
2. Each of the six reduced routers carries the TCW-specific judgment the CLI
   does not — delegability, `[gated]`/`[judgment]` notation, epic and cross-node
   deltas, sub-skill names, store mechanics — and nothing else.
3. Criterion 18 is **enforced by tests in both directions**, with the limits of
   that enforcement stated rather than implied.
4. The shipped prompts gain a self-review pass **only where it checks something
   the stage cannot already see**, and no stage gains a ritual.
5. `hooks.md` and `README.md:605-735` each say a thing once.
6. The `work/configure-the-work-lifecycle` record stops contradicting the tool.

## Non-goals

- **Any change to `tcw/` outside `tcw/work/prompts/*.md`.** No CLI behaviour
  changes; no new command, flag, or output line.
- **Reopening C6's §5 split.** Its "Moves into the prompt / Stays in the skill /
  Deliberately lost" table is the contract. The one borderline case C7 examined
  and left alone is recorded in `## Notes`.
- **`stage-inbox.md`.** Exempt by constraint 3 — no prompt ships for `inbox`,
  `tcw work stage inbox <slug>` is refused by design, and reducing it would
  strand its methodology. It is not edited at all.
- Review calibration, a generalized no-placeholders ban, and an explicit
  decomposition trigger. Declined by the requester; not folded in.
- Restructuring `README.md` outside `605-735` (see `## Notes` — the heading has
  no closing boundary, which is a pre-existing defect and a C8 candidate).
- Raising `SKILL.md`'s 60-line budget. The rule on breach is "extract, don't
  grow" (`tests/test_skill_lifecycle_parity.py:190-198`).
- Editing any capability record other than the one declared above (and, if the
  requester accepts the recommendation, the four `--field` calls).

## Design

### 1. The operative rule: a router may name, it may not instruct

Constraint 2 asks for this tension to be resolved explicitly. The resolution:

> **Naming is addressing; restating is instruction.** A router may name the
> stage, its inputs, its artifact, and the command that prints the methodology.
> It may not restate *how* to perform the stage — the steps, the content of the
> artifact's required sections, or the exit-badly branches.

Naming is load-bearing and cannot move to the CLI: `SKILL.md`'s "Finding your
place" (`SKILL.md:40-46`) routes on artifact filenames, and an agent choosing
which document to load must know what a stage produces *before* it runs
anything. Instruction is what C6 moved and what criterion 18 protects.

This also settles the structural-test question below: a one-line `## Produce`
naming `spec.md` is addressing and stays; a `## Exit` section reproducing three
redirect branches the prompt already carries is instruction and goes.

### 2. Per-stage self-review pass in `tcw/work/prompts/*.md`

**The admission gate for a pass**, applied uniformly: *the pass must check
something against a source outside the artifact being reviewed* — the tree, a
prior artifact, or a command's output. A pass that only re-reads the prose just
written catches only what its author already knew, which is the ritual the
requester's constraint 6 rules out.

Under that gate, three stages get one and three do not.

| Stage | Pass | Why |
| --- | --- | --- |
| `request` | **No** | Its artifact is the requester's intent. There is nothing outside it to check it against — that is the stage's premise. Its one falsifiable obligation ("asked; none provided") is already step 2 (`request.md:21-26`). |
| `spec` | **Yes — three items** | The stage that produced both of this epic's defects, and the only one whose artifact makes claims that are mechanically re-checkable. |
| `plan` | **Yes — it already has one; name it and complete it** | `plan.md:30-31` already says "Re-read the finished plan against the spec: coverage gaps, inconsistent names, tasks that appear twice", and `plan.md:28-29` already bans placeholders. C7 does **not** add a second block. |
| `implement` | **Yes — one line, folded into an existing step** | The suite is the external check and it already runs (`implement.md:30`, "No completion claim without output from a command you ran just now"). One item is missing and is one line. |
| `verify` | **No** | The stage *is* a review pass. Its step 2 already reads the diff against the spec's acceptance criteria and runs the checks. A self-review block here reviews the reviewer. |
| `postmortem` | **No** | Terminal and out-of-band (`postmortem.md:18-24`). It has no downstream consumer to protect, and its "the problem is a one-off — record and stop" branch already covers its failure mode. |

**`spec`'s three items** (what they check, not their wording — wording is
implementation):

1. **Every `file:line` citation re-resolves to what the spec claims it shows**,
   re-checked at the end rather than trusted from when it was written. A sibling
   item landing mid-spec moves lines. This is the C6 `cli.py:801`→`:804` defect
   exactly.
2. **Every acceptance criterion that can be executed against the tree today is
   executed** — a set equality, a count, a grep — and any that fails is
   reworded or dropped before the spec is committed. This is the C5 criterion 13
   defect exactly.
3. **Any criterion two readers could check two different ways is pinned to one
   reading.** This is the one item transplanted from superpowers'
   Spec Self-Review (`brainstorming/SKILL.md:218`), and it is transplanted
   because TCW's own criterion-quality rule ("checkable by someone else without
   asking what you meant", `spec.md:25-27`) states the goal without saying what
   to do when it fails.

Items 1 and 2 are TCW-original: superpowers' checklist has no grounding-in-code
item, because its specs do not cite code.

**`plan`'s added item:** the existing re-read gains the coverage direction it
half-states — *every acceptance criterion in the spec is covered by at least one
task, and every task traces back to one*. "Coverage gaps" today is one-directional
and unpinned.

**`implement`'s one line:** an `outcome.md` whose "what the plan or spec got
wrong" section is empty is making a claim, not omitting one. The prompt already
requires the section (`implement.md:10-12`); the pass makes silence deliberate.

**What is deliberately not added anywhere:** a placeholder scan outside `plan`
(the requester declined a generalized ban), a scope/decomposition trigger (also
declined), and reviewer calibration (also declined).

### 3. Does a self-review pass catch the two real defects? Partly

**A generic four-item checklist would have caught neither**, and this is worth
stating because copying superpowers' list into six files is the obvious
implementation and it is worthless here. C5's criterion 13 was internally
consistent, unambiguous, free of placeholders, and in scope; it was simply false
about the tree. C6's `cli.py:801` was likewise all four things. Re-reading
either spec with fresh eyes finds nothing.

**The pass designed above would have caught both**, because both defects are
re-executable claims and items 1 and 2 exist to re-execute them. That is not a
coincidence — the items were derived from the defects.

**What it still would not catch**, stated so nobody over-claims for it:

- A criterion that is checkable in principle but not executable *yet*, because
  the code it describes does not exist. Item 2 covers "executable today" only.
- A claim grounded in a file that exists and says what is claimed, but which is
  the wrong file for the argument.
- Anything at `request`, `verify`, or `postmortem`, which get no pass.

Both defects were caught one stage later and cost a spec revision each. The pass
moves the catch earlier and saves that round. It does not make `plan` redundant
as a check on `spec`, and the prompts must not imply that it does.

### 4. Line arithmetic — every prompt fits, one with little margin

Ceiling 50 (`tests/test_shipped_prompts.py:39-50`), floor 15 non-blank (`:31-35`).

| Prompt | Now | Pass | After | Margin |
| --- | --- | --- | --- | --- |
| `request.md` | 39 | none | 39 | 11 |
| `spec.md` | 40 | new block, 3 items | **~48** | **~2** |
| `plan.md` | 40 | rewrite of an existing 2-line step, +1 item | ~44 | ~6 |
| `implement.md` | 39 | +1 line in an existing step | ~40 | ~10 |
| `verify.md` | 40 | none | 40 | 10 |
| `postmortem.md` | 40 | none | 40 | 10 |

`spec.md` is the only prompt under real pressure: a heading, a blank line, and
three items at two lines each is 8 lines, landing at 48 of 50. **The
implementation gets a hard budget of 10 lines for that block**; if it cannot fit
in 10, the ceiling has started deciding the seam, which is the exact thing the
40→50 raise (`ab86012`) existed to prevent — so that is a finding to escalate to
the requester, not a licence to trim `spec.md`'s existing content.

Two lines of margin on `spec.md` also means the routers must not push anything
else into it. Section 6 records the one candidate and why it stays out.

### 5. What fills each router — and five of six cannot reach 40 lines

**This is the spec's principal finding, and it does not meet constraint 1's
range.** Constraint 1 targets 40–50 lines; constraint 2 authorizes shorter with
a stated reason. The reason is arithmetic: C6's §5 table moved the methodology,
and what is left per stage is 20–40 lines including the structure the parity
tests require.

The structural floor, from `tests/test_skill_lifecycle_parity.py`: a title, the
route line, `## Purpose`, `## Inputs`, `## Produce` (naming every artifact in
`step.produces`, `:85-104`), `## Steps` (carrying at least one marker,
`:134-138`), and the blank lines between them — **about 18 lines before any
judgment is written**.

| Router | Skill-only content that survives | Expected |
| --- | --- | --- |
| `stage-request.md` | Not delegable, and why (it needs input only the user has); the epic's coordination goal. C6 assigns the board-`R` and `reconcile`/`rollup.md` material to "deliberately lost", so it does not come back. | **~22** |
| `stage-spec.md` | Delegability, with `Inputs` as the context brief and `Produce` as the return contract; the epic's Design→child-boundaries substitution; routes to `decompose.md` and `epic-deltas.md`; the `tcw-capabilities` sub-skill name. | **~28** |
| `stage-plan.md` | Delegability; the epic coordination-plan variant → `epic-deltas.md`; the `documentation-sync` sub-skill name; the bounded-DAG-of-stage-documents paragraph; `--blocked-by` marked `[gated]`. | **~30** |
| `stage-implement.md` | Delegability and that this is where it pays → `delegation.md`; the `tcw-capabilities` and `documentation-sync` sub-skill names; `tcw work start` marked `[gated]`. | **~26** |
| `stage-verify.md` | The assess/decide split; the `tcw-verifier` agent and the Claude/Codex difference → `delegation.md`; the stop marked user `[judgment]`; `tcw-capabilities`; the version-cut *mechanics* — the option menu, the unpushed-local-tag case, `/tcw-cut-version`, `documentation-sync`'s `references/cut-version.md`. | **~38** |
| `stage-postmortem.md` | Delegability to a read-only subagent, and the `tcw-post-mortem` agent under Claude. Everything else moved. | **~22** |
| `stage-inbox.md` | **Unchanged, 67 lines.** Exempt. | 67 |

So: **`verify` is the only router that approaches 40**, and the honest bracket is
a **ceiling of 40** (the bottom of the requester's range, so no router exceeds
what was asked) with no floor beyond the structural one. Padding five documents
by 12–18 lines each to hit a range is the one outcome constraint 2 names as
worse than a long document.

**The `## Exit` section is dropped from the six reduced routers**, and
`stage-inbox.md` keeps all five. Verified per stage rather than assumed:

- Every "**Badly**" branch in all six is already in the corresponding prompt —
  C6's §5 table says "all three exit-badly branches" for each of the six, and
  the shipped prompts carry them under `## Exit badly`.
- Every "**Well**" statement is already implied or stated by its prompt's
  `Produce` and `Steps`. Checked one by one: `spec`'s ("could be handed to
  someone else and checked without asking what you meant") is `spec.md:25-27`
  verbatim in substance; `implement`'s four clauses are steps 7–9 plus the
  `Produce` block; `verify`'s is `verify.md:9-12`; `plan`'s is `plan.md:9-12`;
  `postmortem`'s is `postmortem.md:12-16` plus step 2; `request`'s is
  `request.md:10-15`.

Keeping `## Exit` would therefore *require* a restatement in every router, which
is criterion 18 enforced by one test and violated by another. The test changes.

### 6. The seam moves nothing except the self-review pass

Constraint 6 gives C7 the ability to move a clause into the CLI and out of the
skill because it is the only child that sees both. C7 examined the candidates
and moves none. The one real case, recorded so it is a decision rather than an
oversight:

**`stage-plan.md:28-30`, the bounded-DAG-of-stage-documents paragraph.** It
describes a store feature (`plan/<id>.md`, `README.md:906-913`), not a plugin
feature, so a Codex user driving `tcw` directly never learns it exists — which
is the usual argument for moving something into the CLI. C6's §5 assigned it to
the skill as "router mechanics". It stays, for two reasons: it is about how an
agent *routes over* a plan document, which is the router's own subject matter;
and `plan.md`'s post-pass margin is ~6 lines, so moving it would consume most of
the headroom the 40→50 raise created, for a paragraph C6 already placed. The
arithmetic permits it if the requester disagrees.

### 7. `hooks.md`: consolidate, do not rewrite

The initial request calls for `hooks.md` to be "rewritten around the roles,
kinds, and conditions C3 shipped". **It already is** — C3, C4, and C5 each
updated it as they landed (`205ea7d`, `d7802b1`, `8a8f179`). Nothing in it is
false. Restating the premise so the implementation does not go looking for drift
that is not there.

Its actual defect is duplication in two directions:

- **Against `README.md:605-735`**: the roles table, the six kinds, the `when:`
  keys, the `generate:` contract, the `serve`-runs-no-hooks caveat, and the
  trust-model sentence appear in both, in near-identical prose.
- **Against the CLI**: `hooks.md:76-118` (43 lines) restates `tcw work stage
  --help`, `tcw work scaffold --help`, and the CLI's own refusal messages.

**Target shape, ~70–90 lines**, in this order:

1. What a binding is, with the one minimal config example. (Keep.)
2. The role × kind × combination table (`hooks.md:23-32`). **Keep in full** — it
   is reference an agent reads to *write* configuration, it is not methodology,
   and it is the fastest lookup in the skill.
3. `when:` in two lines. (Keep.)
4. The three verbs — `tcw work lifecycle`, `tcw work stage`, `tcw work scaffold`
   — at roughly one line each plus the two facts an agent must know before
   running them: `tcw work stage` writes nothing, and a draft is not the
   artifact. Everything else in `hooks.md:57-118` is `--help` and refusal-message
   text and goes.
5. **The judgment layer** — the part that is genuinely skill-only and must
   survive intact: `skill:` bindings are named and never executed, and invoking
   one is `[judgment]`; a configured-but-missing skill cannot fail closed under
   Codex; `tcw serve` runs no hooks; `tcw-config.yaml` is trusted, not
   sandboxed.

**Does any of it belong in the CLI instead? One candidate, and the answer is
"recommend, do not do".** `hooks.md:150-152` ("a configured-but-missing skill
cannot fail closed everywhere") is harness-neutral operating advice a Codex user
never sees, and it is not stage-specific, so there is no prompt for it to live
in. It would belong in `tcw work lifecycle`'s output beside a reported `skill:`
binding — which is a CLI behaviour change with a capability delta and criterion
12's inertness to re-verify, and C7 is explicitly not touching `tcw/` outside
the prompts. Filed as a follow-up for C8's sweep.

### 8. `SKILL.md`

**The "Always" repoint fits by replacement, at net zero lines.** The current
bullet is two lines (`SKILL.md:53-54`); the replacement is two lines naming
`tcw work stage <id> <slug>` and keeping the `hooks.md` link (required by
`test_the_router_routes_to_every_reference_file`, `:207-212`). The body stays at
exactly 60 of 60.

Note for the implementation: `slug` is a **required** positional
(`tcw work stage [-h] [--no-exec] stage slug`), not the optional `[ref]` the
epic spec's prose implies. The bullet must show it.

**C5's open question — the stage/artifact table at `SKILL.md:29-35` — is
answered: the table stays, minus one column.**

- It cannot be collapsed. `test_the_router_routes_to_every_stage_document`
  (`:201-204`) requires each literal `stage-<id>.md` to appear in `SKILL.md`,
  and the table is the cheapest place to name seven of them.
- Its `Runs in` column is now a restatement of the CLI. `STAGE_STATUSES`
  (`base.py:781`) is enforced by `tcw work stage`, which refuses an illegal
  stage and names the statuses it does run in — so the column is exactly the
  criterion-18 defect one level up. **Drop `Runs in`.**
- C5's outcome hoped C7 would "revisit it with room to spend". There is no room:
  the repoint is net zero and the body is still 60/60. Dropping a column from a
  Markdown table saves characters, not lines. That is the answer, and it is a
  smaller answer than C5 expected.

### 9. `README.md` §605-735

**Real bounds: `README.md:605` (the `###` heading) through `:735`** ("…does not
block it from the web app"). Line 737 onward is general `tcw work` material —
transition commits, the Definition of Done, the command listing, the board, the
JSON projection, descendants — that sits under this heading only because no
further `###` appears until `:1102`. The epic plan's citation of
`README.md:587-622` is stale.

**C7 rewrites 605–735 and nothing else.** The trailing material is a pre-existing
structural defect (see `## Notes`).

The rewrite is a consolidation, not a re-argument. It must:

- Preserve the substance of C5's and C6's corrections rather than undoing them:
  C6's two edits (the "Six kinds" paragraph now saying TCW ships defaults for
  the six stages and that an unconfigured stage resolves to them, `:634-642`;
  the `tcw work stage` paragraph saying it prints TCW's own with nothing
  configured, `:684-690`) and the back-compat-break paragraph (`:676-682`); C5's
  draft-is-not-the-document paragraphs (`:698-719`).
- Say each fact once. Today the section states the trust model, the `generate:`
  contract, and the resolve-then-write rule in more than one place across its
  four accreted layers.
- Add exactly one new user-facing sentence: that TCW's shipped instructions
  include a short self-review pass at the stages where one earns its place.
- Carry **no line target.** A target on a public README section invites either
  padding or a destructive trim; the acceptance test is factual accuracy and
  single-statement, not length.

### 10. Documentation Sync

Evaluated against `CLAUDE.md`'s four entries:

- **`README.md`** [Public-API] — fires. §9 above is the work.
- **`docs/release-notes/upcoming.md`** [Public-API] — fires. One short section:
  the shipped instructions now include a self-review pass at `spec`, `plan`, and
  `implement`. Nothing else in C7 is user-visible. §161-176 already carries the
  correct `prompt: []` upgrade wording and is **not** edited.
- **`docs/changelogs/upcoming.md`** [Any-Code-Change] — fires. *Changed*: the
  shipped `spec`, `plan`, and `implement` prompts; the seven stage reference
  documents reduced to routers; `hooks.md` consolidated; `SKILL.md` repointed;
  the parity-test changes.
- **`skills/<component>/SKILL.md`** [Skill-Driven-Component] — fires; it is the
  item.

### 11. Test changes

Criterion 18's enforcement, and the structural tests that must move for the
routers to be legal. All in `tests/test_skill_lifecycle_parity.py` unless noted.

| Test | Change | Why |
| --- | --- | --- |
| `test_every_stage_document_names_the_harness_neutral_binding_command` (`:153-159`) | Assert `tcw work stage <id>` for the six; keep asserting `tcw work lifecycle` for `inbox`. | The harness-neutral command that answers "what do I do here" is now the stage verb. `tcw work stage inbox` is refused, so `inbox` must keep the old command. |
| `test_every_stage_document_has_the_five_sections_in_order` (`:127-131`) | Four sections (`Purpose`, `Inputs`, `Produce`, `Steps`) for the six; five for `inbox`. | §5: `## Exit` in a router is a restatement by construction. |
| **new** — no shared sentence | For each of the six: no normalized sentence of ≥ 8 words appears in both `stage-<id>.md` and `prompts/<id>.md`. | The literal-restatement guard, and the one that matters now that one author writes both sides in one sitting. |
| **new** — router ceiling | Each of the six ≤ 40 lines. `inbox` exempt. | The backstop: a router that restated its prompt could not fit. |
| **new** — judgment survives | Each of the six contains a delegability statement and at least one enforcement marker. | Criterion 18's second direction: a near-empty router that only names the command fails. |
| `tests/test_shipped_prompts.py` **new** | A self-review pass appears in exactly `{spec, plan, implement}` and in no other prompt. | Stops a later editor copying the pass into all six — the failure mode this design rejects by name. |

Unchanged and still passing: the produce/inputs subset checks, the marker
vocabulary check, the deleted-reference check, the `SKILL.md` 60-line budget,
the stage-document and reference-file routing checks, and every guard in
`tests/test_shipped_prompts.py` (50-line ceiling, 15-line floor, the
`tcw work lifecycle --stage` grep, the sub-skill-name grep).

## Acceptance criteria

1. Each of `stage-{request,spec,plan,implement,verify,postmortem}.md` is **≤ 40
   lines** and names `tcw work stage <id>` literally.
   `skills/tcw-work/references/stage-inbox.md` is **byte-identical** to its
   pre-C7 content — `git diff <C7's first commit>~1 -- <that path>` is empty —
   and still names `tcw work lifecycle`.
2. For each of those six, **no normalized sentence of eight or more words
   appears in both** the router and `tcw/work/prompts/<id>.md`. Normalization is
   stated in the test (lowercased, punctuation and Markdown emphasis stripped,
   whitespace collapsed). A router that copies a prompt sentence fails.
3. For each of those six, the router contains a delegability statement and at
   least one of `[auto]`/`[gated]`/`[prompted]`/`[judgment]`. A router reduced to
   a title and a command fails.
4. Each of those six has exactly the sections `Purpose`, `Inputs`, `Produce`,
   `Steps`, in that order, and **no `Exit` section**. `stage-inbox.md` keeps all
   five. The existing produce/inputs subset assertions still pass for all seven.
5. `tcw/work/prompts/{spec,plan,implement}.md` each contain a self-review pass;
   `tcw/work/prompts/{request,verify,postmortem}.md` contain none — asserted as
   **exact set equality** against `{spec, plan, implement}`, so adding a seventh
   or dropping one fails.
6. Every shipped prompt is still ≤ 50 lines and ≥ 15 non-blank lines. `spec.md`
   is ≤ 48. If any prompt exceeds 50 the item is not done; trimming existing
   prompt content to make room is a rejection, not a fix (see Risks).
7. `spec.md`'s pass checks all three of: citations re-resolving, executable
   criteria executed, and two-reading criteria pinned. `plan.md`'s existing
   re-read step covers criterion→task coverage in **both** directions and there
   is exactly one such step (not two blocks). `implement.md` states that an empty
   "what the plan or spec got wrong" is a claim.
8. `hooks.md` is ≤ 95 lines and still contains, in substance, all four judgment
   items: `skill:` bindings are never executed; a configured-but-missing skill
   cannot fail closed under Codex; `tcw serve` runs no hooks; `tcw-config.yaml`
   is trusted and not sandboxed. It retains the role × kind table.
9. `SKILL.md`'s body is ≤ 60 lines; the string `tcw work lifecycle --stage` does
   not appear in it; `tcw work stage` does; the stage/artifact table has no
   `Runs in` column; every existing routing assertion still passes.
10. `README.md`'s section between the `###` heading at `:605` and the paragraph
    ending "does not block it from the web app" states each of the following
    **in exactly one paragraph**: the trust model, the `generate:` contract,
    resolve-then-write, and the `tcw serve` caveat. (A later sentence pointing
    back at that paragraph is a cross-reference, not a second statement; a
    second paragraph explaining the same rule again is the defect.) It still
    states that TCW ships defaults for the
    six stages, that an unconfigured stage resolves to them, that `prompt: []`
    is now refused with `{blob: ""}` as the deliberate opt-out, and that a draft
    is not the document. It adds one sentence about the self-review pass. No
    line outside `605-735` is modified.
11. `docs/capabilities/work/configure-the-work-lifecycle/description.md` no
    longer asserts unconditionally that everything configured before still
    prints the same thing; it names the `prompt: []` / bare `stages.<id>: []`
    exception and the `{blob: ""}` opt-out. `Status` is still `Supported`. The
    item's `capabilities.yaml` reads `changed: [work/configure-the-work-lifecycle]`.
12. **Conditional on the requester accepting the recommendation in
    `## Capability changes`:** `work/run-a-lifecycle-stage` carries
    `Subject: work-item/lifecycle-stage`;
    `work/configure-the-work-lifecycle` carries both
    `work-item/lifecycle-stage` and `work-item/lifecycle-hook`; and the four
    lifecycle capabilities carry `Feature: configurable-work-lifecycle`. If the
    requester defers it to C8, this criterion is recorded as waived rather than
    silently dropped.
13. `tcw capabilities check`, `tcw capabilities drift`, and `tcw validate` are
    all clean, and the full pytest suite is green.
14. Release notes and changelog carry the entries named in §10, and no other
    Documentation Sync trigger fired.

## Risks

- **C7 authors both sides of the seam, which makes accidental restatement more
  likely, not less.** Writing a prompt clause and its router in the same sitting
  is exactly how the same sentence lands in both files. Criterion 2's
  shared-sentence check catches the literal form. **It cannot catch a faithful
  paraphrase**, and no test can — the epic's Verification section already
  concedes that a test "cannot assert the router's summary is faithful". The
  40-line ceiling is the backstop: a router that paraphrased its whole prompt
  would not fit. What remains uncaught is a single paraphrased paragraph inside
  budget, and the only defence is review.
- **`spec.md` has ~2 lines of margin.** If the pass cannot be written in 10
  lines, the ceiling has begun deciding the seam. The correct response is to
  escalate, not to remove existing `spec.md` content — every clause in it was
  placed by C6's §5 table against a stated rule, and quietly evicting one to fit
  a new block is how a contract stops being one.
- **Five of six routers land at 20–30 lines, well under the requested 40–50.**
  This is a deliberate departure from constraint 1 under the licence constraint 2
  grants, but it is a visible one: the routers will look thin next to what they
  replaced. The mitigation is that the ceiling is binding and the floor is not,
  so a later author can add real judgment without a test fighting them.
- **A self-review pass is process, and process that catches nothing decays into
  ritual.** The design mitigates this by refusing three stages a pass and by
  deriving `spec`'s items from two real defects — but nothing measures whether
  the pass fires again. If a future post-mortem finds a `spec` defect that
  item 1 or 2 should have caught, the finding is that the pass was not run, and
  the response is not a fourth item.
- **Version skew reads as a stale answer only if the routers stay silent about
  methodology.** That is the whole point of criterion 18, and criterion 2 is the
  only mechanical guard behind it. A router edited later to "just briefly
  explain" a step reintroduces the hazard, and the test will only catch it if
  the explanation shares a sentence with the prompt.
- **The `## Exit` removal is irreversible in review terms.** If a reader later
  wants "how does this stage end well" in the skill, it will have to be argued
  back in against a test. That is intended, and it is recorded here so the
  argument is available rather than rediscovered.

## Notes

- **`README.md`'s heading at `:605` has no closing boundary.** Everything from
  `:737` to `:1017` — transition commits, the Definition of Done, the whole
  `tcw work` command listing, the board, the JSON projection, descendants, and
  decomposition — renders inside "Binding your own skills and commands to the
  lifecycle", because the next `###` is at `:1102`. This predates the epic and
  is not C7's to fix; it is a clean C8 candidate and it is why C6's plan appeared
  to contradict itself about which lines were in scope (C6 outcome §4).
- **The epic plan's `README.md:587-622` citation for this section is stale.**
  The real bounds are `605-735`. Recorded rather than corrected in the plan,
  since the plan is the epic's artifact.
- **`hooks.md` was not drifting; it was accreting.** Three children each appended
  a correct section. Worth knowing before the implementation goes looking for
  false statements to fix — there are none.
- **Carried forward for C8**, and not addressed here: `read_artifact`'s
  `p.is_file()` (`tcw/store/fs.py:3478`) still disagrees with the canonical
  presence rule (`fs.py:2217-2221`), per C5's refined outcome; and the
  "configured-but-missing skill" note in `hooks.md:150-152`, which would be
  better served by `tcw work lifecycle` saying it than by the skill.
- **`brainstorming` was read for its Spec Self-Review checklist only**, per the
  request. One of its four items (ambiguity) is transplanted; the other three
  are declined or already present. Its procedure was not followed — it is a
  human-dialogue protocol that gates on approval, which would deadlock a
  delegated `spec` stage.
