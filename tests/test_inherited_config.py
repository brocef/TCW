"""Configuration a project takes from its parents (TCW-109 Design 1-3, 6, 7),
through `load_config` and the command line.

Each test is named after the criterion it proves. The layouts are the spec's:
`core` is a parent, `app` its child, both side by side in one folder, where
TCW-107's search finds them."""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw.config import Withheld, load_config
from tcw.errors import BackendError, InheritedUnavailable
from tests.projectfiles import config_file, local_config_file, write_config, \
    write_config_file, write_local_config, write_manifest
from tests.test_project_files_cli import personal_env, tcw
from tests.work.projects import commit_all, make_project

INHERIT = {"inherit": True}


@dataclass
class Ran:
    code: int
    out: str
    err: str


@pytest.fixture
def run(monkeypatch, capsys):
    """`tcw` in this process, from `cwd`: what a test that replaces a
    function inside the command needs."""
    from tcw.cli import main

    def go(cwd: Path, *argv: str, stdin: str = "") -> Ran:
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(list(argv))
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Ran(code, captured.out, captured.err)
    return go


def set_work(root: Path, work: dict | None = None, **keys) -> Path:
    """Replace `work:` (and any other top-level key given) in a project
    `make_project` built."""
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    if work is not None:
        document["work"] = work
    document.update(keys)
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    return root


def project(root: Path, project_id: str, *, parents=None, children=None,
            work=None, extra: dict | None = None) -> Path:
    """A 4.0 project at `root`. Every key a test's outcome depends on is given
    by the test: nothing is defaulted but the ID."""
    data: dict = {"id": project_id}
    if parents is not None:
        data["parents"] = parents
    if children is not None:
        data["children"] = children
    if work is not None:
        data["work"] = work
    data.update(extra or {})
    write_config(root, yaml.safe_dump(data, sort_keys=False))
    return root.resolve()


def problems(config) -> list[str]:
    return [str(p) for p in config.problems]


# -- one project: `inherit: true` in `work.tags`, and `null` (Design 2.4, 2.5) -----------


def test_ac7_inherit_in_a_project_with_no_parents(tmp_path):
    app = project(tmp_path / "app", "app", work={"tags": [INHERIT, "c"]})
    config = load_config(app)
    assert problems(config) == []
    assert config.work.tags == ("c",)
    ran = tcw(app, "validate")
    assert ran.code == 0, ran


def test_ac7_inherit_elsewhere_is_refused_naming_work_tags(tmp_path):
    app = project(tmp_path / "app", "app", work={"documentation": [INHERIT]})
    found = [p for p in problems(load_config(app)) if "'inherit' is allowed only" in p]
    assert len(found) == 1 and "work.tags" in found[0]


def test_ac7_two_inherit_entries_in_work_tags(tmp_path):
    app = project(tmp_path / "app", "app", work={"tags": [INHERIT, "c", INHERIT]})
    assert any("a list may hold one 'inherit' entry" in p
               for p in problems(load_config(app)))


def test_ac8_null_in_a_personal_file_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    app = project(tmp_path / "app", "app")
    write_local_config(app, "work:\n  tags: null\n")
    assert any("null has no meaning in a personal file" in p
               for p in problems(load_config(app)))


def test_ac8_a_null_backend_is_still_refused(tmp_path):
    app = project(tmp_path / "app", "app", work={"backend": None})
    assert any("must be one of" in p for p in problems(load_config(app)))


@pytest.mark.parametrize("key", ["tags", "jira"])
def test_ac8_null_at_an_inherited_key_in_one_project_is_no_value(tmp_path, key):
    app = project(tmp_path / "app", "app", work={key: None})
    config = load_config(app)
    assert problems(config) == []
    assert config.work.tags == ()
    assert key not in config.values["work"]


# -- what reads an inherited key reads it only when it uses it (Design 3.4) ------------


def test_withheld_raises_only_when_used():
    held = Withheld(lambda: BackendError("held back"))
    for use in (list, len, bool, lambda h: "a" in h, lambda h: h.site):
        with pytest.raises(BackendError, match="held back"):
            use(held)
    assert repr(held) == "Withheld(...)"
    assert (lambda value: value)(held) is held
    import copy
    assert copy.deepcopy(held) is held


def test_a_tag_is_read_only_when_one_is_applied():
    from tcw.work.model import Changes, validate_changes
    held = Withheld(lambda: BackendError("held back"))
    common = dict(item_slug=None, registered_tags=held, current_project="app",
                  parent_of=lambda slug: None)
    validate_changes(Changes(), **common)
    with pytest.raises(BackendError, match="held back"):
        validate_changes(Changes(add_tags=("t",)), **common)


@pytest.fixture
def no_store(monkeypatch):
    """Opening a work store fails loudly."""
    import tcw.work.cli
    import tcw.work.open

    def refuse(*args, **kwargs):
        raise AssertionError("the work store was opened")
    monkeypatch.setattr(tcw.work.open, "open_backend", refuse)
    monkeypatch.setattr(tcw.work.cli, "open_backend", refuse)


def _two_projects(tmp_path, run):
    """`app` and `lib`, with an item in `lib`, and what each command that
    needs nothing inherited answers in `app` while the store can be opened."""
    app = make_project(tmp_path, "app", config={})
    lib = make_project(tmp_path, "lib", config={})
    commit_all(app)
    made = run(lib, "work", "new", "lib thing")
    assert made.code == 0, made
    item = made.out.strip()
    before = {argv: run(app, *argv) for argv in [
        ("work", "lifecycle"), ("work", "docs"), ("work", "stage", "prompt", "spec"),
        ("work", "procedure", "search"), ("work", "path"), ("work", "show", item)]}
    assert all(r.code == 0 for r in before.values()), before
    assert "owner: lib" in before[("work", "show", item)].out
    return app, before


