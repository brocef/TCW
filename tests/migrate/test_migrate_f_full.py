"""F-full end to end, and the families (TCW-116 criteria 5-17 and 51 on
F-full, 45, 48 as a whole, 61 on F-full; plan Step 24).

F-full is the app of F-single placed in a family: `ws` holding `app`, `sib`
and `kid`, `core` beside it, and `lib` known only by its repository, whose
3.x clone is below the test's cache folder (`tests/conftest.py`). Every run
is against the fake Jira at F-single's site; nothing here can reach a real
one.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tcw.migrate import progress, report
from tests.migrate import fixtures
from tests.migrate.fixtures import F_FULL_PROJECTS, build_f_full, lib_clone, seed_tickets
from tests.move_stops import Fixture, every_stop
from tests.objectcli import tcw  # noqa: F401  (a fixture)
from tests.work.jira.fake import FakeJira

GOLDEN = Path(__file__).parent / "golden" / "f-full.json"


def new_fake(monkeypatch):
    monkeypatch.setenv(fixtures.EMAIL_VARIABLE, "dev@example.invalid")
    monkeypatch.setenv(fixtures.TOKEN_VARIABLE, "token")
    fake = FakeJira(site=fixtures.SITE)
    fake.install(monkeypatch)
    seed_tickets(fake)
    return fake


@pytest.fixture
def fake(monkeypatch):
    return new_fake(monkeypatch)


def cache() -> Path:
    return Path(os.environ["XDG_CACHE_HOME"])


def family(base: Path) -> dict[str, Path]:
    """F-full below `base`, each project's folder by its ID."""
    build_f_full(base, cache_home=cache())
    out = {pid: base / rel for pid, rel in F_FULL_PROJECTS.items()}
    out["lib"] = lib_clone(cache())
    return out


def tree(*roots: Path) -> dict[str, bytes | str]:
    """Every path below each root, `.git/` left out: a file's bytes, a folder
    as `<folder>`; keyed by the root's position and the relative path."""
    out = {}
    for i, root in enumerate(roots):
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root)
            if ".git" in rel.parts:
                continue
            out[f"{i}:{rel.as_posix()}"] = path.read_bytes() if path.is_file() \
                else "<folder>"
    return out


def lines(done) -> list[str]:
    return done.err.splitlines()


def changes(done) -> list[str]:
    return [line.removeprefix("would ") for line in lines(done)
            if line.startswith(("would write ", "would move ", "would delete ",
                                 "would edit ", "write ", "move ", "delete ", "edit "))]


# ── criteria 5-7, 14 and 16 on F-full: the app's own run ────────────────────

def test_the_dry_run_changes_nothing_and_names_the_real_run_s_changes(tcw, fake, tmp_path):
    projects = family(tmp_path / "f")
    roots = (tmp_path / "f", cache())
    before = tree(*roots)
    dry = tcw(["migrate", "--dry-run"], projects["app"])
    assert dry.code == 0, dry.err
    assert tree(*roots) == before
    assert not [m for m, _, _ in fake.log if m == "PUT"]
    real = tcw(["migrate"], projects["app"])
    assert real.code == 0, real.err
    assert changes(dry) == changes(real)


def test_a_second_run_changes_nothing(tcw, fake, tmp_path):
    projects = family(tmp_path / "f")
    assert tcw(["migrate"], projects["app"]).code == 0
    before = tree(tmp_path / "f", cache())
    done = tcw(["migrate"], projects["app"])
    assert (done.code, lines(done)) == (0, ["nothing to migrate"])
    assert tree(tmp_path / "f", cache()) == before


def test_only_app_s_files_change(tcw, fake, tmp_path):
    """Design 1.4: the run writes the app's own files, its work store in the
    workspace included, and never another project's."""
    projects = family(tmp_path / "f")
    others = [projects[p] for p in ("core", "lib", "sib", "kid")]
    before = tree(*others)
    ws_files = {p for p in tree(projects["ws"]) if not p.startswith(("0:app/", "0:docs/app/",
                                                                     "0:sib/", "0:kid/"))}
    ws_before = {k: v for k, v in tree(projects["ws"]).items() if k in ws_files}
    done = tcw(["migrate"], projects["app"])
    assert done.code == 0, done.err
    assert tree(*others) == before
    assert {k: v for k, v in tree(projects["ws"]).items() if k in ws_files} == ws_before
    # app has no repository of its own: it and its work store are both in
    # ws's, so nothing is left in another one.
    assert not any(line.startswith("left in another repository") for line in lines(done))


def test_a_stop_at_every_write_is_finished_by_running_again(tcw, tmp_path, monkeypatch):
    made = []

    def make() -> Fixture:
        base = tmp_path / f"run-{len(made)}"
        projects = family(base)
        made.append(projects["app"])
        return Fixture(base, new_fake(monkeypatch))

    def command(fixture: Fixture):
        return tcw(["migrate"], fixture.root / F_FULL_PROJECTS["app"])
    total = every_stop(pytest.MonkeyPatch.context, make, command,
                       stopped_says=(report.RUN_AGAIN,))
    assert total > 50
    for root in made:
        assert not (root / progress.PROGRESS).exists()


# ── criterion 45: the family migrated in two orders ─────────────────────────

