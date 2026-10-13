"""`tcw capabilities` on the output contract (TCW-73 Design 1, 2, 4, 5.5, 8.6;
AC 8, 9, 10, 15, 16).

stdout carries the product, stderr names every file changed, each failure
exits with its class's code, and the retired `Planning doc` and `Tracker`
fields are refused on write and reported by the check.
"""

import io
import json
import sys

import pytest

from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, init
from tests.work.projects import make_project


@pytest.fixture
def project(tmp_path):
    root = make_project(tmp_path, "fx")
    init(["taxonomy", "capabilities"], root, "fx")
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


@pytest.fixture
def thing(project, run):
    assert run(project, "capabilities", "add", "ns/do-a-thing")[0] == 0
    return project


def test_add_prints_the_path_and_names_its_files(project, run):
    code, out, err = run(project, "capabilities", "add", "ns/do-a-thing", stdin="Body.\n")
    assert (code, out) == (0, "ns/do-a-thing\n")
    assert "wrote docs/capabilities/ns/do-a-thing/meta.yaml" in err.splitlines()
    assert "Body." in FsCapabilitiesStore.open(project).get("ns/do-a-thing").body


def test_set_prints_nothing(thing, run):
    code, out, err = run(thing, "capabilities", "set", "ns/do-a-thing",
                         "--status", "Supported")
    assert (code, out) == (0, "")
    assert err.splitlines() == ["wrote docs/capabilities/ns/do-a-thing/meta.yaml"]
    assert FsCapabilitiesStore.open(thing).get("ns/do-a-thing").status == "Supported"


def test_an_unknown_subject_is_a_usage_error(thing, run):
    assert run(thing, "capabilities", "set", "ns/do-a-thing",
               "--field", "Subject=nosuch")[0] == 2


def test_a_comma_in_a_field_value_sets_a_list(thing, run):
    taxonomy = FsTaxonomyStore.open(thing)
    taxonomy.add("A")
    taxonomy.add("B")
    code, _, err = run(thing, "capabilities", "set", "ns/do-a-thing", "--field", "Subject=a,b")
    assert code == 0, err
    assert "Subject: a, b" in run(thing, "capabilities", "show", "ns/do-a-thing")[1]


@pytest.mark.parametrize("fields", [
    ["--field", "Status=Supported", "--field", "Status=Missing"],
    ["--status", "Supported", "--field", "Status=Missing"],
    ["--field", "Status"],
    ["--field", "Planning doc=x"],
    ["--field", "Tracker=x"],
    [],
])
def test_bad_fields_are_usage_errors(thing, run, fields):
    code, out, _ = run(thing, "capabilities", "set", "ns/do-a-thing", *fields)
    assert (code, out) == (2, "")


def test_reset_of_a_local_capability_is_refused(thing, run):
    assert run(thing, "capabilities", "reset", "ns/do-a-thing")[0] == 3


def test_show_of_nothing_is_not_found(project, run):
    code, out, err = run(project, "capabilities", "show", "nosuch")
    assert (code, out) == (4, "")
    assert err.startswith("tcw capabilities show: ")


def test_rm_names_each_file_it_removed(thing, run):
    code, out, err = run(thing, "capabilities", "rm", "ns/do-a-thing")
    assert (code, out) == (0, "")
    assert sorted(err.splitlines()) == [
        "removed docs/capabilities/ns/do-a-thing/description.md",
        "removed docs/capabilities/ns/do-a-thing/meta.yaml"]


def test_list_and_search_print_one_path_per_line(thing, run):
    run(thing, "capabilities", "add", "ns/other", stdin="findme\n")
    assert run(thing, "capabilities", "list")[1] == "ns/do-a-thing\nns/other\n"
    assert run(thing, "capabilities", "list", "--local")[1] == "ns/do-a-thing\nns/other\n"
    assert run(thing, "capabilities", "search", "findme")[1] == "ns/other\n"
    data = json.loads(run(thing, "capabilities", "list", "--json")[1])
    assert data["schema"] == 1
    assert data["capabilities"][0] == {"path": "ns/do-a-thing", "name": "Do A Thing",
                                       "status": "Missing", "origin": "local"}
    shown = json.loads(run(thing, "capabilities", "show", "ns/do-a-thing", "--json")[1])
    assert shown["capability"]["fields"]["Status"] == "Missing"


def test_a_record_carrying_a_retired_field_is_a_check_error(thing):
    meta = thing / "docs" / "capabilities" / "ns" / "do-a-thing" / "meta.yaml"
    meta.write_text(meta.read_text() + "Planning doc: docs/plan/x.md\nTracker: X-1\n")
    findings = FsCapabilitiesStore.open(thing).check()
    retired = [f for f in findings if "migration-guide-2.8-to-3.0.0.md" in f.message]
    assert {f.severity for f in retired} == {"error"} and len(retired) == 2, findings


@pytest.mark.parametrize("argv", [
    ["capabilities", "ns/do-a-thing"], ["capabilities", "init"], ["capabilities", "check"],
    ["capabilities", "list", "--local-only"], ["capabilities", "add", "ns/x", "-s", "Missing"],
    ["capabilities", "extends", "base", "--rm"]])
def test_removed_spellings(thing, run, argv):
    assert run(thing, *argv)[0] == 2
