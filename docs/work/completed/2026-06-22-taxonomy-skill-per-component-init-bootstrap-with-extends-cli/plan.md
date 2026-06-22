# Taxonomy skill + per-component init bootstrap (extends CLI) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the missing `tcw-taxonomy` skill, a per-component agent-driven bootstrap (`/tcw-taxonomy-init`, `/tcw-capabilities-init`), and a canonical `tcw taxonomy extends add|rm` CLI for declaring taxonomy inheritance.

**Architecture:** Most of the feature is skill/command markdown orchestrating existing `tcw` commands. The only executable logic is the `extends` write path: two new abstract `TaxonomyStore` methods realized by `FsTaxonomyStore` (read/write the `extends:` map in `docs/taxonomy/config.yaml`), surfaced as a nested CLI subparser.

**Tech Stack:** Python 3 (argparse, stdlib), pytest over `tmp_path` git repos, Markdown skills/commands.

## Global Constraints

- **Storage-abstracted (litmus test):** `extends_add`/`extends_remove` go on the `TaxonomyStore` ABC with an opaque `ref: str`; only `FsTaxonomyStore` knows it's a repo path written to `config.yaml`. Never put the FS layout in the ABC or the skill prose.
- **Never hand-edit store content when a command exists.** `extends` goes through the CLI; term/capability markdown through `add`/`set`.
- **Spec + plan live in the work-item folder** and are committed as the `tcw work start` transition (the first implementation commit).
- **No version cut.** Five-file version string stays at the current value.
- **Skill authoring:** thin router; always-relevant judgment inline, rare sub-procedures in `docs/*.md` behind a clear gate (mirror `tcw-work`/`tcw-capabilities`).
- Slug for this item: `2026-06-22-taxonomy-skill-per-component-init-bootstrap-with-extends-cli`.

---

### Task 1: Start the item + declare capability-ledger deltas

**Files:**
- Move (CLI): item folder `docs/work/backlog/<slug>/` → `docs/work/active/<slug>/`
- Create: `docs/capabilities/taxonomy/bootstrap-the-taxonomy.md` (via `tcw capabilities add`)
- Create: `docs/capabilities/capabilities/bootstrap-the-capabilities.md` (via `tcw capabilities add`)
- Create: `docs/work/active/<slug>/capabilities.yaml`

- [ ] **Step 1: Commit the start transition (carries spec.md + plan.md)**

```bash
git add docs/work/backlog/2026-06-22-taxonomy-skill-per-component-init-bootstrap-with-extends-cli/spec.md \
        docs/work/backlog/2026-06-22-taxonomy-skill-per-component-init-bootstrap-with-extends-cli/plan.md
tcw work start 2026-06-22-taxonomy-skill-per-component-init-bootstrap-with-extends-cli
# `start` moves the folder backlog→active and stages the rename; re-add the moved planning docs:
git add docs/work/active/2026-06-22-taxonomy-skill-per-component-init-bootstrap-with-extends-cli/
git commit -m "tcw work: start taxonomy-skill-per-component-init-bootstrap-with-extends-cli"
```

- [ ] **Step 2: Declare the two new (Missing) capabilities with the planning back-pointer**

```bash
SLUG=2026-06-22-taxonomy-skill-per-component-init-bootstrap-with-extends-cli
printf 'As a user, I run `/tcw-taxonomy-init` so the agent deep-dives my codebase, proposes domain terms, refines them with me, and writes the first taxonomy draft.\n' \
  | tcw capabilities add taxonomy/bootstrap-the-taxonomy "Bootstrap the taxonomy" --status Missing
tcw capabilities set taxonomy/bootstrap-the-taxonomy --field "Planning doc=$SLUG"

printf 'As a user, I run `/tcw-capabilities-init` so the agent deep-dives my codebase, proposes user capabilities, refines them with me, and writes the first capabilities draft.\n' \
  | tcw capabilities add capabilities/bootstrap-the-capabilities "Bootstrap the capabilities" --status Missing
tcw capabilities set capabilities/bootstrap-the-capabilities --field "Planning doc=$SLUG"
```

- [ ] **Step 3: Record the work→capability back-pointers**

Create `docs/work/active/<slug>/capabilities.yaml`:

