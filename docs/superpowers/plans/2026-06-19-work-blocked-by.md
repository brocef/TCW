# Work blocked-by relations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `blocked` work-item status with a blocked-by *relation* stored in `state.yaml`, with cycle-safe edit commands, a topologically ordered board, and start/complete gating on unresolved blockers.

**Architecture:** Blocked-ness becomes a derived overlay, not a folder. The abstract `WorkStore` (core) owns the new relation ops, cycle detection, ordering, and gating — all pure computation over `get`/`set_field`. `FsWorkStore` only changes where it reads the list (`state.yaml`, not `links.yaml`) and which status folders exist. The CLI gains `edit` / `--blocked-by` / `--force`.

**Tech Stack:** Python ≥3.11 (type hints, no `from __future__ import annotations`), pytest over `tmp_path` git repos, PyYAML, stdlib `argparse`.

**Spec:** `docs/superpowers/specs/2026-06-19-work-blocked-by-design.md` (read it; this plan implements it verbatim).

## Global Constraints

- Python **≥3.11**; do **not** add `from __future__ import annotations`.
- Type hints on all new functions/methods.
- ABC + adapter pattern: anything implementable by a non-FS backend lives in `WorkStore` (core), not `FsWorkStore`. Run the litmus test before adding any interface method.
- Commit messages: **no co-authoring trailers**; conventional-commit style (`feat(work):`, `test(work):`, `docs(work):`).
- Tests: each runs `git init` + sets `user.name`/`user.email` over a `tmp_path` repo (use the existing `node()` helper in `tests/test_work.py`).
- Work on branch `work-blocked-by` (already checked out).
- `WORK_STATUSES` is duplicated at `tcw/store/base.py` and `tcw/store/fs.py` — they must stay identical.

---

### Task 1: Remove the `blocked` status; move `blocked_by` into `state.yaml`

Atomic demolition: dropping the `blocked` folder forces removing `block`/`unblock`/`link` and rewriting the tests that use them, all in one green commit. No new behavior yet — just the relation data readable/writable via the existing `set_field`/`get`.

**Files:**
- Modify: `tcw/store/base.py` (`WORK_STATUSES`, `LEGAL_TRANSITIONS`, `WorkItem`, `WorkStore`)
- Modify: `tcw/store/fs.py` (`WORK_STATUSES`, `FsWorkStore.get`, remove `link`, `_safe_yaml` docstring)
- Modify: `tcw/work/cli.py` (`SUBCOMMANDS`, remove `_block`/`_unblock` + their parsers, `_print_item`, `init` help)
- Test: `tests/test_work.py` (rewrite the 5 block-dependent tests; add a `blocked_by`-in-`state.yaml` read test)

**Interfaces:**
- Produces: `WorkItem.blocked_by: list[dict]`; `WORK_STATUSES = ("inbox","backlog","active","completed")`; `FsWorkStore.get()` reads `blocked_by` from `state.yaml`. `WorkStore.block/unblock/link` and `FsWorkStore.link` no longer exist.

- [ ] **Step 1: Rewrite the block-dependent tests first (they will fail to import/run)**

In `tests/test_work.py`:

Replace `test_init_gitkeep_persistence` (drop `"blocked"`):

```python
def test_init_gitkeep_persistence(tmp_path):
    root = node(tmp_path)
    for s in ("inbox", "backlog", "active", "completed"):
        assert (root / "docs" / "work" / s / ".gitkeep").is_file()
    assert not (root / "docs" / "work" / "blocked").exists()
```

Replace `test_legal_transition_lifecycle` (no block/unblock leg):

```python
def test_legal_transition_lifecycle(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    assert st.get(item.slug).status == "backlog"
    assert st.start(item.slug).status == "active"
    assert st.complete(item.slug, "done", ["acked"]).status == "completed"
    assert st.get(item.slug).resolution == "done"
```

Replace `test_illegal_transitions_refused` (drop the `block` setup):

```python
def test_illegal_transitions_refused(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(IllegalTransition):
        st.complete(item.slug, "done", [])    # backlog → completed (only from active)
    st.start(item.slug)
    st.complete(item.slug, "done", [])
    with pytest.raises(IllegalTransition):
        st.start(item.slug)                   # completed → active (sink)
```

Delete `test_unblock_refuses_unresolved_passes_on_dropped` and `test_unblock_passes_when_blocker_completed` entirely (and the `# ── unblock blocker resolution ──` comment) — gating is re-tested in Task 3.

Add a new test (the relation now lives in `state.yaml`):

