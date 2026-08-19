# Plan — Validate capability Subject and Feature refs at write time

Six tasks. The spec settled every design question; this orders them so the suite
is green at each commit boundary and names the exact strings that prove "one
renderer" at implementation time rather than at review time.

**This plan addresses code by symbol, not by line.** That is not a style
preference: `FsCapabilitiesStore.set` moved three times *while this plan was
being written* — `:1644` → `:1669` → `:1673` — because a sibling item is
committing into `tcw/store/fs.py` right now (see `## Notes`). Every symbol named
below is unique within `FsCapabilitiesStore`, so the name is a complete address
and a line number would only rot. Where a line is genuinely useful for
navigation it is marked *as of `b59ffbd`* and should be re-derived, not trusted.

Anchors as of `b59ffbd`, for orientation only: `add` `:1567`,
`_validate_fields` `:1606`, `_write_target` `:1626`, `_merge_meta` `:1659`,
`set` `:1673`, `check` `:1745`, `_ref_error` `:1873`, `_check_globals` `:1881`,
`_check_subject` `:1894`, `_check_feature` `:1907`, `update_capability` `:1944`.

## Caller walk

The spec's Design §2 removes the `where` parameter from three methods and
extracts a fourth block out of `check`. Before ordering that, every caller:

| Symbol | Callers (whole repo, `tcw/` + `tests/`) | What it needs |
| --- | --- | --- |
| `_check_globals` | **one**: `check` | prefix moves to the caller |
| `_check_subject` | **one**: `check` | same |
| `_check_feature` | **one**: `check` | same |
| `_ref_error` | **two**: `check`, inline for `Superseded by`/`Blocked by`; and `_check_globals` | unchanged — keep it as-is, it already returns an unprefixed tail |
| `_validate_fields` | **two**: `set`, `update_capability` | both gain ref refusal for free; this is the seam |
| `_merge_meta` | **two**: `set`, `update_capability` | untouched |
| `_write_target` | **two**: `set`, `update_capability` | untouched by this item; **the symlink item guards it** |

**The walk turned up something the spec did not predict, and it makes Task 1
safer than the spec assumed: no test calls any of the four helpers directly.**
`grep -rn --include=*.py "_check_globals\|_check_subject\|_check_feature\|_ref_error\|_validate_fields" tcw/ tests/`
returns only the definitions and the call sites above. The three
`test_check_feature_*` / `test_check_feature_ref_ok` hits are *test function
names*, not calls. Every stub-injecting test
(`StubTax`/`FeatureTax`/`AmbiguousFeatureTax`, `tests/test_capabilities.py:45-63`
and `:92-96`) drives the **public** `check(taxonomy=…)`, never a helper. So the
signature change is invisible to the suite, and Task 1 is pure motion with no
test edit at all — which is exactly the property that makes it revertable.

One consequence to record: **the spec's own Reproduction snippet calls
`cap._check_subject("web/editing", {...}, AmbigTax())` with a `where` argument.**
After Task 1 that call is written `cap._check_subject({...}, AmbigTax())` and
returns `["Subject → ambiguous ref 'dup'"]` without the prefix. The spec is not
wrong about the *behavior*; the snippet just records a pre-Task-1 call shape.
Do not "fix" the committed spec — note it in `outcome.md`.

## The six message strings, byte for byte

These are what `check` emits today — its inline `Superseded by`/`Blocked by`
block, plus `_check_globals`, `_check_subject` and `_check_feature` — and what
the refusal must emit after Task 1, minus the `f"{where}: "` prefix. **Copy them
from here into the test, not from memory.** `{tok}`/`{ref}`/`{subj}`/`{feature}`
are the caller's raw value; `{kind}` is `Term.kind`.

