"""Plain `tcw validate` in Jira mode needs no network and no credentials
(TCW-71 AC 2, AC 19)."""

import pytest
import yaml

from tcw.cli import main
from tcw.work.jira import client as jira
from tcw.work.jira.backend import link_exists
from tests.work.jira.conftest import EMAIL_ENV, TOKEN_ENV
from tests.work.jira.fake import SITE
from tests.work.projects import connect, make_project, write_item
from tests.projectfiles import config_file, write_config_file
from tests.projectfiles import write_connected_config_file


@pytest.fixture
def offline(jira_project, monkeypatch):
    """No credentials, and any request fails the test."""
    def no_network(*args, **kwargs):
        pytest.fail("plain validate made a request")
    monkeypatch.setattr(jira.JiraClient, "_request", no_network)
    monkeypatch.delenv(EMAIL_ENV)
    monkeypatch.delenv(TOKEN_ENV)
    return jira_project


def validate(project, monkeypatch, capsys):
    monkeypatch.chdir(project.root)
    code = main(["validate"])
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def folder(project, name, ticket=None, **extra):
    path = project.work / name
    path.mkdir(parents=True)
    key = "-".join(name.split("-")[:2])
    data = {"ticket": ticket or f"{SITE}/browse/{key}", **extra}
    (path / "item.yaml").write_text(yaml.safe_dump(data))
    return path


def test_a_clean_tree_is_clean(offline, monkeypatch, capsys):
    folder(offline, "TCW-1-x")
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 0, text


@pytest.mark.parametrize("make, words", [
    (lambda p: folder(p, "TCW-1-x", stage="spec"), "exactly one key, ticket; it also has stage"),
    (lambda p: folder(p, "TCW-1-x", ticket="https://other.atlassian.net/browse/TCW-1"),
     "is not on"),
    (lambda p: folder(p, "TCW-1-x", ticket=f"{SITE}/browse/TCW-2"), "names TCW-2"),
    (lambda p: (folder(p, "TCW-5-a"), folder(p, "TCW-5-b")), "the key TCW-5 names 2 folders"),
    (lambda p: (p.work / "tcw-5-x").mkdir(parents=True), "is not a Jira item folder"),
    (lambda p: (p.work / "TCW-1-x").mkdir(parents=True), "is missing"),
])
def test_each_error(offline, monkeypatch, capsys, make, words):
    make(offline)
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 1 and words in text, text


@pytest.mark.parametrize("stage", ["request", "qa"])
def test_a_stage_folder_jira_keeps_is_a_warning(offline, monkeypatch, capsys, stage):
    (folder(offline, "TCW-1-x") / stage).mkdir()
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 0 and f"Jira keeps the {stage} record" in text, text


def test_a_malformed_work_jira_is_an_error(offline, monkeypatch, capsys):
    path = config_file(offline.root)
    doc = yaml.safe_load(path.read_text())
    doc["work"]["jira"]["project"] = "tcw"
    write_connected_config_file(path, yaml.safe_dump(doc, sort_keys=False))
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 1 and "work.jira.project" in text, text


def test_a_malformed_connected_jira_block_is_an_error(offline, tmp_path, monkeypatch,
                                                      capsys):
    other = make_project(tmp_path, "web")
    connect(offline.root, other, "children")
    connect(other, offline.root, "parent")
    path = config_file(offline.root)
    doc = yaml.safe_load(path.read_text())
    # The entry's location is in the manifest `connect` wrote (TCW-107).
    doc["projects"]["children"]["web"] = {"jira": {"site": "x"}}
    write_connected_config_file(path, yaml.safe_dump(doc, sort_keys=False))
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 1 and "projects.children.web.jira.site" in text, text


# -- work links (AC 19) ----------------------------------------------------------------


def linking(project, target):
    spec = folder(project, "TCW-2-linker") / "spec"
    spec.mkdir()
    (spec / "spec.md").write_text(f"Depends on [the other](tcw://tcw.work/{target}).\n")


def test_a_link_to_an_existing_folder(offline, monkeypatch, capsys):
    folder(offline, "TCW-1-x")
    linking(offline, "TCW-1-x")
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 0, text


def test_a_link_to_a_missing_folder(offline, monkeypatch, capsys):
    linking(offline, "TCW-9-gone")
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 1 and "tcw://tcw.work/TCW-9-gone" in text, text


def test_link_exists(tmp_path):
    (tmp_path / "TCW-1-x").mkdir()
    (tmp_path / "2026-10-01-y").mkdir()
    assert link_exists(tmp_path, "TCW-1-x")
    assert not link_exists(tmp_path, "TCW-1-y")
    assert not link_exists(tmp_path, "2026-10-01-y")
    assert not link_exists(tmp_path, "TCW-1-x/../TCW-1-x")


def test_a_filesystem_item_naming_a_jira_item_stays_offline(offline, tmp_path, monkeypatch,
                                                           capsys):
    folder(offline, "TCW-1-x")
    p = make_project(tmp_path, "p", config={})
    connect(p, offline.root, "children")
    connect(offline.root, p, "parent")
    write_item(p, "2026-10-01-child", {"title": "c", "stage": "spec", "parent": "tcw.work/TCW-1-x"})
    write_item(p, "2026-10-01-orphan", {"title": "o", "stage": "spec",
                                        "parent": "tcw.work/TCW-7-gone"})
    monkeypatch.chdir(p)
    assert main(["validate"]) == 0
    text = "".join(capsys.readouterr())
    # A reference to a missing item is a warning (TCW-69); one that exists is fine.
    assert "parent references a missing item, tcw.work/TCW-7-gone" in text
    assert "TCW-1-x" not in text


