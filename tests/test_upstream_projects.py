"""An upstream project: one a node reads from, that does not name the node back
(spec: 2026-09-29-let-a-project-read-taxonomy-and-capabilities-from-a-connected-
project-that-does-not-name-it-back).

A 3.x upstream is written as what TCW 4.0 reads it as: a parent passing no
axis (`{id: core, inherit: none}`), or passing the axes a test inherits from
it. Every fixture writes each project's parents, children and manifest in
full. None defaults a relation, a path or a repository entry: the relation is
exactly the axis the code under test branches on."""

from pathlib import Path

from tcw.store.base import ParentLink
from tcw.store.project import FsProjectRegistry
import yaml

from tests.projectfiles import write_config, write_manifest


def config(root: Path, text: str, where: dict | None = None) -> None:
    """`text` as the configuration at `root`; `where`, when given, written to
    its manifest, saying where the projects it names are. A text still under
    the 3.x `projects:` key, kept by the test whose subject is a broken one,
    has its locations moved into the manifest as before."""
    root.mkdir(parents=True, exist_ok=True)
    if "projects" in (yaml.safe_load(text) or {}):
        write_config(root, text, encoding="utf-8")
    else:
        write_config(root, text, encoding="utf-8")
    if where:
        write_manifest(root, where)


# ── loading ──────────────────────────────────────────────────────────────────

def test_a_bare_path_upstream_loads_without_naming_the_reader(tmp_path):
    config(tmp_path / "app", "id: app\nparents:\n- {id: core, inherit: none}\n",
           {"core": "../core"})
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.check() == []
    assert registry.get("core") is not None
    assert Path(registry.get("core").locator) == (tmp_path / "core").resolve()
    # A 3.x upstream is a parent passing nothing (TCW-108 Design 3.5).
    assert registry.parents() == [ParentLink("core", frozenset())]


def test_a_mapping_upstream_loads_by_its_path(tmp_path):
    config(tmp_path / "app", "id: app\nparents:\n- {id: core, inherit: none}\n",
           {"core": "../core"})
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.check() == []
    assert registry.get("core") is not None


def test_the_override_variable_wins_for_an_upstream(tmp_path, monkeypatch):
    config(tmp_path / "app", "id: app\nparents:\n- {id: core, inherit: none}\n",
           {"core": "../core"})
    config(tmp_path / "core", "id: core\n")
    config(tmp_path / "elsewhere", "id: core\n")
    monkeypatch.setenv("TCW_PROJECT_CORE", str(tmp_path / "elsewhere"))
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert Path(registry.get("core").locator) == (tmp_path / "elsewhere").resolve()


def test_an_absent_upstream_is_unreachable_not_a_problem(tmp_path):
    config(tmp_path / "app", "id: app\nparents:\n- {id: core, inherit: none}\n",
           {"core": "../core"})
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.check() == []
    assert "core" in [u.id for u in registry.unreachable()]


def test_nothing_beyond_an_upstream_is_loaded(tmp_path):
    """The upstream's own connections are not the reader's to load, check or
    write: a project reachable only beyond it never enters the reader's graph."""
    config(tmp_path / "app", "id: app\nparents:\n- {id: core, inherit: none}\n",
           {"core": "../core"})
    config(tmp_path / "core", "id: core\nchildren:\n- x\n", {"x": "x"})
    config(tmp_path / "core" / "x", "id: x\nparents:\n- core\n", {"core": ".."})
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.get("core") is not None
    assert registry.get("x") is None
    assert registry.check() == []


def test_a_broken_graph_beyond_an_upstream_does_not_block_the_reader(tmp_path):
    config(tmp_path / "app", "id: app\nparents:\n- {id: core, inherit: none}\n",
           {"core": "../core"})
    config(tmp_path / "core", "id: core\nprojects:\n  children:\n"
                               "    x: x\n  bogus: 1\n")
    config(tmp_path / "core" / "x", "id: x\n")            # names no parent
    assert FsProjectRegistry.open(tmp_path / "app").check() == []


def test_the_upstream_does_not_see_its_reader(tmp_path):
    config(tmp_path / "app", "id: app\nparents:\n- {id: core, inherit: none}\n",
           {"core": "../core"})
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "core")
    assert registry.check() == []
    assert registry.get("app") is None


def test_an_upstream_reached_through_a_parent_is_found(tmp_path):
    """The app-repository shape: a package reaches core through its parent."""
    config(tmp_path / "repo", "id: repo\nparents:\n- {id: core, inherit: none}\nchildren:\n- pkg\n",
           {"pkg": "pkg", "core": "../core"})
    config(tmp_path / "repo" / "pkg", "id: pkg\nparents:\n- repo\n", {"repo": ".."})
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "repo" / "pkg")
    assert registry.check() == []
    assert registry.get("core") is not None


