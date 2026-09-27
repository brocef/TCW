## Inbox manifest

- `2026-09-11-lifecycle-tag-conditions-compare-raw-strings.md`

## Inbox body

# Lifecycle `when.tags` conditions compare raw strings, so a mis-spelled binding silently never fires

## Desired outcome

A lifecycle binding whose `when.tags` names a tag either fires, or is reported as
wrong. It never silently does nothing.

## Context

Found by adversarial review of
`2026-08-11-accept-comma-separated-tags-on-tcw-work-new`, which fixed the same
silent-failure class in the tag CLI: a comma in a tag value became part of the
tag rather than a separator, and nothing said so.

`LifecycleCondition.matches` compares the raw strings from `tcw-config.yaml`
against an item's tags (`tcw/store/base.py:818`), and the parser that builds it
only strips whitespace (`:1207`). Nothing normalizes the configured value and
nothing checks it against the registered tag set. So:

- `when: { tags: [CLI] }` never fires, because every tag on an item came through
  `normalize_tag` and is lowercase.
- `when: { tags: ["cli,docs"] }` never fires, for the reason the tags item just
  fixed everywhere else.
- `when: { tags: [clii] }` never fires, and is a plain typo.

In all three cases the binding quietly does nothing and `tcw validate` reports
the node sound. A project can believe a bug-specific spec template is in force
for a year without it ever being used.

This repository has a live binding of this kind at `tcw-config.yaml:60` —
`when: { tags: [bug] }`, which works only because `bug` is already canonical.

## Constraints

- **Two decisions a fix has to make, and they are the substance of the item.**
    1. **Normalize at read time, validate at config-parse time, or both?** They
       catch different things. Normalizing makes `CLI` and `cli,docs` behave as
       written. Only validating against the registry catches `clii`, which
       normalization cannot — it is a well-formed tag that nobody registered.
    2. **Does `not_tags` get the same treatment?** It is not symmetric. A
       normalized `tags` newly *includes* items; a normalized `not_tags` newly
       *excludes* them, so a binding that fires today could stop firing.

- **Normalizing at read time cannot break a binding that works today.** Every tag
  that can appear on an item passed through `normalize_tag`, and that function is
  a fixed point on its own output, so anything matching now still matches. The
  only change is that values matching nothing today start matching. That is the
  point, but it is still a behaviour change and the spec should say so — `not_tags`
  especially.

- **Validation has a sequencing problem worth thinking about.** A `when.tags`
  naming an unregistered tag is almost certainly a mistake, but refusing to load
  the config over it would make an unregister-then-fix sequence impossible. A
  warning from `tcw validate` may be the right shape rather than a hard failure.

## A sibling with the same shape

`tcw work list --tags <typo>` exits 0 and prints nothing, which is
indistinguishable from a correct filter over an empty result. A user cannot tell
"no items carry this tag" from "that is not a tag". Same silent-failure shape as
the condition defect above, and the two may want to be one item: both are places
where naming a tag that does not exist produces silence rather than an answer.

Deliberately **not** filed: `tcw work tags rm <absent>` is also a silent no-op,
and that one is right. Removing something absent cannot write bad data, and the
capability documents it as intended.

## Supporting resources

- `tcw://work/2026-08-11-accept-comma-separated-tags-on-tcw-work-new` — the item
  whose review found this. Its spec states the rule that decides where a comma
  may be a separator, and its outcome records why scoping a change by grepping
  for one argparse mechanism missed the call sites that used another. Both apply
  directly here: the tag readers listed in that review are where to look.
- Three other readers found by the same review, all pre-existing, none able to
  corrupt the registry, and all the same class. Worth deciding whether they
  belong in this item or their own.
    - `registered_tags` returns config values verbatim (`tcw/store/fs.py:4918`),
      so a hand-edited entry can hold a tag no command can name.
    - Plan-stage declarations check `tags:` against the registry **without**
      normalizing (`:3866-3871`), so a stage declaring `Cli` is refused where
      `--tag Cli` is accepted. Two rules for the same word, in one repository.
    - The web API passes `tags` from JSON through untyped
      (`tcw/serve/__init__.py:826`, `:1080`). A JSON string rather than an array
      makes the validator iterate it character by character and report a single
      letter as unregistered — verified, `"cli"` iterates as `c`, `l`, `i`. It
      fails closed and the browser client uses checkboxes over the registered
      set, so no user path reaches it; the message is still nonsense.

## Triage (2026-09-15)

Merged at triage because both entries are defects in how `tcw-config.yaml`'s work
configuration is parsed and checked in `tcw/store/base.py` — a `when.tags` value
nobody normalizes or checks, and unknown-key messages that crash on an integer key.
The maintainer asked for items touching the same feature to be combined.

## Folded in: inbox entry `2026-09-14-config-parsers-crash-on-a-non-string-key.md`

## Config parsers crash on a non-string key instead of reporting it

Found during the code review of
`2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`. That item fixed
the same defect in `parse_tracker_config`, because inheritance would have carried
it into every child node, and in the project registry's `connected-projects` check,
because `tracker_config()` now opens the registry. Every site listed below is
unchanged.

### What happens

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

### Sites with the same shape

- `tcw/store/base.py:1462` — a binding's `when`
- `tcw/store/base.py:1517` — a binding
- `tcw/store/base.py:1674` — a stage's bindings (`pre` / `prompt`)
- `tcw/store/base.py:1890` — a documentation entry
- `tcw/store/base.py:1954` — `work.lifecycle`
- `tcw/store/base.py:2021` — `pre`/`post` keys

Line numbers are from the inheritance item's branch and will move.

### Suggested fix

Sort and join with `str`: `', '.join(sorted(map(str, unknown)))`. Add one
parametrized test that feeds each parser a mapping with an integer key, and
another with both kinds of key, and asserts a problem is returned and nothing
raises. The tracker parser's tests in `tests/test_tracker_inheritance.py`
(`test_mixed_key_types_*`) show the pattern.
