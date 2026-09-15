# Outcome — `load_yaml` reads a falsy YAML document as an empty mapping

Four lines of production logic across four files, one of them a docstring. The
intake reported one defect on one file; three shipped, and the reading task the
plan predicted would change nothing changed two things.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `7aaf66ae` | The loader contract in `tests/test_environment_hardness.py`, red |
| 2 | `b94ab11f` | `load_yaml` returns a mapping or raises `yaml.YAMLError` |
| 3 | `edfe5733` | Classified all 30 call sites; `main()` gained a `yaml.YAMLError` handler |
| 4 | `edfe5733` | `validate` parses directly and shape-checks the names TCW owns |
| 5 | `edfe5733` | The rule stated on `WorkStore.check` in `tcw/store/base.py` |
| 6 | — | End-to-end by hand; no diff |
| — | `9e8b7e08` | Changelog, release note, validation guide |

## Acceptance criteria

All nine met.

1. `[]`, `false`, `0` and `- a` each raise `yaml.YAMLError` naming the path and
   the type. Parametrised, plus `hello` for a non-mapping scalar.
2. Absent, empty, `null` and a comment-only file each return `{}`.
3. A mapping returns unchanged, `{}` written literally included.
4. **A.** All four shapes: exit 1, the file's SHA-256 unchanged, a message
   naming the file, no traceback. Verified both in pytest and by hand at the
   command line.
5. **C.** With `- a`, `tcw work list` exits 0 and lists the item and
   `tcw work show` exits 0. No traceback from either.
6. **B.** With `[]` or `- a`, `tcw validate` exits 1 and names the file:
   `docs/work/backlog/…/state.yaml: expected a mapping, found list`.
7. `tcw validate` on this repository exits 0 with `validate OK`, `dod.yaml`
   being a top-level list and 372 owned files being mappings.
8. A `*.yaml` attachment holding a list does not fail validate.
9. Suite green, no fewer than the 2627 baseline.

## Task 3 — the classification

The plan predicted no diff here and was wrong twice. Thirty call sites, 28 in
`tcw/store/fs.py` and 2 in `tcw/validate.py` (the third became a direct parse in
task 4).

**Eleven already catch it**, which is why `yaml.YAMLError` rather than
`ValueError` was the load-bearing choice: defect C is fixed at every one of them
with no per-site edit.

| Site | Catches | Effect of the new raise |
| --- | --- | --- |
| `fs.py:2018` `check` | `yaml.YAMLError` | reported as a problem |
| `fs.py:2652` `check` | `yaml.YAMLError` | reported as a problem |
| `fs.py:2674` `check` | `yaml.YAMLError` | reported as a problem |
| `fs.py:2748` `_validation_resources` | `ValueError`, `yaml.YAMLError` | target resolves to nothing |
| `fs.py:4063` `_safe_yaml` | `yaml.YAMLError` | **degrades to `{}` — this is defect C's fix** |
| `fs.py:4099` `_read_item` | `yaml.YAMLError` | capability read degrades |
| `fs.py:4326` `_graveyard_dirt_is_only` | `Exception` | reads as dirty |
| `fs.py:4366` `_require_writable_graveyard` | `yaml.YAMLError` | refuses with its own message |
| `fs.py:4999` `_config` | `yaml.YAMLError` | refuses with its own message |
| `validate.py:93` `_claims_work` | `Exception` | answers False, as its docstring says |
| `validate.py:161` `_configured_path_problem` | `Exception` | defers to the YAML pass |

**Nineteen do not catch it, and refusing is correct at every one.** None of them
consumes a non-mapping as its data contract, and the alternative — carrying on
with `{}` — is the defect being fixed: `init` overwriting a config it could not
read is exactly shape A. What was wrong at all nineteen was the *presentation*:
an uncaught `yaml.YAMLError` reached the terminal as a traceback, because
`main()` caught only `ValueError` and `CalledProcessError`.

**Reading them was not enough, and the suite said so.** A first attempt fixed
the presentation with a single `yaml.YAMLError` handler in `main()`. The suite
refused it: `test_init_reports_a_malformed_config_rather_than_raising_through_it`
and `test_malformed_config_raises_clear_error`, written at different times in
different files, both assert that a malformed node sentinel is a **`ValueError`
naming the path**. The first spells the reason out — *"both are user-facing
config mistakes and belong in the `ValueError` channel the CLI already
renders"*. A second parallel channel for the same class of mistake was the wrong
answer, and the tests were the thing that knew it.

So the sentinel now has one reader, `load_config`, which converts. Six call
sites go through it — `write_sentinel`, `init` twice, `resolve_store`, and the
work store's `_config`, which already did this conversion by hand and now
doesn't. Two sites deliberately do not: `declared_repository` and
`declared_connected_projects` exist to answer for a graph that cannot be fully
loaded, so a config too broken to read declares nothing rather than raising.

`load_yaml` raises `NotAMapping`, a subclass of `yaml.YAMLError`, so all eleven
catching sites are still untouched and `load_config` can tell "not a mapping"
from "not YAML". The `main()` handler stays as the net for the thirteen sites
reading records rather than config; it is what keeps a corrupt `meta.yaml` from
reaching a user as a traceback.

