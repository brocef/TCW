"""`tcw validate` — one aggregate soundness pass over the current project.

Passes over the scan roots (the project's taxonomy, capabilities and work
stores wherever each resolves — moved by `<c>.path` or kept in another
repository):

  (a) YAML well-formedness — every ``*.yaml`` loads via the unique-key loader
      (duplicate keys included); a parse error is a problem. Any shape is
      accepted, *except* that a file TCW writes as a record
      (``OWNED_YAML_NAMES``) must be a mapping.
  (b) ``tcw://`` links — every ``*.md`` link-target ``](tcw://…)`` resolves
      (code spans stripped first, so examples that teach the scheme don't fail).
  (c) component ``check()`` — taxonomy + capabilities, unless (a) hit a syntax
      error or a record of the wrong shape (they re-load the file and raise).
  (d) when (a) skipped (c): each tree store's open failure or leftover pre-2.5.0
      store config file, so malformed YAML cannot hide either.
  (e) the work checks (TCW-70 Design 10.1), and an invalid latest verdict
      round in any item (TCW-73 Design 6.1.7).

Every problem is a `Finding` (TCW-73 Design 6.3) with a severity of `error`,
`warning` or `unresolved`; only errors fail the command. What is said about
the run rather than found in it — checks skipped, files not read — goes to
the `notes` list a caller passes, for stderr.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import yaml

from tcw.findings import Finding
from tcw.refs import resolve_tcw_ref
from tcw.store.yaml_source import load as _load_named_yaml
from tcw.store.base import StoreLocationUnusable
from tcw.store.fs import (
    OWNED_YAML_NAMES, STORE_CLASSES, FsCapabilitiesStore, FsTaxonomyStore,
    WorkLocation, _UniqueKeyLoader, load_yaml,
)

if TYPE_CHECKING:
    from tcw.work.model import Item

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
    """Storage-neutral identity of one object to validate.

    For `axis="work"`, `ref` is the item's folder name and `item` the item as
    the caller last read or wrote it, when it has one (TCW-73 Design 6.4)."""

    axis: Literal["taxonomy", "capabilities", "work"]
    ref: str
    item: "Item | None" = field(default=None, compare=False)


def _strip_code(md: str) -> str:
    """Drop fenced then inline code spans so `tcw://` examples in code are ignored."""
    return _INLINE_CODE_RE.sub("", _FENCE_RE.sub("", md))


def _rel(f: Path, project_root: Path) -> str:
    try:
        return str(f.relative_to(project_root))
    except ValueError:
        return str(f)


def _read_text(f: Path) -> tuple[str | None, str | None]:
    """`(text, None)`, or `(None, problem)` for a file that cannot be read.
    Never opens anything but a regular file: a named pipe would block the read,
    and no exception rescues that."""
    try:
        if not f.is_file():
            return None, "not a regular file"
        return f.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        return None, "not valid UTF-8"
    except OSError as e:
        return None, f"cannot be read ({e.strerror or e.__class__.__name__})"


def _iter(root: Path, pattern: str):
    if root.is_file():
        return [root] if root.match(pattern) else []
    return sorted(root.rglob(pattern))


def _tree_roots(project_root: Path) -> dict[str, "Path | ValueError"]:
    """Each tree store this project has, at its resolved root — or why it could
    not be opened. Resolved once, so scanning and checking cannot disagree about
    where a store is. A store moved by `<c>.path` or kept in another repository
    is found here; testing for `docs/<c>` found neither.

    The rule `find_component_project` uses: a store that opens is here when its root is a
    directory, and one that will not open is reported — which includes a broken
    `extends` in a project with no tree of its own.
    """
    roots: dict[str, Path | ValueError] = {}
    for comp in ("taxonomy", "capabilities"):
        try:
            root = STORE_CLASSES[comp].open(project_root).root
        except ValueError as e:
            roots[comp] = e
            continue
        if root.is_dir():
            roots[comp] = root
    return roots


def _scan_roots(project_root: Path, trees: dict) -> list[Path]:
    roots = [r for r in trees.values() if isinstance(r, Path)]
    try:
        roots.append(WorkLocation.open(project_root).root)
    except ValueError:
        roots.append(project_root / "docs" / "work")
    return roots


def _under(p: Path, d: Path) -> bool:
    return p == d or d in p.parents


def _claims_work(project_root: Path) -> bool:
    """Whether the project's config asks for a work store at all.

    A `work:` section that configures only tags or documentation entries is not
    a claim about *where* the store is; a `path` or a `repository` is. Read
    permissively — a config too broken to parse is reported by the graph check
    long before this, and answering True there would bury that behind a
    second, worse message.
    """
    try:
        config = load_yaml(project_root / "tcw-config.yaml", unique=True)
    except Exception:
        return False
    section = config.get("work") if isinstance(config, dict) else None
    if not isinstance(section, dict):
        return False
    return section.get("path") is not None or section.get("repository") is not None


def _work_root(project_root: Path) -> Path | None:
    try:
        return WorkLocation.open(project_root).root
    except ValueError:
        return None


def _checks_work(project_root: Path) -> bool:
    """Whether to run the work checks: on a project that has a work store or
    claims one.

    A project that *claims* a work store and cannot open one has to say why — a
    declared-but-unprovisioned board, a `work.path` typo — rather than silently
    skipping the check. But "has a tcw-config.yaml" is true of every project, and a
    project may legitimately keep no board at all: a repository root registered
    purely so its packages can reach each other. Claiming one means a `work:`
    `path` or `repository`, or a tree on disk.
    """
    root = _work_root(project_root)
    return (root is not None or (project_root / "docs" / "work").exists()
            or _claims_work(project_root))


def _configured_path_problem(project_root: Path, comp: str) -> str | None:
    """A configured `<comp>.path` that is present and holds no store, or None.

    **Asked independently of resolution, and that is the whole point.** The
    resolution ladder treats an unusable configured path as a location that did
    not work out and moves on to the declaration, which is right for reading and
    wrong for a command whose entire job is enumerating configuration problems.
    Two faults were reported as one, and `_run_check` collapses any opening
    failure into a single string, so even a compound message still counts once.

    Running this only when resolution fails would miss the user it helps most:
    the one whose declared store provisions fine, so nothing ever tells them the
    path they wrote is wrong and they quietly read a second copy of the board.

    **Silent when the path is absent.** With a declaration present that is the
    ordinary case the declaration exists for, and reporting it would make every
    provisioned project noisy. Presence is tested here rather than inferred from
    the message, because `_open_at` raises the same text for a path that is
    missing and one that is a file.

    Asks the component's own `_open_at` rather than re-listing what a store
    looks like. A third spelling of the store layout is exactly the drift the
    shared ladder exists to prevent.
    """
    config_path = project_root / "tcw-config.yaml"
    try:
        config = load_yaml(config_path, unique=True)
    except Exception:
        return None                      # reported by the YAML pass above
    section = config.get(comp) if isinstance(config, dict) else None
    configured = section.get("path") if isinstance(section, dict) else None
    if not isinstance(configured, str) or not configured.strip():
        return None
    store_cls = STORE_CLASSES[comp]
    raw_root = store_cls._local_root(project_root, configured)
    if not raw_root.exists():
        return None
    try:
        store_cls._open_at(raw_root, project_root, config_path,
                           external=True, must_exist=True)
    except StoreLocationUnusable as unusable:
        return str(unusable)
    except Exception:
        # Anything else is either not this check's business or is already
        # reported by the component check beside it. Never swallow it into a
        # second, differently worded copy of the same fault.
        return None
    return None


def _config_file(project_root: Path) -> str:
    return _rel(project_root / "tcw-config.yaml", project_root)


def _config_message(error: Exception, project_root: Path) -> str:
    """An error about the config file, without the path its finding already
    gives as `where`."""
    text = str(error)
    prefix = f"{project_root / 'tcw-config.yaml'}: "
    return text[len(prefix):] if text.startswith(prefix) else text


def _run_check(project_root: Path, comp: str,
               identifier: str | None = None) -> list[Finding]:
    """One component's `check()`, or the reason its store could not be opened.

    Opening is guarded for every component, not just work. A store that is
    declared-but-unprovisioned or declared-malformed raises rather than
    returning problems, and those are exactly the configuration faults
    `tcw validate` exists to report — so an unguarded `open` would abort the
    whole validation with one component's problem instead of listing it beside
    the others. The project-root `tcw-config.yaml` is also not among the YAML-scan
    roots, so nothing else would catch it.
    """
    store_cls = {"taxonomy": FsTaxonomyStore,
                 "capabilities": FsCapabilitiesStore}[comp]
    try:
        store = store_cls.open(project_root)
        # Inside the guard too: a check can open another store on the way — the
        # capabilities check opens the taxonomy — and that one can fail as well.
        if comp == "capabilities":
            problems = store.check(identifier=identifier)
        else:
            problems = store.check(identifier)
    except ValueError as e:
        return [Finding("error", _config_file(project_root), f"{comp}: {e}")]
    return problems


def _target_roots(project_root: Path, target: ValidationTarget) -> list[Path]:
    """Resolve a taxonomy or capabilities target through the filesystem
    adapter's private view."""
    if target.axis == "taxonomy":
        store = FsTaxonomyStore.open(project_root)
    elif target.axis == "capabilities":
        store = FsCapabilitiesStore.open(project_root)
    else:
        raise ValueError(f"validate cannot target the {target.axis!r} axis")
    return store._validation_resources(target.ref)


