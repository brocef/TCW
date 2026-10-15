## 1. Check the preconditions

Three things must hold. Each failure is a legitimate state, not an error to work
around — name the one that failed and stop.

```bash
gh auth status           # gh present and authenticated?
gh repo view --json nameWithOwner,url    # a GitHub repo to read issues from?
```

- **`gh` not found** → tell the user to install the GitHub CLI. Do not fall back
  to scraping the web UI.
- **Not authenticated** → tell them to run `gh auth login` themselves. It is
  interactive; do not attempt it for them.
- **No GitHub remote** → this project's issues do not live on GitHub. Say so.

## 2. Sweep the open issues

```bash
gh issue list --state open --limit 50 \
  --json number,title,body,author,labels,url,createdAt,comments
```

Only **open** issues. That is load-bearing — see §6.

If the limit truncates the list, **say what was dropped.** A partial sweep
reported as a clean one is worse than no sweep.

## 3. Drop the ones already tracked

An accepted issue writes its URL into the request of the work item it created
(§5), so the URL is the join key. Look for it among the items, finished ones
included (`tcw work list --all`):
<!-- backend: filesystem -->
search under the folder `tcw work path` prints for the URL.
<!-- /backend -->
<!-- backend: jira -->
search Jira for the URL, since each item's request is its ticket's description.
<!-- /backend -->
Then confirm a hit with `tcw work show <slug>`, which prints the item's stage,
its request and its comments.

A hit means this issue has been triaged before. **It does not mean the issue is
settled** — ask what actually happened to the item:

| Item stage                                          | What it means                        | What to do                                       |
| --------------------------------------------------- | ------------------------------------ | ------------------------------------------------ |
| inbox, request, spec, plan, implement, review or qa | Genuinely tracked                    | Report it, name the item, move on                |
| `completed`                                         | The change already shipped           | No new item. Offer a reply saying so, and close. |
| `discarded`                                         | It ended **without being done**      | Depends entirely on _why_ — read the reason first. |

The last two rows are the ones that bite. A discarded item means the project
already decided something about this issue and the reporter was never told: the
issue is still open, still unanswered, and re-triaging it from scratch would
relitigate a decision that has already been made.

**`discarded` is not a verdict — it is several.** The reason given when the item
was discarded is in its comments (`tcw work show <slug>`). Read it before
drafting anything:

| The reason says           | What it actually means                | Reply                                                                                         |
| ------------------------- | ------------------------------------- | --------------------------------------------------------------------------------------------- |
| not worth doing           | Genuinely rejected                    | The "not worth doing" outcome, reason on record. Close.                                       |
| a duplicate of an item    | Folded into another item              | Point at that item. Close.                                                                    |
| replaced by another item  | **Still wanted, tracked differently** | Find the replacing item and read what it did with the request — absorbed, or deferred?        |

Replacement is the trap. It does not mean no. The replacing item may have
absorbed the request, or it may have _deferred_ it and written it down so it
would not be lost — in which case the honest answer is that nothing tracks it
today and it likely needs recreating as a follow-up item. Saying "we decided
against this" to a reporter whose request was merely postponed is the worst reply
this procedure can produce.

## 4. Triage what is left

Read each issue in full (`gh issue view <n> --comments` when the thread matters).
Then decide, before creating anything:

| Outcome             | Meaning                                                    | Result                            |
| ------------------- | ---------------------------------------------------------- | --------------------------------- |
| **Worth doing**     | A real change this project should make                     | → §5, becomes a work item         |
| **Duplicate**       | Of another open issue, or of an existing work item         | No item. Close with a pointer.    |
| **Not worth doing** | Out of scope, contrary to the design, or simply not wanted | No item. Close with the reason.   |
| **Ill-defined**     | May be real, but there is not enough here to act on        | No item. Ask for what is missing. |

Only the first creates a work item.

To check for duplicates, search **both** queues — the other open issues from §2,
and the existing work items (`tcw work list --all --json` for titles and tags,
then `tcw work show <slug>` on the likely ones). An issue duplicating an item
that already exists is the case most easily missed, because the two are worded
differently.

**Recommend, then ask.** The rejection outcomes are the user's call, not yours.
Say which outcome you think fits and why, and let them decide — especially for
"not worth doing", which is a judgment about the project's direction.

## 5. Accept: create the work item

