# Config parsers crash on a non-string key instead of reporting it

Found during the code review of
`2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`. That item fixed
the same defect in `parse_tracker_config`, because inheritance would have carried
it into every child node, and in the project registry's `connected-projects` check,
because `tracker_config()` now opens the registry. Every site listed below is
unchanged.

## What happens

YAML reads an unquoted number key as an integer, so `5: bad` under a mapping
TCW validates gives a key of type `int`. Several parsers build their "unknown
key" message with `', '.join(sorted(unknown))`. With a mix of string and integer
keys, `sorted` raises `TypeError`. With a single integer key, `join` raises
`TypeError`. Either way the parser raises instead of returning a problem, and
the command crashes with a traceback rather than naming the bad key.

It was first reproduced on the project registry, where a `tcw-config.yaml` holding

```yaml
id: n
connected-projects:
  5: bad
  z: 1
```

made `FsProjectRegistry.open(node)` raise
`TypeError: '<' not supported between instances of 'int' and 'str'`. That site
(`tcw/store/project.py:448`) **is fixed** on the inheritance item's branch, because
that item made `tracker_config()` open the registry and its spec promises it never
raises. The six sites below have the same shape and are not fixed.

## Sites with the same shape

- `tcw/store/base.py:1462` — a binding's `when`
- `tcw/store/base.py:1517` — a binding
- `tcw/store/base.py:1674` — a stage's bindings (`pre` / `prompt`)
- `tcw/store/base.py:1890` — a documentation entry
- `tcw/store/base.py:1954` — `work.lifecycle`
- `tcw/store/base.py:2021` — `pre`/`post` keys

Line numbers are from the inheritance item's branch and will move.

## Suggested fix

Sort and join with `str`: `', '.join(sorted(map(str, unknown)))`. Add one
parametrized test that feeds each parser a mapping with an integer key, and
another with both kinds of key, and asserts a problem is returned and nothing
raises. The tracker parser's tests in `tests/test_tracker_inheritance.py`
(`test_mixed_key_types_*`) show the pattern.