def test_checkout_of_finds_an_upstream_by_its_repository(tmp_path):
    url = "https://example.invalid/core.git"
    config(tmp_path / "app", "id: app\nparents:\n- {id: core, inherit: none}\n")
    write_manifest(tmp_path / "app", {"core": {"path": "../core",
                                               "repository": f"{url}#main"}})
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.checkout_of(url) == (tmp_path / "core").resolve()


# ── an upstream and the family ───────────────────────────────────────────────

def _family(tmp_path: Path) -> Path:
    """Root `r` with children `a` and `b`; `a` names `core` as a parent
    passing no axis (a 3.x upstream)."""
    config(tmp_path / "r", "id: r\nchildren:\n- a\n- b\n", {"a": "a", "b": "b"})
    config(tmp_path / "r" / "a", "id: a\nparents:\n- r\n- {id: core, inherit: none}\n",
           {"r": "..", "core": "../../core"})
    config(tmp_path / "r" / "b", "id: b\nparents:\n- r\n", {"r": ".."})
    config(tmp_path / "core", "id: core\n")
    return tmp_path / "r"


def test_an_upstream_is_outside_the_family_of_the_declarers_sibling_and_parent(tmp_path):
    """From `b` and from `r`, `core` is a sibling's or a descendant's other
    parent, outside the family (TCW-108 Design 3.1, 3.3), so the registry
    there does not hold it."""
    root = _family(tmp_path)
    for node in (root / "b", root):
        registry = FsProjectRegistry.open(node)
        assert registry.check() == [], registry.check()
        assert registry.get("core") is None, node


# ── graph rules ──────────────────────────────────────────────────────────────

def test_a_self_upstream_is_a_problem(tmp_path):
    config(tmp_path / "app", "id: app\nparents:\n- {id: app, inherit: none}\n",
           {"app": "."})
    # A parent of itself: a loop (TCW-108 Design 4.7).
    assert any("loop in parents: app -> app" in p
               for p in map(str, FsProjectRegistry.open(tmp_path / "app").check()))


def test_an_upstream_that_is_also_a_child_is_a_problem(tmp_path):
    config(tmp_path / "app", "id: app\nparents:\n- {id: core, inherit: none}\nchildren:\n- core\n",
           {"core": "core"})
    config(tmp_path / "app" / "core", "id: core\nparents:\n- app\n", {"app": ".."})
    problems = [str(f) for f in FsProjectRegistry.open(tmp_path / "app").check()]
    # Named both as a parent and as a child (TCW-108 Design 1.3).
    assert any("'core' is named both as a parent and as a child" in p
               for p in problems), problems


def test_two_declarers_of_one_folder_are_one_project(tmp_path):
    root = _family(tmp_path)
    config(root / "b", "id: b\nparents:\n- r\n- {id: core, inherit: none}\n",
           {"r": "..", "core": "../../core"})
    assert FsProjectRegistry.open(root).check() == []


# ── migration ────────────────────────────────────────────────────────────────

def test_the_reverse_migration_order_still_fails(tmp_path):
    config(tmp_path / "r", "id: r\nchildren:\n- core\n", {"core": "core"})
    config(tmp_path / "r" / "core", "id: core\n")
    # TCW-108 Design 2.5: a listed child must name the lister.
    assert any("'core' is listed as a child of 'r' but does not name 'r'" in p
               for p in map(str, FsProjectRegistry.open(tmp_path / "r").check()))


# ── reading through an upstream, from the CLI ────────────────────────────────

import subprocess  # noqa: E402

import pytest  # noqa: E402

from tcw.store.fs import init  # noqa: E402


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True,
                   capture_output=True)


def _tcw(cwd: Path, *args: str, env: dict | None = None):
    import os
    return subprocess.run(["tcw", *args], cwd=str(cwd), capture_output=True,
                          text=True, env={**os.environ, **(env or {})})


def _core_node(path: Path, term: str = "Argument") -> Path:
    """A standalone project with one term and one capability, committed —
    usable as a node and as a remote."""
    path.mkdir(parents=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "t@t")
    _git(path, "config", "user.name", "t")
    init(["taxonomy", "capabilities", "work"], path, "core")
    assert _tcw(path, "taxonomy", "add", term).returncode == 0
    assert _tcw(path, "capabilities", "add", "arguments/build-an-argument").returncode == 0
    _git(path, "add", "-A")
    _git(path, "commit", "-qm", "seed")
    return path


