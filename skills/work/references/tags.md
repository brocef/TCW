# Tags

A project's classification vocabulary for grouping and filtering work. Tags are
descriptive facets — `cli`, `docs`, `bug`, `tech-debt` — and change nothing
about priority, stage, ownership, or moves.

Prefer a small reusable vocabulary. A tag that restates one item's title is
noise.

The registry lives in `tcw-config.yaml` (`work.tags`) and is **fail-closed**: an
unregistered tag is rejected, not created.

```sh
tcw work tags list                   # the registered set
tcw work tags add bug tech-debt      # register
tcw work tags rm tech-debt           # unregister

tcw work new "Login crash" --tag bug         # repeatable; must be registered
tcw work edit <slug> --tag cli --untag stale
tcw work list --tag bug --tag cli            # repeatable = match any
```

**One tag per use.** A tag may contain only letters, digits and hyphens, and a
value holding a comma is refused rather than split: repeat the option, or list
several tags as separate arguments to `tags add` and `tags rm`.

When deciding on an arrival or writing a request, read the registry and choose
every tag that materially applies. Register a new one only when it will be
useful beyond the item in front of you.

A tag left on an item after being unregistered is reported by `tcw validate`
until the item is retagged or the tag restored.
