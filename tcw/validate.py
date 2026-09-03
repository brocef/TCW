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
    roots = [node_root / "docs" / c for c in ("taxonomy", "capabilities")]
    try:
        roots.append(FsWorkStore.open(node_root).root)
    except ValueError:
        roots.append(node_root / "docs" / "work")
    return roots


def _under(p: Path, d: Path) -> bool:
    return p == d or d in p.parents


def _components_to_check(node_root: Path, path) -> list[str]:
    """Which component check()s to run: both when scanning the whole node, else
    the one whose tree the path falls under (a path under docs/work — or spanning
    several trees — runs none)."""
    if path is None:
        present = [c for c in ("taxonomy", "capabilities")
                   if (node_root / "docs" / c).is_dir()]
        try:
            FsWorkStore.open(node_root)
            present.append("work")
        except ValueError:
            if (node_root / "docs" / "work").exists() or (node_root / "tcw-config.yaml").exists():
                present.append("work")
        return present
    p = Path(path).resolve()
    for c in ("taxonomy", "capabilities"):
        if _under(p, (node_root / "docs" / c).resolve()):
            return [c]
    try:
        if _under(p, FsWorkStore.open(node_root).root):
            return ["work"]
    except ValueError:
        pass
    return []


def _run_check(node_root: Path, comp: str, identifier: str | None = None) -> list[str]:
    """One component's `check()`, or the reason its store could not be opened.

    Opening is guarded for every component, not just work. A store that is
    declared-but-unprovisioned or declared-malformed raises rather than
    returning problems, and those are exactly the configuration faults
    `tcw validate` exists to report — so an unguarded `open` would abort the
    whole validation with one component's problem instead of listing it beside
    the others. The node-root `tcw-config.yaml` is also not among the YAML-scan
    roots, so nothing else would catch it.
    """
    store_cls = {"taxonomy": FsTaxonomyStore, "work": FsWorkStore,
                 "capabilities": FsCapabilitiesStore}[comp]
    try:
        store = store_cls.open(node_root)
    except ValueError as e:
        return [f"{comp} check: {e}"]
    if comp == "capabilities":
        problems = store.check(identifier=identifier)
    else:
        problems = store.check(identifier)
    return [f"{comp} check: {p}" for p in problems]


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
    registry = FsProjectRegistry.open(node_root).require_valid()
    # Over the projects this checkout can open. A partial graph makes this scan
    # narrower, never wrong: it can miss a collision a complete checkout would
    # catch, and cannot invent one. The unreachable edges themselves are reported
    # by `tcw validate`'s caller, so they are not silently dropped here.
    work_roots: dict[Path, str] = {}
    for project in [registry.current, *registry.ancestors(), *registry.descendants()]:
        try:
            root = FsWorkStore.open(Path(project.locator)).root
        except ValueError:
            continue
        previous = work_roots.get(root)
        if previous is not None and previous != project.id:
            return [f"project graph: projects '{previous}' and '{project.id}' resolve to the same work.path: {root}"]
        work_roots[root] = project.id
    if target is not None:
        roots = _target_roots(node_root, target)
        if not roots:
            return [f"{target.axis} target: no such object '{target.ref}'"]
    else:
        roots = [r for r in _scan_roots(node_root, path) if r.exists()]
    problems: list[str] = []
    yaml_syntax_error = False

    # Retention: a malformed setting reads as the safe default, so the only
    # place a user learns about it is here. And a node that says it retains
    # while git ignores the folder is a real contradiction — the items will not
    # be tracked whatever the config says.
    try:
        work_store = FsWorkStore.open(node_root)
    except ValueError:
        work_store = None
    if work_store is not None:
        problems += [f"work: {p}" for p in work_store.retention_problems()]
        problems += work_store.retention_conflicts()

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
