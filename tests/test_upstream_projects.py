"""An upstream project: one a node reads from, that does not name the node back
(spec: 2026-09-29-let-a-project-read-taxonomy-and-capabilities-from-a-connected-
project-that-does-not-name-it-back).

Every fixture writes each project's `connected-projects` in full. None defaults
a relation, a path or a repository entry: the relation is exactly the axis the
code under test branches on."""

from pathlib import Path

from tcw.store.project import FsProjectRegistry


def config(root: Path, text: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "tcw-config.yaml").write_text(text, encoding="utf-8")


# ── loading ──────────────────────────────────────────────────────────────────

def test_a_bare_path_upstream_loads_without_naming_the_reader(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.check() == []
    assert registry.get("core") is not None
    assert Path(registry.get("core").locator) == (tmp_path / "core").resolve()
    assert registry.declared_upstream_ids() == ["core"]


def test_a_mapping_upstream_loads_by_its_path(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core:\n      path: ../core\n")
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.check() == []
    assert registry.get("core") is not None


def test_the_override_variable_wins_for_an_upstream(tmp_path, monkeypatch):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    config(tmp_path / "core", "id: core\n")
    config(tmp_path / "elsewhere", "id: core\n")
    monkeypatch.setenv("TCW_PROJECT_CORE", str(tmp_path / "elsewhere"))
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert Path(registry.get("core").locator) == (tmp_path / "elsewhere").resolve()


def test_an_absent_upstream_is_unreachable_not_a_problem(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.check() == []
    assert "core" in [u.id for u in registry.unreachable()]


def test_nothing_beyond_an_upstream_is_loaded(tmp_path):
    """The upstream's own connections are not the reader's to load, check or
    write: a project reachable only beyond it never enters the reader's graph."""
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    config(tmp_path / "core", "id: core\nconnected-projects:\n  children:\n"
                               "    x: x\n")
    config(tmp_path / "core" / "x", "id: x\nconnected-projects:\n  parent:\n"
                                    "    core: ..\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.get("core") is not None
    assert registry.get("x") is None
    assert registry.check() == []


def test_a_broken_graph_beyond_an_upstream_does_not_block_the_reader(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    config(tmp_path / "core", "id: core\nconnected-projects:\n  children:\n"
                               "    x: x\n  bogus: 1\n")
    config(tmp_path / "core" / "x", "id: x\n")            # names no parent
    assert FsProjectRegistry.open(tmp_path / "app").check() == []


def test_the_upstream_does_not_see_its_reader(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "core")
    assert registry.check() == []
    assert registry.get("app") is None


def test_an_upstream_reached_through_a_parent_is_found(tmp_path):
    """The proposit-app shape: a package reaches core through its parent."""
    config(tmp_path / "repo", "id: repo\nconnected-projects:\n  children:\n"
                               "    pkg: pkg\n  upstream:\n    core: ../core\n")
    config(tmp_path / "repo" / "pkg", "id: pkg\nconnected-projects:\n  parent:\n"
                                       "    repo: ..\n")
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "repo" / "pkg")
    assert registry.check() == []
    assert registry.get("core") is not None


def test_checkout_of_finds_an_upstream_by_its_repository(tmp_path):
    url = "https://example.invalid/core.git"
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              f"    core:\n      path: ../core\n      repository:\n"
                              f"        url: {url}\n        ref: main\n")
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.checkout_of(url) == (tmp_path / "core").resolve()


# ── the write rule ───────────────────────────────────────────────────────────

def _family(tmp_path: Path) -> Path:
    """Root `r` with children `a` and `b`; `a` declares `core` upstream."""
    config(tmp_path / "r", "id: r\nconnected-projects:\n  children:\n"
                            "    a: a\n    b: b\n")
    config(tmp_path / "r" / "a", "id: a\nconnected-projects:\n  parent:\n"
                                  "    r: ..\n  upstream:\n    core: ../../core\n")
    config(tmp_path / "r" / "b", "id: b\nconnected-projects:\n  parent:\n"
                                  "    r: ..\n")
    config(tmp_path / "core", "id: core\n")
    return tmp_path / "r"


def test_an_upstream_is_read_only_from_its_declarer(tmp_path):
    root = _family(tmp_path)
    registry = FsProjectRegistry.open(root / "a")
    reason = registry.read_only_reason("core")
    assert reason is not None and "read-only" in reason and "'a'" in reason


def test_an_upstream_is_read_only_from_the_declarers_sibling_and_parent(tmp_path):
    """A narrower rule — "an upstream of this node or an ancestor" — lets both
    of these write into it."""
    root = _family(tmp_path)
    for node in (root / "b", root):
        registry = FsProjectRegistry.open(node)
        assert registry.check() == [], registry.check()
        assert registry.read_only_reason("core") is not None, node


def test_family_members_stay_writable(tmp_path):
    root = _family(tmp_path)
    registry = FsProjectRegistry.open(root / "b")
    for project_id in ("b", "r", "a"):
        assert registry.read_only_reason(project_id) is None, project_id


def test_the_upstream_writes_to_itself_from_its_own_checkout(tmp_path):
    _family(tmp_path)
    assert FsProjectRegistry.open(tmp_path / "core").read_only_reason("core") is None


# ── graph rules ──────────────────────────────────────────────────────────────

def test_a_self_upstream_is_a_problem(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    app: .\n")
    assert any("own upstream" in p
               for p in FsProjectRegistry.open(tmp_path / "app").check())


def test_an_upstream_that_is_also_a_child_is_a_problem(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  children:\n"
                              "    core: core\n  upstream:\n    core: core\n")
    config(tmp_path / "app" / "core", "id: core\nconnected-projects:\n  parent:\n"
                                       "    app: ..\n")
    problems = FsProjectRegistry.open(tmp_path / "app").check()
    assert any("declared upstream" in p and "core" in p for p in problems), problems


def test_an_upstream_that_is_also_a_sibling_is_a_problem(tmp_path):
    """The migration's forbidden middle state: a package's parent declares core
    upstream while the root still lists core as a child."""
    config(tmp_path / "r", "id: r\nconnected-projects:\n  children:\n"
                            "    a: a\n    core: core\n")
    config(tmp_path / "r" / "a", "id: a\nconnected-projects:\n  parent:\n"
                                  "    r: ..\n  upstream:\n    core: ../core\n")
    config(tmp_path / "r" / "core", "id: core\nconnected-projects:\n  parent:\n"
                                     "    r: ..\n")
    problems = FsProjectRegistry.open(tmp_path / "r" / "a").check()
    assert any("declared upstream" in p and "core" in p for p in problems), problems


def test_an_upstream_that_is_also_a_grandparent_is_a_problem(tmp_path):
    config(tmp_path / "gp", "id: gp\nconnected-projects:\n  children:\n    mid: mid\n")
    config(tmp_path / "gp" / "mid", "id: mid\nconnected-projects:\n  parent:\n"
                                     "    gp: ..\n  children:\n    kid: kid\n")
    config(tmp_path / "gp" / "mid" / "kid", "id: kid\nconnected-projects:\n"
                                             "  parent:\n    mid: ..\n"
                                             "  upstream:\n    gp: ../..\n")
    problems = FsProjectRegistry.open(tmp_path / "gp" / "mid" / "kid").check()
    assert any("declared upstream" in p and "'gp'" in p for p in problems), problems


def test_two_declarers_of_one_folder_are_one_project(tmp_path):
    root = _family(tmp_path)
    config(root / "b", "id: b\nconnected-projects:\n  parent:\n"
                        "    r: ..\n  upstream:\n    core: ../../core\n")
    assert FsProjectRegistry.open(root).check() == []


def test_two_declarers_of_different_folders_name_both(tmp_path):
    root = _family(tmp_path)
    config(tmp_path / "core2", "id: core\n")
    config(root / "b", "id: b\nconnected-projects:\n  parent:\n"
                        "    r: ..\n  upstream:\n    core: ../../core2\n")
    problems = FsProjectRegistry.open(root).check()
    duplicate = [p for p in problems if "duplicate project id 'core'" in p]
    assert duplicate and "'a'" in duplicate[0] and "'b'" in duplicate[0], problems


# ── migration ────────────────────────────────────────────────────────────────

def _moved_root(tmp_path: Path) -> Path:
    """Step 1 done: the root reads core as upstream; core still names it parent."""
    config(tmp_path / "r", "id: r\nconnected-projects:\n  upstream:\n"
                            "    core: core\n")
    config(tmp_path / "r" / "core", "id: core\nconnected-projects:\n  parent:\n"
                                     "    r: ..\n")
    return tmp_path / "r"


def test_a_parent_claim_answered_by_an_upstream_declaration_is_a_warning(tmp_path):
    root = _moved_root(tmp_path)
    for node in (root, root / "core"):
        registry = FsProjectRegistry.open(node)
        assert registry.check() == [], (node, registry.check())
        assert any("core" in w and "upstream" in w and "parent" in w
                   for w in registry.warnings()), (node, registry.warnings())


def test_the_reverse_migration_order_still_fails(tmp_path):
    config(tmp_path / "r", "id: r\nconnected-projects:\n  children:\n"
                            "    core: core\n")
    config(tmp_path / "r" / "core", "id: core\n")
    assert any("nonreciprocal connection" in p
               for p in FsProjectRegistry.open(tmp_path / "r").check())


# ── reading through an upstream, from the CLI ────────────────────────────────

import subprocess  # noqa: E402

import pytest  # noqa: E402
import yaml  # noqa: E402

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


def _reader(path: Path, project_id: str, connected: dict) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "t@t")
    _git(path, "config", "user.name", "t")
    init(["taxonomy", "capabilities", "work"], path, project_id)
    cfg = yaml.safe_load((path / "tcw-config.yaml").read_text())
    cfg["connected-projects"] = connected
    (path / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    return path


def _assert_reads_core(app: Path, term_slug: str = "argument") -> None:
    for command in (("taxonomy", "extends", "add", "core"),
                    ("capabilities", "extends", "core")):
        out = _tcw(app, *command)
        assert out.returncode == 0, (command, out.stderr)
    out = _tcw(app, "taxonomy", "show", f"core/{term_slug}")
    assert out.returncode == 0, out.stderr
    out = _tcw(app, "capabilities", "show", "core/arguments/build-an-argument")
    assert out.returncode == 0, out.stderr
    out = _tcw(app, "validate")
    assert out.returncode == 0, out.stderr
    assert "nonreciprocal" not in out.stderr


def test_the_cli_reads_an_upstream_one_hop(tmp_path):
    core = _core_node(tmp_path / "core")
    app = _reader(tmp_path / "app", "app", {"upstream": {"core": "../core"}})
    _assert_reads_core(app)
    out = _tcw(core, "validate")
    assert out.returncode == 0, out.stderr
    assert "app" not in out.stdout + out.stderr


def test_the_cli_reads_an_upstream_through_a_parent(tmp_path):
    _core_node(tmp_path / "core")
    repo = _reader(tmp_path / "repo", "repo", {"children": {"pkg": "pkg"},
                                              "upstream": {"core": "../core"}})
    pkg = repo / "pkg"
    pkg.mkdir()
    init(["taxonomy", "capabilities", "work"], pkg, "pkg")
    cfg = yaml.safe_load((pkg / "tcw-config.yaml").read_text())
    cfg["connected-projects"] = {"parent": {"repo": ".."}}
    (pkg / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    _assert_reads_core(pkg)


def test_a_public_upstream_is_provisioned_into_a_reader_only_checkout(
        tmp_path, monkeypatch):
    """The case that motivated this: the upstream is fetched by its repository
    entry on a machine holding only the reader, and it names nothing back."""
    cache = tmp_path / "cache"
    remote = _core_node(tmp_path / "remote-core")
    app = _reader(tmp_path / "app", "app", {"upstream": {"core": {
        "path": "../not-here", "repository": {"url": str(remote), "ref": "main"}}}})
    env = {"XDG_CACHE_HOME": str(cache)}
    before = _tcw(app, "validate", env=env)
    assert before.returncode == 0 and "tcw provision" in before.stderr, before.stderr
    out = _tcw(app, "provision", env=env)
    assert out.returncode == 0, out.stderr
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    _assert_reads_core(app)
    assert "connected-projects" not in (remote / "tcw-config.yaml").read_text()


def test_the_override_variable_redirects_an_upstream_from_the_cli(tmp_path):
    _core_node(tmp_path / "core", term="Argument")
    _core_node(tmp_path / "other-core", term="Premise")
    app = _reader(tmp_path / "app", "app", {"upstream": {"core": "../core"}})
    assert _tcw(app, "taxonomy", "extends", "add", "core").returncode == 0
    env = {"TCW_PROJECT_CORE": str(tmp_path / "other-core")}
    assert _tcw(app, "taxonomy", "show", "core/premise", env=env).returncode == 0
    assert _tcw(app, "taxonomy", "show", "core/argument", env=env).returncode != 0


# ── refusing writes, and allowing reads, from the CLI ────────────────────────

def _cli_family(tmp_path: Path) -> tuple[Path, str]:
    """Root `r` (a repository) with children `a` and `b`; `a` declares `core`
    upstream; `core` is its own repository holding one committed work item.
    Returns (root, the core item's slug)."""
    core = _core_node(tmp_path / "core")
    slug = _tcw(core, "work", "new", "Core thing").stdout.strip()
    _git(core, "add", "-A")
    _git(core, "commit", "-qm", "item")
    root = _reader(tmp_path / "r", "r", {"children": {"a": "a", "b": "b"}})
    for child, extra in (("a", {"upstream": {"core": "../../core"}}), ("b", {})):
        node = root / child
        node.mkdir()
        init(["taxonomy", "capabilities", "work"], node, child)
        cfg = yaml.safe_load((node / "tcw-config.yaml").read_text())
        cfg["connected-projects"] = {"parent": {"r": ".."}, **extra}
        (node / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
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
    ("work", "procedure", "prompt", "create-work", "{ref}"),
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
    for args in (("work", "show", f"core/{slug}"), ("work", "path", f"core/{slug}")):
        out = _tcw(root / where, *args)
        assert out.returncode == 0, (args, out.stderr)
    _assert_core_untouched(tmp_path)


def test_a_link_into_an_upstream_item_resolves(tmp_path):
    root, slug = _cli_family(tmp_path)
    (root / "a" / "docs" / "note.md").write_text(f"See tcw://W/core/{slug}.\n")
    out = _tcw(root / "a", "validate", "--no-recurse")
    assert out.returncode == 0, out.stderr
