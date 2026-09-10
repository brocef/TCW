# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

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

## The board now tells you what is waiting in the inbox

Raw requests dropped into a project's inbox are not work items yet, so they have
never appeared on the board — which made them easy to forget entirely.

`tcw work list` now says how many are waiting. The count prints under the board,
and a project with an empty inbox says nothing. Listing descendant projects with
`-i` counts each one separately and names it, so you can see at a glance which
repository has requests nobody has looked at.

The board itself is unchanged: the counts are printed alongside it, not as rows,
so anything you pipe the board into still sees one line per work item.

