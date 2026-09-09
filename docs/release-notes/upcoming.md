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

The two questions are now two commands:

```sh
tcw work stage prompt plan             # what does the plan stage ask for?
tcw work stage begin plan my-item      # enter it: gates first, then instructions
```

**`begin` is the old command, renamed and otherwise untouched** — same gates,
same output, same exit codes. If all you want is to keep working the way you
were, insert the word `begin` and you are done.

**`prompt` is new.** It runs no gate at all, so it answers for a stage the item
is not ready for, which is exactly when you want to ask. Naming the item is
optional: without one you get the stage's generic instructions, with one you get
them resolved for that item — its tags, its documents, and, across a set of
connected repositories, that project's own configuration rather than the one you
happen to be standing in.

If you read a stage that is not legal for the item, it prints the instructions
anyway and says so in a note on the side. Worth knowing rather than silently
allowed: the built-in instructions for some stages name commands that change an
item's state, so reading them early is fine and following them is not.

The old spelling is not accepted and does not quietly do something else. It tells
you which of the two commands you meant and stops:

```
$ tcw work stage spec my-item
tcw work stage: 'spec' is not a subcommand; run `tcw work stage begin spec my-item`
to enter the stage, or `tcw work stage prompt spec` to read its instructions
without entering it
```

## Instructions for the inbox stage, from the command line

TCW now answers for every stage of the lifecycle, including the inbox — the point
where a raw drop becomes a tracked item. It used to answer for six of the seven
and return an error for that one, so the guidance on how to turn an incoming
request into a work item was only available to people who had installed the agent
plugin. Anyone who installed `tcw` on its own got nothing.

Because the inbox stage runs before an item exists, it is the one stage `begin`
takes with nothing after it:

```sh
tcw work stage begin inbox
```

Naming an item there is reported as a mistake rather than guessed at, on both
verbs.

If you have written your own instructions for a stage, nothing about how they are
chosen has changed — the inbox stage now simply has a TCW default to fall back
to, the same as the rest.

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