def test_commands_that_need_nothing_inherited_do_not_open_the_store(
        tmp_path, run, monkeypatch):
    """Design 3.4: the active project's store is never opened by these, so
    they answer as they did with it refused."""
    app, before = _two_projects(tmp_path, run)
    import tcw.work.cli
    import tcw.work.open
    real = tcw.work.open.open_backend

    def refuse_app(root, **kwargs):
        if Path(root).resolve() == app.resolve():
            raise AssertionError("the active project's work store was opened")
        return real(root, **kwargs)
    monkeypatch.setattr(tcw.work.cli, "open_backend", refuse_app)
    monkeypatch.setattr(tcw.work.open, "open_backend", refuse_app)
    for argv, was in before.items():
        now = run(app, *argv)
        assert (now.code, now.out, now.err) == (was.code, was.out, was.err), argv


def test_the_checks_the_store_made_are_kept(tmp_path, run):
    """In a project whose graph is invalid, each command that no longer opens
    the store fails with the message it gave when it did."""
    app = make_project(tmp_path, "app", config={})
    make_project(tmp_path, "kid", config={})
    set_work(app, children=["kid"])
    listed = run(app, "work", "list")
    assert listed.code == 1, listed
    graph = listed.err.split(": ", 1)[1]
    for argv in [("work", "lifecycle"), ("work", "docs"),
                 ("work", "stage", "prompt", "spec"), ("work", "path")]:
        ran = run(app, *argv)
        assert ran.code == 1, (argv, ran)
        assert graph in ran.err, (argv, ran.err)


def test_no_work_path_is_still_the_same_failure(tmp_path, run):
    app = project(tmp_path / "app", "app", work={"path": "nowhere"})
    listed, path = run(app, "work", "list"), run(app, "work", "path")
    assert listed.code == path.code != 0
    assert listed.err.split(": ", 1)[1] == path.err.split(": ", 1)[1]


# -- the fold (Step 7a): what crosses a parent link ------------------------------------

from tcw.store.fs import init as _init  # noqa: E402
from tests.work.jira.conftest import OPTIONAL, STATUSES  # noqa: E402
from tests.work.projects import git  # noqa: E402

CORE_JIRA = {"site": "https://core.example.net", "project": "CORE",
             "credentials": {"email-env": "CORE_EMAIL", "token-env": "CORE_TOKEN"},
             "fields": {"project": "TCW Project", "item": "TCW Item"}}


def jira_mode(**work) -> dict:
    """`work:` of a project in Jira mode: its own backend, and a status of its
    own for every enabled stage."""
    stages = {name: ({"enabled": True, "status": status} if name in OPTIONAL
                     else {"status": status}) for name, status in STATUSES.items()}
    return {"backend": "jira", "stages": stages, **work}


def made(tmp_path: Path, project_id: str, *, parents=None, children=None,
         work: dict | None = None, **top) -> Path:
    """A project at `tmp_path/<id>`, a git repository with a taxonomy and a
    work store, its `parents:`, `children:` and `work:` as given and nothing
    else, so every key an outcome depends on is the test's."""
    root = tmp_path / project_id
    root.mkdir(parents=True)
    git(root, "init", "-q")
    _init(["taxonomy", "capabilities", "work"], root, project_id)
    document = yaml.safe_load(config_file(root).read_text())
    if parents is not None:
        document["parents"] = parents
    if children is not None:
        document["children"] = children
    if work is not None:
        document["work"] = work
    document.update(top)
    write_config_file(config_file(root), yaml.safe_dump(document, sort_keys=False))
    return root.resolve()


def tags_of(root: Path, env: dict | None = None) -> set:
    ran = tcw(root, "work", "tags", "list", env=env)
    assert ran.code == 0, ran
    return set(ran.out.split())


def lines_of(ran) -> list[str]:
    return [line for line in ran.out.splitlines() if line.strip()]


def test_ac1_the_inherited_keys_cross(tmp_path):
    made(tmp_path, "core", work=jira_mode(jira=CORE_JIRA, tags=["a", "b"]))
    app = made(tmp_path, "app", parents=["core"], work=jira_mode())
    config = load_config(app)
    assert problems(config) == []
    assert (config.jira.site, config.jira.project, config.jira.email_env) == (
        "https://core.example.net", "CORE", "CORE_EMAIL")
    assert tags_of(app) == {"a", "b"}
    assert config.sources == ("core", "app")


def test_ac1_an_inherited_value_names_where_it_came_from(tmp_path):
    """Design 2.6, 1.4: the origin of an inherited value is the declaring
    project's file, and its folder that project's root."""
    core = made(tmp_path, "core", work=jira_mode(jira=CORE_JIRA))
    app = made(tmp_path, "app", parents=["core"], work=jira_mode())
    origin = load_config(app).origins[("work", "jira", "site")]
    assert (origin.project, origin.layer, origin.file) == (
        "core", "project", core / ".tcw" / "tcw-config.yaml")
    assert origin.folder == core
    assert origin.rank < load_config(app).origins[("work", "backend")].rank


def test_ac2_nothing_else_crosses(tmp_path, run):
    made(tmp_path, "core", work={
        "hooks": {"timeout": 5},
        "stages": {"spec": {"prompt": [{"blob": "core-text"}]}},
        "procedures": {"search": [{"blob": "core-search"}]},
        "documentation": [{"path": "README.md", "trigger": "Public-API",
                           "description": "the readme"}],
        "path": "elsewhere"})
    app = made(tmp_path, "app", parents=["core"])
    config = load_config(app)
    from tcw.work.config import HookLimits
    assert config.work.hooks.timeout == HookLimits().timeout
    item = run(app, "work", "new", "thing").out.strip()
    for argv in (("work", "stage", "prompt", "spec", item),
                 ("work", "procedure", "search")):
        ran = run(app, *argv)
        assert ran.code == 0, (argv, ran)
        assert "core-text" not in ran.out and "core-search" not in ran.out, argv
    docs = run(app, "work", "docs")
    assert docs.code == 0 and "README.md" not in docs.out, docs
    path = run(app, "work", "path")
    assert Path(path.out.strip()).resolve().is_relative_to(app), path