```yaml
# Capability deltas this work item lands (work→capability back-pointers).
new:
  - taxonomy#bootstrap-the-taxonomy          # "Bootstrap the taxonomy" — Missing → Supported at complete
  - capabilities#bootstrap-the-capabilities  # "Bootstrap the capabilities" — Missing → Supported at complete
changed:
  - taxonomy#federate-shared-vocabulary      # now declarable via `tcw taxonomy extends add` (stays Partial)
```

- [ ] **Step 4: Validate + commit**

Run: `tcw capabilities check`
Expected: `capabilities OK`

```bash
git add docs/capabilities/ docs/work/active/2026-06-22-taxonomy-skill-per-component-init-bootstrap-with-extends-cli/capabilities.yaml
git commit -m "capabilities: declare bootstrap capabilities (Missing) + back-pointers"
```

---

### Task 2: `extends` store methods (ABC + FS adapter)

**Files:**
- Modify: `tcw/store/base.py` (add two abstract methods to `TaxonomyStore`, after `check`)
- Modify: `tcw/store/fs.py` (implement on `FsTaxonomyStore`)
- Test: `tests/test_taxonomy.py`

**Interfaces:**
- Produces: `TaxonomyStore.extends_add(self, alias: str, ref: str) -> None`, `TaxonomyStore.extends_remove(self, alias: str) -> None`. FS realization reads/writes `self.config["extends"]` → `docs/taxonomy/config.yaml` via `dump_yaml`, stages via `self._stage`. Resolution: `(self.node_root / ref / "docs" / "taxonomy").resolve()` (matches the loader at `fs.py:317`).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_taxonomy.py`)

```python
# ── extends (federation) write path ───────────────────────────────────────────

def test_extends_add_writes_map_and_resolves(tmp_path):
    base = node(tmp_path, "base")
    write_term(base, "widget", name="Widget")
    consumer = node(tmp_path, "consumer")
    FsTaxonomyStore.open(consumer).extends_add("shared", "../base")
    st = FsTaxonomyStore.open(consumer)            # reopen to load the new federation
    assert "shared/widget" in {t.qualified for t in st.list()}
    assert st.get("shared/widget").name == "Widget"


def test_extends_add_refuses(tmp_path):
    node(tmp_path, "base")
    consumer = node(tmp_path, "consumer")
    FsTaxonomyStore.open(consumer).extends_add("shared", "../base")
    st = FsTaxonomyStore.open(consumer)
    with pytest.raises(ValueError):               # duplicate alias
        st.extends_add("shared", "../base")
    with pytest.raises(ValueError):               # missing target repo
        st.extends_add("nope", "../does-not-exist")
    with pytest.raises(ValueError):               # self-reference
        st.extends_add("self", ".")


def test_extends_remove(tmp_path):
    node(tmp_path, "base")
    consumer = node(tmp_path, "consumer")
    FsTaxonomyStore.open(consumer).extends_add("shared", "../base")
    st = FsTaxonomyStore.open(consumer)
    st.extends_remove("shared")
    assert "shared" not in (FsTaxonomyStore.open(consumer).config.get("extends") or {})
    with pytest.raises(ValueError):               # absent alias
        FsTaxonomyStore.open(consumer).extends_remove("shared")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_taxonomy.py -k extends -v`
Expected: FAIL — `AttributeError`/`TypeError` (methods not defined; `TaxonomyStore` abstract).

- [ ] **Step 3: Add the abstract methods** to `tcw/store/base.py`, immediately after the `check` abstractmethod in `class TaxonomyStore`:

```python
    @abstractmethod
    def extends_add(self, alias: str, ref: str) -> None:
        """Declare federation: this taxonomy extends another store under `alias`.

        `ref` is opaque to the interface (a sibling-repo path for the FS adapter,
        a URL/id for a remote one). Refuse a duplicate alias or an unresolvable ref.
        """

    @abstractmethod
    def extends_remove(self, alias: str) -> None:
        """Drop a federation alias. Refuse if it isn't present."""
