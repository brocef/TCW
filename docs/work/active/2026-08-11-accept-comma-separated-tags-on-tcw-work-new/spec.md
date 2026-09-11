# Spec — Accept comma-separated tags

## Capability changes

**Revise `work/tag-a-work-item` (`cap-609d75`).** Its description enumerates the
CLI surface for registering, applying and filtering tags, so a new accepted
spelling and a changed reading of a comma both belong in it. Status stays
`Supported`; this widens an existing capability rather than adding one.

No other ledger entry is touched.

## Problem

Two defects. One is the reported papercut; the other was found by running the
commands and is the reason this item is worth doing. Both verified at `ceedd07a`
on a scratch node with `cli` and `docs` registered.

**1. `--tags` is not an option.**

```
$ tcw work new "A" --tags cli,docs
tcw: error: unrecognized arguments: --tags cli,docs
```

A hard argparse error with no hint that `--tag` is the spelling.

**2. A comma in a tag is silently swallowed, and the node can be corrupted
permanently.** `normalize_tag` (`tcw/store/base.py:702-709`) replaces every run
of `[^a-z0-9]+` with a hyphen, so `cli,docs` becomes the single tag `cli-docs`
everywhere a tag is accepted. That has three faces, in worsening order:

```
$ tcw work new "B" --tag cli,docs
tcw work new: unregistered tag 'cli-docs'; register it with `tcw work tags add cli-docs`
```

Applying is caught, but only by the registration check, and the message tells the
user to register the nonsense tag.

```
$ tcw work tags add "cli,docs"
cli
cli-docs
docs
$ tcw validate
validate OK
$ tcw work new "C" --tag cli,docs && tcw work show 2026-09-11-c | grep tags
tags: cli-docs
```

**Registering is not caught at all.** `tcw work tags add` takes `nargs="+"`
positionals with no converter (`tcw/work/cli.py:1855`, `:1858`) and
`register_tags` normalizes each value (`tcw/store/fs.py:5268-5274`). So the
advice the first message gives works, writes `cli-docs` into `tcw-config.yaml`,
and `tcw validate` reports the result sound. From then on `--tag cli,docs`
succeeds silently and every item tagged that way carries a tag nobody meant.

Removing inherits the same reading: `tcw work tags rm "cli,docs"` unregisters
`cli-docs` when that tag exists, and reports a stale-tag warning for every item
still carrying it.

**The repository already has the convention that is missing here.**
`tcw work edit --blocks` takes a comma-separated string (`tcw/work/cli.py:2006`)
split by `_split` (`:123-125`), whose docstring calls comma-splitting "repo
idiom"; `tcw capabilities set --field` advertises `Subject accepts a,b,c`
(`tcw/capabilities/cli.py:290`). A user who has met either reaches for
`--tags cli,docs` reasonably, and tags are where the idiom is absent.

## Goals

1. `tcw work new --tags cli,docs` applies two tags.
2. **A comma is a list separator wherever a tag is accepted, never a character
   inside one.** That covers applying, filtering, registering and unregistering
   — the last two being where the damage is done.
3. The spellings and the repeatable form compose in any combination.

## Non-goals

- **Generalizing to every repeatable option.** The request asks whether to; the
  answer is no, and the line is *whether a comma can occur inside a value that is
  legitimate today*:
    - `--blocked-by` / `--unblocked-by` (`:1881`, `:2004`, `:2007`) take "a slug
      or external text". Free prose contains commas:
      `--blocked-by "external: waiting on Acme, Inc."` records **one** blocker
      today, verified, and splitting it would silently make two.
    - `tcw capabilities set --field` (`capabilities/cli.py:289`) takes `K=V`
      with its own grammar per key; some keys already split on commas and
      others must not.
    - `tcw taxonomy add --vocab` (`taxonomy/cli.py:198`) takes refs and would be
      safe. Excluded as scope, not as principle: nobody has asked, and this item
      is not a CLI-wide convention change.
    - `tcw provision --component` (`cli.py:486`) would be safe too, splitting
      before its `choices=` check. Also excluded as scope. **The earlier draft of
      this spec claimed `choices=` made it unsafe; that was wrong** — `choices=`
      is an implementation detail, not a reason a comma cannot be a separator.
  - A **tag** is the one value that cannot contain a comma by construction:
    `normalize_tag` admits only `[a-z0-9-]`.