def _file_findings(project_root: Path, roots: list[Path]) -> tuple[list[Finding], bool]:
    """(a) and (b) over `roots`: YAML well-formedness, and `tcw://` links.
    Also whether a YAML problem was found that the component checks would
    raise on re-reading."""
    problems: list[Finding] = []
    yaml_syntax_error = False
    # (a) YAML well-formedness, and the shape of the files TCW writes
    #
    # Parsed here rather than through `load_yaml`, because this loop must keep
    # accepting *any* shape: an attachment may hold whatever its author wanted. `load_yaml`'s
    # mapping contract belongs to the records TCW owns, and this is where those
    # are held to it — by name, from `OWNED_YAML_NAMES`.
    #
    # This is the half that makes a corrupt record visible at all. The store
    # deliberately degrades one to empty rather than crashing the board, so
    # without a report here an item whose state file is not a state file reads
    # as healthy everywhere.
    work_root = _work_root(project_root)
    for root in roots:
        for f in _iter(root, "*.yaml"):
            if f.name == "item.yaml" and work_root is not None \
                    and _under(f.resolve(), work_root):
                # The work checks read every `item.yaml` and report one that
                # cannot be read with its file and key; a second line here
                # would only repeat it.
                continue
            text, unreadable = _read_text(f)
            if unreadable is not None:
                problems.append(Finding("error", _rel(f, project_root), unreadable))
                # The component checks would re-read it and fail the same way.
                yaml_syntax_error = True
                continue
            try:
                data = _load_named_yaml(text, f, _UniqueKeyLoader)
            except yaml.YAMLError as e:
                problems.append(Finding("error", _rel(f, project_root), str(e)))
                if isinstance(e, yaml.MarkedYAMLError):   # real syntax error, not dup-key
                    yaml_syntax_error = True
                continue
            if f.name in OWNED_YAML_NAMES and data is not None and not isinstance(data, dict):
                problems.append(Finding("error", _rel(f, project_root),
                                        f"expected a mapping, found "
                                        f"{type(data).__name__}"))
                # Same reason a syntax error skips (c): the component check
                # re-reads this file through `load_yaml`, which now raises on it.
                yaml_syntax_error = True

    # (b) tcw:// link resolution
    for root in roots:
        for f in _iter(root, "*.md"):
            raw, unreadable = _read_text(f)
            if unreadable is not None:
                problems.append(Finding("error", _rel(f, project_root), unreadable))
                continue
            text = _strip_code(raw)
            for m in _LINK_RE.finditer(text):
                uri = m.group(1)
                r = resolve_tcw_ref(project_root, uri)
                if r.ok:
                    continue
                # A project declared but not on this machine is reported and
                # not counted (TCW-70 Design 12.1).
                level, _, why = r.reason.partition("unresolved: ")
                if not level and why:
                    problems.append(Finding("unresolved", _rel(f, project_root),
                                            f"tcw:// {uri} → {why}"))
                else:
                    problems.append(Finding("error", _rel(f, project_root),
                                            f"tcw:// {uri} → {r.reason}"))
    return problems, yaml_syntax_error


