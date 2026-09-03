"""Top-level `tcw` CLI: dispatches `init | taxonomy | capabilities | work`.

Built component groups register their own subparsers; the rest stub to "not yet
implemented" until their phase lands (capabilities = Phase 3, work = Phase 5).
"""

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

from tcw import __version__
from tcw.capabilities import cli as capabilities_cli
from tcw.serve import DEFAULT_PORT, serve
from tcw.store.fs import (
    COMPONENTS, NOT_A_REPOSITORY, SENTINEL, STORE_CLASSES, FsStoreProvisioner,
    FsWorkStore, declared_repository, find_node_root, git_root, init,
)
from tcw.store.project import FsProjectRegistry
import yaml
from tcw.taxonomy import cli as taxonomy_cli
from tcw.work import cli as work_cli


# Every component the provisioning verb can serve. This was narrowed to `work`
# while only the work store had an adapter — a taxonomy declaration was cloned
# and then refused for missing work statuses — and widens here together with the
# adapters that make the other two values honest, never ahead of them.
PROVISION_COMPONENTS = COMPONENTS

# Component CLI modules (each exposes NAME / SUBCOMMANDS / DEFAULT_SUBCOMMAND /
# add_subparser). All three components are now built.
_BUILT = [taxonomy_cli, capabilities_cli, work_cli]
_STUBBED = [c for c in COMPONENTS if c not in {m.NAME for m in _BUILT}]


def run_init(components: list[str], project_id: str | None = None,
             work_path: str | None = None,
             paths: dict[str, str] | None = None) -> int:
    """Scaffold `docs/<component>/` trees under the current directory, mark it a
    node, and report. Shared by `tcw init` and each `tcw <component> init`."""
    root = Path.cwd()
    if git_root(root) is None:                 # returns the repo root for any dir inside it
        # Checked here rather than in the store, because init runs before one
        # exists. The wording is the store's, so every write says the same thing.
        print(f"tcw init: {NOT_A_REPOSITORY}", file=sys.stderr)
        return 1
    unknown = [c for c in components if c not in COMPONENTS]
    if unknown:
        print(f"tcw init: unknown component(s): {', '.join(unknown)}. "
              f"Choose from: {', '.join(COMPONENTS)}.", file=sys.stderr)
        return 2
    sentinel = root / SENTINEL
    if project_id is None:
        try:
            configured = yaml.safe_load(sentinel.read_text(encoding="utf-8")) if sentinel.exists() else {}
        except yaml.YAMLError as error:
            print(f"tcw init: invalid {SENTINEL}: {error}", file=sys.stderr)
            return 1
        if not isinstance(configured, dict) or not configured.get("id"):
            print(
                "tcw init: new or legacy TCW nodes require `--id <project-id>`; "
                "IDs are not inferred",
                file=sys.stderr,
            )
            return 1
    try:
        created = init(
            components, root, project_id,
            Path(work_path).expanduser() if work_path is not None else None,
            {c: Path(p).expanduser() for c, p in (paths or {}).items()})
    except (ValueError, OSError) as error:
        print(f"tcw init: {error}", file=sys.stderr)
        return 1
    print(f"Scaffolded {len(created)} dir(s):")
    for p in created:
        try:
            shown = p.relative_to(root)
        except ValueError:
            shown = p
        print(f"  {shown}")
    print(f"Node marker: {SENTINEL}")          # deterministic across runs
    if "work" in components:
        print(".gitignore: resolved work (completed/, discarded/) stays on disk, "
              "out of the tracked tree")
    return 0


def run_provision(components: list[str], *, refresh: bool = False,
                  dry_run: bool = False) -> int:
    """Make this node's declared component stores usable here.

    The only command in `tcw` that reaches the network, and it does so only
    because it was asked to. That is the whole security posture of the feature:
    a repository's config can name a URL, so nothing may act on that URL without
    an explicit instruction from the person holding the checkout. The remote is
    printed before it is contacted, for the same reason.
    """
    node_root = find_node_root()
    if node_root is None:
        print("tcw provision: no tcw node here — run `tcw init` in the project folder.",
              file=sys.stderr)
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

    if not declared:
        print(f"Nothing to provision: no component declares a home repository "
              f"in {SENTINEL}.")
        return 0

    failed = False
    for component, declaration in declared:
        provisioner = FsStoreProvisioner(node_root, component, declaration)
        declared_available = provisioner.is_available()
        if not refresh and not declared_available:
            try:
                # *This* component's store. Asking `FsWorkStore` here was
                # correct only while the loop had one component to run: with
                # more, a taxonomy declaration was measured against whether the
                # work store resolved, and would be cloned because it did not.
                resolved = STORE_CLASSES[component].open(node_root)
            except ValueError:
                pass
            else:
                print(f"  {component}: already available at {resolved.root}")
                continue
        if not declared_available or refresh:
            print(f"→ {provisioner.describe()}")      # says what it will contact
        try:
            result = provisioner.ensure_available(refresh=refresh, dry_run=dry_run)
        except (ValueError, OSError) as error:
            print(f"tcw provision: {error}", file=sys.stderr)
            failed = True
            continue
        print(f"  {result.detail}")
    return 1 if failed else 0


