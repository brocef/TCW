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


@pytest.mark.parametrize("present", [False, True])
def test_provision_does_not_follow_an_upstreams_own_connections(
        tmp_path, present):
    """Mid-migration, core still names a private parent it can be fetched from.
    A reader holding only its own repository obtains core and stops there: the
    parent is core's to provision, not the reader's. `present` covers core
    already being on the machine rather than obtained in this run."""
    cache = tmp_path / "cache"
    private = _core_node(tmp_path / "private-root")
    remote = _core_node(tmp_path / "remote-core")
    _edit(remote, lambda c: c.update({"connected-projects": {"parent": {"root": {
        "path": "../not-here-either",
        "repository": {"url": str(private), "ref": "main"}}}}}))
    _git(remote, "commit", "-qam", "names its parent")
    where = ({"path": "../remote-core"} if present else
             {"path": "../not-here", "repository": {"url": str(remote), "ref": "main"}})
    app = _reader(tmp_path / "app", "app", {"upstream": {"core": where}})
    out = _tcw(app, "provision", env={"XDG_CACHE_HOME": str(cache)})
    assert out.returncode == 0, out.stdout + out.stderr
    assert str(private) not in out.stdout + out.stderr, out.stdout
    assert "root" not in out.stdout, out.stdout


def test_the_override_variable_redirects_an_upstream_from_the_cli(tmp_path):
    _core_node(tmp_path / "core", term="Argument")
    _core_node(tmp_path / "other-core", term="Premise")
    app = _reader(tmp_path / "app", "app", {"upstream": {"core": "../core"}})
    assert _tcw(app, "taxonomy", "extends", "add", "core").returncode == 0
    env = {"TCW_PROJECT_CORE": str(tmp_path / "other-core")}
    assert _tcw(app, "taxonomy", "show", "core/premise", env=env).returncode == 0
    assert _tcw(app, "taxonomy", "show", "core/argument", env=env).returncode != 0
    listed = _tcw(app, "taxonomy", "list", env=env).stdout
    assert "premise" in listed and "argument" not in listed, listed


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
    for args in (("work", "show", f"core/{slug}"), ("work", "path", f"core/{slug}"),
                 ("work", "stage", "validate", "spec", f"core/{slug}")):
        out = _tcw(root / where, *args)
        assert out.returncode == 0, (args, out.stderr)
    _assert_core_untouched(tmp_path)


def test_a_link_into_an_upstream_item_resolves(tmp_path):
    root, slug = _cli_family(tmp_path)
    (root / "a" / "docs" / "note.md").write_text(f"See tcw://W/core/{slug}.\n")
    out = _tcw(root / "a", "validate", "--no-recurse")
    assert out.returncode == 0, out.stderr


# ── tcw serve ────────────────────────────────────────────────────────────────

import json  # noqa: E402
import threading  # noqa: E402
from urllib.error import HTTPError  # noqa: E402
from urllib.parse import quote  # noqa: E402
from urllib.request import Request, urlopen  # noqa: E402

from tcw.serve import HOST, TcwServer  # noqa: E402


def _http(base: str, method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if method != "GET" else {}
    req = Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req) as res:
            return res.status, res.read().decode("utf-8")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8")