```

- [ ] **Step 4: Implement on `FsTaxonomyStore`** in `tcw/store/fs.py` (add after `remove`, before the `relators`/`check` section):

```python
    def extends_add(self, alias: str, ref: str) -> None:
        extends = dict(self.config.get("extends") or {})
        if alias in extends:
            raise ValueError(f"extends alias already exists: {alias} (rm it first)")
        target = (self.node_root / ref / "docs" / "taxonomy").resolve()
        if not target.is_dir():
            raise ValueError(f"no docs/taxonomy/ under {ref}")
        if target == self.root.resolve():
            raise ValueError("a taxonomy cannot extend itself")
        extends[alias] = ref
        self.config["extends"] = extends
        cfg = self.root / "config.yaml"
        dump_yaml(cfg, self.config)
        self._stage(cfg)

    def extends_remove(self, alias: str) -> None:
        extends = dict(self.config.get("extends") or {})
        if alias not in extends:
            raise ValueError(f"no such extends alias: {alias}")
        del extends[alias]
        if extends:
            self.config["extends"] = extends
        else:
            self.config.pop("extends", None)
        cfg = self.root / "config.yaml"
        dump_yaml(cfg, self.config)
        self._stage(cfg)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_taxonomy.py -k extends -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add tcw/store/base.py tcw/store/fs.py tests/test_taxonomy.py
git commit -m "feat(taxonomy): extends_add/extends_remove store methods"
```

---

### Task 3: `tcw taxonomy extends` CLI

**Files:**
- Modify: `tcw/taxonomy/cli.py` (add `"extends"` to `SUBCOMMANDS`; two handlers; nested subparser)
- Test: `tests/test_taxonomy.py`

**Interfaces:**
- Consumes: `FsTaxonomyStore.extends_add/extends_remove` (Task 2), `_store()` (existing).
- Produces: CLI paths `tcw taxonomy extends add <alias> <path>` and `tcw taxonomy extends rm <alias>`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_taxonomy.py`)

```python
def test_cli_extends_add_and_rm(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    node(tmp_path, "base")
    consumer = node(tmp_path, "consumer")
    monkeypatch.chdir(consumer)
    assert main(["taxonomy", "extends", "add", "shared", "../base"]) == 0
    capsys.readouterr()
    assert (consumer / "docs/taxonomy/config.yaml").exists()
    assert main(["taxonomy", "extends", "add", "shared", "../base"]) == 1   # duplicate → error exit
    capsys.readouterr()
    assert main(["taxonomy", "extends", "rm", "shared"]) == 0


def test_cli_extends_is_not_treated_as_a_term_path(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path, "repo")
    monkeypatch.chdir(root)
    # "extends" must dispatch to the subcommand, not the `taxonomy <path>` show-sugar
    assert main(["taxonomy", "extends", "rm", "ghost"]) == 1   # absent alias → handled error, not "no such term"
    assert "no such term" not in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_taxonomy.py -k "extends and cli" -v`
Expected: FAIL — argparse rejects the `extends` subcommand (invalid choice).

- [ ] **Step 3: Add `"extends"` to `SUBCOMMANDS`** in `tcw/taxonomy/cli.py:10`:

```python
SUBCOMMANDS = {"init", "list", "add", "show", "rm", "search", "check", "extends"}
```

- [ ] **Step 4: Add the two handlers** in `tcw/taxonomy/cli.py` (near the other `_`-prefixed handlers):

```python
def _extends_add(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        st.extends_add(args.alias, args.path)
    except ValueError as e:
        print(f"tcw taxonomy extends add: {e}", file=sys.stderr)
        return 1
    print(f"Extends '{args.alias}' -> {args.path}  (docs/taxonomy/config.yaml). "
          f"Run `tcw taxonomy check`.")
    return 0


def _extends_rm(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        st.extends_remove(args.alias)
    except ValueError as e:
        print(f"tcw taxonomy extends rm: {e}", file=sys.stderr)
        return 1
    print(f"Removed extends '{args.alias}'")
    return 0
```

- [ ] **Step 5: Wire the nested subparser** in `add_subparser`, after the `check` parser:

```python
    pe = g.add_parser("extends", help="declare taxonomy inheritance (federation)")
    eg = pe.add_subparsers(dest="ecmd", required=True)
    pea = eg.add_parser("add", help="add an extends alias -> sibling repo path")
    pea.add_argument("alias")
    pea.add_argument("path", help="path to a sibling repo containing docs/taxonomy/")
    pea.set_defaults(func=_extends_add)
    per = eg.add_parser("rm", help="remove an extends alias")
    per.add_argument("alias")
    per.set_defaults(func=_extends_rm)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_taxonomy.py -k "extends" -v`
Expected: PASS (all extends tests).