- **Changing `normalize_tag`.** It keeps collapsing punctuation to hyphens, which
  is what makes `My Tag` and `my-tag` the same tag. The fix splits before it.
- **Cleaning up an already-poisoned node.** A node where someone followed the
  misleading advice keeps its joined tag, and `tcw validate` keeps reporting OK.
  See **Risks**.
- **The web UI.** `tcw serve` edits tags against the registered set through its
  own control; there is no comma-separated text field.

## Design

One converter, used two ways.

```python
def _tags(value: str) -> list[str]:
    """--tag/--tags and `tags add|rm`: a value is a comma-separated list."""
```

It splits with the existing `_split`, normalizes each token with
`normalize_tag`, and refuses a value that yields nothing — echoing the value as
typed, so `--tags ",,"` names the commas rather than an empty string.

**Four options** take `type=_tags, action="extend"` and a second spelling:

| Site | `tcw/work/cli.py` | Spellings |
| --- | --- | --- |
| `work new` | `:1883` | `--tag`, `--tags` |
| `work list` | `:1892` | `--tag`, `--tags` |
| `work edit` | `:2016` | `--tag`, `--tags` |
| `work edit` | `:2017` | `--untag`, `--untags` |

`extend` flattens each returned list into `dest`, and `dest` comes from the first
long option, so `dest` stays `tag` and `untag` and **no command handler changes**.
Verified: `--tag a --tags b,c` gives `[a, b, c]`; `--tags a,,b` gives `[a, b]`;
`--tags ""` exits 2 with `argument --tag/--tags: invalid tag '': …`.

**Two positionals** — `tags add` and `tags rm` (`:1855`, `:1858`) — keep
`nargs="+"` and flatten in their handlers, because argparse does not flatten a
list-returning `type=` under `nargs`. Verified: both `store` and `extend` yield
`[['cli','docs'], ['web']]`. One line each, using the same `_tags`.

The existing `_tag` converter (`:68-74`) becomes unreferenced and is deleted.

**Decisions the request asked for:**

- **Composition.** `--tag a --tags b,c` yields `[a, b, c]`. A spelling, not a
  mode.
- **Duplicates.** Not handled here, because they are already handled everywhere
  downstream: `_validate_tags` dedupes preserving first-seen order and its
  docstring says so (`store/fs.py:5276-5289`); `_edit` checks membership before
  appending (`cli.py:1539-1545`); the board filter builds a set (`:371`).
  `--tag cli --tag cli` yields one tag today. **An earlier draft added
  parser-level deduplication and justified it as something "the store already
  assumes"; the store does not assume it, it performs it**, so that code would
  have been new behaviour duplicating existing behaviour.
- **Empty segments and empty values, one rule:** *blank segments are ignored, and
  every occurrence of the option must yield at least one tag.* So `a,,b` is two
  tags and `""` and `",,"` are errors. The earlier draft defended these two
  halves with two different precedents, picking whichever supported each answer.

## Acceptance criteria

Run against a scratch node with `cli`, `docs` and `web` registered, unless a
criterion says otherwise.

1. `tcw work new "X" --tags cli,docs` succeeds; `tcw work show` lists `cli, docs`.
2. `tcw work new "X" --tag cli,docs` succeeds with the same two tags. The
   pre-change `unregistered tag 'cli-docs'` no longer occurs.
3. `--tag cli --tags docs` and `--tags docs --tag cli` both yield `cli, docs`.
4. `--tags cli,cli` and `--tag cli --tags cli` each yield `cli` once.
5. `--tags "cli, docs"` (space after the comma) yields `cli, docs`.
6. `--tags ""` and `--tags ",,"` each exit non-zero, create no item, and echo the
   value as typed — the second naming `',,'`, not `''`.
7. `--tags cli,nope` exits non-zero naming `nope`, and creates no item.
8. `--tags "cli,!!!"` exits non-zero. A non-blank invalid token is refused, not
   discarded.
9. `tcw work edit <slug> --tags web` adds without disturbing existing tags;
   `--untags cli,docs` removes both; `--tag cli --untag cli` preserves today's
   add-wins outcome.
