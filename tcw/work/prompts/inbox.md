# Stage: inbox

**Purpose.** Decide whether each arrival becomes work. An arrival is not work
yet, so this stage takes no work item reference.

**Inputs.** Every arrival waiting in the inbox, and whatever in the repository
helps you understand one well enough to decide.
<!-- backend: filesystem -->
Each arrival is an item at the inbox stage: `tcw work list --stage inbox`
lists them, and `tcw work path <slug> request` names the request each carries.
<!-- /backend -->
<!-- backend: jira -->
Each arrival is a Jira ticket that is not an item yet.
`tcw work tickets list --json` gives each one's key, summary, status, reporter,
link and description. Decide from the summary and the description.
<!-- /backend -->

**Produce** no document. The outcome is each arrival accepted, turned away, or
left for a person, and a short report saying which and why.

## Steps

1. Read every arrival. One that describes several unrelated changes is several
   pieces of work; one change with several parts is one.
2. Check the board before accepting anything: `tcw work list`, then
   `tcw work show <slug>` for a likely match. An arrival already tracked is
   recorded on the existing item, with `tcw work comment <slug>` (the text on
   stdin), not accepted a second time.
3. Choose every tag that applies from `tcw work tags list`. Register a new
   one only if it will earn its place beyond this arrival.
4. Accept.
<!-- backend: filesystem -->
   `tcw work advance <slug>` moves the item to request. Add tags with
   `tcw work edit <slug> --tag <tag>`. For each extra piece of a split
   arrival, `tcw work new "<title>"` with its part of the text on stdin.
<!-- /backend -->
<!-- backend: jira -->
   `tcw work tickets adopt <KEY>` creates the item and moves the ticket to
   request. Add tags with `tcw work edit <slug> --tag <tag>`.
<!-- /backend -->
5. Turn away a duplicate, or something the project will not do.
<!-- backend: filesystem -->
   `tcw work discard <slug> --reason "<why>"`, naming the existing item for a
   duplicate.
<!-- /backend -->
<!-- backend: jira -->
   A person closes a turned-away ticket in Jira; TCW has no command for a
   ticket with no item. List it in your report with the reason, naming the
   existing item for a duplicate, for the person to paste when they close it.
<!-- /backend -->
6. Do not ask whoever filed it for more detail. They are usually not present
   to answer; the request stage asks.

## Exit badly

- _Too vague to decide._ Do not invent scope.
<!-- backend: filesystem -->
  Accept it and leave the questions for request, or leave it where it is and
  say why.
<!-- /backend -->
<!-- backend: jira -->
  Leave the ticket in the inbox and say so in your report for a person. Do
  not adopt a ticket to read it: an adoption is undone only by a discard.
<!-- /backend -->
- _You cannot tell whether it is already tracked._ Leave it, and name the
  items you suspect it overlaps.
