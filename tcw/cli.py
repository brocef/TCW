"""Top-level `tcw` CLI: dispatches `init | taxonomy | capabilities | work`.

Built component groups register their own subparsers; the rest stub to "not yet
implemented" until their phase lands (capabilities = Phase 3, work = Phase 5).
"""

import argparse
import os
import sys
from pathlib import Path

from tcw.cli_suggest import SuggestingParser, attach_index
from tcw.errors import TcwError
from tcw import __version__
from tcw import projects_cli
from tcw.capabilities import cli as capabilities_cli
from tcw.serve import DEFAULT_PORT, serve
from tcw.store.fs import (
    COMPONENTS, SENTINEL, STORE_CLASSES, FsStoreProvisioner,
    declared_repository, find_node_root, git_root, init,
    provisioned_store_root,
)
from tcw.store.base import MultipleMatch
from tcw.store.project import FsProjectRegistry
from tcw.store.yaml_source import load as _load_named_yaml
import yaml
from tcw.taxonomy import cli as taxonomy_cli
from tcw.work import cli as work_cli


# Every component the provisioning verb can serve. This was narrowed to `work`
# while only the work store had an adapter — a taxonomy declaration was cloned
# and then refused for missing work statuses — and widens here together with the
# adapters that make the other two values honest, never ahead of them.
PROVISION_COMPONENTS = COMPONENTS

# Component CLI modules (each exposes NAME and
# add_subparser). All three components are now built.
_BUILT = [taxonomy_cli, capabilities_cli, work_cli]
_STUBBED = [c for c in COMPONENTS if c not in {m.NAME for m in _BUILT}]


def run_init(components: list[str], project_id: str | None = None,
             work_path: str | None = None,
             paths: dict[str, str] | None = None) -> int:
    """Scaffold the named stores under the current directory and mark it a
    project. Prints nothing on stdout; names each file written and folder
    created on stderr (TCW-73 Design 1.7)."""
    from tcw.errors import BackendError, UsageError
    from tcw.output import changed
    root = Path.cwd()
    unknown = [c for c in components if c not in COMPONENTS]
    if unknown:
        raise UsageError(f"unknown axis {', '.join(repr(c) for c in unknown)}; "
                         f"choose from {', '.join(COMPONENTS)}")
    sentinel = root / SENTINEL
    if project_id is None:
        configured = (_load_named_yaml(sentinel.read_text(encoding="utf-8"), sentinel)
                      if sentinel.exists() else {})
        if not isinstance(configured, dict) or not configured.get("id"):
            raise UsageError("a new project needs `--id <project-id>`; IDs are not "
                             "inferred")
    try:
        written = init(
            components, root, project_id,
            Path(work_path).expanduser() if work_path is not None else None,
            {c: Path(p).expanduser() for c, p in (paths or {}).items()})
    # `RuntimeError` too: `Path.expanduser()` raises it for a `~name` naming no
    # user, whether that came from `--path` or from `work.path` in the config.
    except (ValueError, OSError, RuntimeError) as error:
        raise BackendError(str(error)) from None
    changed(written)
    return 0


