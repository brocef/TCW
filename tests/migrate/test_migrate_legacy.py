"""`tcw migrate`'s copies of the TCW 3.x readers read as 3.x read (TCW-116
Design 4.1, 8.2; plan Step 2).

The listings are compared with what TCW 3.0.2 itself listed for the same
fixture, recorded once in `tests/migrate/golden/` by
`tests/migrate/record_3x_listings.py`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tcw.migrate import legacy
from tests.migrate.fixtures import build_f_single, user_file

GOLDEN = Path(__file__).resolve().parent / "golden"


def listed(name: str, command: str, key: str) -> list[str]:
    golden = json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))
    return sorted(row["path"] for row in json.loads(golden["commands"][command]["stdout"])[key])


@pytest.mark.parametrize("name, backend", [("f-single", "jira"),
                                           ("f-single-files", "filesystem")])
def test_the_objects_are_the_ones_3x_listed(tmp_path, name, backend):
    root = build_f_single(tmp_path / "app", backend="jira" if backend == "jira" else "files",
                          git=False)
    assert legacy.objects_3x(root / "docs/taxonomy", "taxonomy") == \
        listed(name, "taxonomy list --json", "terms")
    assert legacy.objects_3x(root / "docs/capabilities", "capabilities") == \
        listed(name, "capabilities list --json", "capabilities")


def test_work_items_are_the_folders_holding_item_yaml(tmp_path):
    jira = build_f_single(tmp_path / "jira", git=False)
    files = build_f_single(tmp_path / "files", backend="files", git=False)
    assert legacy.objects_3x(jira / "docs/work", "work") == ["APP-1-a", "APP-2-b"]
    assert legacy.objects_3x(files / "docs/work", "work") == ["2026-10-01-a",
                                                               "2026-10-02-b"]


def test_a_hidden_folder_is_no_capability_and_a_missing_store_lists_nothing(tmp_path):
    store = tmp_path / "caps"
    (store / ".hidden/x").mkdir(parents=True)
    (store / ".hidden/x/meta.yaml").write_text("Status: Supported\n")
    assert legacy.objects_3x(store, "capabilities") == []
    assert legacy.objects_3x(tmp_path / "none", "taxonomy") == []


def test_the_layers_merge_as_3x_merged_them(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    root = build_f_single(tmp_path / "app", config_home=tmp_path / "xdg", git=False)
    layers = legacy.read_3x_layers(root)
    assert layers.user.path == user_file(tmp_path / "xdg")
    assert layers.problems == []
    merged = layers.merged()
    assert merged["user"] == {"name": "Ada"}
    assert merged["id"] == "app"
    # The user-wide file's spec prompt, a chain list, resolved its `inherit`.
    prompt = merged["work"]["stages"]["spec"]["prompt"]
    assert prompt[0] == {"blob": "Write the spec."}
    assert prompt[-1]["blob"] == "My own reminder."


def test_personal_layers_are_not_read_when_3x_would_not(tmp_path):
    root = build_f_single(tmp_path / "app", git=False)
    assert "user" not in legacy.read_3x_layers(root).merged()


def test_a_duplicate_key_is_a_problem_naming_it(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    (root / "tcw-config.yaml").write_text("id: app\nid: again\n")
    layers = legacy.read_3x_layers(root)
    assert layers.shared.data is None
    assert "duplicate key: 'id'" in layers.shared.problem
    assert layers.problems == [layers.shared]


def test_a_file_is_read_with_its_line_endings(tmp_path):
    (tmp_path / "tcw-config.yaml").write_bytes(b"id: app\r\n")
    layer = legacy.read_layer_3x(tmp_path / "tcw-config.yaml", "shared")
    assert layer.text == "id: app\r\n" and layer.data == {"id": "app"}


def test_a_file_that_is_not_utf8_or_not_a_mapping_is_a_problem(tmp_path):
    (tmp_path / "a.yaml").write_bytes(b"id: \xff\n")
    (tmp_path / "b.yaml").write_text("- a\n")
    assert "not valid UTF-8" in legacy.read_layer_3x(tmp_path / "a.yaml", "shared").problem
    assert legacy.read_layer_3x(tmp_path / "b.yaml", "shared").problem == \
        "must be a mapping, not a list"
    absent = legacy.read_layer_3x(tmp_path / "c.yaml", "shared")
    assert (absent.present, absent.problem) == (False, None)


def test_links_outside_code_are_found_with_their_place():
    text = ("See [x](tcw://C/cli/x) and `[y](tcw://C/cli/y)`.\n"
            "```\n[z](tcw://T/z)\n```\n[w](tcw://W/app/APP-1-a)\n")
    found = legacy.links_3x(text)
    assert [link.uri for link in found] == ["tcw://C/cli/x", "tcw://W/app/APP-1-a"]
    assert all(text[link.start:link.end] == link.uri for link in found)
    assert found[0].parsed == legacy.TcwRef3("", "C", "cli/x")
    assert found[1].parsed == legacy.TcwRef3("", "W", "app/APP-1-a")


def test_a_link_is_parsed_as_3x_parsed_it():
    assert legacy.parse_tcw_uri_3x("tcw://core/T/term") == legacy.TcwRef3("core", "T", "term")
    assert legacy.parse_tcw_uri_3x("tcw://c//cli/x") == legacy.TcwRef3("", "C", "cli/x")
    assert legacy.parse_tcw_uri_3x("tcw://x/y") is None
    assert legacy.parse_tcw_uri_3x("tcw://C/a/../b") is None


def _as_4_0(root: Path) -> None:
    """The project's two files moved into `.tcw/`, as a finished run leaves them."""
    (root / ".tcw").mkdir()
    for name in ("tcw-config.yaml", "tcw-config.local.yaml"):
        text = (root / name).read_text()
        (root / ".tcw" / name).write_text("tcw-version: 4\n" + text)
        (root / name).unlink()