def test_ac3_only_a_link_that_passes_config_carries_it(tmp_path):
    made(tmp_path, "core", work=jira_mode(jira=CORE_JIRA, tags=["a", "b"]))
    app = made(tmp_path, "app", parents=[{"id": "core", "inherit": ["taxonomy"]}],
               work=jira_mode(jira={"project": "APP"}))
    ran = tcw(app, "validate")
    assert ran.code == 1, ran
    assert any(line.startswith("error:") and "work.jira.site: required" in line
               for line in lines_of(ran)), ran
    set_work(app, {})
    assert tags_of(app) == set()
    set_work(app, {}, parents=[{"id": "core", "inherit": ["config"]}])
    assert tags_of(app) == {"a", "b"}


def test_ac4_several_levels(tmp_path):
    made(tmp_path, "core", work={"tags": ["a"]})
    lib = made(tmp_path, "lib", parents=["core"])
    app = made(tmp_path, "app", parents=["lib"])
    assert tags_of(app) == {"a"}
    set_work(lib, {"tags": ["c"]})
    assert tags_of(app) == {"c"}


def test_ac5_the_last_project_that_declares_a_key_wins(tmp_path):
    made(tmp_path, "bb", work={"tags": ["b"]})
    made(tmp_path, "cc", parents=["bb"], work={"tags": ["c"]})
    dd = made(tmp_path, "dd", parents=["bb"])
    ee = made(tmp_path, "ee", parents=["cc", "dd"])
    assert tags_of(ee) == {"c"}
    set_work(dd, {"tags": ["d"]})
    assert tags_of(ee) == {"d"}
    set_work(dd, {"tags": [INHERIT, "d"]})
    assert tags_of(ee) == {"c", "d"}
    assert tags_of(dd) == {"b", "d"}


def test_ac6_mappings_merge_key_by_key(tmp_path):
    made(tmp_path, "core", work=jira_mode(jira=CORE_JIRA))
    app = made(tmp_path, "app", parents=["core"], work=jira_mode(jira={"project": "APP"}))
    jira = load_config(app).jira
    assert jira.project == "APP"
    assert (jira.site, jira.email_env, jira.fields.item) == (
        "https://core.example.net", "CORE_EMAIL", "TCW Item")


def test_ac7_lists_are_replaced_and_inherit_adds(tmp_path):
    made(tmp_path, "core", work={"tags": ["a", "b"]})
    app = made(tmp_path, "app", parents=["core"], work={"tags": ["c"]})
    assert tags_of(app) == {"c"}
    set_work(app, {"tags": [INHERIT, "c"]})
    assert tags_of(app) == {"a", "b", "c"}


def test_ac8_null_removes_an_inherited_value(tmp_path):
    jira = {**CORE_JIRA, "fields": {**CORE_JIRA["fields"], "effort": "Effort"}}
    made(tmp_path, "core", work=jira_mode(jira=jira, tags=["a"]))
    app = made(tmp_path, "app", parents=["core"], work=jira_mode(tags=None))
    assert tags_of(app) == set()
    set_work(app, jira_mode(jira={"fields": {"effort": None}}))
    config = load_config(app)
    assert problems(config) == []
    assert config.jira.fields.effort is None
    assert config.jira.site == "https://core.example.net"
    document = yaml.safe_load(config_file(app).read_text())
    del document["work"]
    write_config_file(config_file(app), yaml.safe_dump(document) + "work:\n")
    assert tags_of(app) == {"a"}


def test_ac8_null_at_a_jira_key_restores_its_default(tmp_path):
    made(tmp_path, "core", work=jira_mode(jira={**CORE_JIRA, "timeout": 40}))
    app = made(tmp_path, "app", parents=["core"], work=jira_mode(jira={"timeout": None}))
    config = load_config(app)
    assert problems(config) == []
    from tcw.work.jira.config import DEFAULT_TIMEOUT
    assert config.jira.timeout == DEFAULT_TIMEOUT


def test_ac9_the_backend_is_not_inherited(tmp_path, run):
    made(tmp_path, "core", work=jira_mode(jira=CORE_JIRA, tags=["a"]))
    app = made(tmp_path, "app", parents=["core"])
    config = load_config(app)
    assert config.work.backend == "filesystem"
    assert problems(config) == []
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    assert "work.jira" not in ran.out + ran.err
    assert tcw(app, "work", "list").code == 0
    set_work(app, {"jira": {"site": "https://x.example.net"}})
    assert any("'jira' is only read with `backend: jira`" in p
               for p in problems(load_config(app)))


def test_ac16_a_gap_behind_a_link_that_passes_no_configuration(tmp_path):
    made(tmp_path, "core", work={"tags": ["a"]})
    app = made(tmp_path, "app", parents=[{"id": "ws", "inherit": "none"}, "core"])
    assert tags_of(app) == {"a"}
    assert tcw(app, "work", "list").code == 0


# -- personal settings of a source (Design 5.2, AC 11, 12, 33) ---------------------------


def test_ac11_an_ancestors_personal_settings_flow_down(tmp_path):
    env = personal_env(tmp_path)
    core = made(tmp_path, "core", work=jira_mode(jira=CORE_JIRA))
    app = made(tmp_path, "app", parents=["core"], work=jira_mode())
    write_local_config(core, "work:\n  jira:\n    credentials:\n      email-env: MINE\n")

    def email(**more) -> str:
        script = ("import sys; from pathlib import Path; from tcw.config import "
                  "load_config\nfrom tcw.store.project import FsProjectRegistry\n"
                  f"app = Path({str(app)!r}); core = Path({str(core)!r})\n"
                  "if sys.argv[1] == 'app':\n print(load_config(app).jira.email_env)\n"
                  "else:\n r = FsProjectRegistry.open(app)\n"
                  " print(load_config(core, personal=False, registry=r).jira.email_env)\n")
        import os
        import subprocess
        full = {**os.environ, **env, **more}
        full = {k: v for k, v in full.items() if v is not None}
        out = {}
        for who in ("app", "core"):
            done = subprocess.run([sys.executable, "-c", script, who], env=full,
                                  capture_output=True, text=True, cwd=app)
            assert done.returncode == 0, done.stderr
            out[who] = done.stdout.strip()
        return out["app"], out["core"]

    assert email() == ("MINE", "CORE_EMAIL")
    variable = {"TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__CORE": "VAR"}
    assert email(**variable)[0] == "VAR"
    write_local_config(app, "work:\n  jira:\n    credentials:\n      email-env: APPS\n")
    assert email(**variable)[0] == "APPS"
    assert email(TCW_NO_PERSONAL_CONFIG="1")[0] == "CORE_EMAIL"
    local_config_file(app).unlink()
    assert email(**variable)[1] == "VAR"
    assert email(**variable, TCW_NO_PERSONAL_CONFIG="1")[1] == "CORE_EMAIL"


