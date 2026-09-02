# A configured component path that is absent advises `tcw init`

## Desired outcome

A node whose `<component>.path` names a location that is not there says so, and
names the path. It never advises `tcw init`, which would scaffold a second,
empty store beside the configured one.

## Context

With a configured path and **no** `repository:` declaration, every read command
reports the node as having no such component at all:

```
$ cat tcw-config.yaml
id: my-project
taxonomy:
    path: vendor/taxonomy/docs/taxonomy      # not present in this checkout

$ tcw taxonomy list          # exit 1
tcw taxonomy: no tcw taxonomy node here — run `tcw init` in the project folder.
```

The configured path is never mentioned, and the suggested command is the one
hazard `find_node`'s comment (`tcw/store/fs.py:202-210`) says the resolution
ladder exists to avoid — "which would send you to `tcw init` and scaffold a
second, empty store beside the real one". Work behaves identically:

```
$ tcw work list              # exit 1, with work.path configured and absent
tcw work: no tcw work node here — run `tcw init` in the project folder.
```

`tcw validate` gets work right and is silent for the trees:

```
$ tcw validate               # exit 1
work check: …/tcw-config.yaml: work.path is not a directory: …/vendor/taxonomy/docs/work
1 problem(s).
```

So the good message already exists — `validate` composes it for work — but the
read commands do not use it, and `validate` does not check `taxonomy.path` or
`capabilities.path` for existence at all.

## Why it happens

`resolve_store` (`tcw/store/fs.py:742`) takes rule 4 when no declaration is
present, `_open_at` raises a bare `ValueError` for the unusable path, and the CLI
renders that as its generic "no node here" text. The configured path is known at
the point of failure; it is simply not carried into the message.

## Relationship to the existing backlog item

`2026-09-01-a-broken-work-path-is-hidden-when-a-repository-is-also-declared`
covers a path **and** a declaration together, where rule 1's failure is discarded
in favour of rule 3's `StoreNotProvisioned`. This is the case with a path and
**no** declaration, which takes rule 4 and produces a different message.

The two are complementary, and their boundary is clean: that item argues "the
local path does not exist at all" should stay *silent* when a declaration is
present, because a provisioned node is normally in exactly that state. With no
declaration there is nothing to fall back to, so the same condition is
unambiguously an error and should be loud. Worth speccing together; they are not
duplicates.

## The case that prompted it

Evaluating git submodules as a layout for a work or taxonomy folder that lives in
another repository. A submodule mounted at a component path works when it is
checked out, but `git clone` without `--recurse-submodules` — the default in most
CI and in cloud agent sessions — leaves the mount point empty, which lands
exactly here.

Two distinct shapes, both reproduced by hand:

- `path` pointing *inside* the submodule (`vendor/taxonomy/docs/taxonomy`) does
  not exist → the misleading message above.
- `path` pointing *at* the submodule mount (`vendor/taxonomy`) exists and is
  empty → for a tree store, accepted as a valid, empty taxonomy: exit 0, empty
  listing.

The second is the documented tree-store tradeoff at `_usable`
(`tcw/store/fs.py:2720-2739`) — "an empty taxonomy is a real state and nothing
distinguishes the two" — and that reasoning holds in general. It is worth
recording that in this one case something *does* distinguish them, cheaply and
locally:

```
$ git submodule status
-e10b6057… vendor/taxonomy          # leading '-' = not initialized
$ git ls-files -s vendor/taxonomy
160000 e10b6057… 0   vendor/taxonomy # mode 160000 = gitlink
```

Whether to consult that is a spec question, and it is secondary to the main
finding, which is not submodule-specific — a typo in `work.path` produces the
same "run `tcw init`" advice. Any such check is an FS-adapter diagnostic only:
git is the adapter's own substrate, no config surface is added, and another store
adapter simply never produces the message.

## Notes

- Reproduced by hand on `tcw 1.2.3` with a scratch superproject and submodule;
  all four command outputs above are measured, not reconstructed.
- No submodule concept should enter the model. The prime directive refuses it:
  a submodule is a git-and-filesystem construct. It is a layout a user may
  choose under the existing `path` mechanism, and the model stays unaware.
