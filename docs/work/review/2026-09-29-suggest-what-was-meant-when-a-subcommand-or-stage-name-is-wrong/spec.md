# Spec — Suggest what was meant when a subcommand or stage name is wrong

## Capability changes

- **added:** `cli/get-a-suggestion-for-a-mistyped-command`: a wrong
  subcommand, or a wrong stage name, is answered with the command that was
  probably meant.

## Problem

`tcw` reports a wrong word by listing every valid choice at that level and
nothing more:

- `tcw tracker status` fails at the top level, although `tracker` exists one
  level down (`tcw work tracker`), where `show` is what was meant.
- `tcw work status <slug>` fails listing every `work` verb; `show` was meant.
- `tcw work stage gate refined-outcome <slug>` says "unknown stage", although
  `refined-outcome.md` is what the `verify` stage writes.

In the first case an agent concluded the CLI could not show a ticket's sync
state and went to Jira directly.

## Goals

1. **A word that is a subcommand elsewhere.** When the invalid word is a
   subcommand at another place in the command tree, the error adds a line
   naming the full command, for example "did you mean `tcw work tracker`?". If
   the next word is not valid there, the synonym and close-spelling rules below
   are applied to it. So `tcw tracker status` suggests `tcw work tracker show`.
2. **A likely synonym.** A small fixed table, offered only when its target is a
   valid choice at that level:
   - `status`, `info`, `view`, `get`, `cat` → `show`;
   - `ls` → `list`.
   - At the `work` level, `status` suggests both `show` (one item) and `list`
     (the board, whose `--status` filters by it).
   - Words for removal are not mapped. `drop`, `delete` and `rm` are
     destructive, and pointing at one is worse than no hint.
3. **A close spelling.** Otherwise, close matches among the choices valid at
   that level (`difflib`), for example `strat` → `start`.
4. **Stage names.** `tcw work stage gate|prompt <word>`:
   - an artifact name, with or without `.md` (`initial-request`, `outcome`,
     `refined-outcome`, `post-mortem`), names the stage that writes it:
     "`refined-outcome.md` is written by the `verify` stage";
   - `post-mortem` also resolves to the stage `postmortem` in the message;
   - a transition name (`start`, `submit`, `complete`, `discard`) says it is a
     transition, not a stage, and names its command;
   - `rework` says both: `rework.md` is written by `verify`, and
     `tcw work rework` is the transition;
   - otherwise, close matches among stage ids.
   The command is not run under the suggested name.
5. **Nothing else changes.** The existing error text stays word for word, with
   the hint added as a line after it. The exit codes stay the same: 2 for a
   subcommand, and 1 for an unknown stage, as today. `--help` output is
   unchanged.

## Non-goals

- **No aliases.** `status` does not become a working command. An alias adds to
  the documented surface (`tests/test_documented_cli_surface.py` reads it from
  `--help`), can collide with a later verb, and the project already chose not
  to alias the removed stage spellings.
- **No hints for option values** (`--status`, `--resolution`). Their errors
  already list the choices, and nobody has reported a problem with them.
- **`tcw taxonomy <word>` and `tcw capabilities <word>`.** An unknown verb
  there is already read as `show <word>` (`_normalize` in `tcw/cli.py`), so
  they never produce this error. That is unchanged.

## Design

- A parser class, `_SuggestingParser`, used as the root parser in
  `build_parser`. `add_subparsers` gives every subparser its parent's class,
  so taxonomy, capabilities and every nested group get it.
  `_HidesRemovedSpellings` is made a subclass of it.
- Its `_check_value` acts only for a subcommand choice
  (`argparse._SubParsersAction`). On an invalid word it raises argparse's
  usual `ArgumentError`, with the same message, plus a hint line.
- A `_visible_choices(action)` hook gives the choices that may be offered. The
  base gives all of them; `_HidesRemovedSpellings` leaves out the seven removed
  stage spellings. Its own message ("choose from …" without them) is kept, and
  it now also gets the hint.
- An index from each subcommand name to its full paths
  (`tcw work tracker`, …), built by walking the finished tree once in
  `build_parser`, leaving out the removed stage spellings. It is attached to
  every parser, since a nested parser reports its own error and cannot see the
  root.
- The next word after the invalid one comes from the argument list the root
  was parsing, kept on the root by its `parse_args`/`parse_known_args`.
- `suggest_on_error` is set to `False` explicitly. Python 3.14 has argparse's
  own suggestion, and it may later be turned on by default, which would print
  two hints.
- Stage names: `_stage_step` in `tcw/work/cli.py` builds its message from
  `LIFECYCLE_STEPS` (`produces`, `kind`), adding the hint after today's text.

Litmus: CLI presentation only, no store operation.

## Acceptance criteria

1. `tcw tracker status`: exit 2, stderr contains today's "invalid choice" text
   and a line naming `tcw work tracker show`.
2. `tcw work status x`: exit 2, stderr names `tcw work show` and
   `tcw work list`.
3. `tcw work strat x`: suggests `tcw work start`.
4. `tcw work stage gate refined-outcome x`: exit 1; stderr keeps
   "unknown stage 'refined-outcome'" and adds that `refined-outcome.md` is
   written by the `verify` stage. The same for `outcome.md`, `initial-request`
   and `post-mortem`.
5. `tcw work stage gate start x` says `start` is a transition and names
   `tcw work start`. `rework` names both its artifact and its transition.
6. `tcw work stage gat x` suggests `gate` and offers no removed stage spelling.
   `tcw spec` suggests nothing under `tcw work stage spec`.
7. `tcw work list --status bogus` has no hint added.
8. A test walks the whole parser tree and asserts every parser is a
   `_SuggestingParser`.
9. Existing tests pass unchanged; the full suite passes as CI runs it.

## Risks

- **A wrong suggestion.** Every hint is phrased "did you mean …?", and only
  words with one clear target are in the table.

## Notes

- Advisors: Opus, and Sonnet in place of Codex (at its usage limit until
  2026-10-03). Both chose suggestion only, no alias.
  - Sonnet: route through `_check_value` rather than `error()`, keep the
    table small, drop `rm`, and put the elsewhere-in-the-tree rule first, so
    that case 1 reaches `show`.
  - Opus: act only for subcommand choices, leave out the removed spellings,
    add the visible-choices hook, turn `suggest_on_error` off, give
    transitions their own message, accept `post-mortem`, and keep exit 1 for
    stages.