def test_ac12_the_user_wide_file_still_beats_the_shared_file(tmp_path):
    env = personal_env(tmp_path)
    user = tmp_path / "xdg" / "tcw" / "config.yaml"
    write_config_file(user, "work:\n  stages:\n    spec:\n      prompt:\n"
                            "      - blob: mine\n")
    app = made(tmp_path, "app", work={"stages": {"spec": {"prompt": [{"blob": "team"}]}}})
    item = tcw(app, "work", "new", "x", env=env).out.strip()
    shown = tcw(app, "work", "stage", "prompt", "spec", item, env=env)
    assert "mine" in shown.out and "team" not in shown.out, shown


def test_ac12_the_user_wide_file_is_checked_once(tmp_path, monkeypatch):
    for key, value in personal_env(tmp_path).items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    user = tmp_path / "xdg" / "tcw" / "config.yaml"
    write_config_file(user, "work:\n  tags: [u]\n  jira:\n    credentials:\n"
                            "      email-env: MINE\n")
    made(tmp_path, "core", work=jira_mode(jira=CORE_JIRA))
    app = made(tmp_path, "app", parents=["core"], work=jira_mode())
    config = load_config(app)
    tag_problems = [p for p in config.problems if p.key_path[:2] == ("work", "tags")]
    assert len(tag_problems) == 1 and tag_problems[0].file == user, problems(config)
    assert len(config.refused) == 1
    assert config.inherited_problems == [] and config.inherited_refusals == []
    assert config.jira.email_env == "MINE"
    ran = tcw(app, "validate", env=personal_env(tmp_path))
    found = [line for line in lines_of(ran) if "work.tags" in line]
    assert len(found) == 1 and found[0].startswith("error:"), ran


def test_ac33_an_ancestors_personal_file_in_a_linked_worktree(tmp_path):
    env = personal_env(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    write_config(repo, yaml.safe_dump({"id": "core", "work": jira_mode(jira=CORE_JIRA)},
                                      sort_keys=False))
    write_config(repo / "app", yaml.safe_dump(
        {"id": "app", "parents": ["core"], "work": jira_mode()}, sort_keys=False))
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "two projects")
    write_local_config(repo, "work:\n  jira:\n    credentials:\n      email-env: MINE\n")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "-q", str(linked))
    import os
    import subprocess
    full = {k: v for k, v in {**os.environ, **env}.items() if v is not None}
    done = subprocess.run(
        [sys.executable, "-c", "from tcw.config import load_config; "
         f"print(load_config({str(linked / 'app')!r}).jira.email_env)"],
        env=full, capture_output=True, text=True, cwd=linked / "app")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "MINE"


# -- a project read for itself (Design 5.2, plan choices 3, 15) --------------------------


def test_a_project_read_for_itself_needs_the_registry(tmp_path):
    made(tmp_path, "base", work={"tags": ["b"]})
    core = made(tmp_path, "core", parents=["base"])
    with pytest.raises(TypeError, match="registry"):
        load_config(core, personal=False)
    alone = made(tmp_path, "alone")
    assert load_config(alone, personal=False).problems == []


def test_a_project_read_for_itself_takes_its_parents_and_keeps_its_id(tmp_path, run):
    from tcw.store.project import FsProjectRegistry
    from tcw.work.open import project_facts
    made(tmp_path, "base", work={"tags": ["b"]})
    lib = made(tmp_path, "lib", parents=["base"])
    app = made(tmp_path, "app", parents=["lib"])
    made_item = run(lib, "work", "new", "lib thing", "--tag", "b")
    assert made_item.code == 0, made_item
    item = made_item.out.strip()
    shown = run(app, "work", "show", item)
    assert shown.code == 0, shown
    assert "owner: lib" in shown.out and "tags: b" in shown.out, shown.out
    registry = FsProjectRegistry.open(app)
    facts = project_facts(lib, personal=False, registry=registry)
    assert facts.project == "lib"
    assert facts.layered.work.tags == ("b",)


def test_each_reading_of_another_project_passes_the_registry(tmp_path, run):
    """Filing into a descendant and `edit --blocks` read it for itself, its
    parents found through the command's registry: no `TypeError`."""
    made(tmp_path, "base", work={"tags": ["b"]})
    kid = made(tmp_path, "kid", parents=["app", "base"])
    app = made(tmp_path, "app", children=["kid"])
    commit_all(kid)
    filed = run(app, "work", "new", "--project", "kid", "filed")
    assert filed.code == 0, filed
    commit_all(kid)
    mine = run(app, "work", "new", "mine").out.strip()
    edited = run(app, "work", "edit", mine, "--blocks", filed.out.strip())
    assert edited.code == 0, edited


# -- a problem in an inherited value (Step 7b, Design 1.6, AC 10) ------------------------


def test_ac10_an_ancestors_problem_stops_only_what_reads_it(tmp_path):
    core = made(tmp_path, "core", work={"tags": "notalist"})
    app = made(tmp_path, "app", parents=["core"])
    whole = str(core / ".tcw" / "tcw-config.yaml")
    for argv in (("work", "tags", "list"), ("work", "new", "y", "--tag", "t")):
        ran = tcw(app, *argv)
        assert ran.code == 1, (argv, ran)
        assert whole in ran.err and "work.tags" in ran.err, (argv, ran.err)
    assert not list((app / "docs" / "work").glob("*-y"))
    for argv in (("work", "list"), ("work", "new", "x"), ("taxonomy", "list")):
        ran = tcw(app, *argv)
        assert ran.code == 0, (argv, ran)
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    warnings = [line for line in lines_of(ran) if line.startswith("warning:")]
    assert len(warnings) == 1 and whole in warnings[0] and "work.tags" in warnings[0], ran
    assert tcw(core, "validate").code == 1
    set_work(app, {"tags": ["x"]})
    assert tags_of(app) == {"x"}
    ran = tcw(app, "validate")
    assert ran.code == 0 and "warning:" not in ran.out, ran


