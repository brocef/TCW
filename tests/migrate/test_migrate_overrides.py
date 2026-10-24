"""Overrides move to their original's path (TCW-116 C14, C15, B9, D2, D3,
D4; Design 7's `moved:`; criteria 32's D2 half, 38, 39, 40 and 61; plan
Step 21).

`core` is a 3.x project the app extends for capabilities; its capability
`auth/login` has the id `cap-aaa111`, and each case gives the app an
override of it somewhere else.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tcw.migrate import execute
from tests.migrate.test_migrate_config import make, tree
from tests.objectcli import tcw  # noqa: F401  (a fixture)

C = "docs/capabilities"
T = "docs/taxonomy"
CORE_LOGIN = ("id: cap-aaa111\nname: Login\nStatus: Supported\nSubject:\n- auth\n"
              "Feature: sign-in\n")
APP = ("id: app\nprojects:\n  upstream:\n    core: ../core\n"
       "capabilities:\n  extends:\n  - core\n")
OV = "Status: Experimental\noverrides: {pointer}\n"


def core(base: Path, extra: dict | None = None) -> Path:
    return make(base / "core", {"tcw-config.yaml": "id: core\n",
                                f"{C}/auth/login/meta.yaml": CORE_LOGIN,
                                f"{C}/auth/login/description.md": "Signs a user in.\n",
                                **(extra or {})})


def app(base: Path, files: dict, config: str = APP) -> Path:
    return make(base / "app", {"tcw-config.yaml": config, **files})


def migrate(tcw, root: Path, code: int = 0, *argv):
    done = tcw(["migrate", "--no-jira", *argv], root)
    assert done.code == code, done.err
    return done


def state(root: Path, id_path: str) -> dict:
    return yaml.safe_load((root / C / id_path / "tcw-capability.yaml").read_text())


def record(root: Path) -> dict:
    return yaml.safe_load((root / ".tcw/tcw-migration.yaml").read_text())


def said(done) -> list[str]:
    return done.err.splitlines()


# ── criterion 38: the moves ─────────────────────────────────────────────────

@pytest.mark.parametrize("pointer", ["cap-aaa111", "core/cap-aaa111"])
def test_an_override_moves_to_its_original_s_path(tcw, tmp_path, pointer):
    core(tmp_path)
    root = app(tmp_path, {
        f"{C}/ov/login/meta.yaml": "id: cap-ccc333\n" + OV.format(pointer=pointer),
        f"{C}/ov/login/description.md": "Signs a user in, by app.\n",
        f"{C}/ov/login/notes.md": "Notes.\n",
        f"{C}/ov/login/resources/flow.txt": "flow\n"})
    done = migrate(tcw, root)
    assert state(root, "auth/login") == {"tcw-version": state(root, "auth/login")
                                         ["tcw-version"], "Status": "Experimental"}
    assert (root / C / "auth/login/description.md").read_text() == "Signs a user in, by app.\n"
    assert (root / C / "auth/login/resources/notes.md").read_text() == "Notes.\n"
    assert (root / C / "auth/login/resources/flow.txt").read_text() == "flow\n"
    assert not [p for p in (root / C / "ov").rglob("*") if p.is_file()]
    assert record(root)["moved"] == {"ov/login": "auth/login"}
    assert record(root)["capability-ids"] == {"cap-ccc333": "auth/login"}
    assert f"move {C}/ov/login/notes.md -> {C}/auth/login/resources/notes.md: C13, C14" \
        in said(done)
    assert f"write {C}/auth/login/tcw-capability.yaml: C9, C10, C14" in said(done)


def test_4_0_shows_the_fields_3_x_showed(tcw, tmp_path):
    """3.x showed the override merged onto its original: the original's name,
    Subject and Feature, the override's Status and description."""
    base = core(tmp_path)
    root = app(tmp_path, {f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111"),
                          f"{C}/ov/login/description.md": "By app.\n"})
    migrate(tcw, base)
    migrate(tcw, root)
    shown = tcw(["capabilities", "show", "auth/login"], root)
    assert shown.code == 0, shown.err
    for text in ("overrides: core.capabilities/auth/login", "name: Login",
                 "Status: Experimental", "Subject: core.taxonomy/auth",
                 "Feature: core.taxonomy/sign-in", "By app."):
        assert text in shown.out, (text, shown.out)


