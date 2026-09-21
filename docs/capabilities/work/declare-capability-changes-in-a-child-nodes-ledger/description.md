As a user working an item on a board whose own node keeps no capabilities ledger
— a repository root that groups packages, for example — I name the capabilities
my item adds, changes or removes in a child's ledger by starting each path in the
item's `capabilities.yaml` with the child's project id:

```yaml
new:
    - proposit-shared/authoring/add-a-claim
changed:
    - proposit-server/authoring/add-a-claim
```

The child must be declared under my node's `connected-projects.children`.
`tcw work complete` then checks each path against that child's own ledger, with
the same rules as a local path: a `new:` capability must exist and no longer read
`Missing`, a `changed:` one must still exist, and a `removed:` one must no longer
exist as one of the child's own capabilities. The part after the child's id is
read the way the child reads it, so it can name a capability the child inherits,
including one the child has overridden. I reconcile each path by running
`tcw capabilities set` (or `rm`) inside the child, with the path after the id.

A path the gate cannot check is refused rather than passed: a child that is
declared but not present in this checkout, one with no ledger, one whose ledger
is declared but not provisioned, and an unqualified path on a node with no ledger
of its own. When my node does keep a ledger, a path is still read as an inherited
one when its first segment names a project my ledger extends; and a first segment
that names both a child and a namespace my ledger already shows is refused as
ambiguous instead of guessed at.