def test_ac10_any_other_problem_of_an_ancestor_is_not_the_readers(tmp_path):
    core = made(tmp_path, "core", work={"hooks": {"timeout": "soon"}})
    app = made(tmp_path, "app", parents=["core"])
    assert tcw(app, "work", "list").code == 0
    ran = tcw(app, "validate")
    assert ran.code == 0 and "timeout" not in ran.out + ran.err, ran
    assert tcw(core, "validate").code == 1


def test_ac10_in_jira_mode_a_broken_jira_block_is_a_warning(tmp_path):
    core = made(tmp_path, "core", work=jira_mode(jira={**CORE_JIRA, "site": "nope"}))
    app = made(tmp_path, "app", parents=["core"], work=jira_mode())
    listed = tcw(app, "work", "list")
    assert listed.code == 1 and "work.jira.site" in listed.err, listed
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    [warning] = [line for line in lines_of(ran) if line.startswith("warning:")]
    assert str(core / ".tcw" / "tcw-config.yaml") in warning and "work.jira.site" in warning


def test_a_refused_value_in_an_ancestors_local_file_is_a_warning(tmp_path):
    env = personal_env(tmp_path)
    core = made(tmp_path, "core", work={"tags": ["a"]})
    app = made(tmp_path, "app", parents=["core"])
    write_local_config(core, "work:\n  tags: [x]\n")
    assert tags_of(app, env) == {"a"}
    ran = tcw(app, "validate", env=env)
    assert ran.code == 0, ran
    [warning] = [line for line in lines_of(ran) if line.startswith("warning:")]
    assert str(local_config_file(core)) in warning, warning


# -- a gap (Step 7c, Design 3) ----------------------------------------------------------


GAP_TAGS = "'app' inherits its configuration (work.tags) from project 'core', which is " \
           "not on this machine:"
SUFFIX = "could not check the configuration inherited from it"


def test_ac13_a_missing_parent_in_filesystem_mode(tmp_path):
    app = made(tmp_path, "app", parents=["core"])
    new = tcw(app, "work", "new", "x")
    assert new.code == 0, new
    item = new.out.strip()
    for argv in (("work", "list"), ("work", "show", item),
                 ("work", "advance", item, "--dry-run"), ("projects", "list"),
                 ("taxonomy", "list")):
        ran = tcw(app, *argv)
        assert ran.code == 0, (argv, ran)
    for argv in (("work", "new", "y", "--tag", "t"), ("work", "tags", "list")):
        ran = tcw(app, *argv)
        assert ran.code == 7 and GAP_TAGS in ran.err, (argv, ran)
    assert not list((app / "docs" / "work").glob("*-y"))
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    assert not [line for line in lines_of(ran) if line.startswith("error:")], ran
    [finding] = [line for line in lines_of(ran) if line.startswith("unresolved:")]
    assert "'core'" in finding and SUFFIX in finding, finding
    assert finding.count(SUFFIX) == 1
    set_work(app, {"tags": ["t"]})
    for argv in (("work", "new", "y", "--tag", "t"), ("work", "tags", "list")):
        assert tcw(app, *argv).code == 0, argv
    set_work(app, {}, parents=[{"id": "core", "inherit": ["taxonomy", "capabilities"]}])
    listed = tcw(app, "work", "tags", "list")
    assert (listed.code, listed.out) == (0, ""), listed


def test_ac13_an_undecided_key_is_no_tags_only_by_mistake(tmp_path):
    """What the withheld value protects: read as no tags, `tags list` would
    print nothing and exit 0, and `new --tag` would refuse the tag with exit
    2. The mutation check of Step 7c makes those happen."""
    app = made(tmp_path, "app", parents=["core"])
    config = load_config(app)
    assert isinstance(config.work.tags, Withheld)
    with pytest.raises(InheritedUnavailable, match=r"\(work\.tags\)"):
        list(config.work.tags)
    assert config.problems == [] and config.gaps_withholding == ("core",)


@pytest.fixture
def no_requests(monkeypatch):
    from tcw.work.jira import client
    sent: list = []

    def refuse(self, method, path, *args, **kwargs):
        sent.append((method, path))
        raise AssertionError("a Jira request was made")
    monkeypatch.setattr(client.JiraClient, "_request", refuse)
    return sent


def test_ac14_a_missing_parent_in_jira_mode(tmp_path, run, no_requests):
    lib = made(tmp_path, "lib")
    lib_item = run(lib, "work", "new", "lib thing").out.strip()
    app = made(tmp_path, "app", parents=["core", {"id": "lib", "inherit": "none"}],
               work=jira_mode(jira={"project": "APP"}))
    listed = run(app, "work", "list")
    assert listed.code == 7 and "(work.jira)" in listed.err, listed
    assert no_requests == []
    drift = run(app, "capabilities", "drift")
    assert drift.code == 7 and "(work.jira)" in drift.err, drift
    for argv in (("work", "lifecycle"), ("work", "docs"), ("work", "stage", "prompt", "spec"),
                 ("work", "procedure", "search"), ("work", "path"), ("taxonomy", "list")):
        ran = run(app, *argv)
        assert ran.code == 0, (argv, ran)
    shown = run(app, "work", "show", lib_item)
    assert shown.code == 0 and "owner: lib" in shown.out, shown
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    [finding] = [line for line in lines_of(ran) if line.startswith("unresolved:")]
    assert "'core'" in finding
    assert no_requests == []


def test_ac14_capabilities_drift_in_filesystem_mode_is_not_stopped(tmp_path):
    app = made(tmp_path, "app", parents=["core"])
    assert tcw(app, "capabilities", "drift").code == 0


