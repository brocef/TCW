# Tags

A project-scoped classification vocabulary for grouping and filtering work across
statuses. Tags are descriptive facets — `cli`, `docs`, `bug`, `tech-debt` — and
change nothing about priority, status, ownership, or transitions.

Prefer a small reusable vocabulary. A tag that restates one item's title is
noise.

The registry lives in `tcw-config.yaml` (`work.tags`) and is **fail-closed**: an
unregistered tag is rejected, not created.

```sh
tcw work tags list                   # the registered set
tcw work tags add bug tech-debt      # register
tcw work tags rm tech-debt           # unregister (warns if items still carry it)

tcw work new "Login crash" --tag bug         # repeatable; must be registered
tcw work edit <slug> --tag cli --untag stale
tcw work list --tag bug --tag cli            # repeatable = match any
```

**A comma separates tags, everywhere one is named.** `--tags` and `--untags` are
accepted wherever `--tag` and `--untag` are, and any value of either spelling may
be a list — including the positionals of `tags add` and `tags rm`. The spellings
compose, blank segments are ignored, and a value naming no tag at all is refused.

```sh
tcw work tags add cli,docs                   # registers two tags, not "cli-docs"
tcw work new "Login crash" --tags bug,cli
tcw work edit <slug> --tags web --untags cli,docs
tcw work list --tags bug,cli                 # match any
```

A comma is never part of a tag: a tag may contain only letters, digits and
hyphens, so there is nothing for it to mean inside one. That is why this is safe
here and **not** on `--blocked-by`, whose value may be free text.

During request intake, inspect the registry and choose every materially
applicable tag. Register a new one only when it will be useful beyond the item in
front of you.

A tag left on an item after being unregistered is flagged by `tcw validate`,
which stays red until the item is retagged or the tag restored.
