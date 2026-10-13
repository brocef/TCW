# TCW-71 live check against `TCWTEST` (plan Task 15; AC 23, 24)

Run on 2026-10-13 from the branch checkout, after `TCWTEST` was prepared
(`tcwtest-checklist.md`, "Applied on 2026-10-13"):

    source ~/.bashrc >/dev/null 2>&1
    TCW_JIRA_LIVE=1 TCW_JIRA_CAPTURE=tests/work/jira/recorded \
      pytest tests/work/jira/test_jira_scenario.py -k live -s

The scenario (Design 15.4, steps 1-10) ran five times. The first two runs
stopped on findings, the third on a setup gap; each is below with what changed.
The last two passed every step, and `validate --remote` exited 0. The fifth
run's output is at the end and is the one `recorded/` comes from. Its probes
(`scenario.probe`) answer the spec's questions.

## The answers (Design 15.4, and the reviewers' three)

| # | Question | Answer, with evidence | Effect on the design |
| --- | --- | --- | --- |
| 1 | Direction of `Blocks` links | `add_link("Blocks", inward=TCWTEST-62, outward=TCWTEST-65)`; on the blocked ticket TCWTEST-65 the blocker is under `inwardIssue`, with the type's inward wording "is blocked by". | None: `mapping.blocker_links` and `block_link` read it this way. `test_recorded_shapes.py` now fails if the fake reverses it. |
| 2 | Is a comment accepted on a transition with no screen? | **Accepted with 204, the move applied, and the comment discarded without a word** (In Review: comments 0 -> 0). On a transition whose screen holds only the comment box it is kept (Planning: 0 -> 1). | **Contradicted Design 5 step 3.** Spec amended on main (`fed1fc18`); `set_stage` now posts the note on its own after a screenless move (`579e57af`). Found when run 1 lost a qa rejection's reason. |
| 3 | Is a cross-project parent accepted? | Accepted on this company-managed site: TCWTEST-69 was created with parent TCWCLAIM-7 (an epic in `TCWCLAIM`), and the parent was removed again. | None: Design 11 step 4 sends it and reports a refusal. |
| 4 | Can a non-administrator read the workflow definition? | Not asked: the scenario's account is a Jira administrator and no other account was available. As an administrator, `POST /rest/api/3/workflows` answered with the 10 transitions. | None: a 403 or an empty answer falls back to sample tickets (`test_without_the_definition_moves_are_sampled`, `test_an_empty_definition_is_sampled_rather_than_failed`). Still open for a non-administrator. |
| 5 | `expand=transitions.fields` for no screen, and a comment-only screen | **Both answer `fields: {}`.** Only `hasScreen` (false / true) tells them apart. | The choice rule is unchanged (both ask for nothing but a comment). The client's `Transition` now carries `has_screen` for question 2's fix. |
| 6 | `cf[TCW Project] ~ "tcw-test-live"` | Finds the ticket valued `tcw-test-live`; does **not** find those valued `tcw-test` or `live`. | None: the design never uses `~` on TCW Project. |
| 7 | `key in (…)` naming a missing key | Answered, skipping the missing key (`['TCWTEST-62']`), not 400. | None: the design works either way; the fake keeps the 400 as a switch. |
| 8 | Search lag | A new ticket appeared in `list` after 0.6-0.7 s in all five runs; a ticket just given a TCW Item value, after 0.2-0.3 s. | None: the design does not depend on it. |
| 9 | Offset on `created` | `2026-10-13T11:46:40.135-0400` for an account whose profile time zone is America/New_York. Only one account was available, so whether the offset follows the reader's profile or the site's default zone is not separated. | None: `created` is converted to UTC either way. |
| 10 | Translated status names | Not asked: no account with a non-English profile language exists (checklist step 7). | Still open; see "Not settled". |
| R1 | Shape of the workflow's INITIAL transition (reviewer) | `{"type": "INITIAL", "links": [], "toStatusReference": "10012", "name": "Create"}`. | None: `validate --remote` skips INITIAL, and the fake lists one in this shape. |
| R2 | `/workflows` for a non-administrator (reviewer) | As question 4. | As question 4. |
| R3 | A JQL status the site does not have (reviewer) | **Answered with no issues and no error** (`{"issues": [], "isLast": true}`), not 400. | The fake had been changed to answer 400 after review round 1; it now matches nothing (`7be0e850`). No code depended on the 400. A misspelt stage status therefore makes `list` show nothing rather than fail; `validate --remote` reports a status missing from the project. |

