# Plan: ask the requester for reference material during the request stage

Three independent document edits, then the documentation block. Nothing under
`tcw/` is touched, so there is no infrastructure to build first and no risky
change to isolate. The ordering below is by document, smallest blast radius last;
the suite is green at every boundary because each task edits one file that only
`tests/test_skill_lifecycle_parity.py` constrains.

The standing guard to respect throughout: that test requires each stage document
to keep the five sections `Purpose · Inputs · Produce · Steps · Exit` **in order**
(`:121-125`), every `Steps` block to carry a recognized marker from
`[auto] [gated] [prompted] [judgment]` (`:128-144`), and `Inputs`/`Produce` to
keep naming the artifacts `LIFECYCLE_STEPS` lists (`:85-104`). So `## References`
is described *inside* `Produce` — it is a section of `initial-request.md`, never a
new heading in the stage document.

## Tasks

### 1. `stage-request.md` — produce and solicit `## References`

**Changes** `skills/tcw-work/references/stage-request.md`:

- `Produce` (after the existing `Optional ## Notes` line, ~`:26`): add the
  optional `## References` section — a link, repo path, or work-item reference per
  entry, each with a one-line note on why it matters, and the reason for the
  annotation (a bare URL list saves the `spec` stage nothing).
- `Steps`: insert the new step between the current step 2 ("Ask the user what is
  unclear", `:32-34`) and step 3 ("Write the request in the requester's terms",
  `:35-37`), renumbering 3–5 → 4–6. The step must state: what to ask for (docs,
  spec, issue, prior art, in-repo file, related item); capture-only — no fetching,
  validating, or summarizing; links are context for `spec`, not directives it must
  accept; and the empty case goes in `## Notes` as "asked; none provided". Marker
  `— agent [judgment]`.
- `Exit` / **Well** (`:44-45`): amend the bar to "…without re-interviewing anyone
  or re-finding the requester's sources."

**Verified by** `pytest tests/test_skill_lifecycle_parity.py` (sections still in
order, new step marked, no unknown marker, `Produce` still names
`initial-request.md`) plus a read-through against acceptance criteria 1–3: the
step is between the two named steps, and all three clauses are present.

Budget check while editing: the document is 56 lines today and the spec allots
roughly six more. If the edit runs materially past that, the wording is too long
for a document loaded on every planning run — tighten rather than accept it.

### 2. `stage-spec.md` — consume the section

**Changes** `skills/tcw-work/references/stage-spec.md`:

- `Inputs` (`:9-14`): `initial-request.md`, **including its `## References`
  section when present — the starting set for research, not the limit of it.**
  The literal string `initial-request.md` must survive.
- Step 3 (`:38-39`, "Read the code the change touches"): add a leading clause to
  read the request's references before hunting for sources independently.

**Verified by** `pytest tests/test_skill_lifecycle_parity.py` —
`test_inputs_names_every_artifact_the_table_lists` (`:96-104`) is the specific
guard on the `Inputs` rewording, since it checks against
`LIFECYCLE_STEPS[spec].inputs = ("initial-request.md",)`
(`tcw/store/base.py:602-605`). Plus acceptance criteria 4–5 by reading.

### 3. `stage-inbox.md` — carry existing links through

**Changes** `skills/tcw-work/references/stage-inbox.md`, step 6 (`:44`, the
`tcw work edit` step): add the carry-through clause — if the entry carried links
or attachments, make sure they survived into the item's `## References` rather
than staying buried in pasted text; do **not** prompt for more here, because the
requester (a GitHub issue reporter, another node) is usually not present, and the
`request` stage is what asks.

`Produce` stays "**No lifecycle artifact**" — unchanged, and
`test_a_stage_producing_nothing_says_so_explicitly` (`:107-111`) depends on that
exact phrase.

**Verified by** `pytest tests/test_skill_lifecycle_parity.py` plus acceptance
criterion 6 by reading.