def validate(project_root: Path, *, target: ValidationTarget | None = None,
             notes: list[str] | None = None) -> list[Finding]:
    """Every finding for the project ([] = clean). Lines about the run itself
    are appended to `notes` when given."""
    notes = [] if notes is None else notes
    from tcw.store.project import FsProjectRegistry

    graph_problems = FsProjectRegistry.open(project_root).check()
    if graph_problems:
        return graph_problems
    registry = FsProjectRegistry.open(project_root).require_valid()
    # Over the projects this checkout can open. A partial graph makes this scan
    # narrower, never wrong: it can miss a collision a complete checkout would
    # catch, and cannot invent one. The unreachable edges themselves are reported
    # by `tcw validate`'s caller, so they are not silently dropped here.
    shared = _shared_work_paths(registry)
    if shared:
        return shared
    if target is not None and target.axis == "work":
        return _work_target_findings(project_root, registry, target)
    trees = _tree_roots(project_root) if target is None else {}
    if target is not None:
        roots = _target_roots(project_root, target)
        if not roots:
            return [Finding("error", target.ref, f"no such {target.axis} object")]
    else:
        roots = [r for r in _scan_roots(project_root, trees) if r.exists()]
    problems, yaml_syntax_error = _file_findings(project_root, roots)

    # (c) component checks — skipped when (a) found a file they'd re-raise on
    if yaml_syntax_error:
        notes.append("taxonomy and capabilities checks skipped: a YAML problem "
                     "above stops them")
    else:
        # Every tree store, one that cannot open included, so `_run_check`
        # says why. The work store is not among them: its checks are (e).
        components = [target.axis] if target is not None else list(trees)
        for comp in components:
            # Before the component's own check, so a project reads "your path is
            # broken" ahead of whatever the store it fell back to has to say.
            configured = _configured_path_problem(project_root, comp)
            if configured is not None:
                problems.append(Finding("error", _config_file(project_root),
                                        f"{comp}.path: {configured}"))
            problems += _run_check(project_root, comp, target.ref if target else None)

    # (d) With the component checks skipped by a YAML problem, each tree store
    # still says whether it can open and whether a pre-2.5.0 store config is
    # left in it. Only that much: a migration message that malformed YAML
    # elsewhere could hide would be found only after fixing something unrelated.
    if yaml_syntax_error and target is None:
        for comp, root in trees.items():
            if isinstance(root, ValueError):
                problems.append(Finding("error", _config_file(project_root),
                                        f"{comp}: {root}"))
                continue
            store = STORE_CLASSES[comp].open(project_root)
            problems += store._legacy_config_problems()

    # (e) The work checks. Not skipped after a YAML problem: they read only the
    # work store, and an unreadable item is one of their own findings.
    if target is None and _checks_work(project_root):
        findings, note = _work_findings(project_root, registry)
        problems += findings
        if note is not None:
            notes.append(note)

    return problems


