"""Manifests and finding a project's folder, as a person meets them on the
command line (TCW-107 acceptance criteria 1-15, 20-22 and 25).

Each test is named after the criterion it proves, and runs `tcw` as a shell
runs it, from a folder the test builds. The lookup itself is tested at the
library level in `tests/test_project_lookup.py`, and git worktrees in
`tests/test_manifest_worktree.py`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.project_files import LEGACY_PROJECT
from tests.projectfiles import write_config, write_config_file, write_manifest
from tests.test_project_files_cli import personal_env, tcw

NO_ENTRY = "no manifest lists it, and no folder next to {} or enclosing it declares it"


def proj(root: Path, project_id: str, **relations) -> Path:
    data: dict = {"id": project_id}
    if relations:
        data["projects"] = {name: ({i: None for i in ids} if isinstance(ids, list)
                                   else ids)
                            for name, ids in relations.items()}
    write_config(root, yaml.safe_dump(data, sort_keys=False))
    return root.resolve()


def listed(cwd: Path, env: dict | None = None) -> dict:
    ran = tcw(cwd, "projects", "list", "--json", env=env)
    assert ran.code == 0, ran
    return {row["id"]: row for row in json.loads(ran.out)["projects"]}


def validated(cwd: Path, env: dict | None = None):
    ran = tcw(cwd, "validate", env=env)
    lines = [line for line in ran.out.splitlines() if line.strip()]
    return ran, lines


def git(root: Path, *argv: str) -> str:
    return subprocess.run(["git", "-C", str(root), "-c", "protocol.file.allow=always",
                           *argv], check=True, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout


def committed(root: Path) -> Path:
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "fixture")
    return root


def manifest_path(root: Path, local: bool = False) -> str:
    return str(root / ".tcw" / ("tcw-manifest.local.yaml" if local else
                                "tcw-manifest.yaml"))


def pair(tmp_path: Path, **relations):
    """AC 1's layout: `app` reading `lib`, side by side."""
    app = proj(tmp_path / "app", "app", **(relations or {"upstream": ["lib"]}))
    lib = proj(tmp_path / "lib", "lib")
    return app, lib


# ---------------------------------------------------------------------------


def test_ac1_a_manifest_entry_both_forms(tmp_path):
    app, lib = pair(tmp_path)
    expected = {"by": "manifest", "file": manifest_path(app)}
    for entry in ("../lib", {"path": "../lib",
                             "repository": "https://example.invalid/lib.git#main"},
                  {"path": "../lib", "repository": "https://example.invalid/lib.git"}):
        write_manifest(app, {"lib": entry})
        row = listed(app)["lib"]
        assert (row["present"], row["path"], row["found"]) == (True, str(lib), expected)
    assert listed(app)["app"]["found"] is None


@pytest.mark.parametrize("text, words", [
    ("projects:\n  lib: ../lib\n", "a manifest starts with 'tcw-version:"),
    ("tcw-version: 99.0.0\nprojects:\n  lib: ../lib\n", "upgrade TCW"),
    ("other: 1\nprojects:\n  lib: ../lib\n", "'other'"),
    ("projects:\n  lib: {path: ../lib, ref: main}\n", "'ref'"),
    ("projects:\n  lib: /abs/lib\n", "relative"),
    ("projects:\n  lib: ~/lib\n", "relative"),
    ("projects:\n  lib: {repository: 'https://example.invalid/lib.git'}\n", "path"),
    ("projects:\n  lib: {path: ../lib, repository: 'https://example.invalid/lib.git#'}\n",
     "after '#'"),
    ("projects:\n  lib: {path: ../lib, repository: '#main'}\n", "before '#'"),
    ("projects:\n  lib: {path: ../lib, repository: 'x#a#b'}\n", "second '#'"),
    ("projects:\n  x: {path: ../a/x, repository: u, subfolder: ../x}\n", "subfolder"),
    ("projects:\n  x: {path: ../app, repository: u, subfolder: apps/x}\n", "subfolder"),
    ("projects:\n  x: {path: ../a/x, subfolder: x}\n", "repository"),
    ("projects:\n  Lib: ../lib\n", "project ID"),
])
def test_ac2_a_manifest_format_problem(tmp_path, text, words):
    app, _ = pair(tmp_path)
    if "tcw-version:" in words:
        (app / ".tcw" / "tcw-manifest.yaml").write_text(text)   # no version line
    else:
        write_manifest(app, text)
    assert tcw(app, "projects", "list").code == 1
    ran, lines = validated(app)
    assert ran.code == 1
    errors = [line for line in lines if line.startswith("error: .tcw/tcw-manifest.yaml:")]
    assert errors, ran
    assert any(words in line for line in errors), errors
    if "tcw-version:" in words:
        assert "tcw migrate" not in ran.out


