"""The configuration converted (TCW-116 Design 3: C1, C2, C7; Design 2.7's
both-files rule; Design 2.9's B1, B2, B5, B11, B14, B15, A4, A5, A9, A13,
D5; plan Step 5).

Every case is a small 3.x project run with `tcw migrate` in-process.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.project_files import version_line
from tests.objectcli import tcw  # noqa: F401  (a fixture)

DATA = Path(__file__).parent / "data"

SHARED = "id: app\n# the stores\ntaxonomy:\n  path: docs/terms\n"
LOCAL = "user:\n  name: Ada\n"


def make(root: Path, files: dict[str, str], *, git: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    if git:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    return root


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}


def lines(err: str) -> list[str]:
    return err.splitlines()


# ── C1: into .tcw/, the version first, the ignore lines ──────────────────────

def test_both_files_move_into_tcw_with_the_version_first(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED, "tcw-config.local.yaml": LOCAL})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert done.out == ""
    files = tree(app)
    assert files[".tcw/tcw-config.yaml"] == (version_line() + SHARED).encode()
    assert files[".tcw/tcw-config.local.yaml"] == (version_line() + LOCAL).encode()
    assert files[".tcw/.gitignore"].decode().splitlines() == [
        "/tcw-migration-progress.yaml", "/tcw-config.local.yaml", "/tcw-manifest.local.yaml"]
    assert "tcw-config.yaml" not in files and "tcw-config.local.yaml" not in files
    assert ".tcw/tcw-migration-progress.yaml" not in files
    assert "write .tcw/tcw-config.yaml: C1" in lines(done.err)
    assert "delete tcw-config.yaml: C1" in lines(done.err)
    assert "run 'tcw migrate'" not in tcw(["work", "list"], app).err


def test_outside_a_git_repository_there_is_no_ignore_file(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED, "tcw-config.local.yaml": LOCAL},
               git=False)
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    files = tree(app)
    assert ".tcw/.gitignore" not in files
    assert files[".tcw/tcw-config.yaml"] == (version_line() + SHARED).encode()


def test_an_ignore_line_already_there_is_not_written_again(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED,
                                  ".tcw/.gitignore": "# mine\ntcw-config.local.yaml\n"})
    assert tcw(["migrate"], app).code == 0
    assert (app / ".tcw/.gitignore").read_text().splitlines() == [
        "# mine", "tcw-config.local.yaml", "/tcw-migration-progress.yaml",
        "/tcw-manifest.local.yaml"]


def test_the_dry_run_writes_nothing_and_says_would(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED, "tcw-config.local.yaml": LOCAL})
    before = tree(app)
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 0, done.err
    assert tree(app) == before
    assert "would write .tcw/tcw-config.yaml: C1" in lines(done.err)
    assert "would delete tcw-config.local.yaml: C1" in lines(done.err)


def test_a_second_run_has_nothing_to_migrate(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED, "tcw-config.local.yaml": LOCAL})
    assert tcw(["migrate"], app).code == 0
    before = tree(app)
    again = tcw(["migrate"], app)
    assert (again.code, again.err) == (0, "nothing to migrate\n")
    assert tree(app) == before


# ── criterion 15: this repository's own configuration ────────────────────────

def test_this_repositorys_configuration_converts_byte_for_byte(tcw, tmp_path):
    frozen = (DATA / "repo-tcw-config-3x.yaml").read_bytes()
    app = make(tmp_path / "app", {})
    (app / "tcw-config.yaml").write_bytes(frozen)
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    converted = (app / ".tcw/tcw-config.yaml").read_bytes()
    assert converted == version_line().encode() + frozen.replace(b"not_tags:", b"not-tags:")
    assert frozen.count(b"not_tags:") == 1
    assert not [line for line in lines(done.err) if line.lstrip().startswith("A13")]


# ── criterion 13: a root file beside its .tcw/ copy ──────────────────────────

def test_an_equal_pair_keeps_the_tcw_file_and_deletes_the_root_one(tcw, tmp_path):
    shared4 = version_line() + "# my own comment\nid: app\ntaxonomy: {path: docs/terms}\n"
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED, ".tcw/tcw-config.yaml": shared4})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    files = tree(app)
    assert files[".tcw/tcw-config.yaml"] == shared4.encode()
    assert "tcw-config.yaml" not in files
    assert "write .tcw/tcw-config.yaml: C1" not in lines(done.err)


def test_an_equal_pair_after_the_rename_is_equal(tcw, tmp_path):
    three = "id: app\nwork:\n  stages:\n    spec:\n      prompt:\n      - blob: x\n" \
            "        when:\n          not_tags: [bug]\n"
    four = version_line() + three.replace("not_tags", "not-tags")
    app = make(tmp_path / "app", {"tcw-config.yaml": three, ".tcw/tcw-config.yaml": four})
    assert tcw(["migrate"], app).code == 0
    assert not (app / "tcw-config.yaml").exists()


def test_a_differing_pair_is_b11_naming_both_and_the_first_key(tcw, tmp_path):
    shared4 = version_line() + "id: app\ntaxonomy:\n  path: docs/other\n"
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED, ".tcw/tcw-config.yaml": shared4})
    before = tree(app)
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert tree(app) == before
    assert ("  B11 tcw-config.yaml: differs from .tcw/tcw-config.yaml at taxonomy.path"
            in lines(done.err)[lines(done.err).index("refused:") + 1])


def test_a_differing_personal_pair_is_b11(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED, "tcw-config.local.yaml": LOCAL,
                                  ".tcw/tcw-config.local.yaml":
                                  version_line() + "user:\n  name: Bo\n"})
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 3
    assert "B11 tcw-config.local.yaml: differs from .tcw/tcw-config.local.yaml at " \
           "user.name" in done.err


# ── criterion 19: empty files ─────────────────────────────────────────────────

def test_an_empty_personal_file_gains_only_its_version_line(tcw, tmp_path):
    app = make(tmp_path / "app", {".tcw/tcw-config.yaml": version_line() + "id: app\n",
                                  ".tcw/tcw-config.local.yaml": ""})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert (app / ".tcw/tcw-config.local.yaml").read_text() == version_line()


def test_an_empty_shared_file_beside_a_root_file_gets_its_conversion(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED, ".tcw/tcw-config.yaml": "\n"})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert (app / ".tcw/tcw-config.yaml").read_text() == version_line() + SHARED
    assert not (app / "tcw-config.yaml").exists()


def test_an_empty_shared_file_with_no_root_file_is_b15(tcw, tmp_path):
    app = make(tmp_path / "app", {".tcw/tcw-config.yaml": ""})
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert "B15 .tcw/tcw-config.yaml:" in done.err
    refused = tcw(["work", "list"], app)
    assert refused.code == 1
    assert "has no tcw-version" in refused.err


def test_a_root_file_without_an_id_is_b15(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml": "taxonomy:\n  path: docs/terms\n"})
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 3
    assert "B15 tcw-config.yaml: has no id" in done.err


# ── C2 and B1, B2, B14 ───────────────────────────────────────────────────────

def test_not_tags_is_renamed_in_both_files_and_another_bad_key_is_b1(tcw, tmp_path):
    shared = "id: app\nwork:\n  stages:\n    spec:\n      prompt:\n      - blob: x\n" \
             "        when:\n          not_tags: [bug]\n"
    local = "work:\n  stages:\n    spec:\n      prompt:\n      - blob: y\n" \
            "        when:\n          not_tags: [docs]\n"
    app = make(tmp_path / "app", {"tcw-config.yaml": shared, "tcw-config.local.yaml": local})
    assert tcw(["migrate"], app).code == 0
    assert (app / ".tcw/tcw-config.yaml").read_text() == \
        version_line() + shared.replace("not_tags", "not-tags")
    assert (app / ".tcw/tcw-config.local.yaml").read_text() == \
        version_line() + local.replace("not_tags", "not-tags")
    bad = make(tmp_path / "bad", {"tcw-config.yaml": "id: bad\nwork:\n  work_tags: [x]\n"})
    done = tcw(["migrate"], bad)
    assert done.code == 3
    assert "B1 tcw-config.yaml: work.work_tags: key 'work_tags' must be lowercase" in done.err
    assert not (bad / ".tcw").exists()


def test_connected_projects_is_b2_naming_the_3_0_guide(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml":
                                  "id: app\nconnected-projects:\n  lib: ../lib\n"})
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert "B2 tcw-config.yaml: connected-projects:" in done.err
    assert "docs/migration-guide-2.8-to-3.0.0.md" in done.err


def test_an_unreadable_file_is_b14(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml": "id: app\nid: again\n"})
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert "B14 tcw-config.yaml:" in done.err
    assert "again" in done.err or "duplicate" in done.err.lower()


# ── reports: A4, A5, A9, A13, D5 ─────────────────────────────────────────────

def test_a9_and_d5(tcw, tmp_path):
    from tests.migrate.fixtures import _CONFIG
    shared = _CONFIG.replace("APP_JIRA_TOKEN", "APP_TOKEN")
    app = make(tmp_path / "app", {"tcw-config.yaml": shared})
    done = tcw(["migrate", "--dry-run", "--no-jira"], app)
    assert done.code == 0, done.err
    assert "  A9 tcw-config.yaml: work.jira.credentials.email-env: TCW_JIRA__EMAIL starts " \
           "with TCW_ and holds __, which TCW 4 reads as an override of a configuration " \
           "value; name another variable" in lines(done.err)
    assert any(line.startswith("  D5 tcw-config.yaml: work.tags: null") for line in
               lines(done.err)), done.err
    assert not any("APP_TOKEN" in line for line in lines(done.err) if "A9" in line)


def test_a5_names_the_user_files_line_and_leaves_it(tcw, tmp_path, monkeypatch):
    home = tmp_path / "xdg"
    user = home / "tcw" / "config.yaml"
    user.parent.mkdir(parents=True)
    text = "work:\n  stages:\n    spec:\n      prompt:\n      - blob: z\n" \
           "        when:\n          not_tags: [docs]\n"
    user.write_text(text)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home))
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert f"  A5 {user}:7: work.stages.spec.prompt[0].when.not_tags: TCW 4 refuses " \
           f"not_tags; write not-tags (this file is shared with any TCW 3.x on this " \
           f"machine, which needs not_tags, so tcw migrate leaves it)" in lines(done.err)
    assert user.read_text() == text


def test_a4_names_the_root_ignore_line_and_leaves_it(tcw, tmp_path):
    ignore = "node_modules/\n/tcw-config.local.yaml\n"
    app = make(tmp_path / "app", {"tcw-config.yaml": SHARED, ".gitignore": ignore})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert "  A4 .gitignore:2: /tcw-config.local.yaml now ignores nothing: the personal " \
           "file is .tcw/tcw-config.local.yaml, which .tcw/.gitignore ignores" \
           in lines(done.err)
    assert (app / ".gitignore").read_text() == ignore


def test_a13_names_each_binding_and_leaves_its_bytes(tcw, tmp_path):
    shared = ("id: app\nwork:\n  procedures:\n    create-work:\n"
              "    - generate: tcw work new Next --blocks app/x\n"
              "  stages:\n    spec:\n      post:\n      - command: tcw provision\n"
              "      pre:\n      - command: tcw provisional-check --projects-ok\n")
    app = make(tmp_path / "app", {"tcw-config.yaml": shared})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    a13 = [line for line in lines(done.err) if line.startswith("  A13")]
    assert a13 == [
        "  A13 tcw-config.yaml:5: work.procedures.create-work[0].generate: 'tcw work new "
        "Next --blocks app/x' uses --blocks, which TCW 4 removes; it is left as written",
        "  A13 tcw-config.yaml:9: work.stages.spec.post[0].command: 'tcw provision' uses "
        "tcw provision, which TCW 4 removes; it is left as written"]
    assert (app / ".tcw/tcw-config.yaml").read_text() == version_line() + shared


# ── part 2's forms, refused for now (Decided 17) ─────────────────────────────

@pytest.mark.parametrize("text, form", [
    ("id: app\nwork:\n  path: ../elsewhere/work\n", "a work store outside the project"),
    ("id: app\ntaxonomy:\n  repository:\n    url: https://example.invalid/t.git\n",
     "a taxonomy store with only a repository"),
])
def test_each_part_two_form_is_b5_and_nothing_is_written(tcw, tmp_path, text, form):
    app = make(tmp_path / "app", {"tcw-config.yaml": text})
    before = tree(app)
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert f"tcw migrate does not convert {form} yet" in done.err
    assert any(line.startswith("  B5 tcw-config.yaml:") for line in lines(done.err))
    assert tree(app) == before


def test_every_blocker_is_listed_with_the_changes_it_stopped(tcw, tmp_path):
    app = make(tmp_path / "app", {"tcw-config.yaml": "id: app\nwork:\n  work_tags: [x]\n"
                                  "  path: ../elsewhere/work\n",
                                  "tcw-config.local.yaml": LOCAL})
    done = tcw(["migrate"], app)
    assert done.code == 3
    said = lines(done.err)
    assert "would write .tcw/tcw-config.local.yaml: C1" in said
    assert said.index("refused:") > said.index("would write .tcw/tcw-config.local.yaml: C1")
    assert sum(1 for line in said if line.startswith("  B")) == 2
    assert yaml.safe_load((app / "tcw-config.yaml").read_text())["id"] == "app"


# ── C3, C6: projects: becomes parents: and children: (plan Step 17) ──────────
#
# `config.plan_relations` is called directly: the command still refuses
# `projects:` until Step 18 writes the manifest entries that locate each
# converted parent and child.

def relations_of(text: str):
    from tcw.migrate import config
    from tcw.migrate.editors import convert_text
    from tcw.store.config_edit import intended
    mapping = yaml.safe_load(text)
    planned = config.plan_relations("tcw-config.yaml", mapping)
    edits = planned.edits()
    new = convert_text(".tcw/tcw-config.yaml", text, edits,
                       expect={"tcw-version": __import__("tcw").__version__,
                               **intended(mapping, edits)}) if edits else None
    return planned, new


def parsed_links(text: str):
    from tcw.store.links import parse_children, parse_parents
    data = yaml.safe_load(text)
    parents, problems = parse_parents(data.get("parents"), ".tcw/tcw-config.yaml")
    children, child_problems = parse_children(data.get("children"), ".tcw/tcw-config.yaml",
                                              own_id=data["id"])
    assert problems == [] and child_problems == []
    return data, parents, children


def test_a_parent_becomes_a_plain_parent_id(tmp_path):
    planned, new = relations_of("id: app\nprojects:\n  parent:\n    ws: ..\n")
    data, parents, children = parsed_links(new.text)
    assert "projects" not in data
    assert data["parents"] == ["ws"]
    assert [(p.id, sorted(p.inherit)) for p in parents] == [
        ("ws", ["capabilities", "config", "taxonomy"])]
    assert children == [] and "children" not in data
    assert new.text == version_line() + "id: app\nparents:\n- ws\n"


def test_children_become_children_in_order():
    planned, new = relations_of(
        "id: ws\nprojects:\n  children:\n    b: b\n    a:\n      path: a\nwork:\n"
        "  tags: []\n")
    data, parents, children = parsed_links(new.text)
    assert children == ["b", "a"] and "parents" not in data
    assert data["work"] == {"tags": []}


@pytest.mark.parametrize("extends, inherit", [
    ("taxonomy:\n  extends:\n  - core\n", ["taxonomy"]),
    ("taxonomy:\n  extends:\n  - core\ncapabilities:\n  extends:\n  - core\n",
     ["taxonomy", "capabilities"]),
    ("", "none")])
def test_an_upstream_passes_the_axes_its_extends_names(extends, inherit):
    planned, _ = relations_of(
        f"id: app\nprojects:\n  upstream:\n    core: ../core\n{extends}")
    assert [link.value() for link in planned.parents] == [{"id": "core", "inherit": inherit}]


def test_the_upstream_entry_is_read_by_tcw_4(tmp_path):
    """The `extends` keys are Step 19's to remove; here only the links."""
    planned, new = relations_of(
        "id: app\nprojects:\n  parent:\n    ws: ..\n  upstream:\n    core: ../core\n"
        "    lib:\n      repository:\n        url: https://example.invalid/lib.git\n"
        "taxonomy:\n  extends:\n  - core\n")
    data, parents, _ = parsed_links(new.text)
    assert data["parents"] == ["ws", {"id": "core", "inherit": ["taxonomy"]},
                               {"id": "lib", "inherit": "none"}]
    assert [(p.id, sorted(p.inherit)) for p in parents] == [
        ("ws", ["capabilities", "config", "taxonomy"]), ("core", ["taxonomy"]),
        ("lib", [])]
    assert [r.id for r in planned.entries] == ["ws", "core", "lib"]