# ---------------------------------------------------------------------------
# The work checks (TCW-70 Design 10.1).


def _names_folder(finding: Finding, work_path: Path, name: str) -> bool:
    """Whether a finding located at the work store itself is about the folder
    `name`: Jira mode's "the key X names N folders: a, b" lists them after
    its last colon."""
    if Path(finding.where) != work_path:
        return False
    return name in finding.message.rsplit(": ", 1)[-1].split(", ")


def _work_target_findings(project_root: Path, registry,
                          target: ValidationTarget) -> list[Finding]:
    """The checks of one work item that need no network in either mode
    (TCW-73 Design 6.4): YAML and `tcw://` links over its folder, the
    backend's offline check of that folder, and an invalid latest round.

    Two checks need the item's stage or links: the records check on its
    `capabilities.yaml` (when the stage is not terminal) and its `parent` and
    `blocked-by` within this project. They use `target.item` when given; in
    filesystem mode they read `item.yaml` otherwise; in Jira mode, with no
    item, they are skipped, so this never contacts Jira. References into
    other projects are left to a full `tcw validate`."""
    from tcw.errors import TcwError
    from tcw.work.fs_backend import FsWorkBackend, work_store_problems
    from tcw.work.gates import project_reader, records_problems
    from tcw.work.jira.backend import JiraBackend, jira_store_problems
    from tcw.work.model import TERMINAL, Slug, stage as table_stage
    from tcw.work.open import open_backend

    config_file = _config_file(project_root)
    try:
        backend = open_backend(project_root)
    except TcwError as error:
        return [Finding("error", config_file, _config_message(error, project_root))]
    folder = Path(backend.work_path) / target.ref
    if "/" in target.ref or target.ref.startswith(".") or not folder.is_dir():
        return [Finding("error", target.ref, "no such work object")]
    # (a) leaves `item.yaml` to the backend's own check, below.
    problems, _ = _file_findings(project_root, [folder])
    if isinstance(backend, JiraBackend):
        store = jira_store_problems(backend.work_path, backend.jira)
    elif isinstance(backend, FsWorkBackend):
        store = work_store_problems(backend.work_path, backend.project, backend.config)
    else:
        store = []
    problems += [p for p in store if _under(Path(p.where), folder)
                 or _names_folder(p, Path(backend.work_path), target.ref)]
    layout = backend.layout
    problems += round_findings(backend.work_path, backend.project, layout,
                               folders={target.ref})

    item = target.item
    if item is None and isinstance(backend, FsWorkBackend):
        try:
            item = backend.read(target.ref)
        except TcwError:
            item = None              # the backend's check above has said why
    if item is None:
        return problems
    if item.stage is not None and table_stage(item.stage).kind != TERMINAL \
            and layout.capabilities_file(item.slug).exists():
        reader = project_reader(project_root, registry)
        problems += [Finding("error", str(layout.capabilities_file(item.slug)), message)
                     for message in records_problems(layout, item.slug, reader,
                                                     finished=False)]
    refs = ([("parent", item.parent)] if item.parent else []) + \
        [("blocked-by", ref) for ref in item.blocked_by]
    for name, ref in refs:
        if ref.project != backend.project:
            continue
        if not (Path(backend.work_path) / ref.folder).is_dir():
            problems.append(Finding("warning", str(layout.item_dir(item.slug) / "item.yaml"),
                                    f"{name} references a missing item, {ref}"))
    return problems