```python
def test_blocked_by_read_from_state_yaml(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    assert st.get(item.slug).blocked_by == []          # absent key → empty
    st.set_field(item.slug, "blocked_by", [{"external": "vendor"}])
    assert st.get(item.slug).blocked_by == [{"external": "vendor"}]
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `python -m pytest tests/test_work.py -q`
Expected: FAIL — `test_blocked_by_read_from_state_yaml` raises `AttributeError: 'WorkItem' object has no attribute 'blocked_by'` (the field is still named `blocked_on`). The rewritten lifecycle/illegal-transition tests still pass for now because `block`/`unblock` still exist. The point is the suite is red on the new test; proceed.

- [ ] **Step 3: Edit `tcw/store/base.py` — statuses, transitions, dataclass field**

Set `WORK_STATUSES`:

```python
WORK_STATUSES = ("inbox", "backlog", "active", "completed")
```

Set `LEGAL_TRANSITIONS`:

```python
LEGAL_TRANSITIONS = {
    ("inbox", "active"), ("backlog", "active"),     # start
    ("active", "completed"),                        # complete (DoD gate)
}
```

In `WorkItem`, rename the field:

```python
    blocked_by: list[dict] = field(default_factory=list)
```

- [ ] **Step 4: Edit `tcw/store/base.py` — remove `block`, `unblock`, and the `link` primitive**

Delete the `@abstractmethod def link(...)` declaration from `WorkStore`, and delete the entire `block` and `unblock` concrete methods. Leave `_require`, `transition`, `start`, `complete`, `drop` in place (they are rewritten in Task 3 for gating; for now keep `start`/`complete` exactly as they were minus nothing — they don't reference `blocked`).

Also fix the now-stale `WorkStore` class docstring: it currently says "items moving through a **five**-status state machine" and lists the named operations as "`start`/`block`/`unblock`/`complete`/`drop`". Change to a four-status machine with named operations `start`/`complete`/`drop` plus the relation ops `add_blocker`/`remove_blocker` (added in Task 2). (Don't leave the code/design drift the plan itself warns against.)

- [ ] **Step 5: Edit `tcw/store/fs.py` — statuses, `get`, remove `link`, docstring**

Set the module-level constant to match base:

```python
WORK_STATUSES = ("inbox", "backlog", "active", "completed")
```

Rewrite `FsWorkStore.get` to source the list from `state.yaml` and drop the `links.yaml` read:

```python
    def get(self, slug: str) -> WorkItem | None:
        d = self._find(slug)
        if d is None:
            return None
        state = self._safe_yaml(d / "state.yaml")
        content = d / "content.md"
        caps = d / "capabilities.yaml"
        return WorkItem(
            slug=slug,
            title=state.get("title", slug),
            status=d.parent.name,
            phase=state.get("phase", ""),
            created=state.get("created", ""),
            resolution=state.get("resolution"),
            body=content.read_text(encoding="utf-8") if content.exists() else "",
            blocked_by=list(state.get("blocked_by") or []),
            capabilities=load_yaml(caps) if caps.exists() else None,
        )
```

Delete the `FsWorkStore.link` method. Update `_safe_yaml`'s docstring to drop the "links" mention:

```python
    @staticmethod
    def _safe_yaml(path: Path) -> dict:
        """Tolerant load: a malformed state file degrades to empty rather than
        crashing the board (the item still lists, status comes from the dir)."""
        try:
            return load_yaml(path)
        except yaml.YAMLError:
            return {}
```

- [ ] **Step 6: Edit `tcw/work/cli.py` — remove block/unblock, fix `_print_item`, statuses help**

Remove `"block"` and `"unblock"` from `SUBCOMMANDS` (Task 5 adds `"edit"`):

```python
SUBCOMMANDS = {"init", "new", "list", "show", "path", "start", "complete", "drop"}
```

Delete the `_block` and `_unblock` functions. In `add_subparser`, delete the `pb`/`block` and `pu`/`unblock` parser blocks. Change the `init` parser help string to drop `blocked`:

```python
    g.add_parser("init", help="create docs/work/{inbox,backlog,active,completed}/") \
        .set_defaults(func=_init)
```

In `_print_item`, replace the `blocked_on` block with a formatted `blocked_by`:

```python
    if item.blocked_by:
        labels = [b["slug"] if "slug" in b else f"external: {b['external']}"
                  for b in item.blocked_by]
        print(f"blocked_by: {', '.join(labels)}")
```

Remove the now-unused `WORK_RESOLUTIONS`? No — `complete` still uses it. Leave imports as-is **except** nothing references the removed names. (`block`/`unblock` were local; no import change needed.)

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest tests/test_work.py -q`
Expected: PASS (all tests, including `test_blocked_by_read_from_state_yaml`).

