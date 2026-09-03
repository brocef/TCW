As a user working in a checkout that holds only some of my project graph's
repositories, I declare where a *connected project* comes from, beside the
locator that says where it sits on my own machine. The entry takes the same
`repository` block a component store takes — `url`, and optionally `ref`, a
`path` within the repository, and a local `checkout` — so one configuration
serves a machine that has the repository and one that does not.

A node that is already here always wins: the declaration answers only when the
locator names nothing, so nothing about a machine that has the project changes,
and nothing is contacted on its behalf. Where the node is absent, TCW says it is
declared but not reachable in this checkout and names the remote, rather than
reporting that the project was never registered.

`tcw provision` is what obtains it, and it follows the graph: a node obtained
because it was declared may itself declare others, and those are obtained in the
same run. One working copy serves every node and component naming the same
repository and ref. Declarations therefore stay where the knowledge is — my
repository declares only its own edge, and the node on the other side declares
its own — so I never have to name a repository my project does not know about.

Provisioning still only ever happens because I asked for it. Declaring a
connected project's home repository does not make any other command reach the
network.

Planning doc: 2026-09-03-connected-project-entries-declare-where-they-come-from-so-tcw-provision-can-obtain-a-node
