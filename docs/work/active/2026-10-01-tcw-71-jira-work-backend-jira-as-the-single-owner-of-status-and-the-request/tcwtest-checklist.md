# Preparing `TCWTEST` for TCW-71's live check

TCW-71's live scenario (plan Task 15) runs the Jira backend against the real
Jira project `TCWTEST` ("TCW Bridge Test", https://proposit.atlassian.net). Do
these steps in Jira, ticking each one as you confirm it, then say it is done.
Nothing else in TCW-71 waits on this; only the live run does.

**State on 2026-10-08:** `TCWTEST` has three statuses (To Do, In Progress,
Done), shared by its issue types Task, Sub-task, Story, Bug and Epic.

- [x] **1. Statuses.** The workflow used by `Task` and `Sub-task` has all nine
      of: `Triage`, `To Do`, `Specifying`, `Planning`, `In Progress`,
      `In Review`, `In QA`, `Done`, `Won't Do`. Six are new: Triage,
      Specifying, Planning, In Review, In QA, Won't Do.
      *Confirm:* Project settings → Workflows shows all nine on that workflow.
- [x] **2. No `Start` or `Accept` transitions.** Remove any transition with
      either name. *Confirm:* the workflow's transition list has neither.
- [x] **3. One global transition into each status.** A global transition is one
      that can start from any status ("Allow all statuses to transition to
      this one"). Add one into each of the nine, with no screen — except the
      one into `Planning`, which gets a screen holding only the Comment field.
      *Confirm:* on a test ticket, the status menu offers all nine from any
      status, and moving to Planning shows a comment box and nothing else.
- [x] **4. Text fields `TCW Project` and `TCW Item`.** Create both as
      short-text fields, and put both on the create and edit screens of `Task`
      and `Sub-task`. *Confirm:* creating a Task shows both fields.
- [x] **5. `Effort` and `Complexity`.** Create both as single-choice lists
      with exactly the options `low`, `medium`, `high`, `very-high`, on the same
      screens. *Confirm:* editing a Task shows both, each with those four
      options.
- [x] **6. The `Blocks` link type exists.** *Confirm:* Settings → Issues →
      Issue linking lists `Blocks` (blocks / is blocked by).
- [x] **7. A non-English account.** Name one account whose profile language is
      not English, or write "none available". (It answers whether Jira
      translates status names in its answers.) Account: none available
- [x] **8. The scenario's account.** The account behind `TCW_JIRA_EMAIL` and
      `TCW_JIRA_API_KEY` (already exported from `~/.bashrc` on this machine)
      can create, edit, transition and comment in `TCWTEST`.
      Is it a Jira administrator? **yes** (an administrator can read the
      workflow definition; otherwise TCW falls back to sample tickets).

## Applied on 2026-10-13

The owner answered steps 7 and 8 (no non-English account; the scenario's
account is a Jira administrator, confirmed by its global `ADMINISTER`
permission) and asked for steps 1–5 to be applied through the Jira API. Step 6
was already true, and so was step 2: the old workflow's only transitions were
global ones named To Do, In Progress and Done.

What was created, so it can be removed later:

- **Statuses** (global): `Specifying` 10042, `Planning` 10043, `In QA` 10044.
  `Triage` 10011, `In Review` 10013 and `Won't Do` 10041 already existed on the
  site and were reused. Jira's workflow-create call reset the description of
  every status it was given to blank; the three new ones were restored, and the
  site's Free plan has no audit log to say whether the six reused ones had any.
- **Screen** 10049 `TCWTEST: Planning transition screen`, with no fields, so
  the move to Planning shows only the comment box.
- **Workflow** `TCWTEST: TCW lifecycle workflow (Task, Sub-task)`
  (19ccd58a-6ea1-49ff-b707-e0288d3495d7): the nine statuses, a `Create`
  initial transition into To Do, and one global transition into each status,
  named after it (ids 11–91).
- **Workflow scheme** 10040 `TCWTEST: TCW lifecycle workflow scheme`: Task and
  Sub-task use the workflow above; Story, Bug and Epic keep
  `Software Simplified Workflow for Project TCWTEST`. `TCWTEST` was switched
  to it from scheme 10005; its three tickets kept their statuses.
- **Fields**: `TCW Project` customfield_10076 (short text), `Effort`
  customfield_10077 and `Complexity` customfield_10078 (single choice, options
  low, medium, high, very-high). The existing `TCW Item` customfield_10042 was
  reused. All four were added to screen 10013 (`TCWTEST: Scrum Default
  Screen Scheme`'s only screen), which serves create, edit and view for Task,
  Sub-task and Story.

Verified afterwards: `/project/TCWTEST/statuses` lists the nine for Task and
Sub-task; `TCWTEST-1` offers a transition into all nine, only Planning with a
screen and that screen with no fields; create and edit metadata for Task and
Sub-task carry all four fields with the four options.

## The configuration the scenario uses

The live test writes this into a scratch project; nothing here is to be set by
hand.

```yaml
id: tcw-test-live
work:
  backend: jira
  jira:
    site: https://proposit.atlassian.net
    project: TCWTEST
    credentials:
      email-env: TCW_JIRA_EMAIL
      token-env: TCW_JIRA_API_KEY
    fields:
      project: TCW Project
      item: TCW Item
      effort: Effort
      complexity: Complexity
  stages:
    inbox: {status: To Do}
    request: {status: Triage}
    spec: {enabled: true, status: Specifying}
    plan: {enabled: true, status: Planning}
    implement: {status: In Progress}
    review: {enabled: true, status: In Review}
    qa: {enabled: true, status: In QA}
    completed: {status: Done}
    discarded: {status: Won't Do}
```

`To Do` is the inbox status: tickets there are what `tcw work tickets list`
offers for adoption. The key names follow the spec's Design 1 (`work.jira`) and
TCW-69's stage configuration (every enabled stage but `postmortem` needs its
own status).