def run_provision(components: list[str], *, dry_run: bool = False) -> int:
    """Make this node's declared component stores usable here.

    The only command in `tcw` that reaches the network, and it does so only
    because it was asked to. That is the whole security posture of the feature:
    a repository's config can name a URL, so nothing may act on that URL without
    an explicit instruction from the person holding the checkout. The remote is
    printed before it is contacted, for the same reason. Everything it says
    goes to stderr, `--dry-run` included: it has no product (TCW-73 Design
    1.7). A store already here is never fetched into (Design 8.4).
    """
    node_root = find_node_root()
    if node_root is None:
        from tcw.errors import NO_PROJECT, BackendError
        raise BackendError(NO_PROJECT)

    # An override that is present and wrong refuses here too, and it has to be
    # said here rather than left to the registry. Every other command reaches a
    # broken override through `check()`, but this one reads declarations straight
    # from the configs — so without this gate the registry refused the override
    # while `tcw provision` went and cloned a second copy of the very project the
    # override was pointing at. That is the bug the whole feature exists to stop.
    #
    # Deliberately only overrides, not graph problems at large:
    # `_declared_nodes_in_graph` opens the registry without `require_valid` on
    # purpose, because a graph with an unreachable node is the graph this command
    # exists to complete. An override is a declaration the environment made, and
    # a declaration that is present and wrong refuses — the same rule the two
    # blocks below apply to the ones written in files.
    try:
        failed_overrides = [o for o in FsProjectRegistry.open(node_root).overrides()
                            if o.problem is not None]
    except Exception:
        failed_overrides = []
    if failed_overrides:
        for override in failed_overrides:
            print(f"tcw provision: {override.problem}", file=sys.stderr)
        return 1

    declared: list[tuple[str, object]] = []
    problems: list[str] = []
    for component in components:
        declaration, component_problems = declared_repository(node_root, component)
        problems += [f"{SENTINEL}: {p}" for p in component_problems]
        if declaration is not None:
            declared.append((component, declaration))

    # A malformed declaration refuses rather than reading as "nothing declared".
    # Silently doing nothing here would be the worst outcome: the user asked for
    # a store and would be told everything is fine.
    if problems:
        for problem in problems:
            print(f"tcw provision: {problem}", file=sys.stderr)
        return 1

    declared_nodes, node_problems = _declared_nodes_in_graph(node_root)
    # Same rule as a component's: a declaration that is present and wrong
    # refuses, rather than reading as "nothing declared" and reporting success.
    if node_problems:
        for problem in node_problems:
            print(f"tcw provision: {problem}", file=sys.stderr)
        return 1
    if not declared and not declared_nodes:
        print(f"Nothing to provision: no component or connected project declares "
              f"a home repository in {SENTINEL}.", file=sys.stderr)
        return 0

    failed = False
    for component, declaration in declared:
        provisioner = FsStoreProvisioner(node_root, component, declaration)
        declared_available = provisioner.is_available()
        if not declared_available:
            try:
                # *This* component's store. Asking the work store here was
                # correct only while the loop had one component to run: with
                # more, a taxonomy declaration was measured against whether the
                # work store resolved, and would be cloned because it did not.
                resolved = STORE_CLASSES[component].open(node_root)
            except ValueError:
                pass
            else:
                print(f"  {component}: already available at {resolved.root}", file=sys.stderr)
                continue
        if not declared_available:
            print(f"→ {provisioner.describe()}", file=sys.stderr)      # says what it will contact
        try:
            result = provisioner.ensure_available(dry_run=dry_run)
        except (ValueError, OSError) as error:
            print(f"tcw provision: {error}", file=sys.stderr)
            failed = True
            continue
        print(f"  {result.detail}", file=sys.stderr)
    if _provision_nodes(node_root, dry_run=dry_run):
        failed = True
    return 1 if failed else 0


def _declared_nodes_in_graph(
    root: Path, seen: set[Path] | None = None
) -> tuple[list[tuple[Path, str, object]], list[str]]:
    """Declarations on `root` and on every node reachable from it here.

    Not just the node the command was run in: a declaration lives on whichever
    node knows about that edge, which in a monorepo is routinely a sibling
    package rather than the one the user happens to be standing in. Walking the
    present graph is what makes "declarations follow the graph" true from
    anywhere in it.

    The registry is opened without `require_valid`, deliberately — a graph with
    an unreachable node is exactly the graph this command exists to complete, and
    refusing to read it would be circular.
    """
    from tcw.store.fs import declared_connected_projects

    seen = set() if seen is None else seen
    roots = [root]
    try:
        # Every project the registry holds, not `ancestors + descendants`. That
        # triple omits a sibling and a sibling of an ancestor — the shapes a
        # workspace is actually made of — so a declaration living on one was
        # never read, and the repository it named never obtained. Except an
        # upstream: what it connects to is its own to obtain, not its readers'.
        registry = FsProjectRegistry.open(root)
        roots += [Path(project.locator) for project in registry.projects()
                  if registry.read_only_reason(project.id) is None]
    except Exception:
        pass
    found: list[tuple[Path, str, object, str]] = []
    problems: list[str] = []
    for candidate in roots:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        declared, candidate_problems = declared_connected_projects(candidate)
        problems += [f"{candidate / SENTINEL}: {p}" for p in candidate_problems]
        found += [(candidate, pid, d, relation) for pid, d, relation in declared]
    return found, problems


