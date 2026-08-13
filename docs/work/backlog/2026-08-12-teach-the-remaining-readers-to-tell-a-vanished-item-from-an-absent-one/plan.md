# Teach Readers to Distinguish Vanished and Absent Work Items Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize filesystem reads across atomic claims so blockers and web details never mistake an in-flight item for a missing one.

**Architecture:** Keep claim awareness inside `FsWorkStore`: split immediate lookup from stable public `get`, poll only with exact private-claim evidence, and make composite detail snapshots retry from scratch. Storage-neutral blocker logic remains unchanged and benefits from the adapter guarantee.

**Tech Stack:** Python 3.11+, pathlib/os atomic rename, threading synchronization, pytest, abstract `WorkStore` plus filesystem adapter.

---

### Task 1: Characterize blocker reads during private claims

**Files:**
- Modify: `tests/test_external_work_store.py`
- Modify: `tests/test_work.py`

- [ ] **Step 1: Add a deterministic in-flight blocker fixture**

Move blocker A from backlog to an exact `.claiming/<slug>-<32 hex>` path, start a thread that publishes it to active after a synchronization event, and keep target B in backlog with `blocked_by: [{slug: A}]`.

- [ ] **Step 2: Add start and create assertions**

Assert `start(B)` waits for publication then raises `blocked by: A`. In a separate case, call `create_work(..., blockers=[A])` while A is private and assert the stored entry is `{"slug": A}`.

- [ ] **Step 3: Add immediate genuine-miss timing coverage**

Measure `get("missing")` with no matching claim and assert it returns `None` well below the 500 ms claim window. Reuse the prefix-collision fixture to prove a longer slug's claim is ignored.

- [ ] **Step 4: Run red tests and commit**

Run: `pytest tests/test_external_work_store.py tests/test_work.py -k 'blocker or stable_get' -v`

Expected: blocker cases fail because base methods observe `None`; genuine miss remains fast.

```bash
git add tests/test_external_work_store.py tests/test_work.py
git commit -m "test: define stable reads during work claims"
```

### Task 2: Split immediate and stable filesystem reads

**Files:**
- Modify: `tcw/store/fs.py:1904-2140` and the existing `get` implementation
- Modify: `tcw/store/base.py` only if a domain error class belongs beside `AlreadyClaimed`
- Test: `tests/test_external_work_store.py`

- [ ] **Step 1: Introduce the immediate probe**

Move the current one-shot `FsWorkStore.get` body into `_get_now(slug)`. Keep decoding and status construction byte-for-byte equivalent so normal read semantics do not drift.

- [ ] **Step 2: Implement conditional stabilization**

Make `get` return `_get_now` hits immediately. On a miss with no exact `_claiming_dirs`, return `None`. With claim evidence, poll `_get_now` 50 times at 10 ms; return the published item or raise a domain `InterruptedClaim`/clear `ValueError` consistently with takeover messaging.

- [ ] **Step 3: Remove recursive waiting from `_lost_the_claim`**

Poll `_get_now` there. Continue raising `AlreadyClaimed` when active publishes and the interrupted-claim error after one bounded window.

- [ ] **Step 4: Run claim and blocker suites**

Run: `pytest tests/test_external_work_store.py tests/test_work.py -q`

Expected: PASS, including one winner, loser metadata, interrupted takeover, prefix matching, blocker start, and blocker creation.

- [ ] **Step 5: Commit the stable-read adapter**

```bash
git add tcw/store/base.py tcw/store/fs.py tests/test_external_work_store.py tests/test_work.py
git commit -m "fix: stabilize filesystem reads across claims"
```

### Task 3: Make detail snapshots retry atomically

**Files:**
- Modify: `tests/test_store_editor.py:87-145`
- Modify: `tests/test_serve.py` or `tests/test_serve_write.py`
- Modify: `tcw/store/fs.py:2897-2940`

- [ ] **Step 1: Replace the obsolete second-find test**

Keep genuine unknown-slug coverage, then add a controlled race that moves the item after `_find` but before `state.yaml` read and publishes it active. Assert `get_detail` returns an active `WorkDetail` with revisions instead of `None` or `FileNotFoundError`.

