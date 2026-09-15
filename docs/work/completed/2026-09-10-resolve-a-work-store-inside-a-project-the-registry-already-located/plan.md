# Plan: resolve a work store inside a project the registry already located

Seven tasks. Tasks 1 to 5 are production code, ordered so `pytest` is green at
every commit boundary. Task 6 is the capability ledger. Task 7 is the
documentation block.

The riskiest change is Task 3, the new rung. It is placed after its two
dependencies exist and are tested on their own, so a failure there is a failure
in the rung and not in the machinery underneath it.

## Task 1 — add a URL identity function, leaving `_cache_key` alone

**Modifies:** `tcw/store/checkouts.py`, `tests/test_store_provisioning.py`

Add a module-level `normalized_url(url: str) -> str` to
`tcw/store/checkouts.py`, returning a canonical string for comparing whether two
declarations name the same repository: strip surrounding whitespace and a
trailing `/`, strip a `.git` suffix, drop any `git@` user part, lowercase the
host. Its docstring states the identity contract, so nobody later mistakes it
for a display helper.

**`_cache_key` is not modified.** Not one line. It contains similar-looking text
handling, and reusing it was this plan's first draft, but the two hold opposite
policies: `_cache_key` hashes the **raw** url
(`tcw/store/checkouts.py:52-53`), so it deliberately gives
`host/owner/repo` and `host/owner/repo.git` two different cache directories,
while this item's lookup must treat them as one. Spec Design §3 carries the
reasoning.

The point of leaving it alone is that the worst outcome this change could
produce becomes unreachable. Routing that digest through a shared normalizer
would rename every provisioned directory on every machine at once, silently, and
no test of the new code would notice.

**Proves:**

- `test_two_spellings_of_one_repository_normalize_alike` covering
  `https://host/owner/repo`, `https://host/owner/repo.git`,
  `https://host/owner/repo/`, and `git@host:owner/repo.git`.
- `test_two_different_repositories_do_not_normalize_alike` for
  `host/owner/repo` against `host/other/repo`.
- `test_the_cache_key_is_unchanged` asserting literal expected key strings.
  Spec criterion 11. Kept even though the function is untouched, because it is
  the only thing that would catch a later change reopening the route. Generated
  from the current code during planning:

  ```
  github.com-proposit-app-proposit-orchestration-73cbcd814e44   https://github.com/Proposit-App/proposit-orchestration.git  @main
  github.com-proposit-app-proposit-orchestration-bc251d728153   https://github.com/Proposit-App/proposit-orchestration      @main
  github.com-proposit-app-proposit-orchestration-d5bbabd1bdc8   git@github.com:Proposit-App/proposit-orchestration.git      @main
  github.com-proposit-app-proposit-orchestration-447264907fc6   https://github.com/Proposit-App/proposit-orchestration.git  @dev
  ```

  The readable half is identical in all four and only the digest separates them,
  which is the property the test exists to hold.

**Green at this boundary:** yes. One new function nothing calls yet, plus tests.

## Task 2 — teach the registry to answer "which project is this repository?"

**Modifies:** `tcw/store/project.py`, `tests/test_project_registry.py`

Add an adapter-private method to `FsProjectRegistry`:

```
def checkout_of(self, url: str) -> Path | None
```

It loads the graph, walks each `_Config`'s `parent` and `children` entries
(`tcw/store/project.py:124-130`), and for any `ConnectedProject` whose
`repository` is not `None` and whose `repository.url` normalizes equal to `url`,
returns `Path(project.locator)` for the project that entry names — provided that
project is actually in the graph. Returns `None` when nothing matches.

Normalization is `normalized_url` from Task 1. `tcw/store/project.py` already
imports from `tcw.store.checkouts` at line 19, so no new import edge is created.

Not added to the abstract `ProjectRegistry` in `tcw/store/base.py`. The spec's
Design §2 gives the reason: the comparison reads `RepositoryDeclaration.url` and
returns a filesystem locator, both of which are documented as adapter-private.

**Proves:**

- `test_checkout_of_finds_a_project_declared_from_that_repository` — a two-node
  graph where the parent declares a `repository`, asserting the returned path is
  the parent's root.
