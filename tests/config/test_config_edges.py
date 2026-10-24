"""Edge cases of reading and showing configuration that TCW-72's review left
(the pre-freeze clean-up, P1, P2 and P5)."""

from __future__ import annotations

import pytest
import yaml

from tcw.config_cli import _scalar
from tests.config.conftest import tcw
from tests.projectfiles import write_config_file

LIST_KEY = "? [a]\n: 1\n"


# -- P1: a key that is a list or mapping -------------------------------------------------


@pytest.mark.parametrize("which", ["project", "local"])
def test_a_list_as_a_key_names_the_file_without_a_traceback(personal, which):
    target = personal.project_file if which == "project" else personal.local_file
    if which == "project":
        write_config_file(target, "id: p\n" + LIST_KEY)
    else:
        personal.local(LIST_KEY)
    result = tcw(personal.root, "project", "config")
    assert result.code == 1, result
    assert target.name in result.err
    assert "Traceback" not in result.err
    assert "a mapping key must be a single value" in result.err


# -- P2: two layers writing the same empty mapping ---------------------------------------


def test_an_empty_mapping_written_twice_is_blamed_on_the_higher_layer(personal):
    personal.project({"work": {"procedures": {"custom": {}}}})
    personal.local({"work": {"procedures": {"custom": {}}}})
    result = tcw(personal.root, "project", "config", "--origin")
    [line] = [l for l in result.out.splitlines() if "custom:" in l]
    assert line.endswith("custom: {}  # local: .tcw/tcw-config.local.yaml"), line


# -- P5: values only an unknown key can hold ---------------------------------------------


@pytest.mark.parametrize("value", [b"\x00binary\xff", {1, "a", 2.5, None},
                                   frozenset({"x"}), set()],
                         ids=["bytes", "mixed set", "frozenset", "empty set"])
def test_a_binary_or_set_value_is_one_line_that_reads_back(value):
    line = _scalar(value)
    assert "\n" not in line
    assert yaml.safe_load(f"k: {line}\n") == {"k": value}


def test_config_show_writes_an_unknown_keys_binary_and_set_on_one_line(personal):
    write_config_file(personal.project_file,
        "id: p\nextra:\n  blob: !!binary AGJpbmFyef8=\n"
        "  members: !!set {1: null, a: null}\n")
    result = tcw(personal.root, "project", "config")
    assert result.code == 0, result
    lines = [l.strip() for l in result.out.splitlines()
             if l.strip().startswith(("blob:", "members:"))]
    assert len(lines) == 2, result.out
    assert yaml.safe_load(result.out)["extra"] == {"blob": b"\x00binary\xff",
                                                   "members": {1, "a"}}
