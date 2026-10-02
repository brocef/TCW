"""Structural guards over the 3.0 work model's source (TCW-69 AC 5, AC 19).

AC 5: behavior comes from the stage table's columns, never from a stage's name,
so no new module but `model.py` spells a stage name, and `model.py` spells
them only inside `STAGES`.

AC 19: TCW 3.0 never changes git state. None of the new modules starts a
process or reaches the git helpers in `tcw/store/fs.py` that change state;
hooks run only through `tcw.work.hooks`.
"""

import ast
import re
from pathlib import Path

import pytest

import tcw
from tcw.work.model import STAGES

PACKAGE = Path(tcw.__file__).resolve().parent
NEW_MODULES = [PACKAGE / "work" / f"{name}.py" for name in
               ("advance", "gates", "layout", "backend", "references", "config")]
TOP_MODULES = [PACKAGE / "exit.py", PACKAGE / "errors.py"]
MODEL = PACKAGE / "work" / "model.py"
ALL_MODULES = NEW_MODULES + TOP_MODULES + [MODEL]

STAGE_NAME = re.compile(r"\b(" + "|".join(s.name for s in STAGES) + r")\b")
GIT_WRITERS = {"_git", "_git_index", "git_stage", "git_rm", "git_mv",
               "git_commit", "git_commit_result", "add_worktree",
               "merge_worktree", "remove_worktree"}


def _docstrings(tree):
    """The string constants that are docstrings, by identity."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                    and isinstance(first.value.value, str):
                found.add(id(first.value))
    return found


def _strings(tree):
    """Every string constant that is not a docstring. The literal pieces of an
    f-string and each part of an implicitly joined literal are constants of
    their own to `ast`, so they are checked too."""
    skip = _docstrings(tree)
    return [n for n in ast.walk(tree) if isinstance(n, ast.Constant)
            and isinstance(n.value, str) and id(n) not in skip]


def _parse(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _stage_literals(nodes, path):
    return [f"{path.name}:{n.lineno}: {n.value!r}" for n in nodes
            if STAGE_NAME.search(n.value)]


@pytest.mark.parametrize("path", NEW_MODULES + TOP_MODULES, ids=lambda p: p.name)
def test_no_stage_name_is_spelled_outside_the_table(path):
    assert _stage_literals(_strings(_parse(path)), path) == []


def test_model_spells_stage_names_only_inside_the_table():
    tree = _parse(MODEL)
    table = next(n for n in tree.body
                 if isinstance(n, (ast.Assign, ast.AnnAssign))
                 and any(isinstance(t, ast.Name) and t.id == "STAGES"
                         for t in (n.targets if isinstance(n, ast.Assign)
                                   else [n.target])))
    inside = {id(n) for n in ast.walk(table)}
    outside = [n for n in _strings(tree) if id(n) not in inside]
    assert _stage_literals(outside, MODEL) == []
    assert _stage_literals([n for n in _strings(tree) if id(n) in inside], MODEL)


def _process_or_git_uses(path):
    found = []
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Import):
            found += [f"import {a.name}" for a in node.names
                      if a.name.split(".")[0] == "subprocess"]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".")[0] == "subprocess":
                found.append(f"from {module} import ...")
            for alias in node.names:
                if module == "os" and alias.name in ("system", "popen"):
                    found.append(f"from os import {alias.name}")
                if alias.name in GIT_WRITERS:
                    found.append(f"from {module} import {alias.name}")
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "os" \
                    and node.attr in ("system", "popen"):
                found.append(f"os.{node.attr}")
            if node.attr in GIT_WRITERS:
                found.append(f".{node.attr}")
        elif isinstance(node, ast.Name) and node.id in GIT_WRITERS:
            found.append(node.id)
    return found


@pytest.mark.parametrize("path", ALL_MODULES, ids=lambda p: p.name)
def test_no_module_starts_a_process_or_writes_to_git(path):
    assert _process_or_git_uses(path) == []
