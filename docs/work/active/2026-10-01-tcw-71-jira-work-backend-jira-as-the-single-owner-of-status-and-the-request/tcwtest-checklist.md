# Preparing `TCWTEST` for TCW-71's live check

TCW-71's live scenario (plan Task 15) runs the Jira backend against the real
Jira project `TCWTEST` ("TCW Bridge Test", https://proposit.atlassian.net). Do
these steps in Jira, ticking each one as you confirm it, then say it is done.
Nothing else in TCW-71 waits on this; only the live run does.

**State on 2026-10-08:** `TCWTEST` has three statuses (To Do, In Progress,
Done), shared by its issue types Task, Sub-task, Story, Bug and Epic.

- [ ] **1. Statuses.** The workflow used by `Task` and `Sub-task` has all nine
      of: `Triage`, `To Do`, `Specifying`, `Planning`, `In Progress`,
      `In Review`, `In QA`, `Done`, `Won't Do`. Six are new: Triage,
      Specifying, Planning, In Review, In QA, Won't Do.
      *Confirm:* Project settings → Workflows shows all nine on that workflow.
- [ ] **2. No `Start` or `Accept` transitions.** Remove any transition with
      either name. *Confirm:* the workflow's transition list has neither.
- [ ] **3. One global transition into each status.** A global transition is one
      that can start from any status ("Allow all statuses to transition to
      this one"). Add one into each of the nine, with no screen — except the
      one into `Planning`, which gets a screen holding only the Comment field.
      *Confirm:* on a test ticket, the status menu offers all nine from any
      status, and moving to Planning shows a comment box and nothing else.
- [ ] **4. Text fields `TCW Project` and `TCW Item`.** Create both as
      short-text fields, and put both on the create and edit screens of `Task`
      and `Sub-task`. *Confirm:* creating a Task shows both fields.
- [ ] **5. `Effort` and `Complexity`.** Create both as single-choice lists
      with exactly the options `low`, `medium`, `high`, `very-high`, on the same
      screens. *Confirm:* editing a Task shows both, each with those four
      options.
- [ ] **6. The `Blocks` link type exists.** *Confirm:* Settings → Issues →
      Issue linking lists `Blocks` (blocks / is blocked by).
- [ ] **7. A non-English account.** Name one account whose profile language is
      not English, or write "none available". (It answers whether Jira
      translates status names in its answers.) Account: ____________
- [ ] **8. The scenario's account.** The account behind `TCW_JIRA_EMAIL` and
      `TCW_JIRA_API_KEY` (already exported from `~/.bashrc` on this machine)
      can create, edit, transition and comment in `TCWTEST`.
      Is it a Jira administrator? yes / no (an administrator can read the
      workflow definition; otherwise TCW falls back to sample tickets).

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
