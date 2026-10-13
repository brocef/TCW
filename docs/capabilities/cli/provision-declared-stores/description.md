As a developer arriving in a fresh checkout, I can run one explicit command,
`tcw provision`, to obtain what this project declares but does not have here.
It reports on standard error what it is about to contact before contacting it,
fetches into the location the declaration names or a per-machine cache, and says
where each store landed. It prints nothing on standard output.

It serves all three component stores **and my connected projects**. A project I
connect to may declare the repository it lives in, and `tcw provision` obtains it
after the stores — following the trail, since a project it has just obtained
may declare others. That is the one place it contacts a repository I did not name
myself, so every remote is printed before it is contacted, and `--dry-run` plans
the whole walk without a network call, telling me plainly that a project it has
not fetched may declare more. `--component` limits **the store pass** to
`work`, `taxonomy`, or `capabilities` (repeat it for more than one); connected
projects are obtained either way. With no component named, every store that
declares a home repository is provisioned. Each is resolved, reported, and
failed on its own, so one store's bad declaration neither suppresses nor
corrupts another's result.

Obtaining a missing copy is all it does. No `tcw` command pulls, pushes or
updates a provisioned copy: bringing one up to date, and committing and pushing
what I change in it, are mine to do (or my project's own hooks').

Running it again does nothing: a store that already resolves is reported as
already available and no network call is made. **That covers whatever resolution
can reach**, which includes a store sitting inside a project I already have
here — so a workspace laid out differently from the way its configuration
describes it does not clone a second copy of a repository it is standing next
to. The same holds for a connected project — one I can already reach is never
fetched, whoever declared where it comes from, so declaring a connection from
both sides costs me nothing. `--dry-run` shows me the plan without contacting
anything.

Provisioning only ever happens because I asked for it. No other `tcw` command
reaches the network on a project's behalf (apart from a project that keeps its
work items in Jira, which reaches Jira), so a repository I have merely checked
out never fetches from a remote its config chose until I run this command. Nor
does it contact a remote other than the one it showed me: if the place a store
would be fetched into is already occupied by something else, I am told what is
there and nothing is contacted at all.

A failure — unreachable remote, unknown ref, refused authentication, or a
repository that turns out not to carry the store where the declaration says —
tells me the cause, exits 1, and leaves nothing new behind. A working copy I
already had is never deleted on my behalf.
