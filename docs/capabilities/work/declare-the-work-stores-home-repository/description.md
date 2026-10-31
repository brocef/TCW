As a project owner whose work items live in a repository other than the code
repository, I can record that repository in `tcw-config.yaml` under
`work.repository` — its URL, optionally a ref, the store's path within it, and
optionally where a working copy should live on this machine. The declaration is
portable: it describes where the store comes from rather than where it happens to
sit on one disk, so a machine that has never seen the store can obtain it with
`tcw project provision`.

Declaring costs me nothing where the store is already present. A checkout that
resolves `work.path` to a real store keeps using it untouched, and the
declaration is consulted only when that store is absent — so the same config
works on a laptop that has the folder and in a session that cloned only the code.

Where the store is absent, TCW tells me so in those words, naming the declared
remote and the command that fetches it, `tcw project provision --component work`,
instead of reporting that the project has no work component.

With no argument, `tcw project provision` obtains every declared store that is
missing and then fetches the projects of the family that are not here;
`tcw project provision --component work` obtains this store alone and fetches no
project (see [Provision declared
stores](tcw://C/cli/provision-declared-stores)). The declaration's `ref` may
name a branch, a tag or a commit; one that names none of these fails, with
git's reason.

**TCW never pulls or pushes that repository.** It reads and writes the files in
the working copy, and committing and publishing them is mine to do, as in any
other repository.

A declaration I got *wrong* is held to the same standard. A missing URL, a store
path that escapes the repository root, an unrecognized key — each is reported
against the configuration line that carries it, by every command and not only by
`tcw validate`. Nothing falls back to reporting that the project has no work
component, which would point me at `tcw project new` and scaffold a second, empty store
beside the real one.
