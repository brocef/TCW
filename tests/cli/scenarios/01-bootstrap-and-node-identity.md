# 01 — Bootstrap and node identity

`tcw init`, the `tcw-config.yaml` sentinel, per-component init, and where a node
decides it is a node.

## Functionality covered

- `tcw init [components...] [--id ID] [--work-path PATH]`
- `tcw taxonomy init`, `tcw capabilities init`, `tcw work init` (the per-component
  mirrors)
- Node detection: the `tcw-config.yaml` sentinel, and discovery from a
  subdirectory
- `tcw --version` and `tcw --help`
- `tcw <group> path` for all three components

## What is tested

| # | Assertion |
| - | --------- |
| 1 | `tcw init --id demo` in a fresh git repo exits 0 and creates `docs/taxonomy/`, `docs/capabilities/`, `docs/work/`, and `tcw-config.yaml`. |
| 2 | `tcw-config.yaml` records `id: demo`. |
| 3 | `tcw init` with **no `--id`** on a fresh repo exits non-zero and writes nothing — the tree is byte-identical before and after (hash every path, do not trust `git status`). |
| 4 | `tcw init --id demo work` creates **only** `docs/work/`; the other two component roots are absent. |
| 5 | Re-running `tcw init --id demo` on an initialised node is idempotent: exit 0, and no tracked file's content changes. |
| 6 | `tcw work init` after `tcw init --id demo taxonomy` adds the work store without disturbing the taxonomy tree. |
| 7 | Every command run from a **nested subdirectory** (`mkdir -p a/b/c && cd a/b/c`) finds the node and behaves as it does from the root. |
| 8 | Outside any node, `tcw work list` exits non-zero and names `tcw init` in the message. |
| 9 | `tcw --version` exits 0 and prints a string matching `^tcw \d+\.\d+\.\d+$` (or the argparse default form — assert the shape, not the number). |
| 10 | `tcw init --id demo --work-path ../external-store` puts the work store at the external path; `tcw work path` prints that path, and `docs/work/` is **not** created inside the node. |
| 11 | With an external work store, `tcw work new` creates the item under the external path and the node repo stays clean of work folders. |
| 12 | `tcw work path <slug>` prints the item folder; `tcw work path` with no slug prints the store root. Both paths exist on disk. |
| 13 | `tcw taxonomy path` and `tcw capabilities path` print existing directories. |

## Refusals asserted

- init without `--id` (3)
- any command outside a node (8)
- `tcw work path` for a slug that does not exist → non-zero, nothing on stdout

## Explicitly not covered here

- Behaviour outside a git repository — that is a known open backlog item
  (`2026-07-30-fix-non-git-write-paths-...`); scenario 12 records it as a
  documented gap rather than asserting either way.
- The `.claude-plugin` / `.codex-plugin` manifests, covered by
  `tests/test_plugin_manifests.py` in-process.

## Notes for the implementer

Assertion 3 is the load-bearing one and the easiest to get wrong: capture a
manifest of `path → sha256` for every file excluding `.git/`, run the command,
and compare. A `git status` check would pass even if `tcw` wrote and then
restored a file.
