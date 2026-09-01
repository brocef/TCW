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

**The declaration governs writes as well as reads.** A store I obtained through
it publishes its transitions back to it — see
[publishing store writes](tcw://C/work/publish-store-writes-to-the-remote) — while
a store I already had at `work.path` does not, because a declaration that did not
answer the read does not cause a write.

A declaration I got *wrong* is held to the same standard. A missing URL, a store
path that escapes the repository root, an unrecognized key — each is reported
against the configuration line that carries it, by every command and not only by
`tcw validate`. Nothing falls back to reporting that the project has no work
component, which would point me at `tcw init` and scaffold a second, empty store
beside the real one.