- [ ] **Step 7: Commit**

```bash
git add tcw/taxonomy/cli.py tests/test_taxonomy.py
git commit -m "feat(taxonomy): tcw taxonomy extends add|rm CLI"
```

---

### Task 4: `tcw-taxonomy` skill (thin router)

**Files:**
- Create: `skills/tcw-taxonomy/SKILL.md`

- [ ] **Step 1: Write the skill** — frontmatter + inline judgment + gated bootstrap pointer + quick-ref. Use this content:

```markdown
---
name: tcw-taxonomy
description: Use when planning, seeding, or maintaining a project's domain terms — declaring nouns, linking related terms, federating shared vocabulary across repos, or bootstrapping a taxonomy from an existing codebase. Drives `tcw taxonomy`; the capabilities axis is tcw-capabilities, the work axis is tcw-work.
---

# The taxonomy process

**What it is:** the taxonomy axis is the *nouns* — the canonical domain terms a
project reasons about (its ubiquitous language). It exists so the other axes point
at shared, unambiguous concepts instead of re-defining words: capabilities name a
term as their **Subject**, work references terms. The pointers are one-directional —
**taxonomy never points back** at capabilities or work.

Drive `tcw taxonomy`; never hand-edit term markdown when a command applies. Read
with `list` / `show` / `search`; create with `add`; validate with `check`; remove a
local term with `rm`. The capabilities axis is **REQUIRED SUB-SKILL: Use tcw-capabilities**.

## Judgment

- **One term per distinct concept.** A near-synonym or merely-related concept is a
  `relatesTo` link (in the term's `meta.yaml`), not a second term.
- **Nest specializations** under a parent: `tcw taxonomy add <Name> --parent <path>`
  (`-s` to override the leaf slug; description inline or piped on stdin).
- **Keep descriptions short** — one or two sentences of what the noun means here.
- **Run `tcw taxonomy check` after edits** — it validates extends aliases and every
  relatesTo / subject reference (cycles, dup aliases, dangling/ambiguous refs).

## Inheritance (federation)

Import another repo's taxonomy so shared nouns mean the same thing everywhere:
`tcw taxonomy extends add <alias> <sibling-repo-path>` (writes the `extends:` map;
`rm <alias>` drops it). Inherited terms show in `list` flagged by origin and qualify
as `<alias>/<slug>`; they can't be removed locally. Remote git/URL sources are not
yet supported (local sibling-repo paths only).

## Bootstrap (read on demand)

To seed a new or empty taxonomy from an existing codebase (deep-dive → draft →
refine with the user → write) → read [`docs/init.md`](docs/init.md).

## Quick reference

| Goal | Command |
|---|---|
| add a term | `tcw taxonomy add "<Name>" [--parent <path>] [-s <slug>]` |
| nest under a parent | `tcw taxonomy add "<Name>" --parent <path>` |
| link related terms | edit `relatesTo` in the term's `meta.yaml`, then `check` |
| browse / read / find | `tcw taxonomy list` · `tcw taxonomy show <path>` · `tcw taxonomy search <q>` |
| inherit another repo's terms | `tcw taxonomy extends add <alias> <repo-path>` · `… extends rm <alias>` |
| validate | `tcw taxonomy check` |
| remove a local term | `tcw taxonomy rm <path>` |
```

- [ ] **Step 2: Verify** the file parses as a skill (frontmatter `name:` matches the directory).

Run: `head -4 skills/tcw-taxonomy/SKILL.md`
Expected: shows `name: tcw-taxonomy`.

- [ ] **Step 3: Commit**

```bash
git add skills/tcw-taxonomy/SKILL.md
git commit -m "docs(skill): add tcw-taxonomy driving skill"
```

---

### Task 5: bootstrap sub-docs

**Files:**
- Create: `skills/tcw-taxonomy/docs/init.md`
- Create: `skills/tcw-capabilities/docs/init.md`

- [ ] **Step 1: Write `skills/tcw-taxonomy/docs/init.md`:**

