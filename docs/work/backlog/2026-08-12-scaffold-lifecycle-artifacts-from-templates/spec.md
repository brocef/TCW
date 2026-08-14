# Spec — Scaffold lifecycle artifacts from templates

Child **C5**. The initiative's `spec.md` decides the boundaries; this decides how
C5 is built and settles the decisions it was explicitly assigned.

> Revised after a `codex` / `bllm-review` pass. Every finding was checked against
> the shipped code before being folded in; the ones that did not survive are in
> `## Notes`.

## Capability changes

Planned ledger deltas. **Declared here, written at `implement`, flipped by this
item's `complete` gate** — the pattern C4 used
(`docs/work/completed/2026-08-12-add-the-stage-entry-verb/capabilities.yaml`).

| Delta   | Capability                                    | Today                                                                 |
| ------- | --------------------------------------------- | --------------------------------------------------------------------- |
| **New** | `work/customize-lifecycle-artifact-templates`  | Absent — no such directory under `docs/capabilities/work/`             |

Verified against the ledger: `docs/capabilities/work/` holds 30 capabilities
including `configure-the-work-lifecycle`, `inspect-the-lifecycle-contract`, and
C4's `run-a-lifecycle-stage`, and **none** named
`customize-lifecycle-artifact-templates`. This item's folder has no
`capabilities.yaml` yet either; `plan` seeds one carrying the row above.

**No other capability changes.** `configure-the-work-lifecycle` already covers
declaring `work.lifecycle.artifacts:` — C3 changed it when it shipped the key —
and this item adds the verb that consumes it, which is a new capability rather
than a widening of an existing one.

**No taxonomy delta.** The Feature `configurable-work-lifecycle`
(`docs/taxonomy/configurable-work-lifecycle/`) covers this initiative, and C3
already added the Vocabulary term `work-item/lifecycle-hook`
(`docs/taxonomy/work-item/lifecycle-hook/`), which is the noun an artifact
template is. The capability's `Subject:` is that term plus
`work-item/lifecycle-stage`. A draft is a derived resource, not a new domain
noun; adding a term for it would register vocabulary nothing else needs.

## Problem

C3 shipped `resolve_artifact` (`tcw/work/resolve.py:212-239`) and the
`work.lifecycle.artifacts:` config key with its ordering validation
(`tcw/store/base.py:921-951`, `1037-1052`). **Nothing calls
`resolve_artifact` outside its own tests** — so a project can declare an artifact
template, `tcw validate` will accept it, and it will never render anything. Every
lifecycle document still starts from a blank file and whatever the agent
remembers.

The obvious command — "write the artifact from its template" — is the one the
initiative spent a whole review round rejecting. Artifact presence is what
`tcw work list` renders and what "find your place" reads; a command that wrote
`spec.md` would light `S` on the board before any spec existed, which is exactly
the defect C1 needed three verify rounds to remove for the request.

`Builtins.artifact_templates` is also still empty. C3 ships the registry
(`tcw/work/resolve.py:39-40`) and C4 passes a bare `Builtins()`
(`tcw/work/cli.py:801`), so `{builtin: true}` in an artifact list resolves to
`""` today (`tcw/work/resolve.py:155`).

## Goals

1. A command that gives you a starting point for a lifecycle document.
2. It cannot be mistaken for the document itself, by the board, by `serve`, or by
   anyone.
3. Every artifact has a template, a project can override any of them, and a
   project that configures nothing still gets one.
4. Resolve-then-write: a failed hook writes nothing and a retry is clean.
5. Nothing you have already typed is destroyed by running the command again.

## Non-goals

- Authoring the artifact. The draft is a file to type into; the agent writes the
  real document.
- Scaffolding from `tcw serve`. Decided below, against.
- Removing a draft when the artifact lands. Decided below, against.
- The stage/status legality table — **C4 owns it**, shipped at
  `tcw/store/base.py:769-777`, and C5 consumes it.
- Built-in *stage prompt* content. That is C6's half of `Builtins`.
- Changing `resolve_artifact`'s contract. C3 owns it; C5 calls it and supplies
  the fallback it does not have (Design, below).
- Concurrency control. Two simultaneous `scaffold` runs against one item are a
  stated limit, not a guarded case (Risks).

## Design

### `produces` becomes a tuple, and `--json` does not move