- `test_checkout_of_matches_across_url_spellings` — the declaration written
  `git@host:owner/repo.git`, queried as `https://host/owner/repo`.
- `test_checkout_of_returns_none_for_an_unrelated_repository`.
- `test_checkout_of_follows_an_override` — with `TCW_PROJECT_<ID>` pointing the
  parent somewhere else, the returned path is the override's, not the declared
  locator's. This is the whole point of the item and belongs at the registry
  level where the override already lives.
- `test_checkout_of_ignores_a_project_the_graph_does_not_hold` — a declared but
  unreachable project yields `None` rather than a path that is not there.

**Green at this boundary:** yes. New method, nothing calls it.

## Task 3 — add the new rung to `resolve_store`

**Modifies:** `tcw/store/fs.py`, `tests/test_store_provisioning.py`

In `resolve_store` (`tcw/store/fs.py:2939`), between the rung-1 `except
StoreLocationUnusable` at line 3021 and the rung-2 `try` at line 3028, insert
the new rung:

1. Open `FsProjectRegistry` for `node_root`. **Without `require_valid()`**, and
   wrapped so any exception falls through to rung 2 — the shape already used at
   `tcw/cli.py:120-124`.
2. Ask `checkout_of(declaration.url)`. `None` falls through to rung 2.
3. Join: the returned path plus `declaration.path` when `declaration.path` is
   non-empty.
4. Call `store_cls._open_at(joined, node_root, config_path, external=True,
   must_exist=True, _walk=_walk)`. **`declaration=` is deliberately not passed**
   — that single omission is the whole of "must not publish", because
   `publishes` reads nothing else (`tcw/store/fs.py:4877`).
5. `except StoreLocationUnusable: pass`, falling through to rung 2. Every other
   exception surfaces, matching rungs 1 and 2.

Renumber the rung comments and update the `resolve_store` docstring's numbered
ladder (`tcw/store/fs.py:2941-2946`) so the numbers in the comments and the
numbers in the prose still agree.

**Proves:** spec criteria 1 through 6.

- `test_a_store_in_a_project_the_registry_located_is_used` — the flat workspace
  from issue #31, built with the file's existing `_repo` and `_local_store`
  helpers and three `TCW_PROJECT_*` variables. Asserts the resolved root is
  inside the located project. (Criterion 1.)
- `test_a_store_already_here_wins_over_the_declaration`
  (`tests/test_store_provisioning.py:378`) must pass **unmodified**. It is
  criterion 2, and it already exists. Do not touch it.
- `test_a_store_found_through_the_registry_does_not_publish` — asserts
  `publishes` is `False`, and pairs with the existing rung-2 publication tests
  in `tests/test_store_publication.py` which must stay green. (Criterion 3.)
- `test_the_registry_rung_never_touches_the_cache` — with `XDG_CACHE_HOME`
  pointed at an empty directory, asserts it is still empty, using the existing
  `_count_git` helper to assert no `git clone`. (Criterion 4.)
- `test_the_registry_rung_serves_all_three_components` — parametrized over
  `taxonomy`, `capabilities`, `work`. (Criterion 5.)
- `test_a_ref_mismatch_does_not_stop_the_registry_rung` — the located checkout
  on a branch other than the declared `ref`; asserts it resolves, with no
  warning on stderr. (Criterion 6.)
- `test_provision_reports_a_registry_resolved_store_as_available` — spec
  criterion 7, proving §1 propagates to `tcw provision` through the existing
  check at `tcw/cli.py:163-172`. Asserts `already available at` in stdout, no
  `clone` or `fetch` in the `_count_git` calls, exit 0. **No production change
  accompanies this test.**

**Green at this boundary:** yes.

## Task 4 — carry the failed configured path into the not-provisioned error

**Modifies:** `tcw/store/fs.py`, `tests/test_store_provisioning.py`

Capture rung 1's `StoreLocationUnusable` instead of discarding it at
`tcw/store/fs.py:3021`, and append a clause naming it to the `StoreNotProvisioned`
message raised at `tcw/store/fs.py:3038`.

