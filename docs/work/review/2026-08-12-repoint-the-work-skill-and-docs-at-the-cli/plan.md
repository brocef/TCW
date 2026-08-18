# Plan — Repoint the work skill and docs at the CLI

Eight tasks, linear. Every task is one commit except task 8, which writes
nothing. The suite is green at each of the seven commit boundaries, and
§Ordering says why the tests travel *with* the documents they govern rather
than ahead of them.

## Ordering

Three constraints fix this order; nothing else about it is discretionary.

1. **A test change that lands before the document it governs is a red tree.**
   Every parity assertion this item touches is parametrized over the stage ids.
   Changing `test_every_stage_document_has_the_five_sections_in_order` to demand
   four sections while six routers still carry five is red; so is adding the ≤40
   ceiling before the routers are reduced. There is no ordering of "tests first"
   that is green, so **each test change is committed with the documents it
   governs** — the prompt test in task 1, the four router tests in task 2.
2. **Prompts before routers.** Criterion 2 compares each router against its
   prompt. If the routers landed first, task 1 could reintroduce a sentence a
   router already carries and the shared-sentence test would only notice on the
   later commit, in a diff that does not contain the router. Editing the fixed
   side first means the routers are written against text that no longer moves.
3. **The Documentation Sync block last**, per `CLAUDE.md` and `stage-plan.md`
   step 4 — one pass over the finished diff, after the code and skill tasks.
   The capability work (tasks 6–7) follows it, as in C6's plan.

## Tasks

### 1. The self-review pass in three shipped prompts

`tcw/work/prompts/{spec,plan,implement}.md`, plus one new test in
`tests/test_shipped_prompts.py`. The other three prompts are not opened.

**The detection token.** Criterion 5 asserts exact set equality, so "a
self-review pass" has to be mechanically visible in all three files and absent
from the other three. `spec.md` gets a heading; `plan.md` and `implement.md`
fold theirs into existing steps and so have no heading to find. The token is
therefore the literal string **`self-review`** (case-insensitive), written as
the `## Self-review` heading in `spec.md` and as a bold `**Self-review.**` lead
on the edited step in the other two. One word, one grep, and it names the thing
for the reader as well as for the test.

**`spec.md` — a new block, hard budget 8 lines.** Three items, from spec §2: a
`file:line` citation re-resolves to what the spec claims it shows; every
acceptance criterion executable against the tree today has been executed and any
that fails is reworded or dropped; a criterion two readers could check two ways
is pinned to one reading. Draft the three items **first**, one line each, then
add the heading and the blank line around it, then measure — that order is what
keeps it at 6–8 lines. `spec.md` is 40 lines today, so 8 lands it at 48.

> **Budget and escalation.** Spec §4 gives the block a hard budget of 10 lines
> while criterion 6 caps `spec.md` at 48 lines — from a 40-line file those are 10
> and 8, and **the operative number is 8**, the tighter of the two. If the three
> items cannot be written in 8 lines: **stop, and report to the requester**
> before any further edit. The report names which item does not fit and offers
> the three choices that are theirs and not the implementation's — raise the
> 50-line ceiling again, accept `spec.md` above 48, or drop an item. Removing or
> compressing existing `spec.md` content to make room is a rejection, not a fix
> (spec §Risks): every clause in it was placed by C6's §5 table against a stated
> rule. Do not proceed to task 2 with an unescalated overflow.

**`plan.md` — rewrite step 6, add no block.** It reads "Re-read the finished plan
against the spec: coverage gaps, inconsistent names, tasks that appear twice".
It gains the coverage direction it half-states — every acceptance criterion is
covered by at least one task **and** every task traces back to one — and the
`**Self-review.**` lead. It stays **one** step; criterion 7 fails on two.

**`implement.md` — one line.** Fold into step 9 (`Write outcome.md and commit
it.`): an empty "what the plan or spec got wrong" section is a claim, not an
omission. Carries the token.

**The test**, in `tests/test_shipped_prompts.py` beside the existing greps:

```python
def test_the_self_review_pass_appears_in_exactly_three_prompts():
    prompts = load_builtins().stage_prompts
    found = {sid for sid, text in prompts.items() if "self-review" in text.lower()}
    assert found == {"spec", "plan", "implement"}
```