| Field | Condition | String after the `<path>: ` prefix is stripped |
| --- | --- | --- |
| `Superseded by` | unresolvable | `Superseded by → dangling identifier '{v}'` |
| `Superseded by` | ambiguous | `Superseded by → ambiguous identifier '{v}'` |
| `Blocked by` | unresolvable | `Blocked by → dangling identifier '{v}'` |
| `Blocked by` | ambiguous | `Blocked by → ambiguous identifier '{v}'` |
| `Roles` | not `roles/`-prefixed | `Roles '{tok}' must be a roles/ slug` |
| `Roles` | unresolvable | `Roles → dangling identifier '{ref}'` |
| `Roles` | ambiguous | `Roles → ambiguous identifier '{ref}'` |
| `When` | not `conditions/`-prefixed | `When '{tok}' must be a conditions/ slug` |
| `When` | unresolvable | `When → dangling identifier '{ref}'` |
| `When` | ambiguous | `When → ambiguous identifier '{ref}'` |
| `Subject` | unresolvable | `Subject → dangling ref '{subj}'` |
| `Subject` | ambiguous | `Subject → ambiguous ref '{subj}'` |
| `Feature` | unresolvable | `Feature → dangling ref '{feature}'` |
| `Feature` | ambiguous | `Feature → ambiguous ref '{feature}'` |
| `Feature` | wrong kind | `Feature → ref '{feature}' points to {kind}, expected Feature` |

Three shapes worth noticing before writing the extraction:

- **`Roles`/`When` have a non-`→` variant.** The prefix rule (`must be a
  roles/ slug`) is not a ref problem in the `→` family, but it lives in the same
  loop and is refused on the same write. Do not drop it.
- **`Roles`/`When` are comma-split and `!`-negatable** (in `_check_globals`): the
  token keeps its `!` in the "must be a … slug" message, and loses it (`ref =
  tok.lstrip("!")`) in the `→` messages. Preserve both.
- **`Feature`'s wrong-kind string is written across two source lines** in
  `_check_feature` and concatenates to one line with a single space before
  `{kind}`. Keep the join exact.

## Ordering rationale

Task 1 is pure motion — no behavior change, no test edit — so its diff reviews
as motion and reverts alone. Task 2 changes only `check`'s default and is
isolated from writes, so a bisect names it. Task 3 is the reported fix and the
first behavior change users see; it ships with the one test it breaks. Task 4
depends on Task 3 (it needs `_validate_fields` to already refuse) and is the
only task touching a file outside `tcw/store/fs.py`. Tasks 5 and 6 close.

Tasks 2 and 3 were **measured, not predicted** — see each task's "Verified by".

## Criterion coverage

Every acceptance criterion, and the task that discharges it — the spec's
self-review requirement, made explicit so nothing rides on prose.

| Criteria | Task |
| --- | --- |
| 1-7 (CLI refusals, all six fields, multi-problem, byte-identical wording) | 3 |
| 8 (PATCH 422, `meta.yaml` unchanged) | 3 — `update_capability` shares the seam; no serve edit |
| 9, 10 (POST refused leaves nothing; valid POST still 201) | 4 |
| 11 (existing bad data stays repairable via `--status Omitted`) | 3 |
| 12 (taxonomy-less node still accepts `Subject`, still refuses `Blocked by`) | 3 |
| 13 (`check()` fallback; falsey injected taxonomy still wins) | 2 |
| 14 (one renderer, checked behaviorally) | 1 builds it, 3 asserts it |
| 15 (suite green; exactly one rewritten test) | 3 |
| 16 (this repo still clean) | 5, and `## Verification` |
| 17 (documentation, per document) | 5 (the two capability bodies), 6 (the four entries) |

No task exists that no criterion needs; no criterion lacks a task.

## Tasks

### 1. Extract `_ref_problems` (no behavior change)

**Changes** `tcw/store/fs.py`, `FsCapabilitiesStore` only.

Add one private method returning the unprefixed tails, and drop the `where`
parameter from the three helpers it absorbs:

```python
def _ref_problems(self, f: dict, taxonomy) -> list[str]:
    """Every cross-object ref problem in `f`, worded exactly as `check` reports
    it, minus the `<path>: ` location prefix. The single renderer: `check`
    prefixes these, the write path raises them."""
    out = []
    for key in ("Superseded by", "Blocked by"):
        if key in f and (e := self._ref_error(str(f[key]))):
            out.append(f"{key} → {e}")
    return out + self._check_globals(f) + self._check_subject(f, taxonomy) \
               + self._check_feature(f, taxonomy)
```

