# Skill layer + capabilities process (work Spec 3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the judgment layer that drives `tcw` — two Claude Code skills (`tcw-work`, `tcw-capabilities`) — plus the one tool affordance the lifecycle handshake needs (`tcw capabilities set`).

**Architecture:** `set` is a mechanism (a field write on a capability node), realized by the FS adapter as a line-based in-place markdown edit scoped to one `## <heading>` block — the parser discards line positions and there's no serializer, so the editor locates the block itself. The two skills carry judgment only; they orchestrate existing `tcw` commands and never reimplement tool logic. An integration test captures the worked dry-run so the skills are authored against a proven command sequence.

**Tech Stack:** Python 3 (stdlib `re`, `argparse`, `pathlib`, `subprocess`) + PyYAML; pytest over `tmp_path` git repos; Claude Code `SKILL.md` (markdown + YAML frontmatter), authored via `superpowers:writing-skills`.

## Global Constraints

- **Mechanism vs. judgment:** only `set` is tool code; everything else is markdown skills. Skills name `tcw …` commands, never duplicate the locked vocabulary or store internals.
- **`set` is line-based and heading-scoped:** locate the `## <name>` block whose `heading_slug` matches; update-or-insert `**K:** V` at the **end of the metadata run** (consecutive `_FIELD_RE` lines after the heading), never keying off a blank line; require `#heading` when the file holds >1 capability.
- **`set` validation:** field keys ∈ `CAP_FIELDS`; `Status` value ∈ `CAP_STATUSES`. Other field *values* and status business-semantics are `check`'s job, not `set`'s.
- **Stage-only**, like `add`/`taxonomy add` — no `--commit` on `set`.
- **`"set"` must be added to `capabilities/cli.py`'s `SUBCOMMANDS`** or the top-level `show`-sugar normalizer rewrites it to `show set …`.
- Follow existing idioms: `_store()`, `_stdin_body()`, `_resolve_file`, `parse_capability_file`, `_FIELD_RE`, `heading_slug`, `_IDENT_RE`, `_disk_id`.

---

## File Structure

- `tcw/store/base.py` — **modify**: add abstract `CapabilitiesStore.set(identifier, fields) -> Capability`.
- `tcw/store/fs.py` — **modify**: add module fn `_set_inline_fields` + `FsCapabilitiesStore.set`.
- `tcw/capabilities/cli.py` — **modify**: `"set"` → `SUBCOMMANDS`; `_set` handler; `set` subparser.
- `tests/test_capabilities.py` — **modify**: `set` unit tests.
- `tests/test_skill_flow.py` — **create**: the lifecycle-flow integration test (the worked dry-run as pytest).
- `skills/tcw-work/SKILL.md` — **create**.
- `skills/tcw-capabilities/SKILL.md` — **create**.
- Docs — **modify**: `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, `docs/plan/phase-6-beyond.md`, `docs/plan/phase-3-capabilities.md`, `docs/plan/phase-5-work.md`.

---

## Task 1: `tcw capabilities set` (the ledger-flip mechanism)

**Files:**
- Modify: `tcw/store/base.py` (`CapabilitiesStore`, after `add`/`remove`)
- Modify: `tcw/store/fs.py` (module fn near `parse_capability_file`; method on `FsCapabilitiesStore`)
- Modify: `tcw/capabilities/cli.py`
- Test: `tests/test_capabilities.py`

**Interfaces:**
- Produces: `CapabilitiesStore.set(identifier: str, fields: dict[str, str]) -> Capability`; `FsCapabilitiesStore.set`; module fn `_set_inline_fields(text: str, target_slug: str, fields: dict[str, str]) -> str`; CLI `tcw capabilities set <id> [--status S] [--field "K=V"]...`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_capabilities.py`)

