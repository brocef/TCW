# Migration prompt: a TCW project from 0.10.X → 0.11.0

> **This document is a prompt.** Give it to a coding agent (with access to the
> target project's repo and the `tcw` CLI at version ≥ 0.11.0) and tell it to
> follow the instructions. It migrates the project's stored representation from
> the pre-0.11.0 layout to the 0.11.0 layout.

---

You are migrating a TCW project from a **pre-0.11.0** on-disk representation to the
**0.11.0** representation. The one and only structural change that needs migrating
is the **Capabilities** axis: capabilities moved from a _file + `## heading`_ model
to a _folder-per-capability_ model with stable ids. Taxonomy and Work are
**unchanged** — do not touch `docs/taxonomy/` or `docs/work/`. The new
`tcw://` linking and `tcw validate` features are purely additive and need no
migration.

Work carefully and verifiably. **git is your rollback**: start from a clean tree,
make the change, and prove equivalence before you delete anything.

## 1. What changed (and why a migration is needed)

**Before (≤ 0.10.X):** `docs/capabilities/` held Markdown files — flat `*.md` and
per-folder `capabilities.md` — where each `## heading` was one capability, its
metadata written inline as `**Field:** value` lines, followed by a prose body.
Capabilities were addressed as `<file_id>#<heading>`.

**After (0.11.0):** every capability is its **own folder** `docs/capabilities/<path>/`
containing:

- `meta.yaml` — `id` (opaque stable id), `name`, then the fields (`Status`,
  `Subject`, `Feature`, `Planning doc`, …). `Subject` is now a **list**.
- `description.md` — the body prose.

Capabilities are now addressed by **path** (e.g. `auth/login`), never a `#heading`.
Each carries an opaque immutable `id` used as the durable key for federation
overrides and `tcw://` references — so the id must be assigned **deterministically**
(below), not randomly. This is why you must not migrate with `tcw capabilities add`
(it mints a random id); write the folders directly.

## 2. Preconditions

1. Confirm the CLI is new enough: `tcw --version` → must be `0.11.0` or later.
2. Confirm you're at the project's TCW node (a `tcw-config.yaml` sentinel is at the
   repo/subproject root; `tcw capabilities list` runs without a "no node" error).
3. **Start from a clean git working tree** (`git status` shows nothing). Commit or
   stash first. You will verify, then commit; git is the rollback if anything is
   off.

## 3. Detect whether migration is even needed

Look under `docs/capabilities/`:

- If every capability is already a folder with a `meta.yaml` + `description.md`
  and there are **no** stray `*.md` capability files, the project is already on
  the 0.11.0 model — **stop, nothing to do.**
- If you see `*.md` files (a flat `foo.md`, or a `capabilities.md` inside a
  folder) whose content has `## heading` blocks with `**Field:**` lines, those are
  legacy capabilities that must be migrated.

## 4. The transformation rules

For each **legacy capability file** (`*.md` under `docs/capabilities/`, **except**
already-migrated `description.md`, and the retired sidecars `errors.md` /
`states.md` — see §6):

1. **Compute the file id** (`file_id`): the file's path under
   `docs/capabilities/` with the `.md` dropped — **except** a file literally named
   `capabilities.md`, whose `file_id` is its **parent directory** path.
    - `docs/capabilities/web.md` → `file_id = web`
    - `docs/capabilities/capabilities/capabilities.md` → `file_id = capabilities`
    - `docs/capabilities/auth/login.md` → `file_id = auth/login`
    - **Edge case:** a `capabilities.md` sitting _directly_ in `docs/capabilities/`
      (no enclosing namespace folder) has no target path — do **not** migrate it
      mechanically; give each of its capabilities an explicit namespace folder by
      hand. (Real projects always namespace their capabilities, so you're unlikely
      to hit this.)

2. **Parse the file into capability blocks.** Split on lines starting with `## `.
   For each block: the heading text is the `name`; the immediately-following
   `**Key:** value` lines are the `fields`; everything after them is the `body`.

3. **Compute each heading's slug** (`heading_slug(name)`): lowercase, strip any
   character that is not a word char / whitespace / hyphen, then replace runs of
   whitespace with a single `-`.
    - `"Browse TCW content in a local web app"` → `browse-tcw-content-in-a-local-web-app`

4. **Choose the target folder path:**
    - File has **one** heading → collapse: target = `file_id` (drop the heading
      segment). `web.md`'s single heading → folder `docs/capabilities/web/`.
    - File has **multiple** headings → one folder per heading:
      target = `file_id/<heading_slug>`. `capabilities/capabilities.md`'s "Add a
      capability" → folder `docs/capabilities/capabilities/add-a-capability/`.
    - A duplicate heading slug within one file is **fatal** — it can't get a unique
      id. Stop and fix that source file by hand.

5. **Assign the stable id** (deterministic, so re-runs and federated copies agree):

    ```
    id = "cap-" + sha1(f"{file_id}#{heading_slug}").hexdigest()[:6]
    ```

    (SHA-1 of the exact string `<file_id>#<heading_slug>`, first 6 hex chars.)

6. **Write the folder:**
    - `meta.yaml` with keys in this order: `id`, `name`, then each parsed field.
      Convert the `Subject` field from a scalar (`Subject: cli` or comma-separated
      `a, b`) to a **YAML list**. Leave other fields (`Status`, `Feature`,
      `Planning doc`, …) as scalars.
    - `description.md` with the block's body (may be empty).

7. After all folders are written **and verified** (§5), **delete the legacy
   `*.md` files** you migrated.

### Concrete example

Legacy `docs/capabilities/web.md`:

```markdown
# Web — capabilities

## Browse TCW content in a local web app

**Status:** Supported
**Planning doc:** 2026-07-01-local-read-only-web-viewer-tcw-serve
**Subject:** cli
```

Becomes `docs/capabilities/web/meta.yaml`:

```yaml
id: cap-9d225a
name: Browse TCW content in a local web app
Status: Supported
Planning doc: 2026-07-01-local-read-only-web-viewer-tcw-serve
Subject:
    - cli
```

plus an (empty here) `docs/capabilities/web/description.md`. Note the top-of-file
`# Web — capabilities` title line is discarded — it was never a capability, only a
file header.

## 5. Verify before you delete

Migration is not done until it's proven equivalent:

1. **Field-set equality.** For every migrated capability, the set of fields + body
   in the new `meta.yaml`/`description.md` must equal the legacy block's fields +
   body, with `Subject` compared as a set/sorted-list (scalar vs one-element list
   must match). If any capability's normalized field set differs, **stop** — do not
   delete the legacy files; investigate.
2. `tcw capabilities check` → must pass (validates ids, Subject/Feature refs
   against the taxonomy, federation, etc.).
3. `tcw capabilities list` → the same capabilities you had before, now
   path-addressed and showing their status/origin.
4. `tcw validate` → `validate OK` for the whole node.
5. `git diff --stat` and spot-check a couple of folders by eye.

Only after all five pass: `git rm` the legacy files and commit the whole migration
as one commit.

## 6. Rare legacy artifacts (manual review)

Very old trees may contain artifacts that 0.11.0 removed outright — handle these by
hand, they are **not** part of the mechanical transform above:

- `errors.md` / `states.md` sidecars → **drop them** (the model no longer has
  per-capability error/state sidecars). Preserve anything still meaningful by
  folding it into the capability's `description.md` body first.
- State-variant files (`with-<x>.md` / `without-<x>.md`) and any `[state]`
  addressing → there is no state-variant concept anymore. Review each and either
  collapse it into a single capability folder or drop it. If your project never
  used these (most didn't), you'll have none.

## 7. Recommended approach: a throwaway script

Migrating more than a handful of capabilities by hand is error-prone. Prefer
writing a **one-off Python script** that implements §4 exactly, run it against the
clean tree, verify (§5), then discard the script. A faithful reference
implementation of the core transform:

```python
import hashlib, re, yaml
from pathlib import Path

ROOT = Path("docs/capabilities")
FIELD = re.compile(r"^\*\*([^:*]+):\*\*\s*(.*)$")
LIST_FIELDS = {"Subject"}

def hslug(text):
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"\s+", "-", s)

def cap_id(file_id, hs):
    return "cap-" + hashlib.sha1(f"{file_id}#{hs}".encode()).hexdigest()[:6]

def file_id_of(p):                      # capabilities.md -> parent dir; else path minus .md
    rel = p.relative_to(ROOT)
    fid = str(rel.parent) if p.name == "capabilities.md" else str(rel.with_suffix(""))
    if fid in (".", ""):                # root-level capabilities.md has no namespace path
        raise SystemExit(f"{p}: root-level capabilities file has no path — give its "
                         "capabilities explicit namespace folders by hand (see §4).")
    return fid

def parse(text):                        # -> [{name, hs, fields, body}]
    out = []
    for block in re.split(r"(?m)^##\s+", text)[1:]:
        lines = block.splitlines()
        name, fields, i = lines[0].strip(), {}, 1
        while i < len(lines) and (m := FIELD.match(lines[i].strip())):
            fields[m.group(1).strip()] = m.group(2).strip(); i += 1
        out.append({"name": name, "hs": hslug(name), "fields": fields,
                    "body": "\n".join(lines[i:]).strip()})
    return out

def as_list(v):
    return v if isinstance(v, list) else [s.strip() for s in str(v).split(",") if s.strip()]

legacy = [p for p in sorted(ROOT.rglob("*.md"))
          if p.name not in {"errors.md", "states.md", "description.md"}]
for p in legacy:
    fid = file_id_of(p)
    caps = parse(p.read_text(encoding="utf-8"))
    multi = len(caps) > 1
    for c in caps:
        target = ROOT / (f"{fid}/{c['hs']}" if multi else fid)
        target.mkdir(parents=True, exist_ok=True)
        meta = {"id": cap_id(fid, c["hs"]), "name": c["name"]}
        for k, v in c["fields"].items():
            meta[k] = as_list(v) if k in LIST_FIELDS else v
        (target / "meta.yaml").write_text(
            yaml.safe_dump(meta, sort_keys=False, allow_unicode=True))
        (target / "description.md").write_text(c["body"] + ("\n" if c["body"] else ""))
    # p.unlink()   # <- only after the §5 verification passes
```

Leave the `p.unlink()` commented until §5 passes, then delete the legacy files (a
`git rm` keeps the rename legible in review).

## 8. After migrating

You're now on the 0.11.0 model. Two additive features are available (no migration,
just usable):

- **`tcw://` links** — reference any object from an object's body with
  `[text](tcw://[<namespace>/]<axis>/<ref>)` (axis `T`/`C`/`W`).
- **`tcw validate [path]`** — one-pass YAML + `tcw://` link + component-check
  soundness for the whole node.

Commit the migration as a single, well-described commit.
