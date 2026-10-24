"""Taxonomy and capabilities inherited through the parent links (TCW-112
Design 1.1, 1.2, 1.3; AC 1, 2, 3, 4, 17, 18 and 19).

Every project here is a git repository under the test's own folder, with its
stores at the defaults, its parents named by `parents:` and located by a
manifest entry; no fixture writes `extends`. Commands run in this process
through `tcw.cli.main`; the suite's autouse fixtures keep personal
configuration off and point `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` into the
test's folder, and `home` below points `HOME` there too, so nothing reads the
real user's files.

The helpers at the top are shared with `tests/test_no_extends.py` and
`tests/test_tree_parent_missing.py`."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tcw.cli import main
from tests.projectfiles import connect_projects, write_config, write_manifest
from tests.statefiles import CAPABILITY_STATE, TAXONOMY_STATE, write_state_data


# -- helpers ----------------------------------------------------------------------------


@dataclass
class Ran:
    code: int
    out: str
    err: str


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """`HOME` inside the test, so no command reads the real home folder."""
    folder = tmp_path / "home"
    folder.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(folder))
    return folder


@pytest.fixture
def tcw(monkeypatch, capsys):
    """`tcw <argv>` in this process from `cwd`, with `stdin` as its input."""
    def run(cwd: Path, *argv: str, stdin: str = "") -> Ran:
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(list(argv))
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Ran(code, captured.out, captured.err)
    return run


def project(tmp_path: Path, project_id: str, *, stores=("taxonomy", "capabilities"),
            config: str = "") -> Path:
    """A project `project_id` at `tmp_path/<id>`: a git repository holding the
    default folder of each store in `stores`, and a configuration holding its
    ID and then `config` as given."""
    root = tmp_path / project_id
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for tree in stores:
        (root / "docs" / tree).mkdir(parents=True)
    write_config(root, f"id: {project_id}\n{config}")
    return root


def inherits(child: Path, *parents: Path, inherit="all", located=None) -> None:
    """`child` names each of `parents` under `parents:` with `inherit`, and
    its manifest locates each by the folder next to it (or, for a project ID
    in `located`, by the folder given there)."""
    connect_projects(child, "parent", *(p.name for p in parents), inherit=inherit)
    write_manifest(child, {p.name: f"../{p.name}" for p in parents})
    if located:
        write_manifest(child, located)


def term(root: Path, path: str, *, description: str | None = None, **fields) -> Path:
    """A term folder holding its state file with `fields`, and a
    `description.md` holding `description` when one is given."""
    folder = root / "docs" / "taxonomy" / path
    write_state_data(folder / TAXONOMY_STATE, fields)
    if description is not None:
        (folder / "description.md").write_text(description, encoding="utf-8")
    return folder


def capability(root: Path, path: str, *, description: str | None = None,
               store: str = "docs/capabilities", **fields) -> Path:
    """A capability folder holding its state file with `fields`, and a
    `description.md` holding `description` when one is given."""
    folder = root / store / path
    write_state_data(folder / CAPABILITY_STATE, fields)
    if description is not None:
        (folder / "description.md").write_text(description, encoding="utf-8")
    return folder


def listed(ran: Ran) -> list[str]:
    """The identifiers a `list` printed."""
    assert ran.code == 0, ran
    return [line for line in ran.out.splitlines() if line.strip()]


def record(ran: Ran, key: str) -> dict:
    """The record a `show --json` printed under `key`."""
    assert ran.code == 0, ran
    return json.loads(ran.out)[key]


def findings(ran: Ran) -> list[str]:
    """The finding lines `tcw validate` printed."""
    return [line for line in ran.out.splitlines()
            if line.startswith(("error:", "warning:", "unresolved:"))]


def core_with_invoice_and_x(tmp_path: Path) -> Path:
    """AC 1's `core`: a term `invoice` and a capability `cli/x`."""
    core = project(tmp_path, "core")
    term(core, "invoice", name="Invoice", kind="Vocabulary", description="")
    capability(core, "cli/x", name="X", Status="Missing", description="")
    return core


INVOICE = "core.taxonomy/invoice"
CORE_X = "core.capabilities/cli/x"


# -- AC 1: inherited through the parent link ---------------------------------------------


