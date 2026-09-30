"""Changing an item whose `state.yaml` cannot be read is refused with a message
naming the item, the file and `tcw validate` — never the YAML parser's bare text
(spec: 2026-09-30-name-the-item-and-file-when-editing-an-item-whose-state-yaml-cannot-be-read)."""

import subprocess

import pytest

from test_cross_node_blocker_cycles import new, node, state_bytes, store, tcw

BARE = '"<unicode string>"'          # PyYAML's name for a string it was handed


@pytest.fixture
def project(tmp_path):
    root = node(tmp_path / "p", "p")
    st = store(tmp_path, "p")
    damaged, other = new(st, "Damaged"), new(st, "Other")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    (root / "docs/work/backlog" / damaged / "state.yaml").write_text("key: [unclosed\n")
    return root, st, damaged, other


def assert_named(out, slug):
    assert out.returncode == 1, (out.stdout, out.stderr)
    assert slug in out.stderr, out.stderr
    assert f"docs/work/backlog/{slug}/state.yaml" in out.stderr, out.stderr
    assert "tcw validate" in out.stderr, out.stderr
    assert BARE not in out.stderr, out.stderr
    assert "Traceback" not in out.stderr, out.stderr


@pytest.mark.parametrize("flags", [["--tag", "bug"], ["--title", "x"],
                                   ["--priority", "2"]])
def test_edit_names_the_item_and_file(project, flags):
    root, st, damaged, _ = project
    before = state_bytes(st, damaged)
    out = tcw(root, "edit", damaged, *flags)
    assert_named(out, damaged)
    assert state_bytes(st, damaged) == before


def test_adding_a_blocker_to_a_damaged_item_names_it(project):
    root, st, damaged, other = project
    before = state_bytes(st, damaged)
    out = tcw(root, "edit", damaged, "--blocked-by", other)
    assert_named(out, damaged)
    assert state_bytes(st, damaged) == before


def test_start_names_the_file_and_validate(project):
    root, _, damaged, _ = project
    assert_named(tcw(root, "start", damaged), damaged)


def test_validate_lists_the_damaged_file(project):
    root, _, damaged, _ = project
    out = subprocess.run(["tcw", "validate"], cwd=root, capture_output=True, text=True)
    assert out.returncode != 0
    assert f"docs/work/backlog/{damaged}/state.yaml" in out.stdout + out.stderr


def test_a_yaml_error_names_the_file_it_came_from(project):
    root, *_ = project
    (root / "tcw-config.yaml").write_text("key: [\n")
    out = tcw(root, "list")
    assert out.returncode == 1, out.stderr
    assert f'in "{root / "tcw-config.yaml"}"' in out.stderr, out.stderr
    assert BARE not in out.stderr, out.stderr
    # The file's name must not cost the parser's excerpt of the line and caret.
    # Without the excerpt, the position line ends with no colon and no caret.
    assert 'line 2, column 1:\n' in out.stderr and "^" in out.stderr, out.stderr


def test_validate_keeps_the_excerpt(project):
    root, _, damaged, _ = project
    out = subprocess.run(["tcw", "validate"], cwd=root, capture_output=True, text=True)
    text = out.stdout + out.stderr
    assert "key: [unclosed" in text and "^" in text, text
    assert BARE not in text, text