def _provision_nodes(node_root: Path, *, dry_run: bool) -> bool:
    """Obtain the connected projects this node declares, and the ones they
    declare. Returns True if anything failed.

    **Transitive on purpose, and this is the one place a URL the user did not
    write can be contacted.** A node obtained here may declare others, and that
    is what lets declarations stay where the knowledge is: a repository names
    only its own edges, and never has to know about a project two hops away.
    The safeguard is not to refuse it but to make it visible — every remote is
    printed before it is contacted, transitive ones included, and `--dry-run`
    walks the whole queue without touching the network. A consent prompt would
    be worse than useless: `tcw` is non-interactive by contract, and every
    script calling `tcw provision` would hang on it.

    The walk terminates on the resolved checkout path, which is keyed on
    (url, ref), so a cycle among declarations revisits nothing and two entries
    naming one repository share one working copy.
    """
    from tcw.store.fs import NODE_TARGET

    failed = False
    seen: set[Path] = set()
    queue: list[tuple[Path, str, object, str]] = []
    # "A project that is already here always wins" is the rule the whole feature
    # rests on, and the walk is the one place it was not applied: a declaration
    # is written by whichever node knows about that edge, so an ancestor
    # routinely declares where a project comes from that the *caller* is standing
    # inside, or beside. Taking that at face value re-cloned repositories the
    # user already had.
    #
    # The registry is asked directly rather than reconstructed from a chosen set
    # of relations. An earlier version enumerated current/ancestors/descendants
    # and missed a sibling of an ancestor — which is what a workspace looks like,
    # and meant a machine holding every repository still planned a clone.
    # Identity is the id; the registry rejects duplicates, so this inherits that
    # guarantee.
    starting_registry = None
    try:
        starting_registry = FsProjectRegistry.open(node_root)
    except Exception:
        pass
    # Obtained during *this* run, so not in a registry read before they existed.
    have: set[str] = set()

    def resolved_outside(project_id: str, target: Path) -> "Path | None":
        """Whether the graph already resolves this project somewhere other than
        the copy this declaration would create.

        A project resolved somewhere else is a checkout the user has, and
        obtaining one anyway puts a second project in the graph under a single
        id, which `require_valid` then rejects as a duplicate.
        """
        if starting_registry is None:
            return None
        try:
            project = starting_registry.get(project_id)
        except Exception:
            return None
        if project is None:
            return None
        try:
            located = Path(project.locator).resolve()
        except Exception:                       # an unresolvable locator: not it
            return None
        return located if located != target.resolve() else None

    def enqueue(root: Path, relation: str = "children") -> None:
        nonlocal failed
        if relation == "upstream":
            # Obtained so it can be read; its own connections are not followed,
            # as the registry does not follow them. A reader must never fetch a
            # project named only by something it reads — a public upstream can
            # still name the private repository it is migrating away from.
            return
        found, problems = _declared_nodes_in_graph(root, enqueued)
        for problem in problems:
            print(f"tcw provision: {problem}", file=sys.stderr)
        # Counted, not merely printed. The same malformed declaration exits 1 on
        # the starting graph and used to exit 0 on a node obtained during the
        # walk, so a CI step gated on `tcw provision` read the second as success.
        # A declaration that is present and wrong is present and wrong wherever
        # it was found.
        failed = failed or bool(problems)
        queue.extend(found)

    enqueued: set[Path] = set()
    enqueue(node_root)
    while queue:
        source, project_id, declaration, relation = queue.pop(0)
        target = provisioned_store_root(source, declaration)
        if target in seen:
            continue
        seen.add(target)
        if project_id in have:
            # Obtained or confirmed earlier in this same run.
            print(f"  {project_id}: already available", file=sys.stderr)
            continue
        if (present := resolved_outside(project_id, target)) is not None:
            # A checkout of this project that is not the copy this declaration
            # would create — including, routinely, the one the command is being
            # run from. No location claimed: it may be in the working checkout
            # or in a copy provisioned earlier, and both mean "do not fetch".
            #
            # Still enqueued. Not fetching a project is no reason to stop
            # reading it: its own declarations are how the walk reaches anything
            # beyond it, and skipping them made a repository disappear from
            # provisioning precisely when an earlier one was already in place.
            print(f"  {project_id}: already available", file=sys.stderr)
            have.add(project_id)
            enqueue(present, relation)
            continue
        provisioner = FsStoreProvisioner(source, NODE_TARGET, declaration)
        if provisioner.is_available():
            print(f"  {project_id}: already available at {target}", file=sys.stderr)
            have.add(project_id)
            enqueue(target, relation)
            continue
        print(f"→ {project_id}: {provisioner.describe().split(': ', 1)[1]}", file=sys.stderr)
        try:
            result = provisioner.ensure_available(dry_run=dry_run)
        except (ValueError, OSError) as error:
            print(f"tcw provision: {error}", file=sys.stderr)
            failed = True
            continue
        print(f"  {project_id}: {result.detail.split(': ', 1)[1]}", file=sys.stderr)
        if dry_run:
            # Its own declarations live in a config we have not fetched, so
            # saying nothing here would imply there are none. Say what is
            # actually true instead.
            print(f"  {project_id}: any projects it declares cannot be listed "
                  f"until it is obtained", file=sys.stderr)
            continue
        # After the dry-run return, never before it: recording a *planned*
        # obtain as available made a second declaration of the same project —
        # routine when a parent and a grandparent both name it — report
        # "already available" in a run that fetched nothing.
        have.add(project_id)
        enqueue(target, relation)
    return failed


