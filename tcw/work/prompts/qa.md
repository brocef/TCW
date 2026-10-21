# Stage: qa

**Purpose.** Check the product's behavior against the request and the QA plan:
what a user will now be able to do, tried the way a user would.

**Inputs.** The request's Product changes, from `tcw work show <slug>`, and the
newest comment there whose first line is `QA plan`. With no QA plan, test
against the request's Product changes and say so.

**Resuming.** Read the newest handoff first, as a description of the work when
it was written, and check for anything newer before trusting it.
<!-- backend: filesystem -->
It is the newest `handoff-*.md` in `tcw work path <slug> qa`. To leave one,
write it to `tcw work path <slug> qa --handoff`.
<!-- /backend -->
<!-- backend: jira -->
It is the newest comment in `tcw work show <slug>` whose first line is
`Handoff`. To leave one, post it with `tcw work comment <slug>`, `Handoff` as
its first line.
<!-- /backend -->

<!-- backend: filesystem -->
**Produce** one round at `tcw work path <slug> qa --next`, starting with the
front matter review uses:

```yaml
---
verdict: accepted        # or rejected
judges: 3                # the newest implement round
---
```

`judges` is the highest `N` among the `round-N.md` files in
`tcw work path <slug> implement`, or 0 when there are none. Under it, list each
QA plan scenario as passed, failed or not run, with the evidence for each.

## Steps

1. Run each scenario in the QA plan, in the environment it names.
2. Judge the product against the request's Product changes and each
   scenario's expected behavior. **No claim without output or an observation
   from just now.**
3. `accepted` only when every scenario passed, or the round says why one not
   run does not matter. Otherwise `rejected`, saying what implement must fix.
4. Write the round. By default you record the verdict yourself. If the
   project's instructions for this stage say a person decides the verdict:
   run the scenarios, present the evidence, ask the person for `accepted` or
   `rejected` with a reason, and write the round at `qa --next` recording
   their decision, with `decided-by: <their name>` beside `verdict` and
   `judges`. Do not choose the verdict for them. If they do not answer, write
   no round and say so.
<!-- /backend -->
<!-- backend: jira -->
**Produce** findings, not a verdict. In Jira, qa happens on the ticket, and the
ticket's status, which people move, is the verdict. You may run the scenarios
and post what you found with `tcw work comment <slug>`.

## Steps

1. Run each scenario in the QA plan, in the environment it names.
2. Post one comment listing each scenario as passed, failed or not run, with
   evidence. **No claim without output or an observation from just now.**
3. A person decides the verdict, never you. Ask them for it. When the person
   who decides gives you the verdict in this conversation, record it: accepted
   with `tcw work advance <slug> --to completed --reason "accepted by <name>:
   <why>"`, rejected with `tcw work advance <slug> --to implement --reason
   "rejected by <name>: <what to fix>"`, whose reason becomes the comment
   implement reads. They may instead move the ticket in Jira themselves. If
   they give no verdict, stop at qa and say the item waits for them.
<!-- /backend -->

## Exit badly

- _A scenario cannot be run_ (no environment, no account). Record it as not
  run and say what is missing; do not mark it passed.
- _The product does what the spec says but not what the request asked._ That
  is a finding for the person deciding, and for a postmortem.