def test_ac3_the_personal_manifest(tmp_path):
    app, lib = pair(tmp_path)
    write_manifest(app, {"lib": "../lib"})
    env = personal_env(tmp_path)
    copy = proj(tmp_path / "home" / "copies" / "lib", "lib")
    write_manifest(app, {"lib": str(copy)}, local=True)
    row = listed(app, env)["lib"]
    assert (row["path"], row["found"]["file"]) == (str(copy), manifest_path(app, True))
    write_manifest(app, {"lib": "~/copies/lib"}, local=True)
    assert listed(app, env)["lib"]["path"] == str(copy)
    assert listed(app, {**env, "TCW_NO_PERSONAL_CONFIG": "1"})["lib"]["path"] == str(lib)
    ran = tcw(app, "projects", "list", env={**env, "TCW_NO_PERSONAL_CONFIG": "true"})
    assert ran.code == 1 and "TCW_NO_PERSONAL_CONFIG must be 1" in ran.err


def test_ac4_a_manifest_entry_connects_nothing(tmp_path):
    app, _ = pair(tmp_path)
    proj(tmp_path / "other", "other")
    write_manifest(app, {"lib": "../lib", "other": "../other"})
    assert tcw(app, "projects", "list").out.split() == ["app", "lib"]


def test_ac5_an_ancestors_manifest(tmp_path):
    shared = proj(tmp_path / "shared", "shared", children=["desktop"])
    desktop = proj(tmp_path / "shared" / "desktop", "desktop", parent=["shared"],
                   upstream=["core"])
    core = proj(tmp_path / "x" / "core", "core")
    write_manifest(shared, {"desktop": "desktop", "core": "../x/core"})
    rows = listed(desktop)
    assert rows["shared"]["found"] == {"by": "search"}
    assert (rows["core"]["path"], rows["core"]["found"]["file"]) == (
        str(core), manifest_path(shared))
    ran, _ = validated(desktop)
    assert ran.code == 0, ran
    assert str(shared / ".tcw") not in ran.out + ran.err


def test_ac5a_an_upstreams_manifest_is_not_read(tmp_path):
    app = proj(tmp_path / "app", "app", upstream=["lib", "y"])
    lib = proj(tmp_path / "lib", "lib")
    proj(tmp_path / "x" / "y", "y")
    write_manifest(lib, {"y": "../x/y"})
    rows = listed(app)
    assert rows["lib"]["present"] is True
    assert rows["y"]["present"] is False


def test_ac6_a_descendants_manifest_and_the_order(tmp_path):
    docs = proj(tmp_path / "docs", "docs", children=["shared"], upstream=["core"])
    shared = proj(tmp_path / "docs" / "shared", "shared", parent=["docs"])
    proj(tmp_path / "x" / "core", "core")
    write_manifest(docs, {"shared": "shared"})
    write_manifest(shared, {"core": "../../x/core"})
    assert listed(docs)["core"]["found"]["file"] == manifest_path(shared)
    copy = proj(tmp_path / "y" / "core", "core")
    write_manifest(docs, {"core": "../y/core"})
    row = listed(docs)["core"]
    assert (row["path"], row["found"]["file"]) == (str(copy), manifest_path(docs))