```python
# ── set (the ledger-flip affordance) ──────────────────────────────────────────

_MULTI = (
    "# Auth — capabilities\n\n"
    "## Sign in with Google\n**Status:** Missing\n\nUser clicks the Google button.\n\n"
    "## Sign out\n**Status:** Supported\n**Priority:** P1\n\nUser ends the session.\n"
)


def test_set_updates_status_preserving_siblings(tmp_path):
    root = node(tmp_path)
    write_cap(root, "auth.md", _MULTI)
    st = FsCapabilitiesStore.open(root)
    cap = st.set("auth#sign-in-with-google", {"Status": "Supported"})
    assert cap.status == "Supported"
    # sibling block untouched
    sign_out = next(c for c in st.get("auth").capabilities if c.name == "Sign out")
    assert sign_out.status == "Supported" and sign_out.fields.get("Priority") == "P1"
    # body preserved
    assert "User clicks the Google button." in (root / "docs/capabilities/auth.md").read_text()


def test_set_inserts_new_field_into_metadata_run(tmp_path):
    root = node(tmp_path)
    write_cap(root, "auth.md", _MULTI)
    st = FsCapabilitiesStore.open(root)
    st.set("auth#sign-in-with-google", {"Planning doc": "2026-01-01-google-sso"})
    cap = next(c for c in st.get("auth").capabilities if c.name == "Sign in with Google")
    assert cap.fields.get("Planning doc") == "2026-01-01-google-sso"   # re-parsed as a field, not body
    assert cap.body.startswith("User clicks")                          # body intact


def test_set_requires_heading_for_multicap(tmp_path):
    root = node(tmp_path)
    write_cap(root, "auth.md", _MULTI)
    with pytest.raises(RefError):
        FsCapabilitiesStore.open(root).set("auth", {"Status": "Supported"})


def test_set_bare_id_on_single_cap(tmp_path):
    root = node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")            # single-cap file
    cap = st.set("routes/login", {"Status": "Supported"})
    assert cap.status == "Supported"


def test_set_rejects_invalid_status_and_unknown_field(tmp_path):
    root = node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    with pytest.raises(ValueError):
        st.set("routes/login", {"Status": "Broken"})       # not in CAP_STATUSES
    with pytest.raises(ValueError):
        st.set("routes/login", {"Frobnicate": "x"})        # not in CAP_FIELDS


def test_set_dangling_id_errors(tmp_path):
    root = node(tmp_path)
    with pytest.raises((ValueError, RefError)):
        FsCapabilitiesStore.open(root).set("routes/nope", {"Status": "Supported"})
```

Add `RefError` to the test imports: `from tcw.store.base import RefError` (alongside the existing imports), and `from tcw.store.fs import FsCapabilitiesStore, heading_slug`.

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_capabilities.py -k set -v`
Expected: FAIL — `AttributeError: 'FsCapabilitiesStore' object has no attribute 'set'`.

- [ ] **Step 3: Add the abstract method to `CapabilitiesStore` (`tcw/store/base.py`)**

After the `remove` abstractmethod in `CapabilitiesStore`:

```python
    @abstractmethod
    def set(self, identifier: str, fields: dict[str, str]) -> Capability:
        """Update/insert inline metadata fields on the resolved capability;
        return it. Keys must be in CAP_FIELDS; a Status value must be in
        CAP_STATUSES. Other field-value semantics are `check`'s job."""
```

- [ ] **Step 4: Add the editor + method to `tcw/store/fs.py`**

Module-level, near `parse_capability_file`:

```python
def _set_inline_fields(text: str, target_slug: str, fields: dict[str, str]) -> str:
    """Update-or-insert `**K:** V` lines in the metadata run of the `## <name>`
    block whose heading_slug == target_slug. The run is the consecutive
    `_FIELD_RE` lines right after the heading; inserts land at its end (or right
    after the heading when empty), never keyed off a blank line — so the body and
    sibling blocks are untouched."""
    lines = text.splitlines()
    hi = next((i for i, ln in enumerate(lines)
               if ln.startswith("## ") and heading_slug(ln[3:].strip()) == target_slug), None)
    if hi is None:
        raise RefError(f"heading '#{target_slug}' not found")
    run_end, existing = hi + 1, {}
    while run_end < len(lines):
        fm = _FIELD_RE.match(lines[run_end].strip())
        if not fm:
            break
        existing[fm.group(1).strip()] = run_end
        run_end += 1
    remaining = dict(fields)
    for k in list(remaining):
        if k in existing:
            lines[existing[k]] = f"**{k}:** {remaining.pop(k)}"
    lines[run_end:run_end] = [f"**{k}:** {v}" for k, v in remaining.items()]
    out = "\n".join(lines)
    return out + "\n" if text.endswith("\n") else out