def _cmd_provision(args: argparse.Namespace) -> int:
    return run_provision(args.component or list(PROVISION_COMPONENTS),
                         dry_run=args.dry_run)


def _cmd_init(args: argparse.Namespace) -> int:
    return run_init(
        args.components or list(COMPONENTS), args.id, args.work_path,
        {c: getattr(args, f"{c}_path") for c in ("taxonomy", "capabilities")
         if getattr(args, f"{c}_path", None) is not None})


def _not_yet(name: str):
    def run(args: argparse.Namespace) -> int:
        print(f"tcw {name}: not yet implemented.", file=sys.stderr)
        return 1
    return run


def _cmd_validate(args: argparse.Namespace) -> int:
    """Findings on stdout, one per line; overrides in effect, what was skipped
    and the closing count on stderr (TCW-73 Design 6). Exit 1 with any error,
    5 when `--remote` could not reach Jira, else 0."""
    from tcw.errors import NO_PROJECT, BackendError, UsageError
    from tcw.findings import Finding
    from tcw.validate import validate
    node_root = find_node_root()
    if node_root is None:
        raise BackendError(NO_PROJECT)
    if args.remote and not _jira_mode(node_root):
        raise UsageError("--remote checks a Jira-mode project, and this project's "
                         "work.backend is filesystem")
    registry = FsProjectRegistry.open(node_root)
    # An override is set in an environment rather than in any file this
    # checkout holds, so a graph that resolves because of one resolves for a
    # reason no reader can grep. Narration, never a finding: an override is a
    # statement about this machine, not a defect. Said first, because a graph
    # problem below ends the run.
    for override in registry.overrides():
        print(f"connected project '{override.id}' is overridden by "
              f"{override.source} to {override.locator}", file=sys.stderr)
        if override.warning:
            print(f"  warning: {override.warning}", file=sys.stderr)
    graph = registry.check()
    if graph:
        return _report(graph)
    findings: list[Finding] = []
    for absent in registry.unreachable():
        if absent.declaration is not None:
            message = (f"connected project '{absent.id}' is declared in "
                       f"{absent.declaration.url} but has not been provisioned "
                       f"here; run `tcw provision` to obtain it")
        else:
            message = (f"connected project '{absent.id}' is declared but not "
                       f"reachable in this checkout ({absent.locator})")
        findings.append(Finding("unresolved", str(absent.declared_in), message))
    # A locator that does not resolve here, for a project that is here: a typo,
    # or a locator right for another machine. Both facts, no conclusion.
    for entry in registry.misdirected():
        findings.append(Finding(
            "warning", str(entry.declared_in),
            f"connected project '{entry.id}' is declared at {entry.locator}, which "
            f"is not in this checkout; it was found at {registry.get(entry.id).locator}"))
    for warning in registry.warnings():
        findings.append(Finding("warning", SENTINEL, warning))
    notes: list[str] = []
    findings += validate(node_root, notes=notes)
    for note in notes:
        print(note, file=sys.stderr)
    if args.remote:
        remote, unreachable = _validate_remote(node_root)
        findings += remote
        code = _report(findings)
        return 5 if unreachable else code
    return _report(findings)


