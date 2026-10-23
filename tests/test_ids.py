"""Full identifiers and `tcw://` addresses: the grammar of TCW-110 Design 1
and 2, in `tcw/ids.py` (AC 1, AC 2)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from tcw import exit as codes
from tcw.ids import (FolderAddress, FullId, MalformedId, ThreeXReference,
                     identity, is_3x_address, looks_full, parse_address,
                     parse_full_id, parse_stored, same_target, sort_input)

ADDRESSES = json.loads(
    (Path(__file__).parent / "fixtures" / "tcw-addresses.json").read_text())
KEY = re.compile(r"[A-Z][A-Z0-9_]+-[0-9]+")


@pytest.mark.parametrize("text, parts", [
    ("a.taxonomy/x", ("a", "taxonomy", "x")),
    ("a-1.capabilities/cli/x_y", ("a-1", "capabilities", "cli/x_y")),
    ("p.work/TCW-120-add-login", ("p", "work", "TCW-120-add-login")),
])
def test_ac1_valid_identifiers_parse(text, parts):
    full_id = parse_full_id(text)
    assert (full_id.project, full_id.namespace, full_id.id_path) == parts
    assert str(full_id) == text


@pytest.mark.parametrize("text, rule", [
    ("a/x", "<project>.<namespace>/<id-path>"),
    ("A.work/x", "not a project ID"),
    ("a.Work/x", "not a namespace"),
    ("a.thing/x", "not a namespace"),
    ("a.work/", "no id-path"),
    ("a.work//x", "no empty part"),
    ("a.work/-x", "starting with a letter or digit"),
    ("a.work/x.y", "breaks the rule"),
    ("a.work/x y", "breaks the rule"),
    ("a.work/x%20", "breaks the rule"),
    ("local.work/x", "reserved"),
    ("a.work/" + "x" * 129, "longer than 128"),
])
def test_ac1_invalid_identifiers_are_refused_naming_the_rule(text, rule):
    with pytest.raises(MalformedId) as caught:
        parse_full_id(text)
    assert rule in str(caught.value)
    assert caught.value.code == codes.USAGE


def test_an_id_part_of_128_characters_is_accepted():
    assert parse_full_id("a.work/" + "x" * 128).id_path == "x" * 128


def test_a_namespace_other_than_the_one_expected_names_the_expected_one():
    with pytest.raises(MalformedId) as caught:
        parse_full_id("demo.taxonomy/term", "work")
    assert "work" in str(caught.value) and "taxonomy" in str(caught.value)


@pytest.mark.parametrize("case", ADDRESSES["accepted"], ids=lambda c: c["address"])
def test_ac2_accepted_addresses_parse_and_urlsplit_reads_the_same_path(case):
    address = case["address"]
    parsed = parse_address(address)
    text = parsed.address() if isinstance(parsed, FullId) else str(parsed)
    assert text == address
    assert urlsplit(address).path == case["path"]
    assert address[len("tcw://"):].partition("/")[1:] == ("/", case["path"][1:])


@pytest.mark.parametrize("address", ADDRESSES["refused"])
def test_ac2_refused_addresses(address):
    with pytest.raises(MalformedId):
        parse_address(address)


@pytest.mark.parametrize("address, rule", [
    ("tcw://p1/", "needs a namespace or .path"),
    ("tcw://p1.path", "'/' after .path"),
    ("tcw://p1.path/../x", "'.' or '..'"),
    ("tcw://p1.path/./x", "'.' or '..'"),
    ("tcw://p1.path/a//b", "no empty part"),
    ("tcw://p1.work/x/", "does not end in '/'"),
    ("tcw://p1.work/x#y", "'#' is not allowed"),
    ("tcw://p1.work/x?y", "'?' is not allowed"),
    ("tcw://p1.work/x%20", "'%' is not allowed"),
    ("tcw://p1.work/x y", "' ' is not allowed"),
    ("tcw://p1:80.work/x", "':' is not allowed"),
    ("tcw://u@p1.work/x", "'@' is not allowed"),
    ("tcw://P1.work/x", "lowercase"),
])
def test_ac2_each_refusal_names_its_rule(address, rule):
    with pytest.raises(MalformedId) as caught:
        parse_address(address)
    assert rule in str(caught.value)


def test_ac2_an_address_with_no_namespace_is_not_called_3x():
    with pytest.raises(MalformedId) as caught:
        parse_address("tcw://p1/")
    assert "TCW 3.x reference" not in str(caught.value)
    assert not isinstance(caught.value, ThreeXReference)
    assert not is_3x_address("tcw://p1/x")


def test_ac2_a_trailing_slash_is_ignored_and_case_is_not():
    docs, docs_slash = parse_address("tcw://p1.path/docs"), parse_address("tcw://p1.path/docs/")
    assert same_target(docs, docs_slash)
    assert not same_target(docs, parse_address("tcw://p1.path/Docs"))
    assert str(docs_slash) == "tcw://p1.path/docs/"


def test_a_folder_address_keeps_its_namespace():
    assert parse_address("tcw://p1.capabilities.path/cli") == FolderAddress(
        "p1", "capabilities", "cli")
    assert parse_address("tcw://p1.path/") == FolderAddress("p1", None, "")


@pytest.mark.parametrize("address", [
    "tcw://C/cli/x", "tcw://W/2026-01-01-x", "tcw://core/T/term"])
def test_3x_addresses_are_recognised_with_the_migrate_message(address):
    assert is_3x_address(address)
    with pytest.raises(ThreeXReference) as caught:
        parse_address(address)
    message = str(caught.value)
    assert message == (f"{address} is a TCW 3.x reference; TCW 4 writes "
                       f"tcw://<project>.<namespace>/<id-path> (run 'tcw migrate' "
                       f"in this project)")


def test_looks_full_is_a_dot_before_the_first_slash():
    assert looks_full("demo.work/x")
    assert looks_full("has.dot")
    assert not looks_full("cli/has.dot")
    assert not looks_full("demo/x")


@pytest.mark.parametrize("value", ["demo/x", "term", "roles/admin"])
def test_parse_stored_reports_3x_values(value):
    with pytest.raises(ThreeXReference) as caught:
        parse_stored(value, "taxonomy")
    assert "tcw migrate" in str(caught.value)


def test_parse_stored_reads_a_full_identifier_and_refuses_a_malformed_one():
    assert parse_stored("demo.work/x", "work") == FullId("demo", "work", "x")
    with pytest.raises(MalformedId):
        parse_stored("demo.work/x.y", "work")
    with pytest.raises(MalformedId):
        parse_stored("demo.taxonomy/x", "work")


@pytest.mark.parametrize("text, pattern, form", [
    ("demo.work/TCW-120-add", KEY, "a"),
    ("tcw://demo.work/TCW-120-add", KEY, "a"),
    ("TCW-120", KEY, "b"),
    ("demo.work/TCW-120", KEY, "c"),
    ("tcw://demo.work/TCW-120", KEY, "c"),
    ("TCW-120", None, "d"),
    ("demo.work/TCW-120", None, "a"),
    ("2026-01-01-x", KEY, "d"),
    ("demo/2026-01-01-x", KEY, "d"),
])
def test_sort_input_follows_design_3_1(text, pattern, form):
    assert sort_input(text, "work", pattern).form == form


def test_sort_input_forms_carry_what_they_name():
    assert sort_input("TCW-120", "work", KEY).key == "TCW-120"
    c = sort_input("demo.work/TCW-120", "work", KEY)
    assert c.key == "TCW-120" and c.full_id == FullId("demo", "work", "TCW-120")
    assert sort_input("cli/x", "capabilities").id_path == "cli/x"


@pytest.mark.parametrize("text", [
    "demo.taxonomy/term", "tcw://demo.taxonomy/term", "tcw://demo.path/x",
    "-x", "cli/has.dot", "has.dot", ""])
def test_sort_input_refuses_anything_else_as_a_usage_error(text):
    with pytest.raises(MalformedId) as caught:
        sort_input(text, "work", KEY)
    assert caught.value.code == codes.USAGE


def test_identity_is_full_id_and_owner():
    assert identity(FullId("core", "taxonomy", "term")) == {
        "full-id": "core.taxonomy/term", "owner": "core"}


class _OtherConstructor(FullId):
    """A stand-in for the work model's `Slug`: a subclass whose constructor
    takes other arguments."""

    def __init__(self, project, folder):
        object.__setattr__(self, "project", project)
        object.__setattr__(self, "namespace", "work")
        object.__setattr__(self, "id_path", folder)


def test_a_full_id_equals_a_subclass_instance_for_the_same_object():
    plain, sub = FullId("demo", "work", "x"), _OtherConstructor("demo", "x")
    assert plain == sub and sub == plain
    assert hash(plain) == hash(sub)
    assert plain in {sub} and sub in {plain}
    assert sorted([_OtherConstructor("demo", "y"), plain]) == [plain, FullId("demo", "work", "y")]
    assert FullId("demo", "work", "x") != FullId("demo", "taxonomy", "x")


def test_with_id_path_and_parts():
    full_id = FullId("demo", "capabilities", "cli/x")
    assert full_id.parts == ["cli", "x"]
    assert full_id.with_id_path("cli/y") == FullId("demo", "capabilities", "cli/y")
    assert full_id.address() == "tcw://demo.capabilities/cli/x"
