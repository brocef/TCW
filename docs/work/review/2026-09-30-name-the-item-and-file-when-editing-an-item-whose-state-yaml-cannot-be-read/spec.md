# Spec: Name the item and file when editing an item whose state.yaml cannot be read

_Compressed spec, agreed with the maintainer for a small fix._

## Capability changes

None.

## Problem

With an item's `state.yaml` replaced by `key: [unclosed`, every
`tcw work edit <slug> …` (checked at spec: `--tag`, `--title`, `--priority`,
`--blocked-by`) fails with only:

```
tcw: while parsing a flow sequence
  in "<unicode string>", line 1, column 6:
```

It names neither the item nor the file. The refusal itself is right.

Causes, in the code:

- `_set_fields_at` (`tcw/store/fs.py:8147`) and `update_work`
  (`tcw/store/fs.py:8497`, strict read at `:8517`) read `state.yaml` with a
  strict `load_yaml` and let the parser error escape to the top-level handler in
  `tcw/cli.py` `main` (line 554).
- That handler's comment says "The loader's message names the file", which is
  false: `load_yaml` (`tcw/store/fs.py:1526`) reads the file to text and parses
  the string, so PyYAML reports `"<unicode string>"`. This affects **every** YAML
  file TCW reads strictly, not only `state.yaml` — the repo-wide sibling of this
  defect.
- Moves already refuse properly, before anything changes, through
  `_require_readable_state` (`tcw/store/fs.py:5264`): `tcw work start` prints
  `<slug>: state.yaml cannot be read (while parsing a flow sequence); fix or
  replace it before changing the item`. That message names the item but not the
  file's path, and does not mention `tcw validate`.

## Goals

1. Any write to a damaged item's fields (`edit` in all its forms, and every
   other caller of `_set_fields_at` or `update_work`) refuses with the same
   message moves give, before anything is written.
2. That message names the item, the file's path from the project root, the
   parser's reason, and that `tcw validate` lists items it cannot read.
3. Every YAML parse error TCW reports names the file it came from, instead of
   `<unicode string>`.

## Non-goals

- Reads that deliberately tolerate damage (`show`, `list`, the board's
  `_safe_yaml`): they degrade to defaults by design so one bad file cannot take
  the board down. Unchanged.
- Repairing the file.

## Design

- `_require_readable_state` gains the path (as `_shown_path` prints it) and the
  `tcw validate` pointer. It is currently a static method; it becomes an
  instance method so it can use `_shown_path`. Its three callers already call it
  on `self`.
- `_set_fields_at` and `update_work` call it before their strict read.
- `load_yaml` hands PyYAML a text stream carrying the file's name, so the
  parser's own position line reads `in "<path>", line 1, column 6`. The text is
  still read with `read_text(encoding="utf-8")`, so decoding behavior is
  unchanged, and the raised type is unchanged, so the ten sites that catch
  `yaml.YAMLError` are untouched.

`tcw validate` must actually list such an item for the pointer to be honest;
verified during implementation (criterion 4).

## Acceptance criteria

With an item `<slug>` whose `state.yaml` holds `key: [unclosed`:

1. `tcw work edit <slug> --tag bug` exits 1; stderr names `<slug>`, the path
   `docs/work/backlog/<slug>/state.yaml`, and `tcw validate`; the file is
   unchanged.
2. The same for `--title x`, `--priority 2`, and `--blocked-by <other>`.
3. `tcw work start <slug>` still refuses, now with the path and the pointer.
4. `tcw validate` in that project reports `<slug>`'s `state.yaml`.
5. A YAML syntax error in any file read with `load_yaml` (for example a broken
   `tcw-config.yaml`) prints a message containing that file's path rather than
   `<unicode string>`.

## Risks

- Tests that assert the exact text of the old move refusal or of a YAML error
  need their expected wording updated.
- The path in the message is absolute when a store lives outside the project;
  `_shown_path` already falls back to that.

## Notes

- Found reviewing
  `2026-09-29-see-a-blocker-cycle-that-runs-through-an-item-whose-state-yaml-cannot-be-read`.

## Amended after spec review (2026-09-30)

An adversarial spec review ran before implementation. Accepted:

- **A named stream loses PyYAML's source excerpt.** Handed a stream, PyYAML's
  position lines drop the quoted line and the `^` caret (checked). Instead the
  loader is built from the string and given the file's name
  (`loader.name = path`), which keeps both the name and the excerpt.
- **Goal 3 was wider than the design.** About twenty direct `yaml.safe_load` /
  `yaml.load` calls bypass `load_yaml`, and duplicate-key errors carry no
  position at all. Goal 3 is narrowed to: the three reads of a *named file* that
  report parse errors to the user — `load_yaml`, the project config reader in
  `tcw/store/project.py`, and `tcw validate`'s scan. The rest is recorded as a
  follow-up, not done here.