| Site | Function | Reached by |
| --- | --- | --- |
| `fs.py:157` | `write_sentinel` | any write that backfills the sentinel |
| `fs.py:868`, `:1013` | `init` | `tcw init` — **this is criterion 4** |
| `fs.py:1469` | `FsStore.__init__` | opening any component store |
| `fs.py:1699` | `_load_node` | reading a taxonomy term |
| `fs.py:2125` | `update_term` | `tcw taxonomy edit` |
| `fs.py:2246`, `:2252`, `:2346`, `:2542` | capabilities reads | `tcw capabilities …` |
| `fs.py:2718` | `check` | `tcw capabilities check` |
| `fs.py:3061` | `resolve_store` | store resolution |
| `fs.py:3176`, `:3197` | repository declarations | `tcw provision`, `tcw nodes` |
| `fs.py:3613`, `:3706` | `start` | `tcw work start` |
| `fs.py:4441` | `_write_tombstone` | resolving an item |
| `fs.py:5724` | `_set_fields_at` | any transition |
| `fs.py:6067` | `update_work` | `tcw work edit` |

So the fix is one handler in `main()`, not nineteen catches. One guard where
every caller already routes is a smaller change than a guard per caller, and it
cannot be missed by a twentieth site added later.

**The second thing the reading found**: a `meta.yaml` that is not a mapping made
`tcw validate` traceback through the component check at `fs.py:2718`. Pass (a)
reported it, but only a `MarkedYAMLError` set the flag that skips the component
checks, and a well-formed non-mapping is not marked. So (c) ran, re-read the
same file, and raised. An owned file of the wrong shape now sets that flag for
the same reason a syntax error does — the checks re-read the file and raise on
it. The note's wording widened from "YAML syntax error above" to "YAML problem
above".

## `capabilities.yaml` did not belong in the owned set at all

The spec named five owned filenames and justified them by observing that all 372
such files in this repository are mappings. That is true and it is the wrong
test, because it measures this repository rather than the format.
`tests/test_recursion.py::test_reconcile_surfaces_capability_deltas` went red
and said why: a work item's `capabilities.yaml` has **two** valid shapes. The
Definition-of-Done gate reads a mapping of `new:`/`changed:` lists; `reconcile`
writes a top-level list of `{file, heading, from, to}` entries. The abstract
store says so in `declared_capabilities` and has since long before this item —
*"the reconcile list-form sidecar and any other shape declare nothing here"*.

Two consequences, and the second is worse than a false report:

- `validate` would have called a sound list-form sidecar a problem.
- `_read_item` read the sidecar through `load_yaml`, so the list form raised,
  was caught, and became `{"_tcw_parse_error": …}` — which
  `declared_capabilities` turns into a `SidecarError` so the gate **fails
  closed**. A valid sidecar would have blocked completing its own item.

`capabilities.yaml` is out of the set, and `_read_item` parses the sidecar
directly so both shapes survive the read. This is the clearest argument in the
item for why the spec's *"a test asserting every `*.yaml` TCW writes is in the
set would be better"* was right: the set is now three names short of the naive
answer, and every absence is a file that is legitimately not a mapping.

## Task 4 — and one gap the plan's own verification step caught

The plan asked for the owned-name set to be checked against every YAML filename
TCW writes. It was short one: the capabilities store's `CONFIG_NAME` is
`.config.yaml`, with a leading dot, where taxonomy and work use `config.yaml`.
`pathlib.rglob("*.yaml")` does match a dotfile, so the file was being scanned
and simply was not being shape-checked.

`OWNED_YAML_NAMES` holds five names — `.config.yaml` added, `capabilities.yaml`
removed for the reason above — and the spec's stated risk — *"a test
asserting every `*.yaml` TCW writes is in the set would be better and is not
attempted here"* — is closed after all. `test_every_yaml_name_tcw_writes_is_
owned_or_deliberately_not` greps the source for quoted `*.yaml` literals and
asserts the only two outside the set are `dod.yaml` (a top-level list by design)
`tcw-config.yaml` (outside the scanned trees, and refused by `load_config` the
moment anything reads it) and `capabilities.yaml` (two valid shapes).

The pass also stopped naming the file twice. Going through `load_yaml` produced
`<relative path>: <absolute path>: expected a mapping…`, because the loader's
message names the path too. `test_the_reported_path_is_named_once` pins it.

## Verification beyond the suite

The plan named three things pytest cannot answer.

- **Whether any uncaught site turns a corrupt file into a traceback.** Swept by
  hand on a scratch node against a corrupt `state.yaml`, a corrupt `meta.yaml`
  and a corrupt `tcw-config.yaml`: `validate`, `taxonomy list`,
  `capabilities list`, `work list`, `work show`, `nodes`, `work docs`,
  `work lifecycle`. No traceback from any, before or after the handler for the
  ones that already caught it. This is how the `meta.yaml` gap above was found.
- **Whether the owned-name set is complete.** Done, found `.config.yaml`, now
  guarded by a test rather than by having looked once.
- **That `validate` is still useful.** `tcw validate` on this repository exits 0.
  A check that fires on a healthy node is worse than none, and this node carries
  372 owned files plus the one deliberate list.

## Notes

- `tcw validate` failing mid-implementation was predicted by the spec and is
  what task 4 fixed. It blocked `tcw work complete` anywhere validate is a `pre`
  hook, which is this repository, so it blocked completing *any* item and not
  only this one. It passes again.
- The version is not cut here. Changelog and release notes accumulate in
  `upcoming.md` across the run.
- **Four suite failures were this session's environment, not this change.**
  `test_no_reference_to_a_deleted_document_survives` walks every `*.md` under the
  repository and excludes archives by a path prefix that a linked worktree
  nested under `.claude/worktrees/` defeats. `.claude` joins `.worktrees` in the
  skipped-directory set — one line, out of this item's scope, recorded in
  `docs/work/inbox/2026-09-11-a-linked-worktree-under-dot-claude-makes-the-parity-test-fail.md`
  with the larger point that the test would be better off asking git what is
  tracked.