def _work_findings(project_root: Path, registry) -> "tuple[list, str | None]":
    """Every work finding for a filesystem-mode project, and a note for stderr
    naming the files whose references could not be checked, or None.

    Unreadable items do not stop the checks: they come from `read_all`, each
    is one error, and every other check runs over the readable items."""
    from tcw.errors import BackendError
    from tcw.findings import Finding
    from tcw.work.fs_backend import FsWorkBackend, read_all, work_store_problems
    from tcw.work.jira.backend import JiraBackend, jira_store_problems
    from tcw.work.jira.config import connected_block_problems
    from tcw.work.gates import project_reader, records_problems
    from tcw.work.model import TERMINAL, stage as table_stage
    from tcw.work.open import open_backend, reference_resolver
    from tcw.work.references import reference_problems, stage_problems

    config_file = _config_file(project_root)
    blocks = [Finding("error", config_file, str(problem))
              for problem in connected_block_problems(registry.config())]
    try:
        backend = open_backend(project_root)
    except BackendError as error:
        return [Finding("error", config_file, _config_message(error, project_root)), *blocks], None
    if isinstance(backend, JiraBackend):
        # Offline: nothing Jira owns is checked here (TCW-71 Design 9.1).
        # Rounds are files in both modes, so they are checked here too.
        return [*blocks, *jira_store_problems(backend.work_path, backend.jira),
                *round_findings(backend.work_path, backend.project, backend.layout)], None
    if not isinstance(backend, FsWorkBackend):
        return blocks, None
    layout = backend.layout
    findings = [*blocks, *work_store_problems(backend.work_path, backend.project,
                                              backend.config),
                *round_findings(backend.work_path, backend.project, layout)]
    items, unreadable = read_all(backend.work_path, backend.project, backend.enabled)

    def item_file(slug) -> str:
        return str(layout.item_dir(slug) / "item.yaml")

    resolve = reference_resolver(project_root)

    for problem in reference_problems(items, backend.project, resolve):
        findings.append(Finding(problem.level, item_file(problem.slug), problem.message))
    for problem in stage_problems(items, layout):
        findings.append(Finding(problem.level, item_file(problem.slug),
                                f"stage {problem.message}"))
    reader = None
    for item in items:
        if item.stage is None or table_stage(item.stage).kind == TERMINAL:
            continue
        path = layout.capabilities_file(item.slug)
        if not path.exists():
            continue
        if reader is None:
            reader = project_reader(project_root, registry)
        for message in records_problems(layout, item.slug, reader, finished=False):
            findings.append(Finding("error", str(path), message))
    note = None
    if unreadable:
        note = ("references in these files were not checked, because the files "
                "could not be read: " + ", ".join(str(u.path) for u in unreadable))
    return findings, note