`check`'s seven ref lines collapse to one:

```python
problems += [f"{where}: {p}" for p in self._ref_problems(f, taxonomy)]
```

`_ref_error` keeps its signature — it already returns an unprefixed tail and has
a second caller inside `_check_globals`.

**This task is pure motion.** Every emitted string must be byte-identical to the
table above. The suite must pass with **no test modified**; if a test needs
editing, the extraction changed behavior and is wrong.

**Verified by** `python -m pytest -q` green with a clean `git diff --stat
tests/` — zero test files touched. The wordings are asserted at
`tests/test_capabilities.py:207-256` and
`tests/test_capabilities_federation.py:156-200`. Criterion 14's behavioral
one-renderer test is written in Task 3, once there are two paths to compare.

### 2. `_taxonomy()` accessor, and `check` falls back to it

**Changes** `tcw/store/fs.py`, `FsCapabilitiesStore`.

```python
def _taxonomy(self) -> "FsTaxonomyStore | None":
    """The sibling taxonomy store for this node, or None if it has none.

    The FS adapter's answer to "where does this store's taxonomy live"; another
    adapter answers it from its own connection. Not on the abstract interface.
    """
    d = self.node_root / "docs" / "taxonomy"
    return FsTaxonomyStore.open(self.node_root) if d.is_dir() else None
```

and in `check`, as the first statement:

```python
taxonomy = taxonomy if taxonomy is not None else self._taxonomy()
```

**`is not None`, not `or`** — spec Design §4. A falsey injected store must still
win; `or` would discard it and break criterion 13.

Then delete the two duplicate wirings this replaces:
`_taxonomy_for` (`tcw/capabilities/cli.py:30-32`) with its only call site
(`cli.py:227` → `FsCapabilitiesStore.open(node).check()`), and the `tax = …`
conditional in `tcw/validate.py:113-117` (→ `.check(identifier=identifier)`).
Net deletion, and one place decides where a taxonomy comes from.

**Verified by** — measured, not asserted. The fallback was simulated against the
whole suite via a pytest plugin that monkeypatches `check` without editing
`tcw/`, at this task's exact semantics: **1772 passed, 0 failed** on the tree at
`c0b340e`. Reproduce with `scratchpad/simfallback.py` (`python -m pytest -q -p
simfallback`). Also criterion 13, as a new test: on a node whose
`docs/taxonomy/` exists and lacks the ref, bare `check()` reports
`Subject → dangling ref …`; and a stub whose `__bool__` returns `False`, passed
explicitly, is still consulted.

### 3. `_validate_fields` refuses unresolvable refs

**Changes** `tcw/store/fs.py` (`_validate_fields`), and
`tests/test_environment_hardness.py` **in the same commit**.

After the existing normalization loop, before `return out`:

```python
supplied = {k: v for k, v in out.items() if v is not None}
if problems := self._ref_problems(supplied, self._taxonomy()):
    raise ValueError("; ".join(problems))
```

Four details are load-bearing, all from spec Design §2 and §3:

- **`out`, not `fields`** — `Subject` must be checked after `_as_list`
  normalization, so `Subject=a,b` is two refs.
- **`v is not None`** — `None` is `_validate_fields`'s clear sentinel.
  Passing it through makes `_check_globals` stringify it
  (`str(None).split(",")` → a bogus `must be a roles/ slug` for a field the
  caller just cleared).
- **`supplied`, never the merged node** — a `set --status Omitted` on a
  capability that already stores a bad ref must still succeed (criterion 11).
- **All problems, joined `"; "`** — not first-wins. No message contains
  `no such`, so `_map_store_error` (`tcw/serve/__init__.py:196-216`) keeps them
  at 422 rather than 404.

