## The advisors

Run both at once, on the same brief:

- **Codex**: `codex -C <repo> exec -c sandbox_mode=read-only "<brief>"` as a
  command run in the background. Never bare `codex`, which opens an
  interactive screen and hangs the call; `-C` goes *before* `exec`; without
  the sandbox setting it stops to ask for approval.
- **A second agent**: a read-only subagent on the strongest model you can
  start.

The brief must stand alone: the item's slug, the files involved, the exact
question, the options you see, and which one you lean towards. A brief that
only makes sense with your context returns advice that only sounds right.

Decide from what they say: if they agree, act. If they split, take the
stronger argument, not a majority (there is no majority of two), and write
down why. If both say there is not enough information about something that
cannot be undone, that is a hard blocker. You are not bound by either; they
replace a second opinion, not your judgement.

**An agent that stops without reporting has not answered.** It happens often,
and silence reads exactly like "nothing to say". Ask it again for the
conclusion, restating what the answer must cover. Never write down a verdict
you did not read. When an answer matters, do not let the run wait on one
advisor alone.

## Where each stage needs a person

| The stage asks for          | Do this instead |
| --------------------------- | --------------- |
| What the requester wants, at request | Do not ask the advisors: what the requester wants is not theirs to know. Write the request from the evidence available, marking each assumption, as the request prompt says when there is no user to ask. Where the backend keeps the request, as Jira does, post your questions with `tcw work comment <slug>` instead and leave its text alone, and leave the item at request unless the user's own instruction for this run explicitly said to move it out of request. Then move on to other work. |
| One agent or several        | Decide yourself. One, unless the parts are truly independent. |
| An open question in a spec or plan | Ask the advisors, then write the answer into the document with the assumption stated in the text. |
| Review                      | Run the review stage as its prompt says: a read-only reviewer, never the agent that implemented. Apply what you agree with; write down what you reject and why. |
| A qa verdict                | Where the qa prompt lets the agent record the verdict, ask the advisors first, and add your own hands-on use of whatever the project produces. Where it says a person decides, or the qa stage is kept by the backend, post your findings with `tcw work comment <slug>`, leave the item at qa, and move on to other work. |
| The same criterion failing review or qa three times | A hard blocker. Stop work on the item and say so in the report. |
| Hands-on checking           | Use the real thing yourself, however this project runs it. Agent reports and passing tests are what someone says, not evidence. |
| Capability records          | The `capabilities` skill, unchanged. |
| A release                   | Not yours to make. Nobody is present to ask for one, so let the upcoming changelog entries accumulate and move on. |
| The audit trail             | Write each decision you made in a person's place, with the advisors' answers, into the round you write next: the implement round for decisions up to implement, the review or qa round for decisions there. Where no round gets written, because a person decides the qa verdict or the backend keeps qa, put them in the findings comment you post with `tcw work comment <slug>`, or in your report if you post none. The person reading it later then sees what was decided for them. |
