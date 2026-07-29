# Plan: Transactional multi-file writes in the Fs store

Everything below happens in `tcw/store/fs.py` and `tests/test_store_editor.py`
(the "Fault injection — temp-file / atomic-replace failure paths" section that
starts at line 818). `tcw/store/base.py` is not touched.

**Suite command (real, verified):** `python -m pytest -q` from the repo root —
baseline today is `1066 passed in 162s`. Every task below ends with that command
green, so each task is a commit boundary.

## Ordering rationale

The helper lands first with no callers (zero behavioral risk, its own tests
prove it). The two update-shape adopters follow, then `create_work`'s directory
rollback. `FsWorkStore.create` → delegate goes **last and alone**: it is the one
change whose blast radius is the whole test suite (262 `.create(` call sites
across 17 modules), and it only satisfies its acceptance criterion *because*
`create_work` already rolls back by then — delegating earlier would inherit the
weaker path.

---

## Task 1 — `_atomic_write_all(pairs)` helper + its own tests

**Changes:** `tcw/store/fs.py` — add a module-level function directly below
`_atomic_write` (line 546). Two phases: stage every `path.with_suffix(suffix +
".tmp")`, then `tmp.replace(path)` for each in turn. **One** `try` /
`except BaseException:` spans *both* phases; the handler unlinks every temp in
the batch (`missing_ok=True`, so already-promoted entries are a no-op) and
re-raises. One handler rather than two is both the smaller code and the stricter
guarantee: it matches `_atomic_write`, which also cleans up when `replace`
fails, so a failure anywhere — including mid-promote — leaves no `.tmp` junk
beside a real file in the user's git tree. The `BaseException` catch means a
`KeyboardInterrupt` mid-batch still cleans up.

Carries a `# ponytail:` comment naming the ceiling and the upgrade path: the
promote loop is not atomic across files — a process death between two
`replace()` calls still leaves a partial update; upgrade is a journal or a
whole-directory swap (the `accept_inbox` shape), not worth it here.

**Nothing calls it yet.** That is deliberate: the risky adopters land against a
helper whose tests already exist.

Signature is `list[tuple[Path, str]]` — `(target path, content)`, in promote
order. Task 3 calls it with a **one**-entry list, so the helper must not assume
two.

**Tests** (new, in the fault-injection section):
- success: both files written with expected content, no `*.tmp` survives.
- single-pair success: a one-entry list works — the shape `update_work` uses
  when `body is _UNSET`.
- `BaseException` cleanup: inject a `KeyboardInterrupt` (not an `OSError`) into
  the second temp write; assert no `*.tmp` survives and it propagates. This pins
  the `except BaseException` choice so narrowing it to `OSError` later fails a
  test rather than silently leaking temps on Ctrl-C.
- staging failure: patch so the *second* file's temp write raises; assert no
  `*.tmp` remains, **neither** target was created/modified, and the injected
  exception type (not a cleanup error) is what `pytest.raises` catches.
- promote failure (the recorded ceiling): patch `Path.replace` to raise on its
  second call; assert the first target *was* promoted, the second was not, the
  exception propagates, and **no `*.tmp` survives** (the shared handler cleans
  up here too). This test exists so the limit is a decision on record, not an
  accident someone "fixes" without knowing it was known.

**Fault-injection mechanism** (used by every test below — write it once here as
a module-level helper in the test file, ~5 lines):

```python
def _fail_writing(monkeypatch, name, exc=OSError(28, "No space left on device")):
    real = Path.write_text                   # name = "description.md", "initial-request.md", …
    def guard(self, *a, **kw):
        if self.name.startswith(name):
            raise exc
        return real(self, *a, **kw)
    monkeypatch.setattr(Path, "write_text", guard)
```

Matching on the target's name (temps are `<name>.tmp`, so `startswith` covers
both) is deterministic where a call-counter is not — `_stage`, `git`, and
fixture setup do their own writes.

**Verified by:** `python -m pytest -q tests/test_store_editor.py` then the full
`python -m pytest -q`.

---

## Task 2 — `_write_node` uses the helper, and rolls back a directory it created

**Changes:** `FsTreeStore._write_node` (fs.py:625–631):

1. Capture `existed = d.exists()` **before** `d.mkdir(parents=True, exist_ok=True)`.
2. Replace the two `_atomic_write` calls with one `_atomic_write_all` call.
3. Wrap that call in `try` / `except BaseException:` → `shutil.rmtree(d,
   ignore_errors=True)` **only when `not existed`** / `raise`. (`shutil` is
   already imported — `accept_inbox` uses it at fs.py:2265.)
4. `self._stage(...)` stays **outside** the `try`. A git failure after both
   files landed leaves a fully valid object on disk; deleting it would destroy
   content the caller just wrote, which is worse than an unstaged file. The
   failure class in scope is content production, not staging.

This is one edit inherited by all four call sites — `fs.py:748` and `1229`
(`add`, which pre-checks `d.exists()` and raises, so `existed` is always False
there) and `fs.py:977` and `1614` (update, `existed` always True). `update_term`
and `update_capability` are **not** patched directly.

