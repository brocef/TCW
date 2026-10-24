As a user working an item in a project that keeps no capabilities ledger of its
own — a repository root that groups packages, for example — I name the
capabilities my item adds, changes or removes in another project's ledger by
writing each entry in the item's `capabilities.yaml`, at the root of the item's
folder, as that capability's full identifier, which names the project whose
ledger answers for it:

```yaml
new:
    - shared.capabilities/authoring/add-a-claim
changed:
    - server.capabilities/authoring/add-a-claim
```

The project can be any project TCW can locate from mine, a child or not. When
the item leaves implementation, `tcw work advance` checks each entry against
that project's own ledger, with the same rules as an entry of my own project: a
`new:` capability must exist and no longer read `Missing`, a `changed:` one
must still exist, and a `removed:` one must no longer exist as one of that
project's own capabilities. While the item is still being worked, `tcw validate`
checks the same file for entries that cannot be right. I reconcile each entry by
running `tcw capabilities set` (or `rm`) inside the project that owns it; from
any other project those commands refuse to change it.

An entry the gate cannot check is refused rather than passed: one whose project
is known but not on this machine, one whose project keeps no ledger, and one
naming my own project when it keeps no ledger. An entry naming a project TCW
cannot find at all, or still written in a TCW 3.x form such as
`server/authoring/add-a-claim`, is reported as wrong, the 3.x one as needing
tcw migrate. Every entry is checked against its owner's own capability as
its owner sees it, whether or not my project inherits from that owner:
`app.capabilities/cli/x` is my project's own capability, which exists once I
override the inherited one with `tcw capabilities set`, and
`core.capabilities/cli/x` is `core`'s, never my override of it. A `removed:`
entry is satisfied when its owner has no capability of its own at that path.
