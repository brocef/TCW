"""The family `F` of TCW-113's acceptance criteria, in the 4.0 layout.

`build_family` makes the projects the spec's criteria use (spec, Acceptance
criteria, the opening list), each in its own folder side by side, each a git
repository with all three stores, its links under `parents:` and
`children:`, and located by manifest entries:

- `docs` has no parents and lists `shared` and `other`;
- `shared` has `docs` as its parent, passing `docs_passes` (nothing unless
  given), and lists `desktop`, `server` and `mobile`;
- `desktop` and `server` each have `shared` as their parent, passing all;
- `other` has `docs` as its parent (a sibling of `shared`);
- `mobile` is named in `shared`'s manifest at a folder that does not exist,
  with a repository.

Objects: `shared`'s capabilities `abc` (`name: Abc`, `Status: Missing`) and
`ghi` (`Status: Missing`), complete, and its term `invoice`; `desktop`'s own
`abc` holding only `Status: Supported`, and a complete `def`; `server`'s own
`abc` holding only `Status: Omitted`; `docs`'s term `plan`. Each of `docs`,
`shared`, `desktop`, `server` and `other` has one unfinished work item,
`2026-10-01-<id>-item`.

`Family.run` runs `tcw` in a project's folder in this process, through
`tcw.cli.main`, so a test can wrap a function and count its calls.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from tcw.store.fs import init
from tests.projectfiles import config_file, write_config_file, write_manifest
from tests.statefiles import (CAPABILITY_STATE, ITEM_STATE, TAXONOMY_STATE, write_state,
                              write_state_data)

#: The projects on this machine, in the order they are built.
PRESENT = ("docs", "shared", "desktop", "server", "other")
MOBILE_REPOSITORY = "https://example.invalid/mobile.git"
ITEM_STAGE = "request"


def item_folder(project_id: str) -> str:
    """The one unfinished item each project of the family starts with."""
    return f"2026-10-01-{project_id}-item"


@dataclass
class Result:
    code: int
    out: str
    err: str

    @property
    def json(self) -> Any:
        return json.loads(self.out)

    @property
    def lines(self) -> list[str]:
        return self.out.splitlines()

    @property
    def err_lines(self) -> list[str]:
        return self.err.splitlines()


@dataclass
class Family:
    base: Path
    roots: dict[str, Path] = field(default_factory=dict)

    def __getitem__(self, project_id: str) -> Path:
        return self.roots[project_id]

    def run(self, project_id: str, *argv: str, stdin: str = "") -> Result:
        """`tcw <argv>` in `project_id`'s folder, in this process, with
        standard output and standard error captured."""
        from tcw.cli import main
        out, err = io.StringIO(), io.StringIO()
        here = os.getcwd()
        stdin_before = sys.stdin
        os.chdir(self.roots[project_id])
        sys.stdin = io.StringIO(stdin)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    code = main(list(argv))
                except SystemExit as stop:
                    code = stop.code if isinstance(stop.code, int) else 1
        finally:
            sys.stdin = stdin_before
            os.chdir(here)
        return Result(code, out.getvalue(), err.getvalue())

    def remove(self, project_id: str) -> None:
        """Take a project's folder off this machine, its manifest entries
        kept."""
        shutil.rmtree(self.roots[project_id])

    def config(self, project_id: str) -> dict:
        path = config_file(self.roots[project_id])
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def write_config(self, project_id: str, document: dict) -> None:
        body = {k: v for k, v in document.items() if k != "tcw-version"}
        write_config_file(config_file(self.roots[project_id]),
                          yaml.safe_dump(body, sort_keys=False))

    def set_parents(self, project_id: str, parents: list) -> None:
        document = self.config(project_id)
        document["parents"] = parents
        self.write_config(project_id, document)

    def add_parent(self, project_id: str, parent_id: str, *, inherit="all",
                   folder: str | None = None, repository: str | None = None) -> None:
        """Name `parent_id` as another parent of `project_id`, located by a
        manifest entry at `folder` (`../<parent_id>` unless given)."""
        document = self.config(project_id)
        document.setdefault("parents", []).append(
            parent_id if inherit == "all" else {"id": parent_id, "inherit": inherit})
        self.write_config(project_id, document)
        entry: Any = folder or f"../{parent_id}"
        if repository is not None:
            entry = {"path": entry, "repository": repository}
        write_manifest(self.roots[project_id], {parent_id: entry})

    def add_child(self, project_id: str, child_id: str, *,
                  folder: str | None = None) -> None:
        document = self.config(project_id)
        document.setdefault("children", []).append(child_id)
        self.write_config(project_id, document)
        write_manifest(self.roots[project_id], {child_id: folder or f"../{child_id}"})

    def capability(self, project_id: str, path: str, *, description: str | None = None,
                   **fields) -> Path:
        return _object(self.roots[project_id], "capabilities", CAPABILITY_STATE, path,
                       description, fields)

    def term(self, project_id: str, slug: str, *, description: str | None = None,
             **fields) -> Path:
        return _object(self.roots[project_id], "taxonomy", TAXONOMY_STATE, slug,
                       description, fields)

    def item(self, project_id: str, folder: str, **data) -> Path:
        path = self.roots[project_id] / "docs" / "work" / folder
        path.mkdir(parents=True, exist_ok=True)
        write_state(path / ITEM_STATE,
                    yaml.safe_dump({"title": folder, "stage": ITEM_STAGE, **data},
                                   sort_keys=False))
        return path


def _object(root: Path, store: str, state: str, id_path: str,
            description: str | None, fields: dict) -> Path:
    folder = root / "docs" / store / id_path
    write_state_data(folder / state, fields)
    if description is not None:
        (folder / "description.md").write_text(description, encoding="utf-8")
    return folder


def _project(base: Path, project_id: str) -> Path:
    root = base / project_id
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    init(["taxonomy", "capabilities", "work"], root, project_id)
    return root


def build_family(tmp_path: Path, *, docs_passes, extra=None) -> Family:
    """The family `F` under `tmp_path`. `docs_passes` is what `shared`'s
    link to `docs` passes down: "none", "all" or a list of axes, given by
    every caller, since what `shared` inherits is a branch the code under
    test takes. `extra(family)`, when given, runs before the family is
    returned."""
    family = Family(Path(tmp_path))
    for project_id in PRESENT:
        family.roots[project_id] = _project(family.base, project_id)
    links = {
        "docs": {"children": ["shared", "other"]},
        "shared": {"parents": ["docs" if docs_passes == "all"
                               else {"id": "docs", "inherit": docs_passes}],
                   "children": ["desktop", "server", "mobile"]},
        "desktop": {"parents": ["shared"]},
        "server": {"parents": ["shared"]},
        "other": {"parents": ["docs"]},
    }
    for project_id, named in links.items():
        document = family.config(project_id)
        document.update(named)
        family.write_config(project_id, document)
    write_manifest(family["docs"], {"shared": "../shared", "other": "../other"})
    write_manifest(family["shared"], {
        "docs": "../docs", "desktop": "../desktop", "server": "../server",
        "mobile": {"path": "../mobile", "repository": MOBILE_REPOSITORY}})
    write_manifest(family["desktop"], {"shared": "../shared"})
    write_manifest(family["server"], {"shared": "../shared"})
    write_manifest(family["other"], {"docs": "../docs"})

    family.capability("shared", "abc", description="", name="Abc", Status="Missing")
    family.capability("shared", "ghi", description="", name="Ghi", Status="Missing")
    family.term("shared", "invoice", description="", name="Invoice", kind="vocabulary")
    family.capability("desktop", "abc", Status="Supported")
    family.capability("desktop", "def", description="", name="Def", Status="Supported")
    family.capability("server", "abc", Status="Omitted")
    family.term("docs", "plan", description="", name="Plan", kind="vocabulary")
    for project_id in PRESENT:
        family.item(project_id, item_folder(project_id))
    if extra is not None:
        extra(family)
    return family


# -- Jira mode ------------------------------------------------------------------------


def jira_mode(family: Family, project_id: str, fake, *, jira_project: str = "APP",
              email_env: str = "TCW_TEST_JIRA_EMAIL",
              token_env: str = "TCW_TEST_JIRA_TOKEN", stages: dict | None = None,
              tags=("ui", "api")) -> dict[str, str]:
    """Switch `project_id` to `work.backend: jira` against `fake`, keeping
    its items in Jira project `jira_project`, signing in through the
    variables `email_env` and `token_env` (which the test sets). Each of its
    item folders becomes a ticket with a folder named by its key. `stages`
    replaces the stage table (each stage with its `status`); the default is
    the one every Jira fixture of the suite shares. Returns each old folder
    name's new one."""
    from tests.work.jira.conftest import STATUSES, jira_config
    from tests.work.jira.fake import FIELDS
    if jira_project not in fake.projects:
        fake.add_project(jira_project)
    config = jira_config(project_id, jira_project=jira_project, site=fake.site,
                         tags=tags)
    config["jira"]["credentials"] = {"email-env": email_env, "token-env": token_env}
    if stages is not None:
        config["stages"] = stages
    document = family.config(project_id)
    document["work"] = config
    family.write_config(project_id, document)
    work = family[project_id] / "docs" / "work"
    renamed: dict[str, str] = {}
    for old in sorted(p.name for p in work.iterdir() if (p / ITEM_STATE).is_file()):
        data = yaml.safe_load((work / old / ITEM_STATE).read_text(encoding="utf-8"))
        stage = data.get("stage", ITEM_STAGE)
        ticket = fake.ticket(data.get("title", old), project=jira_project,
                             status=(config["stages"].get(stage) or {}).get("status")
                             or STATUSES[stage],
                             assignee=data.get("assignee"))
        new = f"{ticket.key}-{old}"
        ticket.custom[FIELDS["TCW Project"]] = project_id
        ticket.custom[FIELDS["TCW Item"]] = f"{project_id}.work/{new}"
        shutil.rmtree(work / old)
        (work / new).mkdir()
        write_state(work / new / ITEM_STATE,
                    yaml.safe_dump({"ticket": f"{fake.site}/browse/{ticket.key}"}))
        renamed[old] = new
    return renamed