def test_several_parents_convert_in_the_order_written():
    """3.x refused more than one parent; a file that has several anyway
    keeps them in its order."""
    planned, new = relations_of(
        "id: app\nprojects:\n  parent:\n    b: ../b\n    a: ../a\n")
    assert yaml.safe_load(new.text)["parents"] == ["b", "a"]


def test_a_jira_block_is_dropped_recorded_and_reported():
    """Criterion 27."""
    planned, new = relations_of(
        "id: ws\nprojects:\n  children:\n    app:\n      path: app\n      jira:\n"
        "        project: APP\n        credentials:\n          email-env: TCW_X__EMAIL\n")
    assert yaml.safe_load(new.text) == {"tcw-version": __import__("tcw").__version__,
                                        "id": "ws", "children": ["app"]}
    assert planned.removed == [{"file": "tcw-config.yaml",
                                "key": "projects.children.app.jira",
                                "value": {"project": "APP",
                                          "credentials": {"email-env": "TCW_X__EMAIL"}}}]
    assert [(r.code, r.where) for r in planned.reports] == [("D6", "tcw-config.yaml"),
                                                            ("A9", "tcw-config.yaml")]
    assert planned.reports[0].text.startswith("projects.children.app.jira: dropped;")
    assert "TCW_X__EMAIL starts with TCW_ and holds __" in planned.reports[1].text


def test_a_comment_inside_the_block_is_returned_as_dropped():
    _, new = relations_of("id: ws\n# kept\nprojects:\n  # the children\n  children:\n"
                          "    app: app\n")
    assert new.dropped == ["# the children"]
    assert "# kept\n" in new.text


def test_an_anchor_the_block_defines_and_the_file_uses_is_refused():
    """B12: removing the block would lose the value the alias reads."""
    from tcw.store.config_edit import ConfigEditRefused
    with pytest.raises(ConfigEditRefused, match="anchor"):
        relations_of("id: ws\nprojects:\n  children:\n    app: &where app\n"
                     "work:\n  path: *where\n")


def test_a_projects_block_3x_refused_is_b14():
    planned, new = relations_of("id: ws\nprojects:\n  children:\n    Bad: x\n")
    assert [b.code for b in planned.blockers] == ["B14"]
    assert "children key" in planned.blockers[0].why


def test_no_projects_key_plans_nothing():
    planned, new = relations_of("id: ws\n")
    assert (planned.present, planned.edits(), new) == (False, [], None)
