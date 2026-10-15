## Instructions for the new stages

Everything TCW tells an agent now describes the 3.0 stages, and each piece of it
lives in one place.

- **Every stage has built-in instructions,** including the new `review` and
  `qa`: `tcw work stage prompt <stage> <slug>` prints what the stage is for,
  what it reads, what it writes and where, and how to finish. A stage that
  moves the item on ends with the `tcw work advance` command to run; inbox,
  postmortem, and the stages Jira keeps (request and qa there) end without
  one, because a person or the backend moves the item. Review and qa write a round whose
  `verdict` and `judges` decide where the item goes. Where your project keeps
  its work in Jira, the request and qa instructions describe the ticket rather
  than files.
- **No instruction tells an agent to commit, push, branch or use a worktree.**
  How your changes are saved and shared is your project's business; add it to
  a stage's instructions under `work.stages.<stage>.prompt` if you want it
  followed.
- **Capability records change with the code.** The `capabilities` skill now
  has the agent declare capability changes in the item's `capabilities.yaml`
  during spec, and add or edit the records themselves during implement with
  the status they really have (`--status Supported`). Moving out of implement
  checks they are there; nothing is flipped at completion.
- **Pausing work** writes the handoff in the folder of the stage the item is
  at (`tcw work path <slug> <stage> --handoff`), or as a `Handoff` comment where
  Jira keeps the stage, and no longer commits or pushes. What the handoff
  holds comes from the new `pause-work` procedure, which your project can
  replace.
- **The procedures are** `unattended-work`, `triage-issues`,
  `documentation-sync`, `create-work`, `audit-backlog`, `search` and
  `pause-work`. `post-mortem`, `consolidate-plans`, `decompose` and
  `delegation` are gone: the postmortem stage has its own instructions, and
  splitting and filing into another project are described in the `work`
  skill. A configuration that still names a removed id is refused by
  `tcw validate`, which says where that procedure's text went.
- **Skills removed:** `work-stage` (read `tcw work stage prompt` instead),
  `commands-verify-work` (review and qa replace verify) and `post-mortem` (use
  the postmortem stage). The `verifier` and `post-mortem` agents are replaced
  by a `reviewer` agent that reads the review stage's instructions.
- **The `setup` skill** can now walk you through configuring a project to
  keep its work in Jira (`backend: jira`), checking the workflow with
  `tcw validate --remote`. It configures the backend; it does not move
  existing items, so finish or discard the items kept as files first.
