# Consolidating external plans

**This page holds only the part of this procedure a project cannot replace.**
For the rest, run `tcw work procedure prompt consolidate-plans` and follow what
it prints: this project's text if it configured one, TCW's own otherwise. The
rules on this page hold whatever it prints. If the command fails, say so rather
than working from memory.

## The two rules, before any step

**Start only when asked.** Do not begin a consolidation run on your own
initiative — not while doing adjacent work in `docs/`, not as a tidy-up pass, not
because you noticed a stray `plans/` folder. The user asks for it, or it does not
run.

**Never delete a source without a grouped, itemized approval.** Present every
document proposed for deletion by path, with its destination slug, as **one** ask
covering the whole run. Not one ask per file — that is unusable on a real run —
and not a blanket "may I clean up?", which is a yes to decisions the user has not
seen. Deletion happens after the answer, never before.

## Deletion is limited to what git can give back

Delete only files git has **already committed**, and only with `git rm`. A source
that is untracked, or tracked with uncommitted modifications, is **reported and
left in place**: its content exists nowhere else, so removing it is
unrecoverable. Two checks decide it, and anyone can re-run them:

| Check                                 | Meaning                                                                             |
| ------------------------------------- | ----------------------------------------------------------------------------------- |
| `git ls-files --error-unmatch <path>` | exit 0 → tracked; non-zero → untracked, do not delete                               |
| `git status --porcelain <path>`       | empty → committed as-is, deletable; any output → uncommitted changes, do not delete |

Report the skipped files with the reason. Committing someone else's stray file
just to make it deletable is not your call.
