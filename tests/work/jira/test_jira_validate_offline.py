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
    path = offline.root / "tcw-config.yaml"
    doc = yaml.safe_load(path.read_text())
    doc["work"]["jira"]["project"] = "tcw"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 1 and "work.jira.project" in text, text


def test_a_malformed_connected_jira_block_is_an_error(offline, tmp_path, monkeypatch,
                                                      capsys):
    other = make_project(tmp_path, "web")
    connect(offline.root, other, "children")
    connect(other, offline.root, "parent")
    path = offline.root / "tcw-config.yaml"
    doc = yaml.safe_load(path.read_text())
    doc["projects"]["children"]["web"] = {
        "path": doc["projects"]["children"]["web"], "jira": {"site": "x"}}
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 1 and "projects.children.web.jira.site" in text, text


# -- work links (AC 19) ----------------------------------------------------------------


def linking(project, target):
    spec = folder(project, "TCW-2-linker") / "spec"
    spec.mkdir()
    (spec / "spec.md").write_text(f"Depends on [the other](tcw://W/{target}).\n")


def test_a_link_to_an_existing_folder(offline, monkeypatch, capsys):
    folder(offline, "TCW-1-x")
    linking(offline, "TCW-1-x")
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 0, text


def test_a_link_to_a_missing_folder(offline, monkeypatch, capsys):
    linking(offline, "TCW-9-gone")
    code, text = validate(offline, monkeypatch, capsys)
    assert code == 1 and "tcw://W/TCW-9-gone" in text, text


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
    write_item(p, "2026-10-01-child", {"title": "c", "stage": "spec", "parent": "tcw/TCW-1-x"})
    write_item(p, "2026-10-01-orphan", {"title": "o", "stage": "spec",
                                        "parent": "tcw/TCW-7-gone"})
    monkeypatch.chdir(p)
    assert main(["validate"]) == 0
    text = "".join(capsys.readouterr())
    # A reference to a missing item is a warning (TCW-69); one that exists is fine.
    assert "parent references a missing item, tcw/TCW-7-gone" in text
    assert "TCW-1-x" not in text


def test_one_item_without_its_item_contacts_nothing(offline):
    """TCW-73 AC 24: with no `Item`, the stage- and link-dependent checks are
    skipped, and nothing is asked of Jira (`offline` fails on any request)."""
    from tcw.findings import Finding
    from tcw.validate import ValidationTarget, validate as validate_one
    _, name = offline.item("At spec", "spec")
    (offline.work / name / "capabilities.yaml").write_text("added: [x/y]\n")
    (offline.work / name / "review").mkdir()
    (offline.work / name / "review" / "round-1.md").write_text("---\nverdict: x\n---\n")
    found = validate_one(offline.root, target=ValidationTarget("work", name))
    assert all(type(f) is Finding for f in found)
    assert [f.severity for f in found] == ["warning"], found
    assert found[0].where.endswith("review/round-1.md")