def _reader(path: Path, project_id: str, links: dict, where: dict) -> Path:
    """A project at `path` whose configuration also holds `links` (its
    `parents` and `children`), with `where` as its manifest."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "t@t")
    _git(path, "config", "user.name", "t")
    init(["taxonomy", "capabilities", "work"], path, project_id)
    cfg = yaml.safe_load((path / ".tcw/tcw-config.yaml").read_text())
    cfg.update(links)
    write_config(path, yaml.safe_dump(cfg, sort_keys=False))
    write_manifest(path, where)
    return path


# `core` as a parent passing both axes, which `_assert_reads_core` reads.
_READ_CORE = {"id": "core", "inherit": ["taxonomy", "capabilities"]}


def _assert_reads_core(app: Path, term_slug: str = "argument") -> None:
    listed = _tcw(app, "taxonomy", "list", "--scope", "up")
    assert listed.returncode == 0, listed.stderr
    assert f"core.taxonomy/{term_slug}" in listed.stdout.splitlines(), listed.stdout
    listed = _tcw(app, "capabilities", "list", "--scope", "up")
    assert listed.returncode == 0, listed.stderr
    assert "core.capabilities/arguments/build-an-argument" in listed.stdout.splitlines()
    out = _tcw(app, "taxonomy", "show", f"core.taxonomy/{term_slug}")
    assert out.returncode == 0, out.stderr
    out = _tcw(app, "capabilities", "show", "core.capabilities/arguments/build-an-argument")
    assert out.returncode == 0, out.stderr
    out = _tcw(app, "validate")
    assert out.returncode == 0, out.stderr
    assert "nonreciprocal" not in out.stderr


def test_the_cli_reads_an_upstream_one_hop(tmp_path):
    core = _core_node(tmp_path / "core")
    app = _reader(tmp_path / "app", "app", {"parents": [_READ_CORE]}, {"core": "../core"})
    _assert_reads_core(app)
    out = _tcw(core, "validate")
    assert out.returncode == 0, out.stderr
    assert "app" not in out.stdout + out.stderr


def test_the_cli_reads_an_upstream_through_a_parent(tmp_path):
    _core_node(tmp_path / "core")
    repo = _reader(tmp_path / "repo", "repo",
                   {"parents": [_READ_CORE], "children": ["pkg"]},
                   {"pkg": "pkg", "core": "../core"})
    pkg = repo / "pkg"
    pkg.mkdir()
    init(["taxonomy", "capabilities", "work"], pkg, "pkg")
    cfg = yaml.safe_load((pkg / ".tcw/tcw-config.yaml").read_text())
    cfg["parents"] = ["repo"]
    write_config(pkg, yaml.safe_dump(cfg, sort_keys=False))
    write_manifest(pkg, {"repo": ".."})
    _assert_reads_core(pkg)


def test_the_override_variable_redirects_an_upstream_from_the_cli(tmp_path):
    _core_node(tmp_path / "core", term="Argument")
    _core_node(tmp_path / "other-core", term="Premise")
    app = _reader(tmp_path / "app", "app",
                  {"parents": [{"id": "core", "inherit": ["taxonomy"]}]},
                  {"core": "../core"})
    env = {"TCW_PROJECT_CORE": str(tmp_path / "other-core")}
    assert _tcw(app, "taxonomy", "show", "core.taxonomy/premise", "--scope", "up", env=env).returncode == 0
    assert _tcw(app, "taxonomy", "show", "core.taxonomy/argument", "--scope", "up", env=env).returncode != 0
    listed = _tcw(app, "taxonomy", "list", "--scope", "up", env=env).stdout
    assert "premise" in listed and "argument" not in listed, listed


# ── refusing writes, and allowing reads, from the CLI ────────────────────────

def _cli_family(tmp_path: Path) -> tuple[Path, str]:
    """Root `r` (a repository) with children `a` and `b`; `a` names `core` as
    a parent passing no axis (a 3.x upstream); `core` is its own repository holding one committed work item.
    Returns (root, the core item's slug)."""
    core = _core_node(tmp_path / "core")
    slug = _tcw(core, "work", "new", "Core thing").stdout.strip()
    _git(core, "add", "-A")          # `new` commits its own files; this catches the rest
    if subprocess.run(["git", "-C", str(core), "status", "--porcelain"],
                      capture_output=True, text=True).stdout.strip():
        _git(core, "commit", "-qm", "item")
    root = _reader(tmp_path / "r", "r", {"children": ["a", "b"]}, {"a": "a", "b": "b"})
    for child, extra, where in (
            ("a", [{"id": "core", "inherit": "none"}], {"core": "../../core"}),
            ("b", [], {})):
        node = root / child
        node.mkdir()
        init(["taxonomy", "capabilities", "work"], node, child)
        cfg = yaml.safe_load((node / ".tcw/tcw-config.yaml").read_text())
        cfg["parents"] = ["r", *extra]
        write_config(node, yaml.safe_dump(cfg, sort_keys=False))
        write_manifest(node, {"r": "..", **where})
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "family")
    return root, slug


