# Migrating from 2.x to 3.0.0

Version 3.0.0 has **exactly one break**: a TCW project now keeps all of its
configuration in `tcw-config.yaml`. The two config files that used to live
*inside* a store are no longer read.

**Most projects have nothing to do.** Those files only ever held one key,
`extends`, and only a project that federates has one. If you have never run
`tcw taxonomy extends add` or `tcw capabilities extends`, the files do not exist
and there is nothing to migrate. Check quickly:

```sh
ls docs/taxonomy/config.yaml docs/capabilities/.config.yaml 2>/dev/null
```

Nothing listed means nothing to do. (Note the leading dot on the capabilities
one — a plain `find -name config.yaml` will not show it.)

## The break: `extends` moved into `tcw-config.yaml`

**Before**, inheritance was declared in a file inside each tree:

```yaml
# docs/taxonomy/config.yaml
extends:
    - acme-shared
```

```yaml
# docs/capabilities/.config.yaml
extends:
    - acme-shared
```

**After**, both are keys in the project's own config, beside the `path` and
`repository` keys those components already had:

```yaml
# tcw-config.yaml
id: my-project
taxonomy:
    extends:
        - acme-shared
capabilities:
    extends:
        - acme-shared
```

Nothing else about federation changed. The value is still a list of registered
project IDs, still validated the same way, still transitive, and a legacy
alias-to-path map still fails closed.

### What to do

For each of the two files you actually have:

1. Copy its `extends:` list into `tcw-config.yaml` under `taxonomy:` or
   `capabilities:`, keeping any `path` or `repository` already in that section.
2. Delete the old file.
3. Run `tcw taxonomy check` / `tcw capabilities check`.

Or let TCW write it for you — re-running the command writes the new key:

```sh
tcw taxonomy extends add acme-shared
tcw capabilities extends acme-shared
rm docs/taxonomy/config.yaml docs/capabilities/.config.yaml
```

### Nothing warns you

This is the part worth reading twice. An old file is not read, not reported and
not deleted — it is simply inert. A project that upgrades and does nothing
**silently loses its inherited entries**.

The symptom is `tcw taxonomy list` or `tcw capabilities list` showing only your
own entries, with none of the `acme-shared/…` ones you expect. If you see that
after upgrading, this is why.

One exception: a *corrupt* leftover file is still reported by `tcw validate`,
because refusing to parse is worth saying whether or not anything reads it.

## Two consequences worth knowing

**Inheritance now belongs to the project, not to the store.** A tree can live
outside its project (`taxonomy.path`) or in another repository
(`taxonomy.repository`), and can be shared by several projects. The declaration
used to sit in the shared folder, so every project reading it inherited the same
ancestors. Now each project declares its own, and two projects sharing one tree
may inherit differently.

That also makes a previously impossible arrangement work. If projects A and B
shared a tree and A declared `extends: [B]`, the shared file was B's declaration
too, so B extended itself and the read failed outright. With separate
declarations there is no collision: A resolves the shared terms twice, once as
its own and once under `B/`, each namespace honest about where it came from. If
you were working around that failure, you can stop.

**Inside a linked git worktree, `extends` follows the branch.** It is read from
the worktree's own checked-out `tcw-config.yaml`, so two branches can declare
different inheritance. This only differs from 2.x when `taxonomy.path` or
`capabilities.path` is a relative path pointing *outside* the worktree; a tree
that stays inside it already belonged to the branch.

## One more thing: writing the key re-renders the file

`tcw taxonomy extends add` and `tcw capabilities extends` now write
`tcw-config.yaml`, which means they rewrite it whole: keys, values and their
order survive, but comments and custom formatting do not. `tcw work tags add`
has always behaved this way; two more commands now do. If you keep comments in
that file, edit the key by hand instead.
