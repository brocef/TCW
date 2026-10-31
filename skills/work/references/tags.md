# Tags

A project's classification vocabulary for grouping and filtering work. Tags are
descriptive facets — `cli`, `docs`, `bug`, `tech-debt` — and change nothing
about priority, stage, ownership, or moves.

Prefer a small reusable vocabulary. A tag that restates one item's title is
noise.

The registry lives in the project's `.tcw/tcw-config.yaml` (`work.tags`) and is
**fail-closed**: an unregistered tag is rejected, not created.

**A child inherits its parents' tags** when its parent link passes `config`,
which a link does unless its `inherit` list leaves `config` out. In such a
child, `tcw work tags list` prints the inherited tags and the child's own;
`tcw work tags add` writes `- inherit: true` as the first entry of the child's
`work.tags` before the new tag, so the inherited tags stay; and
`tcw work tags rm` of an inherited tag is refused (exit 3) with a message that
says how to stop inheriting it. When a parent that passes `config` is not on
this machine, every `tags` command exits 7, as the skill's exit-code rules
describe.

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