`LifecycleStep.produces` is a prose string today (`tcw/store/base.py:683`),
carrying `"refined-outcome.md (accepted) or rework.md (rejected)"` for `verify`
(`base.py:716`). One artifact per stage was never true — `inbox` produces none
(`base.py:695`) and `verify` produces one of two — so templates keyed by artifact
name need the names, not a sentence.

But `--json` ships that sentence under `produces` (`tcw/work/cli.py:915`) and the
human renderer prints it (`cli.py:670-671`), and C3's captured baselines assert
both byte-identical for eleven configurations —
`tests/fixtures/lifecycle_baseline/*.json` carry
`"produces": "refined-outcome.md (accepted) or rework.md (rejected)"` and
`  produces: spec.md` verbatim. Changing the key's value would break them for a
reason that has nothing to do with configuration compatibility, which is what
those baselines exist to protect.

So:

- **`LifecycleStep.produces`** becomes `tuple[str, ...]` of artifact names —
  `()`, `("spec",)`, `("refined-outcome", "rework")`.
- **`LifecycleStep.produces_note`** carries the prose, and is what
  `_lifecycle_lines` and `--json` print, under the key they always used.

The tuple is **not** added to `--json`. Nothing outside TCW needs it, and adding
a key that appears for every configuration would fail the initiative's criterion
1 for a change that is not a configuration change. If a consumer ever wants it,
that is its own item with its own reason.

**The split needs a checked invariant, not a convention.** Two fields describing
the same fact drift silently: `produces = ("refined-outcome", "rework")` beside
`produces_note = "outcome.md"` would be wrong and nothing would notice. The
invariant, asserted for every step in `LIFECYCLE_STEPS`:

> the set of `<name>.md` filenames appearing in `produces_note` equals
> `{f"{n}.md" for n in produces}`

It holds for every row today, including the empty and two-artifact cases, so it
is a real check rather than one written around the data.

**The full consumer set**, enumerated rather than assumed —
`grep -rn "\.produces\b"` over the repository finds four call sites plus the
definition:

| Site                                     | What it does                            | Moves to        |
| ---------------------------------------- | --------------------------------------- | --------------- |
| `tcw/store/base.py:683`                  | the field                               | split in two    |
| `tcw/work/cli.py:670-671`                | `produces:` line in the human render    | `produces_note` |
| `tcw/work/cli.py:915`                    | `"produces"` key in `--json`            | `produces_note` |
| `tests/test_lifecycle_hooks.py:277`      | `assert spec["produces"] == "spec.md"`  | unchanged — it asserts the JSON, which does not move |
| `tests/test_skill_lifecycle_parity.py:91`| `artifacts_in(step.produces)`           | the tuple, tightened below |

`tests/test_lifecycle_hooks.py:277` is a consumer the review's list missed. It
needs no edit, which is the point: if it did, `--json` would have moved.

### The parity test gets stronger, not weaker

`test_produce_names_every_artifact_the_table_lists`
(`tests/test_skill_lifecycle_parity.py:85-93`) regexes filenames out of the prose
with `artifacts_in()` (`:55-57`) and then asserts each one *occurs* in the
document's `Produce` section. Two weaknesses, both real: a stage document
claiming `spec` also produces `plan.md` passes today, and the tuple holds
**extensionless** names, so a naive `for artifact in step.produces` would assert
`"spec" in body` — a substring that matches `spec.md`, `specification`, and the
word "spec".

The revised test converts names to filenames and compares **exact sets**:
`artifacts_in(produce_section) == {f"{n}.md" for n in step.produces}`. That
subsumes `test_verify_names_both_of_its_outcomes` (`:114-116`), which hard-codes
what the table already says.

### `tcw work scaffold <artifact> <ref>`

`<ref>` is a **required positional**, matching what C4 shipped — `tcw work stage`
declares `pstg.add_argument("slug")` with no default (`tcw/work/cli.py:1305`) and
its capability record reads `tcw work stage <id> <ref>`. The initiative's spec
wrote `[ref]`; C4 settled the shape by shipping, and two writing verbs with
different ref rules would be a worse inconsistency than either choice.

1. Resolve the artifact name against `WORK_ARTIFACTS` (`base.py:1089-1090`);
   unknown → exit 1 naming the legal names.
2. Resolve the item; missing or ambiguous → exit 1.
3. **Refuse when the real artifact is present** — see the presence rule below.
4. **Refuse when a draft is already present**, unless `--force` — see below.
5. Check stage/status legality via C4's `STAGE_STATUSES` (`base.py:769-777`) for
   the stage that produces this artifact.