`set` and `update_capability` need **no edit**: both already call
`_validate_fields` ahead of their first `mkdir` — `set` on its first line, and
`update_capability` before its revision check, `_write_target` and `mkdir`.
Re-confirm that order at `implement` rather than assuming it; the non-git item
is inserting a `_require_repository()` line into both.

**The test this breaks, rewritten in the same commit.**
`tests/test_environment_hardness.py::TestLoneProject::test_capability_check_dangling_subject`
builds its fixture with `caps.set("routes/x", {"Subject": "ghost"})` — a call
this task makes impossible. Rewrite it to write the invalid node directly (the
`write_cap` helper in `tests/test_capabilities.py`) and keep asserting that
`check` reports it dangling. Its docstring records why:

```python
def test_capability_check_dangling_subject(self, tmp_path):
    """Invalid data is written directly, not through `set`: `set` refuses a
    dangling ref at write time. `check` must still report data that predates
    that rule — which is what keeps existing bad refs repairable, not stuck."""
```

**Verified by** — measured. Tasks 2+3 together were simulated against the whole
suite (`scratchpad/simwrite.py`, `python -m pytest -q -p simwrite`) on the
post-`c0b340e` tree: **`1 failed, 1766 passed`**, and the one failure is exactly
the test named above, with `ValueError: Subject → dangling ref 'ghost'`. So
"exactly one casualty" is a measurement, not a prediction.

Compare totals across runs with care rather than treating them as a constant:
the non-git item is landing tests as it goes, so the suite grew from 1763
(`aff0cbb`) to 1767 to 1772 during this planning stage. The durable claim is
**one failure, and it is that test** — re-run the simulation at `implement`
rather than trusting the absolute number.

Also criteria 1-8, 11, 12, 14 and 15 as new or re-run tests.

### 4. `add` takes its fields, so `POST /api/capabilities` is one write

**Changes** `tcw/store/base.py` (the abstract signature), `tcw/store/fs.py`
(`FsCapabilitiesStore.add`), `tcw/serve/__init__.py` (the POST handler).

**Abstract, `tcw/store/base.py:370-372`** — one optional trailing keyword; the
docstring gains the refusal:

```python
@abstractmethod
def add(self, identifier: str, name: str | None = None, status: str = "Missing",
        body: str = "", fields: dict[str, Any] | None = None) -> Capability:
    """Create a local capability folder at `identifier` (a path). Refuse a
    collision. `fields` are validated as `set` validates them, before anything
    is written, so a create carrying a bad field writes nothing."""
```

**`fs.py`** — validate after the cheap refusals, merge before `_write_node`:

```python
d = self.root / path
if d.exists():
    raise ValueError(f"capability already exists: {path}")
norm = self._validate_fields(fields or {})   # after the cheap checks: this one
                                             # may open a taxonomy store
display = name or path.rsplit("/", 1)[-1].replace("-", " ").title()
meta = {"id": _mint_cap_id(), "name": display, "Status": status}
meta.update({k: v for k, v in norm.items() if v is not None})
self._write_node(d, meta, body)
```

Field values win over the `status` parameter — precisely what add-then-`set`
does today, so the happy path is byte-identical. A `None` sentinel is skipped:
on a node being created there is nothing to clear, and `_merge_meta` pops the
key today on a non-override node, so the resulting `meta.yaml` matches.

**`tcw/serve/__init__.py`**, the `POST /api/capabilities` handler — three lines
become one:

```python
capabilities.add(cap_path, name=name, status=status, body=body_text, fields=fields)
```

Delete the `if fields: capabilities.set(cap_path, fields)` that followed. The
handler's existing `except (ValueError, RefError)` already maps to
422 — no error-handling change.

**Every existing caller of `add`, verified compatible** (none passes a fifth
positional, so the trailing keyword is invisible to all of them):