def _assert_core_untouched(tmp_path: Path) -> None:
    status = subprocess.run(["git", "-C", str(tmp_path / "core"), "status",
                             "--porcelain"], capture_output=True, text=True).stdout
    assert status == "", status
    head = subprocess.run(["git", "-C", str(tmp_path / "core"), "rev-list",
                           "--count", "HEAD"], capture_output=True, text=True).stdout
    assert head.strip() == "2", "a commit was made in the upstream"


@pytest.mark.parametrize("where", ["a", "b", "."])
@pytest.mark.parametrize("command", [
    ("work", "start", "{ref}"),
    ("work", "edit", "{ref}", "--title", "Renamed"),
    ("work", "stage", "gate", "spec", "{ref}"),
    ("work", "procedure", "create-work", "{ref}"),
    ("work", "drop", "{ref}", "--confirm"),
])
def test_a_write_into_an_upstream_is_refused_as_read_only(tmp_path, where, command):
    root, slug = _cli_family(tmp_path)
    args = [part.replace("{ref}", f"core/{slug}") for part in command]
    out = _tcw(root / where, *args)
    assert out.returncode != 0, out.stdout
    assert "read-only" in out.stderr and "core" in out.stderr, out.stderr
    assert "nonreciprocal" not in out.stderr
    _assert_core_untouched(tmp_path)


@pytest.mark.parametrize("where", ["a", "b", "."])
def test_reading_an_upstream_item_is_allowed(tmp_path, where):
    root, slug = _cli_family(tmp_path)
    for args in (("work", "show", f"core/{slug}"), ("work", "path", f"core/{slug}"),
                 ("work", "stage", "validate", "spec", f"core/{slug}")):
        out = _tcw(root / where, *args)
        assert out.returncode == 0, (args, out.stderr)
    _assert_core_untouched(tmp_path)


def test_a_link_into_an_upstream_item_resolves(tmp_path):
    root, slug = _cli_family(tmp_path)
    (root / "a" / "docs" / "note.md").write_text(f"See tcw://W/core/{slug}.\n")
    out = _tcw(root / "a", "validate")
    assert out.returncode == 0, out.stderr


# ── delegate, nodes, and staying off the family's lists ──────────────────────

def _with_package(root: Path) -> Path:
    """Give `a` a child `pkg`, so there is a node below the declarer."""
    a = root / "a"
    cfg = yaml.safe_load((a / ".tcw/tcw-config.yaml").read_text())
    cfg["children"] = ["pkg"]
    write_config(a, yaml.safe_dump(cfg, sort_keys=False))
    write_manifest(a, {"pkg": "pkg"})
    pkg = a / "pkg"
    pkg.mkdir()
    init(["taxonomy", "capabilities", "work"], pkg, "pkg")
    cfg = yaml.safe_load((pkg / ".tcw/tcw-config.yaml").read_text())
    cfg["parents"] = ["a"]
    write_config(pkg, yaml.safe_dump(cfg, sort_keys=False))
    write_manifest(pkg, {"a": ".."})
    return pkg


@pytest.mark.parametrize("where", ["a", "."])
def test_delegate_into_an_upstream_is_refused(tmp_path, where):
    root, _ = _cli_family(tmp_path)
    out = _tcw(root / where, "work", "delegate", "core", "Please do a thing")
    assert out.returncode != 0, out.stdout
    assert "read-only" in out.stderr and "child projects" in out.stderr, out.stderr
    _assert_core_untouched(tmp_path)


def _listed(where):
    import json
    out = _tcw(where, "projects", "list", "--json")
    assert out.returncode == 0, out.stderr
    return {p["id"]: p for p in json.loads(out.stdout)["projects"]}


