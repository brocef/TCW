# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

**This is a major version, and it has exactly one break.** `tcw work stage` is
now two commands instead of one. Everything else here is an addition or a
document you did not have before. Nothing about your configuration, your work
items, or your history changes.

[**Read the 1.x → 2.0.0 migration guide**](../migration-guide-1.X-to-2.0.0.md) —
it is short, and the break is a search and replace.

## One command was answering two questions

`tcw work stage <stage> <item>` did two jobs at once. It ran the gates that
decide whether an item may enter a stage, and it printed what that stage asks you
to produce. You could not ask the second question without paying for the first.

On a project that binds a check to a stage, that made the obvious question
unanswerable. Asking what the plan stage involves ran the check, the check
refused because the spec was not written yet, and you were told nothing about
planning. The command you would use to find out what to do required you to have
already done it.

It is now two commands, and each does one job:

```sh
tcw work stage gate plan my-item       # may it run? checks only — prints nothing
tcw work stage prompt plan             # what does the plan stage ask for?
```

**`gate` is the refusal.** It checks the stage makes sense for where the item is
and runs whatever your project bound to it, and then it stops. Success is exit 0
and silence; the exit code is the answer. It changes nothing — no status, no
document, no field — so there is nothing else for it to report.

**`prompt` is the instructions**, and the only command that prints them. It runs
no check at all, so it answers for a stage the item is not ready for, which is
exactly when you want to ask. Naming the item is optional: without one you get
the stage's generic instructions, with one you get them resolved for that item —
its tags, its documents, and, across a set of connected repositories, that
project's own configuration rather than the one you happen to be standing in.

If you read a stage that is not legal for the item, it prints the instructions
anyway and says so in a note on the side. Worth knowing rather than silently
allowed: the built-in instructions for some stages name commands that change an
item's state, so reading them early is fine and following them is not.

Splitting them this way means the instructions exist in one place instead of
coming out of two commands identically, which is what made anything that showed
you a stage show you the same text twice.

The old spelling is not accepted and does not quietly do something else. It tells
you both commands and stops:

```
$ tcw work stage spec my-item
tcw work stage: 'spec' is not a subcommand; run `tcw work stage gate spec my-item`
to check the stage and run its checks, or `tcw work stage prompt spec my-item` for
its instructions
```

## Every stage's instructions now say where they sit

Because `prompt` runs no checks, wanting the instructions is no longer a reason
to run the gate. So the instructions say so themselves. What `prompt` prints is
wrapped in two lines you did not write:

- at the top, that this text ran no checks, and the exact `gate` command for
  this stage and item;
- at the bottom, what to do once the stage's output is written — the next stage,
  or the transition that has to happen first.

Your own stage instructions get the same wrapper. Overriding what a stage says is
not overriding where the lifecycle goes next. A stage that resolves to nothing
stays silent and gets no wrapper, since a header and footer around an empty
middle would read as a stage that failed.

If you compare stage output byte for byte anywhere, that comparison will move
once. It is the only text this release changes.

## Reading a stage in one piece, if you drive TCW with Claude

Working a stage has always meant two reads: the document describing how to work
it, and the instructions your project resolves for it. The plugin now ships a
skill, `tcw-work-stage`, that hands you both at once — give it the stage and the
item and it returns one document.

It is built on the reading verb, so it runs no gate — and the instructions it
hands you carry that reminder themselves, along with the `gate` command to run.
Treat it as a way to see everything before you start, not as a way to start.

This one is Claude-only: it works by running commands and folding their output
into the skill, which Codex does not do. Nothing moved behind it — the stage
documents and both commands are unchanged, so running them yourself gets you the
same text in two pieces.

## Instructions for the inbox stage, from the command line

TCW now answers for every stage of the lifecycle, including the inbox — the point
where a raw drop becomes a tracked item. It used to answer for six of the seven
and return an error for that one, so the guidance on how to turn an incoming
request into a work item was only available to people who had installed the agent
plugin. Anyone who installed `tcw` on its own got nothing.

Because the inbox stage runs before an item exists, it is the one stage that
takes nothing after it, on either verb:

```sh
tcw work stage prompt inbox
```

Naming an item there is reported as a mistake rather than guessed at.

If you have written your own instructions for a stage, nothing about how they are
chosen has changed — the inbox stage now simply has a TCW default to fall back
to, the same as the rest.

## Things that were wrong, found in review before this shipped

A last review pass over this release found several things worth naming, because
two of them would have cost you something real.

**Finishing a rejected work item.** The `verify` stage ends one of two ways: you
accept the work, or you send it back. The closing line of its instructions named
only the first, and it is the last thing you read before acting. Follow it after
a rejection and the item closed as *done*, carrying the record of the rejection
into the completed folder with it. That line now names both endings.

The command that closes an item still does not refuse one you rejected, and that
is deliberate. An item sent back once, reworked, and then accepted legitimately
carries both records, so refusing on the presence of a rejection record would
refuse perfectly good work. Getting there is the reviewer's call, and the
instructions now point both ways rather than one.

**Reading a stage for an item in another repository.** TCW lets you name an item
in a connected project, and the instructions come back resolved against *that*
project. But the commands quoted back at you had the project prefix stripped, so
running one acted on your own repository instead. Where two projects had filed a
similarly-named request, that silently pointed at the wrong item. The prefix now
survives.

**Silencing a stage never worked as documented, and now it does.** If you wanted
a stage to say nothing, four different documents told you to write
`prompt: [{blob: ""}]`. TCW rejected it as blank, dropped the binding, and fell
back to printing its own built-in instructions — the loudest possible outcome
from the setting meant to produce silence.

Rather than correct four documents to describe a workaround, that spelling now
works. A stage silenced this way prints nothing at all, and gets no header or
footer either. If you tried it once and gave up, try it again.

An empty list, `prompt: []`, is still refused, and the difference is the whole
point: writing the opt-out down is a choice you made, while an empty list cannot
be told apart from never having written the setting.

**Smaller things.** `tcw work stage inbox` pointed you at a command that is
itself refused. A typo in the verb was told the seven old spellings were valid.
Asking what an inbox stage would run stayed silent about checks it was skipping
rather than naming them. The Codex plugin listed eight skills while shipping
nine, so the newest was invisible to anyone reading the description.

**One thing to check if you bound hooks to the inbox stage.** Those bindings
could never run before, because the old command refused that stage outright. They
run now.

## A shorter README, and a set of guides behind it

The README had grown to 1628 lines and read as a reference manual. Someone
deciding whether TCW was worth adopting had to read the whole thing to find out.

It is now about 320 lines and answers that question directly: what problem TCW
solves, what using it actually looks like end to end, why a codebase split across
many repositories is the case it is built for, and what adopting it costs you.

The reference material did not go away. It moved into six guides under
`docs/guide/` — one each for work, taxonomy and capabilities, working across
repositories, configuration, the web viewer, and linking and validation — and the
README links to all of them.

Two things were wrong and are now fixed. The README claimed that being able to
run against Jira or a wiki is what makes TCW work at scale, while also saying
those adapters were not built; it now says plainly that only filesystem storage
ships today. And a missing heading meant the whole `tcw work` command reference
was filed under a section about documentation settings, in GitHub's outline and
in every Markdown viewer.
