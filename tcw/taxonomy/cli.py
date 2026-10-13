"""`tcw taxonomy` — the nouns.

stdout carries each command's product and nothing else (TCW-73 Design 1):
`add` prints the new term's qualified path, `list` and `search` one path per
line, `show` the record, `path` the store folder; `rm` and `extends add|rm`
print nothing. Every file a write changed is named on stderr. A failure is
raised for the top-level handler to print and turn into its exit code.
"""

import argparse

from tcw import exit as codes
from tcw.cli_help import command, group
from tcw.errors import BackendError, NotFound
from tcw.output import changed, print_json
from tcw.stdin import read_piped_stdin
from tcw.store.base import Term
from tcw.store.fs import FsTaxonomyStore, find_node

NAME = "taxonomy"


def _store() -> FsTaxonomyStore:
    node = find_node(NAME)
    if node is None:
        raise BackendError("no taxonomy store here — run `tcw init taxonomy --id <id>` "
                           "in the project folder")
    return FsTaxonomyStore.open(node)


def _record(term: Term) -> dict:
    return {"path": term.qualified, "name": term.name, "kind": term.kind,
            "origin": term.origin}


def _detail(term: Term) -> dict:
    return {**_record(term), "vocabulary": list(term.vocabulary),
            "relatesTo": list(term.relates_to), "attachments": list(term.attachments),
            "description": term.description}


def _get(st: FsTaxonomyStore, ref: str) -> Term:
    term = st.get(ref)
    if term is None:
        raise NotFound(f"no such term: '{ref}'")
    return term


def _ordered(terms: list[Term]) -> list[Term]:
    # Sort on the SEGMENT TUPLE, never the joined path: `-` (0x2D) sorts before
    # `/` (0x2F), so keying on `qualified` puts a hyphen-extended root slug
    # (`event-reporting`) between `event` and `event/log-batch`. `origin`
    # groups each inherited tree separately: every `extends` alias is a
    # distinct store with its own slug namespace.
    return sorted(terms, key=lambda t: (t.origin != "local", t.origin,
                                        tuple(t.slug.split("/"))))


def _print_terms(terms: list[Term], as_json: bool) -> int:
    if as_json:
        print_json("terms", [_record(t) for t in terms])
    else:
        for t in terms:
            print(t.qualified)
    return codes.OK


def _list(args: argparse.Namespace) -> int:
    return _print_terms(_ordered(_store().list_all(local_only=args.local)), args.json)


def _search(args: argparse.Namespace) -> int:
    return _print_terms(list(_store().search(args.query)), args.json)


def _show(args: argparse.Namespace) -> int:
    term = _get(_store(), args.path)
    detail = _detail(term)
    if args.json:
        print_json("term", detail)
        return codes.OK
    lines = [f"path: {term.qualified}", f"name: {term.name}", f"kind: {term.kind}",
             f"origin: {term.origin}"]
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
    term = st.add(args.name, slug=args.slug, parent=args.parent,
                  description=read_piped_stdin(), kind=args.kind,
                  vocabulary=args.vocab)
    changed(st.changed)
    print(term.qualified)
    return codes.OK


def _rm(args: argparse.Namespace) -> int:
    st = _store()
    st.remove(args.path)
    changed(st.changed)
    return codes.OK


def _extends_add(args: argparse.Namespace) -> int:
    st = _store()
    st.extends_add(args.project_id)
    changed(st.changed)
    return codes.OK


def _extends_rm(args: argparse.Namespace) -> int:
    st = _store()
    st.extends_remove(args.project_id)
    changed(st.changed)
    return codes.OK


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = group(sub, NAME, help="vocabulary and feature entries")
    g = p.add_subparsers(dest="cmd", required=True)

    pl = command(g, "list", help="every entry's path",
                 prints="one qualified path per line, or --json", writes="nothing",
                 examples=["taxonomy list", "taxonomy list --local --json"])
    pl.add_argument("--local", action="store_true", help="local entries only")
    pl.add_argument("--json", action="store_true",
                    help='print {"schema": 1, "terms": [...]}')
    pl.set_defaults(func=_list)

    pa = command(g, "add", help="create a vocabulary term or feature; the "
                                "description is read from stdin",
                 prints="the new entry's qualified path",
                 writes="the entry's files, each named on stderr",
                 examples=["taxonomy add Invoice", "taxonomy add Refund --parent invoice",
                           "taxonomy add 'Pay an invoice' --kind feature --vocab invoice"])
    pa.add_argument("name", help="display name of the entry (source of the default slug)")
    pa.add_argument("--slug", help="leaf slug (default: the name, slugified)")
    pa.add_argument("--parent", help="parent term path (default: the root)")
    pa.add_argument("--kind", choices=("vocabulary", "feature"), default="vocabulary",
                    help="taxonomy object kind (default: vocabulary)")
    pa.add_argument("--vocab", action="append", metavar="REF",
                    help="vocabulary ref a feature involves; repeat for more")
    pa.set_defaults(func=_add)

    ps = command(g, "show", help="read an entry", prints="the record, or --json",
                 writes="nothing", examples=["taxonomy show invoice",
                                             "taxonomy show shared/invoice --json"])
    ps.add_argument("path",
                    help="term path, e.g. event/log-batch (alias-prefixed if inherited)")
    ps.add_argument("--json", action="store_true",
                    help='print {"schema": 1, "term": {...}}')
    ps.set_defaults(func=_show)

    command(g, "path", help="print the taxonomy store folder", prints="the folder",
            writes="nothing", examples=["taxonomy path"]).set_defaults(func=_path)

    pr = command(g, "rm", help="remove a local entry", prints="nothing",
                 writes="removes the entry's files, each named on stderr",
                 examples=["taxonomy rm invoice/refund"])
    pr.add_argument("path", help="path of the local term to remove")
    pr.set_defaults(func=_rm)

    pse = command(g, "search", help="entries whose name or description holds the text",
                  prints="one qualified path per line, or --json", writes="nothing",
                  examples=["taxonomy search refund", "taxonomy search refund --json"])
    pse.add_argument("query", help="text matched case-insensitively in names + descriptions")
    pse.add_argument("--json", action="store_true",
                     help='print {"schema": 1, "terms": [...]}')
    pse.set_defaults(func=_search)

    pe = group(g, "extends", help="inherit other projects' taxonomies")
    eg = pe.add_subparsers(dest="ecmd", required=True)
    pea = command(eg, "add", help="inherit a connected project's taxonomy",
                  prints="nothing", writes="tcw-config.yaml, named on stderr",
                  examples=["taxonomy extends add shared"])
    pea.add_argument("project_id", help="registered project ID whose taxonomy to inherit")
    pea.set_defaults(func=_extends_add)
    per = command(eg, "rm", help="stop inheriting a project's taxonomy",
                  prints="nothing", writes="tcw-config.yaml, named on stderr",
                  examples=["taxonomy extends rm shared"])
    per.add_argument("project_id", help="registered project ID to stop inheriting")
    per.set_defaults(func=_extends_rm)