def test_ac14_references_into_the_project_are_answered_from_its_folders(tmp_path, run):
    from tests.test_capabilities_rm import write_cap
    from tests.work.projects import write_item
    from tcw.store.fs import init
    app = made(tmp_path, "app", parents=["core"], work=jira_mode(jira={"project": "APP"}))
    init(["capabilities"], app, "app")
    write_item(app, "APP-1-thing", {"ticket": "https://x.example.net/browse/APP-1"})
    write_cap(app, "cli", id="cap-cli00001", Status="Supported")
    (app / "docs" / "capabilities" / "cli" / "description.md").write_text(
        "See [this](tcw://app.work/APP-1-thing).\n")
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    assert "APP-1" not in ran.out, ran
    lib = made(tmp_path, "lib")
    item = run(lib, "work", "new", "lib thing").out.strip()
    folder = item.partition("/")[2]
    path = lib / "docs" / "work" / folder / "item.yaml"
    document = yaml.safe_load(path.read_text())
    document["blocked-by"] = ["app.work/APP-1-thing"]
    path.write_text(yaml.safe_dump(document))
    ran = tcw(lib, "validate")
    assert ran.code == 0, ran
    assert "APP-1" not in ran.out, ran


@pytest.mark.parametrize("text", ["id: core\nparents: notalist\n", "id: core\nwork: [\n"])
def test_ac15_an_unreadable_parent(tmp_path, text):
    write_config(tmp_path / "core", text)
    app = made(tmp_path, "app", parents=["core"])
    # A file that cannot be read declares no ID the search could match.
    write_manifest(app, {"core": "../core"})
    listed = tcw(app, "work", "tags", "list")
    assert listed.code == 7, listed
    assert ("'app' inherits its configuration (work.tags) through project 'core', whose "
            "parents could not be read") in listed.err
    assert tcw(app, "work", "list").code == 0
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    [finding] = [line for line in lines_of(ran) if line.startswith("unresolved:")]
    assert "'core'" in finding and SUFFIX in finding, finding


def test_ac15_a_descendants_unreadable_file_stays_an_error(tmp_path):
    write_config(tmp_path / "core", "id: core\nparents: [app]\nwork: [\n")
    app = made(tmp_path, "app", children=["core"])
    write_manifest(app, {"core": "../core"})
    ran = tcw(app, "validate")
    assert ran.code == 1, ran
    assert any(line.startswith("error:") and "core" in line for line in lines_of(ran))


@pytest.fixture(params=["parents", "loop"])
def no_order(request, tmp_path):
    """A project whose configuration sources cannot be had (Design 1.3)."""
    if request.param == "parents":
        app = made(tmp_path, "app", parents="notalist")
    else:
        made(tmp_path, "lib", parents=["top"])
        made(tmp_path, "top", parents=["lib"])
        app = made(tmp_path, "app", parents=["lib"])
    return request.param, app


def test_ac15_when_the_order_cannot_be_had(no_order):
    shape, app = no_order
    config = load_config(app)
    assert config.sources == ("app",)
    listed = tcw(app, "work", "list")
    assert listed.code == 1, listed
    message = listed.err.split(": ", 1)[1]
    if shape == "loop":
        assert "loop in parents: lib -> top -> lib" in message
        assert "loop in parents: lib -> top -> lib" in config.order_error
    tags = tcw(app, "work", "tags", "list")
    assert tags.code == 1 and tags.err.split(": ", 1)[1] == message, tags
    new = tcw(app, "work", "new", "y", "--tag", "t")
    assert new.code == 1 and not list((app / "docs" / "work").glob("*-y")), new
    ran = tcw(app, "validate")
    assert ran.code == 1 and "Traceback" not in ran.err, ran
    assert any(line.startswith("error:") for line in lines_of(ran)), ran
    assert ran.err.rstrip().endswith("unresolved"), ran.err
    set_work(app, {"tags": ["t"], "hooks": {"timeout": "soon"}})
    ran = tcw(app, "validate")
    errors = [line for line in lines_of(ran) if line.startswith("error:")]
    assert ran.code == 1 and len(errors) >= 2 and any("timeout" in e for e in errors), ran
    set_work(app, {"tags": ["t"]})
    assert tags_of(app) == {"t"}


def test_ac15_the_trigger_is_the_projects_own_parents(tmp_path, monkeypatch):
    """Plan re-check B1: with the registry answering an order of the project
    alone, its own refused `parents:` still means no order."""
    from tcw.store.base import ProjectRegistry, SourceEntry
    from tcw.store.base import Project as P
    app = made(tmp_path, "app", parents="notalist")
    monkeypatch.setattr(ProjectRegistry, "source_entries",
                        lambda self, *a, **k: [SourceEntry("app", P("app", app), "here")])
    assert load_config(app).order_error is not None


def test_ac15_a_graph_problem_below_stops_no_tag_command(tmp_path):
    made(tmp_path, "core", work={"tags": ["a"]})
    made(tmp_path, "kid")
    app = made(tmp_path, "app", parents=["core"], children=["kid"])
    assert tags_of(app) == {"a"}


def test_ac29_two_repositories(tmp_path):
    a = made(tmp_path, "a", work={"tags": ["plan"]}, id="ws", children=["app"])
    write_config_file(a / ".gitignore", "b/\n")
    b = made(a, "b", parents=["ws"], id="app")
    assert tags_of(b) == {"plan"}
    commit_all(b)
    # Nowhere near repository A, so nothing finds `ws`.
    clone = tmp_path / "elsewhere" / "alone"
    clone.parent.mkdir()
    git(tmp_path, "clone", "-q", str(b), str(clone))
    assert tcw(clone, "work", "list").code == 0
    listed = tcw(clone, "work", "tags", "list")
    assert listed.code == 7 and "'ws'" in listed.err, listed
    ran = tcw(clone, "validate")
    assert ran.code == 0, ran
    [finding] = [line for line in lines_of(ran) if line.startswith("unresolved:")]
    assert "'ws'" in finding and SUFFIX in finding, finding


# -- `tcw config show` (Step 9, Design 7.1, AC 17) ---------------------------------------


def test_ac17_config_show_prints_what_is_inherited(tmp_path):
    core = made(tmp_path, "core", work=jira_mode(jira=CORE_JIRA, tags=["a", "b"]))
    app = made(tmp_path, "app", parents=["core"], work=jira_mode())
    shown = tcw(app, "config", "show")
    assert shown.code == 0, shown
    values = yaml.safe_load(shown.out)
    assert values["work"]["tags"] == ["a", "b"]
    assert values["work"]["jira"]["site"] == "https://core.example.net"
    origin = tcw(app, "config", "show", "--origin")
    [site] = [line for line in origin.out.splitlines() if line.strip().startswith("site:")]
    assert str(core / ".tcw" / "tcw-config.yaml") in site, site