def test_ac1_app_lists_both_of_cores_objects_through_its_parent_link(tmp_path, tcw):
    """AC 1, first sentence: `app` inherits from `core` and has neither
    object, and both `list` commands list `core`'s."""
    core = core_with_invoice_and_x(tmp_path)
    app = project(tmp_path, "app")
    inherits(app, core)
    assert listed(tcw(app, "taxonomy", "list", "--scope", "up")) == [INVOICE]
    assert listed(tcw(app, "capabilities", "list", "--scope", "up")) == [CORE_X]


def test_ac1_show_of_an_inherited_term_names_core_as_owner_and_no_override(tmp_path, tcw):
    """AC 1, last sentence: `show invoice` has `full-id`
    `core.taxonomy/invoice`, `owner` `core` and `overrides` null."""
    core = core_with_invoice_and_x(tmp_path)
    app = project(tmp_path, "app")
    inherits(app, core)
    shown = record(tcw(app, "taxonomy", "show", "invoice", "--json", "--scope", "up"), "term")
    assert shown["full-id"] == INVOICE
    assert shown["owner"] == "core"
    assert "overrides" in shown and shown["overrides"] is None


# -- AC 2: per-parent inherit ------------------------------------------------------------


@pytest.mark.parametrize("inherit, terms, capabilities", [
    (["taxonomy"], [INVOICE], []),
    ("none", [], []),
    (["capabilities"], [], [CORE_X]),
    (["taxonomy", "capabilities"], [INVOICE], [CORE_X]),
    (["config"], [], []),
], ids=["taxonomy", "none", "capabilities", "both-axes", "config-only"])
def test_ac2_each_inherit_form_passes_only_the_axes_it_names(
        tmp_path, tcw, inherit, terms, capabilities):
    """AC 2: with `parents: [{id: core, inherit: ...}]`, `[taxonomy]` passes
    only the term, `none` neither, `[capabilities]` only the capability (and
    the two axes both, `[config]` neither)."""
    core = core_with_invoice_and_x(tmp_path)
    app = project(tmp_path, "app")
    inherits(app, core, inherit=inherit)
    assert listed(tcw(app, "taxonomy", "list", "--scope", "up")) == terms
    assert listed(tcw(app, "capabilities", "list", "--scope", "up")) == capabilities


# -- AC 3: several levels ----------------------------------------------------------------


def _three_levels(tmp_path: Path, lib_inherits="all") -> Path:
    core = core_with_invoice_and_x(tmp_path)
    lib = project(tmp_path, "lib")
    term(lib, "money", name="Money", kind="Vocabulary", description="")
    inherits(lib, core, inherit=lib_inherits)
    app = project(tmp_path, "app")
    inherits(app, lib)
    return app


def test_ac3_app_inherits_through_two_levels(tmp_path, tcw):
    """AC 3, first sentences: `lib` inherits from `core`, `app` from `lib`;
    `app` lists `core.taxonomy/invoice` and `lib.taxonomy/money`."""
    app = _three_levels(tmp_path)
    assert set(listed(tcw(app, "taxonomy", "list", "--scope", "up"))) == {INVOICE, "lib.taxonomy/money"}
    assert listed(tcw(app, "capabilities", "list", "--scope", "up")) == [CORE_X]


def test_ac3_a_middle_link_passing_only_config_stops_cores_terms(tmp_path, tcw):
    """AC 3, last sentence: with `lib`'s link to `core` set to `inherit:
    [config]`, `app` does not list `core.taxonomy/invoice`."""
    app = _three_levels(tmp_path, lib_inherits=["config"])
    assert listed(tcw(app, "taxonomy", "list", "--scope", "up")) == ["lib.taxonomy/money"]
    assert listed(tcw(app, "capabilities", "list", "--scope", "up")) == []


# -- AC 4: a parent with no store --------------------------------------------------------


def test_ac4_a_parent_with_no_store_contributes_nothing(tmp_path, tcw):
    """AC 4: `app` has `parents: [ws, core]`, `ws` having no taxonomy or
    capabilities store and declaring none; both `list` commands exit 0 and
    list `core`'s objects."""
    ws = project(tmp_path, "ws", stores=())
    core = core_with_invoice_and_x(tmp_path)
    app = project(tmp_path, "app")
    inherits(app, ws, core)
    assert listed(tcw(app, "taxonomy", "list", "--scope", "up")) == [INVOICE]
    assert listed(tcw(app, "capabilities", "list", "--scope", "up")) == [CORE_X]


