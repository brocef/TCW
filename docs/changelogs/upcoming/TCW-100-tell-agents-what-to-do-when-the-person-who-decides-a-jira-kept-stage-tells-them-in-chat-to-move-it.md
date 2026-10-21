## Changed

- `stage_footer` (`tcw/work/resolve.py`): the footer of a stage the backend
  keeps (Jira: request, qa) now says a person decides whether the item moves
  on, and names the `tcw work advance` to run once that person says to move
  it: with `--reason` for request, with `--to <stage> --reason` for a verdict
  stage. It no longer says "Do not move it yourself". (TCW-100)
- The Jira passages of the `request` and `qa` stage prompts say what to do
  when the deciding person tells the agent to move the item. At request: write
  the adopted wording into the description (or have the person paste it), read
  it back, then advance with `--reason`. At qa: record the person's verdict with
  `advance --to completed|implement --reason`.
- Skills `commands-plan-work`, `commands-process-inbox`, `work`,
  `commands-drive-work-to-completion` and `extras-autonomous-work`, the Jira and
  work guides, the README and three capability descriptions state the same
  rule. Advisors in an unattended run never stand in for the deciding person.
- `extras-autonomous-work` and the `unattended-work` procedure: a Jira-kept request moves only on the user's explicit instruction for the run; a Jira-kept qa never moves in an unattended run.