def _cmd_provision(args: argparse.Namespace) -> int:
    return run_provision(args.component or list(PROVISION_COMPONENTS),
                         refresh=args.refresh, dry_run=args.dry_run)


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
    node_root = find_node_root()
    if node_root is None:
        print("tcw validate: no tcw node here — run `tcw init` in the project folder.",
              file=sys.stderr)
        return 1
    registry = FsProjectRegistry.open(node_root)
    registry_problems = registry.check()
    if registry_problems:
        for problem in registry_problems:
            print(problem, file=sys.stderr)
        print(f"{len(registry_problems)} project graph problem(s).", file=sys.stderr)
        return 1
    # Reported, never counted, and never fatal. These are declarations this
    # checkout cannot follow, not defects — but they are also how a genuine typo
    # in a locator now surfaces, so they are printed every run rather than
    # behind a flag.
    for absent in registry.unreachable():
        print(f"{absent.declared_in}: connected project '{absent.id}' is declared "
              f"but not reachable in this checkout ({absent.locator})",
              file=sys.stderr)
    from tcw.validate import validate
    recurse = args.path is None and not args.no_recurse
    projects = [registry.current, *registry.descendants()] if recurse else [registry.current]
    problems: list[str] = []
    for project in projects:
        project_problems = validate(Path(project.locator), args.path)
        if len(projects) > 1:
            project_problems = [f"[{project.id}] {problem}" for problem in project_problems]
        problems.extend(project_problems)
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s).", file=sys.stderr)
        return 1
    print("validate OK")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    # Descendant node boards are aggregated by default (like
    # `tcw work list --include-descendants`).
    node_root = find_node_root()
    if node_root is None:
        print("tcw serve: no tcw node here — run `tcw init --id <project-id>`.",
              file=sys.stderr)
        return 1
    FsProjectRegistry.open(node_root).require_valid()
    return serve(port=args.port, open_browser=not args.no_open,
                 include_descendants=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tcw", description="Taxonomy · Capabilities · Work.")
    parser.add_argument("--version", action="version", version=f"tcw {__version__}")
    sub = parser.add_subparsers(dest="group", required=True)

    p_init = sub.add_parser("init", help="scaffold component doc trees in this git repo")
    p_init.add_argument("components", nargs="*",
                        help=f"any of: {', '.join(COMPONENTS)} (default: all)")
    p_init.add_argument("--id", help="canonical project ID (required for new/legacy nodes)")
    p_init.add_argument("--work-path", help="filesystem location for the work store")
    p_init.add_argument("--taxonomy-path",
                        help="filesystem location for the taxonomy store")
    p_init.add_argument("--capabilities-path",
                        help="filesystem location for the capabilities store")
    p_init.set_defaults(func=_cmd_init)

    p_provision = sub.add_parser(
        "provision", help="obtain the work store this project declares but does not have here")
    p_provision.add_argument(
        "--component", action="append", choices=list(PROVISION_COMPONENTS),
        help="limit provisioning by component (default: every declared one)")
    p_provision.add_argument("--refresh", action="store_true",
                             help="bring an existing working copy to the declared version")
    p_provision.add_argument("--dry-run", action="store_true",
                             help="print the plan; contact nothing")
    p_provision.set_defaults(func=_cmd_provision)

    p_validate = sub.add_parser(
        "validate", help="check YAML soundness, tcw:// links, and component integrity")
    p_validate.add_argument("path", nargs="?",
                            help="narrow the active project scan to one file or directory (disables recursion)")
    p_validate.add_argument(
        "--no-recurse", action="store_true",
        help="validate only the active project, excluding registered descendants",
    )
    p_validate.set_defaults(func=_cmd_validate)

    p_serve = sub.add_parser("serve", help="serve a local read-only web viewer")
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT,
                         help=f"loopback port to bind (default: {DEFAULT_PORT})")
    p_serve.add_argument("--no-open", action="store_true",
                         help="do not open a browser automatically")
    p_serve.set_defaults(func=_cmd_serve)

    for mod in _BUILT:
        mod.add_subparser(sub)
    for name in _STUBBED:
        p = sub.add_parser(name, help=f"{name} commands (not yet implemented)")
        p.set_defaults(func=_not_yet(name))

    return parser


def _normalize(argv: list[str]) -> list[str]:
    """Sugar: `tcw <component> <path>` → `tcw <component> show <path>`."""
    if len(argv) >= 2 and not argv[1].startswith("-"):
        for mod in _BUILT:
            default = getattr(mod, "DEFAULT_SUBCOMMAND", None)
            if default and argv[0] == mod.NAME and argv[1] not in mod.SUBCOMMANDS:
                return [argv[0], default, *argv[1:]]
    return argv


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(_normalize(argv))
    try:
        return args.func(args)
    except ValueError as error:
        print(f"tcw: {error}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        # Deliberately generic: the only policy here is "a git subprocess
        # failed", which is true of every component. git's own diagnostic has
        # already reached the terminal — no `check=True` call in the filesystem
        # adapter captures output — so re-printing `error.stderr` would double it.
        # `cmd` is a sequence *or* a string (stdlib contract); joining a string
        # iterates its characters. No shipped raiser passes one, but a handler
        # whose whole justification is that it assumes nothing about its caller
        # cannot assume that either.
        cmd = error.cmd if isinstance(error.cmd, str) else \
            shlex.join(str(a) for a in error.cmd)
        print(f"tcw: git command failed (exit {error.returncode}): {cmd}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
