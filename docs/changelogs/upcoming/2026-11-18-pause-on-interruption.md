## Changed

- `commands-pause-work` skill: an agent whose turn is interrupted without
  warning now assumes the user interrupted it to deliver a pending message,
  reads that message and pauses if asked, instead of resuming its plan or
  treating itself as finished. An agent passing a pause on to others treats a
  quiet agent as still processing it, not done and idle, until more than ten
  minutes pass with no message or confirmation.
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
