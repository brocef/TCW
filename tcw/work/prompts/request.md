# Stage: request

**Purpose.** Record what is being asked for and why, at a product level and for
any reader, before anyone decides what to build. Keep code references light
unless the work is technical by nature.

**Inputs.** What the item asks for, as `tcw work show <slug>` prints it, and the
person asking. Repository discovery is unrestricted.

**Resuming.** Read the newest handoff first, as a description of the work when
it was written, and check for anything newer before trusting it.
<!-- backend: filesystem -->
It is the newest `handoff-*.md` beside the file `tcw work path <slug> request`
names. To leave one, write it to `tcw work path <slug> request --handoff`.
<!-- /backend -->
<!-- backend: jira -->
It is the newest comment in `tcw work show <slug>` whose first line is
`Handoff`. To leave one, post it with `tcw work comment <slug>`, `Handoff` as
its first line.
<!-- /backend -->

**Produce** the request, in five sections:

- **What and why**: the change, and the reason for it.
- **Product changes**: what users will be able to do differently, and what the
  change adds, changes or removes. "None" is a valid answer; write it as such.
- **Out of scope**: what is deliberately left out.
- **Constraints**: deadlines, compatibility, anything that limits the answer.
- **References**: each with one line on why it matters.
<!-- backend: filesystem -->
Write it to `tcw work path <slug> request`. Keep any dated `## Added`
sections already there: they are amendments made after it was written.
<!-- /backend -->
<!-- backend: jira -->
The request is the ticket's description, and Jira owns it: never rewrite it on
your own judgment. When a section is missing or unclear, post a comment with
`tcw work comment <slug>` listing what is missing and proposing wording, for
the requester to adopt.

The requester decides when the request is ready. When they tell you to move
the item on, in this conversation, do it. If they adopted changed wording,
first put it into the ticket's description: write it yourself if your harness
can edit Jira tickets, or ask them to paste it in. Change only what they
adopted, and keep everything else in the description. Then read it back and
confirm the description now says what they adopted. Then run
`tcw work advance <slug> --reason "<who told you to move it>"`. A question,
such as whether accepting the wording moves the item, is not an instruction to
move it.
<!-- /backend -->

## Steps

1. **Ask the user what is unclear.** This stage exists to get input only they
   have.
2. **Ask for reference material**: docs, an issue, prior work, a related item.
   Do not fetch or judge it here. If there is none, write "asked; none
   provided" under References, so spec can tell that from never asking.
3. Write in the requester's terms. Do not specify a solution; that is spec's
   job, and doing it here hides the alternatives.

## Exit badly

- _The request contradicts something already true of the product._ Say so and
  ask, rather than recording a request nobody can satisfy.
- _The work is larger than one item._ Say so now; splitting after a spec is
  written wastes the spec.
- _There is no user to ask._ Write from the evidence available and mark each
  assumption, so spec knows which parts are inference.
