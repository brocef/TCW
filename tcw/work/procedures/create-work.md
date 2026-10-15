## How it runs

Decide the mode before step 1. It decides who answers every question below.

| Mode | When | Questions are answered by |
| --- | --- | --- |
| **Interactive** | You are the session the user is talking to | The user. Ask everything left in one message |
| **Delegated** | You are a subagent working from a brief | The brief. Anything it leaves open, return as `needs decision` |
| **Unattended** | The session was told to work without asking | The defaults in the tables below |

A subagent is **Delegated**, never **Unattended**, unless its brief says the
session that sent it was itself told to work without asking. It must not answer
for a user who is present in the parent session.

**Handing the idea to a subagent** keeps the board search out of your context.
Its brief carries the idea; where it came from (the item you are working, and
the task or review that surfaced it); reference material already in the
conversation; any answer the user has given, including on blockers ("none",
slugs, or "determine automatically"); and the mode. It reports back step 5's
single line.

## 1. Is the idea understandable?

It needs one sentence saying what should change and why. Nothing more. If you
cannot write that sentence:

- **Interactive:** ask.
- **Delegated:** return `needs decision: clarify`, with the question to ask.
- **Unattended:** leave the decision to a person, and stop.
<!-- backend: filesystem -->
  File it as an arrival for someone to decide on later:
  `tcw work new "<title>" --stage inbox`, with the idea as you have it and
  where it came from on stdin. Report `deferred to inbox <slug>`.
<!-- /backend -->
<!-- backend: jira -->
  In Jira the inbox is tickets that people file, so create nothing: report
  `needs decision: clarify` with the idea as you have it.
<!-- /backend -->

## 3. Act on the result

**When several candidates match:** `covers` beats `partly covers`. Among
`covers` matches, the one furthest along decides, by its stage: implement,
review or qa first, then spec or plan, then request, then inbox. Name every
other `covers` match in your report, because two tracked things covering the
same work is itself news.

| The deciding match | Interactive | Delegated | Unattended | Outcome |
| --- | --- | --- | --- | --- |
| `covers` an item at implement, review or qa | Tell the user the item, and any new information. Change nothing | Return the same | Report the same | `already in progress <slug>` |
| `covers` anything else, and the idea adds nothing it does not already say | Tell the user | Return it | Report it | `already tracked <slug>` |
| `covers` an item at inbox or request, with new information | Add it | Add it | Add it | `amended <slug>` |
| `covers` an item at spec or plan, with new information | Add it, then ask: revise, or leave as is (saying why in what you added) | Add it, then return `needs decision: revise <slug>` unless the brief answers it | Add it, then revise | `revised <slug>`, or `amended <slug>` if left |
| `partly covers`, and the rest can stand alone | Create an item for the rest (step 4), naming the match under References | Same | Same | `created <slug>` |
| `partly covers`, and the rest cannot stand alone | Treat it as `covers` with new information | Same | Same | as that row |
| No match | Create (step 4) | Create | Create | `created <slug>` |

- **Add only what is new**, saying where it came from, and never rewrite what
  is there.
<!-- backend: filesystem -->
  Add it to the request, `tcw work path <slug> request`, under a dated
  `## Added <YYYY-MM-DD>` heading.
<!-- /backend -->
<!-- backend: jira -->
  Post it as a comment with `tcw work comment <slug>`, first line
  `Added <YYYY-MM-DD>`: the request is the ticket's description, which Jira
  owns. A ticket still waiting in the inbox is not an item yet, so
  `tcw work comment` cannot reach it: put the addition, with the ticket's
  key, in your report for a person to add in Jira, and do not adopt the
  ticket to make room for it.
<!-- /backend -->
- **Revise** means running the spec stage again, and the plan stage if the
  item has a plan, after adding the idea: `tcw work stage prompt spec <slug>`
  and follow it, then the same for plan. Report `revised` only once every
  document being revised is written. Inside an `extras-autonomous-work`
  session, its advisors stand in for "ask".
- **Finished items are never the deciding match.** Name a close one under
  References. If it was discarded, put the reason it was discarded, which
  `tcw work show <slug>` prints in its comments, in your report line.

## 4. Create

Ask only what the brief or the conversation has not already answered, and ask
all of it in one message. A request made in chat is its own source, so it
already answers the references and origin questions.

| Question | Accepted answers | Delegated | Unattended default | Recorded as |
| --- | --- | --- | --- | --- |
| Known blockers? | Slugs · "no" · a description (search, then confirm with the user) · "determine automatically" (search, and do not confirm) | From the brief. If the brief is silent, or describes a blocker you would have to confirm, create nothing and return `needs decision: blockers` with step 2's `blocks` lines as candidates | determine automatically | `--blocked-by <ref>` per blocker, plus a line saying why |
| Reference material? | Anything given. Material already in the conversation or brief counts | From the brief; if it has none, write "none given in the brief" (the request stage asks again later) | Take it from context; if there is none, write "no user to ask; none in context" | `## References`, one line of why it matters each |
| A bug, or a follow-up to another item? | Yes, naming the item or symptom · no | From the brief's origin; if it has none, write "none given in the brief" | The item being worked when the idea came up | `## Origin`, plus the `bug` tag for a bug |

**Record a blocker only when the idea cannot proceed until that item lands.**
Sharing a topic, touching the same files, or a preferred order does not count;
those go under References. Determining blockers automatically uses step 2's
`blocks` lines. It is not a second search.

Pick tags from `tcw work tags list`, and give the text on stdin. It becomes
the item's request, which the request stage shapes later:

```bash
tcw work new "<title, as a change>" --tag <tag> [--blocked-by <ref> ...] <<'MD'
# <title, as a change>

<the idea: what should change, and why>

## Origin

<where it came from: the item being worked, the review, the bug's symptom>

## References

- <link or ref> — <why it matters>

<one line per blocker: "Blocked by <ref>: <why it cannot proceed first>">
MD
```

A batch of related leftovers, such as one review's findings, may be one item.
Treat the batch as one idea.

## 5. Report

Exactly one of these lines, with its reference and a one-line reason:

- `created <slug>`
- `amended <slug>`
- `revised <slug>`
- `already tracked <slug>`
- `already in progress <slug>`
- `deferred to inbox <slug>`
- `needs decision: <clarify | revise <slug> | blockers>`, followed by step 2's
  lines, so whoever asks the user does not search again.

In an Interactive run, say the reference to the user.