def test_the_jira_settings_read_alike_from_either_form(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    three = build_f_single(tmp_path / "three", config_home=tmp_path / "xdg", git=False)
    four = tmp_path / "four"
    shutil.copytree(three, four)
    _as_4_0(four)
    a, b = legacy.own_jira_layers(three), legacy.own_jira_layers(four)
    assert a.jira == b.jira
    assert a.jira["project"] == "APP"
    assert a.jira["fields"] == {"project": "TCW Project", "item": "TCW Item"}
    assert a.file_of(("project",)) == three / "tcw-config.yaml"
    assert b.file_of(("project",)) == four / ".tcw/tcw-config.yaml"


def test_credential_names_come_from_a_3x_root_personal_file(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    root = build_f_single(tmp_path / "app", git=False)
    (root / "tcw-config.local.yaml").write_text(
        "work:\n  jira:\n    credentials:\n      email-env: MY_EMAIL\n"
        "    project: NOT-ALLOWED\n")
    found = legacy.own_jira_layers(root)
    assert found.jira["credentials"]["email-env"] == "MY_EMAIL"
    assert found.jira["project"] == "APP"            # a shared key, refused there
    assert found.file_of(("credentials", "email-env")) == root / "tcw-config.local.yaml"


def test_a_store_folder_is_placed_as_3x_placed_it(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    default = legacy.store_folder_3x(root, "work", None)
    assert (default.folder, default.form) == (root / "docs/work", None)
    inside = legacy.store_folder_3x(root, "work", {"path": "board/../board"})
    assert (inside.folder, inside.configured, inside.form) == (
        root / "board/../board", "board/../board", None)
    assert legacy.store_folder_3x(root, "work", {"path": "../board"}).form == "outside"
    assert legacy.store_folder_3x(root, "work", {"path": str(root / "b")}).form is None
    assert legacy.store_folder_3x(root, "work", {"path": str(tmp_path)}).form == "outside"
    assert legacy.store_folder_3x(
        root, "taxonomy", {"repository": {"url": "x"}}).form == "repository"
    assert legacy.store_folder_3x(root, "work", {"path": ""}).problem
