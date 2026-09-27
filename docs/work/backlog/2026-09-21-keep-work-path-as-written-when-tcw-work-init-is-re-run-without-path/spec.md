# Spec: keep work.path as written when init is re-run without --path

## Capability changes

None. This corrects how an existing command writes a configuration value; no
capability is added, changed or retired.

## Problem

`init` in `tcw/store/fs.py` (lines 962-972) reads an existing `work.path` when no
work path was passed in, converts it with `Path(configured_path).expanduser()`, and
stores the result in `paths["work"]`. Every entry in `paths` is then written back to
the configuration file as `str(location)` (`fs.py:1102-1107`). So a value the user
never asked to change is rewritten:

- `path: ./store` → `path: store` (same meaning, needless diff);
- `path: ~/store` → `path: /Users/<someone>/store` — a machine-specific absolute
  path in a committed, shared file.

Callers: `tcw work init` (`tcw/work/cli.py:349-351`) and `tcw init`
(`tcw/cli.py:373`, via `run_init` at `tcw/cli.py:39`). Both go through `init`.

## Goals

1. When no work path is given to `init`, the configuration file's `work.path`
   line is left byte-for-byte as it was.
2. The configured value is still used to locate the store (tilde expanded), as
   today.
3. A path that *is* given on the command line is still written, as today.

## Non-goals

- How an explicitly given path is written (`--path '~/x'` still writes the
  expanded path; the shell usually expands it first anyway).
- `taxonomy.path` / `capabilities.path`: `init` never reads those from the
  configuration file — they only arrive from the command line — so they are
  never round-tripped. Sweep: `SetScalar` is only used for paths at
  `fs.py:1106`; no other writer round-trips a configured value.

## Design

In `init`, remember that the work location came from the configuration file and
leave it out of the `SetScalar` edits. The location is still used for planning,
validation and scaffolding. Abstraction test: "only write the fields the caller
asked to change" is an operation any store can honour; this is local to the
filesystem adapter's config handling.

## Acceptance criteria

1. A node whose `tcw-config.yaml` holds `work:\n  path: ./store` (store
   provisioned there), after `tcw work init` with no `--path`, still contains the
   line `  path: ./store` and the file is otherwise unchanged.
2. Same with `path: ~/…` pointing into a git repository under a temporary `HOME`:
   the file still says `~/…` afterwards, not the expanded path.
3. `tcw work init --path other` still writes `path: other`.
4. The full test suite passes.

## Risks

- A caller relying on `init` normalising the stored value. None found: the only
  reader, `FsWorkStore` config resolution (`fs.py:3893`), expands `~` itself.
