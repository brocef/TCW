"""References within the project rewritten to full identifiers (TCW-116
Design 4.1, C16; B5 and B10 as one project gives them; criteria 41 and 62;
plan Step 8).

One small project per row of TCW-110 Design 5.1's table, each run with
`tcw migrate`; then F-single, whose references all name its own objects.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.project_files import version_line
from tests.migrate.fixtures import build_f_single
from tests.objectcli import tcw  # noqa: F401  (a fixture)

V = version_line()
T, C, W = "docs/taxonomy", "docs/capabilities", "docs/work"
FILES = "id: app\nwork:\n  backend: filesystem\n"


def make(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    return root


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


BASE = {
    f"{T}/invoice/meta.yaml": "name: Invoice\nkind: Vocabulary\n",
    f"{T}/invoice/description.md": "An invoice.\n",
    f"{C}/roles/admin/meta.yaml": "id: cap-6f7081\nname: Admin\nStatus: Supported\n",
    f"{C}/roles/admin/description.md": "Admin.\n",
    f"{C}/conditions/online/meta.yaml": "id: cap-708192\nname: Online\nStatus: Supported\n",
    f"{C}/conditions/online/description.md": "Online.\n",
    f"{C}/cli/old/meta.yaml": "id: cap-1a2b3c\nname: Old\nStatus: Supported\n",
    f"{C}/cli/old/description.md": "Old.\n",
    f"{W}/2026-10-01-a/item.yaml": "title: A\nstage: inbox\n",
}


@pytest.mark.parametrize("rel, text, expected", [
    # A work item's parent and blocked-by (files backend).
    (f"{W}/2026-10-02-b/item.yaml",
     "title: B\nstage: inbox\nparent: app/2026-10-01-a\nblocked-by:\n- app/2026-10-01-a\n",
     "title: B\nstage: inbox\nparent: app.work/2026-10-01-a\nblocked-by:\n"
     "- app.work/2026-10-01-a\n"),
    # A term's relatesTo and vocabulary.
    (f"{T}/line/meta.yaml",
     "name: Line\nkind: Vocabulary\nrelatesTo: [invoice]\nvocabulary:\n- invoice\n",
     "name: Line\nkind: Vocabulary\nrelatesTo: [app.taxonomy/invoice]\nvocabulary:\n"
     "- app.taxonomy/invoice\n"),
    # A capability's six fields, `!` and the roles/ and conditions/ paths kept.
    (f"{C}/cli/x/meta.yaml",
     "name: X\nStatus: Supported\nSubject: invoice, invoice\nFeature: invoice\n"
     "Superseded by: cli/old\nBlocked by: 'cli/old'\nRoles:\n- '!roles/admin'\n"
     "When: [conditions/online, '!conditions/online']\n",
     "name: X\nStatus: Supported\nSubject: app.taxonomy/invoice, app.taxonomy/invoice\n"
     "Feature: app.taxonomy/invoice\nSuperseded by: app.capabilities/cli/old\n"
     "Blocked by: 'app.capabilities/cli/old'\nRoles:\n- '!app.capabilities/roles/admin'\n"
     "When: [app.capabilities/conditions/online, '!app.capabilities/conditions/online']\n"),
])
def test_each_field_of_a_state_file(tcw, tmp_path, rel, text, expected):
    app = make(tmp_path / "app", {"tcw-config.yaml": FILES, **BASE, rel: text})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    new = rel.replace("meta.yaml", "tcw-taxonomy.yaml" if rel.startswith(T)
                      else "tcw-capability.yaml").replace("item.yaml", "tcw-work-item.yaml")
    assert read(app, new) == V + expected
    assert "C16" in next(line for line in done.err.splitlines()
                         if line.startswith(f"write {new}"))


def test_each_entry_of_an_items_capabilities_file(tcw, tmp_path):
    rel = f"{W}/2026-10-01-a/capabilities.yaml"
    text = ("new:\n- cli/not-yet\nchanged: [cli/old]\nremoved:\n- cli/old\n"
            "taxonomy:\n  new:\n  - invoice\n  changed: []\n")
    app = make(tmp_path / "app", {"tcw-config.yaml": FILES, **BASE, rel: text})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert read(app, rel) == (
        "new:\n- app.capabilities/cli/not-yet\nchanged: [app.capabilities/cli/old]\n"
        "removed:\n- app.capabilities/cli/old\ntaxonomy:\n  new:\n"
        "  - app.taxonomy/invoice\n  changed: []\n")
    assert f"write {rel}: C16" in done.err.splitlines()


def test_a_link_outside_code_is_rewritten_and_one_inside_is_not(tcw, tmp_path):
    rel = f"{C}/cli/old/description.md"
    text = ("See [x](tcw://C/cli/old), [t](tcw://T/invoice), [w](tcw://W/2026-10-01-a)\n"
            "and [w2](tcw://W/app/2026-10-01-a) and [done](tcw://app.capabilities/cli/old).\n"
            "In code: `[x](tcw://C/cli/old)`.\n\n```\n[x](tcw://C/cli/old)\n```\n")
    app = make(tmp_path / "app", {"tcw-config.yaml": FILES, **BASE, rel: text})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert read(app, rel) == (
        "See [x](tcw://app.capabilities/cli/old), [t](tcw://app.taxonomy/invoice), "
        "[w](tcw://app.work/2026-10-01-a)\n"
        "and [w2](tcw://app.work/2026-10-01-a) and [done](tcw://app.capabilities/cli/old).\n"
        "In code: `[x](tcw://C/cli/old)`.\n\n```\n[x](tcw://C/cli/old)\n```\n")
    assert f"write {rel}: C16" in done.err.splitlines()


def test_f_single_names_its_own_objects(tcw, tmp_path):
    root = build_f_single(tmp_path / "app")
    done = tcw(["migrate", "--no-jira"], root)
    assert done.code == 0, done.err
    x = yaml.safe_load(read(root, f"{C}/cli/x/tcw-capability.yaml"))
    assert x["Subject"] == ["app.taxonomy/invoice"]
    assert x["Roles"] == ["!app.capabilities/roles/admin"]
    assert x["When"] == ["app.capabilities/conditions/online"]
    assert yaml.safe_load(read(root, f"{T}/invoice/line/tcw-taxonomy.yaml"))["relatesTo"] \
        == ["app.taxonomy/invoice"]
    assert yaml.safe_load(read(root, f"{W}/APP-1-a/capabilities.yaml")) == {
        "new": ["app.capabilities/cli/new-thing"], "changed": ["app.capabilities/cli/x"],
        "taxonomy": {"new": ["app.taxonomy/invoice"]}}
    spec = read(root, f"{W}/APP-2-b/spec/spec.md")
    assert "[the capability](tcw://app.capabilities/cli/x)" in spec
    assert "`[the capability](tcw://C/cli/x)`" in spec
    assert f"write {W}/APP-2-b/spec/spec.md: C13, C16" in done.err.splitlines()


def test_files_backend_f_single_converts_its_parent_and_blocked_by(tcw, tmp_path):
    root = build_f_single(tmp_path / "app", backend="files")
    done = tcw(["migrate"], root)
    assert done.code == 0, done.err
    item = yaml.safe_load(read(root, f"{W}/2026-10-02-b/tcw-work-item.yaml"))
    assert item["parent"] == "app.work/2026-10-01-a"
    assert item["blocked-by"] == ["app.work/2026-10-01-a"]


# ── criterion 62: a branch brings 3.x files back ─────────────────────────────

def test_only_the_3x_files_a_branch_brought_back_convert(tcw, tmp_path):
    app = make(tmp_path / "app", {
        ".tcw/tcw-config.yaml": V + FILES,
        f"{T}/invoice/tcw-taxonomy.yaml": V + "name: Invoice\n",
        f"{T}/invoice/description.md": "An invoice.\n",
        f"{W}/2026-10-01-a/tcw-work-item.yaml": V + "title: A\nstage: inbox\n",
        f"{C}/cli/back/meta.yaml": "id: cap-1a2b3c\nname: Back\nStatus: Supported\n"
                                   "Subject: [invoice]\n",
        f"{C}/cli/back/description.md": "Back.\n",
        f"{W}/2026-10-02-b/item.yaml": "title: B\nstage: inbox\nblocked-by:\n"
                                       "- app/2026-10-01-a\n"})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    changed = sorted(line for line in done.err.splitlines() if line.startswith("write"))
    assert changed == [
        "write .tcw/.gitignore: C1", "write .tcw/.gitignore: C1",
        "write .tcw/tcw-migration.yaml: C10",
        f"write {C}/cli/back/tcw-capability.yaml: C9, C10, C16",
        f"write {W}/2026-10-02-b/tcw-work-item.yaml: C9, C16"]
    assert yaml.safe_load(read(app, f"{C}/cli/back/tcw-capability.yaml"))["Subject"] == \
        ["app.taxonomy/invoice"]
    assert yaml.safe_load(read(app, f"{W}/2026-10-02-b/tcw-work-item.yaml"))[
        "blocked-by"] == ["app.work/2026-10-01-a"]


# ── what one project cannot convert yet, or at all ───────────────────────────

def test_a_cross_project_blocked_by_is_b5_for_now(tcw, tmp_path):
    app = make(tmp_path / "app", {
        "tcw-config.yaml": FILES,
        f"{W}/2026-10-02-b/item.yaml": "title: B\nstage: inbox\nblocked-by:\n"
                                       "- other/2026-10-01-x\n"})
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert "B5 docs/work/2026-10-02-b/item.yaml: blocked-by: tcw migrate does not convert " \
           "a reference to another project's work item yet" in done.err


def test_a_capabilities_entry_with_no_ledger_is_b10(tcw, tmp_path):
    app = make(tmp_path / "app", {
        "tcw-config.yaml": FILES,
        f"{W}/2026-10-01-a/item.yaml": "title: A\nstage: inbox\n",
        f"{W}/2026-10-01-a/capabilities.yaml": "new:\n- cli/x\n"})
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert ("B10 docs/work/2026-10-01-a/capabilities.yaml: cli/x: this project ('app') "
            "keeps no capabilities ledger; qualify the path with a child project id "
            "(it declares no child projects)") in done.err