@pytest.fixture
def served_family(tmp_path):
    """The `_cli_family` graph served from `a` with --include-descendants."""
    root, slug = _cli_family(tmp_path)
    httpd = TcwServer((HOST, 0), root / "a", True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://{HOST}:{httpd.server_port}", quote(f"core/{slug}", safe="")
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.mark.parametrize("method,suffix,body", [
    ("POST", "/actions/start", {}),
    ("PATCH", "", {"title": "Renamed"}),
    ("PUT", "/artifacts/spec", {"content": "# Spec\n"}),
    ("PUT", "/plan-stages/one", {"content": "x"}),
    ("PUT", "/sidecars/capabilities.yaml", {"content": "a: 1\n"}),
    ("DELETE", "/plan-stages/one", None),
    ("DELETE", "", None),
    ("POST", "/plan-stages/one/open", {}),
])
def test_serve_refuses_a_write_into_an_upstream(
        tmp_path, served_family, method, suffix, body):
    base, ref = served_family
    status, text = _http(base, method, f"/api/work/{ref}{suffix}", body)
    assert status == 403, (status, text)
    assert "read-only" in text and "core" in text, text
    _assert_core_untouched(tmp_path)


def test_serve_reads_an_upstream_item(tmp_path, served_family):
    base, ref = served_family
    status, text = _http(base, "GET", f"/api/work/{ref}")
    assert status == 200, (status, text)
    _assert_core_untouched(tmp_path)


# ── delegate, nodes, and staying off the family's lists ──────────────────────

def _with_package(root: Path) -> Path:
    """Give `a` a child `pkg`, so there is a node below the declarer."""
    a = root / "a"
    cfg = yaml.safe_load((a / "tcw-config.yaml").read_text())
    cfg["connected-projects"]["children"] = {"pkg": "pkg"}
    (a / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    pkg = a / "pkg"
    pkg.mkdir()
    init(["taxonomy", "capabilities", "work"], pkg, "pkg")
    cfg = yaml.safe_load((pkg / "tcw-config.yaml").read_text())
    cfg["connected-projects"] = {"parent": {"a": ".."}}
    (pkg / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    return pkg


@pytest.mark.parametrize("where", ["a", "."])
def test_delegate_into_an_upstream_is_refused(tmp_path, where):
    root, _ = _cli_family(tmp_path)
    out = _tcw(root / where, "work", "delegate", "core", "Please do a thing")
    assert out.returncode != 0, out.stdout
    assert "read-only" in out.stderr and "child projects" in out.stderr, out.stderr
    _assert_core_untouched(tmp_path)


@pytest.mark.parametrize("where", ["a", "a/pkg"])
def test_nodes_lists_the_upstream_under_its_own_heading(tmp_path, where):
    root, _ = _cli_family(tmp_path)
    _with_package(root)
    out = _tcw(root / where, "work", "nodes")
    assert out.returncode == 0, out.stderr
    assert "upstream (read-only):" in out.stdout, out.stdout
    section = out.stdout.split("upstream (read-only):", 1)[1]
    assert "core" in section and "declared by a" in section, out.stdout


def test_nodes_names_an_absent_upstream(tmp_path):
    root, _ = _cli_family(tmp_path)
    import shutil
    shutil.rmtree(tmp_path / "core")
    out = _tcw(root / "a", "work", "nodes")
    section = out.stdout.split("upstream (read-only):", 1)[1]
    assert "core" in section and "not in this checkout" in section, out.stdout


def test_nodes_without_an_upstream_is_unchanged(tmp_path):
    root, _ = _cli_family(tmp_path)
    out = _tcw(root / "b", "work", "nodes")
    assert out.returncode == 0, out.stderr
    assert "upstream" not in out.stdout, out.stdout


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
    httpd = TcwServer((HOST, 0), root, True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        status, text = _http(f"http://{HOST}:{httpd.server_port}", "GET", "/api/work")
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert status == 200 and slug not in text, text
    _assert_core_untouched(tmp_path)


# ── the tracker hint for a project with no parent ────────────────────────────

_NO_PARENT = "has no parent to inherit work.tracker settings from"


def _set_tracker(node: Path, tracker: dict) -> None:
    cfg = yaml.safe_load((node / "tcw-config.yaml").read_text())
    cfg.setdefault("work", {})["tracker"] = tracker
    (node / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))


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
    out = _tcw(root / "a", "validate", "--no-recurse")
    text = out.stdout + out.stderr
    assert "required" in text and _NO_PARENT not in text, text


# ── the Proposit shape, end to end ───────────────────────────────────────────

_ROOT_TRACKER = {
    "provider": "jira-cloud",
    "base-url": "https://root.example.invalid",
    "candidate-query": "project = EX",
    "credentials": {"email-env": "ROOT_EMAIL", "token-env": "ROOT_TOKEN"},
}


def _edit(node: Path, change) -> None:
    cfg = yaml.safe_load((node / "tcw-config.yaml").read_text())
    change(cfg)
    (node / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))


def _proposit(tmp_path: Path) -> dict[str, Path]:
    """The shape the request came from: an orchestration root `proposit-app` with
    children `proposit-core` and `proposit-app-repo`; a package `shared` below the
    app repository extending core's taxonomy; core's tracker block holding only
    `candidate-query` and inheriting the rest from the root."""
    root = tmp_path / "ws"
    nodes = {"root": root, "core": root / "proposit-core",
             "app": root / "proposit-app",
             "shared": root / "proposit-app" / "packages" / "shared"}
    for key, pid in (("root", "proposit-app"), ("core", "proposit-core"),
                     ("app", "proposit-app-repo"), ("shared", "shared")):
        nodes[key].mkdir(parents=True)
        if key != "shared":            # three repositories, as in the workspace
            _git(nodes[key], "init", "-q", "-b", "main")
        init(["taxonomy", "capabilities", "work"], nodes[key], pid)
    _edit(root, lambda c: c.update({"connected-projects": {"children": {
        "proposit-core": "proposit-core", "proposit-app-repo": "proposit-app"}}}))
    _set_tracker(root, dict(_ROOT_TRACKER))
    _edit(nodes["core"], lambda c: c.update({"connected-projects": {
        "parent": {"proposit-app": ".."}}}))
    _set_tracker(nodes["core"], {"candidate-query": "project = CORE"})
    _edit(nodes["app"], lambda c: c.update({"connected-projects": {
        "parent": {"proposit-app": ".."}, "children": {"shared": "packages/shared"}}}))
    _edit(nodes["shared"], lambda c: c.update({"connected-projects": {
        "parent": {"proposit-app-repo": "../.."}}}))
    assert _tcw(nodes["core"], "taxonomy", "add", "Argument").returncode == 0
    out = _tcw(nodes["shared"], "taxonomy", "extends", "add", "proposit-core")
    assert out.returncode == 0, out.stderr
    return nodes


def _validate_each(nodes: dict[str, Path]) -> dict[str, tuple[int, str]]:
    result = {}
    for key, node in nodes.items():
        out = _tcw(node, "validate", "--no-recurse")
        result[key] = (out.returncode, out.stdout + out.stderr)
    return result


def _assert_state(nodes, *, warned: set[str]) -> None:
    for key, (code, text) in _validate_each(nodes).items():
        assert code == 0, (key, text)
        has_warning = "read as an upstream project" in text
        assert has_warning == (key in warned), (key, text)
    out = _tcw(nodes["shared"], "taxonomy", "show", "proposit-core/argument")
    assert out.returncode == 0, out.stderr


def test_the_proposit_migration_passes_through_no_blocked_state(tmp_path):
    nodes = _proposit(tmp_path)
    _assert_state(nodes, warned=set())

    step_2 = lambda c: c["connected-projects"].update(  # noqa: E731
        {"upstream": {"proposit-core": "../proposit-core"}})

    # The forbidden middle state: step 2 before step 1.
    _edit(nodes["app"], step_2)
    code, text = _validate_each({"app": nodes["app"]})["app"]
    assert code == 1 and "declare one or the other" in text, text
    _edit(nodes["app"], lambda c: c["connected-projects"].pop("upstream"))

    # Step 1: the root moves core from children to upstream, one edit.
    def step_1(c):
        c["connected-projects"]["children"].pop("proposit-core")
        c["connected-projects"]["upstream"] = {"proposit-core": "proposit-core"}
    _edit(nodes["root"], step_1)
    _assert_state(nodes, warned={"root", "core", "app", "shared"})

    # Step 2: the app repository declares core upstream too — one project.
    _edit(nodes["app"], step_2)
    _assert_state(nodes, warned={"root", "core", "app", "shared"})

    # Step 5 before step 4: the tracker block has nowhere to inherit from.
    _edit(nodes["core"], lambda c: c.pop("connected-projects"))
    code, text = _validate_each({"core": nodes["core"]})["core"]
    assert code == 1 and _NO_PARENT in text, text

    # Step 4: the tracker block goes; with step 5 in place, nothing is left over.
    _edit(nodes["core"], lambda c: c["work"].pop("tracker"))
    _assert_state(nodes, warned=set())
    out = _tcw(nodes["core"], "validate")
    assert "proposit-app" not in out.stdout + out.stderr, out.stdout


# ── the CLI's view of an absent upstream, and of what lies beyond one ────────

def test_an_absent_upstream_is_a_warning_and_extends_says_unreachable(tmp_path):
    app = _reader(tmp_path / "app", "app", {"upstream": {"core": "../core"}})
    out = _tcw(app, "validate")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "core" in out.stdout + out.stderr, out.stdout
    added = _tcw(app, "taxonomy", "extends", "add", "core")
    assert added.returncode != 0
    assert "not reachable" in added.stderr, added.stderr


def test_a_project_beyond_an_upstream_cannot_be_named(tmp_path):
    core = _core_node(tmp_path / "core")
    _edit(core, lambda c: c.update({"connected-projects": {"children": {"x": "x"}}}))
    x = core / "x"
    x.mkdir()
    init(["taxonomy", "capabilities", "work"], x, "x")
    _edit(x, lambda c: c.update({"connected-projects": {"parent": {"core": ".."}}}))
    slug = _tcw(x, "work", "new", "Deep thing").stdout.strip()
    assert slug
    app = _reader(tmp_path / "app", "app", {"upstream": {"core": "../core"}})
    out = _tcw(app, "work", "show", f"x/{slug}")
    assert out.returncode != 0
    assert "no such project" in out.stderr, out.stderr