# -- AC 17: a view-only parent not on this machine ---------------------------------------


@pytest.mark.parametrize("where", ["missing-folder", "no-manifest-entry"])
def test_ac17_a_parent_passing_nothing_need_not_be_on_this_machine(tmp_path, tcw, where):
    """AC 17: `app` has `parents: [{id: ws, inherit: none}, core]` and `ws` is
    not on this machine (its manifest entry names a folder that does not
    exist, or there is no entry); both `list` commands exit 0 and list
    `core`'s objects."""
    core = core_with_invoice_and_x(tmp_path)
    app = project(tmp_path, "app", config="parents:\n- id: ws\n  inherit: none\n- core\n")
    entries = {"core": "../core"}
    if where == "missing-folder":
        entries["ws"] = "../ws"                      # no folder `ws` is made
    write_manifest(app, entries)
    assert not (tmp_path / "ws").exists()
    assert listed(tcw(app, "taxonomy", "list", "--scope", "up")) == [INVOICE]
    assert listed(tcw(app, "capabilities", "list", "--scope", "up")) == [CORE_X]


# -- AC 18: a parent whose store cannot be read -------------------------------------------


def core_with_unprovisioned_taxonomy(tmp_path: Path) -> Path:
    """AC 18's `core`: its taxonomy store is declared in a repository that
    has not been provisioned here, so opening it raises
    `StoreNotProvisioned`; `app` inherits from it. Returns `app`."""
    core = project(tmp_path, "core", stores=("capabilities",), config=(
        "taxonomy:\n  repository:\n    url: https://example.invalid/core-taxonomy.git\n"))
    capability(core, "cli/x", name="X", Status="Missing", description="")
    app = project(tmp_path, "app")
    term(app, "money", name="Money", kind="Vocabulary", description="")
    inherits(app, core)
    return app


def test_ac18_the_store_really_raises_store_not_provisioned(tmp_path):
    """AC 18's premise: opening `core`'s taxonomy store raises
    `StoreNotProvisioned`, so the tests below test that case."""
    from tcw.store.base import StoreNotProvisioned
    from tcw.store.fs import FsTaxonomyStore
    core_with_unprovisioned_taxonomy(tmp_path)
    with pytest.raises(StoreNotProvisioned):
        FsTaxonomyStore.open(tmp_path / "core")


def test_ac18_list_exits_7_when_a_parents_store_cannot_be_read(tmp_path, tcw):
    """AC 18, the `tcw taxonomy list` sentence: it exits 7 with a message
    containing `whose taxonomy store cannot be read here`."""
    app = core_with_unprovisioned_taxonomy(tmp_path)
    ran = tcw(app, "taxonomy", "list", "--scope", "up")
    assert ran.code == 7, ran
    assert "whose taxonomy store cannot be read here" in ran.err, ran
    assert ran.out == ""


def test_ac18_validate_reports_could_not_check_and_exits_0(tmp_path, tcw):
    """AC 18, the `tcw validate` sentence: exit 0 with an `unresolved`
    finding at `.tcw/tcw-config.yaml` containing `could not check the
    taxonomy inherited from 'core'`."""
    app = core_with_unprovisioned_taxonomy(tmp_path)
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    matching = [line for line in findings(ran)
                if "could not check the taxonomy inherited from 'core'" in line]
    assert len(matching) == 1, findings(ran)
    assert matching[0].startswith("unresolved: ")
    assert ".tcw/tcw-config.yaml" in matching[0].split(": ", 2)[1]


# -- AC 19: a source in another repository ------------------------------------------------


def test_ac19_a_source_store_at_its_own_configured_path(tmp_path, tcw):
    """AC 19: `core` is its own git repository beside `app`'s, with
    `capabilities.path: ledger`; `app` lists `core`'s capabilities from
    `core/ledger` (and not from `core/docs/capabilities`, which holds a
    decoy)."""
    core = project(tmp_path, "core", config="capabilities:\n  path: ledger\n")
    (core / "ledger").mkdir()
    capability(core, "cli/x", store="ledger", name="X", Status="Missing", description="")
    capability(core, "cli/decoy", name="Decoy", Status="Missing", description="")
    app = project(tmp_path, "app")
    inherits(app, core)
    assert (app / ".git").is_dir() and (core / ".git").is_dir()
    assert listed(tcw(app, "capabilities", "list", "--scope", "up")) == [CORE_X]