def test_ac7_an_entry_decides_and_a_project_not_here(tmp_path):
    app, _ = pair(tmp_path)
    (app / "docs" / "work").mkdir(parents=True)
    write_manifest(app, {"lib": "../gone"})
    row = listed(app)["lib"]
    assert (row["present"], row["found"]) == (False, None)
    ran, lines = validated(app)
    assert ran.code == 0, ran
    unresolved = [line for line in lines if line.startswith("unresolved:")]
    assert len(unresolved) == 1, lines
    assert "'lib'" in unresolved[0] and "../gone" in unresolved[0]
    assert "tcw project provision" not in unresolved[0]
    write_manifest(app, {"lib": {"path": "../gone",
                                 "repository": "https://example.invalid/lib.git"}})
    ran, lines = validated(app)
    unresolved = [line for line in lines if line.startswith("unresolved:")]
    assert len(unresolved) == 1, lines
    assert "https://example.invalid/lib.git" in unresolved[0]
    assert "tcw project provision lib" in unresolved[0]
    # A personal entry decides whole: the committed entry's repository is not
    # carried over to it (entries never merge).
    env = personal_env(tmp_path)
    write_manifest(app, {"lib": "../gone2"}, local=True)
    ran, lines = validated(app, env)
    mine = [line for line in lines
            if line.startswith("unresolved: .tcw/tcw-manifest.local.yaml:")]
    assert len(mine) == 1 and "../gone2" in mine[0], lines
    assert "example.invalid" not in mine[0]
    shown = tcw(app, "work", "show", "lib/x", env=env)
    assert shown.code == 5 and "../gone2" in shown.err, shown
    assert "example.invalid" not in shown.err
    # No manifest, and no `lib` anywhere.
    for path in app.glob(".tcw/tcw-manifest*.yaml"):
        path.unlink()
    shutil.rmtree(tmp_path / "lib")
    shown = tcw(app, "work", "show", "lib/x")
    assert shown.code == 5, shown
    assert NO_ENTRY.format(app) in shown.err
    assert "tcw provision" not in shown.err.replace("tcw project provision", "")
    ran, lines = validated(app)
    assert ran.code == 0, ran
    assert [line for line in lines if line.startswith("unresolved:")] == [
        f"unresolved: .tcw/tcw-config.yaml: project 'lib' is not on this machine: "
        f"{NO_ENTRY.format(app)}; add it to .tcw/tcw-manifest.yaml or "
        f".tcw/tcw-manifest.local.yaml"]


@pytest.mark.parametrize("names", [False, True])
def test_ac8_an_entry_that_is_wrong(tmp_path, names):
    app = proj(tmp_path / "app", "app", **({"upstream": ["lib"]} if names else {}))
    bad = {
        "readme": lambda f: (f.mkdir(), (f / "README.md").write_text("x\n")),
        "old": lambda f: (f.mkdir(), (f / "tcw-config.yaml").write_text("id: lib\n")),
        "newer": lambda f: write_config(f, "tcw-version: 99.0.0\nid: lib\n"),
        "other": lambda f: proj(f, "other"),
    }
    expected = {"readme": "not a TCW project", "old": LEGACY_PROJECT,
                "newer": "upgrade TCW", "other": "'other'"}
    for name, make in bad.items():
        make(tmp_path / name)
        write_manifest(app, {"lib": f"../{name}"})
        ran, lines = validated(app)
        assert ran.code == 1, (name, ran)
        errors = [line for line in lines
                  if line.startswith("error: .tcw/tcw-manifest.yaml:")]
        assert errors and "'lib'" in errors[0] and expected[name] in errors[0], (name, lines)


