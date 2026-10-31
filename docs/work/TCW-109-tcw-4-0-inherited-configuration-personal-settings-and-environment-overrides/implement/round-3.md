# Implement round 3 — TCW-109

Answers review round 2 (rejected). Built on the branch `impl-109`, from
`34d289b7`, in the worktree `.claude/worktrees/impl-109`, with the code under
test run from that worktree's own virtual environment (`.venv/bin/pytest`).
`.venv/bin/tcw` was never run with this repository as the project; the hand
checks ran in scratch projects with `HOME`, `XDG_CONFIG_HOME` and
`XDG_CACHE_HOME` set inside them and every `TCW_*` variable unset. The
lifecycle was not driven by any CLI: the dispatching session makes every
move, so no ticket was moved and nothing was posted. This round gives no
verdict.

## What was done, per review item

All in `2342ba68`.

- **(a) Finding 1: an ancestor's unknown key behind a gap.** Each mark in
  `_Fold.broken` now holds four things: the key it breaks (still cut by
  `_broken_key` to the longest key TCW knows, which is what `standing` and
  `_withhold` file it under), its layer's rank, the problem, and the
  problem's own key path. `standing` hands `_withhold` the own key path, and
  `fold.unknown` decides by it. So `lib`, after the missing `core`, passing
  `jira: {bogus: 1, priorities: {bogus: x}}` gives both warnings at `lib`'s
  file, as with no gap. For a mark found while reading a layer, the own key
  path is the problem's; for a file that cannot be read at all, which has no
  key path, it is the key it breaks, as before. For a problem found by the
  parser, it is the key path the parser gave, which `fold.broke` already
  received before the variable's name replaced it in the message.
- **(b) Finding 3: an unknown key set to `{}`.** `_Fold.merge` now records,
  beside what a layer replaces whole, every key under `work.jira` the layer
  sets to an empty mapping (`_empty_mappings`), in a list of its own,
  `written_keys`. `unknown` asks that list, not `replaced`, whether a layer
  after the gap wrote anything at or under a key TCW does not know. An empty
  mapping is not added to `replaced`, because it replaces nothing: adding it
  would make `credentials: {}` decide every credential key.
- **(c) Finding 2: the wording.** The release notes now list what in a
  variable stops commands in any project, and what only in the project it
  names (the table below), and say that `tcw validate` reports each problem
  in the project it stops. The changelog line about warnings at a parent's
  file was true for decided keys TCW knows; it now also names an unknown key,
  even inside a known one or set to an empty mapping, and a `work.tags` entry
  (decision 2), and says the problem's own key decides.
- **(d)** This file.

Checked by hand, a variable naming `b`, with `tcw work list` run in `a` and
in `b`:

| The variable's problem | Stops `a` | Stops `b` |
| --- | --- | --- |
| not valid YAML | yes | yes |
| the wrong kind (`{a: 1}` for a `prompt`) | yes | yes |
| `null` | yes | yes |
| an `inherit` entry's rules (`inherit: 5`) | yes | yes |
| `user.name` not a valid name | yes | yes |
| a credential variable name not valid | yes | yes |
| a shared key (`TCW_WORK_BACKEND__B`) | yes | yes |
| names no setting, an unknown stage or procedure | yes | yes |
| a project part that is not valid (`TCW_USER_NAME__`) | yes | yes |
| a binding's shape (`[1]`) or keys | no | yes |
| a `post` entry | no | yes |
| a `file:` binding that leaves `b`'s folder | no | yes |

`tcw validate` in `a` with `TCW_WORK_STAGES_SPEC_PROMPT__B=[1]` exits 0 and
reports nothing; in `b` it exits 1 with the error, starting with the name.

## Decisions

Each was decided by the implementing agent, with its reason. None
contradicts the spec.

1. **A variable's real key path needed no new code, and has no test of its
   own.** `fold.broke` already received the parser's key path, and now keeps
   it as the own key path. No variable can produce a mark whose own key path
   differs from the one it is filed under: a variable may set only
   `user.name`, a stage's `prompt` and `post`, a procedure and the two
   credential names (`PERSONAL_KEYS`), and of those only the credential
   names cross a link. A bad credential name is refused when the variable is
   read (Design 4.6), before the merge, as an error in every project. A test
   written for it showed exactly that, so it was dropped rather than kept as
   a test of something else.
