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

During request intake, inspect the registry and choose every materially
applicable tag. Register a new one only when it will be useful beyond the item in
front of you.

A tag left on an item after being unregistered is flagged by `tcw validate`,
which stays red until the item is retagged or the tag restored.
