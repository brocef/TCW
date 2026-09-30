# Outcome — Let a project read taxonomy and capabilities from a connected project that does not name it back

## What shipped, task by task

1. **Loading `upstream`** (`fe42bc4f`). `connected-projects.upstream` is an
   allowed key. `FsProjectRegistry` loads an upstream's config without following
   its `parent`, `children` or `upstream` edges, drops its connection problems,
   and loads it fully (re-reading it and following its edges) if it is also
   reached as family. `checkout_of` searches upstream entries. The
   `ProjectRegistry` base class gained non-abstract `declared_upstream_ids()`,
   `read_only_reason()` and `warnings()`.
2. **The write rule and the graph rules** (`64aea6d2`). `read_only_reason` walks
   parent/children edges only, from the anchor. Problems: a self-upstream; an
   upstream also reachable as family from its declarer. A duplicate id names
   the upstream declarers. The migration's middle state — a parent claim
   answered by a config declaring the node upstream — is a warning, printed by
   `tcw validate` as `warning: …`.
3. **Reading and provisioning** (`28a971ad`). `declared_connected_projects`
   reads `upstream`; CLI tests read through one hop, through a parent, from a
   reader-only checkout after `tcw provision`, and with `TCW_PROJECT_CORE`.
4. **CLI refusals** (`02ed6885`). `qualified_work_ref_read_only` and
   `resolve_qualified_work_ref_for_write`; `_resolve` in `tcw/work/cli.py` uses
   the write form except for `show`, `path` and `lifecycle`.
5. **`tcw serve` refusals** (`e8ebe682`). `_refused_read_only` answers 403
   (`code: read-only-project`) before eight changing routes resolve the item.
6. **`delegate` and `nodes`** (`60408046`). `delegate` refuses with the
   read-only reason; `tcw work nodes` prints `upstream (read-only):` with each
   upstream, its declarer and location, only when there is one.
7. **Tracker hint** (`9cf81c1b`). An incomplete `work.tracker` block in a project
   with no parent adds "this project has no parent to inherit work.tracker
   settings from; declare the whole block or remove it".
8. **The Proposit shape end to end** (`4fab3653`): baseline, the forbidden
   middle state, steps 1, 2, 5-before-4, then 4 and 5.
9. **Documentation** (`37d8c22a`, `8d2234aa`): `skills/configure/references/projects.md`,
   `docs/guide/multi-repo.md`, `taxonomy-and-capabilities.md`, `work.md`,
   `jira.md`, the taxonomy and capabilities skills, `cross-node-deltas.md`,
   README, changelog and release-note entries, the Vocabulary term
   `upstream-project`, the new capability `cli/read-from-an-upstream-project`,
   the seven changed capability descriptions, and this item's
   `capabilities.yaml`.

Also: `29a7b82d` (provisioning stops at an upstream — see below).

Every test was mutation-checked: each refusal site in serve was removed in turn
and its own case went red; the delegate check, the `nodes` ancestor walk, the
tracker `orphan` flag (both directions), the migration relaxation (both
branches), the "also family" problem, both provisioning guards, and the
no-follow rule in loading were each broken and caught.

## Test result

Bare `pytest`, as CI runs it, at `37d8c22a`: 4980 passed, 3 skipped, 2 failed
in 21 minutes. Both failures were `tests/test_documented_cli_surface.py`
catching the nonexistent `tcw serve --include-descendants` flag in
`docs/guide/multi-repo.md` and `skills/configure/references/projects.md`, fixed
in `8d2234aa`; after it, that file and `tests/test_upstream_projects.py` (67
tests) pass: 337 passed.

## What the plan or spec got wrong

- **Provisioning followed an upstream's own connections.** The spec says an
  upstream's connections are "not the reader's to load, check, provision or
  write", but Task 3 only added `upstream` to `declared_connected_projects`.
  `tcw provision` then walked into the obtained upstream and fetched what *it*
  declared — mid-migration, core's `parent` entry pointing at the private
  orchestration repository. Found while writing the docs; fixed in `29a7b82d`
  (the walk skips read-only projects and does not enqueue what an upstream
  declares), with a test for both an obtained and an already-present upstream.
- **`tcw serve` has no `--include-descendants` flag.** The CLI always serves
  descendants (`tcw/cli.py:478`); the spec and plan named a flag that does not
  exist. The refusal keys on the server's `include_descendants` setting, which
  the CLI always sets. Docs corrected in `8d2234aa`.
- **The legacy `POST …/artifacts/<name>/open` route never takes a qualified
  ref** — it refuses any slug containing `/` before resolving — so the plan's
  refusal there was unreachable and was left out; the test does not list it.
- **The migration leaves core's own old links broken.** Verified on copies of
  the real configs: after step 5, `tcw validate` in proposit-core reports 12
  `no such project` problems — `tcw://W/proposit-app/…`,
  `tcw://W/proposit-shared/…` and `tcw://W/proposit-app-repo/…` links in 11
  completed or discarded items on core's board, which resolved while core
  could see the family. That is correct behavior, but the spec's "after step 5,
  exit 0" does not hold for the real data. The requester has to rewrite or
  unlink them as part of step 4; the scratch test passes because its fixture
  has no such links.

- **The migration warning shows in every node, not only core and the root.**
  Criterion 9 says the warning appears "in core and the root" after steps 1 and
  2. Every node whose graph loads core reports it — all four in the test, all
  six on the real configs — because each of them loads the same stale parent
  claim. The test asserts the actual behavior.

## Fixed at verify

- `tcw work stage validate` resolved a qualified reference with the write form,
  so it refused an upstream item although the spec lists it as a read (spec
  line 210) and it writes nothing. It now uses the reading form;
  `test_reading_an_upstream_item_is_allowed` covers it from `a`, `b` and the
  root. Found by the verifier.
- `test_the_override_variable_redirects_an_upstream_from_the_cli` now also checks
  `tcw taxonomy list`, as criterion 3 words it, not only `show`.

## Verification beyond the suite

On copies of the six Proposit configs (and their `docs/`) in a scratch
workspace of three git repositories — the originals were only read:

- Baseline, step 1 and step 2: `tcw validate --no-recurse` exit 0 in all six
  except `proposit-server`, whose two failures are pre-existing malformed links
  (`tcw://proposit-mobile/…` with no axis letter) unrelated to this change; the
  warning appears in all six after steps 1 and 2; `tcw taxonomy show
  proposit-core/argument` succeeds in all three packages at every step;
  `tcw work nodes` in `proposit-shared` lists core under `upstream (read-only):`.
- Step 5 before step 4: core's `validate` shows the five `required` lines and the
  new "no parent to inherit" line. After step 4: the warning is gone everywhere;
  core fails only on the 12 old links above.
- `tcw serve` in the scratch root: `GET /api/work/proposit-core%2F<slug>` → 200;
  `PATCH` → 403 with "'proposit-core' is a read-only upstream project here
  (reached through 'proposit-app'); change it from that project itself"; a
  `PATCH` on a `proposit-shared` item → 200; no files changed.
- Reader-only clone of `proposit-app` with core and the orchestration repository
  as local bare repositories: `tcw provision` obtained core and did not go past
  it; `tcw taxonomy list` in `proposit-shared` lists 34 `(proposit-core)` terms.

## Notes

- For the requester: rewrite core's 12 upward links before step 5; the two
  malformed links in `proposit-server` are separate and pre-existing.
