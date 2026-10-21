# Spec — Tell agents what to do when the person who decides a Jira-kept stage tells them, in chat, to move it

## Capability changes

Changed, no new or removed capabilities, and no taxonomy changes:

- `work/run-a-lifecycle-stage`: its description says a stage the backend keeps
  ends "without an `advance` command, because a person or the backend moves the
  item there". After this change the footer of such a stage names the
  `advance` command to run once the deciding person says to move the item.
- `skills/commands-plan-work`: "then stops, because a person moves a ticket out
  of request" becomes: it stops unless the requester tells it to move the
  item, and moves it when they do.
- `skills/commands-drive-work-to-completion`: "stops at qa, because moving the
  ticket is the verdict and a person makes it" becomes: a person makes the
  verdict, and the agent records it with `tcw work advance` when that person
  gives it in the conversation.

## Problem

Where a backend keeps a stage itself, every instruction an agent reads says to
stop and leave the move to a person. None says what to do when that person is
the user in the conversation and tells the agent to move the item. The
Jira backend keeps request and qa (`tcw/work/jira/backend.py:60`,
`EXTERNAL_STAGES`).

The places that say it today:

1. `tcw/work/resolve.py:452-454`, `stage_footer`: "**When this stage's work is
   done, a person moves the item on in the backend.** Do not move it
   yourself." That text is printed below the request and qa prompts on a Jira
   project, and is the last thing the agent reads.
2. `tcw/work/prompts/request.md:34-38`, the Jira passage: "Jira owns it: never
   rewrite it", and propose wording in a comment "for the requester to adopt".
   It does not say how adopted wording gets into the description.
3. `tcw/work/prompts/qa.md:62-67`, the Jira passage, step 3: "Leave the
   decision to a person. Tell them how to record it". It already gives the
   `tcw work advance --to … --reason …` commands, but as text for the person
   to run, not for the agent.
4. `skills/commands-plan-work/SKILL.md:34-37`: "a person moves the ticket on.
   Stop after that comment".
5. `skills/commands-process-inbox/SKILL.md:24-26`: "a person moves the ticket on."
6. `skills/work/SKILL.md:50-52`: "the stage has no folder, a person moves the
   item on". Also line 75, about dispatching qa to a subagent, which is right
   and stays.
7. `skills/commands-drive-work-to-completion/SKILL.md:42-43`: "post the
   findings, and stop at qa for a person."
8. `skills/extras-autonomous-work/SKILL.md`: says nothing about who may move a
   Jira-kept stage in an unattended run.
9. `docs/guide/jira.md:44-46` and `:55-62`, `docs/guide/work.md:168-169`,
   `README.md:512`: describe the move as something a person does on the ticket.

The code already expects an agent to make these moves for a person:
`tcw/work/advance.py:92-95` asks for `--to` and a `--reason` to leave a
Jira-kept verdict stage, and `:144-146` refuses one without a reason. Any move
given `--reason` posts a note on the ticket, "Moved from X to Y. Reason: …"
(`advance.py:230-234`, `:277`). TCW has no command that writes a Jira
description: the Jira backend's `update` (`tcw/work/jira/backend.py:793`)
changes properties and links, never the description.

Observed: a session working proposit-app-repo's PRPI-198 under
`commands-plan-work` posted its proposed request wording and stopped. When the
requester asked why it could not move the item itself, it did not know whether
it was allowed to.

## Goals

1. An agent at a Jira-kept stage knows that the rule is that **a person
   decides**, and that once that person tells it explicitly to move the item,
   it moves it with `tcw work advance`.
2. At request, it knows how adopted wording reaches the description, and in
   what order: description, read back, then move.
3. At qa, it knows the exact commands for an accepted and a rejected verdict
   given by the person in the conversation.
4. It still stops when it has no such instruction, and treats an implied yes
   or a question as no instruction.

## Non-goals

- A `tcw` command that writes a ticket's description. That is a new feature,
  and this ships in a patch (request comment, Constraints).
- Any change to what `tcw work advance` does, checks or refuses.
- The filesystem backend's qa, where a project's prompt says a person decides:
  that already has the person's decision recorded in a round with
  `decided-by` (`tcw/work/prompts/qa.md:44-52`), and is not stuck.
- Inbox tickets. Adopting one is `tcw work tickets adopt`, which an agent
  already runs.
- An eval case measuring whether agents follow the new text. TCW-93 holds the
  eval-harness follow-ups; this can be added there.

## Design

The rules every changed place must state, consistently:

1. **Who decides.** At a stage the backend keeps, a person decides whether the
   item moves on: the requester at request, and whoever the project has accept
   work at qa. The agent does not decide.
2. **What counts as being told.** The deciding person tells the agent, in this
   conversation, to move the item (or, at qa, gives the verdict). A question,
   approval of something else, or an assumption is not that instruction. An
   advisor or subagent never stands in for that person.
3. **Request, when told.** If the person adopted changed wording, it goes into
   the ticket's description first: written by the agent with whatever access
   to Jira its harness has, or pasted in by the person when the agent has
   none. The agent reads the description back and confirms it before moving.
   Then it runs `tcw work advance <slug> --reason "<who told it to move the
   item>"`.
