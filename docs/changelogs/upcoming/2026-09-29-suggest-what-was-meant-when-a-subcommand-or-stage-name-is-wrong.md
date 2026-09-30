## Added

- A wrong subcommand now gets a suggestion after argparse's own
  "invalid choice" message, which is unchanged: a word that is a subcommand
  elsewhere in the tree is named with its full path, completed with the next
  word where that is wrong too (`tcw tracker status` → `tcw work tracker
  show`); a small synonym table (`status`/`info`/`view`/`get`/`cat` → `show`,
  `status` also → `list`, `ls` → `list`); else close spellings. `rm`, `drop`
  and `delete` are never offered by any rule, and a typed one gets no hint. New `tcw/cli_suggest.py` (`SuggestingParser`, `attach_index`),
  used as the root parser so every subparser inherits it. Only subcommands
  `--help` lists are offered. Hints apply to subcommand choices only, not to
  option values. argparse's own `suggest_on_error` is turned off. Where no
  subcommand is hidden, the first line is taken from argparse itself, so its
  wording still follows the running Python (unquoted choices on 3.12 and 3.13).
- `tcw work stage gate|prompt <word>` with an artifact name says which stage
  writes it, with a transition name names the transition's command, and
  otherwise suggests close stage ids. `discard` names
  `tcw work complete --resolution …`, since there is no `tcw work discard`, and
  `inbox` is named without a reference, which both verbs refuse for it. The exit code (1) and the existing
  message are unchanged.

## Removed

- `_HidesRemovedSpellings` in `tcw/work/cli.py`: `SuggestingParser` offers only
  help-listed subcommands, which already leaves out the removed
  `tcw work stage <id>` spellings.