6. Resolve the template through `resolve_artifact` — first match wins, with the
   built-in fallback below.
7. Write `<artifact>.draft.md` through the store.
8. Print the draft's locator on stdout.

**Resolve fully, then write.** A hook failure means nothing was written and a
retry is clean. A write failure after successful resolution exits non-zero,
reports to stderr, and puts **nothing** on stdout — so a caller reading stdout
for a path never gets one for a file that does not exist.

**Legality reuses C4's table rather than inventing a rule.** `STAGE_STATUSES` is
keyed by stage id and every artifact except `intake` is produced by exactly one
stage, which the `produces` tuple now makes machine-readable. `intake` is
produced by no stage (it is raw input, `base.py:695` and the epic's intake
design), so it has no legality row and `scaffold intake` is legal wherever the
item is. Stated rather than left to the implementation, because a lookup that
raises `KeyError` on `intake` is the failure mode this paragraph exists to
prevent.

### One definition of "exists", and it is C1's

C1 shipped the canonical presence rule: `FsWorkStore._present` — *is a file and
has non-whitespace content* (`tcw/store/fs.py:2217-2221`) — used by `artifacts()`
(`fs.py:2246-2258`), `_resolve_body` (`fs.py:2223-2233`), and `body_path`.

The code still has a second definition: `read_artifact` returns a resource for
any existing file, `p.is_file()` (`fs.py:3478`). So "the artifact exists" has two
answers today, and a `scaffold` written against the wrong one would refuse on a
whitespace-only `spec.md` that `tcw work list` reports as absent — reproducing
the two-definitions defect C1 spent the epic's first child removing.

**`scaffold` uses the canonical presence rule**, through `artifacts()`, for both
the real artifact and the draft. Consequences, all intended:

- A whitespace-only `spec.md` does not block scaffolding, because the board says
  no spec exists. Nothing is lost: `scaffold` writes `spec.draft.md`, never
  `spec.md`.
- An **empty draft is never present**, so it is always regenerable. That is what
  makes `intake` — whose template is empty — work with no carve-out: an empty
  `intake.draft.md` can be rescaffolded, and one you have typed into cannot.

Fixing `read_artifact`'s divergence is **not** C5's job. It is a real
inconsistency and it belongs to whoever owns the read surface; C5 records it here
and does not route through it.

### A second `scaffold` does not destroy what you typed

The initiative called a draft "a file to type into" and said a retry is clean,
and said nothing about a draft that already exists. Left unsaid, the obvious
implementation truncates it — so `tcw work scaffold spec` run twice, the second
time out of habit or by a script, silently discards a half-written spec. That is
the same class of surprise as a save deleting a sibling file, which this
initiative has been removing.

**`scaffold` refuses when the draft is present**, exit non-zero, naming the
draft's locator. `--force` overwrites. Two properties fall out at no cost:

- The **retry-after-failure** case still works with no flag, because a failed
  resolution wrote nothing, so no draft is present to refuse on.
- The **empty draft** case still works with no flag, by the presence rule above.

`--force` rather than "delete it yourself" because `rm` is filesystem-only
advice: a store-abstracted tool cannot document its escape hatch as a shell
command against a path. The flag is the abstract answer, and it is one flag.

### Where a draft lives, abstractly

`<artifact>.draft.md` is a **bounded derived namespace**: exactly one draft per
`WORK_ARTIFACTS` entry, never an open folder glob. Any store can hold "the draft
of artifact N" as a named resource, and any store can be asked to create one and
refuse if it is already there.

That means it goes through a store method, not a composed path. **One method**
joins the `WorkStore` ABC beside `write_artifact` (`base.py:1468`):

```
write_draft(slug, artifact, content, *, force: bool = False) -> str   # the locator
```

It raises when a draft is present and `force` is false, and returns the locator —
the same `str` shape `artifact_locator` already returns (`base.py:1288`,
`fs.py:2260-2266`), which is what lets the CLI print a path and the documentation
describe one without either composing it. Composing
`store.path(slug) / f"{artifact}.draft.md"` in the CLI would be the same
hardcoded-filesystem-reference defect this initiative has now found three times.

**No `read_draft`.** Nothing reads a draft — the agent opens it, TCW does not —
and presence is decided inside `write_draft`, where the check and the write are
one call. An ABC method with no caller is an interface widened for a test.