| Caller | Call |
| --- | --- |
| `tcw/capabilities/cli.py:91` | `st.add(args.path, name=…, status=…, body=…)` — `tcw capabilities add` has no `--field` flag, and this task does **not** add one |
| `tcw/serve/__init__.py:940` | the one caller that changes |
| `tests/test_serve_write.py:52`, `:966`, `:1499` | positional path + name/status |
| `tests/test_multiproject.py:50` | `caps.add("orders", "Place an order")` |
| `tests/test_environment_hardness.py:294`, `:295`, `:302`, `:308`, `:369`, `:377`, `:458`, `:474`, `:560`, `:567`, `:789`, `:829`, `:844` | path + `name=`/`status=` |
| `tests/test_capabilities.py:104`, `:115`, `:132`, `:133`, `:139`, `:141`, `:202`, `:444`, `:453`, `:462` | path + `name=`/`body=` |

**Verified by** criteria 9 and 10, plus `tests/test_serve_write.py:842-851`
(`test_create_with_fields`) passing **unmodified** — that is the happy-path
proof. New test: POST with a dangling `Feature`, with `NotAField`, and with
`status: "InvalidStatus"` each return 422 **and** leave no
`docs/capabilities/<path>/` and nothing staged. Criterion 9 needs eyes as well
as a test — see `## Verification`.

### 5. Capabilities axis

**REQUIRED SUB-SKILL: use `tcw-capabilities`.** Both entries are already
`changed:` in this item's `capabilities.yaml`; neither changes Status.

- `capabilities/set-a-capabilitys-status` (`cap-03f1a5`) — the body says `set`
  updates "any field in the locked vocabulary in place" and says nothing about
  what a reference-bearing field may hold. State that a ref field must resolve
  and that a write carrying one that does not is refused with the same problem
  `check` would report. Name the fields (`Subject`, `Feature`, `Superseded by`,
  `Blocked by`, `Roles`, `When`), since the scope is six, not two.
- `web/editing` (`cap-d799b3`) — the body promises "Every saved object is
  immediately checked with TCW's standard validation rules, with any findings
  shown as **post-save** warnings." Reconcile: a capability's ref fields are now
  refused **at** save (422), not reported after it, and a refused create leaves
  no capability behind. Post-save warnings remain the rule for everything else.

**Verified by** criterion 17's first two clauses, and `tcw capabilities check`
still exiting 0 on this repo (criterion 16).

### 6. Documentation sync

One pass over the finished diff. Predictions in the block below; if a trigger
fires differently against the real diff, follow the diff.

## Documentation Sync

All four declared entries evaluated (`tcw work docs`).

### `docs/changelogs/upcoming.md` — `[Any-Code-Change]` **fires**

Under **Fixed**: `tcw capabilities set` and the web capability editor now
resolve every reference-bearing field before writing — `Subject`, `Feature`,
`Superseded by`, `Blocked by`, `Roles`, `When` — refusing a dangling, ambiguous
or wrong-kind ref with the same message `tcw capabilities check` reports, via a
single shared renderer. `POST /api/capabilities` is now one write, so a rejected
create leaves no capability behind (this also fixes the pre-existing partial
write on an unknown field or an invalid Status). `FsCapabilitiesStore.check()`
called without a taxonomy now resolves against the node's own taxonomy instead
of skipping `Subject`/`Feature`. Under **Changed**: `CapabilitiesStore.add`
takes an optional `fields`.

### `docs/release-notes/upcoming.md` — `[Public-API]` **fires**

Plain language, no module names. Two points: (1) setting a capability field that
points at something that does not exist is now refused when you set it, instead
of being reported later by `tcw capabilities check` — this is a behavior change,
and a script that set fields loosely and checked at the end will now stop at the
first bad one; it covers six fields, not just `Subject` and `Feature`. (2)
Creating a capability through the web app with a bad field no longer leaves a
half-created capability behind.

### `README.md` — `[Public-API]` **fires**

`README.md:519` and `:531` present `check` as the thing that resolves
`Subject`/`Feature` pointers. Say `set` resolves them too and refuses one that
does not resolve. No new command or flag, so the command tables are untouched.

### `skills/tcw-capabilities/SKILL.md` — `[Skill-Driven-Component]` **fires**

