# Outcome: keep work.path as written when init is re-run without --path

## What shipped

- **Tasks 1-2** — `9cc707d5`. Three tests in `tests/test_config_edit_writers.py`
  (a `./store` value and a `~/store` value survive a re-run byte-for-byte; an
  explicit path is still written). The first two failed on the old code with the
  rewritten value in the diff; the third passed, as planned. `init` in
  `tcw/store/fs.py` now remembers that the work location came from the file
  (`read_from_config`) and leaves it out of the `SetScalar` edits; it is still
  used to plan, check and scaffold the store.
- **Documentation** — same commit: `### Fixed` in `docs/changelogs/upcoming.md`,
  one line in `docs/release-notes/upcoming.md`.

## Tests

- `tests/test_config_edit_writers.py`: 36 passed.
- Full suite against the worktree's source (private venv pinned to the
  worktree, bare `pytest`): **4478 passed, 3 skipped** in 19 minutes.
- Hands-on, with the worktree's `tcw` in a scratch repository: set
  `path: ./store   # kept`, ran `tcw work init`, and `diff` showed the file
  unchanged; then `path: ~/store` under a temporary `HOME`, and again unchanged.

## What the plan or spec got wrong

Nothing found. The spec's claim that only `work.path` is ever read back from the
file held: `taxonomy.path` and `capabilities.path` reach `init` only from the
command line. That is itself a gap — `tcw taxonomy init` ignores a configured
tree path — and it is filed as
`2026-09-26-make-tcw-init-honor-a-configured-taxonomy-or-capabilities-path`.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` [Public-API] | No | No surface change. |
| `docs/guide/jira.md` [Tracker-Change] | No | — |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | No | No guide describes the rewrite. |
| `docs/release-notes/upcoming.md` [Public-API] | Yes | One Fixes line. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | Yes | Fixed entry. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | No | Behaviour agents rely on is unchanged. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | No | The key's meaning is unchanged. |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Planning depth.** A one-function fix; request, spec and plan were written
  compactly rather than skipped. No open question arose, so no advisors were
  consulted at spec or plan.
- **Code review** (adversarial-code-reviewer): DONE, merge with notes; it also
  ran the full suite on a copy (4478 passed, 3 skipped). Accepted and folded in
  (`1d2cb192`): changelog tense; the release note now names `tcw init` too; a
  pre-existing traceback for `work.path: ~no-such-user/…` (and `--path`), fixed
  by catching `RuntimeError` in `run_init`, with a test that went red first.
  Nothing rejected.
- **Verify** (tcw:verifier): accept; criteria 1-3 met with tests and its own
  hands-on runs, criterion 4 on the implementer's and reviewer's full-suite runs.
  Decision: accept.