```markdown
# Bootstrap a taxonomy from an existing codebase

Seed `docs/taxonomy/` for a project adopting TCW. Four beats. Ground every step in
the actual repo; **do not invoke `superpowers:brainstorming`** — run the lightweight
refine loop below.

## 1. Ensure the tree exists
`tcw taxonomy init` if `docs/taxonomy/` is absent (no-op if present).

## 2. Inheritance
Ask the user: **"Does this project inherit its taxonomy from other repos?"**
- If yes, collect a list of sibling-repo paths. For each, derive an alias from the
  repo directory name, confirm it with the user, and run
  `tcw taxonomy extends add <alias> <path>`.
- You may also write other `docs/taxonomy/config.yaml` keys directly if bootstrapping
  additional adapter config — but `extends` always goes through the command.
- Run `tcw taxonomy check`.

## 3. Deep-dive (draft)
Survey the codebase for candidate domain nouns: core models/entities, ubiquitous-
language terms, bounded-context or module names, key value objects. **Skip generic
framework nouns** (Controller, Service, Request) unless they carry domain meaning.
Produce a draft forest: each term with a one-line description and a proposed parent.

## 4. Refine + write
Present the draft. Run a lightweight loop with the user — add / cut / rename / merge /
re-nest — until they're satisfied. Then write the agreed terms:
`tcw taxonomy add "<Name>" [--parent <path>]` (pipe the description on stdin).
Finish with `tcw taxonomy check` and show the resulting `tcw taxonomy list`.
```

- [ ] **Step 2: Write `skills/tcw-capabilities/docs/init.md`:**

```markdown
# Bootstrap capabilities from an existing codebase

Seed `docs/capabilities/` for a project adopting TCW. Same four-beat shape as the
taxonomy bootstrap; **do not invoke `superpowers:brainstorming`**.

## 0. Taxonomy first
Capabilities reference terms (their **Subject**). If `docs/taxonomy/` is empty, point
the user at `/tcw-taxonomy-init` before seeding capabilities.

## 1. Ensure the tree exists
`tcw capabilities init` if `docs/capabilities/` is absent.

## 2. Deep-dive (draft)
Survey the codebase for **user stories — what a user can do**: routes, CLI commands,
request handlers, user-facing features and flows. Group candidates by namespace
(one per major surface/component). For each, draft a `## <Capability name>` with a
one-line "As a user, I …" body and a status: `Supported` for what already ships,
`Missing` / `Partial` otherwise.

## 3. Refine + write
Present the draft; run the lightweight add / cut / rename / regroup loop with the
user. Then write each agreed capability:
`tcw capabilities add <namespace/path> "<Name>" --status <Status>` (pipe the body),
and set status/fields with `tcw capabilities set` where needed. A new namespace's
first capability is a fresh single-capability file; add later ones in that namespace
as additional flat files (`<namespace>/<slug>`). Finish with `tcw capabilities check`.
```

- [ ] **Step 3: Commit**

```bash
git add skills/tcw-taxonomy/docs/init.md skills/tcw-capabilities/docs/init.md
git commit -m "docs(skill): per-component bootstrap (init) sub-docs"
```

---

### Task 6: command routers

**Files:**
- Create: `commands/tcw-taxonomy-init.md`
- Create: `commands/tcw-capabilities-init.md`

- [ ] **Step 1: Write `commands/tcw-taxonomy-init.md`:**

```markdown
---
description: Bootstrap this project's taxonomy — deep-dive the codebase, propose domain terms, refine with you, and write the first draft (incl. optional inheritance).
---

Read `skills/tcw-taxonomy/docs/init.md` in this plugin and follow it. Ground every
step in the actual repository — survey the real code before proposing terms, and
confirm each decision with the user before writing. If `tcw` is missing, see the
tcw-plugin skill first.
```

- [ ] **Step 2: Write `commands/tcw-capabilities-init.md`:**

```markdown
---
description: Bootstrap this project's capabilities — deep-dive the codebase, propose what users can do, refine with you, and write the first draft (taxonomy first).
---

Read `skills/tcw-capabilities/docs/init.md` in this plugin and follow it. Ground
every step in the actual repository, and seed the taxonomy first if it is empty
(`/tcw-taxonomy-init`). If `tcw` is missing, see the tcw-plugin skill first.
```

- [ ] **Step 3: Commit**

```bash
git add commands/tcw-taxonomy-init.md commands/tcw-capabilities-init.md
git commit -m "feat(commands): /tcw-taxonomy-init + /tcw-capabilities-init routers"
```

---

### Task 7: capabilities skill — gated bootstrap pointer

**Files:**
- Modify: `skills/tcw-capabilities/SKILL.md`

- [ ] **Step 1: Add a gated section** to `skills/tcw-capabilities/SKILL.md`, immediately before the `## Quick reference` section:

```markdown
## Bootstrap (read on demand)

To seed `docs/capabilities/` for a project newly adopting TCW (deep-dive the
codebase → draft → refine with the user → write) → read [`docs/init.md`](docs/init.md).
```

- [ ] **Step 2: Commit**

```bash
git add skills/tcw-capabilities/SKILL.md
git commit -m "docs(skill): tcw-capabilities gated bootstrap pointer"
```

---

### Task 8: documentation sync + final verification + complete

**Files:**
- Modify: `README.md`
- Modify: `docs/release-notes/upcoming.md`
- Modify: `docs/changelogs/upcoming.md`

- [ ] **Step 1: README** — in the skills overview, add `tcw-taxonomy` alongside `tcw-capabilities`/`tcw-work`; in the commands/usage section add `/tcw-taxonomy-init` and `/tcw-capabilities-init`; in the `tcw taxonomy` section document `extends add|rm`. Match the existing README voice (plain, high-readability). Read the relevant sections first and insert parallel entries.

- [ ] **Step 2: Release notes** — append to `docs/release-notes/upcoming.md`:

```markdown

## Added
- **Bootstrap your taxonomy and capabilities from your codebase.** Run
  `/tcw-taxonomy-init` or `/tcw-capabilities-init` and the assistant studies your
  code, proposes a first draft, refines it with you, and writes it.
- **Declare shared vocabulary from the command line.** `tcw taxonomy extends add
  <name> <path>` imports another repo's terms — no more hand-editing config.
```

- [ ] **Step 3: Changelog** — capture the commit range and append to `docs/changelogs/upcoming.md`:

```bash
git rev-parse --short HEAD   # note as the range end; range start = previous upcoming entry / release tag
```

```markdown

## Added
- `tcw taxonomy extends add|rm` — write the federation `extends:` map via CLI
  (`TaxonomyStore.extends_add/extends_remove`; FS adapter writes `docs/taxonomy/config.yaml`).
- `tcw-taxonomy` skill (thin router) + per-component bootstrap sub-docs
  (`skills/{tcw-taxonomy,tcw-capabilities}/docs/init.md`).
- `/tcw-taxonomy-init` and `/tcw-capabilities-init` command routers.

## Changed
- `tcw-capabilities` skill gains a gated bootstrap pointer.
```

- [ ] **Step 4: Run the full test suite**

Run: `pytest -q`
Expected: all pass (note: `test_plugin_manifests.py` does not enumerate skills/commands, so the new files don't affect it).

- [ ] **Step 5: Documentation-sync gate + commit**

Invoke the `skill-cefailures:documentation-sync` skill to confirm every triggered entry is handled, then:

```bash
git add README.md docs/release-notes/upcoming.md docs/changelogs/upcoming.md
git commit -m "docs: sync README + release notes + changelog for taxonomy bootstrap"
```

- [ ] **Step 6: Reconcile capabilities + complete the item**

Flip the two new capabilities to Supported (the ledger flip; bare id resolves while each file is single-capability):

```bash
tcw capabilities set taxonomy/bootstrap-the-taxonomy --status Supported
tcw capabilities set capabilities/bootstrap-the-capabilities --status Supported
# federate-shared-vocabulary: body edit only — update its declaration line to mention
# `tcw taxonomy extends add`; it STAYS Partial (remote sources still deferred).
tcw capabilities check
git add docs/capabilities/
git commit -m "capabilities: flip bootstrap capabilities to Supported"
tcw work complete 2026-06-22-taxonomy-skill-per-component-init-bootstrap-with-extends-cli --resolution done --confirm
```

---

## Self-review notes

- **Spec coverage:** Component 1 → Task 4; Component 2 → Tasks 2–3; Component 3 → Task 5; Component 4 → Task 6; Component 5 → Task 7; capability deltas → Tasks 1 & 8; docs sync → Task 8. All covered.
- **`extends list` correctly absent** (out of scope). Only `add`/`rm` implemented.
- **federate-shared-vocabulary** is a body edit that stays Partial (Task 8 Step 6) — no status flip.
- **Method names consistent:** `extends_add`/`extends_remove` (ABC + FS + CLI handlers) throughout.
