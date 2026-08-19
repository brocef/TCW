# Plan: name the item's actual body artifact in the stage prompts

Nine tasks. The suite is green at every commit boundary. Task 2 wires the
substitution without any prompt using it, so the risky refactor lands and is
tested before Task 3 makes it load-bearing; Task 5's fixture regeneration is
isolated in its own commit so its large JSON diff is reviewed alone.

No blockers. The sibling item
`2026-08-19-derive-an-accepted-inbox-item-s-title-from-the-entry-s-h1-and-strip-the-date-prefix`
owns `docs/capabilities/work/retitle-a-work-item/description.md`; this plan does
not touch it, so no `--blocked-by` edge is needed in either direction.

---

## Task 1 — Move the body-resolution order into the abstract layer

**Modifies**

- `tcw/store/base.py` — add a module-level `BODY_ORDER = ("initial-request",
  "intake")` beside `WORK_ARTIFACTS` (`tcw/store/base.py:1214`), with the
  comment from spec §Design 1 stating why it is abstract.
- `tcw/store/fs.py` — delete `_BODY_ORDER` (`tcw/store/fs.py:536`); import
  `BODY_ORDER` from `tcw.store.base` and use it in `_resolve_body`
  (`tcw/store/fs.py:2257`).

**Proves it**

- `python -m pytest -q` green (1734 passing today).
- `grep -c "_BODY_ORDER" tcw/store/fs.py` → `0`.
- `python -c "from tcw.store.base import BODY_ORDER; assert BODY_ORDER == ('initial-request','intake')"`.

Pure move; no behavior change. Covers spec goal 6.

---

## Task 2 — `substitute_body`, wired but unused

**Modifies**

- `tcw/work/resolve.py` — add `BODY_OPEN = "{{tcw:body}}"` / `BODY_CLOSE =
  "{{/tcw:body}}"` and `substitute_body(text, artifacts)`. Replacement is
  **inline**: the span from open token through close token is replaced in place
  by `` `<name>.md` `` for the first `BODY_ORDER` name whose matching
  `Artifact.present` is true — no inserted newline, no indent, no
  following-space adjustment. With no such artifact the span becomes its inner
  text. An unterminated open token leaves the text verbatim. Call it from
  `resolve_prompts` (`tcw/work/resolve.py:338`) after
  `substitute_documentation`, over the joined text.
- `tcw/work/resolve.py` — **do not** change `substitute_documentation`'s
  output. Share code with it only if the shared part is byte-identical for both
  (locating a token pair, slicing the fallback). If sharing forces any change to
  documentation rendering, write the second loop instead and say so in a
  comment.

**Creates**

- `tests/test_body_prompt.py` — unit tests for spec criteria 1 and 2:
  - both artifacts present → `` `initial-request.md` ``
  - only `intake` present → `` `intake.md` ``
  - neither present → the span's inner text, verbatim
  - unterminated `{{tcw:body}}` → input returned unchanged
  - mid-sentence span `**Inputs.** {{tcw:body}}x{{/tcw:body}}. On an …` renders
    as a single line `` **Inputs.** `intake.md`. On an … `` — asserted on the
    exact string, which is what pins the inline policy against the block one.

**Proves it**

- `python -m pytest tests/test_body_prompt.py tests/test_documentation_prompt.py tests/test_resolve.py -q` green.
- `python -m pytest -q` green — `tests/test_documentation_prompt.py` passes
  **unmodified**, which is spec criterion 3.

No shipped prompt contains the token yet, so `tcw work stage` output is
byte-identical to before this task.

---

## Task 3 — Rewrite the `spec` and `plan` prompts

**Modifies**

- `tcw/work/prompts/spec.md` — replace the `**Inputs.**` paragraph (line 5-9)
  with the `{{tcw:body}}` form from spec §Design 3, including the positive
  intake branch ("read the intake as the request, as filed") and dropping the
  unconditional "nobody asked" conclusion.
- `tcw/work/prompts/plan.md` — replace the `**Inputs.**` paragraph (line 5-7)
  with `**Inputs.** {{tcw:body}}the item's body artifact{{/tcw:body}} and
  `spec.md`. Repository discovery is unrestricted.`

**Creates**

- `tests/test_body_prompt.py` (extended) — end-to-end tests for spec criteria
  4–8, driving the real CLI against three fixture items built in a tmp node:
  one with `intake.md` only, one with `initial-request.md` only, one with both,
  and one with neither (`tcw work new "<title>"` with nothing piped).
  - intake-only: `tcw work stage spec` / `plan` stdout contains `intake.md` and
    not `initial-request.md` in the Inputs paragraph
  - request-only and both: contains `initial-request.md`
  - neither: exit 0, prints the fallback text, names neither filename
  - intake-only `spec`: contains the read-the-intake instruction **and** no
    sentence concluding "nobody asked"
  - `spec` and `plan` output for all three states contains no `{{tcw:` and no
    `{{/tcw:`

