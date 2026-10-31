"""Manifest entries, and `projects:` converted by the command (TCW-116
Design 3, C3, C4: M1 to M6; B3, B13, A6, A11; criteria 21 to 24 and 27;
plan Step 18).

Each case is a small 3.x project run with `tcw migrate` in-process. A
project a manifest names is put where TCW-107's search would not find it
(two folders away), unless the case is M6's.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import yaml

from tcw.migrate.legacy import RepoDecl3, cache_folder_3x
from tcw.project_files import version_line
from tests.migrate.test_migrate_config import make, tree
from tests.objectcli import tcw  # noqa: F401  (a fixture)

URL = "https://example.invalid/team/core.git"


def project(folder: Path, project_id: str, extra: str = "", *, git: bool = False) -> Path:
    return make(folder, {"tcw-config.yaml": f"id: {project_id}\n{extra}"}, git=git)


def manifests(root: Path) -> tuple[dict | None, dict | None]:
    out = []
    for name in ("tcw-manifest.yaml", "tcw-manifest.local.yaml"):
        path = root / ".tcw" / name
        if path.is_file():
            text = path.read_text()
            assert text.startswith(version_line())
            out.append(yaml.safe_load(text)["projects"])
        else:
            out.append(None)
    return out[0], out[1]


def migrate(tcw, root: Path, code: int = 0):
    done = tcw(["migrate", "--no-jira"], root)
    assert done.code == code, done.err
    return done


@pytest.fixture
def far(tmp_path):
    """`core`, two folders away from `w/app`: no search finds it."""
    return project(tmp_path / "far/core", "core")


def app_with(tmp_path: Path, block: str, *, git: bool = True) -> Path:
    return project(tmp_path / "w/app", "app", f"projects:\n{block}", git=git)


# ── M1 to M5, one fixture each (criterion 22) ───────────────────────────────

def test_m1_a_relative_locator_is_the_shared_path_as_written(tcw, tmp_path, far):
    app = app_with(tmp_path, "  upstream:\n    core: ../../far/core\n")
    migrate(tcw, app)
    assert manifests(app) == ({"core": {"path": "../../far/core"}}, None)
    config = yaml.safe_load((app / ".tcw/tcw-config.yaml").read_text())
    assert config["parents"] == [{"id": "core", "inherit": "none"}]
    assert "projects" not in config


def only_here(path, relation: str = "upstream", source: str = "tcw-config.yaml") -> str:
    """A14's line for 'core' (review round 1, finding 1)."""
    return (f"  A14 .tcw/tcw-manifest.local.yaml: projects.core.path: {path}, which "
            f"{source}'s projects.{relation}.core held for everyone, is now only in "
            f"this file, which is not shared; every other person must add their own "
            f".tcw/tcw-manifest.local.yaml entry for 'core'")


def test_m1_an_absolute_locator_goes_to_the_personal_manifest(tcw, tmp_path, far):
    app = app_with(tmp_path, f"  upstream:\n    core: {far}\n")
    done = migrate(tcw, app)
    assert manifests(app) == (None, {"core": {"path": str(far)}})
    assert done.err.splitlines().count(only_here(far)) == 1


def test_m1_an_absolute_locator_extended_is_reported_once(tcw, tmp_path, far):
    """The reviewer's case: `taxonomy.extends` names the upstream too."""
    app = app_with(tmp_path, f"  upstream:\n    core: {far}\ntaxonomy:\n"
                             f"  extends: [core]\n")
    done = migrate(tcw, app)
    assert manifests(app) == (None, {"core": {"path": str(far)}})
    assert done.err.splitlines().count(only_here(far)) == 1


def test_m1_the_dry_run_reports_it_too(tcw, tmp_path, far):
    app = app_with(tmp_path, f"  upstream:\n    core: {far}\n")
    before = tree(app)
    done = tcw(["migrate", "--dry-run", "--no-jira"], app)
    assert done.code == 0, done.err
    assert only_here(far) in done.err.splitlines()
    assert tree(app) == before


