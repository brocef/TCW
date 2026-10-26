"""The monorepo (UC-3; TCW-116 criterion 46; Design 2.10, 6.2; plan Step 24).

One repository holding a root, `mono`, and three packages: `api` keeps its
work in Jira with only the keys 3.x requires, `web` reads `api`'s
capabilities, and `jobs` has a term the root has too. Each package reads
the root's taxonomy through `extends`, except `jobs`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.migrate import fixtures
from tests.migrate.fixtures import build_monorepo
from tests.objectcli import tcw  # noqa: F401  (a fixture)
from tests.work.jira.fake import FakeJira

GOLDEN = Path(__file__).parent / "golden" / "monorepo.json"


@pytest.fixture
def mono(tmp_path, monkeypatch):
    """The monorepo, with the fake Jira at F-single's site serving `api`."""
    monkeypatch.setenv("APP_EMAIL", "dev@example.invalid")
    monkeypatch.setenv("APP_TOKEN", "token")
    fake = FakeJira(site=fixtures.SITE)
    fake.install(monkeypatch)
    fixtures.seed_tickets(fake)        # F-single's tickets, all of another project
    return build_monorepo(tmp_path / "m")


def migrate(tcw, root: Path):
    done = tcw(["migrate"], root)
    assert done.code == 0, done.err
    return done


def still_3x(done) -> list[str]:
    """The A8 lines' folders, in the order the summary gives them."""
    return [line.split(":", 1)[0].removeprefix("  A8 ")
            for line in done.err.splitlines() if line.startswith("  A8 ")]


STOPPED = ("check after the run stopped: a related project is still TCW 3.x; run "
           "'tcw validate' once it is migrated")


def test_a_package_migrated_before_its_root(tcw, mono):
    done = migrate(tcw, mono["api"])
    assert still_3x(done) == [str(mono["mono"]), str(mono["web"]), str(mono["jobs"])]
    # The check after the run stops at the 3.x root, before any of the
    # package's own findings, and the summary says so (TCW-118 fix 18).
    assert done.err.splitlines()[-1] == STOPPED
    assert f"migrate it with 'tcw -C {mono['mono']} migrate'" in done.err
    # TCW 4 refuses a related project still in 3.x form before it reads
    # anything it would inherit (TCW-106 Design 4.2), so the stop is exit 1
    # naming the root, not criterion 46's exit 7 naming `work.jira`.
    legacy = f"{mono['mono']}: is a TCW 3.x project"
    listed = tcw(["work", "list"], mono["api"])
    assert listed.code == 1, listed.err
    assert legacy in listed.err and "run 'tcw migrate' in it" in listed.err
    terms = tcw(["taxonomy", "list", "--scope", "up"], mono["api"])
    assert terms.code == 1, terms.err
    assert legacy in terms.err
    root = migrate(tcw, mono["mono"])
    assert still_3x(root) == [str(mono["web"]), str(mono["jobs"])]
    listed = tcw(["work", "list"], mono["api"])
    assert listed.code == 0, listed.err


def test_after_all_four_tcw_4_reads_each_and_lists_what_3_x_listed(tcw, mono):
    said = {pid: migrate(tcw, mono[pid]) for pid in ("api", "mono", "web", "jobs")}
    assert STOPPED not in said["jobs"].err.splitlines()      # the last: nothing is 3.x
    golden = json.loads(GOLDEN.read_text())["projects"]
    for pid, root in mono.items():
        found = tcw(["validate"], root)
        assert found.code == 0, (pid, found.out, found.err)
        assert found.out == "", (pid, found.out)
        if pid == "mono":
            continue
        three = json.loads(golden[pid]["taxonomy list --json"]["stdout"])["terms"]
        expected = {(e["origin"] if e["origin"] != "local" else pid,
                     e["path"].split("/", 1)[1] if e["origin"] != "local" else e["path"])
                    for e in three}
        lines = said[pid].err.splitlines()
        # D1: taxonomy now inherited from a project TCW 3 did not read it from.
        for line in lines:
            if line.startswith("  D1 ") and "now inherits taxonomy from" in line:
                for named in line.split("from ", 1)[1].split(", which")[0].split(", "):
                    owner = named.strip("'")
                    theirs = json.loads(golden[owner]["taxonomy list --json"]["stdout"])
                    expected |= {(owner, e["path"]) for e in theirs["terms"]
                                 if e["origin"] == "local"}
        # D2: the package's own term at a path the root has overrides it.
        overridden = {line.split(" also has ", 1)[1].split(";", 1)[0]
                      for line in lines if line.startswith("  D2 docs/taxonomy/")}
        if pid == "jobs":
            assert overridden == {"party"}
        expected = {(o, p) for o, p in expected if not (o != pid and p in overridden)}
        listed = tcw(["taxonomy", "list", "--scope", "up", "--json"], root)
        assert listed.code == 0, (pid, listed.err)
        four = {(e["owner"], e["full-id"].split("/", 1)[1])
                for e in json.loads(listed.out)["terms"]}
        assert four == expected, (pid, four ^ expected)