def test_projects_list_names_the_upstream_as_a_parent(tmp_path):
    root, _ = _cli_family(tmp_path)
    _with_package(root)
    # A parent row (TCW-108 Design 3.5, 8.1); from `a/pkg` it is an ancestor
    # beyond the parents, which the list does not show.
    assert _listed(root / "a")["core"]["relation"] == "parent"
    assert "core" not in _listed(root / "a" / "pkg")


def test_projects_list_names_an_absent_upstream(tmp_path):
    root, _ = _cli_family(tmp_path)
    import shutil
    shutil.rmtree(tmp_path / "core")
    core = _listed(root / "a")["core"]
    assert (core["relation"], core["present"]) == ("parent", False)


def test_projects_list_without_an_upstream(tmp_path):
    root, _ = _cli_family(tmp_path)
    assert "upstream" not in {p["relation"] for p in _listed(root / "b").values()}


def test_the_upstream_stays_off_the_familys_lists(tmp_path):
    root, slug = _cli_family(tmp_path)
    for where in (".", "a"):
        listed = _tcw(root / where, "work", "list", "--include-descendants")
        assert listed.returncode == 0, listed.stderr
        assert slug not in listed.stdout, listed.stdout
        checked = _tcw(root / where, "validate")
        assert "core" not in checked.stdout + checked.stderr, checked.stdout
    epic = _tcw(root, "work", "new", "Big thing", "--epic").stdout.strip()
    out = _tcw(root, "work", "reconcile", epic)
    assert out.returncode == 0, out.stderr
    assert "core" not in out.stdout, out.stdout
    rollups = list(root.glob(f"docs/work/*/{epic}/rollup.md"))
    assert rollups and "core" not in rollups[0].read_text()
    _assert_core_untouched(tmp_path)


# ── the tracker hint for a project with no parent ────────────────────────────

_NO_PARENT = "has no parent to inherit work.tracker settings from"


def _set_tracker(node: Path, tracker: dict) -> None:
    cfg = yaml.safe_load((node / ".tcw/tcw-config.yaml").read_text())
    cfg.setdefault("work", {})["tracker"] = tracker
    write_config(node, yaml.safe_dump(cfg, sort_keys=False))


def test_an_incomplete_tracker_with_no_parent_says_so(tmp_path):
    core = _core_node(tmp_path / "core")
    _set_tracker(core, {"candidate-query": "project = X"})
    out = _tcw(core, "validate")
    assert out.returncode == 1, out.stdout
    text = out.stdout + out.stderr
    assert "required" in text and _NO_PARENT in text, text


def test_an_incomplete_tracker_with_a_parent_does_not(tmp_path):
    root, _ = _cli_family(tmp_path)
    _set_tracker(root / "a", {"candidate-query": "project = X"})
    out = _tcw(root / "a", "validate")
    text = out.stdout + out.stderr
    assert "required" in text and _NO_PARENT not in text, text


def _edit(node: Path, change) -> None:
    """Apply `change` to `node`'s configuration."""
    cfg = yaml.safe_load((node / ".tcw/tcw-config.yaml").read_text())
    change(cfg)
    write_config(node, yaml.safe_dump(cfg, sort_keys=False))


# ── the CLI's view of an absent upstream, and of what lies beyond one ────────

def test_an_absent_upstream_is_a_warning_and_a_listing_says_unreachable(tmp_path):
    app = _reader(tmp_path / "app", "app",
                  {"parents": [{"id": "core", "inherit": ["taxonomy"]}]},
                  {"core": "../core"})
    out = _tcw(app, "validate")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "core" in out.stdout + out.stderr, out.stdout
    listed = _tcw(app, "taxonomy", "list", "--scope", "up")
    assert listed.returncode == 7
    # TCW-108 Design 6.3: a parent passing the axis, not on this machine.
    assert "from project 'core', which is not on this machine" in listed.stderr, \
        listed.stderr


def test_a_project_beyond_an_upstream_cannot_be_named(tmp_path):
    core = _core_node(tmp_path / "core")
    _edit(core, lambda c: c.update({"children": ["x"]}))
    write_manifest(core, {"x": "x"})
    x = core / "x"
    x.mkdir()
    init(["taxonomy", "capabilities", "work"], x, "x")
    _edit(x, lambda c: c.update({"parents": ["core"]}))
    write_manifest(x, {"core": ".."})
    slug = _tcw(x, "work", "new", "Deep thing").stdout.strip()
    assert slug
    app = _reader(tmp_path / "app", "app", {"parents": [{"id": "core", "inherit": "none"}]},
                  {"core": "../core"})
    out = _tcw(app, "work", "show", f"x/{slug}")
    assert out.returncode != 0
    assert "no such project" in out.stderr, out.stderr
