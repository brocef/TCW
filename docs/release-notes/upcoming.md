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