def test_a14_names_the_ancestor_s_file_an_entry_came_from(tcw, tmp_path, far):
    """A14's other source name (`tcw/migrate/config.py:666-667`): the
    absolute locator is in the parent's file, which 3.x's walk reached
    across this project's `parent` entry, so A14 names that file by its
    path from here."""
    project(tmp_path / "w", "ws", f"projects:\n  upstream:\n    core: {far}\n")
    app = app_with(tmp_path, "  parent:\n    ws: ..\ntaxonomy:\n  extends: [core]\n")
    done = migrate(tcw, app)
    assert manifests(app)[1] == {"core": {"path": str(far)}}
    assert done.err.splitlines().count(only_here(far, source="../tcw-config.yaml")) == 1


def test_a_relative_locator_is_not_a14(tcw, tmp_path, far):
    app = app_with(tmp_path, "  upstream:\n    core: ../../far/core\n")
    assert "  A14 " not in migrate(tcw, app).err


def test_m1_an_absolute_locator_with_a_repository_keeps_m5_s_shared_path(tcw, tmp_path,
                                                                          far):
    app = app_with(tmp_path, f"  upstream:\n    core:\n      path: {far}\n"
                             f"      repository:\n        url: {URL}\n")
    done = migrate(tcw, app)
    assert manifests(app) == ({"core": {"repository": URL, "path": "../core"}},
                              {"core": {"path": str(far)}})
    assert only_here(far) in done.err.splitlines()


def test_m2_the_repository_and_its_ref(tcw, tmp_path, far):
    app = app_with(tmp_path, f"  upstream:\n    core:\n      path: ../../far/core\n"
                             f"      repository:\n        url: {URL}\n        ref: v2\n")
    migrate(tcw, app)
    assert manifests(app)[0] == {"core": {"repository": f"{URL}#v2",
                                          "path": "../../far/core"}}


def test_m2_a_url_holding_a_hash_is_b3(tcw, tmp_path, far):
    app = app_with(tmp_path, "  upstream:\n    core:\n      path: ../../far/core\n"
                             "      repository:\n        url: https://x/a#b.git\n")
    before = tree(app)
    done = migrate(tcw, app, 3)
    assert "  B3 projects.upstream.core.repository.url:" in done.err
    assert tree(app) == before


def test_m3_the_repository_path_is_the_subfolder(tcw, tmp_path):
    project(tmp_path / "far/mono/pkg", "core")
    app = app_with(tmp_path, f"  upstream:\n    core:\n      path: ../../far/mono/pkg\n"
                             f"      repository:\n        url: {URL}\n        path: pkg\n")
    migrate(tcw, app)
    assert manifests(app)[0] == {"core": {"repository": URL, "subfolder": "pkg",
                                          "path": "../../far/mono/pkg"}}


def test_m3_a_locator_not_ending_with_the_repository_path_is_b3(tcw, tmp_path, far):
    app = app_with(tmp_path, f"  upstream:\n    core:\n      path: ../../far/core\n"
                             f"      repository:\n        url: {URL}\n        path: pkg\n")
    done = migrate(tcw, app, 3)
    assert "  B3 .tcw/tcw-manifest.yaml: TCW 4 would refuse the file as planned: " \
           "projects.core: subfolder 'pkg' must be how path" in done.err


def test_m4_a_relative_checkout(tcw, tmp_path, far):
    app = app_with(tmp_path, f"  upstream:\n    core:\n      repository:\n"
                             f"        url: {URL}\n        checkout: ../../far/core\n")
    migrate(tcw, app)
    assert manifests(app) == ({"core": {"repository": URL, "path": "../../far/core"}}, None)


def test_m4_an_absolute_checkout(tcw, tmp_path, far):
    app = app_with(tmp_path, f"  upstream:\n    core:\n      repository:\n"
                             f"        url: {URL}\n        checkout: {far}\n")
    done = migrate(tcw, app)
    assert manifests(app) == ({"core": {"repository": URL, "path": "../core"}},
                              {"core": {"path": str(far)}})
    assert only_here(far) in done.err.splitlines()
    assert "  A14 " not in migrate(tcw, app).err        # the second run: nothing to say