- [ ] **Step 8: Commit**

```bash
git add tcw/store/base.py tcw/store/fs.py tcw/work/cli.py tests/test_work.py
git commit -m "refactor(work): drop blocked status; blocked_by lives in state.yaml"
```

---

### Task 2: `add_blocker` / `remove_blocker` with cycle + self-block guards

**Files:**
- Modify: `tcw/store/base.py` (`WorkStore`: add `_entry_for`, `_same_entry`, `_reaches`, `add_blocker`, `remove_blocker`)
- Test: `tests/test_work.py`

**Interfaces:**
- Consumes: `WorkItem.blocked_by`, `WorkStore.get`, `WorkStore.set_field` (Task 1).
- Produces:
  - `WorkStore.add_blocker(self, slug: str, ref: str) -> None`
  - `WorkStore.remove_blocker(self, slug: str, ref: str) -> None`
  - `WorkStore._reaches(self, start: str, target: str) -> bool`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_work.py`:

```python
# ── blocked-by relation ──────────────────────────────────────────────────────

def test_add_and_remove_blocker_roundtrip(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    st.add_blocker(a.slug, b.slug)
    assert st.get(a.slug).blocked_by == [{"slug": b.slug}]
    st.add_blocker(a.slug, b.slug)                      # idempotent
    assert st.get(a.slug).blocked_by == [{"slug": b.slug}]
    st.remove_blocker(a.slug, b.slug)
    assert st.get(a.slug).blocked_by == []
    st.remove_blocker(a.slug, b.slug)                   # absent → no-op


def test_external_blocker_stored(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    st.add_blocker(a.slug, "waiting on vendor")         # unresolvable → external
    assert st.get(a.slug).blocked_by == [{"external": "waiting on vendor"}]
    st.remove_blocker(a.slug, "waiting on vendor")
    assert st.get(a.slug).blocked_by == []


def test_self_block_refused(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    with pytest.raises(ValueError):
        st.add_blocker(a.slug, a.slug)


def test_cycle_refused_direct_and_transitive(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    c = st.create("C", created="2026-01-03")
    st.add_blocker(a.slug, b.slug)                      # A blocked by B
    with pytest.raises(ValueError):
        st.add_blocker(b.slug, a.slug)                  # B blocked by A → direct cycle
    st.add_blocker(b.slug, c.slug)                      # B blocked by C
    with pytest.raises(ValueError):
        st.add_blocker(c.slug, a.slug)                  # C blocked by A → A→B→C→A cycle
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_work.py -k "blocker or cycle or self_block" -q`
Expected: FAIL — `AttributeError: 'FsWorkStore' object has no attribute 'add_blocker'`.

- [ ] **Step 3: Implement the relation ops in `WorkStore` (`tcw/store/base.py`)**

Add inside `WorkStore`, after `_require`:

```python
    def _entry_for(self, ref: str) -> dict:
        """A blocker entry: a resolvable ref → {slug}, else {external}."""
        return {"slug": ref} if self.get(ref) is not None else {"external": ref}

    @staticmethod
    def _same_entry(a: dict, b: dict) -> bool:
        """Entry identity: same slug value, or same external text; never cross."""
        if "slug" in a and "slug" in b:
            return a["slug"] == b["slug"]
        if "external" in a and "external" in b:
            return a["external"] == b["external"]
        return False

    def _reaches(self, start: str, target: str) -> bool:
        """True if `start` (transitively, via blocked_by slugs) depends on `target`."""
        seen: set[str] = set()
        stack = [start]
        while stack:
            cur = stack.pop()
            if cur == target:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            item = self.get(cur)
            if item is None:
                continue
            stack += [b["slug"] for b in item.blocked_by if "slug" in b]
        return False

    def add_blocker(self, slug: str, ref: str) -> None:
        item = self._require(slug)
        entry = self._entry_for(ref)
        if "slug" in entry:
            if entry["slug"] == slug:
                raise ValueError("an item cannot block itself")
            if self._reaches(entry["slug"], slug):
                raise ValueError(f"{ref} → {slug} would create a blocking cycle")
        if any(self._same_entry(entry, e) for e in item.blocked_by):
            return                                       # idempotent
        self.set_field(slug, "blocked_by", item.blocked_by + [entry])

    def remove_blocker(self, slug: str, ref: str) -> None:
        item = self._require(slug)
        kept = [e for e in item.blocked_by
                if e.get("slug") != ref and e.get("external") != ref]
        if len(kept) != len(item.blocked_by):
            self.set_field(slug, "blocked_by", kept)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_work.py -k "blocker or cycle or self_block" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tcw/store/base.py tests/test_work.py
git commit -m "feat(work): add_blocker/remove_blocker with cycle + self-block guards"
```

---

### Task 3: Gating — `unresolved_blockers` + `start`/`complete` with `--force`

**Files:**
- Modify: `tcw/store/base.py` (`WorkStore`: add `unresolved_blockers`; rewrite `start`/`complete`)
- Test: `tests/test_work.py`

**Interfaces:**
- Consumes: `add_blocker` (Task 2), `WorkItem.status`/`blocked_by`.
- Produces:
  - `WorkStore.unresolved_blockers(self, item: WorkItem) -> list[str]`
  - `WorkStore.start(self, slug: str, force: bool = False) -> WorkItem`
  - `WorkStore.complete(self, slug: str, resolution: str, dod_ack: list[str], force: bool = False) -> WorkItem`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_work.py`:

```python
def test_start_gated_on_unresolved_blocker(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    with pytest.raises(ValueError):
        st.start(target.slug)                          # blocker not completed
    assert st.start(target.slug, force=True).status == "active"


def test_start_ungated_when_blocker_completed_or_dropped(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(blocker.slug)
    st.complete(blocker.slug, "done", [])
    assert st.start(target.slug).status == "active"    # completed blocker → resolved


def test_start_passes_on_dropped_blocker_silently(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.drop(blocker.slug)                              # vanished → resolved, no warning
    assert st.start(target.slug).status == "active"


def test_complete_gated_on_unresolved_blocker(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(target.slug, force=True)
    with pytest.raises(ValueError):
        st.complete(target.slug, "done", [])           # still blocked
    assert st.complete(target.slug, "done", [], force=True).status == "completed"
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_work.py -k "gated or ungated or dropped_blocker" -q`
Expected: FAIL — `start()` takes no `force` argument / does not raise.

- [ ] **Step 3: Implement gating in `WorkStore` (`tcw/store/base.py`)**

Add `unresolved_blockers` (place it near `_reaches`):

```python
    def unresolved_blockers(self, item: WorkItem) -> list[str]:
        """Labels of blockers that still block `item`. An entry is unresolved if
        it is external, or a slug whose item is not completed. A slug that no
        longer resolves counts as resolved (silently)."""
        out: list[str] = []
        for b in item.blocked_by:
            if "external" in b:
                out.append(f"external: {b['external']}")
            else:
                blocker = self.get(b["slug"])
                if blocker is not None and blocker.status != "completed":
                    out.append(b["slug"])
        return out
```

Rewrite `start`:

```python
    def start(self, slug: str, force: bool = False) -> WorkItem:
        item = self._require(slug)
        if not force:
            blockers = self.unresolved_blockers(item)
            if blockers:
                raise ValueError("blocked by: " + ", ".join(blockers)
                                 + " (use --force to override)")
        return self.transition(slug, "active")
```

Rewrite `complete` (add the blocker gate; keep the resolution + legality checks; DoD `--confirm` stays in the CLI):

```python
    def complete(self, slug: str, resolution: str, dod_ack: list[str],
                 force: bool = False) -> WorkItem:
        if resolution not in WORK_RESOLUTIONS:
            raise ValueError(f"invalid resolution '{resolution}' "
                             f"(choose: {', '.join(sorted(WORK_RESOLUTIONS))})")
        item = self._require(slug)
        if (item.status, "completed") not in self.LEGAL_TRANSITIONS:
            raise IllegalTransition(f"cannot complete from {item.status} (only active)")
        if not force:
            blockers = self.unresolved_blockers(item)
            if blockers:
                raise ValueError("blocked by: " + ", ".join(blockers)
                                 + " (use --force to override)")
        self.set_field(slug, "resolution", resolution)
        self.set_field(slug, "dod", dod_ack)
        return self.transition(slug, "completed")
```

- [ ] **Step 4: Run the targeted + full suite**

Run: `python -m pytest tests/test_work.py -q`
Expected: PASS (gating tests + all earlier tests; `test_legal_transition_lifecycle` still passes since its item has no blockers).

- [ ] **Step 5: Commit**

```bash
git add tcw/store/base.py tests/test_work.py
git commit -m "feat(work): gate start/complete on unresolved blockers (--force overrides)"
```

---

### Task 4: `topo_order` + `board`

**Files:**
- Modify: `tcw/store/base.py` (module-level `topo_order`; `WorkStore.board`)
- Test: `tests/test_work.py`

**Interfaces:**
- Consumes: `WorkItem.slug`/`blocked_by`, `WorkStore.query`.
- Produces:
  - `topo_order(items: list[WorkItem]) -> list[WorkItem]` (module-level)
  - `WorkStore.board(self, status: str | None = None) -> list[WorkItem]`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_work.py` (import `topo_order` at the top: extend the existing
`from tcw.store.base import IllegalTransition, MultipleMatch` line to also import
`topo_order`):

```python
def test_topo_order_blocker_before_blocked(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")           # will be blocked by B
    b = st.create("B", created="2026-01-02")
    st.add_blocker(a.slug, b.slug)
    ordered = [i.slug for i in st.board()]
    assert ordered.index(b.slug) < ordered.index(a.slug)


def test_topo_order_stable_on_ties(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    c = st.create("C", created="2026-01-03")           # no edges → input order kept
    st.add_blocker(b.slug, "external wait")            # external is not a graph node
    ordered = [i.slug for i in st.board()]
    assert ordered == [a.slug, b.slug, c.slug]         # external doesn't reorder


def test_topo_order_ignores_blocker_outside_set(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    backlog_blocker = st.create("Blocker", created="2026-01-01")
    x = st.create("X", created="2026-01-02")
    y = st.create("Y", created="2026-01-03")
    st.add_blocker(x.slug, backlog_blocker.slug)        # blocker stays in backlog
    st.start(x.slug, force=True)
    st.start(y.slug)
    ordered = [i.slug for i in st.board(status="active")]
    assert ordered == [x.slug, y.slug]                  # blocker not in set → no reorder
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_work.py -k "topo" -q`
Expected: FAIL — `ImportError` for `topo_order` / `board` missing.

- [ ] **Step 3: Implement `topo_order` and `board` (`tcw/store/base.py`)**

Add `topo_order` as a module-level function (place it just above the `WorkStore` class):

```python
def topo_order(items: list[WorkItem]) -> list[WorkItem]:
    """Stable topological sort: a blocker precedes what it blocks.

    An edge counts only when both endpoints are in `items`; ties keep input
    order. A residual cycle (only via hand-edited data) degrades to original
    order for the leftover nodes. ponytail: re-sort the ready set each step — a
    board holds dozens of items, so the simple version is fine.
    """
    pos = {it.slug: i for i, it in enumerate(items)}
    by_slug = {it.slug: it for it in items}
    indeg = {it.slug: 0 for it in items}
    blocks: dict[str, list[str]] = {it.slug: [] for it in items}
    for it in items:
        for b in it.blocked_by:
            bs = b.get("slug")
            if bs in by_slug and bs != it.slug:          # edge present in this set
                blocks[bs].append(it.slug)
                indeg[it.slug] += 1
    ready = sorted((s for s, d in indeg.items() if d == 0), key=pos.get)
    out: list[str] = []
    while ready:
        s = ready.pop(0)
        out.append(s)
        freed = []
        for t in blocks[s]:
            indeg[t] -= 1
            if indeg[t] == 0:
                freed.append(t)
        if freed:
            ready = sorted(ready + freed, key=pos.get)
    placed = set(out)
    out += [s for s in pos if s not in placed]           # residual cycle → input order
    return [by_slug[s] for s in out]
```

Add `board` to `WorkStore` (near `query`/`transition`):

```python
    def board(self, status: str | None = None) -> list[WorkItem]:
        """The board in workable order: query(status) topologically sorted."""
        return topo_order(self.query(status))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_work.py -k "topo" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tcw/store/base.py tests/test_work.py
git commit -m "feat(work): topological board ordering (blocker before blocked)"
```

---

### Task 5: CLI — `edit`, `new --blocked-by`, `start/complete --force`, ordered `list`

**Files:**
- Modify: `tcw/work/cli.py` (`SUBCOMMANDS`, `_split`, `_new`, `_list`, `_start`, `_complete`, `_edit`, `add_subparser`)
- Test: `tests/test_work.py`

**Interfaces:**
- Consumes: `add_blocker`/`remove_blocker` (Task 2), `unresolved_blockers`/`start`/`complete` (Task 3), `board` (Task 4).
- Produces: CLI verbs `edit`, `new --blocked-by`, `start --force`, `complete --force`; `list` ordered + annotated.

- [ ] **Step 1: Write the failing CLI tests**

Add to `tests/test_work.py` (these use `from tcw.cli import main`, as the existing CLI test does):

```python
def test_cli_edit_blocked_by_and_blocks(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    assert main(["work", "edit", a.slug, "--blocked-by", b.slug]) == 0
    assert FsWorkStore.open(root).get(a.slug).blocked_by == [{"slug": b.slug}]
    # reverse direction: a now blocks b's sibling c
    c = st.create("C", created="2026-01-03")
    assert main(["work", "edit", a.slug, "--blocks", c.slug]) == 0
    assert FsWorkStore.open(root).get(c.slug).blocked_by == [{"slug": a.slug}]
    assert main(["work", "edit", a.slug, "--unblocked-by", b.slug]) == 0
    assert FsWorkStore.open(root).get(a.slug).blocked_by == []


def test_cli_edit_blocks_nonexistent_errors(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    a = FsWorkStore.open(root).create("A", created="2026-01-01")
    assert main(["work", "edit", a.slug, "--blocks", "nope"]) == 1


def test_cli_new_blocked_by(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    b = FsWorkStore.open(root).create("B", created="2026-01-01")
    assert main(["work", "new", "A", "--blocked-by", f"{b.slug}, , extra"]) == 0
    items = FsWorkStore.open(root).query(status="backlog")
    a = next(i for i in items if i.title == "A")
    assert a.blocked_by == [{"slug": b.slug}, {"external": "extra"}]


def test_cli_complete_blocker_gate_before_dod(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(target.slug, force=True)
    rc = main(["work", "complete", target.slug, "--resolution", "done", "--confirm"])
    assert rc == 1
    out = capsys.readouterr()
    assert "blocked by" in out.err and "Definition of Done" not in out.out  # fail-fast
    assert main(["work", "complete", target.slug, "--resolution", "done",
                 "--confirm", "--force"]) == 0
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_work.py -k "cli_edit or cli_new or cli_complete_blocker" -q`
Expected: FAIL — `edit` is not a known subcommand / `--blocked-by` unrecognized.

- [ ] **Step 3: Add the comma-split helper and `_edit`/`_new` handlers (`tcw/work/cli.py`)**

Add `"edit"` to `SUBCOMMANDS`:

```python
SUBCOMMANDS = {"init", "new", "list", "show", "path", "start", "edit", "complete", "drop"}
```

Add the helper (place near `_stdin_body`):

```python
def _split(val: str | None) -> list[str]:
    """Comma-split a flag value: strip tokens, drop empties (repo idiom)."""
    return [s.strip() for s in (val or "").split(",") if s.strip()]
```

Replace `_new`:

```python
def _new(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    item = st.create(args.title, body=_stdin_body())
    try:
        for ref in _split(args.blocked_by):
            st.add_blocker(item.slug, ref)
    except _ERRORS as e:
        print(f"tcw work new: {e}", file=sys.stderr)
    print(item.slug)
    return 0
```

Add `_edit`:

```python
def _edit(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    if st.get(args.slug) is None:
        print(f"tcw work edit: no such work item: {args.slug}", file=sys.stderr)
        return 1
    blocks = _split(args.blocks)
    for ref in blocks:                              # validate targets up front
        if st.get(ref) is None:
            print(f"tcw work edit: no such work item: {ref}", file=sys.stderr)
            return 1
    try:
        for ref in _split(args.blocked_by):
            st.add_blocker(args.slug, ref)
        for ref in blocks:
            st.add_blocker(ref, args.slug)
        for ref in _split(args.unblocked_by):
            st.remove_blocker(args.slug, ref)
    except _ERRORS as e:
        print(f"tcw work edit: {e}", file=sys.stderr)
        return 1
    print(f"edited {args.slug}")
    return 0
```

- [ ] **Step 4: Rewrite `_start`, `_complete`, `_list` (`tcw/work/cli.py`)**

Replace `_start`:

```python
def _start(args: argparse.Namespace) -> int:
    return _run(lambda st: st.start(args.slug, force=args.force), f"started {args.slug}")
```

Replace `_complete` (blocker gate before the DoD print):

```python
def _complete(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        item = st.get(args.slug)
    except MultipleMatch as e:
        print(f"tcw work complete: {e}", file=sys.stderr)
        return 1
    if item is None:
        print(f"tcw work complete: no such work item: {args.slug}", file=sys.stderr)
        return 1
    if not args.force:
        blockers = st.unresolved_blockers(item)
        if blockers:
            print(f"tcw work complete: blocked by: {', '.join(blockers)} "
                  f"(use --force to override)", file=sys.stderr)
            return 1
    checklist = st.dod_checklist()
    print("Definition of Done — acknowledge each item:")
    for c in checklist:
        print(f"  [ ] {c}")
    if not args.confirm:
        print("Refused: re-run with --confirm once the checklist is satisfied.", file=sys.stderr)
        return 1
    try:
        st.complete(args.slug, args.resolution, dod_ack=checklist, force=args.force)
    except _ERRORS as e:
        print(f"tcw work complete: {e}", file=sys.stderr)
        return 1
    print(f"completed {args.slug} ({args.resolution})")
    return 0
```

Replace `_list` (ordered board + blocked annotation):

```python
def _list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    for item in st.board(status=args.status):
        blockers = st.unresolved_blockers(item)
        suffix = f"\tblocked-by: {', '.join(blockers)}" if blockers else ""
        print(f"{item.slug}\t{item.status}\t{item.phase or '-'}\t{item.title}{suffix}")
    return 0
```

- [ ] **Step 5: Wire the parsers (`tcw/work/cli.py` `add_subparser`)**

Add `--blocked-by` to the `new` parser:

```python
    pn = g.add_parser("new", help="create a backlog item; prints its slug")
    pn.add_argument("title")
    pn.add_argument("--blocked-by", help="comma-separated slugs/externals that block it")
    pn.set_defaults(func=_new)
```

Add `--force` to `start`:

```python
    pst = g.add_parser("start", help="inbox|backlog → active")
    pst.add_argument("slug")
    pst.add_argument("--force", action="store_true", help="start despite unresolved blockers")
    pst.set_defaults(func=_start)
```

Add the `edit` parser (replacing the deleted block/unblock parsers):

```python
    pe = g.add_parser("edit", help="change blocking links between items")
    pe.add_argument("slug")
    pe.add_argument("--blocked-by", help="comma-separated slugs/externals that block this item")
    pe.add_argument("--blocks", help="comma-separated items this item blocks")
    pe.add_argument("--unblocked-by", help="comma-separated blockers to remove")
    pe.set_defaults(func=_edit)
```

Add `--force` to `complete`:

```python
    pc = g.add_parser("complete", help="active → completed (DoD gate)")
    pc.add_argument("slug")
    pc.add_argument("--resolution", required=True, choices=sorted(WORK_RESOLUTIONS))
    pc.add_argument("--confirm", action="store_true")
    pc.add_argument("--force", action="store_true", help="complete despite unresolved blockers")
    pc.set_defaults(func=_complete)
```

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest tests/test_work.py -q`
Expected: PASS (all tests).

- [ ] **Step 7: Smoke-test the CLI by hand (optional but recommended)**

Run from a scratch repo:
```bash
cd "$(mktemp -d)" && git init -q && git config user.email t@t && git config user.name t
python -m tcw work init
B=$(python -m tcw work new "B")
A=$(python -m tcw work new "A" --blocked-by "$B")
python -m tcw work list            # B should sort before A; A shows "blocked-by: $B"
python -m tcw work start "$A"       # refused: blocked by B
python -m tcw work start "$A" --force
```
Expected: `list` orders `B` before `A`; `start "$A"` (no force) prints "blocked by".

- [ ] **Step 8: Commit**

```bash
git add tcw/work/cli.py tests/test_work.py
git commit -m "feat(work): edit/new blocked-by flags, --force gating, ordered list"
```

---

### Task 6: Documentation sync

Run the `skill-cefailures:documentation-sync` evaluation; this task pre-identifies every entry whose trigger fires. The public CLI surface changed (commands removed/added) and behavior changed, so all Documentation-Sync entries apply, plus the design doc and capabilities.

**Files:**
- Modify: `docs/plan/phase-5-work.md` (the source-of-truth design — rewrite block/unblock sections, the `links.yaml` description, the CLI table, the transition diagram, and the test list)
- Modify: `README.md` (CLI surface)
- Modify: `docs/release-notes/upcoming.md`
- Modify: `docs/changelogs/upcoming.md`
- Modify: `docs/capabilities/work/` (reconcile the work user stories)

- [ ] **Step 1: Update the source-of-truth design `docs/plan/phase-5-work.md`**

Make the doc describe the *new* model (never leave code/design drift — CLAUDE.md):
- Directory list: `inbox, backlog, active, completed` (drop `blocked`); update the "Directories partition by actionability" paragraph to describe blocked-ness as a derived overlay (an item with ≥1 non-completed blocker), not a folder.
- Remove the `block`/`unblock` rows from the CLI table; add `edit` (blocked-by/blocks/unblocked-by), `new --blocked-by`, and `--force` on `start`/`complete`.
- Replace the transition diagram's `block`/`unblock`/`blocked` arc with the four-status machine (`inbox|backlog → active → completed`, `drop` from inbox/backlog).
- Replace the `links.yaml` description with: `blocked_by:` is a list of `{slug}`/`{external}` entries stored in `state.yaml`.
- Update the core-vs-adapter prose: named operations are now `start`/`complete`/`drop` plus the relation ops `add_blocker`/`remove_blocker`, gating via `unresolved_blockers`, ordering via `topo_order`; the adapter no longer has `link`.
- Update the test-coverage list to match Task 1–5 tests.

- [ ] **Step 2: Update `README.md`**

In the `tcw work` usage: remove `block`/`unblock`; document `tcw work edit <slug> --blocked-by/--blocks/--unblocked-by`, `tcw work new "<title>" --blocked-by=a,b`, and `--force` on `start`/`complete`. Note that `list` is ordered so blockers precede the items they block, and annotates blocked items.

- [ ] **Step 3: Update `docs/release-notes/upcoming.md`**

Plain language, no module names. Example entry:
```markdown
- Work items can now record what blocks them. Use `tcw work edit <item> --blocked-by <other>` (or `--blocks` for the reverse, `--unblocked-by` to clear), and `tcw work new "<title>" --blocked-by a,b`. The board (`tcw work list`) now lists blockers before the work they hold up and flags anything still blocked. Starting or completing a blocked item is refused unless you pass `--force`. The separate "blocked" column and the old `block`/`unblock` commands are gone — blocked is now just "has an unfinished blocker".
```

- [ ] **Step 4: Update `docs/changelogs/upcoming.md`**

Technical, grouped, with the commit range. Get the range:
```bash
git rev-parse --short HEAD          # end of range
git log --oneline work-blocked-by   # find the first commit of this branch
```
Add entries:
```markdown
### Added
- `tcw work edit <slug> --blocked-by/--blocks/--unblocked-by` and `tcw work new --blocked-by`; `--force` on `start`/`complete`.
- `WorkStore.add_blocker`/`remove_blocker` (cycle- and self-block-guarded), `unresolved_blockers`, `board()`, and module-level `topo_order`.

### Changed
- `blocked_by` is stored in `state.yaml`; `tcw work list` is topologically ordered and annotates blocked items.
- `WorkItem.blocked_on` → `WorkItem.blocked_by`.

### Removed
- The `blocked` status/folder, `tcw work block`/`unblock`, `WorkStore.block`/`unblock`/`link`, and `links.yaml`.
```

- [ ] **Step 5: Reconcile `docs/capabilities/work/`**

Read the existing work capability file(s) and update any user stories mentioning block/unblock or a blocked status to describe the relation + edit flags + gating. This is a **by-hand** prose edit: `tcw capabilities check` only validates metadata vocabulary and Subject/relatesTo refs — it does **not** parse user-story body text, so it won't flag stale `tcw work block ...` prose. Use it afterward only to confirm metadata/refs are still clean.

- [ ] **Step 6: Invoke the documentation-sync skill to confirm nothing was missed**

Use `skill-cefailures:documentation-sync` against the change set; address anything it flags.

- [ ] **Step 7: Commit**

```bash
git add docs/plan/phase-5-work.md README.md docs/release-notes/upcoming.md docs/changelogs/upcoming.md docs/capabilities/work
git commit -m "docs(work): sync design, README, release notes, changelog, capabilities for blocked-by"
```

---

## Self-Review

**Spec coverage:**
- Model (statuses, transitions, `blocked_by` in `state.yaml`, drop `link`) → Task 1. ✔
- `add_blocker`/`remove_blocker`/entry identity/`_reaches`/self-block/cycle → Task 2. ✔
- `unresolved_blockers` + `start`/`complete` gating + `--force` → Task 3. ✔
- `board`/`topo_order` (both-endpoints-in-set, stable, residual-cycle fallback) → Task 4. ✔
- CLI `edit`/`new --blocked-by`/`--force`/ordered+annotated `list`/`show` formatting → Task 5 (+ `_print_item` in Task 1). ✔
- `--blocks` nonexistent target errors; comma parsing; edit ordering → Task 5. ✔
- Tests-to-rewrite (the 5 block-dependent tests) → Task 1; all new tests distributed across Tasks 2–5. ✔
- Docs sync (phase-5-work, README, release notes, changelog, capabilities) → Task 6. ✔

**Placeholder scan:** No TBD/TODO; every code step shows full code; the one "clever" line (`indeg.__setitem__`) has an explicit alternative inline. ✔

**Type consistency:** `add_blocker(slug, ref)`, `remove_blocker(slug, ref)`, `unresolved_blockers(item)`, `start(slug, force=False)`, `complete(slug, resolution, dod_ack, force=False)`, `board(status=None)`, `topo_order(items)` — names/signatures identical across the task that defines them and the CLI task that consumes them. ✔
