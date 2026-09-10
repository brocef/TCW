As a user or agent, I work a lifecycle stage with two verbs, each doing one job.
`tcw work stage gate <id> <ref>` asks **may this run**: TCW checks the stage makes
sense for where the item is, runs whatever `pre` checks the project configured,
and answers with an exit code. It prints no instructions.
`tcw work stage prompt <id> [<ref>]` asks **what does it want**: the instructions,
resolved, with no legality check and no `pre` checks at all.

They are two verbs because one command answering both questions made the obvious
one unanswerable. On a project that gates a stage, asking what `plan` involves
ran the gate, the gate refused because the spec was not written, and I learned
nothing about planning — the command I would use to find out what to do required
me to have already done it.

And they print different things because printing the same thing twice is what a
reader has to explain away. Every view that composed a stage out of both showed
the instructions once from each verb; now the text exists in one place.

Those instructions are opinionated where it counts. `implement` does not merely
say to write the failing test first; it tells me what to do when a *new* test
passes on its first run — break the behaviour it names and confirm it goes red,
because a green that was never earned is the same as no test, and the explanation
for one is usually true and beside the point.

**With nothing configured for a stage, the instructions are TCW's own.** TCW
ships defaults for all seven lifecycle stages, `inbox` included, so the command
is useful on a project that has never written a line of lifecycle configuration.
A stage my project does configure replaces them outright; writing `builtin: true`
in that stage's `prompt:` list puts them back, composed with my own in the order
I declared them.

**`inbox` takes no work item reference, on either verb.** It runs before an item
exists, so there is nothing to resolve a stage against: `tcw work stage gate
inbox` and `tcw work stage prompt inbox` each take nothing after them, and naming
an item is reported as the mistake it is rather than guessed at.

**The shipped instructions name my item's own body, not a fixed filename.** The
`spec` and `plan` instructions resolve it the same way `tcw work show` does —
`initial-request.md` once the `request` stage has written one, and the
`intake.md` the item arrived as otherwise — so an item created from a pipe or
adopted from the inbox is never sent after a document nobody wrote. On an item
with neither, they name no file at all rather than inventing one, and the `spec`
instructions say to read a raw intake as the request instead of drawing
conclusions from the request that is missing.

They come out on **stdout alone**, so I can pipe them straight into an agent.
Every check's own output, and every error, goes to stderr — and any failure
prints *nothing* on stdout, so a pipeline receives the whole instruction or none
of it rather than a fragment.

**Neither verb writes anything**: no lifecycle document, no draft, no status
change, no field. Running either purely to read the instructions is safe, which
is what makes it usable — reaching a stage should not mean weighing whether
asking what to do will change something.

**`gate` refuses a stage that makes no sense for the item's current status,
before any hook runs**: `implement` on a backlog item, or `spec` on one already
closed. `verify` is legal from `active` as well as `review`, because an item can
be closed without ever having been submitted. `postmortem` is the out-of-band
exception, legal in review and after completion — but not on a discarded item,
which was closed without shipping.

**`prompt` refuses none of that**, which is the point of having it. Given an item
the stage is not legal for, it prints the instructions anyway and says so in a
note on stderr, leaving stdout carrying the instructions alone and the exit code
0. Worth the note rather than silent, because some built-in instructions name
commands that change an item's state — reading them early is fine, following them
is not.

**Every set of instructions says it ran no checks, and where the stage leads.**
Because `prompt` gates nothing, wanting the instructions is no longer a reason to
run `gate` — so the reminder rides with the text itself, wrapped around whatever
resolved: a line saying this ran no checks and naming my `gate` invocation, and a
closing section saying what to do once the stage's output is written. It wraps my
own `prompt:` bindings too. Overriding what a stage says is not overriding where
the lifecycle goes next.

The reference is optional on `prompt` and changes what resolves. Without one,
`when:` conditions do not match, a `generate:` hook receives no item, and the
body token falls back to its no-body text, so I get the stage's generic
instructions. With one, all three resolve against that item.

`--no-exec` is on both verbs and each reports only its own half: `gate` lists the
`pre` checks it would run, `prompt` lists the bindings it would resolve, marking
the ones a `when:` condition skipped. Neither runs anything, neither reads a
`file:` binding, and under the flag **neither prints anything on stdout** — the
plan goes to stderr, so a dry run can never be mistaken for the instructions. It
is how I read an unfamiliar project's lifecycle before triggering any part of
it.

A project-qualified reference resolves against the owning node, so I can ask
about a descendant's item from the enclosing project — including on `prompt`,
where it reads that node's `prompt:` bindings rather than the one I am standing
in.

**Under Claude I can take both halves in one read.** The `tcw-work-stage` skill
puts the stage's own working document and the instructions `prompt` resolves for
it into a single document, so I am not opening a file and running a command and
joining them in my head. It is an ergonomic over the two commands and nothing
more: it reads with `prompt`, so it runs no gate — and the text it delivers says
so itself, in the header every resolved prompt carries. A Codex user, who gets no
context injection, runs the two commands and reads the same header, which is why
that reminder lives in the CLI's output and not in the skill.
