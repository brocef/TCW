"""Top-level `tcw` CLI: dispatches `init | taxonomy | capabilities | work`.

Built component groups register their own subparsers; the rest stub to "not yet
implemented" until their phase lands (capabilities = Phase 3, work = Phase 5).
"""

import argparse
import sys
from pathlib import Path

from tcw import __version__
from tcw.capabilities import cli as capabilities_cli
from tcw.serve import DEFAULT_PORT, serve
from tcw.store.fs import COMPONENTS, SENTINEL, find_node_root, git_root, init
from tcw.store.project import FsProjectRegistry
import yaml
from tcw.taxonomy import cli as taxonomy_cli
from tcw.work import cli as work_cli

# Component CLI modules (each exposes NAME / SUBCOMMANDS / DEFAULT_SUBCOMMAND /
# add_subparser). All three components are now built.
_BUILT = [taxonomy_cli, capabilities_cli, work_cli]
_STUBBED = [c for c in COMPONENTS if c not in {m.NAME for m in _BUILT}]


def run_init(components: list[str], project_id: str | None = None) -> int:
    """Scaffold `docs/<component>/` trees under the current directory, mark it a
    node, and report. Shared by `tcw init` and each `tcw <component> init`."""
    root = Path.cwd()
    if git_root(root) is None:                 # returns the repo root for any dir inside it
        print("tcw init: not inside a git repository. Run `git init` first.", file=sys.stderr)
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
        created = init(components, root, project_id)
    except (ValueError, OSError) as error:
        print(f"tcw init: {error}", file=sys.stderr)
        return 1
    print(f"Scaffolded {len(created)} dir(s) under {root / 'docs'}:")
    for p in created:
        print(f"  {p.relative_to(root)}")
    print(f"Node marker: {SENTINEL}")          # deterministic across runs
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    return run_init(args.components or list(COMPONENTS), args.id)


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
    registry_problems = FsProjectRegistry.open(node_root).check()
    if registry_problems:
        for problem in registry_problems:
            print(problem, file=sys.stderr)
        print(f"{len(registry_problems)} project graph problem(s).", file=sys.stderr)
        return 1
    from tcw.validate import validate
    problems = validate(node_root, args.path)
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
    p_init.set_defaults(func=_cmd_init)

    p_validate = sub.add_parser(
        "validate", help="check YAML soundness, tcw:// links, and component integrity")
    p_validate.add_argument("path", nargs="?",
                            help="narrow the scan to a single file or directory (default: whole node)")
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


if __name__ == "__main__":
    sys.exit(main())