def _report(findings) -> int:
    """Print each finding on stdout and the closing count on stderr; 1 when
    any is an error."""
    counts = {"error": 0, "warning": 0, "unresolved": 0}
    for finding in findings:
        print(finding)
        counts[finding.severity] += 1
    plural = {"error": "errors", "warning": "warnings", "unresolved": "unresolved"}
    print(", ".join(f"{n} {name if n == 1 else plural[name]}"
                    for name, n in counts.items()), file=sys.stderr)
    return 1 if counts["error"] else 0


def _jira_mode(project_root: Path) -> bool:
    from tcw.errors import TcwError
    from tcw.work.open import read_work_config
    try:
        return read_work_config(project_root).backend == "jira"
    except (TcwError, ValueError):
        return False


def _validate_remote(root: Path):
    """The remote checks of this Jira-mode project (TCW-71 Design 9.2; TCW-73
    Design 6.1): its findings, and whether Jira could not be reached. What
    passed or was skipped goes to stderr."""
    from tcw.errors import TcwError
    from tcw.work.gates import project_reader
    from tcw.work.jira.backend import JiraBackend
    from tcw.work.jira.remote import remote_findings
    from tcw.work.open import open_backend, reference_resolver
    try:
        backend = open_backend(root)
    except TcwError:
        return [], False             # the offline checks have reported it
    if not isinstance(backend, JiraBackend):
        return [], False
    reader = project_reader(root, FsProjectRegistry.open(root))
    findings, narration = remote_findings(backend, backend.layout, reader,
                                          reference_resolver(root))
    for line in narration:
        print(line, file=sys.stderr)
    # `remote_findings` reports Jira out of reach as one `unresolved` finding
    # located at the project itself; every other finding names a slug or a key.
    unreachable = any(f.severity == "unresolved" and f.where == backend.project
                      for f in findings)
    return findings, unreachable


def _cmd_serve(args: argparse.Namespace) -> int:
    # Descendant node boards are aggregated by default (like
    # `tcw work list --include-descendants`).
    node_root = find_node_root()
    if node_root is None:
        from tcw.errors import NO_PROJECT, BackendError
        raise BackendError(NO_PROJECT)
    FsProjectRegistry.open(node_root).require_valid()
    return serve(port=args.port, open_browser=not args.no_open,
                 include_descendants=True)