2. **An entry a parent writes in a `work.tags` list is decided by that
   parent's place in the order** (task (e)). A list holding `inherit: true`
   replaces nothing, so behind a gap `work.tags` stays undecided, and a bad
   entry (`{inherit: 5}`, reported at `work.tags[1]`) was dropped even when
   the parent writing it came after the gap; with no gap it is a warning.
   The entry is that parent's own text whatever reaches the rest of the
   list, and the rule it breaks does not depend on the undecided value
   (Design 3.2), so `unknown` now takes the mark's rank: a key path through
   a list entry is known when the layer that wrote it comes after the last
   gap. Before the gap it stays unknown, so no warning, as Design 1.6 asks.
3. **Left for a separate change: a bad tag the parser finds in the merged
   list** (task (e)). `_parse_tags` reports `5 is not a tag` at `work.tags`,
   with no entry number. Behind a gap that key is undecided, so the problem
   is dropped, even when the project itself wrote `tags: [{inherit: true},
   5]` (checked by hand: reported with no parent, dropped with a missing
   one). Reporting it needs the entry's number, but the parser sees the
   merged list, whose numbers differ from the file's when an `inherit` entry
   pulls a parent's tags in, so the message would point at the wrong entry.
   Fixing it means the parser naming the entry by its place in its own file,
   which changes a message other items' tests read; it belongs to a change
   of its own. Whether to file it, or fold it into this item, is the
   dispatching session's to decide.
4. **The other places where a mark's key and the problem's key could
   differ** (task (e)), each checked: a file that cannot be read (no key
   path, filed under both keys: unchanged, decided by the key it breaks); a
   problem in an ancestor's local file with no key path (filed under
   `work.jira`: the same); the naming and `inherit` rules of a layer (now
   decided by their own key, with decision 2 for list entries); a parser
   problem under `work.jira` (decided by its own key, finding 1); and a
   variable's problem (decision 1). No other case was found.

## Tests and mutation checks

New in `tests/test_inherited_config.py`:

- `test_an_ancestors_unknown_jira_keys_give_a_warning`, with and without the
  missing `core`: `lib` passing `bogus: 1` and `priorities: {bogus: x}`
  gives exactly two warnings at `lib`'s file, `tcw validate` exits 0.
- `test_an_unknown_key_set_to_an_empty_mapping_is_reported_behind_a_gap`:
  `bogus: {}` is one "unknown key" problem with a missing parent and with
  none.
- `test_an_ancestors_bad_tag_entry_is_decided_by_its_place`, after the gap,
  before it, and with no gap: one warning naming `work.tags[1]` at `lib`'s
  file, none, one.

Before the fix, the first test's gap case and the second test were red, and
the third test's after-the-gap case. Each mutation was applied, run against
`tests/test_inherited_config.py`, and reverted (the file compared equal to
the kept copy afterwards):

- Hand `_withhold` the key a mark is filed under again: red, the
  unknown-key gap case and the tag entry after the gap (2).
- Record no empty mappings: red, the empty-mapping test (1).
- No list-entry rule in `unknown`: red, the tag entry after the gap (1).
- A list entry always known: red, the tag entry before the gap and round
  1's `test_a_broken_key_that_is_also_undecided_is_undecided` (2).

## Folded in after the round

Decision 3's open point, **decided by the dispatching session: folded into
this item.** A project's own `work.tags: [{inherit: true}, 5]` behind a
missing parent went unreported, while with no parent it is an error. Design
3.2 keeps every check of a value the project decides itself, and an entry the
project writes in its own list is decided by it, whatever reaches the rest of
the list; this is the same rule as review round 1's finding 1, so it belongs
to this change rather than a separate one.

- `_parse_tags` (`tcw/work/config.py`) reports an entry that is not a tag at
  the entry, `work.tags[<n>]`, not at `work.tags`.
- The merge records, for each entry of a list that takes an `inherit` entry,
  its place in the list of the file that wrote it (`_chain` and `_merge`,
  kept in `_Fold.places`). `load_config` names a parser problem at an entry
  by that place, so the message points at the entry in its own file, whose
  number differs from the merged list's once an `inherit` entry pulls a
  parent's tags in.