4. **Qa, when told.** Accepted:
   `tcw work advance <slug> --to completed --reason "accepted by <name>: <why>"`.
   Rejected: `tcw work advance <slug> --to implement --reason "rejected by
   <name>: <what to fix>"`.
5. **Not told.** Unchanged: the agent posts what the stage asks for, stops, and
   reports that the item waits for that person. In an unattended run the item
   stays at request unless the user's own instruction for the run explicitly
   said to move it out of request, and it always stays at qa: a verdict is
   given after the person has seen the findings, so an instruction given
   before the run is never one. (Corrected at review: the first version
   allowed a run instruction to move qa too, which let the agent choose the
   verdict.)
6. **Why `advance` and not a click in Jira.** The text says that moving with
   `tcw work advance` runs the checks and hooks bound to the move, and that a
   transition made directly in Jira does not.

Where each rule goes:

| Place | Carries |
| --- | --- |
| P1 `stage_footer`, external branch | 1, 2, and the command: plain `advance` for a stage with no verdict, `--to <stage>` and `--reason` for one with a verdict |
| P2 `prompts/request.md`, Jira passage | 3 |
| P3 `prompts/qa.md`, Jira passage step 3 | 4, 5 |
| P4 `commands-plan-work` | 1-3, 5 |
| P5 `commands-process-inbox` | 1-3, 5 (one sentence pointing to the request prompt) |
| P6 `work` skill, line 50-52 | 1, 2, 6 |
| P7 `commands-drive-work-to-completion` | 4, 5 |
| P8 `extras-autonomous-work`, and the `unattended-work` procedure's request row (`tcw/work/procedures/unattended-work.md`, added at review) | 2 (advisors never stand in), 5 |
| P9 `docs/guide/jira.md`, `docs/guide/work.md`, `README.md` | 1, 3, 4, 6, in plain language |

The footer stays generic: it names no stage and no backend, as its comment at
`tcw/work/resolve.py:428-432` requires, and keys only on `row.verdict`.

## Abstraction litmus test

No new operation, and no change to an existing one. Writing a description stays
outside TCW. A move is `set stage` through `tcw work advance`, which any
backend already implements.

## Acceptance criteria

1. On a Jira project, `tcw work stage prompt request <item>` ends with a footer
   that says a person decides, says to move only when that person tells you
   to, and names `` `tcw work advance <item>` ``. It contains no "Do not move it
   yourself".
2. On a Jira project, the qa footer says the same and names
   `` `tcw work advance <item> --to <stage> --reason` ``, and keeps "The verdict
   is that move."
3. On a filesystem project, no footer changes: every stage that is not
   external prints the same footer as before this change.
4. The Jira request passage says: write adopted wording into the description
   (with the harness's Jira access, or ask the person to paste it), read it
   back, then advance with a `--reason`.
5. The Jira qa passage says the agent runs the accept and reject commands
   itself when the person gives the verdict in the conversation, and stops
   otherwise.
6. Each skill in P4-P8 states the rules the table gives it. No place listed in
   Problem still says only that a person moves the item, with no instruction
   for when that person says to move it.
7. The guides and README describe the move as a person deciding, which they
   do on the ticket or by telling the agent.
8. The three capability descriptions in Capability changes are updated.
9. A repository-wide search for "person moves", "move it yourself" and
   "stop at qa for a person" outside `docs/work/` and changelogs finds no hit
   that contradicts the rules.
10. The suite passes as CI runs it (bare `pytest`).

### Coverage

| # | rule 1 | rule 2 | rule 3 | rule 4 | rule 5 | rule 6 |
| - | ------ | ------ | ------ | ------ | ------ | ------ |
| 1 | footer test (Jira, request) | footer test | n/a: the footer only names the command; detail is P2 (`request.md`) | n/a: request has no verdict, `tcw/work/model.py` row | n/a: footer never says stop | n/a: the footer is too short; P6 carries it |
| 2 | footer test (Jira, qa) | footer test | n/a: qa is not request | footer test (`--to`, `--reason`) | n/a, as above | n/a, as above |
| 3 | stand-in backend test in `tests/work/test_stage_bookends.py` | n/a: external branch only | n/a | n/a | n/a | n/a |
| 4 | n/a: request passage | read in review | read in review | n/a | n/a | read in review |
| 5 | read in review | read in review | n/a | read in review | read in review | n/a |
| 6 | grep plus review | grep plus review | review | review | review | review |
| 7 | review | n/a | review | review | n/a | review |

## Risks

- **Agents moving items on their own judgment.** Loose wording turns "a person
  decides" into "the agent decides". Rule 2 must be explicit in every place,
  and the footer must keep a direct "only when that person tells you to".
- **The footer has two readers.** It is generic across backends and stages; a
  footer that names "requester" would be wrong at qa. It names "the person who
  decides".
- **Jira access varies by harness.** An agent without the Atlassian MCP cannot
  write the description. Rule 3 gives it a path that still works: the person
  pastes the wording in.

## Notes

The other session's question that started this, and this session's answer,
are in the item's request (Origin). The answer it gave matches these rules.