Set equality, so copying the pass into `verify` fails and dropping it from
`plan` fails — the failure mode spec §2 rejects by name.

**Checks before commit:** the full suite, plus
`wc -l tcw/work/prompts/*.md` — `spec.md` ≤ 48, all six ≤ 50. The existing
ceiling/floor/`--stage`/sub-skill-name guards must pass untouched; the pass may
not name `tcw-verifier`, `documentation-sync`, or `tcw-capabilities`.

— criteria 5, 6, 7

### 2. Six routers, and the four tests that bound them

The item's largest task: `skills/tcw-work/references/stage-{request,spec,plan,implement,verify,postmortem}.md`
reduced against spec §5's per-router table, plus two changed and three new
assertions in `tests/test_skill_lifecycle_parity.py`.
**`stage-inbox.md` is not opened.**

**One commit, not six.** The four router tests are parametrized over the same six
ids: the moment `STAGE_SECTIONS` becomes four-for-six, every unreduced router
fails, and the ceiling and shared-sentence tests do the same. A per-document
commit would be red at five of six boundaries, and green-at-every-boundary is
the binding constraint here. C6's precedent (six prompt files, one commit,
because a set-equality assertion spanned them) is the same reason; C5 split its
two-part change because its halves were governed by *different* tests, which is
not the case here.

**What each router keeps** — spec §5, not re-derived:

| Router | Keeps | Expected |
| --- | --- | --- |
| `stage-request.md` | not delegable and why; the epic's coordination goal | ~22 |
| `stage-spec.md` | delegability with `Inputs` as brief / `Produce` as return contract; the epic's Design→child-boundaries substitution; routes to `decompose.md`, `epic-deltas.md`; `tcw-capabilities` | ~28 |
| `stage-plan.md` | delegability; the epic coordination-plan variant → `epic-deltas.md`; `documentation-sync`; the bounded-DAG paragraph; `--blocked-by` as `[gated]` | ~30 |
| `stage-implement.md` | delegability and that this is where it pays → `delegation.md`; `tcw-capabilities` and `documentation-sync`; `tcw work start` as `[gated]` | ~26 |
| `stage-verify.md` | the assess/decide split; `tcw-verifier` and the Claude/Codex difference → `delegation.md`; the stop as user `[judgment]`; `tcw-capabilities`; the version-cut mechanics | ~38 |
| `stage-postmortem.md` | delegability to a read-only subagent; the `tcw-post-mortem` agent under Claude | ~22 |

**Shape**, from the structural floor: title, the route line naming
`tcw work stage <id> <slug>`, `## Purpose`, `## Inputs`, `## Produce`,
`## Steps`, and no `## Exit`.

**Write `Inputs` and `Produce` as bare artifact names, not prose sentences.**
This is spec §1's "naming is addressing, restating is instruction" made
mechanical: `outcome.md — plus the code itself` is a name; "`outcome.md`, in the
item's folder, plus the code itself" is an eleven-word sentence one edit away
from the prompt's own. Bare names also stay under the eight-word threshold by
construction, so the shared-sentence test never has to adjudicate them. The
existing subset assertions still require every name in `step.produces` /
`step.inputs` to appear — `postmortem`'s `Inputs` carries all six.

**Per document, in this order** (this is what makes criterion 2 fail early
rather than on the sixth file):

1. Grep the corresponding prompt for each `## Exit` **Badly** branch before
   deleting it. Spec §5 verified all eighteen already; this re-confirms per file
   so the deletion is checked rather than trusted.
2. Write the router.
3. Run `pytest tests/test_skill_lifecycle_parity.py -k <stage-id>` immediately.
   Every one of the four new/changed assertions is parametrized by stage id, so
   this run is a complete verdict on the document just written — including the
   shared-sentence check against a prompt that task 1 already froze. Fix before
   moving to the next document.

**The test changes**, all in `tests/test_skill_lifecycle_parity.py`:

- `test_every_stage_document_names_the_harness_neutral_binding_command`
  (`:153-159`) — assert `f"tcw work stage {stage_id}"` for the six; keep
  `"tcw work lifecycle"` for `inbox`, which the verb refuses.
