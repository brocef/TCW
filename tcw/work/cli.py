"""`tcw work` — the changes. Single-node state machine per phase-5-work B.2."""

import argparse
from dataclasses import dataclass, field
import re
import subprocess
import sys
from pathlib import Path

from tcw.store.base import (
    WORK_RESOLUTIONS, IllegalTransition, MultipleMatch, WorkItem,
)
from tcw.store.fs import (
    COMPONENTS, SENTINEL, WORKTREES_DIR, FsWorkStore, add_worktree, child_nodes,
    ensure_worktree_ignored, find_node, git_commit, merge_worktree, parent_node,
    remove_worktree,
)
from tcw.work.recursion import delegate, escalate, reconcile

NAME = "work"
SUBCOMMANDS = {"init", "new", "list", "show", "path", "start", "edit", "complete",
               "drop", "nodes", "reconcile", "delegate", "escalate",
               "audit-work-backlog"}
DEFAULT_SUBCOMMAND = None  # work uses explicit show/path (slugs aren't tree paths)

_ERRORS = (ValueError, IllegalTransition, MultipleMatch)


def _store() -> FsWorkStore | None:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
        return None
    return FsWorkStore.open(node)


def _stdin_body() -> str:
    if sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read()
    except (OSError, ValueError):
        return ""


def _split(val: str | None) -> list[str]:
    """Comma-split a flag value: strip tokens, drop empties (repo idiom)."""
    return [s.strip() for s in (val or "").split(",") if s.strip()]


def _print_item(item: WorkItem) -> None:
    print(f"{item.slug}  [{item.status}]")
    print(f"title: {item.title}")
    if item.parent:
        print(f"parent: {item.parent}")
    if item.type:
        print(f"type: {item.type}")
    if item.initiative:
        print(f"initiative: {item.initiative}")
    if item.phase:
        print(f"phase: {item.phase}")
    if item.priority is not None:
        print(f"priority: {item.priority}")
    if item.resolution:
        print(f"resolution: {item.resolution}")
    if item.blocked_by:
        labels = []
        for b in item.blocked_by:
            if "slug" in b:
                labels.append(b["slug"])
            elif "external" in b:
                labels.append(f"external: {b['external']}")
        if labels:
            print(f"blocked_by: {', '.join(labels)}")
    body = item.body.strip()
    if body:
        print()
        print("\n".join(body.splitlines()[:12]))


def _nodes(args: argparse.Namespace) -> int:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
        return 1
    parent = parent_node(node)
    print(f"node:   {node}")
    print(f"parent: {parent if parent else '(none — root)'}")
    children = child_nodes(node)
    if children:
        print("children:")
        for c in children:
            print(f"  {c.relative_to(node)}")
    else:
        print("children: (none — leaf)")
    return 0


@dataclass
class _AuditFinding:
    slug: str
    recommendation: str
    severity: str
    reason: str
    evidence: list[str] = field(default_factory=list)
    action: str = ""


_LIFECYCLE_ARTIFACTS = (
    "content.md", "initial-request.md", "spec.md", "plan.md", "outcome.md",
    "refined-outcome.md",
)
_AUDIT_ARTIFACTS = _LIFECYCLE_ARTIFACTS[:4]
_AUDIT_NODE_SCAN_SKIP = {
    ".git", ".hg", ".svn", ".worktrees", ".venv", "venv", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", "build", "dist", "plugins",
}
_PATH_REF_RE = re.compile(
    r"(?<![\w/.-])([A-Za-z0-9_./-]+\.(?:py|md|toml|yaml|yml|json|sh))(?::\d+)?"
)


def _words(text: str) -> set[str]:
    stop = {"a", "an", "and", "for", "in", "of", "the", "to", "with"}
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in stop}


def _read_artifacts(st: FsWorkStore, item: WorkItem) -> dict[str, str]:
    d = st.path(item.slug)
    if d is None:
        return {}
    out: dict[str, str] = {}
    for name in _AUDIT_ARTIFACTS:
        p = d / name
        if p.is_file():
            out[name] = p.read_text(encoding="utf-8")
    return out


def _missing_artifact_findings(st: FsWorkStore, item: WorkItem) -> list[_AuditFinding]:
    d = st.path(item.slug)
    if d is None:
        return []
    missing = [name for name in ("initial-request.md", "spec.md", "plan.md")
               if not (d / name).is_file() or not (d / name).read_text(encoding="utf-8").strip()]
    if not missing:
        return []
    return [_AuditFinding(
        item.slug, "revise", "medium", "missing lifecycle planning artifacts",
        [", ".join(missing)], "write or regenerate the missing lifecycle artifacts",
    )]