@pytest.mark.parametrize("contents", ["empty", ".git file", ".git folder"])
def test_ac8_an_empty_folder_is_not_on_this_machine(tmp_path, contents):
    app, _ = pair(tmp_path)
    (app / "docs" / "work").mkdir(parents=True)
    folder = tmp_path / "gone"
    folder.mkdir()
    if contents == ".git file":
        (folder / ".git").write_text("gitdir: ../x\n")
    elif contents == ".git folder":
        (folder / ".git").mkdir()
    write_manifest(app, {"lib": "../gone"})
    ran, lines = validated(app)
    assert ran.code == 0, ran
    assert not [line for line in lines if line.startswith("error:")]
    unresolved = [line for line in lines if line.startswith("unresolved:")]
    assert len(unresolved) == 1 and "'lib'" in unresolved[0] and "../gone" in unresolved[0]
    assert listed(app)["lib"]["present"] is False
    assert tcw(app, "work", "show", "lib/x").code == 5
    (folder / ".DS_Store").write_text("x")
    ran, lines = validated(app)
    assert ran.code == 1 and any("not a TCW project" in line for line in lines), lines


def test_ac8_an_uninitialised_submodule_is_not_on_this_machine(tmp_path):
    lib = committed(proj(tmp_path / "lib-source", "lib"))
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    write_manifest(app, {"lib": "lib"})
    committed(app)
    git(app, "submodule", "add", "-q", str(lib), "lib")
    git(app, "commit", "-qm", "submodule")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(app), str(clone)], check=True,
                   capture_output=True, stdin=subprocess.DEVNULL)
    assert (clone / "lib").is_dir() and not any((clone / "lib").iterdir())
    ran, lines = validated(clone)
    assert ran.code == 0, ran
    unresolved = [line for line in lines if line.startswith("unresolved:")]
    assert len(unresolved) == 1 and "'lib'" in unresolved[0], lines


def test_ac8a_an_overridden_entry_is_a_warning(tmp_path):
    app, lib = pair(tmp_path)
    (tmp_path / "readme").mkdir()
    (tmp_path / "readme" / "README.md").write_text("x\n")
    write_manifest(app, {"lib": "../readme"})
    env = personal_env(tmp_path)
    write_manifest(app, {"lib": "../lib"}, local=True)
    ran, lines = validated(app, env)
    assert ran.code == 0, ran
    warned = [line for line in lines if line.startswith("warning: .tcw/tcw-manifest.yaml:")]
    assert len(warned) == 1, lines
    assert "overridden on this machine by" in warned[0]
    assert manifest_path(app, True) in warned[0]
    ran, lines = validated(app, {"TCW_PROJECT_LIB": str(lib)})
    assert ran.code == 0, ran
    assert any("overridden on this machine by TCW_PROJECT_LIB" in line for line in lines)
    ran, lines = validated(app)
    assert ran.code == 1, ran
    assert any(line.startswith("error: .tcw/tcw-manifest.yaml:") for line in lines)


def test_ac9_next_to_and_enclosing(tmp_path):
    app, _ = pair(tmp_path)
    assert listed(app)["lib"]["found"] == {"by": "search"}
    mono = proj(tmp_path / "mono", "mono", children=["shared"])
    shared = proj(tmp_path / "mono" / "packages" / "shared", "shared", parent=["mono"],
                  upstream=["other"])
    proj(tmp_path / "mono" / "other", "other")
    write_manifest(mono, {"shared": "packages/shared"})
    rows = listed(shared)
    assert (rows["mono"]["path"], rows["mono"]["found"]) == (str(mono), {"by": "search"})
    assert rows["other"]["present"] is False
    pkg = proj(tmp_path / "mono" / "a" / "b" / "pkg", "pkg", parent=["mono"])
    proj(mono, "mono", children=["shared", "pkg"])
    write_manifest(mono, {"pkg": "a/b/pkg"})
    assert listed(pkg)["mono"]["found"] == {"by": "search"}


def test_ac10_never_downwards(tmp_path):
    app = proj(tmp_path / "app", "app", children=["shared"])
    shared = proj(tmp_path / "app" / "packages" / "shared", "shared", parent=["app"])
    assert listed(app)["shared"]["present"] is False
    proj(tmp_path / "app" / "node_modules" / "dep", "dep")
    proj(app, "app", children=["shared"], upstream=["dep"])
    proj(shared, "shared", parent=["app"], upstream=["dep"])
    write_manifest(app, {"shared": "packages/shared"})
    assert listed(app)["dep"]["present"] is False
    assert listed(shared)["dep"]["present"] is False