```

On `FsCapabilitiesStore`, after `remove`:

```python
    def set(self, identifier: str, fields: dict[str, str]) -> Capability:
        for k, v in fields.items():
            if k not in CAP_FIELDS:
                raise ValueError(f"unknown field '{k}' (not in the locked vocabulary)")
            if k == "Status" and v not in CAP_STATUSES:
                raise ValueError(f"invalid Status '{v}' "
                                 f"(choose: {', '.join(sorted(CAP_STATUSES))})")
        m = _IDENT_RE.match(identifier)
        if not m:
            raise RefError(f"malformed identifier: {identifier}")
        fp = self._resolve_file(m.group("path"), m.group("state"))
        if fp is None:
            raise ValueError(f"no such capability: {identifier}")
        text = fp.read_text(encoding="utf-8")
        cf = parse_capability_file(self._disk_id(fp), text)
        heading = m.group("heading")
        if heading:
            match = next((c for c in cf.capabilities if c.heading_slug == heading), None)
            if match is None:
                raise RefError(f"no heading '#{heading}' in {self._disk_id(fp)}")
        elif len(cf.capabilities) != 1:
            raise RefError(f"{identifier} resolves to {len(cf.capabilities)} "
                           f"capabilities; specify #heading")
        else:
            match = cf.capabilities[0]
        new_text = _set_inline_fields(text, match.heading_slug, fields)
        fp.write_text(new_text, encoding="utf-8")
        self._stage(fp)
        updated = parse_capability_file(self._disk_id(fp), new_text)
        return next(c for c in updated.capabilities if c.heading_slug == match.heading_slug)
