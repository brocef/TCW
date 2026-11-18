## Changed

- `commands-pause-work` skill: an agent that sent the pause to other agents
  and sees one of them interrupted now assumes the user interrupted it so it
  would read the pause, and that it is doing its own handoff. The agent does
  not take that handoff over, and does not count the interrupted agent as done
  and idle until more than ten minutes pass with no message or confirmation.
- `commands-pause-work` skill: the agent reporting to the user now ends with a
  single resume message for a fresh session, covering every paused item and
  saying to start agents again where the work was split, instead of one
  resume line per item. An agent reporting to another agent writes no resume
  message; it sends that agent its report.
- Where a handoff goes moved from the `commands-pause-work` skill into the
  `pause-work` procedure, so a project can replace it under
  `work.procedures.pause-work`. The default asks for a place a fresh session on
  another machine can reach, following the project's and the user's
  instructions, and shares a handoff file the way the project shares its
  files where they allow.
