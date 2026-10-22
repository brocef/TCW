As a developer arriving in a fresh checkout, I can run one explicit command,
`tcw provision`, to obtain the component stores this project declares but does
not have here. It reports on standard error what it is about to contact before
contacting it, fetches into the location the declaration names or a
per-machine cache, and says where each store landed. It prints nothing on
standard output.

It serves the three component stores, `work`, `taxonomy` and `capabilities`.
It does not fetch connected projects: a project not on this machine is
reported with where its manifest entry places it, the repository the entry
gives, and the command that fetches it (a `project provision` command, which
TCW-115 adds).
`--component` limits it to one store (repeat it for more than one). With no
component named, every store that declares a home repository is provisioned.
Each is resolved, reported, and failed on its own, so one store's bad
declaration neither suppresses nor corrupts another's result.

Obtaining a missing copy is all it does. No `tcw` command pulls, pushes or
updates a provisioned copy: bringing one up to date, and committing and pushing
what I change in it, are mine to do (or my project's own hooks').

Running it again does nothing: a store that already resolves is reported as
already available and no network call is made. **That covers whatever
resolution can reach**, which includes a store sitting inside a project I
already have here, matched against the manifest entries that give that
project's repository — so a workspace laid out differently from the way its
configuration describes it does not clone a second copy of a repository it is
standing next to. `--dry-run` shows me the plan without contacting anything.

Provisioning only ever happens because I asked for it. No other `tcw` command
reaches the network on a project's behalf (apart from a project that keeps its
work items in Jira, which reaches Jira), so a repository I have merely checked
out never fetches from a remote its config chose until I run this command. Nor
does it contact a remote other than the one it showed me: if the place a store
would be fetched into is already occupied by something else, I am told what is
there and nothing is contacted at all.

It does not ask me anything while it clones: not for a password or token, not
for an ssh key's passphrase, and not whether to trust a server it has not met.
Where git or ssh would need an answer, the clone fails instead and I am told
git's reason. So a private repository needs credentials git can use without
asking, from a credential helper or an ssh key loaded in an ssh agent. The
exception is an ssh command I have set myself (`GIT_SSH_COMMAND`, `GIT_SSH`, or
`core.sshCommand` in my global or system git config or given on the git
command line, not the current repository's own setting): it is used as it is,
so ssh may still ask.

A failure — unreachable remote, unknown ref, refused authentication, or a
repository that turns out not to carry the store where the declaration says —
tells me the cause, exits 1, and leaves nothing new behind. A working copy I
already had is never deleted on my behalf.
