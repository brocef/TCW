"""`tcw validate [path]` — one aggregate soundness pass over a TCW node.

Three passes over the scan roots (the whole node's `docs/{taxonomy,capabilities,
work}` trees, or a single `[path]`):

  (a) YAML well-formedness — every ``*.yaml`` loads via the unique-key loader
      (duplicate keys included); a parse error is a problem.
  (b) ``tcw://`` links — every ``*.md`` link-target ``](tcw://…)`` resolves
      (code spans stripped first, so examples that teach the scheme don't fail).
  (c) component ``check()`` — taxonomy + capabilities, unless (a) hit a YAML
      *syntax* error (they re-load the same files and would raise).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from tcw.refs import resolve_tcw_ref
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, FsWorkStore, load_yaml

_COMPONENTS = ("taxonomy", "capabilities", "work")
_LINK_RE = re.compile(r"\]\((tcw://[^)\s]+)\)")
# Fenced block: an opening ``` / ~~~ run (line-start) to a matching closing run.
_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$",
                       re.MULTILINE | re.DOTALL)
# Inline code span: a backtick run not adjacent to more backticks, closed by an
# equal-length run (CommonMark-ish — handles adjacent runs in scheme-teaching docs).
_INLINE_CODE_RE = re.compile(r"(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)", re.DOTALL)


@dataclass(frozen=True)
class ValidationTarget:
    """Storage-neutral identity of one object to validate."""

    axis: Literal["taxonomy", "capabilities", "work"]
    ref: str


def _strip_code(md: str) -> str:
    """Drop fenced then inline code spans so `tcw://` examples in code are ignored."""
    return _INLINE_CODE_RE.sub("", _FENCE_RE.sub("", md))


def _rel(f: Path, node_root: Path) -> str:
    try:
        return str(f.relative_to(node_root))
    except ValueError:
        return str(f)


def _iter(root: Path, pattern: str):
    if root.is_file():
        return [root] if root.match(pattern) else []
    return sorted(root.rglob(pattern))


def _scan_roots(node_root: Path, path) -> list[Path]:
    if path is not None:
        return [Path(path)]
    return [node_root / "docs" / c for c in _COMPONENTS]


def _under(p: Path, d: Path) -> bool:
    return p == d or d in p.parents


def _components_to_check(node_root: Path, path) -> list[str]:
    """Which component check()s to run: both when scanning the whole node, else
    the one whose tree the path falls under (a path under docs/work — or spanning
    several trees — runs none)."""
    if path is None:
        return [c for c in ("taxonomy", "capabilities", "work")
                if (node_root / "docs" / c).is_dir()]
    p = Path(path).resolve()
    for c in ("taxonomy", "capabilities", "work"):
        if _under(p, (node_root / "docs" / c).resolve()):
            return [c]
    return []


def _run_check(node_root: Path, comp: str, identifier: str | None = None) -> list[str]:
    if comp == "taxonomy":
        return [f"taxonomy check: {p}"
                for p in FsTaxonomyStore.open(node_root).check(identifier)]
    if comp == "work":
        try:                                          # a malformed node-root tcw-config.yaml
            problems = FsWorkStore.open(node_root).check(identifier)  # (the tag registry) isn't in the
        except ValueError as e:                       # YAML-scan roots, so report it, don't crash
            return [f"work check: {e}"]
        return [f"work check: {p}" for p in problems]
    tax = (FsTaxonomyStore.open(node_root)
           if (node_root / "docs" / "taxonomy").is_dir() else None)
    return [f"capabilities check: {p}"
            for p in FsCapabilitiesStore.open(node_root).check(
                taxonomy=tax, identifier=identifier)]


def _target_roots(node_root: Path, target: ValidationTarget) -> list[Path]:
    """Resolve an abstract target through the filesystem adapter's private view."""
    if target.axis == "taxonomy":
        store = FsTaxonomyStore.open(node_root)
    elif target.axis == "capabilities":
        store = FsCapabilitiesStore.open(node_root)
    else:
        store = FsWorkStore.open(node_root)
    return store._validation_resources(target.ref)


def validate(node_root: Path, path: Path | None = None, *,
             target: ValidationTarget | None = None) -> list[str]:
    """Return a flat list of problem strings ([] = clean node)."""
    from tcw.store.project import FsProjectRegistry

    if path is not None and target is not None:
        raise ValueError("path and target are mutually exclusive validation selectors")

    graph_problems = [
        f"project graph: {problem}"
        for problem in FsProjectRegistry.open(node_root).check()
    ]
    if graph_problems:
        return graph_problems
    if target is not None:
        roots = _target_roots(node_root, target)
        if not roots:
            return [f"{target.axis} target: no such object '{target.ref}'"]
    else:
        roots = [r for r in _scan_roots(node_root, path) if r.exists()]
    problems: list[str] = []
    yaml_syntax_error = False

    # (a) YAML well-formedness
    for root in roots:
        for f in _iter(root, "*.yaml"):
            try:
                load_yaml(f, unique=True)
            except yaml.YAMLError as e:
                problems.append(f"{_rel(f, node_root)}: {e}")
                if isinstance(e, yaml.MarkedYAMLError):   # real syntax error, not dup-key
                    yaml_syntax_error = True

    # (b) tcw:// link resolution
    for root in roots:
        for f in _iter(root, "*.md"):
            text = _strip_code(f.read_text(encoding="utf-8"))
            for m in _LINK_RE.finditer(text):
                uri = m.group(1)
                r = resolve_tcw_ref(node_root, uri)
                if not r.ok:
                    problems.append(f"{_rel(f, node_root)}: tcw:// {uri} → {r.reason}")

    # (c) component checks — skipped on a YAML syntax error (they'd re-raise)
    if yaml_syntax_error:
        problems.append("(component checks skipped: YAML syntax error above)")
    else:
        components = [target.axis] if target is not None else _components_to_check(node_root, path)
        for comp in components:
            problems += _run_check(node_root, comp, target.ref if target else None)

    return problems