The FS adapter writes through `_atomic_write` (`fs.py:715-727`), the temp-file +
`replace` helper `write_artifact` already uses (`fs.py:3512`), so a mid-write I/O
failure leaves the previous file intact rather than a truncated one. (The review
attributed this pattern to `inbox_accept`; that one swaps a whole temp *directory*
(`fs.py:2993-3005`). `_atomic_write` is the per-file helper, and it is the one to
match.)

`artifacts()` looks up `<name>.md` from the registry (`fs.py:2251-2252`) and
never sees a `.draft.md`, so presence stays honest with no new machinery — no
content hashing, no in-file marker, no adapter-visible draft state.

### Built-in templates, and the fallback C3 did not ship

A module-level map, artifact name → text, filling `Builtins.artifact_templates`.
One entry for **every** `WORK_ARTIFACTS` name, asserted as set equality.

**`intake`'s is empty**, deliberately and asserted so: intake has no prescribed
structure because it is whatever someone supplied. `tcw work scaffold intake`
therefore creates an empty `intake.draft.md` — a file to type into — rather than
refusing, so every artifact keeps the same rule with no carve-out. That is also
what replaces `tcw work new`'s old `→ edit:` hint.

**`resolve_artifact` has no implicit fallback, and `scaffold` must supply one.**
Read it: it iterates `policy.artifact(artifact)` and returns an empty
`Resolution` when that list is empty (`tcw/work/resolve.py:222-239`). `builtin`
resolves only when a binding *says* `{builtin: true}` (`resolve.py:154-155`). So
on a project that configures no `artifacts:` key at all — every project today —
`resolve_artifact` returns `""`, and a `scaffold` that trusted it would write an
empty draft for every artifact while claiming "every artifact has a template".

`scaffold` therefore treats the built-in as the fallback when **no binding won**,
distinguishable from "a binding won and resolved to empty text" by
`Resolution.plan`: no `PlanEntry` with `matched=True` means nothing won
(`resolve.py:44-56`, `226-238`). The fallback lives in the verb, not in
`resolve_artifact` — C3 owns that function, its behavior is asserted by
`tests/test_resolve.py`, and a project that binds `{blob: ""}` deliberately has
asked for an empty template and should get one.

### Decision: `tcw serve` does not offer scaffolding

The initiative asked C5 to decide, and to weigh a "safe subset" —
`blob`/`file`/`builtin` are pure text rendering, only `generate` is shell.

**Against.** `serve` runs no hooks, and that is a stated posture rather than an
oversight. A safe subset would mean the same configuration produces a draft in
the CLI and an error in the browser, for reasons a user cannot see from the
config — and the moment a project adds one `generate:` template, the button they
have been using stops working. A capability that silently depends on which kinds
someone happened to configure is worse than one that is absent.

The web app already shows every present artifact and lets you edit it. Creating
one from a template is a CLI operation.

**`serve` must also stay unaware that drafts exist**, on every surface and not
only the two the earlier criteria named. It has four artifact routes and all four
gate on the registry — `name not in WORK_ARTIFACTS` at
`tcw/serve/__init__.py:515` (GET one), `:1144` (PUT), `:1321` (DELETE) — and the
detail response builds its artifact list by iterating `WORK_ARTIFACTS` (`:659`).
A draft is not a registry name, so it is already unreachable through every one of
them. That makes this a **regression criterion rather than a design change**: the
property holds today and must survive C5.

### Decision: landing an artifact does not remove its draft

**Against**, for two reasons. `write_artifact` deleting a sibling file is a side
effect nobody asked that method for, and it would fire from `serve`'s editor too
(`serve/__init__.py:1144` onward) — a save in the browser silently deleting a
file is the kind of surprise this initiative has been removing, not adding.

The staleness the initiative worried about is real: `spec.draft.md` can sit
beside `spec.md` disagreeing with it. The protection is step 3 — `scaffold`
refuses once the real artifact is present, so a draft can never be *regenerated*
into confusion — plus the name itself, which says what it is. Cleaning up is the
user's call, and a tool that deletes your files to tidy up is a worse trade.

### Documentation this child owns

The epic plan makes each child update its own docs before C7 consolidates
(`plan.md`, "Every child owns its own documentation"). C5's share, each with a
criterion below:

- **`README.md`** — the `scaffold` line in the work command block
  (`README.md:764-773`, beside C4's `tcw work stage` lines) and the drafts
  paragraph in §"Reading a stage's instructions" (`README.md:676`).
  C7 owns the §"Binding your own skills and commands to the lifecycle" rewrite;
  C5 does not touch it.
- **`docs/release-notes/upcoming.md`** — what a draft is and why it is not the
  document, in plain language.
- **`docs/changelogs/upcoming.md`** — the `produces`/`produces_note` split,
  `write_draft`, the template registry, and the new verb.
- **`skills/tcw-work/references/commands.md:26`** — the row beside `tcw work
  stage`. **`references/hooks.md:79-93`** — how an `artifacts:` binding is
  reached, which is currently documented with no verb that reaches it.

## Acceptance criteria

The initiative's criteria 11 and 17 are the requirement. Each below is checkable
by someone else without asking what it meant.

1. **`tcw work scaffold spec <ref>` writes `spec.draft.md` with exactly the
   resolved content**, byte-for-byte — not "contains the template" — and prints
   that draft's locator on stdout and nothing else.
2. **It does not create the real artifact, for any artifact**: parametrized over
   every `WORK_ARTIFACTS` name, after `scaffold <name>` the file `<name>.md` is
   absent and `tcw work list` shows the **same string** for that item as before
   the command ran. An implementation that writes nothing fails criterion 1; one
   that writes `<name>.md` fails this.
3. **It refuses when the real artifact is present**, exit non-zero, naming the
   file, **and** it does **not** refuse when the artifact file exists but holds
   only whitespace — because `artifacts()` reports that item as absent
   (`fs.py:2217-2221`). Both directions tested, so an implementation using
   `.exists()` fails.
4. **It refuses when a draft is present**, exit non-zero, naming the draft's
   locator, and leaves the existing draft **byte-identical**. `--force`
   overwrites. A draft that exists but is empty does **not** trigger the refusal.
5. **A built-in template exists for every `WORK_ARTIFACTS` name**, asserted as
   **exact set equality** rather than "at least one", and each has exactly one
   definition in the codebase.
6. **`intake`'s built-in template is empty**, asserted explicitly so nobody
   helpfully adds headings later, and `tcw work scaffold intake` creates an empty
   `intake.draft.md` rather than refusing.
7. **With nothing configured, every artifact scaffolds to its built-in** —
   parametrized over all of `WORK_ARTIFACTS` against a node with no
   `work.lifecycle.artifacts:` key, each draft byte-equal to its built-in entry.
   This is the criterion an implementation trusting `resolve_artifact`'s empty
   return fails (`resolve.py:222-239`).
8. **Resolve-then-write, on every failing kind**: with a `generate` template that
   exits non-zero, one that exceeds the timeout, and one that exceeds the output
   cap, **and** with a `file` template pointing at a deleted path, no draft is
   written and a retry after fixing it succeeds. With an unwritable target, exit
   non-zero, message on stderr, **nothing on stdout**.
9. **The draft goes through the store**: `write_draft` is declared on the
   `WorkStore` ABC, the CLI module contains no `.draft.md` literal and no
   `store.path(...)`-composed draft path, and a monkeypatched `write_draft`
   records the call — so an implementation writing beside the store fails.
10. **`produces` is a tuple for every step**, `verify`'s is exactly
    `("refined-outcome", "rework")`, and the union over all steps equals the set
    of artifact names any stage produces.
11. **`produces` and `produces_note` agree for every step**: the `<name>.md`
    filenames found in `produces_note` equal `{f"{n}.md" for n in produces}`,
    asserted per step over `LIFECYCLE_STEPS`, including `inbox`'s empty pair.
12. **C3's lifecycle baselines still pass, unmodified** — all eleven fixtures in
    `tests/fixtures/lifecycle_baseline/`, proving neither the `--json` payload
    nor the human render moved. `tests/test_lifecycle_hooks.py:277` also passes
    unmodified.
13. **The parity test compares exact sets**: for every stage,
    `artifacts_in(Produce section) == {f"{n}.md" for n in step.produces}`. A
    stage document naming an extra artifact fails it, which it does not today,
    and the extensionless tuple names are converted rather than substring-matched.
14. **No surface reports a draft as an artifact**: with **every** draft present
    and no real artifact, `tcw work list`'s string is unchanged, `artifacts()`
    reports all absent, `tcw work show --json`'s `artifacts` map is all `false`,
    and `serve`'s detail response (`serve/__init__.py:659`) lists none of them as
    present. All four surfaces, not two.
15. **Legality is checked before anything is written**, using `STAGE_STATUSES`:
    `scaffold outcome` on a `backlog` item exits non-zero having written nothing,
    and `scaffold intake` — whose artifact no stage produces — succeeds in every
    status rather than raising.
16. **A project template overrides the built-in, and conditions select**: one
    `blob` template `when: {tags: [bug]}` above a `builtin` fallback, checked
    both ways — a tagged item gets the blob, an untagged one the built-in.
17. **`README.md`, `docs/release-notes/upcoming.md`,
    `docs/changelogs/upcoming.md`, `skills/tcw-work/references/commands.md`, and
    `skills/tcw-work/references/hooks.md` each document `tcw work scaffold`**,
    including `--force` and the draft-versus-artifact distinction. A test asserts
    the command name appears in the README command block and in `commands.md`,
    the same guard `tcw work stage` has.
18. **The capability `work/customize-lifecycle-artifact-templates` is declared in
    this item's `capabilities.yaml` as `new`, written to the ledger during
    `implement`, and flipped by `complete`** — `tcw capabilities check` and
    `tcw capabilities drift` clean afterwards.

## Risks

- **A draft that disagrees with its artifact is clutter.** Accepted, with
  `scaffold`'s two refusals as the guard rather than deletion.
- **`write_draft` widens the store interface** by one method for one command.
  Justified by the litmus test — the alternative is a composed path — and the
  namespace is bounded to one draft per registered artifact.
- **Two simultaneous `scaffold` runs race.** The presence check and the write are
  separate operations, so the loser's content wins and the refusal can be
  skipped. Accepted as a stated limit rather than guarded: `_atomic_write` makes
  the file itself never torn (`fs.py:715-727`), the blast radius is one draft in
  one work item, and locking a store that may be a remote tracker is a far larger
  design than the failure justifies.
- **`generate` templates re-run on retry.** Inherited from the initiative's
  resolve-then-write decision, unchanged here: a failed write discards resolved
  output, so the next attempt re-executes the generator. `--force` re-executes it
  too. Generators must be side-effect-free, and the README must say so.
- **The `--json` decision defers a real question.** A consumer that wants the
  artifact names machine-readably has no way to get them. That is a smaller
  problem than breaking a compatibility baseline for a non-compatibility reason,
  and it is one item away from being fixed.
- **`read_artifact` still disagrees with the presence rule** (`fs.py:3478` vs
  `fs.py:2217-2221`). C5 routes around it rather than fixing it, so the
  inconsistency outlives this item. Worth a backlog entry at C8.

## Notes

### Reviewed and rejected

Findings from the pre-implementation `codex` / `bllm-review` pass that did not
survive verification, kept so the reasoning is not re-derived.

- **"Test `write_draft` on all supported store backends."** There is exactly one
  — `grep "WorkStore)"` finds only `class FsWorkStore(FsTreeStore, WorkStore)`
  (`fs.py:1956`) — and "Building a remote store adapter" is an explicit
  initiative non-goal. A parametrized backend test would have one parameter.
- **"`generate` hooks need environment isolation and a clean temp dir."** C3 owns
  and settled the hook contract: `tcw/work/generate.py` runs the command in its
  own process group with bounded drains, a timeout, an output cap, and all stdout
  discarded on non-zero exit, reached only through `resolve.py:162-173`.
  Re-litigating it in the verb that calls it would give the contract two owners.
- **"`--json` mechanism underspecified."** The same ground as the
  `produces`/`produces_note` finding, which is accepted above as criterion 11.
  Recorded as one finding rather than two.
- **"Every one of the twelve criteria is escapable."** Partly true and acted on
  where it was: the criteria testing one artifact where the rule is universal
  (old 1, 5, 11) are now parametrized over `WORK_ARTIFACTS` (new 2, 7, 16); the
  ones testing one surface where the property spans several (old 2, 10) now name
  all four (new 2, 14); the resolve-then-write criterion now covers four failure
  kinds rather than one (new 8). The claim that criteria 8 and 9 "hard-code an
  expected value both sides can be wrong about together" does **not** hold:
  `verify`'s tuple and the eleven captured baselines are compared against data
  the change is not allowed to touch, which is the only way a compatibility
  assertion can work.
- **"Criterion 12 claims a declaration that does not exist."** True as stated,
  but it is not a defect in the criterion — the spec was missing its
  `## Capability changes` section entirely, and a delta planned there is *meant*
  to be absent from the ledger until `implement` writes it. Fixed by adding the
  section and restating the criterion (18) as the work rather than as a fact.