def build_parser() -> argparse.ArgumentParser:
    from tcw.cli_help import EXIT_CODES, command
    parser = SuggestingParser(prog="tcw", description="Taxonomy · Capabilities · Work.",
                              epilog=EXIT_CODES,
                              formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"tcw {__version__}")
    sub = parser.add_subparsers(dest="group", required=True)

    p_init = command(
        sub, "init", help="make this folder a TCW project, with the named stores",
        prints="nothing", writes="tcw-config.yaml and each store's folder, each "
        "named on stderr",
        examples=["init --id my-app", "init work --id my-app --work-path ../board"])
    p_init.add_argument("components", nargs="*", metavar="axis",
                        help=f"any of: {', '.join(COMPONENTS)} (default: all)")
    p_init.add_argument("--id", help="the project's ID; required for a new project")
    p_init.add_argument("--work-path", help="where the work store lives")
    p_init.add_argument("--taxonomy-path", help="where the taxonomy store lives")
    p_init.add_argument("--capabilities-path", help="where the capabilities store lives")
    p_init.set_defaults(func=_cmd_init)

    p_provision = command(
        sub, "provision", help="obtain the stores and projects this project declares "
        "but does not have here",
        prints="nothing; its plan and every remote, before it is contacted, on stderr",
        writes="a clone of each declared repository that is missing",
        examples=["provision", "provision --component work --dry-run"])
    p_provision.add_argument(
        "--component", action="append", choices=list(PROVISION_COMPONENTS),
        help="only this axis's store; repeat for more (default: every declared one)")
    p_provision.add_argument("--dry-run", action="store_true",
                             help="print the plan; contact nothing")
    p_provision.set_defaults(func=_cmd_provision)

    p_validate = command(
        sub, "validate", help="check this project's files, stores and work items",
        prints="one finding per line, `<severity>: <where>: <message>`; nothing "
        "when clean", writes="nothing",
        examples=["validate", "validate --remote"])
    p_validate.add_argument(
        "--remote", action="store_true",
        help="also check this Jira-mode project against Jira itself (reads only)",
    )
    p_validate.set_defaults(func=_cmd_validate)

    p_serve = command(sub, "serve", help="serve a local web viewer",
                      prints="the URL", writes="what the viewer saves",
                      examples=["serve", "serve --port 8123 --no-open"])
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT,
                         help=f"loopback port to bind (default: {DEFAULT_PORT})")
    p_serve.add_argument("--no-open", action="store_true",
                         help="do not open a browser")
    p_serve.set_defaults(func=_cmd_serve)

    projects_cli.add_subparser(sub)
    for mod in _BUILT:
        mod.add_subparser(sub)
    for name in _STUBBED:
        p = sub.add_parser(name, help=f"{name} commands (not yet implemented)")
        p.set_defaults(func=_not_yet(name))

    attach_index(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    command = getattr(args, "_command", "tcw")
    try:
        return args.func(args)
    except TcwError as error:
        # A failure after something was created still names it, on stdout
        # exactly as success would (Design 1.8).
        if error.name:
            print(error.name)
        print(f"{command}: {error}", file=sys.stderr)
        return error.code
    except (ValueError, MultipleMatch) as error:
        # A fault that reached here unclassified, not an answer: exit 1.
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    except yaml.YAMLError as error:
        # A malformed YAML file is the user's, not a bug in TCW, so it reads as
        # a message rather than a traceback. The loader's message names the
        # file (`tcw.store.yaml_source.load`).
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        # Whoever read stdout stopped reading (`tcw work list | head -1`).
        # Nothing to say about it: point stdout at the null device so the
        # interpreter's own flush at exit cannot fail a second time, and exit
        # 1 as Python's documentation on SIGPIPE recommends.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass                       # stdout is not a file descriptor here
        return 1
    except OSError as error:
        # A file TCW could not read or write — permissions, a full disk, a
        # path that vanished — is reported in one line, not as a traceback.
        print(f"{command}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
