"""Find every function under `tcw/` that calls a writer of a work backend or
a tree store (TCW-114 plan Step 21; review S6).

The writer names are read from the interfaces: each method of `WorkBackend`,
`TaxonomyStore` and `CapabilitiesStore` that carries the `@writes` marker.
An AST walk sees names, not types, and `add`, `set`, `update`, `remove` and
`move` are also methods of Python's sets, dicts and lists, so a call
`<r>.<m>(…)` with `m` a writer name counts as a writer call unless `r` is
provably a builtin container: a plain name that, in the same function, is
last bound from a literal or a container constructor, or is annotated as
one. Every other such call counts, an unresolved receiver included: the
guard may be noisy, and its list absorbs the noise with a reason per entry,
but it never skips a real backend reached through an unexpected name.
"""

from __future__ import annotations

import ast
from pathlib import Path

CONTAINER_CALLS = {"set", "dict", "list", "frozenset", "defaultdict", "OrderedDict",
                   "Counter", "deque"}
CONTAINER_TYPES = CONTAINER_CALLS | {"Set", "Dict", "List", "FrozenSet", "MutableSet",
                                     "MutableMapping", "DefaultDict", "Mapping"}


def writer_names() -> set[str]:
    from tcw.store.base import CapabilitiesStore, TaxonomyStore
    from tcw.work.backend import WorkBackend
    names = set()
    for interface in (WorkBackend, TaxonomyStore, CapabilitiesStore):
        for name, member in vars(interface).items():
            if getattr(member, "__tcw_writes__", False):
                names.add(name)
    return names


def _is_container_value(node: ast.AST) -> bool:
    if isinstance(node, (ast.Set, ast.Dict, ast.List, ast.SetComp, ast.DictComp,
                         ast.ListComp)):
        return True
    if isinstance(node, ast.Call):
        func = node.func
        name = func.id if isinstance(func, ast.Name) else \
            func.attr if isinstance(func, ast.Attribute) else None
        return name in CONTAINER_CALLS
    return False


def _is_container_type(node: ast.AST | None) -> bool:
    if node is None:
        return False
    if isinstance(node, ast.Subscript):
        node = node.value
    if isinstance(node, ast.Attribute):
        return node.attr in CONTAINER_TYPES
    if isinstance(node, ast.Name):
        return node.id in CONTAINER_TYPES
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.split("[")[0].split(".")[-1] in CONTAINER_TYPES
    return False


class _Function(ast.NodeVisitor):
    """The writer calls of one function body, in source order. Bindings are
    followed in order, so a name is a container when its latest binding
    before the call makes it one."""

    def __init__(self, names: set[str], args: ast.arguments | None):
        self.names = names
        self.containers: set[str] = set()
        self.calls: list[tuple[int, str]] = []
        if args is not None:
            for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                if _is_container_type(arg.annotation):
                    self.containers.add(arg.arg)

    def _bind(self, target: ast.AST, container: bool) -> None:
        if isinstance(target, ast.Name):
            (self.containers.add if container else self.containers.discard)(target.id)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self._bind(target, _is_container_value(node.value))

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
        self._bind(node.target, _is_container_type(node.annotation)
                   or (node.value is not None and _is_container_value(node.value)))

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in self.names:
            receiver = func.value
            if not (isinstance(receiver, ast.Name) and receiver.id in self.containers) \
                    and not _is_container_value(receiver):
                self.calls.append((node.lineno, f"{ast.unparse(receiver)}.{func.attr}"))
        self.generic_visit(node)

    # A nested function or class is its own entry.
    def visit_FunctionDef(self, node) -> None:
        pass

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef
    visit_Lambda = None  # set below

    def visit_Lambda_(self, node: ast.Lambda) -> None:
        self.visit(node.body)


_Function.visit_Lambda = _Function.visit_Lambda_


def writer_calls(source: str, names: set[str]) -> dict[str, list[tuple[int, str]]]:
    """`{qualified function: [(line, "receiver.method"), …]}` for one module;
    a call at module level is under the name `<module>`."""
    found: dict[str, list[tuple[int, str]]] = {}

    def walk(node: ast.AST, scope: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                here = (*scope, child.name)
                visitor = _Function(names, child.args)
                for statement in child.body:
                    visitor.visit(statement)
                if visitor.calls:
                    found[".".join(here)] = visitor.calls
                walk(child, here)
            elif isinstance(child, ast.ClassDef):
                walk(child, (*scope, child.name))
    walk(ast.parse(source), ())
    module = _Function(names, None)
    for statement in ast.parse(source).body:
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module.visit(statement)
    if module.calls:
        found["<module>"] = module.calls
    return found


def all_writer_calls(package: Path) -> dict[str, list[tuple[int, str]]]:
    """`{"<module path>:<function>": calls}` over every module of `package`."""
    names = writer_names()
    out = {}
    for path in sorted(package.rglob("*.py")):
        module = path.relative_to(package).as_posix()
        for function, calls in writer_calls(path.read_text(encoding="utf-8"),
                                            names).items():
            out[f"{module}:{function}"] = calls
    return out
