# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixed

`tcw work inbox show` and `tcw work inbox accept` now take either identifier that
`tcw work inbox list` prints. The list shows an entry as `request.md | file |
request`, and until now only `request.md` worked — typing the name the same
command had just shown you failed. If a name matches more than one entry and is
not itself an exact entry name, you get an error listing the candidates instead of
one being picked for you; nothing is consumed in that case.

Accepting a request that was delegated from another project now keeps the epic it
was stamped with. Previously the link was dropped on acceptance, so a slice
quietly detached from the initiative that asked for it and stopped appearing in
that epic's rollup.

`tcw work delegate`'s help text said its first argument was a child node path. It
is the child's canonical project ID — the form `tcw work nodes` lists. The command
always behaved that way; only the help was wrong.

Work items being claimed by another process are no longer mistaken for missing
ones. Starting an item is briefly a two-step move, and during that instant other
commands could read the item as absent — so a blocker that was being started
elsewhere silently stopped blocking, and adding it as a blocker recorded it as
free text instead of a real link. Reads now settle across that instant. Ordinary
lookups are unaffected: asking for an item that genuinely does not exist still
answers immediately.

If a process died mid-claim, reads now say the item has an interrupted claim and
point at `tcw work start <slug> --take-over --owner <identity>` to recover it,
rather than reporting it missing. Starting a *different* item that is blocked by
such an item reports it as a blocker, as it should.

Opening a work item in the local web app while it is being moved no longer risks
an internal error; the app now retries and shows the item in its new state.

When two people (or two agents) act on the same work item at the same moment, the
one that loses now leaves the item completely untouched. Before, it had already
written its own answer before discovering it had lost — so completing an item as
"done" while someone else completed it as "wontfix" could leave the item filed
under completed while reading `wontfix`, and submitting an item someone else had
just moved could clear the owner off their copy. The command that loses now says
so and changes nothing.

Creating or editing an item that something else moves at the same instant now
reports a plain error naming the item, instead of an internal error. The message
includes the item's name, so if `tcw work new` hits this, you can still find the
item it created.

Reconciling an epic with `--commit` now tells you when the commit was refused —
by a pre-commit hook, a signing key it could not use, or anything else git
declines — instead of showing an internal error. The message says the rollup was
written and staged, so you know the work is sitting in your index rather than
lost, and re-running the command once the cause is fixed now finishes the job.
Previously that retry reported success without ever committing.