def _broken_reference_findings(st: FsWorkStore, item: WorkItem,
                               artifacts: dict[str, str]) -> list[_AuditFinding]:
    findings: list[_AuditFinding] = []
    seen: set[str] = set()
    item_dir = st.path(item.slug)
    for name, text in artifacts.items():
        for ref in _PATH_REF_RE.findall(text):
            if ref.startswith(("http", "https")) or ref in seen or ref in _LIFECYCLE_ARTIFACTS:
                continue
            seen.add(ref)
            if not (st.node_root / ref).exists() and not (
                item_dir is not None and (item_dir / ref).exists()
            ):
                findings.append(_AuditFinding(
                    item.slug, "revise", "high", "broken local file reference",
                    [f"{name}: {ref}"], "update or remove the stale reference",
                ))
    return findings


def _duplicate_findings(item: WorkItem, items: list[WorkItem]) -> list[_AuditFinding]:
    item_words = _words(f"{item.title} {item.body}")
    if not item_words:
        return []
    findings: list[_AuditFinding] = []
    for other in items:
        if other.slug == item.slug:
            continue
        other_words = _words(f"{other.title} {other.body}")
        if not other_words:
            continue
        score = len(item_words & other_words) / len(item_words | other_words)
        exact_title = item.title.strip().lower() == other.title.strip().lower()
        if exact_title or score >= 0.65:
            if other.status == "completed":
                recommendation = "complete-as-duplicate"
                severity = "high"
                action = f"compare with completed item {other.slug}"
            else:
                recommendation = "revise"
                severity = "medium"
                action = f"merge, split, or mark duplicate of {other.slug}"
            findings.append(_AuditFinding(
                item.slug, recommendation, severity, "duplicate or overlapping work item",
                [f"{other.status}: {other.slug}"], action,
            ))
            break
    return findings


def _blocker_findings(st: FsWorkStore, item: WorkItem) -> list[_AuditFinding]:
    findings: list[_AuditFinding] = []
    for blocker in item.blocked_by:
        if "external" in blocker:
            label = str(blocker["external"])
            if not re.search(r"\b(owner|by|until|waiting on|ticket|issue|jira)\b", label, re.I):
                findings.append(_AuditFinding(
                    item.slug, "revise", "medium", "external blocker has no next action",
                    [f"external: {label}"], "record owner, wait condition, or follow-up action",
                ))
        elif "slug" in blocker:
            blocked_by = st.get(blocker["slug"])
            if blocked_by is None:
                findings.append(_AuditFinding(
                    item.slug, "revise", "low", "blocker no longer resolves",
                    [blocker["slug"]], "remove the stale blocker reference",
                ))
            elif blocked_by.status == "completed":
                findings.append(_AuditFinding(
                    item.slug, "revise", "low", "blocker is already completed",
                    [blocker["slug"]], "remove the resolved blocker reference",
                ))
    return findings


def _capability_findings(st: FsWorkStore, item: WorkItem) -> list[_AuditFinding]:
    caps = item.capabilities
    if not caps:
        return []
    if isinstance(caps, dict) and caps.get("_tcw_parse_error"):
        return [_AuditFinding(
            item.slug, "revise", "high", "malformed capabilities.yaml",
            [str(caps["_tcw_parse_error"]).splitlines()[0]],
            "repair or remove the malformed capability delta file",
        )]
    if isinstance(caps, dict):
        refs = []
        for values in caps.values():
            if isinstance(values, list):
                refs.extend(str(v).split("#", 1)[0] for v in values if isinstance(v, str))
        broken = [ref for ref in refs if ref and not (st.node_root / "docs" / "capabilities" /
                                                      f"{ref}.md").exists()
                  and not (st.node_root / "docs" / "capabilities" / ref /
                           "capabilities.md").exists()]
        if broken:
            return [_AuditFinding(
                item.slug, "revise", "medium", "capability reference no longer resolves",
                [", ".join(sorted(set(broken)))], "update capabilities.yaml references",
            )]
    elif not isinstance(caps, list):
        return [_AuditFinding(
            item.slug, "revise", "low", "capabilities.yaml has an unexpected shape",
            [type(caps).__name__], "normalize the capability delta file",
        )]
    return []