### 4. Full verification pass

- `pytest` (whole suite) — acceptance criterion 8.
- `tcw validate` — acceptance criterion 9.
- `git diff --stat` shows no file under `tcw/` — acceptance criterion 7. This is
  a criterion precisely because the harness rule creates a standing pull toward
  putting guarantees in the CLI; the spec argues against it, so the diff should
  show the argument was followed.

## Documentation Sync block (one block, after the code tasks)

Evaluated with the `documentation-sync` skill against the four entries in
`CLAUDE.md`:

### 5. `docs/changelogs/upcoming.md` — trigger fires

`[Any-Code-Change]`. Add under **Changed**: the three stage documents and what
each gained; name the new optional `## References` section of
`initial-request.md`; state explicitly that no CLI or `LIFECYCLE_STEPS` change
was needed and why (`inputs` are artifact filenames, not sections).

### 6. `docs/release-notes/upcoming.md` — trigger fires

`[Public-API]` — user-facing behavior changes: planning now asks the user a
question it did not ask before. One plain-language entry: when TCW plans a work
item it now asks you for any documentation, links, or prior work that applies, and
records them in the request so the spec stage starts from your sources instead of
re-finding them. No module names, no section names.

### 7. `README.md` and `skills/tcw-work/SKILL.md` — confirm no change

Both are expected **not** to fire; this task is to confirm that against the
finished diff rather than assume it, and to make the change if the confirmation
fails.

- `README.md` `[Public-API]` — the public CLI surface does not change. The README
  describes `initial-request.md` as "seeded with title, the three-axis scaffold …
  and any piped stdin" (`:684-686`) — that seeding is unchanged — and its
  `tcw-work` skill bullet (`:847-856`) is a stage-level summary that stays true.
  Expected: no edit. This is the one genuine judgment call in the block; a
  reviewer who disagrees can be satisfied with one sentence, so do not defend it
  at length.
- `skills/tcw-work/SKILL.md` `[Skill-Driven-Component]` — the driven component
  (`tcw work`) does not change, and the router names artifacts, never their
  sections (`:30,43`). Expected: no edit. If an edit does prove necessary, check
  the 60-line body budget (`tests/test_skill_lifecycle_parity.py:184-192`) — the
  rule on breach is extract, not grow.

## Verification

What the suite cannot check, to be confirmed by hand at `implement` and again at
`verify`:

1. **The new step reads as answerable.** The test asserts a marker exists, not
   that the prose is usable. Read the step as if you were the agent running it:
   is it obvious what to ask, and obvious that fetching is out of bounds?
2. **The step is in the right place.** Nothing enforces step order within a
   `Steps` block. Confirm by reading that it follows "ask what is unclear" and
   precedes "write the request".
3. **`stage-spec.md` actually points at the section.** A reader arriving at the
   spec stage cold should learn from `Inputs` alone that references may exist.
4. **Dogfooding.** This item's own `initial-request.md` already carries a
   `## References` section written in the proposed shape. At `verify`, compare it
   against what the finished `stage-request.md` asks for; a mismatch means the
   wording drifted from the worked example during implementation.

## Notes

**Deferred to `complete`, not part of implementation:** the `changed:` capability
in `capabilities.yaml` (`plugin/work-lifecycle`) needs one sentence added to
`docs/capabilities/plugin/work-lifecycle/description.md` covering the new
question. Per `tcw-capabilities`, ledger body edits are the final pre-freeze step
at `tcw work complete`, not an implementation task. Its status stays `Supported`
throughout, so the completion gate (which only blocks on `new:` paths still
reading `Missing`) will not catch a forgotten body edit — acceptance criterion 11
is the only thing that will.

**No blockers.** Nothing in the backlog gates this and it gates nothing, so there
is no `tcw work edit --blocked-by` to record.

**Version cut** is offered after `complete`, per `stage-verify.md` step 9 — not
part of this plan.
