# Key work.documentation uniqueness on (path, trigger) so one file can carry two triggers

A project moving its `## Documentation Sync` section into `work.documentation`
— the migration the 1.0.0 guide recommends — cannot bring across a shape the
Markdown form supported: **two entries naming the same file under different
triggers.**

`proposit-core` has carried this pair for months:

```markdown
- `README.md` [Public-CLI-API] — Concepts, usage examples, and CLI sections
- `README.md` "Invalid Constructions" section [Validation-Rules] — Update when adding, removing, or changing validation rules, thrown errors, error codes, operator constraints, cascade behaviors, or grammar config options
```

These are genuinely different triggers on one file. A CLI-surface change fires
the first; a validation-rule change that touches no CLI surface fires only the
second. Expressed as config, the second entry is rejected:

```
work check: tcw-config.yaml: work.documentation entry 1: duplicate 'path' 'README.md', already declared by entry 0
```

So the recommended form is **strictly less expressive than the fallback it is
meant to replace**, for any file large enough that different sections answer to
different triggers — a README, most of the time.

## What is being asked for

Let one file carry more than one documentation entry when the entries have
different triggers. The reporter suggests keying uniqueness on the
`(path, trigger)` pair rather than on `path` alone, and notes it reads
naturally in `tcw work docs` output, which already prints the trigger beside
the path. They raise an optional `section:` key as the alternative, and judge
the pair the smaller change.

Two entries that share **both** a path and a trigger are still a duplicate and
should still be rejected.

## Why it matters

It lets a project adopt the config form without losing trigger granularity, and
removes a standing reason to stay on the Markdown fallback.

## Constraints

- Existing configs must keep validating unchanged; this only widens what is
  accepted.

## Out of scope

- **The `section:` key.** Named as an alternative, not requested alongside.
- **Validating that a `path` resolves on disk.** The reporter's workaround —
  `README.md#invalid-constructions` — names a path that does not exist, and
  they flag that anything later resolving entries against the filesystem would
  be misled. Real, and deliberately left for its own item: this request is the
  relaxation only.

## Notes

- Confirmed with the requester (2026-08-21): relaxation only, and issue #21 is
  the whole of the reference material — no migration guide excerpt, no
  downstream config to read.
- The reporter is unblocked today via the anchored-path workaround, so this is
  an expressiveness and correctness fix, not an outage.

## References

- [GitHub issue #21](https://github.com/brocef/TCW/issues/21) — the request in
  full, with the error text, the `proposit-core` pair that motivated it, and
  the workaround now in use.