**Tests:**
- `_write_node` against a node that already existed (via `FsTaxonomyStore.update_term`),
  failing on `description.md`: `meta.yaml` **and** `description.md` both hold
  their prior bytes (AC 3).
- `_write_node` against a new node (via `FsTaxonomyStore.add`), failing on
  `description.md`: the node directory does not exist afterwards (AC 4).
- both: no `*.tmp` anywhere under the store root, injected exception reaches the
  caller (AC 6).

**Verified by:** `python -m pytest -q` — the whole taxonomy and capabilities
suites (`test_taxonomy.py`, `test_capabilities*.py`, `test_store_nodes.py`,
`test_store_editor.py`) exercise this helper on every write, so a regression
here is loud.

---

## Task 3 — `update_work` uses the helper

**Changes:** `FsWorkStore.update_work` (writes at fs.py:2623–2626). Build the
pair list — always `state.yaml`, plus the body when `body is not _UNSET` — and
make one `_atomic_write_all` call. No directory rollback: the item directory
already exists, and phase-1 staging is the protection. `self._stage(...)` and
the re-parent `_mv` below it are unchanged and stay outside.

**Tests:** `update_work(slug, title=…, body=…)` failing on the body write —
`state.yaml` is byte-for-byte unchanged, the body is byte-for-byte unchanged, no
`*.tmp` remains, injected exception propagates (AC 5, AC 6).

**Verified by:** `python -m pytest -q`; `test_serve_write.py` and `test_work.py`
drive `update_work` heavily, including the `parent`-move path that must still
run after the writes.

---

## Task 4 — `create_work` rolls back its directory

**Changes:** `FsWorkStore.create_work` (fs.py:2499–2503). Keep the two
`_atomic_write` calls; wrap them in `try` / `except BaseException:` →
`shutil.rmtree(d, ignore_errors=True)` / `raise`. `d.mkdir(parents=True)` (no
`exist_ok`) already proves the directory did not exist, so an unconditional
rmtree is correct here — no `existed` flag needed. `self._stage(...)` stays
outside the `try`, for the same reason as Task 2.

`ignore_errors=True` is the deliberate choice from the spec's Risks: if rollback
itself cannot proceed the caller still sees the real failure, at the price of a
leftover directory. A brief comment says so.

`mkdir(parents=True)` may also create an intermediate `backlog/`; rollback
removes only the leaf. An empty `backlog/` is inert — git does not track it and
every read path tolerates it. Worth one comment line, not code.

**Tests:** `create_work` failing on `initial-request.md` — no directory at the
item's path, no `*.tmp` under the store root, injected exception propagates
(AC 1, AC 6).

**Verified by:** `python -m pytest -q`.

---

## Task 5 — `FsWorkStore.create` delegates to `create_work`

**Changes:** `FsWorkStore.create` (fs.py:2277–2296) becomes a single delegating
call — same signature, `WorkItem` return type preserved via
`create_work(...).item` (`get_detail` builds `WorkDetail.item` from `self.get(slug)`
at fs.py:2379, so this *is* the `self.get(slug)` the spec asks for, without a
second read). The whole `_unique_slug` / parent-resolution / `mkdir` /
`write_text` / `dump_yaml` / `_stage` body is deleted — it was a duplicate and
weaker copy of `create_work`'s create path.

A `# ponytail:` comment states the ceiling: one create path, with `create` kept
as the `WorkItem`-returning face for `WorkStore.create` (`base.py:931`) and the
262 existing call sites; the upgrade path is retiring it once callers move to
`create_work`. `base.py` is **not** edited (AC 7).

Two accepted behavioral deltas (both pre-verified against the tree, not assumed):
- empty title now raises `ValueError` — no test passes one (grepped: no
  `.create("")` / `.create()` anywhere in `tests/`).
- `priority: null` is no longer written when unset — every reader goes through
  `load_yaml` + `.get()`, and no test asserts on raw `state.yaml` text produced
  by `create` (the four raw-text reads in `tests/` are
  `test_store_editor.py:781/786` byte-equality before/after an update,
  `test_work_tags.py:110/145` on `create_work`/CLI-created items, and
  `test_work.py:1260/1644` + `test_lifecycle_hooks.py:50` which parse YAML).

