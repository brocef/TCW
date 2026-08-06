# Gitignore resolved work folders at init by default

## Product changes

`tcw init` / `tcw work init` should scaffold the end-state work folders as
`/dev/null` where git is concerned: `docs/work/completed/` and
`docs/work/discarded/` gitignored except for their `.gitkeep`. The folders still
exist in the tracked tree (so a fresh clone has them), but when an item is
completed or discarded its artifacts leave the repository rather than
accumulating in it.

The record is not lost: the item stays on disk on the machine that did the work,
and it stays in git history via the commits that tracked it while it was live
(assuming those commits are not rebased away).

## Technical changes

The transition half already works — `git_mv` untracks rather than moves when the
destination is ignored (`work/keep-resolved-work-out-of-git`). What is missing is
the setup half: today every node has to add the ignore rules by hand.

## Meta changes

The existing capability `work/keep-resolved-work-out-of-git` describes the manual
setup and needs rewording to say the default does it.
