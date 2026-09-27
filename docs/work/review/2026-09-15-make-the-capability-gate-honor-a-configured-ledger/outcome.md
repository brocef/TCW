# Outcome: keep one bad capabilities.yaml from breaking the board

## What shipped

- Part 1 of the request (the gate ignored a configured ledger) was already fixed
  on main by `61a298b9`; nothing here changes it.
- **Code** — `86b4545b`: `FsWorkStore._read_capabilities_sidecar` turns every
  unreadable `capabilities.yaml` — not a regular file, not UTF-8, over 1 MB, any
  read or parse error, over 10,000 values counted through aliases — into the
  `_tcw_parse_error` value the completion gate already refuses. A missing file
  is still no sidecar. The limits and the count (`sidecar_value_problem`) live
  in `tcw/store/base.py` for any store. `_detail_snapshot` hashes sidecars from
  a tolerant read.
- **Review fold-in** — `47ab486b`: `read_sidecar` raises `UnicodeDecodeError`
  again (strict tracker mode relies on it); the web sidecar route names the file
  instead. `0cce90d5`: a depth limit of 100, which also bounds the count's
  memory; tests for the deep file, a missing file, the gate itself, and the
  board read in a child process. Then the depth message reworded.
- **Docs**: changelog and release notes.

## Tests

- `tests/test_unreadable_capabilities_sidecar.py` (15). On the code before the
  fix: not-UTF-8, folder, alias file, byte limit, gate refusal and web detail
  failed; the named pipe blocked the board read (the bug itself); the depth test
  failed with the depth check removed. The rest guard sound files.
- Full suite on `0cce90d5`: 4552 passed, 3 skipped (the reviewer's run
  agrees). The last commit changes one message string; its file passed.
- Hands-on with the worktree's `tcw`, a non-UTF-8 sidecar: `work list` lists
  both items; `show --json` shows `capabilities.yaml is not valid UTF-8`;
  `complete` refuses naming it, exit 1; `tcw serve` detail 200 and the sidecar
  route `400 capabilities.yaml is not valid UTF-8; fix or replace the file`.

## What the plan or spec got wrong

- The request's part 1 was already done when the item was picked up.
- Spec goal 4 put the UTF-8 message in `read_sidecar`; it belongs in the web
  route, because tracker callers catch `UnicodeDecodeError` from `read_sidecar`
  (a full-suite failure caught it).
- "Nesting deep enough for `RecursionError`" is not only a load-time error:
  aliases nest past every later recursive walk. Added the depth limit.
- Criterion 5 was first tested through `declared_capabilities` only; now also
  through `capability_gate`.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | Checked, no | Says nothing about unreadable sidecars. |
| `docs/guide/jira.md` | No | — |
| `docs/guide/<topic>.md` | Checked, no | `work.md` does not describe the sidecar read. |
| `docs/release-notes/upcoming.md` | Yes | One line. |
| `docs/changelogs/upcoming.md` | Yes | One Fixed entry. |
| `skills/<component>/SKILL.md` | Checked, no | `skills/capabilities/SKILL.md` covers the schema, not read failures. |
| `skills/configure/references/` | No | — |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Scope, given part 1 was already fixed?** Recorded it and fixed part 2.
- **Where to fix, and how to bound expansion?** Both advisors: at the read, with
  a value limit (10,000 is sound), and not by refusing aliases, since PyYAML
  writes `&id001` itself. Opus added: missing file stays `None`, `is_file()`
  first, a cycle-safe count, the helper in `base.py`. Codex added: the web app's
  own raw reads, a byte limit, non-regular files, merge keys (documented: their
  growth is additive and the byte limit bounds them). Took all of it.
- **`state.yaml` has the same weakness?** Opus raised it; filed as
  `2026-09-26-keep-one-unreadable-state-yaml-or-artifact-from-breaking-the-board-or-an-item-s-detail`.
- **Board visibility of the problem** (Codex: not shown on the board or in the
  web app): left out; it shows in `show --json`, at `complete`, and — through
  the sidecar check merged today — in `tcw validate` for unfinished items.
- **Code review round 1**: NOT DONE — the tracker regression, the deep-alias
  crash, quadratic memory, test gaps. All fixed. Round 2: DONE; its two wording
  notes taken. Its question — a web save guarded by the tolerant revision fails
  on a non-UTF-8 sidecar — added to the follow-up above rather than decided here.
- **Verify** (tcw:verifier): accept; all criteria met by hand for the
  non-UTF-8, folder, pipe, alias and self-referencing files, through `list`,
  `show --json`, `complete` and `tcw serve`; part 1 confirmed fixed on main.
  Its note that the depth limit covers any nesting, not only through aliases,
  was a spec-wording mismatch; the spec now says so. Decision: accept.
- **Combined check after merging main** (the `tcw validate` sidecar check
  merged earlier today): `validate` crashed on a non-UTF-8 or folder
  `capabilities.yaml` and hung on a named pipe — true on main too, in its scan of
  every `.yaml` and `.md` file. Folded in (`3b32a52f`, `bce573f8`): `_read_text`
  reports such a file as a problem line, with tests that failed before. Codex
  checked the fold-in: took its two guard gaps; rejected its point that an
  unreadable work-item `capabilities.yaml` should not skip the component checks
  — reporting it once, as every YAML problem is, is the rule the sidecar check's
  review settled on. Unreadable `.md` files the work store re-reads strictly are
  the filed `state.yaml`/artifact follow-up.
