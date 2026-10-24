"""`tcw taxonomy` — the nouns.

stdout carries each command's product and nothing else (TCW-73 Design 1):
`add` prints the new entry's full identifier, `list` and `search` one full
identifier per line (`<project>.taxonomy/<slug>`, TCW-110 Design 4), `show`
the record, `path` the store folder; `rm` prints nothing. Every file a write
changed is named on stderr, and so is each warning about the project's view
(TCW-112 Design 3.2). A failure is raised for the top-level handler to print
and turn into its exit code.
"""

import argparse

from tcw import exit as codes
from tcw.cli_help import command, group
from tcw.errors import BackendError, InheritedUnavailable, UsageError
from tcw.locate import find_tree_writable
from tcw.output import changed, own_only, print_json, say
from tcw.scope import scope_options
from tcw.tree_scope import (LEFT_OUT, active_store, covered_for, print_rows, refuse_local,
                            scope_keys, show_lines, show_row, term_detail)
from tcw.stdin import read_piped_stdin
from tcw.store.base import NotASlug
from tcw.store.fs import FsTaxonomyStore, find_component_project

NAME = "taxonomy"


def _missing() -> BackendError:
    return BackendError("no taxonomy store here — run `tcw project new taxonomy --id <id>` "
                        "in the project folder")


def _store() -> FsTaxonomyStore:
    project = find_component_project(NAME)
    if project is None:
        raise _missing()
    return FsTaxonomyStore.open(project)


def _covered(args: argparse.Namespace):
    return covered_for(args, NAME, _missing)


def _list(args: argparse.Namespace) -> int:
    refuse_local(args)
    return print_rows(_covered(args), NAME, args.json)


def _search(args: argparse.Namespace) -> int:
    return print_rows(_covered(args), NAME, args.json, query=args.query)


def _show(args: argparse.Namespace) -> int:
    covered = _covered(args)
    st = active_store(covered, NAME)
    row = show_row(covered, NAME, args.path, say=say)
    term = row.obj
    covered.warn(LEFT_OUT[NAME][1], say)
    if term.partial and st.view_error is not None:
        own_only(st.view_error, st.project_id)
    detail = term_detail(term)
    if args.json:
        projects = covered.projects_json()
        print_json(None, {"term": {**detail, **scope_keys(row)},
                          **({} if projects is None else {"projects": projects})})
        return codes.OK
    overridden, _ = show_lines(covered, row)
    lines = [f"full-id: {term.full_id}", f"owner: {term.owner}",
             *([f"parent: {term.parent}"] if term.parent is not None else []),
             *([f"overrides: {term.overrides}"] if term.overrides is not None else []),
             *overridden,
             *(["partial: inherited content could not be read"] if term.partial else []),
             f"name: {term.name}", f"kind: {term.kind}"]
    for key in ("vocabulary", "relatesTo", "attachments"):
        if detail[key]:
            lines.append(f"{key}: {', '.join(detail[key])}")
    body = term.description.strip()
    if body:
        lines += ["", "description:",
                  *(f"  {line}" if line else "" for line in body.splitlines())]
    print("\n".join(lines))
    return codes.OK


def _path(args: argparse.Namespace) -> int:
    print(_store().root)
    return codes.OK


def _add(args: argparse.Namespace) -> int:
    st = _store()
    try:
        term = st.add(args.name, slug=args.slug, parent=args.parent,
                      description=read_piped_stdin(), kind=args.kind,
                      vocabulary=args.vocab)
    except NotASlug as error:
        raise UsageError(f"--slug {error}") from None
    changed(st.changed)
    if term.overrides is not None:
        # At a path the project inherits, the new term is an override
        # holding only what differs (TCW-112 Design 4.1).
        say(f"{term.full_id} overrides {term.overrides}")
    print(term.full_id)
    return codes.OK


