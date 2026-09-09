# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Instructions for the inbox stage, from the command line

`tcw work stage` now answers for every stage of the lifecycle, including the
inbox — the point where a raw drop becomes a tracked item. It used to answer for
six of the seven and return an error for that one, so the guidance on how to
turn an incoming request into a work item was only available to people who had
installed the agent plugin. Anyone who installed `tcw` on its own got nothing.

Because the inbox stage runs before an item exists, it is the one stage you run
without naming a work item:

```sh
tcw work stage inbox
```

Naming one is reported as a mistake rather than guessed at. Every other stage is
unchanged and still takes its work item, and what they print is unchanged too.

If you have written your own instructions for a stage, nothing about how they
are chosen has changed — the inbox stage now simply has a TCW default to fall
back to, the same as the rest.

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
