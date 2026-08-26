As a project owner whose work items live in a repository other than the code
repository, I can record that repository in `tcw-config.yaml` under
`work.repository` — its URL, optionally a ref, the store's path within it, and
optionally where a working copy should live on this machine. The declaration is
portable: it describes where the store comes from rather than where it happens to
sit on one disk, so a machine that has never seen the store can obtain it.

Declaring costs me nothing where the store is already present. A checkout that
resolves `work.path` to a real store keeps using it untouched, and the
declaration is consulted only when that store is absent — so the same config
works on a laptop that has the folder and in a session that cloned only the code.

Where the store is absent, TCW tells me so in those words, naming the declared
remote and the command that fetches it, instead of reporting that the project has
no work component.
