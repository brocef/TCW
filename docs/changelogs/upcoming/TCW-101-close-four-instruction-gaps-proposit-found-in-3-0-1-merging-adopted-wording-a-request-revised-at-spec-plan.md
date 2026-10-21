## Changed

- `request` prompt (Jira passage): adopted wording changes only what was
  adopted; the rest of the description is kept. (TCW-101)
- `spec` prompt, "Exit badly": a bullet for the requester revising the request.
  The item stays at spec, and the change is recorded as request does.
- `plan` prompt step 6 and the `work` skill: how to file an epic's part into
  another project (`--project`, record the changes in that project's version
  control, then `tcw work edit` from inside it).
- `commands-plan-work`: says the plan prompt's advance line does not apply.
- `delegate_to_jira` (`tcw/work/jira/tickets.py`): the "left uncommitted"
  report adds that the next filing into that project stays in its Jira inbox
  until the files are recorded in its version control.
