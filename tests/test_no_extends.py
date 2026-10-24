"""`extends` is gone in TCW 4.0 (TCW-112 Design 1.5, 6.6, 6.8; AC 15, 30 and
36): the `extends add|rm` commands and the store methods, the key in the
active project's configuration (refused), the same key in another project's
file (ignored), the override variables naming it, the federation cycle and
alias-collision checks, and the pre-2.5.0 store file's message."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tcw.store.base import CapabilitiesStore, TaxonomyStore
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore
from tests.test_inherited_config import made
from tests.test_project_files_cli import tcw as tcw_process
from tests.test_tree_inheritance import (INVOICE, capability, core_with_invoice_and_x,
                                         findings, home, inherits, listed, project,
                                         tcw, term)  # noqa: F401  (fixtures)

REPO = Path(__file__).resolve().parent.parent
APP_CONFIG = ".tcw/tcw-config.yaml"


def removed_message(axis: str) -> str:
    return f"'{axis}.extends' was removed in TCW 4.0"


# -- AC 15: the commands and the store methods -------------------------------------------


@pytest.mark.parametrize("argv", [
    ("taxonomy", "extends", "add", "core"),
    ("capabilities", "extends", "rm", "core"),
], ids=["taxonomy-extends-add", "capabilities-extends-rm"])
def test_ac15_the_extends_commands_are_no_such_command(tmp_path, tcw, argv):
    """AC 15, first sentence: `tcw taxonomy extends add core` and `tcw
    capabilities extends rm core` exit 2 (no such command)."""
    core = core_with_invoice_and_x(tmp_path)
    app = project(tmp_path, "app")
    inherits(app, core)
    before = (app / APP_CONFIG).read_bytes()
    ran = tcw(app, *argv)
    assert ran.code == 2, ran
    assert (app / APP_CONFIG).read_bytes() == before


@pytest.mark.parametrize("cls", [TaxonomyStore, CapabilitiesStore])
@pytest.mark.parametrize("method", ["extends_add", "extends_remove"])
def test_ac15_the_store_interfaces_have_no_extends_methods(cls, method):
    """AC 15: `TaxonomyStore` and `CapabilitiesStore` have no `extends_add`
    or `extends_remove`."""
    assert not hasattr(cls, method)


@pytest.mark.parametrize("cls", [FsTaxonomyStore, FsCapabilitiesStore])
def test_ac15_an_opened_filesystem_store_has_no_extends_attribute(tmp_path, cls):
    """AC 15: `FsTaxonomyStore` and `FsCapabilitiesStore` have no `extends`
    attribute, opened in a project that inherits from a parent."""
    core = core_with_invoice_and_x(tmp_path)
    app = project(tmp_path, "app")
    inherits(app, core)
    store = cls.open(app)
    assert not hasattr(store, "extends")
    assert not hasattr(cls, "extends")


# -- AC 15: the key ----------------------------------------------------------------------


@pytest.mark.parametrize("axis", ["taxonomy", "capabilities"])
def test_ac15_the_key_in_the_active_project_makes_the_axis_commands_exit_1(
        tmp_path, tcw, axis):
    """AC 15: `<axis>: {extends: [core]}` in `app`'s `.tcw/tcw-config.yaml`
    makes `tcw <axis> list` exit 1 with a message containing
    `'<axis>.extends' was removed in TCW 4.0` and `parents:`."""
    core = core_with_invoice_and_x(tmp_path)
    app = project(tmp_path, "app", config=f"{axis}:\n  extends:\n  - core\n")
    inherits(app, core)
    ran = tcw(app, axis, "list")
    assert ran.code == 1, ran
    assert removed_message(axis) in ran.err and "parents:" in ran.err, ran
    assert ran.out == ""


@pytest.mark.parametrize("axis", ["taxonomy", "capabilities"])
def test_ac15_the_key_in_the_active_project_is_a_validate_error_at_its_file(
        tmp_path, tcw, axis):
    """AC 15: the same key makes `tcw validate` report an error at
    `.tcw/tcw-config.yaml`."""
    core = core_with_invoice_and_x(tmp_path)
    app = project(tmp_path, "app", config=f"{axis}:\n  extends:\n  - core\n")
    inherits(app, core)
    ran = tcw(app, "validate")
    assert ran.code == 1, ran
    errors = [line for line in findings(ran) if removed_message(axis) in line]
    assert errors, findings(ran)
    assert all(line.startswith("error: ") for line in errors)
    assert any(line.split(": ", 2)[1].endswith(APP_CONFIG) for line in errors), errors


@pytest.mark.parametrize("axis", ["taxonomy", "capabilities"])
def test_ac15_the_key_in_a_parents_file_is_ignored(tmp_path, tcw, axis):
    """AC 15: the same key in `core`'s file, `core` being `app`'s parent,
    leaves `tcw taxonomy list` in `app` exiting 0 (listing `core`'s term)."""
    core = core_with_invoice_and_x(tmp_path)
    (core / APP_CONFIG).write_text(
        (core / APP_CONFIG).read_text() + f"{axis}:\n  extends:\n  - elsewhere\n")
    app = project(tmp_path, "app")
    inherits(app, core)
    assert listed(tcw(app, "taxonomy", "list")) == [INVOICE]


@pytest.mark.parametrize("name", ["TCW_TAXONOMY_EXTENDS__APP",
                                  "TCW_CAPABILITIES_EXTENDS__APP"])
def test_ac15_an_override_variable_naming_extends_names_no_key(
        tmp_path, monkeypatch, name):
    """AC 15, last sentence: with `<name>=core` set, `tcw work list` in `app`
    exits 1 with TCW-109 Design 4.3's message (`no configuration key is
    written`), not its message for a shared key (`is a shared key`)."""
    app = made(tmp_path, "app")
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    (tmp_path / "home").mkdir(exist_ok=True)
    env = {"TCW_NO_PERSONAL_CONFIG": None, "HOME": str(tmp_path / "home"), name: "core"}
    ran = tcw_process(app, "work", "list", env=env)
    assert ran.code == 1, ran
    assert name in ran.err and "no configuration key is written" in ran.err, ran
    assert "is a shared key" not in ran.err, ran


# -- AC 30: the checks that go -----------------------------------------------------------


def test_ac30_a_top_level_term_named_like_a_parent_is_not_a_collision(tmp_path, tcw):
    """AC 30, first sentence: `app` inherits from `core` and has a top-level
    term folder named `core`; `tcw validate` reports no finding containing
    `collides with local top-level`."""
    core = core_with_invoice_and_x(tmp_path)
    app = project(tmp_path, "app")
    term(app, "core", name="Core", kind="Vocabulary", description="")
    capability(app, "core", name="Core", Status="Missing", description="")
    inherits(app, core)
    ran = tcw(app, "validate")
    assert not any("collides with local top-level" in line
                   for line in ran.out.splitlines() + ran.err.splitlines()), ran


def test_ac30_no_code_names_the_federation_cycle_or_collision_checks():
    """AC 30, second sentence: `grep -rn "cycle in taxonomy federation\\|cycle
    in capability federation\\|collides with local top-level" tcw/` finds
    nothing."""
    found = subprocess.run(
        ["grep", "-rn", "cycle in taxonomy federation\\|cycle in capability federation"
         "\\|collides with local top-level", str(REPO / "tcw")],
        capture_output=True, text=True)
    assert found.returncode == 1 and found.stdout == "", found.stdout


# -- AC 36: the pre-2.5.0 store file ------------------------------------------------------


def test_ac36_a_pre_2_5_store_file_points_at_parents_not_extends(tmp_path, tcw):
    """AC 36: a `config.yaml` at `app`'s taxonomy root gives the error (the
    one `tcw validate` reports at that file, Design 6.8) whose message
    contains `parents:` and does not contain `extends`."""
    app = project(tmp_path, "app")
    (app / "docs" / "taxonomy" / "config.yaml").write_text("extends: [core]\n")
    checked = tcw(app, "validate")
    assert checked.code == 1, checked
    errors = [line for line in findings(checked)
              if line.split(": ", 2)[1].endswith("docs/taxonomy/config.yaml")]
    assert len(errors) == 1, findings(checked)
    assert errors[0].startswith("error: ")
    message = errors[0].split(": ", 2)[2]
    assert "parents:" in message and "extends" not in message, errors