ORDERS = {"parents first": ("lib", "core", "ws", "sib", "kid", "app"),
          "children first": ("app", "kid", "sib", "ws", "core", "lib")}


def migrated_family(tcw, base: Path, order, said: dict | None = None) -> dict[str, Path]:
    projects = family(base)
    for pid in order:
        done = tcw(["migrate", "--no-jira"], projects[pid])
        assert done.code == 0, (pid, done.err)
        if said is not None:
            said[pid] = done
    return projects


def normalised(projects: dict[str, Path], base: Path) -> dict[str, dict]:
    out = {}
    for pid, root in projects.items():
        files = {}
        for key, value in tree(root).items():
            if isinstance(value, bytes):
                value = value.replace(str(base.resolve()).encode(), b"<base>") \
                             .replace(str(base).encode(), b"<base>")
            files[key] = value
        out[pid] = files
    return out


def test_two_orders_give_identical_files_in_every_project(tcw, tmp_path, monkeypatch):
    found = {}
    for name, order in ORDERS.items():
        base = tmp_path / name.replace(" ", "-")
        with monkeypatch.context() as patch:
            patch.setenv("XDG_CACHE_HOME", str(base / "cache"))
            projects = migrated_family(tcw, base / "f", order)
        found[name] = normalised(projects, base)
    first, second = found.values()
    for pid in first:
        assert first[pid] == second[pid], pid


def test_tcw_4_reads_the_migrated_family(tcw, tmp_path, monkeypatch):
    # `lib` is found through each project's personal manifest (M5), which
    # TCW reads only with personal files on.
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    said = {}
    projects = migrated_family(tcw, tmp_path / "f", ORDERS["parents first"], said)
    for pid, root in projects.items():
        # Each finding is one the run passed on (A1, A12): a project's own
        # problem, which TCW 3's validate gave too.
        found = tcw(["validate"], root)
        reported = [line for line in lines(said[pid]) if line.startswith(("  A1 ", "  A12 "))]
        assert len(found.out.splitlines()) == len(reported), (pid, found.out, reported)
        assert "holds no TCW object" not in found.out, pid
    golden = json.loads(GOLDEN.read_text())["projects"]["app"]
    for axis, key in (("taxonomy", "terms"), ("capabilities", "capabilities")):
        entries = json.loads(golden[f"{axis} list --json"]["stdout"])[key]
        three = {e["path"]: e for e in entries if e["origin"] == "local"}
        for e in entries:
            if e["origin"] == "local":
                continue
            path = e["path"].split("/", 1)[1]
            if path in three and three[path]["origin"] == "local":
                # The app's own object at a path a parent has: in TCW 4 it
                # overrides the parent's, as D2 said.
                assert any(line.startswith(f"  D2 docs/{axis}/{path}/") and
                           f"'{e['origin']}' also has {path}" in line
                           for line in lines(said["app"])), (axis, path)
                continue
            three[path] = e
        three.pop("cli/v/resources", None)        # TCW 4 reads it as cli/v's resources
        listed = tcw([axis, "list", "--scope", "up", "--json"], projects["app"])
        assert listed.code == 0, listed.err
        four = {e["full-id"].split("/", 1)[1]: e for e in json.loads(listed.out)[key]}
        for path, entry in three.items():
            assert path in four, (axis, path)
            assert four[path]["name"] == entry["name"], (axis, path)


# ── criterion 50: the second person (Design 2.11) ──────────────────────────

PERSONAL = (".tcw/tcw-config.local.yaml", ".tcw/tcw-manifest.local.yaml")


def second_person(app: Path) -> None:
    """The app as someone else's clone has it after the first person's
    migration was committed: their own 3.x personal file at the root, and
    no personal file of the first person's."""
    personal = (app / ".tcw/tcw-config.local.yaml").read_text()
    for rel in PERSONAL:
        (app / rel).unlink()
    (app / "tcw-config.local.yaml").write_text(personal.split("\n", 1)[1])


def tracked(root: Path) -> dict:
    return {k: v for k, v in tree(root).items()
            if not k.endswith(("tcw-config.local.yaml", "tcw-manifest.local.yaml"))}


@pytest.mark.parametrize("first", ["with Jira", "--no-jira"])
def test_a_second_person_s_run(tcw, fake, tmp_path, first):
    projects = family(tmp_path / "f")
    app = projects["app"]
    argv = ["migrate"] + (["--no-jira"] if first == "--no-jira" else [])
    assert tcw(argv, app).code == 0
    second_person(app)
    before = tracked(projects["ws"])
    fake.log.clear()
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert "move tcw-config.local.yaml" in done.err or \
        "write .tcw/tcw-config.local.yaml: C1" in done.err
    assert not (app / "tcw-config.local.yaml").exists()
    assert (app / ".tcw/tcw-config.local.yaml").is_file()
    personal = (app / ".tcw/tcw-manifest.local.yaml").read_text()
    assert str(lib_clone(cache())) in personal
    assert tracked(projects["ws"]) == before
    edited = [p for m, p, _ in fake.log if m == "PUT"]
    if first == "with Jira":
        assert edited == []
    else:
        assert sorted(p.split("?")[0].rsplit("/", 1)[1] for p in edited) == \
            ["APP-1", "APP-2", "APP-3"]