def test_one_item_without_its_item_contacts_nothing(offline, monkeypatch):
    """TCW-73 AC 24: with no `Item`, the stage- and link-dependent checks are
    skipped, and nothing is asked of Jira (`offline` fails on any request).
    The declaration is well formed, so only the records check, which needs
    the stage, could report it."""
    from tcw.findings import Finding
    from tcw.validate import ValidationTarget, validate as validate_one
    from tcw.work import gates

    def never(*args, **kwargs):
        raise AssertionError("the records check ran without the item")
    monkeypatch.setattr(gates, "records_problems", never)
    _, name = offline.item("At spec", "spec")
    (offline.work / name / "capabilities.yaml").write_text("changed: [auth/login]\n")
    (offline.work / name / "review").mkdir()
    (offline.work / name / "review" / "round-1.md").write_text("---\nverdict: x\n---\n")
    found = validate_one(offline.root, target=ValidationTarget("work", name))
    assert all(type(f) is Finding for f in found)
    assert [f.severity for f in found] == ["warning"], found
    assert found[0].where.endswith("review/round-1.md")


def test_one_item_without_its_item_still_reports_a_malformed_declaration(offline):
    """Pre-freeze clean-up, T5: the single-item check parses the file
    offline, as a full `tcw validate` does, with the same words."""
    from tcw.validate import ValidationTarget, validate as validate_one
    _, name = offline.item("At spec", "spec")
    _, other = offline.item("Other", "spec")
    path = offline.work / name / "capabilities.yaml"
    write_connected_config_file(path, "added: [x/y]\n")
    (offline.work / other / "capabilities.yaml").write_text("added: [x/y]\n")
    found = validate_one(offline.root, target=ValidationTarget("work", name))
    assert [(f.severity, f.where, f.message) for f in found] == [
        ("error", str(path), "capabilities.yaml: unknown key(s) added; expected "
                             "new, changed, removed or taxonomy")], found


# -- item-folder declarations and rounds (pre-freeze clean-up, T5 and T7) --------------


def test_a_malformed_declaration_is_one_error_naming_the_file(offline, monkeypatch,
                                                             capsys):
    """T5: read offline, in every key-named folder, with the same words as
    filesystem mode."""
    path = folder(offline, "TCW-1-x") / "capabilities.yaml"
    write_connected_config_file(path, "no-such-key: 1\n")
    code, text = validate(offline, monkeypatch, capsys)
    where = path.relative_to(offline.root).as_posix()
    assert code == 1, text
    assert [line for line in text.splitlines() if line.startswith("error: ")] == [
        f"error: {where}: capabilities.yaml: unknown key(s) no-such-key; expected "
        f"new, changed, removed or taxonomy"], text


def test_a_declaration_that_cannot_be_read_is_an_error(offline, monkeypatch, capsys):
    (folder(offline, "TCW-1-x") / "capabilities.yaml").write_text("changed: [a\n")
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 1 and "capabilities.yaml: cannot be read" in text, text


def test_a_finished_items_malformed_declaration_is_still_an_error(offline, monkeypatch,
                                                                 capsys):
    """Offline, the stage is unknown, and a malformed file is wrong whatever
    it is: the ticket is at Done, and the file is still reported."""
    _, name = offline.item("Done", "done", status="Done")
    (offline.work / name / "capabilities.yaml").write_text("- a list\n")
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 1, text
    assert f"{name}/capabilities.yaml: capabilities.yaml: must be a mapping" in text, text


def test_a_well_formed_declaration_has_no_offline_finding(offline, monkeypatch, capsys):
    """Its records are `--remote`'s to check: this project keeps no ledger, so
    `auth/login` could not be checked there, but offline says nothing."""
    (folder(offline, "TCW-1-x") / "capabilities.yaml").write_text(
        "changed: [auth/login]\n")
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 0 and "capabilities.yaml" not in text, text


def test_a_qa_round_is_only_ignored(offline, monkeypatch, capsys):
    """T7: Jira keeps the qa record, so its folder gets the "ignored" warning
    and its rounds are not read."""
    qa = folder(offline, "TCW-1-x") / "qa"
    qa.mkdir()
    (qa / "round-1.md").write_text("---\nverdict: x\n---\n")
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 0, text
    assert "Jira keeps the qa record, so this folder is ignored" in text, text
    assert "latest qa round is invalid" not in text, text


def test_one_finished_item_given_its_item_still_reports_a_malformed_declaration(offline):
    """Pre-freeze clean-up, final fixes: with the item given and its stage
    terminal, the records check does not run, but the file is still parsed
    offline, as a full `tcw validate` parses it whatever the stage, and
    nothing is asked of Jira."""
    from datetime import date
    from tcw.validate import ValidationTarget, validate as validate_one
    from tcw.work.model import Item, Slug
    _, name = offline.item("Done", "done", status="Done")
    path = offline.work / name / "capabilities.yaml"
    write_connected_config_file(path, "- a list\n")
    item = Item(slug=Slug(offline.id, name), title="Done", stage="completed",
                created=date(2026, 10, 1), priority=None, effort=None,
                complexity=None, tags=(), assignee=None, parent=None, blocked_by=())
    found = validate_one(offline.root, target=ValidationTarget("work", name, item=item))
    assert [(f.severity, f.where, f.message) for f in found] == [
        ("error", str(path), "capabilities.yaml: must be a mapping of new, changed, removed "
                             "and taxonomy")], found
