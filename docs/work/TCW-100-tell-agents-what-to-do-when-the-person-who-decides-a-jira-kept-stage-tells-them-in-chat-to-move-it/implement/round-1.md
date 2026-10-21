# Implement round 1 — TCW-100

The work is in commits `ed546e26`, `6e0a118b` and `23a8a1bb`. The last two
answer findings from the two reviews run while the item was at implement
(see the review round).

## What was done, by plan step

1. **Tests first.** Five tests changed or added: the footer tests in
   `tests/work/test_stage_bookends.py` and
   `tests/work/jira/test_jira_stage_bookends.py`, and two Jira-passage tests in
   `tests/test_shipped_prompts.py`. They were run before the code changed: 7
   failed, each because the new text was missing. One of them searched for
   "tells you to move" where the prompt says "tell you to move"; the search
   phrase was corrected. Later, two assertions added after the multi review
   (the "after they have seen your findings" sentence, and the footer's
   "a question or an implied yes is not that") were each checked against the
   old text and failed there.
2. **P1, the footer** (`tcw/work/resolve.py`, `stage_footer`). An external
   stage now says a person decides whether the item moves on, that the agent
   moves it only when that person tells it to, that a question or an implied
   yes is not that, and gives the command: `--reason` for a stage with no
   verdict, `--to <stage> --reason` for one with a verdict. It names no stage
   and no backend.
3. **P2, P3, the prompts.** `request.md` (Jira): the requester decides; when
   told, write adopted wording into the description or ask them to paste it,
   read it back, then `tcw work advance <slug> --reason`. `qa.md` (Jira): a
   person decides the verdict; record it with `--to completed` or
   `--to implement` and a reason naming them; a verdict comes after the
   findings; otherwise stop.
4. **P4-P8, the skills**: `commands-plan-work`, `commands-process-inbox`,
   `work`, `commands-drive-work-to-completion`, `extras-autonomous-work`; and
   the `unattended-work` procedure's request row.
5. **P9**: `docs/guide/jira.md` (request paragraph, accepting or rejecting,
   and the qa examples, which now name who decided), `docs/guide/work.md`,
   `README.md`.
6. **Capability records**: the three descriptions `capabilities.yaml` names.
7. **Documentation entries**: changelog and release-note entries written.
   `documentation-sync` evaluated every entry: README, Jira guide, work guide,
   release notes, changelog and skills fired and are answered;
   Configuration-Key-Change did not fire, since no key changed.
8. **Sweep**: outside `docs/work/` and released notes, "person moves", "move
   it yourself", "stop at qa for a person" and "Leave the decision to a
   person" hit only the tests asserting the old sentence is gone.
9. **Suite**, bare `pytest` as CI runs it, at `23a8a1bb`:
   `5155 passed, 118 skipped in 451.76s (0:07:31)`. `tcw validate`: 0
   errors, 0 warnings, 0 unresolved.

## What the plan or spec got wrong

- **Spec rule 5 let a run instruction move a Jira-kept qa.** At qa, moving is
  choosing the verdict, so that broke rule 1. Corrected in the spec: an
  unattended run never moves qa, and moves request only on an explicit
  instruction for the run.
- **The spec's table missed the `unattended-work` procedure**, whose request
  row said "Then continue". Added to P8.
- **The spec gave rule 5's "after the findings" point to P3 but the first
  version of `qa.md` did not carry it.** The skills did, the prompt did not,
  and the prompt is what an agent without TCW's skills reads. Added.

## Records changed

`docs/capabilities/work/run-a-lifecycle-stage/description.md`,
`docs/capabilities/skills/commands-plan-work/description.md`,
`docs/capabilities/skills/commands-drive-work-to-completion/description.md`.

## Rejections answered

None: no review or qa round has been written yet. The findings answered are
listed in the review round.
