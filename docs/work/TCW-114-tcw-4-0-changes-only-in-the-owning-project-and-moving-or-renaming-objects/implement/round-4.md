# Implement round 4 — TCW-114

Answers review round 3.

## The finding

`tcw/work/cli.py:211`: the placeholder used when the item given to
`tcw work edit --blocks` cannot be resolved, `<this item's full id>`, held an
apostrophe, so a person who pasted the advised command into a shell was left
inside an open quote.

## The change

- The placeholder is now `<full id>`, matching the `--parent <full id>`
  placeholders elsewhere.
- `tests/work/test_removed_options.py`: the placeholder test expects
  `--blocked-by <full id>`, and also splits the advised command (the text
  after `instead: `) with `shlex.split`, which fails on an unclosed quote. With
  the old placeholder that split raises `No closing quotation`, so the check
  would have caught the finding.
- No other file held the old placeholder text: `implement/round-3.md` and the
  upcoming changelog and release-note entries did not mention it.

## Tests

`.venv/bin/pytest -q -p no:cacheprovider tests/work/test_removed_options.py
tests/work/test_cli_items.py`: `48 passed`.

## The suite

The dispatching session runs the full suite as CI runs it.