**Only when the configured path is present on disk.** `_open_at`
(`tcw/store/fs.py:3365`) raises the same "is not a directory" message for an
absent path and for a path that is a file, so test `raw_root.exists()` directly
rather than reading the message. An absent configured path alongside a
declaration is the normal case and must stay silent.

Drawn once here so all three components inherit it.

**Proves:**

- `test_the_not_provisioned_error_names_a_broken_configured_path` — a
  `work.path` directory holding only `backlog/`; asserts the message names both
  the declared URL and the unusable path. (Criterion 9.)
- `test_the_not_provisioned_error_stays_quiet_about_an_absent_path` — a
  `work.path` naming nothing; asserts the message does not mention the
  configured path. (Criterion 10, error-surface half.)
- `test_not_provisioned_names_the_remote_and_the_command`
  (`tests/test_store_provisioning.py:435`) still passes. If its fixture uses an
  absent path it is untouched; if it uses a present-and-broken one, its expected
  message grows the clause. Read it before editing and say which.

**Green at this boundary:** yes.

## Task 5 — report the configured path as its own problem in `tcw validate`

**Modifies:** `tcw/validate.py`, `tests/test_validate.py`

`_run_check` (`tcw/validate.py:129`) turns any `ValueError` from `open` into
exactly one string, so Task 4's compound message would still count as one
problem. Add a check that runs **independently of resolution**: when
`<component>.path` is configured, names something that exists, and does not hold
the component's layout, that is its own entry in the returned list — whether or
not a declaration exists, and whether or not the store went on to open.

Independent of resolution is load-bearing. Running it only on the failure path
would miss the case where the declaration answers successfully and the broken
configured path is never reported at all.

Reuse the component's own `_open_at` to decide "does not hold the layout" rather
than re-listing folder names in `validate.py`. Three spellings of the store
layout is the drift the shared ladder exists to prevent.

**Proves:**

- `test_a_broken_path_and_an_unprovisioned_declaration_are_two_problems` —
  asserts a line naming the unusable `work.path`, a line naming the
  unprovisioned declaration, and `2 problem(s).` (Criterion 8.)
- `test_an_absent_path_with_a_declaration_is_one_problem` — asserts
  `1 problem(s).` and no line mentioning the configured path. (Criterion 10,
  validate half.)
- `test_a_broken_path_is_reported_even_when_the_declaration_answers` — the
  independence case: the declaration resolves, and the broken configured path is
  still reported.
- `test_without_a_declaration_a_broken_path_still_says_what_it_always_said`
  (`tests/test_store_provisioning.py:451`) must pass unmodified — the no-
  declaration path is untouched.

**Green at this boundary:** yes. This is the last production task.

## Task 6 — record and amend the capability ledger

**Creates:** `docs/work/backlog/2026-09-10-resolve-a-work-store-inside-a-project-the-registry-already-located/capabilities.yaml`

**Modifies:** `docs/capabilities/cli/point-tcw-at-a-project-i-already-have/description.md`,
`docs/capabilities/cli/validate-a-node/description.md`,
`docs/capabilities/cli/provision-declared-stores/description.md`

The sidecar lists the three the spec declares:

```yaml
changed:
  - cli/point-tcw-at-a-project-i-already-have
  - cli/validate-a-node
  - cli/provision-declared-stores
```

Then amend each body:

- **`cli/point-tcw-at-a-project-i-already-have`** — it currently says the
  variable is honoured by "every command that resolves the graph". Extend it: a
  component store declared in a repository the graph has already located is now
  found inside that project rather than cloned, so the variable reaches store
  resolution too.
- **`cli/validate-a-node`** — it already claims validation "tells a store's
  three failure modes apart in different words". This is the correction: state
  that a broken `<component>.path` is reported as its own problem even when a
  declaration is also present, so two problems are counted as two.
- **`cli/provision-declared-stores`** — it says a store that already resolves is
  reported as already available with no network call. Widen the set: a store
  found inside a project the registry located counts as already resolving.

No status flips; all three stay `Supported`. `meta.yaml` is not edited — in
particular `Planning doc` keeps naming the item that created each capability,
because this item amends them rather than introducing them.

**Proves:** `tcw capabilities check` passes, and `tcw validate` reports no new
problem.

