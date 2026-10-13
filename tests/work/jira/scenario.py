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



# -- the live check's questions (Design 15.4), asked after the scenario ---------------


def probe(project_root: Path, result: Result, *, other_parent: str,
          say: Callable[[str], None] = print) -> dict[str, str]:
    """Ask the real site what only it can answer, printing the evidence for
    each question. `other_parent` is an epic in another Jira project. Returns
    the answers by question, for the implement round."""
    from tcw.work.jira import client as jira
    from tcw.work.jira.jql import field, keys_query, quote

    backend = open_backend(project_root)
    client, ids = backend.client, backend.metadata().field_ids
    project, kind = backend.jira.project, backend.metadata().issue_type
    stamp = datetime.now().strftime("%H%M%S")
    answers: dict[str, str] = {}

    def ask(question: str, answer: str) -> None:
        answers[question] = answer
        say(f"{question}: {answer}")

    def new_ticket(summary: str, **fields) -> str:
        return client.create_issue({"project": {"key": project},
                                    "issuetype": {"id": kind.id},
                                    "summary": summary, **fields})["key"]

    def wait_for(jql: str, wanted: set[str], limit: float = LAG_LIMIT) -> float | None:
        started = time.monotonic()
        while time.monotonic() - started < limit:
            if wanted <= {i["key"] for i in client.search(jql, ["summary"])}:
                return time.monotonic() - started
            time.sleep(1)
        return None

    # 1. Blocks direction: on the blocked ticket, which side holds the blocker.
    edited = result.keys["edited"]
    client.add_link("Blocks", result.keys["item"], edited)
    links = client.issue(edited, ["issuelinks"])["fields"]["issuelinks"]
    link = next(l for l in links if l["type"]["name"] == "Blocks")
    side = "inwardIssue" if "inwardIssue" in link else "outwardIssue"
    ask("blocks", f"add_link(Blocks, inward={result.keys['item']}, outward={edited}); "
                  f"on {edited} the blocker {link[side]['key']} is under {side}, "
                  f"type inward={link['type']['inward']!r}")
    client.delete_link(link["id"])

    # 2. a comment sent with a transition, with no screen and with a comment-only one.
    key = new_ticket(f"Probe comments {stamp}")
    offered = {t.to_status: t for t in client.transitions(key)}
    seen = []
    for status in ("In Review", "Planning"):
        chosen = offered[status] if status in offered else None
        if chosen is None:
            seen.append(f"{status}: not offered")
            continue
        before = len(client.comments(key, None))
        client.apply_transition(key, chosen.id, jira_document(f"probe {status}"))
        after = len(client.comments(key, None))
        seen.append(f"{status} (hasScreen={chosen.has_screen}, fields={chosen.fields}): "
                    f"accepted, comments {before}->{after}")
        offered = {t.to_status: t for t in client.transitions(key)}
    ask("comment on a transition", "; ".join(seen))

    # 3. a parent in another Jira project.
    try:
        child = new_ticket(f"Probe cross-project parent {stamp}",
                           parent={"key": other_parent})
    except jira.TrackerError as error:
        ask("cross-project parent", f"refused: {type(error).__name__}: {error}")
    else:
        parent = (client.issue(child, ["parent"])["fields"].get("parent") or {}).get("key")
        try:
            client.edit_issue(child, {"parent": None})
            undone = "parent removed again"
        except jira.TrackerError as error:
            undone = f"could not remove the parent: {error}"
        ask("cross-project parent", f"accepted: {child} created with parent {parent}; "
                                    f"{undone}")

    # 4. the workflow definition, and the shape of its INITIAL transition.
    meta = backend.metadata()
    try:
        definition = client.workflows(client.project(project)["id"], kind.id)
    except jira.TrackerError as error:
        ask("workflow definition", f"refused: {type(error).__name__}: {error}")
    else:
        moves = [t for w in definition["workflows"] for t in w.get("transitions", [])]
        initial = [{k: t.get(k) for k in ("type", "links", "toStatusReference", "name")}
                   for t in moves if t.get("type") == "INITIAL"]
        ask("workflow definition", f"read as an administrator; {len(moves)} transitions; "
                                   f"INITIAL: {initial}. A non-administrator was not "
                                   f"available to try")

    # 5. expand=transitions.fields for no screen and a comment-only screen: in (2).

    # 6. `~` on TCW Project with a hyphenated id.
    values = {"tcw-test-live": None, "tcw-test": None, "live": None}
    for value in values:
        values[value] = new_ticket(f"Probe word search {value} {stamp}",
                                   **{ids["project"]: value})
    jql = f"project = {quote(project)} AND {field(ids['project'])} ~ {quote('tcw-test-live')}"
    wait_for(jql, {values["tcw-test-live"]}, 30)
    found = {i["key"] for i in client.search(jql, ["summary"])}
    ask("~ on TCW Project", ", ".join(f"{v}: {'found' if k in found else 'not found'}"
                                      for v, k in values.items()))

    # 7. `key in` naming a key that does not exist; and an unknown status.
    for question, jql in (("key in with a missing key",
                           keys_query([result.keys["item"], f"{project}-999999"])),
                          ("an unknown status in JQL",
                           f"project = {quote(project)} AND status = "
                           f"{quote('No Such Status')}")):
        try:
            got = [i["key"] for i in client.search(jql, ["summary"])]
            ask(question, f"answered, with {got}")
        except jira.TrackerError as error:
            ask(question, f"refused: {type(error).__name__}: {error}")

    # 8. lag: a new ticket (step 1), and a ticket just given a TCW Item value.
    key = new_ticket(f"Probe item lag {stamp}")
    client.edit_issue(key, {ids["item"]: f"{backend.project}/{key}-probe"})
    lag = wait_for(f"key = {quote(key)} AND {field(ids['item'])} IS NOT EMPTY", {key})
    ask("search lag", f"a new ticket: {result.lag:.1f}s (step 1); a ticket just given "
                      f"a TCW Item: {'not within the limit' if lag is None else f'{lag:.1f}s'}")

    # 9. the offset on `created`, against the account's profile time zone.
    me = client.myself()
    created = client.issue(result.keys["item"], ["created"])["fields"]["created"]
    ask("created offset", f"created={created}; the account's time zone is "
                          f"{me.get('timeZone')}")

    # 10. translated status names.
    ask("translated status names", "not asked: no account with a non-English profile "
                                   "language is available (tcwtest-checklist.md step 7)")
    return answers


def jira_document(text: str) -> dict:
    from tcw.work.jira.mapping import text_document
    return text_document(text)
