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
from tcw.ids import identity, inherited_keys, parent_text
from tcw.locate import find_tree, find_tree_writable
from tcw.output import changed, left_out, own_only, print_json, say
from tcw.stdin import read_piped_stdin
from tcw.store.base import NotASlug, Term
from tcw.store.fs import FsTaxonomyStore, find_component_project

NAME = "taxonomy"


def _store() -> FsTaxonomyStore:
    project = find_component_project(NAME)
    if project is None:
        raise BackendError("no taxonomy store here — run `tcw init taxonomy --id <id>` "
                           "in the project folder")
    return FsTaxonomyStore.open(project)


def _record(term: Term) -> dict:
    # `parent` after `owner` (TCW-111 Design 3.1): its text, or null; then
    # `overrides`, or `partial` (TCW-112 choice 7).
    return {**identity(term.full_id), "parent": parent_text(term.parent),
            **inherited_keys(term), "name": term.name, "kind": term.kind}


def _detail(term: Term) -> dict:
    return {**_record(term), "vocabulary": list(term.vocabulary),
            "relatesTo": list(term.relates_to), "attachments": list(term.attachments),
            "description": term.description}


def _ordered(terms: list[Term], project_id: str) -> list[Term]:
    # Sort on the SEGMENT TUPLE, never the joined text: `-` (0x2D) sorts before
    # `/` (0x2F), so keying on the full identifier puts a hyphen-extended root
    # slug (`event-reporting`) between `event` and `event/log-batch`. The
    # owner groups each inherited tree separately, after this project's own.
    return sorted(terms, key=lambda t: (t.owner != project_id, t.owner,
                                        tuple(t.full_id.parts)))


def _print_terms(terms: list[Term], as_json: bool) -> int:
    if as_json:
        print_json("terms", [_record(t) for t in terms])
    else:
        for t in terms:
            print(t.full_id)
    return codes.OK


def _warn_view(st: FsTaxonomyStore, terms: list[Term]) -> None:
    """Design 2.5's warning for each id-path listed, on standard error,
    before the list (TCW-112 Design 3.2)."""
    for warning in st.view_warnings({t.slug for t in terms}):
        say(f"warning: {warning}")


def _list(args: argparse.Namespace) -> int:
    st = _store()
    try:
        terms = st.list_all(local_only=args.local)
        _warn_view(st, terms)
    except InheritedUnavailable as error:
        # The project's own terms are listed without the view, each its own
        # declaration alone (TCW-112 Design 3.4).
        if not args.local:
            raise
        own_only(error, st.project_id)
        terms = st.own_declarations()
    _print_terms(_ordered(terms, st.project_id), args.json)
    return left_out(st.unreadable_files())


def _search(args: argparse.Namespace) -> int:
    st = _store()
    terms = list(st.search(args.query))
    _warn_view(st, terms)
    _print_terms(terms, args.json)
    return left_out(st.unreadable_files())


def _show(args: argparse.Namespace) -> int:
    st = _store()
    term = find_tree(st, args.path)
    if term.partial and st.view_error is not None:
        own_only(st.view_error, st.project_id)
    detail = _detail(term)
    if args.json:
        print_json("term", detail)
        return codes.OK
    lines = [f"full-id: {term.full_id}", f"owner: {term.owner}",
             *([f"parent: {term.parent}"] if term.parent is not None else []),
             *([f"overrides: {term.overrides}"] if term.overrides is not None else []),
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
                 examples=["taxonomy list", "taxonomy list --local --json"])
    pl.add_argument("--local", action="store_true", help="local entries only")
    pl.add_argument("--json", action="store_true",
                    help='print {"schema": 2, "terms": [...]}')
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
                                             "taxonomy show shared.taxonomy/invoice --json"])
    ps.add_argument("path",
                    help="the entry: its full identifier (<project>.taxonomy/<path>), "
                         "or its path in this project, e.g. event/log-batch")
    ps.add_argument("--json", action="store_true",
                    help='print {"schema": 2, "term": {...}}')
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
                  examples=["taxonomy search refund", "taxonomy search refund --json"])
    pse.add_argument("query", help="text matched case-insensitively in names + descriptions")
    pse.add_argument("--json", action="store_true",
                     help='print {"schema": 2, "terms": [...]}')
    pse.set_defaults(func=_search)
