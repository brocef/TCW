# CLI acceptance scenarios

Black-box tests that drive the **installed `tcw` binary** through a shell, in a
throwaway git repo, and assert on exit codes, stdout, stderr, and the resulting
tree.

## Why these exist alongside `tests/test_*.py`

The pytest suite is in-process: it imports `tcw.*`, calls functions, and reads
return values. That is the right shape for logic, and it is where the detailed
coverage lives. It cannot see:

| Gap | What only a shell test catches |
| --- | --- |
| **Packaging** | A module that imports fine from the source tree but is missing from the wheel, or a data file (`prompts/`, `templates/`, web assets) not declared in `pyproject.toml`. |
| **Console-script wiring** | `argparse` subparser registration, `--help` text, and the `tcw` entry point itself. An in-process test calling `main([...])` bypasses the installed script. |
| **Exit codes** | The suite mostly asserts on return values or raised exceptions. A shell caller sees only `$?`, and CI gates on it. |
| **Stream discipline** | Which of stdout/stderr a message lands on. `tcw work new` prints a slug to stdout *so it can be captured*; a warning leaking into that stream corrupts `SLUG=$(tcw work new …)`. |
| **Real process boundaries** | Inherited file descriptors, signals, environment inheritance, concurrent invocations, `git` running the repo's own hooks. |
| **Composability** | The thing an agent or a CI job actually does: pipe one command's output into the next. |

These scenarios are **not** a second copy of the unit tests. Where a behaviour is
already pinned in-process, the scenario asserts the *externally observable*
contract only — the exit code and the stream — and leaves the internals alone.

## Conventions every script follows

1. **All state in a temp dir.** `mktemp -d`, removed by an `EXIT` trap. Nothing
   is written inside this repository, and no scenario depends on this
   repository's own `docs/work/` tree.
2. **`git init` per scenario**, with `user.email`/`user.name` set locally.
   `commit.gpgsign=false` and `init.defaultBranch=main` are forced so a
   developer's global git config cannot change the result.
3. **Timeout every invocation.** A hang is a failure, not a stalled suite. No
   `tcw` call runs unbounded.
4. **`stdin` is explicit.** Every call redirects `</dev/null` unless the scenario
   is specifically about piped input. A script that inherits the terminal's stdin
   cannot test stdin behaviour.
5. **Assert the negative too.** A scenario that only checks the happy path passes
   against a `tcw` that ignores its arguments. Each asserts at least one refusal:
   a bad input, an illegal transition, or an absent file.
6. **No network, ever.** Federation and cross-node scenarios use sibling
   directories on disk.

## Layout

```
tests/cli/
  README.md          this file
  scenarios/*.md     one document per area — reviewed before any script exists
  lib.sh             shared harness (to be written with the scripts)
  NN-<area>.sh       one script per scenario document
  run-all.sh         runs every scenario, reports a summary
```

## Status

Scenarios are written and under review. **No scripts exist yet** — that is
deliberate: the scenarios are the specification, and they get reviewed by Codex
and a local model before anything is implemented against them.