def test_ac11_two_matches(tmp_path):
    app, lib = pair(tmp_path)
    copy = proj(tmp_path / "lib-copy", "lib")
    assert tcw(app, "projects", "list").code == 1
    ran, lines = validated(app)
    errors = " ".join(line for line in lines if line.startswith("error:"))
    assert ran.code == 1
    for named in (str(lib), str(copy), ".tcw/tcw-manifest.local.yaml"):
        assert named in errors, lines
    write_manifest(app, {"lib": "../lib"})
    assert listed(app)["lib"]["path"] == str(lib)
    assert validated(app)[0].code == 0


def test_ac11_one_beside_and_one_enclosing(tmp_path):
    outer = proj(tmp_path / "lib", "lib")
    app = proj(tmp_path / "lib" / "app", "app", upstream=["lib"])
    beside = proj(tmp_path / "lib" / "lib2", "lib")
    ran, lines = validated(app)
    errors = " ".join(lines)
    assert ran.code == 1 and str(outer) in errors and str(beside) in errors


def test_ac11_a_linked_worktree_of_lib_next_to_it(tmp_path):
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    lib = committed(proj(tmp_path / "lib", "lib"))
    git(lib, "worktree", "add", "-q", str(tmp_path / "lib-feature"))
    ran, lines = validated(app)
    errors = " ".join(lines)
    assert ran.code == 1, ran
    assert str(lib) in errors and str((tmp_path / "lib-feature").resolve()) in errors


def test_ac12_one_folder_per_id(tmp_path):
    app = proj(tmp_path / "app", "app", children=["lib"], upstream=["core"])
    lib = proj(tmp_path / "app" / "lib", "lib", parent=["app"], upstream=["core"])
    one = proj(tmp_path / "c1", "core")
    two = proj(tmp_path / "c2", "core")
    write_manifest(app, {"lib": "lib", "core": "../c1"})
    write_manifest(lib, {"core": "../../c2"})
    ran, lines = validated(app)
    errors = " ".join(lines)
    assert ran.code == 1 and "duplicate project id 'core'" in errors
    assert str(one) in errors and str(two) in errors


def test_ac13_unreadable_candidates(tmp_path):
    app, lib = pair(tmp_path)
    write_config_file(tmp_path / "broken" / ".tcw" / "tcw-config.yaml", "id: [x\n")
    locked = tmp_path / "locked"
    write_config(locked, "id: other\n")
    locked.chmod(0)
    try:
        ran, lines = validated(app)
        assert ran.code == 0, ran
        assert listed(app)["lib"]["path"] == str(lib)
    finally:
        locked.chmod(0o755)
    newer = tmp_path / "newer"
    write_config(newer, "tcw-version: 99.0.0\nid: lib\n")
    ran, lines = validated(app)
    assert ran.code == 1 and any(str(newer.resolve()) in line and "upgrade TCW" in line
                                 for line in lines), lines
    shutil.rmtree(newer)
    (tmp_path / "older").mkdir()
    (tmp_path / "older" / "tcw-config.yaml").write_text("id: lib\n")
    ran, lines = validated(app)
    assert ran.code == 1 and any(LEGACY_PROJECT in line for line in lines), lines


def test_ac14_the_variable_decides(tmp_path):
    app, lib = pair(tmp_path)
    write_manifest(app, {"lib": "../lib"})
    copy = proj(tmp_path / "v" / "lib", "lib")
    env = {"TCW_PROJECT_LIB": str(copy)}
    row = listed(app, env)["lib"]
    assert (row["path"], row["found"]) == (str(copy),
                                            {"by": "variable", "name": "TCW_PROJECT_LIB"})
    ran = tcw(app, "validate", env=env)
    assert ran.code == 0, ran
    assert f"connected project 'lib' is overridden by TCW_PROJECT_LIB to {copy}" in ran.err
    (tmp_path / "nothing").mkdir()
    ran = tcw(app, "validate", env={"TCW_PROJECT_LIB": str(tmp_path / "nothing")})
    assert ran.code == 1 and "TCW_PROJECT_LIB names a directory with no" in ran.out


