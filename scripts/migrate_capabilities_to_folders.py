#!/usr/bin/env python3
"""One-time migration: capabilities file+heading model → folder-per-capability.

Converts the legacy `docs/capabilities/` tree (flat `*.md` and folder
`capabilities.md`, each holding one-or-more `## heading` capabilities with inline
`**Field:**` metadata) into folder-per-capability nodes (`meta.yaml` +
`description.md`), matching taxonomy/work.

Rules:
  * multi-heading source file  → one folder per heading: `<file_id>/<heading-slug>/`
  * single-heading source file → collapse: `<file_id>/` (drop the heading segment)
  * stable id = `cap-` + first 6 hex of sha1("<file_id>#<heading_slug>") — reproducible
  * `Subject` scalar → one-element list

Dry-run by default; pass --apply to write folders and delete the old files.
Run against a clean git tree: git is the rollback, and the equality check gates
the delete. Idempotent-ish: on an already-migrated tree there are no legacy files
to convert, so it is a no-op.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import yaml

_FIELD_RE = re.compile(r"^\*\*([^:*]+):\*\*\s*(.*)$")
_STRUCTURAL = ("id", "name")
# Field keys that carry taxonomy-slug lists in the folder model.
_LIST_FIELDS = {"Subject"}


def heading_slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"\s+", "-", s)


def cap_id(file_id: str, hslug: str) -> str:
    return "cap-" + hashlib.sha1(f"{file_id}#{hslug}".encode()).hexdigest()[:6]


def parse_file(text: str) -> list[dict]:
    """Return [{name, heading_slug, fields, body}] for each `## heading` block."""
    caps = []
    for block in re.split(r"(?m)^##\s+", text)[1:]:
        lines = block.splitlines()
        name = lines[0].strip()
        fields: dict = {}
        idx = 1
        while idx < len(lines):
            m = _FIELD_RE.match(lines[idx].strip())
            if not m:
                break
            fields[m.group(1).strip()] = m.group(2).strip()
            idx += 1
        body = "\n".join(lines[idx:]).strip()
        caps.append({"name": name, "heading_slug": heading_slug(name),
                     "fields": fields, "body": body})
    return caps


def _disk_id(root: Path, p: Path) -> str:
    rel = p.relative_to(root)
    return str(rel.parent) if p.name == "capabilities.md" else str(rel)[:-3]


def _legacy_files(root: Path) -> list[Path]:
    """Legacy capability files: flat *.md + folder capabilities.md (skip meta.yaml folders)."""
    out = []
    for p in sorted(root.rglob("*.md")):
        if p.name in {"errors.md", "states.md", "description.md"}:
            continue
        # A folder-model node (already migrated) has a sibling meta.yaml.
        if (p.parent / "meta.yaml").is_file() and p.name == "description.md":
            continue
        out.append(p)
    return out


def collect(root: Path) -> tuple[list[dict], dict]:
    """Parse the legacy tree → (entries, pre-migration index by (file_id, name))."""
    entries = []
    index: dict = {}
    for p in _legacy_files(root):
        file_id = _disk_id(root, p)
        caps = parse_file(p.read_text(encoding="utf-8"))
        multi = len(caps) > 1
        seen_slugs = set()
        for c in caps:
            if c["heading_slug"] in seen_slugs:
                raise SystemExit(f"FATAL: duplicate heading '{c['name']}' in {p} "
                                 "— migration cannot assign a stable id; fix by hand.")
            seen_slugs.add(c["heading_slug"])
            target = f"{file_id}/{c['heading_slug']}" if multi else file_id
            cid = cap_id(file_id, c["heading_slug"])
            entries.append({"src": p, "file_id": file_id, "target": target,
                            "id": cid, **c})
            index[(file_id, c["name"])] = _norm_fields(c["fields"], c["body"])
    return entries, index


def _norm_fields(fields: dict, body: str) -> dict:
    """Normalized comparison view: all CAP_FIELDS + body, Subject as a sorted list."""
    out = {k: (sorted(_as_list(v)) if k in _LIST_FIELDS else v) for k, v in fields.items()}
    out["__body__"] = body.strip()
    return out


def _as_list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [s.strip() for s in str(v).split(",") if s.strip()]


def build_meta(entry: dict) -> dict:
    meta = {"id": entry["id"], "name": entry["name"]}
    for k, v in entry["fields"].items():
        meta[k] = _as_list(v) if k in _LIST_FIELDS else v
    return meta


def verify_equal(root: Path, entries: list[dict], pre_index: dict) -> None:
    """Post-migration equality over full field set (+body), by (target-derived) identity."""
    post = {}
    for e in entries:
        d = root / e["target"]
        meta = yaml.safe_load((d / "meta.yaml").read_text()) or {}
        body = (d / "description.md").read_text(encoding="utf-8") if (d / "description.md").exists() else ""
        fields = {k: v for k, v in meta.items() if k not in _STRUCTURAL}
        post[(e["file_id"], e["name"])] = _norm_fields(fields, body)
    if post != pre_index:
        diff = {k: (pre_index.get(k), post.get(k)) for k in set(pre_index) | set(post)
                if pre_index.get(k) != post.get(k)}
        raise SystemExit(f"FATAL: post-migration field set differs from pre:\n{diff}")
    ids = [e["id"] for e in entries]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"FATAL: id collision among {len(ids)} entries")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default="docs/capabilities",
                    help="capabilities root (default: docs/capabilities)")
    ap.add_argument("--apply", action="store_true", help="write folders + delete legacy files")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"no such dir: {root}")

    entries, pre_index = collect(root)
    if not entries:
        print("nothing to migrate (no legacy capability files).")
        return 0

    # Target-collision guard.
    targets: dict = {}
    for e in entries:
        if e["target"] in targets:
            raise SystemExit(f"FATAL: two capabilities map to '{e['target']}': "
                             f"{targets[e['target']]} and {e['src']}")
        targets[e["target"]] = e["src"]

    for e in entries:
        print(f"  {e['src'].relative_to(root)}#{e['heading_slug']}  →  "
              f"{e['target']}/  ({e['id']})")
    print(f"\n{len(entries)} capabilities from {len({e['src'] for e in entries})} files.")

    if not args.apply:
        print("\n(dry run — pass --apply to write)")
        return 0

    # Write folders.
    for e in entries:
        d = root / e["target"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "meta.yaml").write_text(
            yaml.safe_dump(build_meta(e), sort_keys=False, allow_unicode=True),
            encoding="utf-8")
        (d / "description.md").write_text(e["body"] + ("\n" if e["body"] else ""),
                                          encoding="utf-8")

    # Equality gate BEFORE deleting anything.
    verify_equal(root, entries, pre_index)

    # Delete legacy files.
    for p in {e["src"] for e in entries}:
        p.unlink()

    print(f"\napplied: {len(entries)} folders written, "
          f"{len({e['src'] for e in entries})} legacy files removed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
