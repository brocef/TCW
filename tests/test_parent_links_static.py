"""What TCW-108 removes stays removed, checked by reading source rather than
by running it (AC 8, AC 28).

The test files are searched by rule: a configuration text that still holds
the 3.x `projects:` key, or a dictionary literal that still names relations
under `"projects"`, fails the test unless it is in one of the tests whose
subject is that key's refusal (Design 3.5). A manifest's own top-level key is
also `projects:`; a manifest text is told apart because it is never the text
of a configuration writer, never holds an `id:` key, and is never written to a
`tcw-config` file."""

from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path

TESTS = Path(__file__).resolve().parent
TCW = TESTS.parent / "tcw"

#: The test helpers that write a configuration (TCW-106, TCW-107).
CONFIG_WRITERS = {"write_config", "write_local_config", "write_config_file"}
#: The calls that write a text straight to a file.
DIRECT_WRITERS = {"write_text", "write_bytes", "write"}
CONFIG_FILES = ("tcw-config.yaml", "tcw-config.local.yaml")
RELATIONS = {"parent", "children", "upstream"}

#: The tests whose subject is the refusal of `projects:` (Design 3.5), or a
#: TCW 3.x project's own file, by file and function; only they may still
#: write the key.
REFUSAL_TESTS = {
    ("test_project_files_cli.py", "test_ac13_a_3x_connection_is_reported_and_not_read"),
    ("test_parent_links_cli.py", "test_ac31_the_3x_key_in_a_descendant_is_a_graph_problem"),
    ("test_project_registry.py", "test_invalid_target_fails_closed"),
    ("test_upstream_projects.py",
     "test_a_broken_graph_beyond_an_upstream_does_not_block_the_reader"),
}

#: The folders of tests whose subject is converting TCW 3.x files (TCW-116
#: Decided 24), by path parts below `tests/`: they write `projects:` as the
#: input the migration reads.
MIGRATION_TESTS = (("migrate",),)

_BLOCK_KEY = re.compile(r"(?m)^projects:")
_ID_KEY = re.compile(r"(?m)^id:")


def _literal_text(node: ast.AST) -> str | None:
    """The text of a string constant, of `dedent(...)` of one, or the literal
    parts of an f-string; None for anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        value = node.value
        return value.decode("utf-8", "replace") if isinstance(value, bytes) else value
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value for part in node.values
                       if isinstance(part, ast.Constant) and isinstance(part.value, str))
    if isinstance(node, ast.Call) and node.args and "dedent" in ast.unparse(node.func):
        inner = _literal_text(node.args[0])
        return None if inner is None else textwrap.dedent(inner)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and node.func.attr == "encode":
        return _literal_text(node.func.value)
    return None


def _called(node: ast.Call) -> str:
    func = node.func
    return func.id if isinstance(func, ast.Name) else \
        func.attr if isinstance(func, ast.Attribute) else ""


def _writes_a_config_file(node: ast.Call) -> bool:
    """A `write_text`, `write_bytes` or `open(...).write` call whose target
    names a configuration file by a string constant."""
    if _called(node) not in DIRECT_WRITERS or not isinstance(node.func, ast.Attribute):
        return False
    target = node.func.value
    return any(isinstance(part, ast.Constant) and isinstance(part.value, str)
               and part.value in CONFIG_FILES for part in ast.walk(target))


def _configuration_texts(tree: ast.AST):
    """`(node, text)` for every literal configuration text in `tree`."""
    as_argument: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and (_called(node) in CONFIG_WRITERS
                                           or _writes_a_config_file(node)):
            for arg in node.args:
                for part in ast.walk(arg):
                    as_argument.add(id(part))
    for node in ast.walk(tree):
        text = _literal_text(node)
        if text is None or not _BLOCK_KEY.search(text):
            continue
        if id(node) in as_argument or _ID_KEY.search(text):
            yield node, text


def _relation_dicts(tree: ast.AST):
    """Every dictionary literal whose `"projects"` value is a dictionary
    literal naming a 3.x relation."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "projects" \
                    and isinstance(value, ast.Dict) \
                    and any(isinstance(k, ast.Constant) and k.value in RELATIONS
                            for k in value.keys):
                yield node