`SKILL.md:44-47` says `tcw capabilities check` verifies that `Feature` resolves
to a taxonomy entry of kind `Feature`. Say `set` verifies it as well and refuses
otherwise; name all six ref fields; and state the ordering consequence — the
taxonomy Feature must exist *before* the capability that names it, and a
`roles/…` capability before the capability that lists it. The quick-reference
rows at `:106-107` get the same guardrail in one clause.

`skills/tcw-taxonomy/SKILL.md` — **does not fire.** No taxonomy CLI surface,
model, lifecycle or guardrail changes; `FsTaxonomyStore` is not edited.

`skills/tcw-work/SKILL.md` — **does not fire.** The `complete` reconciliation
route (`tcw capabilities set <path> --status Omitted`) keeps working unchanged,
which criterion 11 pins.

## Verification

Beyond `pytest`:

- **The by-hand `tcw serve` runs, which the suite cannot fully stand in for.**
  Criterion 9's real assertion is about a folder that must *not* exist, and the
  spec's Reproduction recorded that defect at the shell, so verify it there.
  In a throwaway repo, with `tcw serve` running:
    1. `POST /api/capabilities` with a dangling `Feature` → 422, then
       `ls docs/capabilities/` and `git status --porcelain docs/capabilities/`
       both show nothing new. Repeat for `NotAField` and for
       `status: "InvalidStatus"` — the spec's own reproduction used the
       unknown-field case, so that one is the direct before/after.
    2. `POST` with a *valid* field → 201, field present in the response and in
       `meta.yaml`.
    3. `PATCH /api/capabilities/web%2Fediting` with a dangling `Subject` → 422
       and `meta.yaml` byte-identical (`cmp` it against a copy taken first).
  Paste the actual output into `outcome.md`, before and after.
- **Criterion 7's byte-comparison, run rather than eyeballed.** For each bad
  value: write it into `meta.yaml`, capture `check`'s line, strip
  `web/editing: `; capture the `set` refusal, strip `tcw capabilities set: `;
  `diff <(…) <(…)`. For the multi-problem case, split the refusal on `"; "` and
  compare as sets. The table above is the expected text.
- **Criterion 16 on this repo**: `tcw capabilities check` → `capabilities OK`
  and `tcw validate` → `validate OK`. Weak evidence on its own — this repo's
  `docs/capabilities/` is already clean, which is what made "no migration
  needed" true in the spec — so the throwaway-repo criteria carry the weight.
- **Re-run the caller walk at `implement`.** Two items are editing `fs.py`
  concurrently and one of them landed mid-plan. Before Task 1, re-run
  `grep -rn --include=*.py "_check_globals\|_check_subject\|_check_feature" tcw/ tests/`
  and confirm it still returns only the definitions and `check`.
- **Not verifiable here, stated instead:** whether any user script sets
  `Roles`/`When`/`Blocked by` loosely and relies on checking at the end. The
  spec accepts the break; nothing in the suite can prove nobody depends on it,
  which is why it is a release-note line rather than a silent fix.

## Notes

### `FsCapabilitiesStore.add` is edited by three items — the merged shape

This item implements **third** of four. Both items ahead touch `add`'s
neighborhood, and each is easy to drop while rebasing. The merged method, with
each item's contribution marked:

```python
def add(self, identifier, name=None, status="Missing", body="", fields=None):   # ← THIS ITEM
    path = _safe_store_id(identifier, "path")
    if status not in CAP_STATUSES:
        raise ValueError(f"invalid Status '{status}' "
                         f"(choose: {', '.join(sorted(CAP_STATUSES))})")
    d = self.root / path
    if not self._within_store(d):                    # ← SYMLINK ITEM
        raise ValueError(...)                        #   (its wording, not this item's)
    if d.exists():
        raise ValueError(f"capability already exists: {path}")
    norm = self._validate_fields(fields or {})       # ← THIS ITEM
    display = name or path.rsplit("/", 1)[-1].replace("-", " ").title()
    meta = {"id": _mint_cap_id(), "name": display, "Status": status}
    meta.update({k: v for k, v in norm.items() if v is not None})   # ← THIS ITEM
    self._write_node(d, meta, body)                  # ← NON-GIT ITEM's guard lives INSIDE this
    return self._capability(path)
```