@pytest.mark.parametrize("relations", [
    {"upstream": {"lib": None}},
    {"upstream": {"lib": {}}},
    {"children": {"lib": {"jira": {"project": "LIB"}}}},
])
def test_ac15_projects_entries_holding_only_an_id_are_accepted(tmp_path, relations):
    app = proj(tmp_path / "app", "app", **relations)
    proj(tmp_path / "lib", "lib", parent=["app"])
    ran = tcw(app, "projects", "list")
    assert ran.code == 0, ran
    assert ran.out.split() == ["app", "lib"]


def test_ac20_init_and_the_ignore_rule(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    git(root, "init", "-q")
    assert tcw(root, "init", "--id", "demo").code == 0
    ignore = root / ".tcw" / ".gitignore"
    rules = ["/tcw-config.local.yaml", "/tcw-manifest.local.yaml"]
    assert ignore.read_text().splitlines() == rules
    assert not list((root / ".tcw").glob("tcw-manifest*"))
    assert tcw(root, "init").code == 0
    assert ignore.read_text().splitlines() == rules
    ignore.write_text("/tcw-config.local.yaml\n")
    assert tcw(root, "init").code == 0
    assert ignore.read_text().splitlines() == rules
    outside = tmp_path / "q"
    outside.mkdir()
    ran = tcw(outside, "init", "--id", "demo")
    assert ran.code == 0 and not (outside / ".tcw" / ".gitignore").exists()
    assert ".tcw/tcw-manifest.local.yaml" in ran.err
    write_manifest(root, {"lib": "../lib"}, local=True)
    git(root, "add", "-f", ".tcw/tcw-manifest.local.yaml")
    ran, lines = validated(root)
    assert any(line.startswith("warning: .tcw/tcw-manifest.local.yaml:") and
               "tracked" in line for line in lines), lines


def test_ac21_a_single_project_pays_nothing(tmp_path):
    def run(root: Path) -> list[str]:
        outputs = []
        for argv in (("work", "list"), ("projects", "list"), ("validate",)):
            ran = tcw(root, *argv)
            outputs.append(f"{ran.code}\n{ran.out}\n{ran.err}".replace(str(root), "<root>"))
        return outputs

    crowded = tmp_path / "crowd" / "app"
    alone = tmp_path / "alone" / "app"
    for root in (crowded, alone):
        root.mkdir(parents=True)
        assert tcw(root, "init", "--id", "app").code == 0
    write_config_file(tmp_path / "crowd" / "broken" / ".tcw" / "tcw-config.yaml", "id: [\n")
    proj(tmp_path / "crowd" / "twin", "app")
    assert run(crowded.resolve()) == run(alone.resolve())


def test_ac25_one_answer_whichever_project_runs(tmp_path):
    app = proj(tmp_path / "app", "app", children=["a"])
    a = proj(tmp_path / "app" / "packages" / "a", "a", parent=["app"], children=["k"])
    k = proj(tmp_path / "app" / "plugins" / "k", "k", parent=["a"])
    write_manifest(app, {"a": "packages/a", "k": "plugins/k"})
    row = listed(a)["k"]
    assert (row["path"], row["found"]["file"]) == (str(k), manifest_path(app))
    ran, lines = validated(a)
    assert ran.code == 0 and not [line for line in lines if "unresolved" in line], ran
    # `tcw projects list` in `app` shows its children only, so the registry
    # the command would use is asked for the grandchild directly.
    from tcw.store.project import FsProjectRegistry
    assert Path(FsProjectRegistry.open(app).get("k").locator) == k


def test_ac22_provision_fetches_no_project(tmp_path):
    """`tcw provision` fetches the declared component stores only; a project
    not on this machine names `tcw project provision` (TCW-115) instead."""
    app, _ = pair(tmp_path)
    shutil.rmtree(tmp_path / "lib")
    (app / "docs" / "work").mkdir(parents=True)
    write_manifest(app, {"lib": {"path": "../lib",
                                 "repository": "https://example.invalid/lib.git"}})
    tools = tmp_path / "tools"
    tools.mkdir()
    calls = tmp_path / "git-calls"
    (tools / "git").write_text(f"#!/bin/sh\necho \"$@\" >> {calls}\n"
                               f"exec {shutil.which('git')} \"$@\"\n")
    (tools / "git").chmod(0o755)
    env = {"PATH": f"{tools}{os.pathsep}{os.environ['PATH']}"}
    ran = tcw(app, "provision", "--dry-run", env=env)
    assert ran.code == 0, ran
    assert ran.err.strip() == ("Nothing to provision: no component declares a home "
                               "repository in .tcw/tcw-config.yaml."), ran
    ran_git = calls.read_text() if calls.exists() else ""
    assert "example.invalid" not in ran_git and "clone" not in ran_git, ran_git
    assert "'lib'" not in ran.err and "lib.git" not in ran.err
    shown = tcw(app, "work", "show", "lib/x")
    assert shown.code == 5, shown
    assert "https://example.invalid/lib.git" in shown.err
    assert "tcw project provision lib" in shown.err
    for output in (ran.err, shown.err):
        assert "`tcw provision`" not in output and "run tcw provision" not in output


@pytest.mark.parametrize("entry", ["placed", "none"])
def test_delegating_to_a_project_not_on_this_machine_says_where(tmp_path, entry):
    """Exit 3 for a project not here carries Design 6.2's message, so the
    instruction it gives can be passed on (the work skill's rule)."""
    app = proj(tmp_path / "app", "app", children=["lib"])
    (app / "docs" / "work").mkdir(parents=True)
    expected = (f"project 'lib' is not on this machine: {NO_ENTRY.format(app)}; add it "
                f"to .tcw/tcw-manifest.yaml or .tcw/tcw-manifest.local.yaml")
    if entry == "placed":
        manifest = write_manifest(app, {"lib": {
            "path": "../lib", "repository": "https://example.invalid/lib.git"}})
        expected = (f"project 'lib' is not on this machine: {manifest.resolve()} places it "
                    f"at ../lib, from https://example.invalid/lib.git; fetch it with "
                    f"'tcw project provision lib'")
    ran = tcw(app, "work", "new", "x", "--project", "lib")
    assert ran.code == 3, ran
    assert ran.err == f"tcw work new: {expected}\n", ran


@pytest.mark.parametrize("raw, shown", [
    ("../lib", "lib: ../lib"),
    ({"path": "../lib"}, "lib: ../lib"),
    ({"repository": {"url": "x"}}, "lib: {path: <a folder>, repository: x}"),
    ({"path": "../lib", "repository": {"url": "https://h/app.git", "ref": "main",
                                       "path": "libs/lib"}},
     "lib: {path: ../lib, repository: https://h/app.git#main, subfolder: libs/lib}"),
])
def test_ac15_a_location_in_projects_is_refused(tmp_path, raw, shown):
    app = proj(tmp_path / "app", "app", upstream={"lib": raw})
    proj(tmp_path / "lib", "lib")
    ran, lines = validated(app)
    assert ran.code == 1, ran
    assert lines == [
        f"error: .tcw/tcw-config.yaml: projects.upstream.lib: a location goes in "
        f".tcw/tcw-manifest.yaml, not here: write 'lib:' here and '{shown}' under "
        f"projects: there"], ran
    listed = tcw(app, "projects", "list")
    assert listed.code == 1 and ".tcw/tcw-manifest.yaml" in listed.err, listed
    for output in (ran.out + ran.err, listed.err):
        assert "does not point back" not in output
        assert "which is not in this checkout" not in output
