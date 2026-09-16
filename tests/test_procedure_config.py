"""`work.procedures` — every configuration mistake rejected by name, and reading
never broken by one. Spec criteria 8 and 11."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import PROCEDURE_IDS, Binding, Condition, parse_procedures
from tcw.store.fs import FsWorkStore, init


def only(raw) -> str:
    _parsed, found = parse_procedures(raw)
    assert len(found) == 1, found
    return found[0]


def test_nothing_configured_is_no_problem():
    assert parse_procedures(None) == ({}, [])


def test_a_valid_block_parses_in_declaration_order():
    parsed, found = parse_procedures({"search": [
        {"blob": "A"}, {"builtin": True},
        {"file": "x.md", "when": {"tags": ["bug"]}}]})
    assert found == []
    assert parsed["search"] == [
        Binding("blob", "A"), Binding("builtin", ""),
        Binding("file", "x.md", Condition(tags=("bug",)))]


def test_procedures_must_be_a_mapping():
    p = only([{"blob": "A"}])
    assert p.startswith("work.procedures:") and "mapping" in p


def test_an_unknown_procedure_id_names_the_known_ones():
    p = only({"postmortem": [{"blob": "A"}]})
    assert "work.procedures.postmortem" in p and "unknown procedure id" in p
    assert all(pid in p for pid in PROCEDURE_IDS)


def test_a_value_that_is_not_a_list_is_rejected():
    p = only({"search": {"prompt": [{"blob": "A"}]}})
    assert "work.procedures.search" in p and "list of bindings" in p


def test_an_empty_list_is_not_an_opt_out():
    p = only({"search": []})
    assert "work.procedures.search" in p and "empty" in p
    assert "{blob: ''}" in p


def test_a_bare_string_binding_is_rejected():
    p = only({"search": ["docs/search.md"]})
    assert "work.procedures.search[0]" in p and "must be a mapping" in p


def test_a_blank_file_is_rejected():
    p = only({"search": [{"file": "  "}]})
    assert "work.procedures.search[0]" in p and "non-blank" in p


def test_a_duplicate_binding_is_rejected():
    p = only({"search": [{"blob": "A"}, {"blob": "A"}]})
    assert "work.procedures.search" in p and "duplicate" in p


def test_command_names_generate():
    p = only({"search": [{"command": "./x.sh"}]})
    assert "'command' is not allowed in a procedure position" in p
    assert "use 'generate'" in p


def test_a_malformed_when_is_rejected():
    p = only({"search": [{"blob": "A", "when": {"status": "active"}}]})
    assert "work.procedures.search[0]" in p and "status" in p


# ── on disk ──────────────────────────────────────────────────────────────────


def _node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, "repo")
    return root


def _configure(root: Path, procedures) -> None:
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {})["procedures"] = procedures
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def test_a_missing_file_is_reported_by_the_store(tmp_path):
    root = _node(tmp_path)
    _configure(root, {"search": [{"file": "missing.md"}]})
    found = FsWorkStore.open(root).lifecycle_problems()
    assert any("work.procedures.search[0]" in p and "does not exist" in p
               for p in found), found


def test_a_symlink_out_of_the_node_is_reported(tmp_path):
    root = _node(tmp_path)
    (tmp_path / "outside.md").write_text("secrets\n")
    (root / "link.md").symlink_to(tmp_path / "outside.md")
    _configure(root, {"search": [{"file": "link.md"}]})
    found = FsWorkStore.open(root).lifecycle_problems()
    assert any("work.procedures.search[0]" in p and "outside the node root" in p
               for p in found), found


def test_a_valid_file_binding_adds_no_problem(tmp_path):
    root = _node(tmp_path)
    (root / "search.md").write_text("# Search\n")
    _configure(root, {"search": [{"file": "search.md"}]})
    store = FsWorkStore.open(root)
    assert store.lifecycle_problems() == []
    assert store.lifecycle_policy().procedure("search") == [Binding("file", "search.md")]


def test_tcw_validate_fails_on_a_bad_block(tmp_path):
    root = _node(tmp_path)
    _configure(root, {"serach": [{"blob": "A"}]})
    r = subprocess.run(["tcw", "validate"], cwd=root, capture_output=True, text=True)
    assert r.returncode != 0
    assert "work.procedures.serach" in r.stdout + r.stderr


@pytest.mark.parametrize("bad", [[{"blob": "A"}], {"search": [{"command": "x"}]}])
def test_a_malformed_block_does_not_break_reading(tmp_path, bad):
    """Criterion 11: reading is not validating."""
    root = _node(tmp_path)
    _configure(root, bad)
    store = FsWorkStore.open(root)
    assert store.lifecycle_policy().procedure("search") == []
    r = subprocess.run(["tcw", "work", "list"], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run(["tcw", "work", "stage", "prompt", "spec"], cwd=root,
                       capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip(), r.stderr