## Other findings, from the runs

- **Run 3: Epics had only the simplified workflow.** The checklist gave the nine
  statuses to Task and Sub-task only, so adopting an Epic could not reach
  Triage. Epic was mapped to the TCW workflow too (checklist record updated).
- **Run 4: `validate --remote` required Parent on the Epic edit screen.** Nothing
  sits above the top level of the hierarchy, so Jira gives an Epic no Parent
  field. The check now skips Parent for the top-level type (`24f112b4`, spec
  check 2 amended on main, `2d977329`), and the fake no longer lists one. The
  same run showed the TCW fields missing from the Epic screen, another checklist
  gap; they were added.

## Not settled

- Whether status names come back translated for an account whose profile
  language is not English (question 10), and whether a non-administrator can
  read the workflow definition (question 4). Neither can be asked without a
  second account.

## Recorded responses (AC 24)

`tests/work/jira/recorded/` holds 20 files: one answer per endpoint and status,
the one with the most distinct key paths, with account ids, emails, display
names and the site replaced. `test_recorded_shapes.py` checks each path the
backend reads against the recording and against the fake's answer to the same
request. Every listed path appears in the recording. Mutation checks: dropping
`hasScreen` from the fake fails the transitions case; reversing the fake's
`Blocks` direction fails the issue and search cases.

## Output of the fifth run

    step 1: TCWTEST-62 appeared in a search after 0.6s
    step 2: TCWTEST-62 advanced to qa
    step 4: TCWTEST-62 accepted at qa
    step 10: validate --remote exited 0
    lag 0.6s; keys {'item': 'TCWTEST-62', 'edited': 'TCWTEST-63', 'epic': 'TCWTEST-64', 'child': 'TCWTEST-65', 'sub': 'TCWTEST-66', 'adopted': 'TCWTEST-67'}
    validate --remote exited 0
    [33 lines of the form "warning: TCWTEST-N: names tcw-test-live/..., whose folder is not here", one per ticket the earlier runs left, whose folders were in their own throwaway projects]
    tcw-test-live: the credentials and Jira project TCWTEST are readable
    tcw-test-live: moves read from the workflow definition had their screen fields left unchecked; only a sample ticket shows them
    tcw-test-live: 6 item folders checked against their tickets
    tcw-test-live: the model checks ran over 6 items
    validate OK
    blocks: add_link(Blocks, inward=TCWTEST-62, outward=TCWTEST-65); on TCWTEST-65 the blocker TCWTEST-62 is under inwardIssue, type inward='is blocked by'
    comment on a transition: In Review (hasScreen=False, fields=()): accepted, comments 0->0; Planning (hasScreen=True, fields=()): accepted, comments 0->1
    cross-project parent: accepted: TCWTEST-69 created with parent TCWCLAIM-7; parent removed again
    workflow definition: read as an administrator; 10 transitions; INITIAL: [{'type': 'INITIAL', 'links': [], 'toStatusReference': '10012', 'name': 'Create'}]. A non-administrator was not available to try
    ~ on TCW Project: tcw-test-live: found, tcw-test: not found, live: not found
    key in with a missing key: answered, with ['TCWTEST-62']
    an unknown status in JQL: answered, with []
    error bodies: a missing ticket: TrackerNotFound; an invalid transition: TrackerRequestInvalid
    search lag: a new ticket: 0.6s (step 1); a ticket just given a TCW Item: 0.3s
    created offset: created=2026-10-13T11:46:40.135-0400; the account's time zone is America/New_York
    translated status names: not asked: no account with a non-English profile language is available (tcwtest-checklist.md step 7)
    .
    1 passed, 1 deselected in 57.16s
