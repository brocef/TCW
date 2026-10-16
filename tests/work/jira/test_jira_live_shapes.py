"""Record, from the real `TCWTEST` project, the three answers the Jira backend
reads but had never seen from a real site (TCW pre-freeze clean-up, J2, Design
18): a second page of search results, a transition offered from one status
only, and a transition screen that lists a field.

It runs by hand, once, and writes to Jira: it creates up to 101 tickets named
`J2 paging probe NNN` and moves the last of them to `Won't Do`. So besides the
live scenario's variables it needs `TCW_JIRA_J2_PROBE=1` and
`TCW_JIRA_CAPTURE` naming the folder the recordings go to; `TCW_JIRA_LIVE=1`
alone runs the scenario and never this. Only the four files in `NAMED` are
copied from that folder into `recorded/`, by hand.
"""

import json
import os
import re
import time
from pathlib import Path

import pytest

from tcw.work.jira import client as jira
from tcw.work.jira.mapping import read_fields
from tcw.work.open import open_backend
from tests.work.jira.capture import Recorder
from tests.work.jira.test_jira_scenario import LIVE
from tests.work.projects import make_project

PROJECT = LIVE["jira"]["project"]
JQL = f'project = {PROJECT} AND summary ~ "\\"J2 paging probe\\""'
COUNT = 101
SUMMARY = re.compile(r"J2 paging probe (\d{3})")
#: Status ids on TCWTEST (spec Design 18), and the global move into Won't Do.
WONT_DO, TO_DO, INTO_WONT_DO = "10041", "10012", "91"
REOPEN = "J2 probe: reopen"
SEARCH_LAG = 120        # seconds a search may take to find every probe
#: The files this test exists to write, each apart from its endpoint's shared one.
NAMED = ("post-search-jql-200-first-page.json", "post-search-jql-200-next-page.json",
         "post-workflows-200-directed.json",
         "get-issue-key-transitions-200-screen-fields.json")


def _summary(number: int) -> str:
    return f"J2 paging probe {number:03d}"


@pytest.mark.skipif(os.environ.get("TCW_JIRA_LIVE") != "1"
                    or not os.environ.get("TCW_JIRA_EMAIL")
                    or not os.environ.get("TCW_JIRA_API_KEY")
                    or os.environ.get("TCW_JIRA_J2_PROBE") != "1"
                    or not os.environ.get("TCW_JIRA_CAPTURE"),
                    reason="writes to TCWTEST, so it runs by hand: TCW_JIRA_LIVE=1, the "
                           "credential variables, TCW_JIRA_J2_PROBE=1 and "
                           "TCW_JIRA_CAPTURE")
