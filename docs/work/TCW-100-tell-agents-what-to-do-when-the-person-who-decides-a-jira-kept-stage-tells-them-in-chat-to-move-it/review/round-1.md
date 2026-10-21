---
verdict: accepted
judges: 1
---
# Review round 1 — TCW-100

Two reviews by separate, read-only agents that did not write the change, the
second of them a multi review (its own, Codex, and the local model `bllm`).
Both ran while the item was at implement; their findings were fixed before
implement round 1 was written, and this round records them and the state the
change ended in, at `23a8a1bb`.

## Reviewer 1 (the `reviewer` agent), at `ed546e26`

Recommended `rejected`. Accepted findings, all fixed in `6e0a118b`:

- **A.** `skills/extras-autonomous-work/SKILL.md` dropped "explicitly" and let
  a run instruction supply a qa verdict. Now: request moves only on an
  explicit instruction for the run; qa never moves in an unattended run.
- **B.** No implement round. Written (round 1).
- **C.** `tcw/work/procedures/unattended-work.md`, request row, "Then
  continue". Now leaves the item at request unless the run instruction
  explicitly said to move it.

Deferred to a separate change: tests of skill and guide wording, which belong
with TCW-93's eval follow-ups.

## Reviewer 2, multi review, at `6e0a118b`

- **Codex** (`codex exec review --base a573f63a`, header `sandbox:
  read-only`): "No actionable defects were identified." A real answer, weak
  evidence: its prompt had no focus questions.
- **bllm**, in three slices by concern, each checked to hold the right files:
  "no defect" on every question but one, a claim that "The verdict is that
  move." is bad grammar. Rejected: the line is unchanged and criterion 2
  requires it.
- **The reviewer's own findings**, accepted and fixed in `23a8a1bb`:
  1. The Jira qa prompt did not say a verdict comes after the findings, so an
     agent with only the prompt could take "accept it if it passes" as one.
     Sentence added, with a test.
  2. `qa.md` said the status is something "people move"; now "a person
     decides".
  3. The footer tests did not pin "a question or an implied yes is not that".
     Assertion added in both files; it fails against text without the clause.
  - Separate change, folded in as small: the Jira guide's qa examples now
    name who decided.

## Acceptance criteria, at `23a8a1bb`

1. **Met.** Request footer: says a person decides, "only when that person
   tells you to", names `tcw work advance <item> --reason`; no "Do not move it
   yourself". Tests in both footer files.
2. **Met.** Qa footer names `--to <stage> --reason` and keeps "The verdict is
   that move.".
3. **Met.** Only the external branch of `stage_footer` changed; the
   filesystem footer tests are unchanged and pass.
4. **Met.** `request.md` Jira passage, in order; test checks the order.
5. **Met.** `qa.md` Jira step 3; test checks both commands, the
   after-the-findings sentence and the stop.
6. **Met** after fix A and C.
7. **Met.** Jira guide, work guide, README.
8. **Met.** The three descriptions match the text.
9. **Met.** Sweep finds only the tests asserting the old sentence is gone.
10. **Met.** Bare `pytest` at `23a8a1bb`: `5155 passed, 118 skipped in
    451.76s (0:07:31)`.

## Repository review rules

- Suite run as CI runs it: above.
- `documentation-sync` invoked: every fired entry answered (README, Jira
  guide, work guide, release notes, changelog, skills);
  Configuration-Key-Change did not fire.
- Not from a GitHub issue; nothing to close.
- `tcw validate`: 0 errors, 0 warnings, 0 unresolved.
