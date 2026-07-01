# Spec — Accept L/M/H/VH shorthand aliases for --effort/--complexity

## Capability changes

Changes `work#estimate-a-work-items-effort-and-complexity` (stays **Supported**).
`--effort`/`--complexity` gain case-insensitive input shorthand; the canonical
vocabulary (`low | medium | high | very-high`), the persisted value, and every
read surface (`show`, board) are unchanged. Input-only sugar, no model change.

## Problem

`--effort`/`--complexity` use argparse `choices=WORK_LEVELS`, so only the exact
canonical strings are accepted. Typing the natural shorthand (`--effort h`) fails.

## Behavior

A single normalizer maps input → canonical:

| input (any case) | canonical |
|---|---|
| `low`, `medium`, `high`, `very-high` | pass through |
| `l` | `low` |
| `m` | `medium` |
| `h` | `high` |
| `vh` | `very-high` |
| anything else | `argparse.ArgumentTypeError` |

- Case-insensitive: input is lower-cased first, so `VH`, `Vh`, `LOW` all work.
- Applies to `new` and `edit`, both flags.
- Persisted/displayed value stays canonical (aliases never stored).

## Acceptance criteria

- `tcw work new "x" --effort h --complexity vh` stores `high` / `very-high`.
- Canonical values still work: `--effort low`.
- Case-insensitive: `--effort HIGH`, `--effort VH` accepted.
- Invalid (`--effort s`, `--effort xl`) errors with a message listing accepted values.
- `state.yaml` / `tcw work show` show canonical only.
- Store and CLI share one source of truth (normalizer lives beside `WORK_LEVELS`).

## Non-goals

- No T-shirt scale (`S/XL`), no new levels — `S` was a wrong-vocab slip, not a value.
- No change to stored format, display, or board ordering.

## Affected surfaces

- `tcw/store/base.py` — add alias map + normalizer next to `WORK_LEVELS`.
- `tcw/work/cli.py` — 4 argparse lines (`new`/`edit` × effort/complexity).

## Docs advertising

argparse help text for the flags briefly notes the aliases (leaning yes, per request).

## Risks

Minimal. Only widens accepted input; existing invocations unaffected. Main care
point: keep the error message clean (raise `ArgumentTypeError`, not a bare
`ValueError`) so `--help` and failures stay readable.