def test_record_the_three_unseen_shapes(tmp_path, monkeypatch):
    capture = Path(os.environ["TCW_JIRA_CAPTURE"]).resolve()
    capture.mkdir(parents=True, exist_ok=True)
    recorder = Recorder(capture, LIVE["jira"]["site"], PROJECT).install(monkeypatch)
    root = make_project(tmp_path, "tcw-test-live", config=LIVE)
    backend = open_backend(root)
    client, meta = backend.client, backend.metadata()
    ids, kind = meta.field_ids, meta.issue_type

    # 1. Create only what is missing: the numbers neither `j2-keys.json` nor a
    # search knows, so a re-run never makes more than COUNT tickets.
    keys_file = capture / "j2-keys.json"
    keys: dict[str, str] = json.loads(keys_file.read_text()) if keys_file.exists() else {}
    for issue in client.search(JQL, ["summary"]):
        found = SUMMARY.fullmatch(str(issue["fields"].get("summary", "")))
        if found:
            keys.setdefault(found.group(1), issue["key"])
    print(f"step 1: {len(keys)} probe tickets already exist")
    # The clean-up runs whatever happens from here on, a failed create included.
    try:
        for number in range(1, COUNT + 1):
            if f"{number:03d}" in keys:
                continue
            created = client.create_issue({"project": {"key": PROJECT},
                                           "issuetype": {"id": kind.id},
                                           "summary": _summary(number)})
            keys[f"{number:03d}"] = created["key"]
            keys_file.write_text(json.dumps(keys, indent=2, sort_keys=True) + "\n")
        wanted = set(keys.values())
        print(f"step 1: {len(wanted)} probe tickets in all")
        assert len(keys) == COUNT == len(wanted)

        # 2. The pages as Jira sends them, walked here rather than by
        # `JiraClient.search`, so a mistake in its walk cannot change them.
        started = time.monotonic()
        while not wanted <= {i["key"] for i in client.search(JQL, ["summary"])}:
            assert time.monotonic() - started < SEARCH_LAG, "search never found every probe"
            time.sleep(2)
        print(f"step 2: search found every probe after {time.monotonic() - started:.1f}s")
        fields = list(read_fields(ids))
        pages, token = [], None
        while True:
            body: dict = {"jql": JQL, "fields": fields, "maxResults": jira.PAGE}
            if token:
                body["nextPageToken"] = token
            label = {0: "first-page", 1: "next-page"}.get(len(pages))
            if label:
                with recorder.named(label):
                    answer = client._payload("POST", "/rest/api/3/search/jql", body)
            else:
                answer = client._payload("POST", "/rest/api/3/search/jql", body)
            pages.append(answer)
            print(f"step 2: page {len(pages)}: {len(answer.get('issues', []))} issues, "
                  f"isLast {answer.get('isLast', '(absent)')!r}, nextPageToken "
                  f"{type(answer.get('nextPageToken')).__name__}")
            token = answer.get("nextPageToken")
            if not token:
                break
        assert len(pages) >= 2, "every probe came back in one page"
        next_page = json.loads((capture / NAMED[1]).read_text())
        assert next_page["request"]["nextPageToken"] == pages[0]["nextPageToken"]
        walked = [i["key"] for page in pages for i in page.get("issues", [])]
        assert sorted(walked) == sorted(wanted), "the pages do not hold each probe once"
        print(f"step 2: {len(pages)} pages held all {len(walked)} probe keys, each once")

        # 3. The client's own page walk.
        searched = [i["key"] for i in client.search(JQL, fields)]
        assert sorted(searched) == sorted(wanted), \
            f"JiraClient.search returned {len(searched)} keys, {len(set(searched))} distinct"
        print(f"step 3: JiraClient.search returned all {len(searched)} probe keys, each once")

        # 4. The workflow, with a transition offered from Won't Do only. A status
        # reference is not a status id, so both ends go through `statuses`.
        with recorder.named("directed"):
            definition = client.workflows(meta.project_id, kind.id)
        status_id = {s.get("statusReference"): str(s.get("id"))
                     for s in definition["statuses"]}
        moves = [t for w in definition["workflows"] for t in w.get("transitions", [])]
        directed = [t for t in moves
                    if status_id.get(t.get("toStatusReference")) == TO_DO
                    and [status_id.get(link.get("fromStatusReference"))
                         for link in t.get("links") or []] == [WONT_DO]]
        assert directed, "no transition from Won't Do only to To Do"
        print(f"step 4: {[{k: t.get(k) for k in ('id', 'name', 'type', 'links')} for t in directed]}; "
              f"other types {sorted({str(t.get('type')) for t in moves})}, global links "
              f"{sorted({json.dumps(t.get('links')) for t in moves if t.get('type') == 'GLOBAL'})}")

        # 5. The restricted transition's screen, offered at Won't Do.
        last = keys[f"{COUNT:03d}"]
        status = client.issue(last, ["status"])["fields"]["status"]["name"]
        if status != "Won't Do":
            client.apply_transition(last, INTO_WONT_DO)
        print(f"step 5: {last} was at {status!r}"
              + ("" if status == "Won't Do" else ", moved to 'Won't Do'"))
        with recorder.named("screen-fields"):
            offered = client.transitions(last)
        reopen = [t for t in offered if t.name == REOPEN]
        assert reopen and "labels" in reopen[0].fields, \
            f"{REOPEN!r} with labels not offered on {last}: {offered}"
        print(f"step 5: {reopen[0]}")
        missing = [name for name in NAMED if not (capture / name).exists()]
        assert not missing, f"not recorded: {missing}"
    finally:
        _clean_up(client, keys, keys_file)


def _clean_up(client, keys: dict[str, str], keys_file: Path) -> None:
    """Delete the probes if the account may, checking each ticket just before;
    otherwise leave them, keep `j2-keys.json`, and print what remains."""
    try:
        permissions = client._json(
            "GET", f"/rest/api/3/mypermissions?projectKey={PROJECT}"
                   f"&permissions=DELETE_ISSUES")
    except jira.TrackerError:
        permissions = {}
    may_delete = (permissions.get("permissions", {}).get("DELETE_ISSUES", {})
                  .get("havePermission") is True)
    remaining = dict(keys)
    if may_delete:
        for number, key in sorted(keys.items()):
            fields = client.issue(key, ["summary", "project"])["fields"]
            if (fields.get("project") or {}).get("key") != PROJECT \
                    or SUMMARY.fullmatch(str(fields.get("summary", ""))) is None:
                continue
            try:
                client._payload("DELETE", f"/rest/api/3/issue/{key}")
            except jira.TrackerPermissionError:
                break
            del remaining[number]
        keys_file.write_text(json.dumps(remaining, indent=2, sort_keys=True) + "\n")
    else:
        print("clean-up: the account may not delete tickets in "
              f"{PROJECT}, so none was deleted")
    if remaining:
        print(f"clean-up: {len(remaining)} probe tickets remain, kept in {keys_file}: "
              f"{' '.join(remaining[n] for n in sorted(remaining))}")
        print(f"clean-up: they are found by: {JQL}")
