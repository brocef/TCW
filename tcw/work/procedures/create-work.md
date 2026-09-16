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

## 0. Use the primary checkout's board

If `git rev-parse --git-dir` and `git rev-parse --git-common-dir` print different
paths, you are in a linked worktree. The board there is only as current as the
branch, and anything filed there stays on the branch. Run every `tcw` and `git`
command in steps 1–4 with the working directory set to the primary checkout: the
path on the first `worktree` line of `git worktree list --porcelain`. That
includes step 1's inbox entry and the strict-mode fallback. This is the same
rule as `tcw work complete`.

## 1. Is the idea understandable?

It needs one sentence saying what should change and why. Nothing more. If you
cannot write that sentence:

- **Interactive:** ask.
- **Delegated:** return `needs decision: clarify`, with the question to ask.
- **Unattended:** write a raw entry into the folder `tcw work inbox path` prints.
  Give it a `# <title>` heading, the idea as you have it, and where it came
  from. Commit it (step 4's commit), report `deferred to inbox <entry>`, and
  stop.

## 3. Act on the result

**When several candidates match:** `covers` beats `partly covers`. Among
`covers` matches, the one furthest along decides. The order is active or
review, then backlog with a `spec.md` or `plan.md`, then backlog without one,
then an inbox entry. Name every other `covers` match in your report, because two
tracked things covering the same work is itself news.

| The deciding match | Interactive | Delegated | Unattended | Outcome |
| --- | --- | --- | --- | --- |
| `covers` an `active` or `review` item | Tell the user the item, and any new information. Change nothing | Return the same | Report the same | `already in progress <ref>` |
| `covers` anything else, and the idea adds nothing it does not already say | Tell the user | Return it | Report it | `already tracked <ref>` |
| `covers` an inbox entry, or a `backlog` item with no `spec.md`, with new information | Append | Append | Append | `amended <ref>` |
| `covers` a `backlog` item with `spec.md` or `plan.md`, with new information | Append, then ask: revise, or leave as is | Append, then return `needs decision: revise <slug>` unless the brief answers it | Append, then revise | `revised <slug>`, or `amended <slug>` if left |
| `partly covers`, and the rest can stand alone | Create an item for the rest (step 4), naming the match under References | Same | Same | `created <slug>` |
| `partly covers`, and the rest cannot stand alone | Treat it as `covers` with new information | Same | Same | as that row |
| No match | Create (step 4) | Create | Create | `created <slug>` |

- **Append only what is new.** Add it under a dated `## Added <YYYY-MM-DD>`
  heading that says where it came from, and never rewrite what is there. For an
  item, append to `initial-request.md` if it exists, otherwise `intake.md`. For
  an inbox entry that is a folder, append to the Markdown file that
  `tcw work inbox show <entry>` prints as its body. Commit as in step 4.
- **Revise** means re-running `spec`, and `plan` if one exists, after the
  append. Gate each one with `tcw work stage gate`, and commit each artifact
  separately. Hand them to subagents under the `tcw-work` skill's
  `delegation.md` if you can dispatch; otherwise run them yourself. Report
  `revised` only once every artifact being revised is written: the spec alone
  when the item has no plan. Inside a
  `tcw-extras-autonomous-work` session, its advisors stand in for "ask", and
  this default applies only where that skill has no rule.
- **Closed items are never the deciding match.** Name a close one under
  References. If it was discarded, put its resolution in the reason part of
  your one outcome line.

## 4. Create

Ask only what the brief or the conversation has not already answered, and ask
all of it in one message. A request made in chat is its own source, so it
already answers the references and origin questions.

| Question | Accepted answers | Delegated | Unattended default | Recorded as |
| --- | --- | --- | --- | --- |
| Known blockers? | Slugs · "no" · a description (search, then confirm with the user) · "determine automatically" (search, and do not confirm) | From the brief. If the brief is silent, or describes a blocker you would have to confirm, create nothing and return `needs decision: blockers` with step 2's `blocks` lines as candidates | determine automatically | `--blocked-by <ref>` per blocker, plus a line saying why |
| Reference material? | Anything given. Material already in the conversation or brief counts | From the brief; if it has none, write "none given in the brief" (`request` asks again later) | Take it from context; if there is none, write "no user to ask; none in context" | `## References`, one line of why it matters each |
| A bug, or a follow-up to another item? | Yes, naming the item or symptom · no | From the brief's origin; if it has none, write "none given in the brief" | The item being worked when the idea came up | `## Origin`, plus the `bug` tag for a bug |

**Record a blocker only when the idea cannot proceed until that item lands.**
Sharing a topic, touching the same files, or a preferred order does not count;
those go under References. Determining blockers automatically uses step 2's
`blocks` lines. It is not a second search.

Pick tags from `tcw work tags list`, and pipe the body in. `tcw work new` stores
it as the item's `intake.md`, which the `request` stage reads later:

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

Then commit only what you changed, in the repository that holds the store. A
store can live in a different Git repository from the code, and a narrow commit
keeps a working agent's own staged changes out. Run `tcw work path` to get the
store folder, then, with the absolute paths you created or changed (the item
folder `tcw work path <slug>` prints, or the entry file under
`tcw work inbox path`):

```bash
git -C <store folder> add -- <absolute paths>
git -C <store folder> commit -m "<what was filed, and where it came from>" -- <absolute paths>
```

Stage first: a new file git has never seen, such as a raw inbox entry, cannot be
committed by path alone.

A batch of related leftovers, such as one review's findings, may be one item
or one inbox entry. Treat the batch as one idea.

**Strict tracker mode.** If `tcw work new` refuses and points you at
`tcw work tracker import`, the project requires a ticket first. Interactive:
relay that. Delegated: return it. Unattended: write the idea as a raw inbox
entry instead (step 1's shape), and report `deferred to inbox`.

## 5. Report

Exactly one of these lines, with its reference and a one-line reason:

- `created <slug>`
- `amended <ref>`
- `revised <slug>`
- `already tracked <ref>`
- `already in progress <ref>`
- `deferred to inbox <entry>`
- `needs decision: <clarify | revise <slug> | blockers>`, followed by step 2's
  lines, so whoever asks the user does not search again.

In an Interactive run, say the reference to the user.