**Proves it**

- `python -m pytest tests/test_body_prompt.py tests/test_shipped_prompts.py -q` green.
- `wc -l tcw/work/prompts/spec.md tcw/work/prompts/plan.md` — both ≤ 50
  (`spec.md` is at 48; net lines must not grow). If it will not fit, cut an
  existing clause from the prompt — **do not** edit the ceiling in
  `tests/test_shipped_prompts.py:50`.
- Manual: `tcw work stage spec 2026-08-19-derive-an-accepted-inbox-item-s-title-from-the-entry-s-h1-and-strip-the-date-prefix`
  names `intake.md`.

---

## Task 4 — Fix the `postmortem` prompt spine

**Modifies**

- `tcw/work/prompts/postmortem.md` — the `**Inputs.**` spine (line 6-10) ends
  at "the body the item started from — `initial-request.md`, or the `intake.md`
  beneath it when the `request` stage never ran." No `{{tcw:body}}` token here:
  a post-mortem reads whatever the item has, so naming both is correct rather
  than resolving one.

**Proves it**

- `python -m pytest tests/test_shipped_prompts.py -q` green (≤ 50 lines; it is
  at 40).
- `tcw work stage postmortem <a completed item>` mentions `intake.md`.

Sweep row 3.

---

## Task 5 — `LIFECYCLE_STEPS` inputs and the baseline fixtures

**Modifies**

- `tcw/store/base.py` — add `"intake.md"` to `inputs` for `spec`
  (`tcw/store/base.py:726`), `plan` (`:731`), and `postmortem` (`:748`).
- `tests/fixtures/lifecycle_baseline/*.json` — regenerate with
  `python tests/fixtures/lifecycle_baseline/capture.py tests/fixtures/lifecycle_baseline`.

**Proves it**

- `git diff tests/fixtures/lifecycle_baseline/` touches **only** `inputs` lines
  — inspected before staging; any other delta stops the task (spec criterion
  10).
- `tcw work lifecycle --stage spec | grep inputs` shows `intake.md`; same for
  `--stage plan` and `--stage postmortem`.
- `python -m pytest tests/test_lifecycle_baseline.py -q` green.
- `python -m pytest -q` green.

Isolated in its own commit because of the fixture blob size.

---

## Task 6 — Skills, references, commands, and agents (sweep rows 5–15)

**Modifies**

- `skills/tcw-work/references/stage-spec.md:10` — `## Inputs` names the item's
  body artifact (request when the `request` stage has run, intake otherwise),
  pointing at `commands.md` "The body surface".
- `skills/tcw-work/references/stage-plan.md:10` — same, plus `spec.md`.
- `skills/tcw-work/references/stage-postmortem.md:11` — spine gains
  `intake.md`.
- `skills/tcw-post-mortem/SKILL.md:19-21` — spine gains `intake.md` (row 14).
- `agents/tcw-post-mortem.md:19` — spine gains `intake.md` (row 11).
- `skills/tcw-work/references/audit-backlog.md:9` — artifact list gains
  `intake.md` (row 15).
- `agents/tcw-backlog-auditor.md:20` — artifact list gains `intake.md` (row 12).
- `skills/tcw-triage-issues/SKILL.md:130-165` (§5) — rewrite so acceptance files
  the reporter's words as `intake.md`, which is what `tcw work inbox accept` and
  a piped `tcw work new` already write, and the `request` stage is what produces
  `initial-request.md`. Keep the `## Origin` convention and the verbatim-quote
  rule; only the artifact and the ordering change (row 8).
- `skills/tcw-triage-issues/SKILL.md:213-214` — the `## Origin` lookup targets
  the item's body, not `initial-request.md` (row 9).
- `skills/tcw-work/references/transitions.md:98-99` — same `## Origin` fix
  (row 10).
- `commands/tcw-process-inbox.md:13-15` — the `request` stage shapes the item's
  `intake.md` **into** `initial-request.md`; it does not read one (row 13).

**Proves it**

- `python -m pytest tests/test_plugin_manifests.py -q` green.
- `tcw validate` → `validate OK`.
- Row-by-row read-back: each of rows 5–15 is re-read after editing and its
  wording checked against
  `skills/tcw-work/references/commands.md:41-46` (spec criterion 11).

Text only; no code. Fixed before Task 7 so the capability descriptions can cite
the corrected skill text.

---

## Task 7 — Capability descriptions (sweep rows 16–17)

**Modifies**

- `docs/capabilities/plugin/triage-github-issues/description.md:2` — an
  accepted issue's `intake.md` records the number, URL, and the reporter's own
  words; the `request` stage later turns it into `initial-request.md`.
