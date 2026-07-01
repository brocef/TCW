# Accept L/M/H/VH shorthand aliases for --effort/--complexity

## Requested outcome

`tcw work new`/`tcw work edit` should accept case-insensitive shorthand aliases for the
`--effort` and `--complexity` values, mapping onto the canonical `WORK_LEVELS`:

- `L` → `low`
- `M` → `medium`
- `H` → `high`
- `VH` → `very-high`

Canonical values keep working. The stored value stays canonical (aliases are input-only).

## Product changes

- Friendlier CLI input on the two flags that carry the effort/complexity scale.
  Extends `work#estimate-a-work-items-effort-and-complexity`.

## Technical changes

- `tcw/store/base.py:185` `WORK_LEVELS = ("low","medium","high","very-high")` is the scale.
- `tcw/work/cli.py` — both `--effort` and `--complexity` use `choices=WORK_LEVELS` on the
  `new` (line ~413) and `edit` (line ~447) subparsers. Replace `choices=` with a
  `type=<normalizer>` that lower-cases, maps the alias set → canonical, passes canonical
  through, and raises `argparse.ArgumentTypeError` on anything else (so `--help` and error
  messages stay clean). Normalizer + alias map likely belong next to `WORK_LEVELS` in
  `store/base.py` so store and CLI share one source of truth.

## Meta changes

- None.

## Constraints & non-goals

- Aliases are **input normalization only** — persisted `effort`/`complexity` stay canonical
  (`low`…`very-high`), so `state.yaml`, `tcw work show`, and the board are unchanged.
- Case-insensitive (`l`, `L`, `vh`, `VH` all accepted).
- Decide whether the argparse `--help`/error text should advertise the aliases (leaning yes,
  briefly) — a spec detail.

## Context / origin

Raised after I fat-fingered `--effort S` (T-shirt "Small") against the `low/medium/high/
very-high` scale. "S" is **not** a TCW concept — it was a wrong-vocabulary slip, not a
proposed value. This item adds the L/M/H/VH shorthands, which *do* map cleanly onto the scale.