- `test_every_stage_document_has_the_five_sections_in_order` (`:127-131`) —
  `("Purpose", "Inputs", "Produce", "Steps")` for the six, the existing
  five-tuple for `inbox`. Rename to `…_the_sections_in_order`; keep
  `STAGE_SECTIONS` as `inbox`'s tuple and derive the router tuple from it by
  dropping `Exit`, so the two cannot drift apart.
- **new** `test_no_router_sentence_appears_in_its_prompt` — parametrized over the
  six. Normalization, stated in the test's docstring because criterion 2
  requires it: lowercase; strip Markdown emphasis (`*`, `_`, backticks) and all
  punctuation; collapse whitespace; split on `.`/`!`/`?` and line boundaries;
  keep sentences of ≥ 8 words. Assert the intersection is empty, and **put the
  offending sentence in the assertion message** — the fix may be in either file
  and the message is what says which sentence to look for.
- **new** `test_each_router_stays_within_its_ceiling` — ≤ 40 lines for the six;
  `inbox` exempt.
- **new** `test_each_router_keeps_its_judgment` — each of the six contains a
  delegability statement (`delegable` / `not delegable`, matched
  case-insensitively) and at least one of the four `MARKERS`. Criterion 18's
  second direction: a router reduced to a title and a command fails.

Unchanged and still passing: the produce/inputs subset checks, the marker
vocabulary check, the deleted-reference check, `test_a_stage_producing_nothing_says_so_explicitly`,
the `SKILL.md` budget, and both routing checks.

**Corrected at `implement`:** one more guard, and it is in a different file —
`tests/test_documentation_sync_wiring.py:76-82` requires the literal phrase
``invoke the `documentation-sync` skill`` in `stage-plan.md` and
`stage-implement.md`. Neither this list nor spec §11 named it, and the first
drafts of those two routers failed it. The phrase stays in both routers; the
guard is not touched.

**Checks before commit:** full suite, `wc -l` over the six (each ≤ 40), and
`git diff --stat -- skills/tcw-work/references/stage-inbox.md` empty.

— criteria 1, 2, 3, 4

### 3. `SKILL.md`'s "Always" repoint and the dropped column

`skills/tcw-work/SKILL.md`. Two edits, net zero lines — the body is at 60 of 60
and the rule on breach is extract, never grow.

- `SKILL.md:53-54` — replace the `tcw work lifecycle --stage <id>` bullet with
  two lines naming **`tcw work stage <id> <slug>`** (`slug` is a required
  positional, not an optional `[ref]`) and keeping the `hooks.md` link that
  `test_the_router_routes_to_every_reference_file` requires.
- The stage/artifact table (`:27-35`) — drop the **`Runs in`** column. It
  restates `STAGE_STATUSES` (`base.py:781`), which `tcw work stage` enforces and
  names in its own refusal. The table itself stays: it is where seven literal
  `stage-<id>.md` filenames live, and `test_the_router_routes_to_every_stage_document`
  requires them.

**Checks before commit:** full suite (the 60-line budget and both routing tests
are the mechanical half of criterion 9), plus
`grep -c 'tcw work lifecycle --stage' skills/tcw-work/SKILL.md` → 0 and
`grep -c 'tcw work stage' skills/tcw-work/SKILL.md` → ≥ 1, and `Runs in` absent.

— criterion 9

### 4. `hooks.md`: consolidate to ≤ 95 lines

`skills/tcw-work/references/hooks.md`, 159 → ≤ 95. Nothing in it is false (spec
§7) — this is deletion of duplication, not correction. Target shape, in order:
what a binding is with the one minimal config example; the role × kind ×
combination table (`:23-32`) **kept in full**; `when:` in two lines; the three
verbs at roughly a line each plus the two facts that are not in `--help`
(`tcw work stage` writes nothing; a draft is not the artifact); the judgment
layer. `hooks.md:57-118`'s `--help` and refusal-message text is what goes, along
with the prose that duplicates `README.md:605-735`.

**Verified, not eyeballed.** No test governs this file, so the check is a
command whose output goes into `outcome.md`:

```bash
wc -l skills/tcw-work/references/hooks.md
for s in 'never executed' 'fail closed' 'runs no hooks' 'not a sandbox' \
         '| `check`' '| `prompt`' '| `artifact`'; do
  printf '%-20s %s\n' "$s" "$(grep -c -- "$s" skills/tcw-work/references/hooks.md)"
done
```

