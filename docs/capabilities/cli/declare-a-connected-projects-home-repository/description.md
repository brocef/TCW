As a user working in a checkout that holds only some of my connected projects'
repositories, I declare where a *connected project* comes from, beside the
location that says where it sits on my own machine. The entry under `projects:`
in `tcw-config.yaml` takes the same `repository` block a component store takes —
`url`, and optionally `ref`, a `path` within the repository, and a local
`checkout` — so one configuration serves a machine that has the repository and
one that does not.

A project that is already here always wins: the declaration answers only when the
location names nothing, so nothing about a machine that has the project changes,
and nothing is contacted on its behalf. Where the project is absent, TCW says it
is declared but not on this machine and names the remote, rather than reporting
that the project was never declared.

`tcw provision` is what obtains it, and it follows the connections: a project
obtained because it was declared may itself declare others, and those are
obtained in the same run. One working copy serves every project and store naming
the same repository and ref. Declarations therefore stay where the knowledge is —
my project declares only its own connection, and the project on the other side
declares its own — so I never have to name a repository my project does not know
about.

Provisioning still only ever happens because I asked for it. Declaring a
connected project's home repository does not make any other command reach the
network.

`upstream` entries take the same `path` / `repository` forms, and
`tcw provision` obtains them the same way — but stops there: what an upstream
itself declares is its own to obtain, so a reader never fetches a repository
named only by something it reads.