def round_findings(work_path: Path, project: str, layout, folders=None) -> list[Finding]:
    """A warning for each verdict stage whose latest round is invalid, naming
    the round file (TCW-73 Design 6.1.7). Older rounds are history and are not
    read. `folders` narrows the check to those item folders' names."""
    from tcw.work.layout import INVALID
    from tcw.work.model import STAGES, Slug

    stages = [s.name for s in STAGES if s.verdict and s.name in layout.enabled]
    work_path = Path(work_path)
    if not stages or not work_path.is_dir():
        return []
    findings = []
    for entry in sorted(work_path.iterdir(), key=lambda p: p.name):
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        if folders is not None and entry.name not in folders:
            continue
        slug = Slug(project, entry.name)
        for name in stages:
            if layout.current_verdict(slug, name) != INVALID:
                continue
            _, latest = layout.latest_round(slug, name)
            findings.append(Finding(
                "warning", str(latest),
                f"the latest {name} round is invalid: its front matter needs "
                f"`verdict: accepted` or `verdict: rejected` and a whole-number "
                f"`judges`, and `tcw work advance` refuses past {name} until it has them"))
    return findings


def _shared_work_paths(registry) -> list[Finding]:
    """Two filesystem-mode projects in the graph whose work paths are the same
    folder, named with both IDs and the path."""
    from tcw.store.fs import SENTINEL, load_config
    from tcw.work.open import work_path

    seen: dict[Path, str] = {}
    for project in [registry.current, *registry.ancestors(), *registry.descendants()]:
        root = Path(project.locator)
        try:
            raw = load_config(root / SENTINEL)
        except ValueError:
            continue
        work = raw.get("work") if isinstance(raw, dict) else None
        if isinstance(work, dict) and work.get("backend", "filesystem") != "filesystem":
            continue
        try:
            path = work_path(root)
        except ValueError:
            continue
        previous = seen.get(path)
        if previous is not None and previous != project.id:
            return [Finding("error", str(root / SENTINEL),
                            f"projects '{previous}' and '{project.id}' resolve "
                            f"to the same work path: {path}")]
        seen[path] = project.id
    return []
