## Changed

- `commands-pause-work` skill: an agent whose turn is interrupted without
  warning now assumes the user interrupted it to deliver a pending message,
  reads that message and pauses if asked, instead of resuming its plan or
  treating itself as finished. An agent passing a pause on to others treats a
  quiet agent as still processing it, not done and idle, until more than ten
  minutes pass with no message or confirmation.
