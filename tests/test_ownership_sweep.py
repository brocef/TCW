"""Guards that keep TCW-114's sweep swept (Design 1.2, AC 24; plan Step 21).

- What 4.0 removed stays removed: no definition or call of the delegation
  and `--blocks` code, no `/blocks` route, no backend or store `rename`.
- Every function under `tcw/` that calls a writer of a work backend or a
  tree store is listed here, with the function on its path that runs the
  ownership check, or the reason it needs none: a creator writes only the
  active project's store, and a call on something that is not a store is
  named as such. A new caller fails until it is listed.
- No read of the current folder under `tcw/` outside the reads Design 11
  lists.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import tcw
from tests.write_callers import all_writer_calls, writer_calls, writer_names

PACKAGE = Path(tcw.__file__).resolve().parent
REPO = PACKAGE.parent
SEARCHED = [REPO / "tcw", REPO / "web" / "client" / "src", REPO / "scripts", REPO / "evals"]
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".sh"}

REMOVED_NAMES = ("delegate", "open_for_update", "blocks_target", "delegate_to_jira",
                 "uncommitted_changes", "_cannot_make_item")

CHECKED = "checked"
CREATOR = "creator"
NOT_A_STORE = "not a store"

_CLI_ITEM = "work/cli.py:resolve_item, called with writing=True"
_TREE = "locate.py:find_tree_writable, through the store's removal_target"
_OVERRIDE = "locate.py:find_tree_writable, through the store's override_target"
_ROUTE = "serve/server.py:check_writes, for a route marked writes=written_item"
_PROBLEMS = "`problems` collects configuration problems"

#: `"<module>:<function>"` -> (kind, why).
WRITER_CALLERS = {
    "capabilities/cli.py:_add": (CREATOR, "tcw capabilities add writes only the active "
                                          "project's store"),
    "capabilities/cli.py:_set": (CHECKED, _OVERRIDE),
    "capabilities/cli.py:_reset": (CHECKED, _OVERRIDE),
    "capabilities/cli.py:_rm": (CHECKED, _TREE),
    "taxonomy/cli.py:_add": (CREATOR, "tcw taxonomy add writes only the active "
                                      "project's store"),
    "taxonomy/cli.py:_rm": (CHECKED, _TREE),
    "move.py:move_object": (CHECKED, "move.py:_work_target (work/cli.py:resolve_item, "
                                     "writing=True) or move.py:_tree_target "
                                     "(locate.py:find_tree_writable)"),
    "work/cli.py:new_item": (CREATOR, "tcw work new and the web's create route make an "
                                      "item in the active project's store only"),
    "work/cli.py:_edit": (CHECKED, _CLI_ITEM),
    "work/cli.py:_comment": (CHECKED, _CLI_ITEM),
    "work/advance.py:advance": (CHECKED, _CLI_ITEM + " by work/cli.py:_move, and "
                                         "work/cli.py:_discard through discard"),
    "serve/records.py:create_term": (CREATOR, "POST /api/taxonomy, a route marked "
                                              "writes=creates"),
    "serve/records.py:create_capability": (CREATOR, "POST /api/capabilities, a route "
                                                    "marked writes=creates"),
    "serve/records.py:update_term": (CHECKED, "serve/server.py:check_writes, for a "
                                              "route marked writes=_written(...)"),
    "serve/records.py:update_capability": (CHECKED, "serve/server.py:check_writes, for "
                                                    "a route marked writes=_written(...)"),
    "serve/work.py:edit": (CHECKED, _ROUTE),
    "serve/work.py:add_comment": (CHECKED, _ROUTE),
    "config_cli.py:_Writer.mapping": (NOT_A_STORE, "`self` writes YAML text; its "
                                                   "`comment` adds a comment line"),
    "projects_cli.py:connected.add": (NOT_A_STORE, "`seen` is a set made by the "
                                                   "enclosing function"),
    "store/base.py:_path_back.climb": (NOT_A_STORE, "`visited` is a set made by the "
                                                    "enclosing function"),
    "store/base.py:_c3.resolve": (NOT_A_STORE, "`in_progress` is a set made by the "
                                               "enclosing function"),
    "store/config_edit.py:_Document.end_of": (NOT_A_STORE, "`seen` is a set made by "
                                                           "the enclosing function"),
    "store/fs.py:_View.combined": (NOT_A_STORE, "`unreadable` is a set made by the "
                                                "enclosing function"),
    "store/project.py:FsProjectRegistry._walk_up": (NOT_A_STORE, "`_walked` is a set"),
    "store/project.py:FsProjectRegistry._walk_down": (NOT_A_STORE, "`seen` is a set "
                                                      "made by the enclosing function"),
    "store/project.py:FsProjectRegistry._personal_children_of": (
        NOT_A_STORE, "`_personal_children` is a dict"),
    "store/project.py:FsProjectRegistry._resolve_override": (
        NOT_A_STORE, "`_override_refused` is a set"),
    "store/project.py:FsProjectRegistry._entry_answer": (
        NOT_A_STORE, "`_occupied_problems` is a set"),
    "provision.py:_round_ids": (NOT_A_STORE, "`seen` is a set made in the function"),
    "provision.py:provision_projects": (NOT_A_STORE, "`run.attempted` is the run's set "
                                        "of the IDs it tried"),
    "store/project.py:FsProjectRegistry._family": (NOT_A_STORE, "`named` is a set made "
                                                   "by the enclosing function"),
    "work/generate.py:_drain": (NOT_A_STORE, "`overflow` is a threading.Event"),
    # TCW-116 Decided 25: tcw migrate writes files through its executor,
    # never through a backend or store.
    "migrate/stores.py:name_blockers": (NOT_A_STORE, "`seen` is a set made by the "
                                                     "function"),
    "migrate/config.py:_Converter.convert": (NOT_A_STORE, "`relations.parents` is the "
                                                          "list of links being planned"),
    "migrate/config.py:_Converter._classify": (NOT_A_STORE, "`relations.children` is the "
                                                            "list of children being "
                                                            "planned"),
    "migrate/config.py:_Converter.links_of": (NOT_A_STORE, "`absent` and `busy` are the "
                                                           "converter's sets of IDs"),
    "migrate/config.py:_parents_first": (NOT_A_STORE, "`left` is a list made in the "
                                                      "function"),
    "migrate/config.py:_Converter._convert": (NOT_A_STORE, "`relations.parents` is the "
                                                           "list of links being planned"),
    "migrate/config.py:_Converter._below_graphs": (NOT_A_STORE, "`memo` is the converter's "
                                                                "dict of links, put back "
                                                                "as it was"),
    "migrate/plan.py:other_checkout_blockers": (NOT_A_STORE, "`found` is a dict of sets "
                                                             "made in the function"),
    "migrate/report.py:once": (NOT_A_STORE, "`union` is a dict of sets made in the "
                                            "function"),
    "migrate/report.py:once.line": (NOT_A_STORE, "`said` is a set made by the enclosing "
                                                 "function"),
    **{f"work/config.py:{name}": (NOT_A_STORE, _PROBLEMS) for name in (
        "_parse_when", "_parse_binding", "parse_bindings", "_parse_hooks", "_parse_stage",
        "_parse_stages", "_parse_procedures", "_parse_tags", "parse_work_config")},
    **{f"work/jira/config.py:{name}": (NOT_A_STORE, _PROBLEMS) for name in (
        "_mapping", "_unknown", "_missing", "_text", "_site", "_project",
        "_credentials", "_timeout")},
}

#: Design 11's reads of the current folder, as `"<module>:<function>"`: each
#: runs at call time, after `tcw -C` has changed the folder.
CURRENT_FOLDER_READS = {
    "cli.py:run_init", "cli.py:main", "projects_cli.py:_list", "config_cli.py:_show",
    "project_cli.py:_path", "project_cli.py:_info",
    "project_files.py:find_marker", "output.py:shown", "work/cli.py:project_root",
    "work/cli.py:_procedure", "store/project.py:FsProjectRegistry._resolve_override",
    "store/fs.py:git_root",
    # TCW-116: TCW 3's reading of a relative TCW_PROJECT_<ID>, against the
    # folder the command runs in, as 3.x read it.
    "migrate/legacy.py:override_folder_3x",
    # TCW-118: `tcw -C <address>` names the folder it was resolving the
    # address from when the project there is refused. The read is only for
    # that message, and runs before the folder is changed.
    "cli.py:_enter",
}


def _sources():
    for top in SEARCHED:
        for path in sorted(top.rglob("*")):
            if path.is_file() and path.suffix in SOURCE_SUFFIXES \
                    and "node_modules" not in path.parts:
                yield path


def test_what_4_0_removed_is_not_defined_or_called():
    name = "|".join(REMOVED_NAMES)
    pattern = re.compile(rf"\b(?:def |function )?({name})\s*\(")
    found = []
    for path in _sources():
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            if pattern.search(line) or "Jira links only tickets on one site" in line \
                    or re.search(r"/blocks['\"`$)]", line):
                found.append(f"{path.relative_to(REPO)}:{number}: {line.strip()}")
    assert found == []


def test_no_backend_or_store_class_defines_rename():
    found = []
    for path in sorted(PACKAGE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef) and re.search(r"Backend|Store", node.name):
                found += [f"{path.relative_to(PACKAGE)}:{node.name}.rename"
                          for member in node.body
                          if isinstance(member, ast.FunctionDef) and member.name == "rename"]
    assert found == []


def test_the_writer_names_come_from_the_interfaces():
    assert writer_names() == {"create", "update", "set_stage", "comment", "move", "add",
                              "remove", "update_term", "reset", "set",
                              "update_capability"}


def test_every_writer_caller_is_listed_with_its_check_or_reason():
    found = set(all_writer_calls(PACKAGE))
    assert sorted(found - set(WRITER_CALLERS)) == [], "a new caller: list it"
    assert sorted(set(WRITER_CALLERS) - found) == [], "a listed caller is gone"


@pytest.mark.parametrize("caller", sorted(k for k, v in WRITER_CALLERS.items()
                                          if v[0] == CHECKED))
def test_each_checking_function_named_exists(caller):
    """Every `module:function` an entry names as its check is in the source."""
    _, why = WRITER_CALLERS[caller]
    for module, function in re.findall(r"([\w/]+\.py):([\w.]+)", why):
        source = (PACKAGE / module).read_text(encoding="utf-8")
        assert re.search(rf"def {re.escape(function.split('.')[-1])}\b", source), \
            (caller, module, function)


def test_the_guard_skips_a_set_and_reports_a_backend_and_a_parameter():
    names = {"add", "remove", "move"}
    source = (
        "def a(x):\n    seen = set()\n    seen.add(x)\n"
        "def b(root, x):\n    backend = open_backend(root)\n    backend.remove(x)\n"
        "def c(thing, a, b, f):\n    thing.move(a, b, f)\n"
        "def d(x):\n    seen: set[str] = set()\n    seen.add(x)\n    seen = make()\n"
        "    seen.add(x)\n")
    assert writer_calls(source, names) == {
        "b": [(6, "backend.remove")], "c": [(8, "thing.move")], "d": [(13, "seen.add")]}


def test_no_current_folder_read_outside_design_11s_list():
    found = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        module = path.relative_to(PACKAGE).as_posix()

        def walk(node, scope):
            for child in ast.iter_child_nodes(node):
                here = scope
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.ClassDef)):
                    here = (*scope, child.name)
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) \
                        and (ast.unparse(child.func) in ("Path.cwd", "os.getcwd")):
                    found.add(f"{module}:{'.'.join(here)}")
                walk(child, here)
        walk(ast.parse(path.read_text(encoding="utf-8")), ())
    assert found == CURRENT_FOLDER_READS