def test_m5_a_cache_clone_here_is_named_in_the_personal_manifest(tcw, tmp_path,
                                                                 monkeypatch):
    """Criterion 23: and 4.0's lookup finds the project there, once it too
    is migrated (with personal files read, as outside the suite)."""
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    clone = cache_folder_3x(tmp_path, RepoDecl3(URL))
    assert clone.is_relative_to(Path(os.environ["XDG_CACHE_HOME"]))
    project(clone, "core")
    app = app_with(tmp_path, f"  upstream:\n    core:\n      repository:\n"
                             f"        url: {URL}\n")
    done = migrate(tcw, app)
    assert manifests(app) == ({"core": {"repository": URL, "path": "../core"}},
                              {"core": {"path": str(clone.resolve())}})
    assert (f"  A6 .tcw/tcw-manifest.local.yaml: projects.core.path: names TCW 3's clone "
            f"of 'core' at {clone.resolve()}, a cache folder") in done.err
    migrate(tcw, clone)
    from tcw.store.project import FsProjectRegistry, forget_registries
    forget_registries()
    found = FsProjectRegistry.open(app).project_folder("core", app.resolve())
    assert found == clone.resolve()


def test_m5_no_clone_here_says_where_provision_fetches_it(tcw, tmp_path):
    app = app_with(tmp_path, f"  upstream:\n    core:\n      repository:\n"
                             f"        url: {URL}\n")
    done = migrate(tcw, app)
    assert manifests(app) == ({"core": {"repository": URL, "path": "../core"}}, None)
    assert (f"  A6 .tcw/tcw-manifest.yaml: projects.core: TCW 3's clone of 'core' is "
            f"not on this machine; 'tcw project provision' will fetch it into "
            f"{(tmp_path / 'w/core').resolve()}") in done.err


def test_m5_a_folder_holding_something_else_is_b13(tcw, tmp_path):
    project(tmp_path / "w/core", "other")
    app = app_with(tmp_path, f"  upstream:\n    core:\n      repository:\n"
                             f"        url: {URL}\n")
    before = tree(app)
    done = migrate(tcw, app, 3)
    assert ("  B13 .tcw/tcw-manifest.yaml: projects.core.path: the shared manifest's path "
            "../core already holds something other than the project 'core'") in done.err
    assert tree(app) == before


# ── M6: no entry where 4.0 finds the project anyway (criterion 24) ──────────

def test_m6_an_enclosing_parent_and_a_sibling_get_no_entry(tcw, tmp_path):
    project(tmp_path / "ws", "ws", "projects:\n  children:\n    app: app\n")
    project(tmp_path / "ws/lib", "lib")
    app = project(tmp_path / "ws/app", "app",
                  "projects:\n  parent:\n    ws: ..\n  upstream:\n    lib: ../lib\n",
                  git=True)
    migrate(tcw, app)
    assert manifests(app) == (None, None)
    assert yaml.safe_load((app / ".tcw/tcw-config.yaml").read_text())["parents"] == [
        "ws", {"id": "lib", "inherit": "none"}]


def test_m6_the_same_with_a_repository_get_entries(tcw, tmp_path):
    project(tmp_path / "ws", "ws")
    project(tmp_path / "ws/lib", "lib")
    app = project(tmp_path / "ws/app", "app",
                  f"projects:\n  parent:\n    ws:\n      path: ..\n      repository:\n"
                  f"        url: {URL}\n  upstream:\n    lib:\n      path: ../lib\n"
                  f"      repository:\n        url: {URL}\n", git=True)
    migrate(tcw, app)
    assert manifests(app)[0] == {"ws": {"repository": URL, "path": ".."},
                                 "lib": {"repository": URL, "path": "../lib"}}