def _rm(args: argparse.Namespace) -> int:
    st = _store()
    target = find_tree_writable(st, args.path, removing=True)
    try:
        st.remove(target)
    finally:
        # A removal that stops partway has still deleted files; name them.
        changed(st.changed)
    try:
        now = st.get_view(target.id_path)
    except (InheritedUnavailable, BackendError):
        now = None
    if now is not None:
        # The removed term was an override (TCW-112 Design 4.4).
        say(f"{target.id_path} now shows {now.full_id}")
    return codes.OK


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = group(sub, NAME, help="vocabulary and feature entries")
    g = p.add_subparsers(dest="cmd", required=True)

    pl = command(g, "list", help="every entry's full identifier",
                 prints="one full identifier per line, or --json", writes="nothing",
                 examples=["taxonomy list", "taxonomy list --scope up --json",
                           "taxonomy list --scope down"])
    pl.add_argument("--local", action="store_true", help=argparse.SUPPRESS)
    scope_options(pl)
    pl.add_argument("--json", action="store_true",
                    help='print {"schema": 2, "terms": [...]}, and "projects" when the '
                         'scope is not own')
    pl.set_defaults(func=_list)

    pa = command(g, "add", help="create a vocabulary term or feature; the "
                                "description is read from stdin",
                 prints="the new entry's full identifier",
                 writes="the entry's files, each named on stderr",
                 examples=["taxonomy add Invoice", "taxonomy add Refund --parent invoice",
                           "taxonomy add 'Pay an invoice' --kind feature --vocab invoice"])
    pa.add_argument("name", help="display name of the entry (source of the default slug)")
    pa.add_argument("--slug", help="leaf slug (default: the name, slugified)")
    pa.add_argument("--parent", help="the term this one belongs under: its full "
                                     "identifier or its path here; the folder is made "
                                     "inside it when it is this project's own")
    pa.add_argument("--kind", choices=("vocabulary", "feature"),
                    help="taxonomy object kind (default: vocabulary, or for an entry "
                         "at a path this project inherits, the inherited entry's)")
    pa.add_argument("--vocab", action="append", metavar="REF",
                    help="vocabulary ref a feature involves; repeat for more")
    pa.set_defaults(func=_add)

    ps = command(g, "show", help="read an entry", prints="the record, or --json",
                 writes="nothing", examples=["taxonomy show invoice",
                                             "taxonomy show shared.taxonomy/invoice --json",
                                             "taxonomy show invoice --scope up"])
    ps.add_argument("path",
                    help="the entry: its full identifier (<project>.taxonomy/<path>), "
                         "or its path in this project, e.g. event/log-batch")
    scope_options(ps)
    ps.add_argument("--json", action="store_true",
                    help='print {"schema": 2, "term": {...}}, and "projects" when the '
                         'scope is not own')
    ps.set_defaults(func=_show)

    command(g, "path", help="print the taxonomy store folder", prints="the folder",
            writes="nothing", examples=["taxonomy path"]).set_defaults(func=_path)

    pr = command(g, "rm", help="remove a local entry, an override included",
                 prints="nothing",
                 writes="removes the entry's files, each named on stderr",
                 examples=["taxonomy rm invoice/refund"])
    pr.add_argument("path", help="the local entry to remove: its full identifier "
                                 "or its path")
    pr.set_defaults(func=_rm)

    from tcw.move import add_tree_commands
    add_tree_commands(g, command, "taxonomy", "term", "taxonomy rename invoice bill",
                      "taxonomy move invoice/refund --top")

    pse = command(g, "search", help="entries whose name or description holds the text",
                  prints="one full identifier per line, or --json", writes="nothing",
                  examples=["taxonomy search refund", "taxonomy search refund --json",
                            "taxonomy search refund --scope down"])
    pse.add_argument("query", help="text matched case-insensitively in names + descriptions")
    scope_options(pse)
    pse.add_argument("--json", action="store_true",
                     help='print {"schema": 2, "terms": [...]}, and "projects" when the '
                          'scope is not own')
    pse.set_defaults(func=_search)
