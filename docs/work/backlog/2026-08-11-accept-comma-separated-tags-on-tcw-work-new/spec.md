# Spec — Accept comma-separated tags

## Capability changes

**Revise `work/tag-a-work-item` (`cap-609d75`).** Its description enumerates the
CLI surface for applying and filtering tags — `tcw work new --tag`,
`tcw work edit --tag/--untag`, `tcw work list --tag` — so a new accepted spelling
belongs in it. Status stays `Supported`; this widens an existing capability
rather than adding one.

No other ledger entry is touched. `work/manage-blocking-relations` is deliberately
left alone; see **Non-goals**.

## Problem

Two defects, one reported and one found while grounding it. Both verified at
`7e2c5961` against a scratch node with `cli` and `docs` registered.

**1. `--tags` is not an option.** The reported papercut.

```
$ tcw work new "A" --tags cli,docs
tcw: error: unrecognized arguments: --tags cli,docs
```

A hard argparse error with no hint that `--tag` is the spelling.

**2. `--tag cli,docs` silently becomes one tag, and the error invites the user to
make it permanent.** This is the worse of the two and is not in the request.

```
$ tcw work new "B" --tag cli,docs
tcw work new: unregistered tag 'cli-docs'; register it with `tcw work tags add cli-docs`
```

`normalize_tag` (`tcw/store/base.py:702-709`) replaces every run of
`[^a-z0-9]+` with a hyphen, so a comma is silently swallowed and `cli,docs`
becomes the single tag `cli-docs`. Registration is the only thing that catches
it, and the message it produces tells the user to register `cli-docs` — advice
that would write a nonsense tag into `tcw-config.yaml` and make the mistake
permanent and invisible. On a node where someone had followed that advice once,
the command would succeed silently.

**The repository already has the convention this is missing.**
`tcw work edit --blocks` takes a comma-separated string (`tcw/work/cli.py:2006`)
and splits it with `_split` (`:123-125`), whose docstring calls comma-splitting
"repo idiom". `tcw capabilities set --field` advertises `Subject accepts a,b,c`
(`tcw/capabilities/cli.py:290`). So a user who has met either of those reaches
for `--tags cli,docs` reasonably, and tags are the one place the idiom is absent.

## Goals

1. `tcw work new --tags cli,docs` applies two tags.
2. `--tag cli,docs` applies two tags rather than silently making one, closing
   defect 2. A comma in a tag value is a list separator, never a character.
3. The two spellings and the repeatable form compose in any combination.
4. The same treatment reaches every place a tag is accepted, so there is no
   command where a comma means something different.

## Non-goals

- **Doing this generically to every repeatable option.** The request asks
  whether to, and the answer is no, for a reason rather than for scope. Comma
  splitting is only safe where a comma cannot occur inside a legitimate value:
    - `--blocked-by` / `--unblocked-by` (`tcw/work/cli.py:1881`, `:2004`,
      `:2007`) take "a slug or external text". External text is free prose —
      `--blocked-by "external: waiting on Acme, Inc."` is a legal value today,
      and splitting it would silently become two blockers.
    - `tcw provision --component` (`tcw/cli.py:486`) carries argparse `choices=`,
      which validates the whole value; splitting would have to bypass it.
    - `tcw taxonomy add --vocab` (`tcw/taxonomy/cli.py:198`) takes refs. Safe in
      principle, out of scope in practice: nobody has reported wanting it and
      this item is not a CLI-wide convention change.
  - A **tag** is the one value that cannot contain a comma by construction:
    `normalize_tag` admits only `[a-z0-9-]`. That is the line, and it is stated
    so a future reader knows why the change stopped where it did.
- **Changing `normalize_tag`.** It keeps collapsing punctuation to hyphens, which
  is what makes `My Tag` and `my-tag` the same tag. The fix is splitting before
  it, not loosening it.
- **A deprecation of `--tag`.** Additive only, as the request says.
- **The web UI.** `tcw serve` edits tags against the registered set through its
  own control; there is no comma-separated text field to change.

## Design

One argparse `Action`, used at every site that takes a tag.

```python
class _TagList(argparse.Action):
    """--tag/--tags: repeatable, and each value may itself be a comma list."""
```

It splits the value with the existing `_split`, normalizes each token with
`normalize_tag`, and appends to `dest`, skipping a tag already present.

Registered at four sites, each gaining a second spelling:

| Site | `tcw/work/cli.py` | Spellings |
| --- | --- | --- |
| `work new` | `:1883` | `--tag`, `--tags` |
| `work list` | `:1892` | `--tag`, `--tags` |
| `work edit` | `:2016` | `--tag`, `--tags` |
| `work edit` | `:2017` | `--untag`, `--untags` |

argparse takes `dest` from the first long option, so `dest` stays `tag` and
`untag` and **no command handler changes**. The `type=_tag` converter those four
sites use becomes unreferenced and is deleted; the `Action` does its job and
raising `argparse.ArgumentError` from an `Action` produces the same
`argument --tag: <message>` output a `type=` converter does.

**Decisions the request asked for, and the answers:**

- **Composition.** `--tag a --tags b,c` yields `[a, b, c]`. The form is a
  spelling, not a mode; nothing distinguishes the two once parsed.
- **Duplicates.** `--tags a,a` and `--tag a --tags a` both yield `[a]`.
  First-seen order is kept. Deduplicating at the boundary means a handler never
  sees a repeated tag, which is what the store already assumes.
- **Empty segments.** `--tags a,,b` yields `[a, b]`. `_split` drops empty tokens
  and that is the established behaviour of `--blocks`; a value that is only
  separators is not a different kind of input from one with a stray comma.
- **A wholly empty value.** `--tags ""` and `--tags ",,"` are refused, with the
  same message shape `--tag ""` gives today:
  `argument --tags: invalid tag '': empty after normalization`. Today's
  behaviour for an empty tag is an error, and yielding nothing instead would
  make a typo silent.

## Acceptance criteria

Each is a command run against a scratch node with `cli` and `docs` registered.

1. `tcw work new "X" --tags cli,docs` succeeds, and `tcw work show` lists exactly
   `cli, docs`.
2. `tcw work new "X" --tag cli,docs` succeeds with the same two tags. The
   pre-change behaviour — `unregistered tag 'cli-docs'` — no longer occurs.
3. `tcw work new "X" --tag cli --tags docs` yields `cli, docs`.
4. `tcw work new "X" --tags cli,cli` yields `cli` once, as does
   `--tag cli --tags cli`.
5. `tcw work new "X" --tags "cli,,docs"` yields `cli, docs`.
6. `tcw work new "X" --tags ""` exits non-zero with
   `invalid tag '': empty after normalization`, and creates no item.
7. `tcw work new "X" --tags cli,nope` exits non-zero naming `nope` as
   unregistered, and creates no item — a bad tag anywhere in a list refuses the
   whole command, as a bad repeated `--tag` does today.
8. `tcw work edit <slug> --untags cli,docs` removes both.
9. `tcw work list --tags cli,docs` lists items carrying either, matching
   `--tag cli --tag docs`.
10. `--help` for `new`, `list` and `edit` shows both spellings of each option.
11. `tcw work new "X" --blocked-by "external: waiting on Acme, Inc."` still
    records **one** blocker whose text contains the comma. Pins the non-goal.
    Verified to hold today at `7e2c5961`, so this criterion detects a
    regression rather than describing an aspiration.
12. `pytest` passes, and `tests/test_work_tags.py` gains cases for criteria 1
    through 9.
13. `tcw capabilities show work/tag-a-work-item` describes the `--tags` spelling,
    and `tcw capabilities check` passes.

## Risks

- **Defect 2 is a behaviour change, not only an addition.** A node where someone
  followed the misleading error and registered `cli-docs` would today accept
  `--tag cli,docs` and apply that tag; afterwards it applies `cli` and `docs`.
  That is the fix working, but it is not purely additive and the changelog must
  say so. The check is whether any registered tag is the hyphen-join of two
  others. This node registers `bug capabilities cli docs remote skills taxonomy
  tech-debt web work`; none is such a join (`tech-debt` is one concept, and
  neither `tech` nor `debt` is registered), so nothing here changes meaning.
- **A tag containing a comma becomes unreachable from the CLI.** It was already
  unreachable: `normalize_tag` would have turned it into a hyphen. No registered
  tag can contain one, so there is nothing to lose.
- **Four call sites, one `Action`.** Getting `dest` wrong at any site would
  silently break a handler. Criterion 10 and the existing tag tests cover it.

## Notes

- Line citations are against `7e2c5961`.
- Defect 2 was found by running the command rather than by reading the code, and
  it is the more damaging of the two. The request records the argparse error
  because that is what its author hit; the silent normalization is what a user
  hits next, after guessing that `--tag` might take a list.