def _audit_child_nodes(root: Path) -> list[Path]:
    found: list[Path] = []

    def walk(d: Path) -> None:
        for child in sorted(d.iterdir()):
            if child.name in _AUDIT_NODE_SCAN_SKIP or child.is_symlink() or not child.is_dir():
                continue
            if (child / SENTINEL).is_file() and (child / "docs" / "work").is_dir():
                found.append(child)
                continue
            walk(child)

    walk(root)
    return found


def _wrong_node_findings(st: FsWorkStore, item: WorkItem, text: str,
                         node_candidates: list[Path]) -> list[_AuditFinding]:
    findings: list[_AuditFinding] = []
    haystack = f"{item.title}\n{text}".lower()
    for child in node_candidates:
        rel = str(child.relative_to(st.node_root))
        tokens = {rel.lower(), child.name.lower()}
        if any(tok and re.search(rf"\b{re.escape(tok)}\b", haystack) for tok in tokens):
            findings.append(_AuditFinding(
                item.slug, f"move-to-node {rel}", "medium", "item appears to target another TCW node",
                [rel], f"move or split the item into node {rel}",
            ))
            break
    return findings


def _actionability_findings(item: WorkItem, artifacts: dict[str, str]) -> list[_AuditFinding]:
    text = "\n".join(artifacts.values())
    findings: list[_AuditFinding] = []
    if len(_words(item.title)) <= 1:
        findings.append(_AuditFinding(
            item.slug, "revise", "low", "title is too vague",
            [item.title], "rename the item with a concrete outcome",
        ))
    if "acceptance criteria" not in text.lower() and "acceptance" not in text.lower():
        findings.append(_AuditFinding(
            item.slug, "revise", "low", "acceptance criteria are missing",
            ["no acceptance criteria section found"], "add concrete acceptance criteria",
        ))
    if len(text) > 40000:
        findings.append(_AuditFinding(
            item.slug, "split", "medium", "work item artifacts are oversized",
            [f"{len(text)} bytes"], "split the work into smaller items",
        ))
    return findings


def _audit_item(st: FsWorkStore, item: WorkItem, all_items: list[WorkItem],
                node_candidates: list[Path]) -> list[_AuditFinding]:
    artifacts = _read_artifacts(st, item)
    text = "\n".join(artifacts.values())
    findings: list[_AuditFinding] = []
    findings += _duplicate_findings(item, all_items)
    findings += _missing_artifact_findings(st, item)
    findings += _broken_reference_findings(st, item, artifacts)
    findings += _wrong_node_findings(st, item, text, node_candidates)
    findings += _blocker_findings(st, item)
    findings += _capability_findings(st, item)
    findings += _actionability_findings(item, artifacts)
    if not findings:
        findings.append(_AuditFinding(
            item.slug, "keep", "info", "no cleanup findings",
            ["backlog item has readable planning artifacts"], "leave the item in backlog",
        ))
    return findings


