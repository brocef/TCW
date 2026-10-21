## Fixes

- **Clearer instructions for four planning situations.** When you adopt
  proposed wording for a Jira request, the agent changes only what you adopted
  and keeps the rest of the description. When you change your mind about the
  request while the spec is being written, the item stays where it is and the
  change is recorded on the request. The plan-work skill now says outright
  that it stops at the plan. And the plan instructions explain how to file an
  epic's part into another project: file it, commit what TCW wrote there, then
  set its parent from inside that project.
- **A warning before a filing gets stuck.** After `tcw work new --project`
  makes an item in a Jira project, the message now says to commit the new
  files before filing into that project again; otherwise the next ticket stays
  in its Jira inbox.