10. `tcw work edit <slug> --untags cli,nope` removes `cli`, ignores `nope`, and
    exits zero. **Corrected during implementation**: this criterion first said
    the command should refuse. It described a behaviour that has never existed —
    `--untag nope` succeeds as a no-op today, verified — and removal checks no
    registry at any call site. The asymmetry with `--tag`, which refuses the
    whole command on an unregistered token, is deliberate rather than an
    oversight: applying an unregistered tag writes data nobody can act on,
    removing one cannot. A comma list inherits that rule; tightening it would be
    a behaviour change nobody asked for.
11. On a node with four items — one `cli`, one `docs`, one both, one neither —
    `tcw work list --tags cli,docs` lists the first three and not the fourth,
    identically to `--tag cli --tag docs`. Four fixtures, so an AND filter cannot
    pass.
12. **`tcw work tags add "cli,docs"` registers `cli` and `docs` and never
    `cli-docs`**, on a node where neither is registered yet.
13. **`tcw work tags rm "cli,docs"` unregisters both.** On a node still carrying
    `cli-docs` from before, it unregisters nothing and says so rather than
    removing `cli-docs`.
14. `tcw work new "X" --blocked-by "external: waiting on Acme, Inc."` still
    records **one** blocker containing the comma. Verified to hold today, so this
    detects a regression rather than describing an aspiration.
15. `--help` for `new`, `list`, `edit`, `tags add` and `tags rm` shows both
    spellings and says a value may be a comma-separated list.
16. `pytest` passes, and `tests/test_work_tags.py` gains cases for 1 through 13.
17. `tcw capabilities show work/tag-a-work-item` describes the comma form, and
    `tcw capabilities check` passes.
18. Every documentation entry `tcw work docs` reports has been evaluated, and the
    three files naming `--tag` that would otherwise drift —
    `skills/tcw-work/references/tags.md`,
    `skills/tcw-work/references/commands.md`, `docs/guide/work.md` — either
    describe the comma form or are recorded as not needing to.

## Risks

- **This is not additive, and three behaviours change.** `--tag cli,docs` goes
  from failing to succeeding; `tags add "cli,docs"` goes from registering
  `cli-docs` to registering two tags; `tags rm "cli,docs"` goes from removing
  `cli-docs` to removing two. The changelog must say so rather than calling the
  item sugar. The earlier draft said "additive only" — wrong.
- **An already-poisoned node is not repaired and stays silent.** A node where
  `cli-docs` is registered keeps it, keeps every item tagged with it, and
  `tcw validate` keeps reporting OK — confirmed. Cleanup is manual. A `validate`
  warning for a registered tag that is the hyphen-join of two other registered
  tags would close this, and is a separate item rather than this one.
  This repository registers `bug capabilities cli docs remote skills taxonomy
  tech-debt web work`; none is such a join, so nothing here changes meaning.
- **An abbreviation that works today stops working.** Python's parser accepts
  unambiguous prefixes, so `tcw work new "X" --ta cli` creates an item now and
  will fail with `ambiguous option: --ta could match --tag, --tags`. Verified.
  `--tag` itself still matches exactly, and `--t` is already ambiguous with
  `--title`, so the loss is exactly `--ta` and `--unta`. Accepted as a cost of
  the spelling the request asks for, and stated so it is not a surprise.
- **`--tags "$VAR"` with an empty variable now fails.** That is the ordinary way
  a script says "no tags", and it must become a branch. Accepted: the
  alternative is that a typo silently applies nothing, which is how defect 2
  stayed hidden.
- **A neighbouring backlog item will inherit this decision unread.**
  `2026-09-10-let-a-node-declare-its-own-work-item-state-fields` says a declared
  field should behave the way a tag does, registered in config and filterable
  from `list`. It sits above this one in priority. Whoever picks it up should
  read this spec's non-goals rather than re-deriving the comma rule.

## Notes

- Line citations are against `ceedd07a`.
- **`--blocks` accepting commas while `--blocked-by` does not is not an
  inconsistency**, and an earlier draft wrongly called it one. `--blocks` accepts
  only slugs of existing items — the handler refuses an unknown ref with
  `st.get(ref) is None` (`cli.py:1547-1551`) — and a slug cannot contain a comma.
  `--blocked-by` accepts free prose, which can. The asymmetry follows from the
  value grammar, exactly as the tag rule does.
- **Priority.** Filed at 20 as "additive sugar". Once defect 2 is in view the
  alias carries no meaning `--tag` does not, and the value of the item is
  entirely the silent corruption of a project's registered tag set. Raised to 35.