- `load_config` now finds the layer a parser problem is blamed on before
  deciding whether its value is known, and passes that layer's rank to
  `fold.unknown`, so a list entry the active project writes is decided by its
  place in the order, as decision 2 already did for a parent's entry.

So `app`'s own `[{inherit: true}, 5]` gives one error,
`.tcw/tcw-config.yaml: work.tags[1]: 5 is not a tag`, with the missing parent
and with none; the same list in `lib` gives one warning at `lib`'s file when
`lib` comes after the missing `core`, and none when it comes before
(unchanged). No existing test read the old message; the changelog entry says
the problem is now reported at the entry.

New in `tests/test_inherited_config.py`:
`test_a_bad_tag_the_project_writes_is_its_error_behind_a_gap` (with and
without the gap) and `test_an_ancestors_bad_tag_is_decided_by_its_place`
(after and before the gap). Mutation checks, each applied, run against the
file, and reverted (the files compared equal to kept copies afterwards):

- The parser reports at `work.tags` again: red, both own cases and the
  parent after the gap (3).
- `fold.unknown` without the layer's rank: red, the own case behind the gap
  and the parent after the gap (2).
- No translation to the place in the file: red, the same 3 (the message says
  `work.tags[0]`).
- Places recorded as the merged list's numbers: red, the same 3.

## Rebase onto v4

`impl-109` was rebased onto `v4` at `9de3de73`, which holds TCW-111 (state
files under each object's folder in place of `meta.yaml` and `item.yaml`,
nested items, object folders). The 22 commits of this item became
`v4..29bd7c2f`. The hashes named above are from before the rebase:
`2342ba68` (the fixes of this round) is now `f8d2ccc8`, `f361e21d` (this
file) `dd183f7f`, and `eacf78cb` (the folded-in fix) `dbafd60e`.

- **One conflict**, in `work_store_problems` (`tcw/work/fs_backend.py`),
  replaying `TCW-109: a project takes work.tags and work.jira from its
  parents`. TCW-111 rewrote the function to walk the store at any depth and
  check its shape; TCW-109 had made it skip the unregistered-tag check when
  the tags are withheld. Kept TCW-111's walk and shape checks whole, and put
  TCW-109's `registered = None if isinstance(config.tags, Withheld) else
  set(config.tags)` in place of its `set(config.tags)`; the line that skips
  the check when `registered` is None had merged on its own, and now warns
  at the item's state file, as TCW-111 has it.
- **One test converted to the state-file form**, with no conflict:
  `test_ac14_references_into_the_project_are_answered_from_its_folders`
  added `blocked-by` to an item by rewriting its `item.yaml`, which no
  longer exists. It now reads and writes the item's `tcw-work-item.yaml`
  through `tests/statefiles.py` (`read_state`, `write_state_data`, which
  keeps the version line first), in `29bd7c2f`. Its assertions are
  unchanged.
- No other TCW-109 test or fixture writes `item.yaml` or `meta.yaml`. No
  client source or `tcw/serve/dist` file differs from `v4`, so no client
  build or check was run.

## The suite

After the rebase, at `29bd7c2f`, from the worktree's root, with `-q -p
no:cacheprovider`:

- The item's eight files: 483 passed, 3 skipped.
- `tests/work tests/serve`: 1985 passed, 2 skipped (212 s).
- `tests --ignore=tests/work --ignore=tests/serve`: 4357 passed, 111 skipped
  (355 s).

No test failed, so `test_check_versions.py` needed no rerun.

Before the rebase, for round 3 itself, at `2342ba68`, from the worktree's
root, with `-q -p no:cacheprovider`:

- The item's eight files (`tests/test_inherited_config.py`,
  `tests/test_config_environment.py`, `tests/test_config_keys.py`,
  `tests/test_config_overrides.py`, `tests/test_config_edit.py`,
  `tests/test_parent_links.py`, `tests/test_parent_links_cli.py`,
  `tests/test_manifest_cli.py`): 479 passed, 3 skipped.
- `tests/config`: 244 passed.
- `tests/work/jira`: 729 passed, 2 skipped.
- `tests/work tests/serve`: 1915 passed, 2 skipped (210 s).
- `tests --ignore=tests/work --ignore=tests/serve`: 4215 passed, 111 skipped
  (347 s).

No test failed, so `test_check_versions.py` needed no rerun.