Line count ≤ 95 and every count ≥ 1 — the four judgment items and the three
table rows. Anchor strings, not proof of substance: the "in substance" half of
criterion 8 is in §Verification. Also `git diff` the file once and confirm every
deleted line is either duplicated in `README.md:605-735` or reproduced by
`tcw work stage --help` / `tcw work scaffold --help`; a deletion that is neither
is content, and content does not go.

— criterion 8

### 5. Documentation Sync

All four `CLAUDE.md` entries evaluated at plan time; **all four fire**, and one
is discharged by tasks 2–4 rather than by a doc task. One pass over the finished
diff, one commit.

- **`README.md` [Public-API]** — fires. Rewrite the section between the `###`
  heading at `:605` and the paragraph ending "does not block it from the web
  app" (`:735`), and nothing else; line 737 onward is general `tcw work`
  material that renders under this heading only because the next `###` is at
  `:1102` (spec §Notes — a C8 candidate, not C7's). The rewrite is a
  consolidation, so: preserve C6's two corrections (`:634-642`, `:684-690`) and
  the back-compat-break paragraph (`:676-682`), and C5's draft-is-not-the-document
  paragraphs (`:698-719`); say the trust model, the `generate:` contract,
  resolve-then-write, and the `tcw serve` caveat **once each**; add exactly one
  new sentence — that TCW's shipped instructions include a short self-review
  pass at the stages where one earns its place. **No line target**: the
  acceptance test is factual accuracy and single-statement, and a target on a
  README section invites padding or a destructive trim.
- **`docs/release-notes/upcoming.md` [Public-API]** — fires. One short section in
  plain language: the instructions TCW prints now include a brief self-review
  pass at `spec`, `plan`, and `implement`, and why those three. Nothing else in
  C7 is user-visible. **`:161-176` is not edited** — it already carries the
  correct `prompt: []` wording.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — fires. *Changed*: the
  shipped `spec`, `plan`, and `implement` prompts gain a self-review pass; the
  six stage reference documents reduced to routers (`inbox` unchanged);
  `hooks.md` consolidated; `SKILL.md` repointed at `tcw work stage` and the
  `Runs in` column dropped; the parity-test changes and the new prompt test.
- **`skills/<component>/SKILL.md` [Skill-Driven-Component]** — fires, and is
  **already discharged by tasks 2, 3, and 4**: the skill is the item. Recorded
  here so the entry is evaluated rather than skipped, and so it is not
  double-counted as a second edit at the end.

No version-bearing file is touched and no version is cut; the version options
belong to `verify`, after `tcw work complete` (`CLAUDE.md` §Versioning).

— criteria 10, 14

### 6. The capability record's one false line

`docs/capabilities/work/configure-the-work-lifecycle/description.md`, line 6:

> **Everything I configured before this still works and still prints the same
> thing.** A stage id with a plain list under it means what it always meant.

Both halves are false for exactly one plain list — the empty one (C6 spec §3a,
`base.py:_parse_stage`). Replace with wording that keeps the true part and names
the exception, taken from `docs/release-notes/upcoming.md:161-176` rather than
invented: nearly all of it still works, a bare `stages.<id>: []` and `prompt: []`
are now refused by `tcw validate`, and `{blob: ""}` is the deliberate opt-out.

**Prose only.** `tcw capabilities set` does not write description bodies, so this
is a file edit followed by `tcw capabilities check`. `Status` stays `Supported`;
no field changes here. The item's `capabilities.yaml` — seeded at this stage —
reads `changed: [work/configure-the-work-lifecycle]`.

The four other tree hits for that sentence (C6's `outcome.md:180` and
`refined-outcome.md:62`, the epic's `plan.md:179`, this item's `spec.md`) are
archives quoting it to name the contradiction. They are true historical
statements and are **not** edited.

— criterion 11

### 7. The four linkage fixes

Fields, not prose — a different change from task 6 and a separate commit. Four
`tcw capabilities set` calls (`--field` is repeatable; `Subject` takes a
comma-separated list):

```bash
tcw capabilities set work/run-a-lifecycle-stage \
    --field Subject=work-item/lifecycle-stage \
    --field Feature=configurable-work-lifecycle
tcw capabilities set work/configure-the-work-lifecycle \
    --field Subject=work-item/lifecycle-stage,work-item/lifecycle-hook \
    --field Feature=configurable-work-lifecycle
tcw capabilities set work/inspect-the-lifecycle-contract \
    --field Feature=configurable-work-lifecycle
tcw capabilities set work/customize-lifecycle-artifact-templates \
    --field Feature=configurable-work-lifecycle
```

`Feature: configurable-work-lifecycle` matches the spelling every other linked
`work/` record uses (`work/reconcile-an-epic-rollup/meta.yaml`), and the Feature
exists in the local taxonomy. No `Status` moves and no description changes.
Commit the resulting `meta.yaml` files.

— criterion 12

### 8. Whole-tree checks

No edits. Run and record the output in `outcome.md`:

```bash
pytest -q
tcw capabilities check
tcw capabilities drift
tcw validate
git diff <task-1-commit>~1 -- skills/tcw-work/references/stage-inbox.md   # empty
```

The last one is criterion 1's byte-identity clause, checked at the end because
any of tasks 2–5 could have touched the file.

— criterion 13, and criterion 1's `inbox` clause

## Verification

What the suite cannot check, and someone has to read:

- **A faithful paraphrase inside 40 lines.** Criterion 2 catches a copied
  sentence; nothing catches a router that restates its prompt in different
  words, and the epic's own Verification section already concedes this. C7
  writes both sides in one sitting, which makes it *more* likely, not less. Read
  each router beside its prompt with spec §5's table open and ask of every line:
  is this addressing, or is it instruction?
- **The README section says each fact once** (criterion 10). "In exactly one
  paragraph" is a reading, not a grep. Read `605-735` top to bottom in the
  rewritten file and check the four named facts — trust model, `generate:`
  contract, resolve-then-write, `tcw serve` caveat — appear once each, with any
  later mention being a pointer rather than a restatement. Then confirm the five
  preserved claims survive (defaults for six stages, unconfigured resolves to
  them, `prompt: []` refused, `{blob: ""}` opt-out, a draft is not the document)
  and that exactly one new sentence was added.
- **No line outside `605-735` moved.** `git diff -U0 -- README.md` and read the
  hunk headers: the first changed line is ≥ 605 and nothing after the "does not
  block it from the web app" paragraph appears.
- **`hooks.md`'s four judgment items survive *in substance*** (criterion 8). The
  greps in task 4 prove a string is present, not that the point is intact. Read
  the four in the rewritten file.
- **The seam actually works end to end.** After task 3, follow `SKILL.md` as a
  reader with no prior context: it must lead to `tcw work stage <id> <slug>`,
  and running that on this repo — which configures no `work.lifecycle` key —
  must print the built-in for each of the six stages. That is the whole item's
  premise and no test asserts the reading path.
- **Green at every commit boundary, not just the last.** Run the full suite at
  each of the seven commits. Task 2 is the one that can fail late; task 1's
  prompt edits are what its shared-sentence check compares against.
- **The `## Exit` removal is one-directional.** Arguing "how does this stage end
  well" back into a router later means arguing against a test. That is intended
  (spec §Risks) and is recorded here so the argument is available rather than
  rediscovered.

## Notes

- **Task 1's escalation is a stop, not a judgment call.** It is called out as a
  blockquote rather than a bullet because the tempting local fix — evicting one
  clause of `spec.md` to fit the block — is exactly the failure the 40→50 raise
  (`ab86012`) existed to prevent, and it would silently rewrite a contract C6
  agreed with the requester.
- **The 8-vs-10 line budget.** Spec §4 says "hard budget of 10 lines" and
  criterion 6 says `spec.md` ≤ 48; from a 40-line file those are different
  numbers. The plan takes 8, the tighter one, so the acceptance criterion is
  what binds. Anything above 8 goes to the requester either way, so the two
  readings converge on the same action.
- **Five of six routers land well under 40** (spec §5, and the requester's
  amendment to a ceiling with no floor). They will look thin next to what they
  replaced; padding them to look substantial is the one outcome constraint 2
  names as worse than a long document.
- **Two follow-ups carried to C8, not addressed here** (spec §Notes): the
  `hooks.md:150-152` "configured-but-missing skill" note, which would be better
  said by `tcw work lifecycle` than by the skill but is a CLI change; and
  `README.md`'s heading at `:605` having no closing boundary.