def _enclosing_tests(tree: ast.AST) -> dict[int, str]:
    """The test function each node is inside, by node id."""
    found: dict[int, str] = {}
    for function in ast.walk(tree):
        if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for node in ast.walk(function):
                found.setdefault(id(node), function.name)
    return found


def _allowed(file: str, test: str | None) -> bool:
    parts = Path(file).parts
    if any(parts[:len(folder)] == folder and len(parts) > len(folder)
           for folder in MIGRATION_TESTS):
        return True
    return (file, test) in REFUSAL_TESTS or (file, None) in REFUSAL_TESTS


def test_the_migration_exemption_reaches_only_its_own_folder():
    assert _allowed("migrate/test_migrate_editors.py", "test_x")
    assert not _allowed("migrate_like.py", "test_x")
    assert not _allowed("work/migrate/test_x.py", "test_x")
    assert not _allowed("test_migrate.py", None)


def test_ac8_no_fixture_writes_projects_except_to_check_its_refusal():
    found = []
    for path in sorted(TESTS.rglob("*.py")):
        if path.name == Path(__file__).name:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        inside = _enclosing_tests(tree)
        rel = str(path.relative_to(TESTS))
        nodes = [node for node, _ in _configuration_texts(tree)]
        nodes += list(_relation_dicts(tree))
        for node in nodes:
            test = inside.get(id(node))
            if not _allowed(rel, test):
                found.append(f"{rel}:{node.lineno} ({test})")
    assert found == [], "\n".join(found)


def test_the_rule_sees_each_shape_it_names():
    """The search above is only as good as its rule, so each shape it must
    catch is fed to it here."""
    shapes = [
        'write_config(root, "id: a\\nprojects:\\n  parent:\\n    ws:\\n")',
        'write_config(root, f"id: {x}\\nprojects:\\n  children:\\n{y}")',
        'write_config(root, dedent("""\\n    projects:\\n      parent: {ws: }\\n"""))',
        'x = "id: a\\nprojects:\\n  parent:\\n    ws:\\n"',
        '(root / ".tcw" / "tcw-config.yaml").write_text("projects:\\n  parent: {}\\n")',
        'doc = {"id": "a", "projects": {"upstream": {"core": None}}}',
    ]
    for shape in shapes:
        tree = ast.parse(shape)
        assert list(_configuration_texts(tree)) or list(_relation_dicts(tree)), shape
    manifests = [
        'write_manifest(root, "projects:\\n  lib: ../lib\\n")',
        'x = "projects:\\n  lib: ../lib\\n"',
        'doc = {"projects": {"lib": "../lib"}}',
    ]
    for shape in manifests:
        tree = ast.parse(shape)
        assert not list(_configuration_texts(tree)) and not list(_relation_dicts(tree)), shape


def _defined_names(root: Path) -> dict[str, list[str]]:
    names: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.setdefault(node.name, []).append(str(path.relative_to(root.parent)))
    return names


def test_ac28_the_single_parent_helpers_are_gone():
    gone = ["child_projects", "_routed", "routed_children", "routed_unreachable_children",
            "parent_project", "registered_parent", "registered_children",
            "unreachable_parent", "unreachable_children", "descendant_projects",
            "registered_project_id", "parent", "declared_parent_id",
            "declared_upstream_ids"]
    defined = _defined_names(TCW)
    assert {name: defined[name] for name in gone if name in defined} == {}


def test_ac8_the_3x_bookkeeping_is_gone():
    pattern = re.compile(r"declared_upstream_ids|_upstream_only|def entry\b|translate_projects")
    found = [f"{path.relative_to(TCW.parent)}:{n}"
             for path in sorted(TCW.rglob("*.py"))
             for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
             if pattern.search(line)]
    assert found == []
