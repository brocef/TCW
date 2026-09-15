# Outcome: resolve a work store inside a project the registry already located

Seven commits on `work/2026-09-10-resolve-a-work-store-inside-a-project-the-registry-already-located`,
branched from `main` at `2acacac`. Every plan task shipped; nothing was deferred.

## What shipped, task by task

| Task | Commit | What landed |
| --- | --- | --- |
| 1 | `7da8273` | `normalized_url` in `tcw/store/checkouts.py`, comparing two repository URLs for identity across a `.git` suffix, a trailing slash, and `git@host:owner/repo` versus `https://host/owner/repo`. `_cache_key` untouched. |
| 2 | `382f21e` | `FsProjectRegistry.checkout_of(url)` in `tcw/store/project.py`, answering which project in the graph is a checkout of that repository, by resolved location rather than declared locator. |
| 3 | `d201b04` | The new rung in `resolve_store` (`tcw/store/fs.py`), plus `_registry_checkout_root` beside it. |
| 4 | `3f65b8f` | Rung 1's failure carried into `StoreNotProvisioned`, only when the configured path exists. `work.path is not a work store` now names the directory. |
| 5 | `70b2d93` | `_configured_path_problem` in `tcw/validate.py`, run per component independently of resolution. |
| 6 | `58b6c24` | `capabilities.yaml` sidecar and the three amended capability bodies. |
| 7 | `222abe3` | Release notes, changelog, the work skill's command reference, and the multi-repo guide. |
| — | `a6f9074` | Not a plan task. The cache-directory guard moved from one test file to `conftest.py`, after verification caught my own test writing to the real cache. |

## Test result

```
2525 passed in 587.55s (0:09:47)
```

Full suite, run after the conftest fix below and confirmed to leave the real
cache directory empty. An earlier full run on the same tree, before that fix,
was also green at 2525 passed. Twenty tests were added by this change. At each task boundary the targeted set — store provisioning,
store publication, project registry, project overrides, validate, validate
target, multiproject, external work store, store bounds — ran green; the last
such run was 422 passed.

Every new test was watched red before its code existed. Two passed on their
first run and were therefore broken deliberately to confirm they guard
something:

- `test_the_cache_key_is_unchanged` — the digest was routed through
  `normalized_url`, and the expected directory name changed from
  `…-73cbcd814e44` to `…-327bb5febd8d`. That is precisely the silent rename the
  test exists to catch. Reverted and re-confirmed green.
- `test_the_not_provisioned_error_stays_quiet_about_an_absent_path` — the new
  clause was made unconditional, and both it and the pre-existing
  `test_not_provisioned_names_the_remote_and_the_command` went red. Reverted and
  re-confirmed green.

## What the plan or spec got wrong

Three things, all found while building and all fixed rather than worked around.

**1. The message the diagnostic depends on did not name the path.** Task 4's
test asserted the not-provisioned error names the unusable configured path, and
it failed with the clause present but empty of any path.
`FsWorkStore._open_at` raised `work.path is not a work store; missing: …`
without ever naming `root`, while the two branches above it — broken symlink,
not a directory — both name `raw_root`.

Neither spec nor plan noticed. The fix went into `_open_at` rather than into
`resolve_store`'s clause, because every reader of that message has the same
problem, and it is worst exactly where a relative `work.path` resolves somewhere
the user did not expect. Patching the caller would have left the plain
no-declaration case still saying "your path is not a work store" without saying
which path.

**2. The `Skill-Driven-Component` trigger fires. The plan predicted it would
not.** The plan's reasoning was that no component's CLI surface, model, fields,
lifecycle, or guardrails change. The first two thirds hold; the last does not.
`skills/tcw-work/references/commands.md` states the resolution ladder as a
guardrail — "Resolution prefers a store that is **already here** — the
declaration answers only when the local one is absent" — and an agent reading
that after this change would still believe a store not at `work.path` must be
provisioned.

The grep the plan itself named as the way to confirm the prediction is what
disproved it, which is the one part of that plan step that worked.

`docs/guide/multi-repo.md` carried the same gap and was updated too. It is
**not** a declared documentation entry, so the gate did not require it; it is
the user-facing explanation of this exact mechanism, and leaving it stale would
have been drift the gate happens not to cover. Recorded here rather than
silently expanding scope.

**3. Spec Design §4 was already corrected at the `plan` stage** and proved right
in the build: `tcw provision` needed no production change.
`test_provision_reports_a_registry_resolved_store_as_available` passes with no
edit to `tcw/cli.py`, confirming the component loop's existing call to the
resolution ladder carries the new rung.

**4. My own test wrote to the developer's real cache directory.** Found during
manual verification, not by the suite.
`test_a_broken_path_is_reported_even_when_the_declaration_answers` calls
`ensure_available()`, and `tests/test_validate.py` had no cache guard — the
`XDG_CACHE_HOME` fixture lived locally in `tests/test_store_provisioning.py` and
covered only that file. Four working copies were left in `~/.cache/tcw/stores`.

Fixed at the root rather than in my test: the fixture moved to
`tests/conftest.py` as suite-wide and autouse (`a6f9074`), which is the argument
the guards already beside it make in their own docstrings — the dependency is
invisible until a test happens to provision something, so no individual file can
be trusted to remember it. The local copy was removed rather than left as a
second spelling. The stray directories were deleted and the real cache confirmed
clean after a full run.

## A redundancy accepted rather than engineered away

When both faults are present, `tcw validate` prints two lines and the configured
path appears in both — once on its own line from Task 5's independent check, and
once inside the not-provisioned message from Task 4's clause. Each line is
independently meaningful: one says the path is broken, the other says the
declared store is absent and mentions the path as context. Suppressing one in
the other's presence would couple two checks that are deliberately independent,
which costs more than the noise is worth.

## Notes

- The prime directive was applied twice, both times landing on "adapter-private
  rather than abstract". `checkout_of` reads a `RepositoryDeclaration.url` and
  returns a `Project.locator`, both documented as unreadable above the adapter,
  and its only caller is `resolve_store` in the same adapter. Nothing was added
  to `ProjectRegistry` or to any store interface.
- Harness compatibility needed nothing. Every behaviour here is in the `tcw`
  CLI, which is identical under Claude and Codex. The only skill change is
  documentation of CLI behaviour, not a mechanism carrying a requirement.
- One test fixture of mine was broken and produced a misleading failure: the
  `tcw/validate.py` tests failed with `FileNotFoundError` on a missing config
  because the helper skipped the git initialization its neighbour does. Verified
  as a fixture fault before being treated as a finding, per this project's
  implementation rules.
- An unrelated pre-existing defect surfaced during manual verification and is
  **not** fixed here. `tcw work tags add` stages the node's `tcw-config.yaml`
  using the *store's* git repository, which fails whenever `work.path` points
  into a different repository:
  `git -C <store repo> add -- <node repo>/tcw-config.yaml` → *is outside
  repository at*. Reproduced with a bare `work.path` and **no declaration at
  all**, so no part of this change is involved. It is a fifth instance of the
  "store root and node root vary independently" hazard this project's
  implementation rules describe. Worth its own item.
- Suite duration varied widely between runs of the same tree, from about 45
  minutes to 10. Not investigated — the user stopped that line of inquiry — and
  noted only so the two figures in this item's history are not read as a
  regression caused by this change.