Per the inbox stage's instructions (`tcw work stage prompt inbox`) — retitle as
a change, pick tags, split if it is really several items. What you pipe into
`tcw work new` becomes the item's request, which the request stage shapes later.

Compose that text first — piping the bare issue body is not enough, because it
carries none of the provenance the later steps read back. It opens with an
**`## Origin`** section recording two things:

1. **The issue's number, URL, and reporter.** The URL is what §3 looks for on
   the next sweep; without it the issue resurfaces forever.
2. **The reporter's own words, attributed and quoted.** Do not rewrite them into
   first person. The maintainer did not ask for this — someone else did, and the
   distinction is what the qa stage needs later to check the work against what
   was actually reported.

Read the issue with `gh issue view <n> --json number,url,author,body`, then pipe
the composed document in — a quoted heredoc, so nothing in the reporter's text
is expanded by the shell:

```bash
tcw work new "<retitled as a change>" --tag <tag> [--priority <p>] [--effort <e>] <<'MD'
# <retitled as a change>

## Origin

GitHub issue [#42](https://github.com/owner/repo/issues/42), filed 2026-07-18
by @octocat.

> <the reporter's text, verbatim>
MD
```

Tags must already be registered (`tcw work tags add <tag>`) or the command
refuses.

If the project already has its own convention for recording provenance, follow
that one instead — a second heading that means the same thing is drift.

## 6. Reply to the reporter

**An issue that is triaged and then left silent is a worse experience than one
nobody read.** Offer a reply for every issue, matched to its outcome:

| Outcome         | Reply                                                          |
| --------------- | -------------------------------------------------------------- |
| Worth doing     | Acknowledge, and name the work item now tracking it            |
| Duplicate       | Point at the original, close                                   |
| Not worth doing | Give the actual reason, close                                  |
| Ill-defined     | Ask for the **specific** missing detail — not "please clarify" |

```bash
gh issue comment <n> --body "<text>"
gh issue close <n> --comment "<text>"
```

**Why closing matters mechanically:** §2 lists only open issues, so a closed
issue never resurfaces. The reply _is_ the record of the rejection — which is
why an ill-defined issue deliberately stays **open**: it is waiting on the
reporter, and seeing it again next sweep is the correct prompt to chase it. When
you meet an issue where you already asked for detail and the reporter has not
answered, say so and move on.

## 7. Report

Close out with what happened per issue — accepted (with slugs), rejected (with
outcomes), already tracked, and anything the sweep did not reach. If the user
declined replies, say which issues are still open and awaiting one.

## 8. Closing the loop when the work item ends

An accepted issue was told it is being tracked. **That is a promise, and this
section is where it is kept.** Everything above happens once, at intake; this
happens later, when the item that came out of it reaches `completed` or
`discarded`. Nothing in TCW prompts you here: an item ending prints no
reminder, so run this section whenever you see an item from an issue end, and
on every sweep (§3 finds the ended ones).

Find the issue in the item's request:

```bash
tcw work show <slug>      # the request, then the comments; read its ## Origin
```

No `## Origin`, or no issue URL in it → the item did not come from an issue and
there is nothing to do here.

**What to say depends on how the item ended**, and the endings do not mean the
same thing to a reporter:

| How it ended                        | Reply                                                               | Close the issue?     |
| ----------------------------------- | ------------------------------------------------------------------- | -------------------- |
| `completed`                         | It shipped — say in which version                                   | **Yes**, once a release carries it |
| `discarded` as a duplicate          | Name the item that absorbed it                                      | **Yes**              |
| `discarded` as not worth doing      | The actual reason it was not taken on                               | **Yes**              |
| `discarded`, replaced by another    | What replaced it — **and whether the ask was absorbed or deferred** | **Only if absorbed** |

**A replaced item is the one to slow down on.** It does not mean the request was
refused. The replacing item may have absorbed it, or may have _deferred_ it and
written it down so it would not be lost. Closing the issue in the second case
tells someone their request was declined when it was merely postponed — the same
mistake §3 warns about, except here it is irreversible and public rather than
just a mis-triage. Read what the replacing item actually did with the ask
before drafting anything, and leave the issue open when it was deferred.

A completed item is not yet something the reporter can install. Closing the
issue before a release carries the change tells them it is fixed when they
still cannot get it, so reply and close once it is released.

```bash
gh issue close <n> --comment "<text>"    # released, duplicate, not worth doing
gh issue comment <n> --body "<text>"     # replaced but deferred: reply, leave open
```