**Correcting one assumption in the sequencing brief:** the non-git item does
**not** add a guard to `add` itself. Its spec's Tier 2 table puts
`_require_repository()` inside `FsTreeStore._write_node`, and lists capabilities
`add` as *covered by* that — so `add` gains no repository line of its own, and
this item adds no mutation ahead of `_write_node` that would escape it. Two
items edit `add` directly, not three.

**Placement is not arbitrary.** `_validate_fields` goes *after* `d.exists()`
because it may open a taxonomy store — the cheap string and stat refusals should
not pay for that. It goes *before* `_write_node` because that is the whole
point. The symlink item's containment check stays ahead of both: it is a
`resolve()` on a path, cheaper than a store open, and it decides whether `d` is
even addressable.

### The other two items, and what they touch that this one also touches

| Item | Touches | Overlap with this item |
| --- | --- | --- |
| non-git writes (`c0b340e`, **active, partially landed**) | `require_repository` + `_write_git_root`/`_require_repository` on `FsTreeStore` have landed; the ~19 call sites have **not**, including `set`, `update_capability`, `_write_node`, `_write_meta` | `set` and `update_capability` each gain one guard line beside their existing `_validate_fields` call. This item edits neither method's body, so the guard lands cleanly either way. |
| symlink containment | `FsTreeStore._within_store`; guards in `FsCapabilitiesStore.get_local`, `add`, `_all_meta_dirs`, `_write_target`, `_validation_resources` | `add` (above). Its `_write_target` guard is upstream of both `set` and `update_capability`, which this item does not edit. |
| **this item** | `_ref_problems`, `_taxonomy`, `check`, `_validate_fields`, `_check_globals`/`_check_subject`/`_check_feature`, `add`, plus `base.py` and `serve/__init__.py` | — |

Function-level overlap is `add` only. Everything else is disjoint, so a rebase
conflict is textual, not semantic.

Note also that the non-git item's guard in `set` and this item's ref refusal are
both pre-write refusals, and their relative order decides which message a user
outside a git repo sees first. As written they land next to each other with
`_validate_fields` first, so a bad ref is reported ahead of "not a repository".
Acceptable — the ref error is the more actionable of the two — and if the other
item's author prefers the opposite it is a one-line move with no test impact.

### Measurement provenance

The two simulations backing Tasks 2 and 3 monkeypatch `FsCapabilitiesStore`
from a pytest plugin on `PYTHONPATH`; **neither edits `tcw/`**. They are in the
scratchpad (`simfallback.py`, `simwrite.py`) and are disposable — rebuild them
from the task bodies rather than assuming they survive. Their value is that
"exactly one existing test breaks" is a number this plan measured, not a
prediction it made.

### Blockers — to be recorded before `start`, not by this plan

The stage asks for dependencies as blockers rather than prose, and "implements
third" is a real dependency: the merged `add` above only works if this item goes
last of the three that touch it. The two commands:

```
tcw work edit 2026-07-30-validate-capability-subject-and-feature-refs-at-write-time \
  --blocked-by 2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository
tcw work edit 2026-07-30-validate-capability-subject-and-feature-refs-at-write-time \
  --blocked-by 2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically
```

**Deliberately not run from this stage.** `tcw work edit` writes through
`FsWorkStore`, and the non-git item is committing into `tcw/store/fs.py`'s write
paths as this is written (three commits landed during the plan). Driving a store
write through a half-modified adapter is the one avoidable risk here, so the
commands are handed over rather than executed — matching this repo's standing
rule about not driving the CLI while `tcw/` is being modified.

The dependency is an ordering constraint, not a compile-time one: this item's
code and tests pass against the tree with or without the other two. What depends
on the order is the merged `add`, and a dropped guard there is silent, which is
why it is both blocked and documented.