def test_one_already_at_its_original_s_path_loses_only_its_key(tcw, tmp_path):
    core(tmp_path)
    root = app(tmp_path, {f"{C}/auth/login/meta.yaml": OV.format(pointer="cap-aaa111")})
    done = migrate(tcw, root)
    assert state(root, "auth/login")["Status"] == "Experimental"
    assert "overrides" not in state(root, "auth/login")
    assert not any(line.startswith("move ") for line in said(done))
    written = record(root) if (root / ".tcw/tcw-migration.yaml").exists() else {}
    assert "moved" not in written
    assert "  B9 " not in done.err


def test_a_reference_to_the_old_path_names_the_new_one(tcw, tmp_path):
    core(tmp_path)
    root = app(tmp_path, {
        f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111"),
        f"{C}/cli/report/meta.yaml": "name: Report\nStatus: Supported\n"
                                      "Blocked by: ov/login\n",
        f"{C}/cli/report/description.md": "See [it](tcw://C/ov/login).\n"})
    migrate(tcw, root)
    assert state(root, "cli/report")["Blocked by"] == "app.capabilities/auth/login"
    assert "(tcw://app.capabilities/auth/login)" in \
        (root / C / "cli/report/description.md").read_text()


def test_d3_and_d4(tcw, tmp_path):
    core(tmp_path, {f"{C}/auth/login/meta.yaml": CORE_LOGIN + "appendedDocs:\n- more.md\n",
                    f"{C}/auth/login/more.md": "More.\n"})
    make(tmp_path / "kid", {"tcw-config.yaml": "id: kid\nprojects:\n  parent:\n"
                                               "    app: ../app\n"})
    root = app(tmp_path, {f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111")},
               APP.replace("  upstream:", "  children:\n    kid: ../kid\n  upstream:"))
    done = migrate(tcw, root)
    where = f"  D3 {C}/auth/login/tcw-capability.yaml: lists no prependedDocs or " \
            f"appendedDocs while 'core''s auth/login does"
    assert any(line.startswith(where) for line in said(done)), done.err
    assert f"  D4 {C}/auth/login/tcw-capability.yaml: overrides a capability this project " \
           f"passes on; TCW 3 did not apply it in the projects below, and TCW 4 does" \
        in said(done)


def test_no_d4_without_children(tcw, tmp_path):
    core(tmp_path)
    root = app(tmp_path, {f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111")})
    assert "  D4 " not in migrate(tcw, root).err


# ── criterion 39: a migrated source ─────────────────────────────────────────

def test_a_migrated_source_is_read_through_its_record(tcw, tmp_path):
    base = core(tmp_path)
    migrate(tcw, base)
    assert record(base)["capability-ids"] == {"cap-aaa111": "auth/login"}
    root = app(tmp_path, {f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111")})
    migrate(tcw, root)
    assert state(root, "auth/login")["Status"] == "Experimental"


def test_a_migrated_source_with_no_record_is_b9(tcw, tmp_path):
    base = core(tmp_path)
    migrate(tcw, base)
    (base / ".tcw/tcw-migration.yaml").unlink()
    root = app(tmp_path, {f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111")})
    before = tree(root)
    done = migrate(tcw, root, 3)
    assert (f"  B9 {C}/ov/login/meta.yaml: overrides: cap-aaa111: names no capability of "
            f"the projects capabilities.extends names; 'core' is already migrated and "
            f"keeps no .tcw/tcw-migration.yaml to resolve it through") in done.err
    assert tree(root) == before


def test_a_record_naming_a_path_the_source_no_longer_has_is_b9(tcw, tmp_path):
    base = core(tmp_path)
    migrate(tcw, base)
    text = (base / ".tcw/tcw-migration.yaml").read_text()
    (base / ".tcw/tcw-migration.yaml").write_text(text.replace("auth/login", "auth/gone"))
    root = app(tmp_path, {f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111")})
    done = migrate(tcw, root, 3)
    line = next(l for l in said(done) if l.startswith("  B9 "))
    assert "'core''s .tcw/tcw-migration.yaml gives auth/gone, which 'core' no longer " \
           "has" in line
    assert "move the folder to the original's path and delete the overrides key by " \
           "hand" in done.err


# ── criterion 40: each B9 ───────────────────────────────────────────────────

B9_CASES = {
    "names nothing": ({f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-000000")},
                      "names no capability of the projects capabilities.extends names"),
    "ambiguous": ({f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111")},
                  "names more than one capability: 'core' auth/login, 'lib' auth/login"),
    "own": ({f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-bbb222"),
             f"{C}/mine/meta.yaml": "id: cap-bbb222\nname: Mine\nStatus: Supported\n"},
            f"names this project's own capability {C}/mine"),
    "taken": ({f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111"),
               f"{C}/auth/login/meta.yaml": "name: Mine\nStatus: Supported\n"},
              f"its original's path {C}/auth/login holds another of this project's "
              f"objects"),
    "two": ({f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111"),
             f"{C}/ov/again/meta.yaml": OV.format(pointer="core/cap-aaa111")},
            f"overrides the same capability as {C}/ov/again"),
}


@pytest.mark.parametrize("case", sorted(B9_CASES))
def test_each_b9(tcw, tmp_path, case):
    files, why = B9_CASES[case]
    core(tmp_path)
    config = APP
    if case == "ambiguous":
        make(tmp_path / "lib", {"tcw-config.yaml": "id: lib\n",
                                f"{C}/auth/login/meta.yaml": CORE_LOGIN})
        config = ("id: app\nprojects:\n  upstream:\n    core: ../core\n    lib: ../lib\n"
                  "capabilities:\n  extends:\n  - core\n  - lib\n")
    root = app(tmp_path, files, config)
    before = tree(root)
    done = migrate(tcw, root, 3)
    assert any(line.startswith("  B9 ") and why in line for line in said(done)), done.err
    assert tree(root) == before


def test_a_source_not_on_this_machine_is_b5(tcw, tmp_path):
    root = app(tmp_path, {f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111")})
    done = migrate(tcw, root, 3)
    assert f"  B5 tcw-config.yaml: C14: project 'core' is not on this machine" in done.err


# ── C15 and D2 (criterion 32's D2 half) ─────────────────────────────────────

def test_d2_for_a_term_and_a_capability_a_parent_also_has(tcw, tmp_path):
    make(tmp_path / "ws", {"tcw-config.yaml": "id: ws\nprojects:\n  children:\n"
                                              "    app: app\nwork:\n  tags:\n  - bug\n",
                           f"{C}/cli/x/meta.yaml": "name: X\nStatus: Supported\n",
                           f"{T}/auth/meta.yaml": "name: Auth\nkind: Vocabulary\n"})
    root = make(tmp_path / "ws/app", {
        "tcw-config.yaml": "id: app\nprojects:\n  parent:\n    ws: ..\n",
        f"{C}/cli/x/meta.yaml": "name: Mine\nStatus: Supported\n",
        f"{T}/auth/meta.yaml": "name: Auth here\nkind: Vocabulary\n"})
    done = migrate(tcw, root)
    assert (f"  D2 {C}/cli/x/tcw-capability.yaml: 'ws' also has cli/x; in TCW 4 this one "
            f"overrides it and is merged with it field by field") in said(done)
    assert f"  D2 {T}/auth/tcw-taxonomy.yaml: 'ws' also has auth;" in done.err
    assert (root / T / "auth/tcw-taxonomy.yaml").is_file()      # C15: nothing moves
    assert "work.tags: set by parent 'ws'" in done.err


# ── criterion 61: the stop point P4 ─────────────────────────────────────────

def test_a_run_stopped_after_the_override_moved_is_finished(tcw, tmp_path, monkeypatch):
    files = {f"{C}/ov/login/meta.yaml": OV.format(pointer="cap-aaa111"),
             f"{C}/ov/login/notes.md": "Notes.\n",
             f"{C}/ov/login/description.md": "By app.\n"}
    core(tmp_path / "one")
    whole = app(tmp_path / "one", files)
    migrate(tcw, whole)
    core(tmp_path / "two")
    root = app(tmp_path / "two", files)
    real = execute._perform

    def perform(step, at):
        if step.phase == "C":
            raise OSError(5, "made to fail")
        return real(step, at)
    with monkeypatch.context() as patch:
        patch.setattr(execute, "_perform", perform)
        stopped = tcw(["migrate", "--no-jira"], root)
    assert stopped.code == 1, stopped.err
    assert (root / C / "auth/login/resources/notes.md").is_file()
    assert (root / C / "ov/login/meta.yaml").is_file()          # its key still there
    done = migrate(tcw, root)
    assert "  B9 " not in done.err
    assert tree(root) == tree(whole)


# ── criterion 64: TCW 4's move keeps the record correct (plan Step 23) ──────

LIB = {"tcw-config.yaml": "id: lib\n",
       f"{C}/auth/login/meta.yaml": "id: cap-ddd444\nname: Login\nStatus: Supported\n"}
M = {"tcw-config.yaml": "id: core\nprojects:\n  upstream:\n    lib: ../lib\n"
                        "capabilities:\n  extends:\n  - lib\n",
     f"{C}/cli/meta.yaml": "id: cap-eee555\nname: CLI\nStatus: Supported\n",
     f"{C}/cli/x/meta.yaml": "id: cap-aaa111\nname: X\nStatus: Supported\n",
     f"{C}/ov/login/meta.yaml": "Status: Experimental\noverrides: cap-ddd444\n"}


def migrated_m(tcw, base: Path) -> Path:
    migrate(tcw, make(base / "lib", LIB))
    root = make(base / "core", M)
    migrate(tcw, root)
    assert record(root)["capability-ids"] == {"cap-eee555": "cli", "cap-aaa111": "cli/x"}
    assert record(root)["moved"] == {"ov/login": "auth/login"}
    return root


def test_a_rename_in_a_migrated_source_rewrites_its_record(tcw, tmp_path):
    m = migrated_m(tcw, tmp_path)
    done = tcw(["capabilities", "rename", "cli/x", "y"], m)
    assert done.code == 0, done.err
    assert record(m)["capability-ids"] == {"cap-eee555": "cli", "cap-aaa111": "cli/y"}
    assert "rewrote " in done.err and "capability-ids.cap-aaa111 cli/x -> cli/y" in done.err
    reader = app(tmp_path, {f"{C}/ov/x/meta.yaml": OV.format(pointer="core/cap-aaa111")})
    make(tmp_path / "core", {f"{T}/auth/meta.yaml": "name: Auth\nkind: Vocabulary\n"})
    migrate(tcw, reader)
    assert state(reader, "cli/y")["Status"] == "Experimental"


def test_a_value_below_the_moved_path_is_rewritten_too(tcw, tmp_path):
    m = migrated_m(tcw, tmp_path)
    done = tcw(["capabilities", "rename", "cli", "tool"], m)
    assert done.code == 0, done.err
    assert record(m)["capability-ids"] == {"cap-eee555": "tool", "cap-aaa111": "tool/x"}


def test_a_reader_s_reference_to_m_s_override_follows_m_s_moved(tcw, tmp_path):
    """M's own `ov/login -> auth/login` is under `moved:`, and a reader's
    `M/ov/login` becomes `M.capabilities/auth/login`. (TCW 4 refuses to
    rename an override, so a `moved:` value changes by a rename only in a
    project whose record outlived the override; the every-stop test below
    has one.)"""
    migrated_m(tcw, tmp_path)
    reader = app(tmp_path, {f"{C}/cli/r/meta.yaml": "name: R\nStatus: Supported\n"
                                                     "Blocked by: core/ov/login\n"})
    migrate(tcw, reader)
    assert state(reader, "cli/r")["Blocked by"] == "core.capabilities/auth/login"


def test_a_project_with_no_record_is_unchanged_by_the_record_rule(tcw, tmp_path):
    from tests.objectcli import obj, project
    root = project(tmp_path / "p", "demo", work={})
    obj(root, "capabilities", "cli", name="CLI", Status="Supported")
    done = tcw(["capabilities", "rename", "cli", "tool"], root)
    assert done.code == 0, done.err
    assert not (root / ".tcw/tcw-migration.yaml").exists()


def test_every_stop_of_a_capabilities_move_with_a_record(tcw, tmp_path):
    """TCW-114's every-stop test once more, on a project holding a record:
    the record's write is one more counted write, and a stop at any write is
    finished by running the move again."""
    from tests.move_stops import Fixture, every_stop
    from tests.objectcli import obj, project
    made = []

    def make_one():
        folder = tmp_path / f"run-{len(made)}"
        folder.mkdir()
        root = project(folder, "demo", work={})
        made.append(root)
        obj(root, "capabilities", "cli", name="CLI", Status="Supported")
        obj(root, "capabilities", "cli/y", name="Y", Status="Supported",
            parent="demo.capabilities/cli")
        (root / ".tcw/tcw-migration.yaml").write_text(
            "tcw-version: 4.0.0\ncapability-ids:\n  cap-aaa111: cli/y\n"
            "moved:\n  ov/y: cli/y\n")
        return Fixture(root)
    total = every_stop(pytest.MonkeyPatch.context, make_one,
                       lambda f: tcw(["capabilities", "rename", "cli", "tool"], f.root))
    # cli/y's parent, the record, the folder.
    assert total == 3
    assert record(made[0])["capability-ids"] == {"cap-aaa111": "tool/y"}
    assert record(made[0])["moved"] == {"ov/y": "tool/y"}