```

(`CAP_FIELDS`, `CAP_STATUSES`, `Capability`, `RefError`, `_IDENT_RE`, `_FIELD_RE`, `parse_capability_file`, `heading_slug` are already in `fs.py` scope.)

- [ ] **Step 5: Run the store tests to verify they pass**

Run: `python -m pytest tests/test_capabilities.py -k set -v`
Expected: PASS (6 tests).

- [ ] **Step 6: Wire the CLI (`tcw/capabilities/cli.py`)**

Change line 10 to include `set`:

```python
SUBCOMMANDS = {"list", "show", "add", "search", "check", "set"}
```

Add the handler (after `_add`):

```python
def _set(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    fields: dict[str, str] = {}
    if args.status:
        fields["Status"] = args.status
    for kv in (args.field or []):
        if "=" not in kv:
            print(f"tcw capabilities set: --field must be K=V: {kv}", file=sys.stderr)
            return 1
        k, v = kv.split("=", 1)
        fields[k.strip()] = v.strip()
    if not fields:
        print("tcw capabilities set: need --status or at least one --field", file=sys.stderr)
        return 1
    try:
        cap = st.set(args.id, fields)
    except (ValueError, RefError) as e:
        print(f"tcw capabilities set: {e}", file=sys.stderr)
        return 1
    print(f"Set {cap.ref}")
    return 0
```

Register the subparser in `add_subparser` (after the `add` parser block):

```python
    pset = g.add_parser("set", help="update a capability's status/fields in place")
    pset.add_argument("id")
    pset.add_argument("--status", help="shorthand for --field Status=<S>")
    pset.add_argument("--field", action="append", metavar="K=V",
                      help="set a metadata field (repeatable)")
    pset.set_defaults(func=_set)
```

- [ ] **Step 7: Write the CLI normalizer regression test** (append to `tests/test_capabilities.py`)

```python
def test_cli_set_not_rewritten_to_show(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    from tcw.cli import main
    FsCapabilitiesStore.open(root).add("routes/login", name="Sign in")
    assert main(["capabilities", "set", "routes/login", "--status", "Supported"]) == 0
    assert "Set" in capsys.readouterr().out                    # ran `set`, not `show`
    assert FsCapabilitiesStore.open(root).get("routes/login").capabilities[0].status == "Supported"
```

- [ ] **Step 8: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (existing + 7 new).

- [ ] **Step 9: Commit**

```bash
git add tcw/store/base.py tcw/store/fs.py tcw/capabilities/cli.py tests/test_capabilities.py
git commit -m "feat(capabilities): tcw capabilities set — in-place inline-field edit"
```

---

## Task 2: Lifecycle-flow integration test (the worked dry-run, as pytest)

Proves the exact command sequence the skills prescribe, so the skills are authored against a green flow and drift is caught in CI.

**Files:**
- Create: `tests/test_skill_flow.py`

**Interfaces:**
- Consumes: `tcw.cli.main`; the `set` affordance (Task 1); `tcw work` (Spec 1/2).

- [ ] **Step 1: Write the integration test**

```python
"""The Spec 3 lifecycle handshake end-to-end, via the CLI — the worked dry-run
the tcw-work / tcw-capabilities skills prescribe, captured as a regression."""

import subprocess
from pathlib import Path

from tcw.store.fs import FsCapabilitiesStore, FsWorkStore, init


def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work", "capabilities"], root)
    return root


def test_product_first_lifecycle_handshake(tmp_path, monkeypatch, capsys):
    root = repo(tmp_path)
    monkeypatch.chdir(root)
    from tcw.cli import main

    # new → backlog
    assert main(["work", "new", "Add CSV export"]) == 0
    slug = capsys.readouterr().out.strip()
    assert (root / "docs/work/backlog" / slug).is_dir()

    # planning gate: declare the capability Missing + the Planning-doc back-pointer
    assert main(["capabilities", "add", "routes/csv-export", "Export CSV", "--status", "Missing"]) == 0
    assert main(["capabilities", "set", "routes/csv-export", "--field", f"Planning doc={slug}"]) == 0
    cap = FsCapabilitiesStore.open(root).get("routes/csv-export").capabilities[0]
    assert cap.status == "Missing" and cap.fields.get("Planning doc") == slug

    # start → active
    capsys.readouterr()
    assert main(["work", "start", slug]) == 0
    assert (root / "docs/work/active" / slug).is_dir()

    # complete: flip the ledger, then close the item
    assert main(["capabilities", "set", "routes/csv-export", "--status", "Supported"]) == 0
    assert FsCapabilitiesStore.open(root).get("routes/csv-export").capabilities[0].status == "Supported"
    capsys.readouterr()
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    assert (root / "docs/work/completed" / slug).is_dir()
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/test_skill_flow.py -v`
Expected: PASS (1 test).

- [ ] **Step 3: Commit**

```bash
git add tests/test_skill_flow.py
git commit -m "test(work): lifecycle handshake integration flow (Spec 3 dry-run)"
```

---

## Task 3: `skills/tcw-work/SKILL.md`

**Files:**
- Create: `skills/tcw-work/SKILL.md`

- [ ] **Step 1: Author the skill** (invoke `superpowers:writing-skills` to refine wording, but the target content is:)

```markdown
---
name: tcw-work
description: Use when starting, continuing, triaging, or decomposing tcw work items — processing a docs/work/inbox, planning a change along the product/technical/meta axes, running the start/complete lifecycle, resuming an active item across sessions, or splitting an item into a cross-node epic. Drives the `tcw work` CLI; does not reimplement it.
---

# Driving `tcw work`

`tcw work` is the change-tracking state machine (inbox → backlog → active → completed; blocked is a derived overlay). This skill is the *judgment* on top of it. It names `tcw …` commands; it never edits `docs/work/` by hand when a command exists.

## Recursive process-inbox

`docs/work/inbox/` holds raw request docs — including `delegate`/`escalate` drops that carry `---\nfrom: …\n[initiative: …]\n---` front-matter. (Inbox holds raw `.md` docs only; `tcw work new` creates a **backlog** folder, never an inbox folder.)

For each doc:
1. Read it; extract `initiative:` / `from:` from the front-matter.
2. `tcw work new "<title>" [--initiative <slug>]`, piping the **body with the front-matter stripped** as stdin (`tcw work new` reads stdin for the body but does not parse front-matter).
3. `git rm` the source doc — it has been ingested into the new backlog item.

Across child nodes (`tcw work nodes`), an orchestrator triages **its own** inbox and *delegates* down (`tcw work delegate <child> …`); it never writes into a child's tracking tree directly.

## Three-axis / product-first planning

Fill the item's `content.md` under `## Product changes` / `## Technical changes` / `## Meta changes` (which sections are non-empty *is* the classification). **Product-first:** if there is any product delta, run the `tcw-capabilities` skill's planning gate *before* writing the technical plan.

Place the spec and implementation plan inside the work-item folder (`spec.md`, `plan.md`).

## The lifecycle handshake

- **`tcw work new`** — declare the delta; for a product delta, record `Missing` capabilities (see `tcw-capabilities`).
- **`tcw work start <slug>`** — begin; add `--worktree` to isolate the item's code in its own git worktree + branch (transitions stay on trunk; edits ride the work branch and merge back).
- **during `active`** — on any capability change, run contradiction-detection (see `tcw-capabilities`).
- **`tcw work complete <slug> --resolution <done|wontfix|duplicate|superseded> --confirm`** — the final step. Reconcile capabilities first (the `tcw-capabilities` ledger flip), since the DoD "capabilities reconciled" item is acknowledged here. `--force` overrides unresolved blockers.

## Resume (across sessions)

`tcw work list --status active` → `tcw work show <slug>` → read the item's `content.md` / `spec.md` / `plan.md`. For an epic, `tcw work reconcile <slug>` to refresh the rollup before choosing the next action.

## Decompose

Turn a large item into a cross-node initiative:
1. `tcw work new --epic` in the orchestrator node (the epic).
2. `tcw work delegate <child> "<slice title>"` for each child node, or have each child run process-inbox and `tcw work new --initiative <epic-slug>`.
3. `tcw work reconcile <epic-slug>` to consolidate progress into the epic's rollup.
```

- [ ] **Step 2: Verify structure**

Run: `python -c "import yaml,sys; d=open('skills/tcw-work/SKILL.md').read(); fm=d.split('---')[1]; m=yaml.safe_load(fm); assert m.get('name')=='tcw-work' and 'Use when' in m['description']; print('frontmatter OK')"`
Expected: `frontmatter OK`.

Then confirm every `tcw` command the skill names exists (no invented commands):

Run: `grep -oE 'tcw (work|capabilities) [a-z]+' skills/tcw-work/SKILL.md | sort -u`
Expected: only commands present in `tcw work --help` / `tcw capabilities --help` (`work new/start/complete/list/show/reconcile/delegate/nodes`, `capabilities …`). Eyeball the list against `tcw work --help`.

- [ ] **Step 3: Commit**

```bash
git add skills/tcw-work/SKILL.md
git commit -m "feat(skills): tcw-work driving skill (Spec 3)"
```

---

## Task 4: `skills/tcw-capabilities/SKILL.md`

**Files:**
- Create: `skills/tcw-capabilities/SKILL.md`

- [ ] **Step 1: Author the skill** (invoke `superpowers:writing-skills`; target content:)

```markdown
---
name: tcw-capabilities
description: Use when planning or completing a tcw work item that has a product delta, or coordinating capability wording across repos — running the `## Capability changes` planning gate, detecting contradictions with the standing ledger, flipping a capability's status at completion, or relaying canonical product-layer wording. Drives `tcw capabilities`; the work axis is `tcw-work`.
---

# The capabilities process

The standing ledger (`docs/capabilities/`) describes *what a user can currently do*. This skill is the process that keeps it true as work lands. It drives `tcw capabilities` (read with `list`/`show`/`search`, validate with `check`, write status/fields with `set`); it never hand-edits capability markdown when `set` applies.

## The `## Capability changes` planning gate (at `tcw work new`)

When a work item has a product delta, name each new / changed / removed capability and record it:

- **New capability:** `tcw capabilities add <namespace/path> "<Capability name>" --status Missing` (seeds `**Status:** Missing`; the heading slug derives from the name), then `tcw capabilities set <namespace/path> --field "Planning doc=<work-slug>"` (the capability→work forward pointer; a freshly-added file is single-capability so the bare id resolves).
- **Changed/removed existing capability:** record it in the work item's `capabilities.yaml` (the work→capability back-pointer).

## Contradiction-detection (at the moment of change)

Before recording or altering a capability, check it against the standing ledger: `tcw capabilities search <term>` / `tcw capabilities show <id>` for an existing capability the change would contradict (a new capability that conflicts with a `Supported` one; a status that disagrees with reality). Run `tcw capabilities check` (non-zero ⇒ structural problems to fix first). Whether two capabilities semantically contradict is *judgment* — surface candidates to the human; never silently overwrite.

## The ledger flip (at `tcw work complete`)

As the item's final pre-freeze step, apply each declared delta so the ledger describes the present:

- `tcw capabilities set <id>#<heading> --status Supported` (Missing → Supported)
- scope/body edits; `--status Omitted` (Supported → Omitted)

At completion these are long-lived multi-capability files, so include the `#heading`. Flips are idempotent (re-running `set` to the same status is a no-op). This satisfies the work DoD "capabilities reconciled" item by convention — the tool acknowledges it, it does not verify it.

## Product-layer coordination (orchestrator-relay)

A per-node agent does **not** read the orchestrator's `docs/capabilities/`. To get canonical product-layer wording it escalates over the inbox channel: `tcw work escalate "capability wording: <name>"`. The orchestrator replies (delegates back) with canonical wording and flips the **product-layer** entry when the **epic** completes; a **task** completing flips the **leaf** entry.

The protocol is **non-blocking**: never wait on a reply. If canonical wording isn't available when needed, fall back to in-repo evidence and mark the entry `TODO: confirm wording`.
```

- [ ] **Step 2: Verify structure**

Run: `python -c "import yaml; m=yaml.safe_load(open('skills/tcw-capabilities/SKILL.md').read().split('---')[1]); assert m['name']=='tcw-capabilities' and 'Use when' in m['description']; print('frontmatter OK')"`
Expected: `frontmatter OK`.

Confirm cross-reference to `tcw-work` resolves (the skill names the other skill) and commands exist:

Run: `grep -oE 'tcw capabilities [a-z]+' skills/tcw-capabilities/SKILL.md | sort -u`
Expected: only `add`, `check`, `set`, `show`, `search` (all real).

- [ ] **Step 3: Commit**

```bash
git add skills/tcw-capabilities/SKILL.md
git commit -m "feat(skills): tcw-capabilities process skill (Spec 3)"
```

---

## Task 5: Documentation sync

**Files:**
- Modify: `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, `docs/plan/phase-6-beyond.md`, `docs/plan/phase-3-capabilities.md`, `docs/plan/phase-5-work.md`
- Run the `skill-cefailures:documentation-sync` skill to confirm coverage.

- [ ] **Step 1: README** — in the `tcw capabilities` section, document `tcw capabilities set <id> [--status S] [--field "K=V"]` (update a capability's status/fields in place; stage-only). Add a short **"Skills"** section: `skills/tcw-work` and `skills/tcw-capabilities` are the judgment layer that drives the tools — the recursive process-inbox, the product-first lifecycle handshake, and the capabilities ledger flip.

- [ ] **Step 2: `docs/release-notes/upcoming.md`** — plain language: "A command to update a capability's status and fields (`tcw capabilities set`), plus two skills that drive the work and capability lifecycle end-to-end (triage an inbox, plan product-first, flip the capability ledger on completion, coordinate wording across repos)."

- [ ] **Step 3: `docs/changelogs/upcoming.md`** — Added: `CapabilitiesStore.set` + `FsCapabilitiesStore.set` + `_set_inline_fields` + `tcw capabilities set` (with the `SUBCOMMANDS` normalizer note); `skills/tcw-work` and `skills/tcw-capabilities`; `tests/test_skill_flow.py`. Include the commit-hash range (`git rev-parse --short HEAD` before/after).

- [ ] **Step 4: `docs/plan/phase-6-beyond.md`** — mark "Skill layer + capabilities process (work Spec 3)" built; link this work folder.

- [ ] **Step 5: `docs/plan/phase-3-capabilities.md`** — B.2: add `set` to the command surface; note A.9's product-layer coordination protocol is now realized as the `tcw-capabilities` skill (Spec 3).

- [ ] **Step 6: `docs/plan/phase-5-work.md`** — Part C #3: mark Spec 3 built.

- [ ] **Step 7: Invoke the documentation-sync skill** to verify coverage, then commit:

```bash
git add README.md docs/
git commit -m "docs: tcw capabilities set + the tcw-work/tcw-capabilities skills (Spec 3)"
```

---

## Self-Review (done while writing)

- **Spec coverage:** §3 `set` → Task 1; §5 set tests → Task 1 (incl. the `#heading`/multi-cap, invalid-status, unknown-field, dangling, normalizer cases); §5 dry-run → Task 2 (as a durable integration test, exceeding the spec's manual walkthrough); §4.1 `tcw-work` → Task 3; §4.2 `tcw-capabilities` → Task 4; §6 docs → Task 5.
- **Placeholder scan:** every code/test/skill step has real content; the only literal `TODO:` is the protocol's `TODO: confirm wording` marker (intended content, not a plan gap).
- **Type consistency:** `set(identifier, fields) -> Capability` and `_set_inline_fields(text, target_slug, fields) -> str` are used identically across Task 1 and the tests; the CLI maps `--status`→`Status=` and requires ≥1 field, matching §3.3.
- **`SUBCOMMANDS` guard** (the review BLOCKER) is Step 6 + the Task 1 normalizer test.

## Execution note

Run `tcw work start 2026-06-19-skill-layer-capabilities-process-work-spec-3` as the first implementation commit (per CLAUDE.md), then proceed task-by-task. Offer a version cut + complete the work item at the end (as with Spec 2).