**Tests:**
- `create` failing on `initial-request.md` — no directory at the item's path,
  exception propagates (AC 2, inherited from Task 4's rollback).
- `create("")` raises `ValueError` — one line, pinning the accepted behavioral
  delta so it reads as a decision rather than a regression if someone hits it
  later.

A grep-style assertion is unnecessary: AC 2's "contains no `write_text`/`dump_yaml`
write path of its own" is satisfied by the deletion and visible in review.

**Verified by:** `python -m pytest -q` — this is the task where "no edits to
existing test call sites" (AC 8) is proven. If any test does fail, the failure is
information about the deltas above, not licence to edit the test; bring it back
to the spec.

---

## Documentation Sync

Evaluated with the `documentation-sync` skill against every entry in
`CLAUDE.md`. These run as **one block after Task 5**, in a single pass over the
finished diff.

| Entry | Trigger | Fires? | Why |
|---|---|---|---|
| `README.md` | Public-API | **No** | No CLI surface change: no command, flag, argument, or output changes. The stricter empty-title path in `create` is not reachable from the CLI (`cli.py:216` already goes through `create_work`). |
| `docs/release-notes/upcoming.md` | Public-API | **Yes** | User-visible behavior changes on a real failure path — a write interrupted by a full disk or a permission error no longer leaves a half-written item or term behind. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **Yes** | Behavior-affecting code change (not cosmetic). |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | **No** | No component's CLI surface, model/fields, lifecycle, or guardrails change. The skills teach agents to *operate* the components; nothing they say becomes untrue. |

**Task D1 — `docs/release-notes/upcoming.md`.** Add a short plain-language
section (no module names, no `_atomic_write_all`): if TCW is interrupted while
saving — disk full, a permissions problem — the item or term it was saving is
left exactly as it was, instead of half-written. Name the honest limit in one
sentence: a machine losing power during the final moment of the save is still
not covered.

**Task D2 — `docs/changelogs/upcoming.md`.** Under **Fixed** (add the heading;
the file currently has Added/Changed/Internal): `_atomic_write_all` and the
staging/promote split; directory rollback in `_write_node` (guarded by
`existed`) and `create_work`; the residual promote-window ceiling. Under
**Changed** or **Internal**: `FsWorkStore.create` now delegates to `create_work`,
with the two behavioral deltas (empty title rejected; `priority` key omitted when
unset) stated explicitly — those are the entries a future reader will want when
something surprises them.

---

## Verification

Automated (`python -m pytest -q`, repo root) covers acceptance criteria 1–6 and
8 directly. What it does not check, and how to check it:

- **AC 7 — `base.py` unchanged.** No test asserts this. *(Corrected during
  implementation: this item is worked on `main` itself, not a branch, so
  `git diff main -- tcw/store/base.py` compares `main` to itself and is empty no
  matter what the change did. Diff against the item's start commit instead —
  `git diff --stat <the "→ active" commit>..HEAD -- tcw/store/base.py`.)*
- **AC 2's second half — `create` has no write path of its own.** Read the final
  `create`; it should be a docstring/comment plus one `return`. `grep -n
  "write_text\|dump_yaml" tcw/store/fs.py` should show no hit inside it.
- **The ponytail ceilings are actually written down.** Three `# ponytail:`
  comments must exist: the promote window on `_atomic_write_all`, the TOCTOU
  window on `_write_node`'s rollback, and the single create path on `create`.
  `grep -n "ponytail:" tcw/store/fs.py`.
- **The fault injection is really injecting.** A test that patches the wrong
  name passes vacuously (the code never fails, the assertion "directory absent"
  is false — but "state unchanged" would be trivially true). For each
  *unchanged-state* test, confirm by hand once that `pytest.raises` actually
  caught the injected `OSError`, i.e. the assertion is `pytest.raises(OSError)`
  around the call, not a bare call.
- **Nothing under the store root leaks temps.** The `**/*.tmp` glob assertions
  are per-test; run one manual `find` under a failed-run tmpdir if a test is ever
  weakened.
- **Concurrency is explicitly not verified.** The `existed` check in
  `_write_node` is TOCTOU-racy under concurrent writers, and per the spec's
  sharpened Risks entry this introduces a *new* failure mode, not just an
  inherited one: a rollback can remove a node a second writer created between
  our check and our failure. No test is written for it — reproducing it needs
  real concurrency, which is the separate backlog item's job. The rollback in
  Task 2 carries a `# ponytail:` comment naming this ceiling and pointing at
  that item.

## Notes

Read while planning, worth keeping:

- **`FsWorkStore.create` has no caller under `tcw/`** — re-verified this
  session: `grep -rn "\.create(" --include=*.py tcw/` returns nothing. Every
  production create goes through `create_work`.
- **`_write_meta` exists too** (used at fs.py:1611/1614's siblings for override
  bodies). It writes a *single* file, so it is out of scope — do not "unify" it
  with `_atomic_write_all` while in the neighborhood.
- **`_write_node`'s two `add` call sites pre-check `d.exists()` and raise**, so
  `existed` is False there by construction; the two update call sites always
  have an existing directory. The flag is precise, not defensive.
- **`update_work` writes the body only when `body is not _UNSET`** — the pair
  list is 1 or 2 entries. Don't unconditionally include the body path; writing an
  unchanged body would churn its revision hash (`_revision_multi`, fs.py:2387)
  and break the stale-revision guard's meaning.
- **The suite takes ~2m45s.** During Tasks 1–4, `python -m pytest -q
  tests/test_store_editor.py tests/test_taxonomy.py tests/test_capabilities.py
  tests/test_work.py` is the fast inner loop; the full run is still required at
  each commit boundary.
- **`accept_inbox` (fs.py:2246–2273) stays untouched.** It already has the
  property via a stronger mechanism (`mkdtemp` + `os.replace` of a whole
  directory). It is the reference for the upgrade path named in the
  `_atomic_write_all` ponytail comment, should the promote window ever matter.