- `docs/capabilities/work/complete-a-work-item/description.md:20` — closeout
  finds `## Origin` on the item's body — `initial-request.md` when the request
  has been written, `intake.md` otherwise.

**Proves it**

- `tcw capabilities show plugin/triage-github-issues` and
  `tcw capabilities show work/complete-a-work-item` read correctly.
- `tcw capabilities validate` and `tcw validate` pass.
- Both stay `Supported`; no status flip, no new capability.

---

## Task 8 — Documentation Sync block

All four declared entries are evaluated; three fire.

| Entry                          | Trigger                    | Fires  | Action                                                                                                                                                       |
| ------------------------------ | -------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `README.md`                    | `Public-API`               | **Yes** | `tcw work stage` output and `tcw work lifecycle` inputs both change. Add to the stage-instructions paragraph (`README.md:685-693`) that the shipped `spec` and `plan` instructions name the item's own body artifact — the request when written, the raw intake otherwise. `README.md:933-955` already states the body surface and needs no change. |
| `docs/release-notes/upcoming.md` | `Public-API`             | **Yes** | Plain-language entry: the built-in spec and plan instructions now name the file the item actually has, so an item created from a pipe or from the inbox is no longer pointed at a document that was never written. |
| `docs/changelogs/upcoming.md`  | `Any-Code-Change`          | **Yes** | Grouped entries: **Fixed** — the `spec`/`plan` prompts and the `postmortem` spine; the triage-issues §5 ordering. **Added** — `{{tcw:body}}` span, `BODY_ORDER` in `tcw.store.base`. **Changed** — `LIFECYCLE_STEPS.inputs` for `spec`/`plan`/`postmortem` and the regenerated lifecycle baseline fixtures. |
| `skills/<component>/SKILL.md`  | `Skill-Driven-Component`   | **Yes** | The `work` component's shipped instructions change, so the driving skill must follow. Discharged by Task 6, which edits `skills/tcw-work/references/*`, `skills/tcw-post-mortem/SKILL.md`, and `skills/tcw-triage-issues/SKILL.md`. Re-read `skills/tcw-work/SKILL.md` itself in this task and confirm its stage table and "Finding your place" list still hold — they are expected to need no edit, and if they do, edit them here. |

**Proves it**

- `tcw work docs` re-read against the finished diff, one pass.
- Each fired entry has a committed edit, or an explicit line in `outcome.md`
  saying why not.

---

## Task 9 — Full verification

**Runs**

- `python -m pytest -q` — green, with the new `tests/test_body_prompt.py` cases
  counted and `tests/test_documentation_prompt.py` and
  `tests/test_shipped_prompts.py` unmodified.
- `tcw validate` → `validate OK`.
- `wc -l tcw/work/prompts/*.md` — every file ≤ 50.
- `tcw work stage spec` and `tcw work stage plan` run against a real
  intake-only item, a real request-bearing item, and a fresh
  `tcw work new`-with-no-pipe item; output read, not just exit codes.
- `grep -rn "initial-request" tcw/ skills/ commands/ agents/ docs/capabilities/`
  — every remaining hit matched against the spec's closed classification list;
  anything new is either fixed or added to the not-a-defect list with a reason.

**Produces**

`outcome.md`, recording sweep rows 1–17 by number with what happened to each.

---

## Verification

What the suite cannot check, to be carried into `verify`:

1. **Does the rewritten `spec` prompt still read as instructions?** The tests
   assert substrings; they cannot tell whether the paragraph is coherent English
   after the substitution lands. Read the rendered output for all three body
   states, whole.
2. **Is the `tcw-triage-issues` §5 rewrite actually followable?** It is prose an
   agent executes. The check is to walk it against a real open issue without
   running it, and confirm each step names a command that exists and produces
   the artifact the next step expects.
3. **Is the regenerated baseline diff really `inputs`-only?** Automatable as a
   grep, but the judgment that nothing else *should* have changed is human.
4. **Do the two capability descriptions still match what the code does?**
   `tcw capabilities` validates shape, not truth.
5. **The 50-line ceiling under pressure.** If Task 3 had to cut a clause to fit,
   `verify` should see which clause and agree it was the right one.

## Notes

- Spec criterion 12 quotes 1734 passing tests as the pre-change baseline; the
  count grows with `tests/test_body_prompt.py`. The gate is "green", not the
  number.
- Tasks 6 and 7 are text-only and mutually independent, but are ordered so the
  capability descriptions can cite corrected skill wording rather than the
  reverse.
- Every acceptance criterion maps to a task: 1–2 → Task 2; 3 → Task 2; 4–8 →
  Task 3; 9 → Tasks 3, 4, 9; 10 → Task 5; 11 → Tasks 6, 7, 9; 12 → Tasks 7, 9.
  Sweep rows map: 1–2 → Task 3; 3 → Task 4; 4 → Task 5; 5–15 → Task 6; 16–17 →
  Task 7.