## Task 7 — Documentation Sync

Evaluated against `tcw work docs`, all four entries:

| Entry | Trigger | Fires? | Task |
| --- | --- | --- | --- |
| `README.md` | **[Public-API]** | **No** | No CLI verb, flag, or configuration key is added or changed. A store that used to fail to resolve now resolves; there is nothing new for a user to type, and the README documents surface rather than resolution order. |
| `docs/release-notes/upcoming.md` | **[Public-API]** | **Yes** | User-visible behaviour changes. Add a plain-language entry: a workspace checked out in a different layout finds its store in the copy already on disk instead of cloning a second one, and a mistyped store path is now reported even when the project also declares where the store comes from. No module names. |
| `docs/changelogs/upcoming.md` | **[Any-Code-Change]** | **Yes** | Add under **Fixed**: the resolution ladder consults the project registry before the provisioned checkout, so a repository already on disk is not re-cloned and the resolved store does not publish. Add under **Fixed**: a configured `<component>.path` that exists but holds no store is reported alongside an unprovisioned declaration, and counted separately by `tcw validate`. Add under **Internal**: a repository-URL identity helper for comparing declarations, deliberately separate from the cache-directory naming. |
| `skills/<component>/SKILL.md` | **[Skill-Driven-Component]** | **No** | No component's CLI surface, model, fields, lifecycle, or guardrails change. The skills teach agents to drive `tcw work`, `tcw taxonomy`, and `tcw capabilities`; none of those verbs behave differently, and no skill states the resolution ladder. Verify by grepping `skills/` for `resolve_store`, `provision`, and `work.path` before concluding this. |

Write both files in one pass over the finished diff, as the stage instructions
direct.

## Verification

What the suite cannot check, to be run by hand and reported at `implement`:

1. **The real reported workspace.** Rebuild the flat layout from issue #31 in a
   temporary directory — three checkouts side by side, the nested-layout config
   unchanged, the three `TCW_PROJECT_*` variables exported — and confirm
   `tcw work list` reads the orchestration board and `tcw provision` reports
   everything already available. The suite's version of this uses local bare
   repositories as remotes, which is not quite the same shape.
2. **Nothing publishes.** In that workspace, run a `tcw work start` on a
   throwaway item and confirm with `git log` and `git status` in the
   orchestration checkout that the transition was committed locally and **not**
   pushed. This is the consequence that made the issue serious, and no unit test
   fully stands in for observing the real repository afterwards.
3. **The cache stays empty.** Confirm no directory was created under
   `~/.cache/tcw/stores` during either of the above, on a machine where that
   directory's prior contents were noted first.
4. **Existing cache keys.** On this machine, list `~/.cache/tcw/stores` before
   and after installing the change and confirm the directory names are
   identical. Criterion 11 pins this in a test, but the test's expectations were
   written by the same person making the change.
5. **Full suite.** `pytest` green, reported with the summary line.

## Notes

- No blockers. Nothing else in the backlog touches `resolve_store`; the one item
  that did,
  `2026-09-01-a-broken-work-path-is-hidden-when-a-repository-is-also-declared`,
  was absorbed into this item and discarded as `superseded`.
- Task ordering is dependency-driven: Task 2 needs Task 1's `normalized_url`, Task 3
  needs Task 2's lookup, Task 4 edits the same function Task 3 does and is kept
  separate so the rung and the diagnostic can fail independently, and Task 5
  needs Task 4's distinction between an absent and a broken configured path.
- Every spec criterion is covered: 1-6 by Task 3, 7 by Task 3's last test, 8 and
  10 by Task 5, 9 by Task 4, 11 by Task 1, 12 by the suite at every boundary and
  by Verification item 5.
- Task 1 was rewritten after this plan was first committed. It had proposed
  extracting the normalization out of `_cache_key` and sharing it; the two
  callers hold opposite policies about whether two spellings are one
  repository, so the shared version was dropped along with the risk it carried.
- The spec's Design §4 was corrected during this stage. `tcw provision` needs no
  production change, so no task creates one; criterion 7 is a test that proves
  the propagation rather than a task that builds it.