def _audit_work_backlog(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        backlog = st.board(status="backlog")
        all_items = st.query()
        node_candidates = _audit_child_nodes(st.node_root)
    except _ERRORS as e:
        print(f"tcw work audit-work-backlog: {e}", file=sys.stderr)
        return 1
    for item in backlog:
        for finding in _audit_item(st, item, all_items, node_candidates):
            print(f"{finding.slug} | {finding.recommendation} | "
                  f"{finding.severity} | {finding.reason}")
            for evidence in finding.evidence:
                print(f"  evidence: {evidence}")
            if finding.action:
                print(f"  action: {finding.action}")
    return 0


def _reconcile(args: argparse.Namespace) -> int:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
        return 1
    try:
        block = reconcile(node, args.slug, commit=args.commit)
    except _ERRORS as e:
        print(f"tcw work reconcile: {e}", file=sys.stderr)
        return 1
    print(block)
    return 0


def _delegate(args: argparse.Namespace) -> int:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
        return 1
    try:
        doc = delegate(node, args.child, args.title, body=_stdin_body(),
                       initiative=args.initiative)
    except _ERRORS as e:
        print(f"tcw work delegate: {e}", file=sys.stderr)
        return 1
    print(doc)
    return 0


def _escalate(args: argparse.Namespace) -> int:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
        return 1
    try:
        doc = escalate(node, args.title, body=_stdin_body(), initiative=args.initiative)
    except _ERRORS as e:
        print(f"tcw work escalate: {e}", file=sys.stderr)
        return 1
    print(doc)
    print("Reminder: start an orchestrator session to triage the parent's inbox.",
          file=sys.stderr)
    return 0


def _init(args: argparse.Namespace) -> int:
    from tcw.cli import run_init      # function-local: top-level cli imports this module
    return run_init([NAME])


def _new(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        item = st.create(args.title, body=_stdin_body(), priority=args.priority,
                         parent=args.parent)
    except _ERRORS as e:
        print(f"tcw work new: {e}", file=sys.stderr)
        return 1
    rc = 0
    try:
        for ref in _split(args.blocked_by):
            st.add_blocker(item.slug, ref)
    except _ERRORS as e:
        print(f"tcw work new: {e}", file=sys.stderr)
        rc = 1
    if args.epic:
        st.set_field(item.slug, "type", "epic")
    if args.initiative:
        st.set_field(item.slug, "initiative", args.initiative)
    print(item.slug)
    body = st.body_path(item.slug)
    if body is not None:
        print(f"→ edit: {body}", file=sys.stderr)
    if not args.epic:                         # epic's next step is delegate, not start
        print(f"→ next: when you begin implementing, run `tcw work start {item.slug}`",
              file=sys.stderr)
    return rc


def _list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    items = st.board(status=args.status)
    if args.status is None and not args.all:
        items = [i for i in items if i.status != "completed"]
    present = {i.slug for i in items}
    by_parent: dict[str, list[WorkItem]] = {}
    for it in items:                              # board order preserved per sibling group
        by_parent.setdefault(it.parent, []).append(it)

    def emit(it: WorkItem, depth: int) -> None:
        blockers = st.unresolved_blockers(it)
        suffix = f" | blocked-by: {', '.join(blockers)}" if blockers else ""
        pri = it.priority if it.priority is not None else "-"
        print(f"{'  ' * depth}{it.slug} | {it.status} | {it.phase or '-'} | "
              f"{pri} | {it.title}{suffix}")
        for ch in by_parent.get(it.slug, []):
            emit(ch, depth + 1)

    for it in items:                              # roots first; children ride their parent
        if it.parent in present:                  # a visible parent will emit it
            continue
        emit(it, 0)
    return 0


def _show(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        item = st.get(args.slug)
    except MultipleMatch as e:
        print(f"tcw work show: {e}", file=sys.stderr)
        return 1
    if item is None:
        print(f"tcw work show: no such work item: {args.slug}", file=sys.stderr)
        return 1
    _print_item(item)
    return 0


def _path(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    p = st.path(args.slug)
    if p is None:
        print(f"tcw work path: no such work item: {args.slug}", file=sys.stderr)
        return 1
    print(p)
    return 0


def _complete_hint(slug: str) -> None:
    print(f"→ next: when done & verified, run "
          f"`tcw work complete {slug} --resolution done --confirm`", file=sys.stderr)


def _start(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        st.start(args.slug, force=args.force)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return 1
    if not args.worktree:
        print(f"started {args.slug}")
        _complete_hint(args.slug)
        return 0
    node = st.node_root
    ensure_worktree_ignored(node)
    st.set_field(args.slug, "worktree", f"{WORKTREES_DIR}/{args.slug}")
    st.set_field(args.slug, "branch", f"work/{args.slug}")
    try:
        git_commit(node, f"tcw work: start {args.slug} (worktree)", "docs/work", ".gitignore")
        wt, _branch = add_worktree(node, args.slug)
    except subprocess.CalledProcessError as e:
        print(f"tcw work start: worktree setup failed: {e.stderr or e}", file=sys.stderr)
        return 1
    print(f"started {args.slug} → worktree {wt}")
    _complete_hint(args.slug)
    return 0


def _edit(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        if st.get(args.slug) is None:
            print(f"tcw work edit: no such work item: {args.slug}", file=sys.stderr)
            return 1
        blocks = _split(args.blocks)
        for ref in blocks:
            if st.get(ref) is None:
                print(f"tcw work edit: no such work item: {ref}", file=sys.stderr)
                return 1
        for ref in _split(args.blocked_by):
            st.add_blocker(args.slug, ref)
        for ref in blocks:
            st.add_blocker(ref, args.slug)
        for ref in _split(args.unblocked_by):
            st.remove_blocker(args.slug, ref)
        if args.initiative is not None:
            st.set_field(args.slug, "initiative", args.initiative)
        if args.priority is not None:
            st.set_field(args.slug, "priority", args.priority)
    except _ERRORS as e:
        print(f"tcw work edit: {e}", file=sys.stderr)
        return 1
    print(f"edited {args.slug}")
    return 0


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
    branch = item.branch or None              # capture before complete moves the folder
    has_worktree = bool(item.worktree)
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
    if has_worktree and branch:                       # merge-back before the rename/teardown
        err = merge_worktree(st.node_root, branch)
        if err:
            print(f"tcw work complete: {err}", file=sys.stderr)
            return 1
    try:
        st.complete(args.slug, args.resolution, dod_ack=checklist, force=args.force)
    except _ERRORS as e:
        print(f"tcw work complete: {e}", file=sys.stderr)
        return 1
    print(f"completed {args.slug} ({args.resolution})")
    if has_worktree:
        for w in remove_worktree(st.node_root, args.slug, branch):
            print(f"tcw work complete: {w}", file=sys.stderr)
    return 0


def _drop(args: argparse.Namespace) -> int:
    return _run(lambda st: st.drop(args.slug), f"dropped {args.slug}")


def _run(op, success: str) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        op(st)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return 1
    print(success)
    return 0


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help="the changes — work items through a state machine")
    g = p.add_subparsers(dest="cmd", required=True)

    g.add_parser("init", help="create docs/work/{inbox,backlog,active,completed}/") \
        .set_defaults(func=_init)

    g.add_parser("nodes", help="list this node's parent + child nodes").set_defaults(func=_nodes)

    pr = g.add_parser("reconcile", help="scan child nodes → write the epic rollup")
    pr.add_argument("slug")
    pr.add_argument("--commit", action="store_true", help="also commit the rollup")
    pr.set_defaults(func=_reconcile)

    pdg = g.add_parser("delegate", help="write a request into a child node's inbox/")
    pdg.add_argument("child", help="child node path (relative to this node)")
    pdg.add_argument("title")
    pdg.add_argument("--initiative", help="stamp the request with an initiative slug")
    pdg.set_defaults(func=_delegate)

    pes = g.add_parser("escalate", help="write a request into the parent node's inbox/")
    pes.add_argument("title")
    pes.add_argument("--initiative", help="stamp the request with an initiative slug")
    pes.set_defaults(func=_escalate)

    pab = g.add_parser(
        "audit-work-backlog",
        help="review backlog items and print cleanup recommendations",
        description="Review backlog items and print cleanup recommendations.",
    )
    pab.set_defaults(func=_audit_work_backlog)

    pn = g.add_parser("new", help="create a backlog item; prints its slug")
    pn.add_argument("title")
    pn.add_argument("--priority", type=int, help="integer priority (higher = higher)")
    pn.add_argument("--blocked-by", help="comma-separated slugs/externals that block it")
    pn.add_argument("--epic", action="store_true", help="mark as an epic (type: epic)")
    pn.add_argument("--parent", help="create as a child nested under this item's slug")
    pn.add_argument("--initiative", help="back-pointer slug to an owning epic")
    pn.set_defaults(func=_new)

    pl = g.add_parser("list", help="the board (hides completed unless --status/--all)")
    pl.add_argument("--status")
    pl.add_argument("--all", action="store_true", help="include completed items")
    pl.set_defaults(func=_list)

    psh = g.add_parser("show", help="resolve slug → item; print state + body")
    psh.add_argument("slug")
    psh.set_defaults(func=_show)

    pp = g.add_parser("path", help="print the current work item folder path")
    pp.add_argument("slug")
    pp.set_defaults(func=_path)

    pst = g.add_parser("start", help="inbox|backlog → active")
    pst.add_argument("slug")
    pst.add_argument("--force", action="store_true", help="start despite unresolved blockers")
    pst.add_argument("--worktree", action="store_true",
                     help="isolate the item in its own git worktree + branch")
    pst.set_defaults(func=_start)

    pe = g.add_parser("edit", help="change blocking links between items")
    pe.add_argument("slug")
    pe.add_argument("--blocked-by", help="comma-separated slugs/externals that block this item")
    pe.add_argument("--blocks", help="comma-separated items this item blocks")
    pe.add_argument("--unblocked-by", help="comma-separated blockers to remove")
    pe.add_argument("--priority", type=int, help="set integer priority (higher = higher)")
    pe.add_argument("--initiative", help='set the owning-epic back-pointer (use "" to clear)')
    pe.set_defaults(func=_edit)

    pc = g.add_parser("complete", help="active → completed (DoD gate)")
    pc.add_argument("slug")
    pc.add_argument("--resolution", required=True, choices=sorted(WORK_RESOLUTIONS))
    pc.add_argument("--confirm", action="store_true")
    pc.add_argument("--force", action="store_true", help="complete despite unresolved blockers")
    pc.set_defaults(func=_complete)

    pd = g.add_parser("drop", help="inbox|backlog → deleted")
    pd.add_argument("slug")
    pd.set_defaults(func=_drop)