def test_m6_a_sibling_the_search_finds_twice_gets_an_entry(tcw, tmp_path):
    project(tmp_path / "w/lib", "lib")
    project(tmp_path / "w/lib-copy", "lib")
    app = app_with(tmp_path, "  upstream:\n    lib: ../lib\n")
    migrate(tcw, app)
    assert manifests(app)[0] == {"lib": {"path": "../lib"}}


def test_m6_the_variable_changes_no_entry_and_is_a11(tcw, tmp_path, monkeypatch, far):
    project(tmp_path / "ws", "ws")
    elsewhere = project(tmp_path / "elsewhere/ws", "ws")
    app = project(tmp_path / "ws/app", "app",
                  "projects:\n  parent:\n    ws: ..\n  upstream:\n    core: ../../far/core\n",
                  git=True)
    monkeypatch.setenv("TCW_PROJECT_WS", str(elsewhere))
    done = migrate(tcw, app)
    assert manifests(app) == ({"core": {"path": "../../far/core"}}, None)
    assert ("  A11 TCW_PROJECT_WS: is set while migrating; the manifest entry for 'ws' is "
            "decided from where its projects: entry says it is, not from the variable"
            ) in done.err


# ── C3 and C6 through the command (criteria 21 and 27) ──────────────────────

def test_a_family_migrated_parents_first_is_found_by_tcw_4(tcw, tmp_path):
    """Each converted parent and child is found by 4.0's lookup, through
    the written manifests or the search."""
    from tcw.store.project import FsProjectRegistry, forget_registries
    far = project(tmp_path / "far/core", "core")
    ws = project(tmp_path / "ws", "ws", "projects:\n  children:\n    app: app\n", git=True)
    app = project(tmp_path / "ws/app", "app",
                  "projects:\n  parent:\n    ws: ..\n  upstream:\n    core: ../../far/core\n"
                  "taxonomy:\n  path: docs/taxonomy\n")
    for root in (far, ws, app):
        migrate(tcw, root)
    assert yaml.safe_load((ws / ".tcw/tcw-config.yaml").read_text())["children"] == ["app"]
    forget_registries()
    registry = FsProjectRegistry.open(app)
    assert registry.project_folder("ws", app.resolve()) == ws.resolve()
    assert registry.project_folder("core", app.resolve()) == far.resolve()
    assert [p.id for p in registry.parents()] == ["ws", "core"]
    forget_registries()
    assert FsProjectRegistry.open(ws).project_folder("app", ws.resolve()) == app.resolve()


def test_a_jira_block_through_the_command(tcw, tmp_path):
    ws = project(tmp_path / "ws", "ws",
                 "projects:\n  children:\n    app:\n      path: app\n      jira:\n"
                 "        project: APP\n", git=True)
    project(tmp_path / "ws/app", "app", "projects:\n  parent:\n    ws: ..\n")
    done = migrate(tcw, ws)
    assert ("  D6 tcw-config.yaml: projects.children.app.jira: dropped; it filed work "
            "into another project's Jira, which TCW 4 removes (kept in "
            ".tcw/tcw-migration.yaml)") in done.err
    record = yaml.safe_load((ws / ".tcw/tcw-migration.yaml").read_text())
    assert record["removed"] == [{"file": "tcw-config.yaml",
                                  "key": "projects.children.app.jira",
                                  "value": {"project": "APP"}}]
    assert yaml.safe_load((ws / ".tcw/tcw-config.yaml").read_text())["children"] == ["app"]


def test_a_comment_dropped_with_the_block_is_named(tcw, tmp_path):
    ws = project(tmp_path / "ws", "ws",
                 "projects:\n  # the one child\n  children:\n    app: app\n", git=True)
    project(tmp_path / "ws/app", "app")
    done = migrate(tcw, ws)
    assert "a comment is dropped from tcw-config.yaml: # the one child" in done.err


def test_a_second_run_changes_nothing(tcw, tmp_path, far):
    app = app_with(tmp_path, "  upstream:\n    core: ../../far/core\n")
    migrate(tcw, app)
    before = tree(app)
    done = migrate(tcw, app)
    assert done.err.startswith("nothing to migrate")
    assert tree(app) == before
