As a developer arriving in a fresh checkout, I can run one explicit command,
`tcw provision`, to materialize every component store this project declares but
does not have here. It reports what it is about to contact before contacting it,
fetches into the location the declaration names or a per-machine cache, and
prints where each store landed.

Running it again does nothing: a store that already resolves is reported as
already available and no network call is made. `--dry-run` shows me the plan
without contacting anything, and `--refresh` brings an existing working copy back
to the declared ref.

Provisioning only ever happens because I asked for it. No other `tcw` command
reaches the network on a project's behalf, so a repository I have merely checked
out never fetches from a remote its config chose until I run this command. Nor
does it contact a remote other than the one it showed me: if the place a store
would be fetched into is already occupied by something else, I am told what is
there and nothing is contacted at all.

A failure — unreachable remote, unknown ref, refused authentication, or a
repository that turns out not to carry the store where the declaration says —
tells me the cause, exits non-zero, and leaves nothing new behind. A working copy
I already had is never deleted on my behalf.
