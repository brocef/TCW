# Spec — Let --untag remove a tag an item holds that is not a valid tag

## Capability changes

None.

## Reproduction

Scratch node (`tcw init work --id q4`), one item whose `state.yaml` carries
`tags: ['cli,docs', '!!!']`; `tcw work show` lists `tags: cli,docs, !!!`.

- `tcw work edit <slug> --untag 'cli,docs'` → exit 1, "tag 'cli,docs' holds
  several tags; list them separately"; tags unchanged.
- `tcw work edit <slug> --untag '!!!'` → exit 2, "argument --untag/--untags:
  invalid tag '!!!': empty after normalization"; tags unchanged.

## Problem

`--untag` is parsed by `_tags` (`tcw/work/cli.py:95`), which splits on commas
and normalizes every piece (`_tag_list`, cli.py:75) before `_edit` sees it. `_edit`
(cli.py:2471–2478) then removes only exact matches from `current.tags`. But
`read_tags` (`tcw/store/base.py:1036`) deliberately keeps an entry that cannot be
normalized as its raw text, so such a tag can never equal any normalized
argument. `update_work` then re-validates the whole remaining list with
`_validate_tags` (`tcw/store/fs.py:6584`) and refuses it.

**Sibling sweep, repo-wide** (`grep -n "untag\|remove.*tag" tcw/`): the web app
sends the full tag list, so removing the tag there already works; `tcw work tags
rm` removes a *registered* tag from the node, not an item's tag. Only `--untag`
is affected.

## Goals

1. `--untag <value>` removes a tag the item holds whose text is exactly
   `<value>`, whether or not it is a valid tag.
2. Otherwise `--untag` behaves as today: comma-separated, normalized.
3. An edit is refused for the tags it adds, never for a tag the item already
   holds: `--tag`, a partial `--untag`, and a web save resending the tags all
   keep a held tag that is invalid, or valid but no longer registered, as it
   stands; `check` still reports it (added at implement — see Notes).

## Non-goals

- Changing `--tag`'s parsing or how `read_tags` reads.
- Pointing the "holds several tags" refusal at `--untag`.

## Design

`--untag` becomes a plain string option (no `type=`). In `_edit`, each value is
matched first against `current.tags` verbatim; a value the item holds is removed
as it stands, and any other value goes through `_tag_list` (a `ValueError` there
is the existing handler's refusal, exit 1).

`update_work` passes the item's held tags (`read_tags` of its `state.yaml`)
to `_validate_tags`, which keeps any of them as it stands and validates only the
rest.

## Abstraction litmus test

`update_work`'s tag validation changes: "an edit is refused for what it
adds" is a rule any store can apply, since it only compares the new list with
the item's current one. No new operation.

## Acceptance criteria

1. With `tags: ['cli,docs', '!!!', 'cli']`, `edit --untag 'cli,docs'` exits 0
   and leaves `['!!!', 'cli']`.
2. `edit --untag '!!!'` then exits 0 and leaves `['cli']`.
3. `edit --untag 'cli,docs'` on an item holding `cli` and `docs` (and no
   `'cli,docs'` tag) removes both, as today.
4. `edit --untag '!!!'` on an item that does not hold `'!!!'` exits 1 with
   "invalid tag" in stderr and changes nothing.
5. On an item holding `'cli,docs'`, `edit --tag docs` exits 0 leaving
   `['cli,docs', 'docs']`; `update_work(tags=['!!!', 'cli'], title=…)` on an item
   holding both succeeds; `update_work(tags=['cli', 'cli,docs'])` on an item not
   holding `'cli,docs'` is still refused.
6. The full test suite passes.

## Notes

- Amended at implement (2026-09-29). With criterion 1's own example (`'cli,docs'`
  and `'!!!'` both held), removing one left the other, and `update_work`
  re-validated the whole remaining list and refused it — so matching `--untag`
  verbatim alone could not pass criterion 1. The intake's other symptoms (every
  `--tag`, every web save refused) have the same root, so the fix moved to the
  one place all three go through.

## Risks

- An invalid `--untag` value now exits 1 (a handled refusal) rather than 2 (an
  argparse usage error). Scripts checking for exactly 2 would notice; none in
  the repository do (`grep -rn "untag" tests/`).