def test_ac17_a_variable_is_labelled_with_its_name(tmp_path):
    app = made(tmp_path, "app")
    env = {"TCW_NO_PERSONAL_CONFIG": None, "TCW_USER_NAME__APP": "Robin",
           "HOME": str(tmp_path)}
    shown = tcw(app, "config", "show", env=env)
    assert yaml.safe_load(shown.out)["user"]["name"] == "Robin"
    origin = tcw(app, "config", "show", "--origin", env=env)
    [name] = [line for line in origin.out.splitlines() if "Robin" in line]
    assert name.endswith("# environment: TCW_USER_NAME__APP"), name


@pytest.mark.parametrize("flags", [(), ("--origin",)])
def test_ac17_config_show_stops_on_an_undecided_key(tmp_path, flags):
    app = made(tmp_path, "app", parents=["core"])
    shown = tcw(app, "config", "show", *flags)
    assert shown.code == 7 and shown.out == "" and "(work.tags)" in shown.err, shown
    set_work(app, jira_mode(jira={"project": "APP"}))
    shown = tcw(app, "config", "show", *flags)
    assert shown.code == 7 and shown.out == "" and "(work.tags)" in shown.err, shown


def test_ac17_config_show_stops_on_a_broken_key(tmp_path):
    made(tmp_path, "core", work={"tags": "notalist"})
    app = made(tmp_path, "app", parents=["core"])
    shown = tcw(app, "config", "show")
    assert shown.code == 1 and shown.out == "", shown


def test_ac12_the_user_wide_files_shared_key_is_set_aside_once(tmp_path):
    env = personal_env(tmp_path)
    write_config_file(tmp_path / "xdg" / "tcw" / "config.yaml", "work:\n  tags: [u]\n")
    made(tmp_path, "core", work={"tags": ["a"]})
    app = made(tmp_path, "app", parents=["core"])
    shown = tcw(app, "config", "show", "--origin", env=env)
    assert sum(line.startswith("# refused: work.tags") for line in
               shown.out.splitlines()) == 1, shown.out


# -- the tag registry commands (Step 10, Design 6, AC 18) --------------------------------


def test_ac18_tags_add_and_rm_in_a_child(tmp_path):
    core = made(tmp_path, "core", work={"tags": ["a"]})
    lib = made(tmp_path, "lib", parents=["core"])
    app = made(tmp_path, "app", parents=["lib"])
    others = {p: config_file(p).read_bytes() for p in (core, lib)}
    added = tcw(app, "work", "tags", "add", "z")
    assert added.code == 0, added
    assert yaml.safe_load(config_file(app).read_text())["work"]["tags"] == [INHERIT, "z"]
    assert {p: config_file(p).read_bytes() for p in (core, lib)} == others
    assert tags_of(app) == {"a", "z"}
    before = config_file(app).read_bytes()
    assert tcw(app, "work", "tags", "add", "a").code == 0
    assert config_file(app).read_bytes() == before
    refused = tcw(app, "work", "tags", "rm", "a")
    assert refused.code == 3 and "tag 'a' is inherited from 'core'" in refused.err, refused
    assert config_file(app).read_bytes() == before
    assert tcw(app, "work", "tags", "rm", "z").code == 0
    assert yaml.safe_load(config_file(app).read_text())["work"]["tags"] == [INHERIT]
    assert tags_of(app) == {"a"}
    assert tcw(app, "work", "tags", "rm", "nowhere").code == 4


def test_ac18_a_child_keeps_following_parents_with_no_tags_yet(tmp_path):
    core = made(tmp_path, "core")
    app = made(tmp_path, "app", parents=["core"])
    assert tcw(app, "work", "tags", "add", "z").code == 0
    assert yaml.safe_load(config_file(app).read_text())["work"]["tags"] == [INHERIT, "z"]
    set_work(core, {"tags": ["q"]})
    assert tags_of(app) == {"q", "z"}


def test_ac18_a_project_with_no_parents_writes_what_it_wrote(tmp_path):
    app = made(tmp_path, "app", work={"tags": ["b"]})
    assert tcw(app, "work", "tags", "add", "c", "a").code == 0
    assert yaml.safe_load(config_file(app).read_text())["work"]["tags"] == ["a", "b", "c"]
    assert tcw(app, "work", "tags", "rm", "b").code == 0
    assert yaml.safe_load(config_file(app).read_text())["work"]["tags"] == ["a", "c"]
    bare = made(tmp_path, "bare")
    assert tcw(bare, "work", "tags", "add", "x").code == 0
    assert yaml.safe_load(config_file(bare).read_text())["work"]["tags"] == ["x"]


def test_a_broken_key_that_is_also_undecided_is_undecided(tmp_path):
    """Design 1.6: `lib` passes broken tags, and `core`, after it in the load
    order, is missing, so what reaches `app` is not known: exit 7, and no
    warning."""
    made(tmp_path, "lib", work={"tags": [{"inherit": 5}, "a"]})
    app = made(tmp_path, "app", parents=["lib", "core"])
    config = load_config(app)
    assert config.sources == ("lib", "core", "app")
    assert config.inherited_problems == []
    with pytest.raises(InheritedUnavailable):
        config.require("work.tags")
    ran = tcw(app, "validate")
    assert ran.code == 0 and "warning:" not in ran.out, ran


# -- the decided keys under an undecided `work.jira` (Design 3.2) ------------------------


BAD_TIMEOUT = "work.jira.timeout: must be a positive number of seconds"
BAD_EMAIL = "work.jira.credentials.email-env: must name an environment variable"