- [ ] **Step 2: Add an HTTP regression**

Force the same race through the work-detail endpoint and assert a normal detail response (or documented conflict/not-found for an abandoned claim), never a server traceback/connection drop.

- [ ] **Step 3: Run detail tests red**

Run: `pytest tests/test_store_editor.py tests/test_serve.py -k 'detail and (claim or move)' -v`

Expected: FAIL at the unguarded state read.

- [ ] **Step 4: Implement bounded whole-snapshot retries**

For each attempt, discard all prior text/revisions, call stable `get`, locate the corresponding directory, and read state/body/artifacts/sidecars. Catch only disappearance races for paths inside that item and retry; let permissions, malformed content, and unrelated I/O errors surface. Ensure returned item and revisions come from the successful attempt.

- [ ] **Step 5: Run editor and serve suites, then commit**

Run: `pytest tests/test_store_editor.py tests/test_serve.py tests/test_serve_write.py -q`

Expected: PASS.

```bash
git add tcw/store/fs.py tests/test_store_editor.py tests/test_serve.py tests/test_serve_write.py
git commit -m "fix: retry work detail snapshots after moves"
```

### Task 4: Audit sibling find-then-read races

**Files:**
- Modify: only additional `tcw/store/fs.py` callers proven to have the same race
- Modify: corresponding focused test files

- [ ] **Step 1: Perform the required repo-wide sibling sweep**

Run: `rg -n '_find\(|_require_dir\(|state.yaml.*read|load_yaml\(' tcw/store tcw/serve tcw/work`

Classify each `_find` then path-access sequence as transition/write logic (already conflict-aware), stable read, or vulnerable composite read.

- [ ] **Step 2: Add a failing race test for each vulnerable reader**

Use deterministic monkeypatch/events rather than sleeps. Do not expand scope to writers whose contract intentionally raises a move conflict.

- [ ] **Step 3: Apply the same bounded retry boundary**

Reuse a private snapshot helper only if two readers genuinely share the complete operation; do not expose filesystem retries in `WorkStore`.

- [ ] **Step 4: Run affected tests and commit only if code changed**

Run the exact focused pytest modules found in the audit.

Expected: PASS. If no sibling is vulnerable, record the classified list in the implementation outcome and make no empty commit.

### Task 5: Documentation Sync

**Files:**
- Modify: `README.md`
- Modify: `docs/release-notes/upcoming.md`
- Modify: `docs/changelogs/upcoming.md`
- Modify: `skills/tcw-work/SKILL.md` or `skills/tcw-work/references/transitions.md`

- [ ] **Step 1: Document concurrent-read guarantees**

Keep README language user-centered: concurrent claims do not bypass blockers or crash reads. Put recovery/error detail in the transition reference.

- [ ] **Step 2: Add release and technical changelog entries**

Describe stable adapter reads and composite retry behavior without exposing `.claiming/` as model API in release notes.

- [ ] **Step 3: Align the work skill guardrails**

If interrupted-claim messaging or takeover guidance changes, update the transition reference with the exact CLI recovery action.

- [ ] **Step 4: Commit the documentation block**

```bash
git add README.md docs/release-notes/upcoming.md docs/changelogs/upcoming.md skills/tcw-work
git commit -m "docs: describe concurrency-safe work reads"
```

### Task 6: Final verification

- [ ] **Step 1: Run contention tests repeatedly**

Run: `pytest tests/test_external_work_store.py tests/test_store_editor.py tests/test_serve.py -q --count=10` if `pytest-repeat` is installed; otherwise loop the command ten times in the shell.

Expected: all iterations pass without hangs or timing flakes.

- [ ] **Step 2: Run the full suite**

Run: `pytest -q`

Expected: PASS.

- [ ] **Step 3: Validate diff and timing assumptions**

Run: `git diff --check && git status --short`

Expected: clean formatting and only intended files. Confirm the missing-slug timing test has generous CI margin while remaining far below 500 ms.

## Verification

The suite must prove both halves of the claim window: private directory and just-published active item. Review logs/timings to confirm ordinary misses never sleep and abandoned claims consume only one bounded wait.
