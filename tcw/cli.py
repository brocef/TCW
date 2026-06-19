"""Top-level `tcw` CLI: dispatches `init | taxonomy | capabilities | work`.

Component groups stub to "not yet implemented" until their phase lands
(taxonomy = Phase 2, capabilities = Phase 3, work = Phase 5).
"""
from __future__ import annotations

import argparse
import sys

from tcw import __version__
from tcw.store.fs import COMPONENTS, git_root, init


def _cmd_init(args: argparse.Namespace) -> int:
    root = git_root()
    if root is None:
        print("tcw init: not inside a git repository. Run `git init` first.", file=sys.stderr)
        return 1
    components = args.components or list(COMPONENTS)
    unknown = [c for c in components if c not in COMPONENTS]
    if unknown:
        print(f"tcw init: unknown component(s): {', '.join(unknown)}. "
              f"Choose from: {', '.join(COMPONENTS)}.", file=sys.stderr)
        return 2
    created = init(components, root)
    print(f"Scaffolded {len(created)} dir(s) under {root / 'docs'}:")
    for p in created:
        print(f"  {p.relative_to(root)}")
    return 0


def _not_yet(name: str):
    def run(args: argparse.Namespace) -> int:
        print(f"tcw {name}: not yet implemented.", file=sys.stderr)
        return 1
    return run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tcw", description="Taxonomy · Capabilities · Work.")
    parser.add_argument("--version", action="version", version=f"tcw {__version__}")
    sub = parser.add_subparsers(dest="group", required=True)

    p_init = sub.add_parser("init", help="scaffold component doc trees in this git repo")
    p_init.add_argument("components", nargs="*",
                        help=f"any of: {', '.join(COMPONENTS)} (default: all)")
    p_init.set_defaults(func=_cmd_init)

    for name in COMPONENTS:
        p = sub.add_parser(name, help=f"{name} commands (not yet implemented)")
        p.set_defaults(func=_not_yet(name))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