def test_a_projects_own_decided_jira_keys_are_checked_behind_a_gap(tmp_path):
    """`core` is missing, so `work.jira` is undecided; the keys `app` sets
    itself are still checked, and the ones it leaves to `core` are not
    "required"."""
    app = made(tmp_path, "app", parents=["core"], work=jira_mode(jira={
        "project": "APP", "timeout": "soon", "credentials": {"email-env": "bad name"}}))
    found = problems(load_config(app))
    assert [p for p in found if BAD_TIMEOUT in p] and [p for p in found if BAD_EMAIL in p], found
    assert not [p for p in found if "required" in p], found
    ran = tcw(app, "validate")
    assert ran.code == 1, ran
    errors = [line for line in lines_of(ran) if line.startswith("error:")]
    assert len(errors) == 2, ran
    assert any(BAD_TIMEOUT in line for line in errors), ran
    assert any(BAD_EMAIL in line for line in errors), ran
    assert "required" not in ran.out, ran


def test_a_projects_own_bad_key_with_no_gap_is_reported_as_before(tmp_path):
    app = made(tmp_path, "app", work=jira_mode(jira={
        "project": "APP", "timeout": "soon", "credentials": {"email-env": "bad name"}}))
    found = problems(load_config(app))
    assert [p for p in found if BAD_TIMEOUT in p] and [p for p in found if BAD_EMAIL in p], found
    assert [p for p in found if "work.jira.site: required" in p], found


def test_an_ancestors_decided_jira_key_behind_a_gap_gives_a_warning(tmp_path):
    """`lib` comes after the missing `core` in the load order, so the
    `timeout` it passes is decided, and wrong: a warning at `lib`'s file, as
    for any broken inherited key, while `work.jira` stays undecided (exit 7)
    and the keys no one after `core` sets are not "required"."""
    lib = made(tmp_path, "lib", work=jira_mode(jira={"timeout": "soon"}))
    app = made(tmp_path, "app", parents=["core", "lib"],
               work=jira_mode(jira={"project": "APP"}))
    config = load_config(app)
    assert config.sources == ("core", "lib", "app")
    assert problems(config) == []
    assert [str(p) for p in config.inherited_problems if BAD_TIMEOUT in str(p)], \
        config.inherited_problems
    with pytest.raises(InheritedUnavailable, match=r"\(work\.jira\)"):
        config.require("work.jira")
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    [warning] = [line for line in lines_of(ran) if line.startswith("warning:")]
    assert BAD_TIMEOUT in warning and str(config_file(lib)) in warning, ran
    assert "required" not in ran.out, ran


def test_an_ancestors_jira_key_before_the_gap_stays_undecided(tmp_path):
    """The same `timeout`, passed by `lib` before the missing `core`: what
    reaches `app` is not known, so no warning (Design 1.6)."""
    made(tmp_path, "lib", work=jira_mode(jira={"timeout": "soon"}))
    app = made(tmp_path, "app", parents=["lib", "core"],
               work=jira_mode(jira={"project": "APP"}))
    config = load_config(app)
    assert config.sources == ("lib", "core", "app")
    assert problems(config) == [] and config.inherited_problems == []
    ran = tcw(app, "validate")
    assert ran.code == 0 and "warning:" not in ran.out, ran


def test_an_unknown_jira_key_the_project_sets_is_reported_behind_a_gap(tmp_path):
    app = made(tmp_path, "app", parents=["core"], work=jira_mode(jira={
        "project": "APP", "bogus": {"a": 1}, "other": 3}))
    found = problems(load_config(app))
    assert len(found) == 2, found
    assert all("unknown key" in p for p in found), found
    assert {p.split(": ")[1] for p in found} == {"work.jira.bogus", "work.jira.other"}


BAD_KEYS = {"work.jira.bogus", "work.jira.priorities.bogus"}


@pytest.mark.parametrize("parents", [["core", "lib"], ["lib"]], ids=["gap", "no-gap"])
def test_an_ancestors_unknown_jira_keys_give_a_warning(tmp_path, parents):
    """`lib` passes two keys TCW does not know, one inside a key it does
    know. Each is marked at the longest known key above it, but whether its
    value is known is decided by its own key: after the missing `core` they
    are `lib`'s own, so both are warnings at `lib`'s file, as with no gap."""
    lib = made(tmp_path, "lib", work=jira_mode(jira={
        "bogus": 1, "priorities": {"bogus": "x"}}))
    app = made(tmp_path, "app", parents=parents, work=jira_mode(jira={
        "project": "APP", **({} if "core" in parents else {
            k: v for k, v in CORE_JIRA.items() if k != "project"})}))
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    warnings = [line for line in lines_of(ran) if line.startswith("warning:")]
    assert len(warnings) == 2, ran
    assert all(str(config_file(lib)) in w and "unknown key" in w for w in warnings), ran
    assert {key for key in BAD_KEYS for w in warnings if key + ":" in w} == BAD_KEYS, ran


def test_an_unknown_key_set_to_an_empty_mapping_is_reported_behind_a_gap(tmp_path):
    """An empty mapping replaces nothing, but its key is still there, and
    unknown: reported behind a gap as with none."""
    for parents in (["core"], None):
        app = made(tmp_path / str(bool(parents)), "app", parents=parents,
                   work=jira_mode(jira={"project": "APP", "bogus": {}}))
        found = [p for p in problems(load_config(app)) if "unknown key" in p]
        assert len(found) == 1 and "work.jira.bogus" in found[0], (parents, found)



@pytest.mark.parametrize("parents,warned", [(["core", "lib"], True), (["lib", "core"], False),
                                            (["lib"], True)],
                         ids=["after-the-gap", "before-the-gap", "no-gap"])
def test_an_ancestors_bad_tag_entry_is_decided_by_its_place(tmp_path, parents, warned):
    """`lib`'s tags hold an `inherit: true` entry, so they replace nothing and
    `work.tags` stays undecided behind the missing `core`. Its second entry
    is wrong whatever reaches it: after `core` it is `lib`'s own text, and a
    warning; before `core`, what reaches `app` is not known, so none."""
    lib = made(tmp_path, "lib", work={"tags": [{"inherit": True}, {"inherit": 5}]})
    app = made(tmp_path, "app", parents=parents)
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    warnings = [line for line in lines_of(ran) if line.startswith("warning:")]
    if not warned:
        assert warnings == [], ran
        return
    [warning] = warnings
    assert str(config_file(lib)) in warning and "work.tags[1]" in warning, ran
