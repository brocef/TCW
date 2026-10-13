"""`tcw taxonomy` on the output contract (TCW-73 Design 1, 2, 4, 8; AC 2, 8,
9, 10).

stdout carries the product, stderr names every file changed, and each failure
exits with its class's code.
"""

import io
import json
import sys

import pytest

from tcw.cli import main
from tcw.store.fs import init
from tests.work.projects import make_project


@pytest.fixture
def project(tmp_path):
    root = make_project(tmp_path, "fx")
    init(["taxonomy"], root, "fx")
    return root


@pytest.fixture
def run(monkeypatch, capsys):
    def run(root, *argv, stdin=""):
        monkeypatch.chdir(root)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(list(argv))
        except SystemExit as stop:
            code = stop.code
        captured = capsys.readouterr()
        return code, captured.out, captured.err
    return run


def test_a_mistyped_command_is_a_usage_error_not_a_lookup(project, run):
    code, out, err = run(project, "taxonomy", "lst")
    assert (code, out) == (2, "")
    assert "list" in err and "no such term" not in err


def test_add_prints_the_path_and_names_its_files(project, run):
    code, out, err = run(project, "taxonomy", "add", "Widget", stdin="A small part.\n")
    assert (code, out) == (0, "widget\n")
    assert err.splitlines() == ["wrote docs/taxonomy/widget/meta.yaml",
                                "wrote docs/taxonomy/widget/description.md"]
    assert run(project, "taxonomy", "add", "Widget")[0] == 3


def test_show_of_nothing_is_not_found(project, run):
    code, out, err = run(project, "taxonomy", "show", "nosuch")
    assert (code, out) == (4, "")
    assert err.startswith("tcw taxonomy show: ")


def test_rm_of_a_referenced_term_is_refused(project, run):
    run(project, "taxonomy", "add", "Invoice")
    run(project, "taxonomy", "add", "Payment")
    meta = project / "docs" / "taxonomy" / "payment" / "meta.yaml"
    meta.write_text(meta.read_text().replace("relatesTo: []", "relatesTo: [invoice]"))
    code, out, err = run(project, "taxonomy", "rm", "invoice")
    assert (code, out) == (3, "")
    assert "payment" in err


def test_rm_names_each_file_it_removed(project, run):
    run(project, "taxonomy", "add", "Widget")
    code, out, err = run(project, "taxonomy", "rm", "widget")
    assert (code, out) == (0, "")
    assert sorted(err.splitlines()) == ["removed docs/taxonomy/widget/description.md",
                                        "removed docs/taxonomy/widget/meta.yaml"]


def test_extends_add_prints_nothing_and_names_the_config(tmp_path, run):
    base = make_project(tmp_path, "base")
    init(["taxonomy"], base, "base")
    project = make_project(tmp_path, "fx", config={})
    init(["taxonomy"], project, "fx")
    from tests.work.projects import connect
    connect(project, base, "upstream")
    code, out, err = run(project, "taxonomy", "extends", "add", "base")
    assert (code, out) == (0, ""), err
    assert err.splitlines() == ["wrote tcw-config.yaml"]


def test_list_and_search_print_one_path_per_line(project, run):
    run(project, "taxonomy", "add", "Widget", stdin="small\n")
    run(project, "taxonomy", "add", "Gear", "--parent", "widget")
    assert run(project, "taxonomy", "list")[1] == "widget\nwidget/gear\n"
    assert run(project, "taxonomy", "search", "small")[1] == "widget\n"
    data = json.loads(run(project, "taxonomy", "list", "--json")[1])
    assert data["schema"] == 1
    assert data["terms"][1] == {"path": "widget/gear", "name": "Gear",
                                "kind": "Vocabulary", "origin": "local"}


def test_show_json(project, run):
    run(project, "taxonomy", "add", "Widget", stdin="small\n")
    data = json.loads(run(project, "taxonomy", "show", "widget", "--json")[1])
    assert data["schema"] == 1 and data["term"]["path"] == "widget"
    assert data["term"]["description"].strip() == "small"


@pytest.mark.parametrize("argv", [["taxonomy", "widget"], ["taxonomy", "init"],
                                  ["taxonomy", "check"],
                                  ["taxonomy", "add", "X", "a description"],
                                  ["taxonomy", "add", "X", "-s", "x"]])
def test_removed_spellings(project, run, argv):
    assert run(project, *argv)[0] == 2
