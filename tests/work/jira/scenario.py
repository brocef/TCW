"""One scripted scenario, run against the fake and, by hand, against a real
Jira site (TCW-71 Design 15.4).

It drives the commands through `tcw.cli.main`, as a person would, and after
each step asserts what the ticket shows, read through a client of its own.
It returns what the live check records: how long a new ticket took to appear
in a search, and the result of `validate --remote`.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from tcw.cli import main
from tcw.work.jira.backend import JiraBackend, folder_key
from tcw.work.jira.mapping import blocker_keys, document_text, scale_name
from tcw.work.model import DOCUMENT, Slug, flow_order, stage as table_stage, start_stage
from tcw.work.open import open_backend

LAG_LIMIT = 60          # seconds step 1's list may wait for the search to catch up


@dataclass
class Result:
    lag: float = 0.0
    validate: tuple[int, str, str] = (0, "", "")
    keys: dict[str, str] = field(default_factory=dict)


@dataclass
class _Run:
    root: Path
    backend: JiraBackend
    say: Callable[[str], None]

    def tcw(self, *argv: str, stdin: str = "") -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        before, stdin_before = Path.cwd(), sys.stdin
        os.chdir(self.root)
        sys.stdin = io.StringIO(stdin)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    code = main(list(argv))
                except SystemExit as stop:
                    code = stop.code if isinstance(stop.code, int) else 1
        finally:
            os.chdir(before)
            sys.stdin = stdin_before
        return code, out.getvalue(), err.getvalue()

    def work(self, *argv: str, stdin: str = "", expect: int = 0) -> str:
        code, out, err = self.tcw("work", *argv, stdin=stdin)
        assert code == expect, f"tcw work {' '.join(argv)}: exit {code}\n{out}{err}"
        return out.strip()

    def fields(self, key: str) -> dict:
        return self.backend.client.issue(key)["fields"]

    def status(self, key: str) -> str:
        return self.fields(key)["status"]["name"]

    def newest_comment(self, key: str) -> str:
        return document_text(self.backend.client.comments(key, 1)[0].body)

    def write(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def run(project_root: Path, *, live: bool, say: Callable[[str], None] = print) -> Result:
    backend = open_backend(project_root)
    assert isinstance(backend, JiraBackend)
    r = _Run(Path(project_root), backend, say)
    result = Result()
    ids = backend.metadata().field_ids
    statuses = backend.statuses
    layout = backend.layout
    stamp = datetime.now().strftime("%H%M%S")
    me = backend.current_user()
    assert me, "the scenario needs credentials that name an account"

    # 1. new, with a request, a priority and a tag; list by the tag finds it.
    slug = r.work("new", f"Scenario {stamp}", "--priority", "high", "--tag", "ui",
                  stdin="Please do this.\n\nIt matters.")
    folder = slug.split("/", 1)[1]
    key = folder_key(folder)
    result.keys["item"] = key
    fields = r.fields(key)
    assert fields["summary"] == f"Scenario {stamp}"
    assert fields["priority"]["name"] == backend.jira.priorities["high"]
    assert "ui" in fields["labels"]
    assert (fields[ids["project"]], fields[ids["item"]]) == (backend.project, slug)
    assert fields["status"]["name"] == statuses[start_stage()]
    assert document_text(fields["description"]) == "Please do this.\n\nIt matters."
    started = time.monotonic()
    while slug not in r.work("list", "--tag", "ui").split():
        assert time.monotonic() - started < LAG_LIMIT, f"{slug} never appeared in list"
        time.sleep(1)
    result.lag = time.monotonic() - started
    say(f"step 1: {key} appeared in a search after {result.lag:.1f}s")

    # 2. advance through every enabled stage to qa, writing what each leaves:
    # a document at spec and plan, an implementation round before review, and
    # an accepted review judging it before qa.
    item = Slug.parse(slug, backend.project)
    implement_round = 0
    for stage in flow_order(backend.enabled)[2:]:
        if stage == "review":
            implement_round += 1
            r.write(layout.stage_dir(item, "implement") / f"round-{implement_round}.md",
                    "Implemented.\n")
        if stage == "qa":
            r.write(layout.stage_dir(item, "review") / f"round-{implement_round}.md",
                    f"---\nverdict: accepted\njudges: {implement_round}\n---\n")
        assert r.work("advance", slug) == stage
        assert r.status(key) == statuses[stage]
        if table_stage(stage).artifact == DOCUMENT:
            r.write(layout.document(item, stage), f"The {stage}.\n")
    say(f"step 2: {key} advanced to qa")

    # 3. a qa rejection back to implement, with a reason.
    r.work("advance", slug, "--to", "implement", "--reason", "Fails on narrow screens")
    assert r.status(key) == statuses["implement"]
    assert "Fails on narrow screens" in r.newest_comment(key)

    # 4. a qa acceptance.
    implement_round += 1
    r.write(layout.stage_dir(item, "implement") / f"round-{implement_round}.md",
            "Fixed.\n")
    r.work("advance", slug)
    r.write(layout.stage_dir(item, "review") / f"round-{implement_round}.md",
            f"---\nverdict: accepted\njudges: {implement_round}\n---\n")
    r.work("advance", slug)
    assert r.status(key) == statuses["qa"]
    r.work("advance", slug, "--to", "completed", "--reason", "QA passed")
    assert r.status(key) == statuses["completed"]
    assert "QA passed" in r.newest_comment(key)
    say(f"step 4: {key} accepted at qa")

    # 5. reopening, and a discard.
    r.work("advance", slug, "--to", "implement", "--force", "--reason", "Reopened")
    assert r.status(key) == statuses["implement"]
    r.work("discard", slug, "--reason", "Superseded")
    assert r.status(key) == statuses["discarded"]
    assert "Superseded" in r.newest_comment(key)

    # 6. edit each property, with a blocker added and removed.
    other = r.work("new", f"Scenario edits {stamp}")
    other_key = folder_key(other.split("/", 1)[1])
    result.keys["edited"] = other_key
    r.work("edit", other, "--title", f"Scenario edited {stamp}", "--priority", "low",
           "--effort", "high", "--complexity", "medium", "--tag", "api",
           "--assignee", me, "--blocked-by", slug)
    fields = r.fields(other_key)
    assert fields["summary"] == f"Scenario edited {stamp}"
    assert fields["priority"]["name"] == backend.jira.priorities["low"]
    assert scale_name(fields[ids["effort"]]) == "high"
    assert scale_name(fields[ids["complexity"]]) == "medium"
    assert "api" in fields["labels"] and fields["assignee"]["accountId"] == me
    assert blocker_keys(fields["issuelinks"]) == (key,)
    assert blocker_keys(r.fields(key)["issuelinks"]) == ()
    say(f"step 6: the link as Jira reports it on {other_key}: "
        f"{fields['issuelinks']}; on {key}: {r.fields(key)['issuelinks']}")
    r.work("edit", other, "--untag", "api", "--unblocked-by", slug)
    fields = r.fields(other_key)
    assert "api" not in fields["labels"] and blocker_keys(fields["issuelinks"]) == ()

    # 7. rename.
    renamed = r.work("rename", other, "renamed-by-scenario")
    assert renamed == f"{backend.project}/{other_key}-renamed-by-scenario"
    assert r.fields(other_key)[ids["item"]] == renamed
    assert (backend.work_path / renamed.split("/", 1)[1]).is_dir()

    # 8. a child under an epic, and a refused child under a sub-task.
    meta = backend.metadata()
    epic_type = next(t for t in meta.issue_types if t.level == 1)
    epic_key = backend.client.create_issue({
        "project": {"key": backend.jira.project}, "issuetype": {"id": epic_type.id},
        "summary": f"Scenario epic {stamp}"})["key"]
    epic = r.work("tickets", "adopt", epic_key)
    child = r.work("new", f"Scenario child {stamp}", "--parent", epic)
    child_key = folder_key(child.split("/", 1)[1])
    fields = r.fields(child_key)
    assert fields["issuetype"]["name"] == backend.jira.issue_type
    assert fields["parent"]["key"] == epic_key
    sub = r.work("new", f"Scenario sub-task {stamp}", "--parent", child)
    sub_key = folder_key(sub.split("/", 1)[1])
    assert r.fields(sub_key)["issuetype"]["subtask"] is True
    r.work("new", f"Scenario too deep {stamp}", "--parent", sub, expect=3)
    result.keys.update(epic=epic_key, child=child_key, sub=sub_key)

    # 9. tickets adopt of a ticket written without TCW fields.
    plain_key = backend.client.create_issue({
        "project": {"key": backend.jira.project},
        "issuetype": {"id": meta.issue_type.id},
        "summary": f"Scenario plain ticket {stamp}"})["key"]
    adopted = r.work("tickets", "adopt", plain_key)
    fields = r.fields(plain_key)
    assert (fields[ids["project"]], fields[ids["item"]]) == (backend.project, adopted)
    assert fields["status"]["name"] == statuses[start_stage()]
    result.keys["adopted"] = plain_key

    # 10. validate --remote, for the record.
    result.validate = r.tcw("validate", "--remote")
    say(f"step 10: validate --remote exited {result.validate[0]}")
    return result

