# Refined outcome — Emit new location when CLI commands move a TCW object

**Verdict: accepted.** Verified in the coordinating session on 2026-07-30. The
`tcw-verifier` dispatch for this stage died on an account session limit before
producing anything, so the assessment below was run inline rather than delegated.

## Evidence, criterion by criterion

Assessed against `spec.md`'s acceptance criteria over `git diff b9ceba3..927f5df`.

| Criterion | Verdict | Evidence |
| --- | --- | --- |
| `WorkStore` exposes abstract `locate(slug) -> str \| None`; `FsWorkStore` returns the repo-relative folder path | met | `tcw/store/base.py:951` (abstractmethod, beside `artifact_locator`); `tcw/store/fs.py:1779` |
| Four call sites name the location via `st.locate()`, no `relative_to`/`node_root` in the CLI | met | `tcw/work/cli.py:233` (`_new`), `:284` (`_inbox_accept`), `:497`/`:530` (`_start`), `:875` (`_complete`). Diff over `tcw/work/cli.py` contains no `relative_to` and no `node_root` for this feature |
| `inbox accept`/`new` stdout stays a bare slug, location on stderr; `start`/`complete` stdout stays one prose line | met | `print(item.slug)` unchanged at both sites, location printed with `file=sys.stderr` |
| `--worktree` start reports worktree *and* location | met | `cli.py:530-532`, with the pre-change string kept as the `loc is None` fallback |
| `locate` → `None` for a missing item (suffix omitted, command still succeeds); absolute-path fallback outside `node_root`, never raises | met | `fs.py:1780-1787`; every call site guards on truthiness. Covered by `test_locate_reports_repo_relative_home_and_degrades_gracefully` |
| Exit codes and gate behavior unchanged | met | No `return` path altered in the diff |

**Suite:** `python -m pytest -q` → `1098 passed in 172.33s`, re-run in the
coordinating session rather than taken from the implementer's report.

## Checks beyond the criteria

- **Abstraction litmus test (repo prime directive): passes.** `locate()` is
  defined in presentation terms — "a short, human-readable location", with the
  docstring naming an issue URL or status label as the remote-tracker
  realization, and "do not parse it" as the contract. A `JiraWorkStore` can
  honor it. The FS-specific notion (repo-relative path) lives only in the
  adapter.
- **Harness compatibility: unaffected.** Pure CLI output; identical under Claude
  and Codex, no hook or dynamic-context dependency.
- **Documentation Sync claims in `outcome.md` re-checked, and correct.** README
  did fire and carries the new text (`README.md:678`). `skills/tcw-work/SKILL.md`
  genuinely did not fire — grep over `skills/` and `commands/` finds no quotation
  of `started …`/`completed …` output.
- **Capabilities: no delta needed, confirmed rather than assumed.** No
  `capabilities.yaml` sidecar, and no capability body quotes the changed strings.
  `docs/capabilities/work/discard-a-work-item/description.md` matched a grep for
  "started" but only in prose ("was usually never started"), not as output.
- **The discard-path widening is endorsed.** `outcome.md` correction #2 records
  that `_complete`'s single print serves discards too, so a discard now also
  reports `docs/work/discarded/<slug>`. Accepted deliberately: suppressing it
  would mean adding a branch to make the output less useful, and the motivating
  problem — "where did it go?" — applies identically after a discard.

## Deferred follow-ups

None opened. The two forward-looking notes in `outcome.md` are recorded there and
need no item: `FsWorkStore._find`'s lack of caching is load-bearing for all four
call sites, and `locate`'s `ValueError` branch is unreachable through today's FS
adapter and deliberately defensive.

## Closeout choices

- **Route:** committed directly on `main`; no worktree, no PR.
- **Version:** none cut at closeout. Per the user's decision on 2026-07-30, this
  item is one of a batch of seven being driven together, and a single **minor**
  bump will be cut once the batch finishes. This item alone would have justified
  a minor — `start`/`complete` stdout is user-visible prose and changed.
- **Definition of Done:** `tests pass`, `docs synced`, `capabilities reconciled`,
  `reviewed`, and `version offered` are all satisfied. The sixth entry —
  *originating GitHub issue answered and closed* — **does not apply**: this item
  came from a direct request, not an issue (`initial-request.md` has no `## Origin`
  section naming one).
