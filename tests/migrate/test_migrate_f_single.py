"""F-single end to end (TCW-116 Design 2.2-2.8 on one project; plan Step 11;
criteria 4-7, 9's interim form, 10, 11, 14, 16, 17, 49, 51, 60, and 8 for
the blockers part 1 gives).

Every run is against the fake Jira at F-single's site; nothing here can
reach a real one.
"""

from __future__ import annotations

import errno
import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.migrate import execute, progress, report
from tcw.project_files import version_line
from tests.migrate import fixtures
from tests.migrate.fixtures import build_f_single, seed_tickets, snapshot
from tests.move_stops import Counter, Fixture, _install, every_stop
from tests.objectcli import tcw  # noqa: F401  (a fixture)
from tests.processes import git_command, recorded_processes  # noqa: F401
from tests.work.jira.fake import FIELDS, FakeJira

ITEM = FIELDS["TCW Item"]
GOLDEN = Path(__file__).parent / "golden" / "f-single.json"
T, C, W = "docs/taxonomy", "docs/capabilities", "docs/work"


def new_fake(monkeypatch) -> FakeJira:
    monkeypatch.setenv(fixtures.EMAIL_VARIABLE, "dev@example.invalid")
    monkeypatch.setenv(fixtures.TOKEN_VARIABLE, "token")
    fake = FakeJira(site=fixtures.SITE)
    fake.install(monkeypatch)
    seed_tickets(fake)
    return fake


@pytest.fixture
def fake(monkeypatch):
    return new_fake(monkeypatch)


def tree(root: Path) -> dict[str, bytes | str]:
    """Every path below `root` relative to it, `.git/` left out: a file's
    bytes, a folder as `<folder>`."""
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if ".git" in rel.parts:
            continue
        out[rel.as_posix()] = path.read_bytes() if path.is_file() else "<folder>"
    return out


def lines(done) -> list[str]:
    return done.err.splitlines()


def uninterrupted(tcw, tmp_path, monkeypatch, *, backend: str = "jira") -> dict:
    """The tree a clean plain run leaves F-single in."""
    root = build_f_single(tmp_path / "clean", backend=backend)
    with monkeypatch.context() as patch:
        new_fake(patch)
        assert tcw(["migrate"], root).code == 0
    return tree(root)


# ── criteria 5, 6, 7: the dry run ────────────────────────────────────────────

def test_the_dry_run_reads_and_changes_nothing(tcw, fake, tmp_path):
    root = build_f_single(tmp_path / "app")
    fake.page_size = 2
    before = snapshot(root)
    done = tcw(["migrate", "--dry-run"], root)
    assert done.code == 0, done.err
    assert snapshot(root) == before
    searches = [b for m, p, b in fake.log if p.endswith("/search/jql")]
    assert len(searches) == 4                       # seven tickets with an item, two a page
    assert len([p for m, p, _ in fake.log if p.endswith("/editmeta")]) == 1
    assert not [m for m, p, _ in fake.log if m in ("PUT", "DELETE")]
    assert not [p for m, p, _ in fake.log if m == "POST" and not p.endswith("/search/jql")]
    reads = {p.split("?")[0] for m, p, _ in fake.log if m == "GET"}
    assert reads == {"/rest/api/3/project/APP", "/rest/api/3/issue/createmeta/APP/issuetypes/10002",
                     "/rest/api/3/issue/APP-1/editmeta"}


def test_the_dry_run_names_what_the_real_run_changes(tcw, fake, tmp_path):
    root = build_f_single(tmp_path / "app")
    dry = tcw(["migrate", "--dry-run"], root)
    said = set()
    for line in lines(dry):
        if line.startswith("would move "):
            old, new = line[len("would move "):].split(": ")[0].split(" -> ")
            said |= {(old, "move"), (new, "move")}
        elif line.startswith(("would write ", "would delete ")):
            action, path = line.split(" ")[1], line.split(" ")[2].rstrip(":")
            said.add((path, action))
    keys = {line.split(" ")[2].rstrip(":") for line in lines(dry)
            if line.startswith("would edit ")}
    before = tree(root)
    done = tcw(["migrate"], root)
    assert done.code == 0, done.err
    after = tree(root)
    changed = set()
    for path in set(before) | set(after):
        if before.get(path) == after.get(path) or "<folder>" in (before.get(path),
                                                                  after.get(path)):
            continue
        if path in after and path in before:
            changed.add((path, "write"))
        elif path in after:
            changed.add((path, "write"))
        else:
            changed.add((path, "delete"))
    moved = {p for p, a in said if a == "move"}
    inside = {p for p in set(before) | set(after)
              if any(p == m or p.startswith(m + "/") for m in moved)}
    assert {(p, a) for p, a in said if a != "move"} == \
        {(p, a) for p, a in changed if p not in inside}
    assert moved <= inside
    assert keys == {"APP-1", "APP-2", "APP-3"} == \
        {p.rsplit("/", 1)[1] for m, p, _ in fake.log if m == "PUT"}


def test_every_line_names_its_conversion_number_or_values(tcw, fake, tmp_path):
    done = tcw(["migrate"], build_f_single(tmp_path / "app"))
    assert done.code == 0, done.err
    for line in lines(done):
        if line.startswith(("write ", "move ", "delete ")):
            assert line.rsplit(": ", 1)[1].startswith("C"), line
        elif line.startswith("edit "):
            assert " -> " in line and ": C17 TCW Item: " in line, line
        elif line.startswith("  ") and not line.startswith("    "):
            assert line[2] in "AD" and line[3].isdigit(), line


# ── criterion 10: the order of the writes ────────────────────────────────────

def test_the_writes_come_in_the_order_of_the_phases(tcw, fake, tmp_path, monkeypatch):
    root = build_f_single(tmp_path / "app")
    order: list[tuple[str, str]] = []

    def spy(name, real):
        def wrapper(*args):
            paths = [Path(a) for a in args[:2] if isinstance(a, Path)]
            order.append((name, paths[0].relative_to(root).as_posix()))
            return real(*args)
        return wrapper
    for name in ("_write", "_move", "_delete"):
        monkeypatch.setattr(execute, name, spy(name, getattr(execute, name)))
    real_answer = fake.answer

    def answer(client, method, path, body):
        if method == "PUT":
            order.append(("PUT", path.rsplit("/", 1)[1]))
        return real_answer(client, method, path, body)
    monkeypatch.setattr(fake, "answer", answer)
    assert tcw(["migrate"], root).code == 0
    paths = [p for _, p in order]
    assert paths[:3] == [".tcw/tcw-migration.yaml", ".tcw/.gitignore", progress.PROGRESS]
    moves = [i for i, (k, _) in enumerate(order) if k == "_move"]
    states = [i for i, (k, p) in enumerate(order) if k == "_write"
              and p.rsplit("/", 1)[-1].startswith("tcw-") and p.startswith("docs/")]
    assert max(moves) < min(states)
    assert len(states) == len({order[i][1] for i in states})
    shared = paths.index(".tcw/tcw-config.yaml")
    assert all(i < shared for i, (k, p) in enumerate(order) if p.startswith("docs/"))
    assert shared < paths.index("tcw-config.yaml") < paths.index("tcw-config.local.yaml") \
        < len(paths) - 1 - paths[::-1].index(progress.PROGRESS)
    puts = [i for i, (k, _) in enumerate(order) if k == "PUT"]
    assert puts and min(puts) > max(i for i, (k, _) in enumerate(order) if k != "PUT")


# ── criterion 11: a stop at every write is finished by running again ─────────

@pytest.mark.parametrize("backend", ["jira", "files"])
def test_a_stop_at_every_write_is_finished_by_running_again(tcw, tmp_path, monkeypatch,
                                                            backend):
    made = []

    def make() -> Fixture:
        root = build_f_single(tmp_path / f"run-{len(made)}", backend=backend)
        fake = new_fake(monkeypatch) if backend == "jira" else None
        made.append(root)
        return Fixture(root, fake)

    def command(fixture: Fixture):
        return tcw(["migrate"], fixture.root)
    total = every_stop(pytest.MonkeyPatch.context, make, command,
                       stopped_says=(report.RUN_AGAIN,))
    assert total > 40
    for root in made:
        assert not (root / progress.PROGRESS).exists()


# ── criterion 60: each kind of stop, finished from the progress record ───────

def _clean_writes(tcw, tmp_path, monkeypatch) -> list[tuple[str, tuple]]:
    root = build_f_single(tmp_path / "count")
    counter = Counter()
    with monkeypatch.context() as patch:
        fake = new_fake(patch)
        _install(patch, counter, fake)
        assert tcw(["migrate"], root).code == 0
    return [(kind, tuple(Path(t).relative_to(root).as_posix() if isinstance(t, Path)
                         and t.is_relative_to(root) else str(t) for t in targets))
            for kind, targets in counter.writes]


def _point(writes, name: str) -> int:
    """The number (from 1) of the write a stop at point `name` fails at."""
    def first(test):
        return next(i for i, w in enumerate(writes, 1) if test(*w))
    record = first(lambda k, t: t[0] == progress.PROGRESS)
    if name == "P2":
        return record
    if name == "P3":
        return record + 1 + (writes[record][0] == "os.mkdir")
    if name == "P6":
        return first(lambda k, t: k == "_atomic_write_all" and t[0].startswith("docs/"))
    if name == "P7":
        return first(lambda k, t: k == "Path.unlink" and t[0].endswith("meta.yaml"))
    if name == "P8":
        states = [i for i, (k, t) in enumerate(writes, 1) if k == "_atomic_write_all"
                  and t[0].endswith(("tcw-taxonomy.yaml", "tcw-capability.yaml"))]
        return states[3]
    if name == "P9":
        return first(lambda k, t: t[0] == ".tcw/tcw-config.yaml") + 1
    raise KeyError(name)


def _stop(tcw, root, monkeypatch, at: int, *argv):
    with monkeypatch.context() as patch:
        _install(patch, Counter(fail_at=at), None)
        return tcw(["migrate", *argv], root)


@pytest.mark.parametrize("point", ["P2", "P3", "P6", "P7", "P8", "P9"])
def test_each_stop_point_is_finished_from_the_record(tcw, fake, tmp_path, monkeypatch, point):
    expected = uninterrupted(tcw, tmp_path, monkeypatch)
    at = _point(_clean_writes(tcw, tmp_path, monkeypatch), point)
    root = build_f_single(tmp_path / "app")
    stopped = _stop(tcw, root, monkeypatch, at)
    assert stopped.code == 1, stopped.err
    assert report.RUN_AGAIN in lines(stopped) and report.DO_NOT_SAVE in lines(stopped)
    if point == "P2":
        assert not (root / progress.PROGRESS).exists()
    else:
        assert (root / progress.PROGRESS).is_file()
        assert "/tcw-migration-progress.yaml" in (root / ".tcw/.gitignore").read_text()
        monkeypatch.setattr("tcw.migrate.plan.make_plan",
                            lambda *a, **k: (_ for _ in ()).throw(AssertionError("planned")))
    fake.log.clear()
    again = tcw(["migrate"], root)
    assert again.code == 0, again.err
    assert tree(root) == expected


def test_a_meta_yaml_changed_after_p8_is_b17(tcw, fake, tmp_path, monkeypatch):
    at = _point(_clean_writes(tcw, tmp_path, monkeypatch), "P8")
    root = build_f_single(tmp_path / "app")
    assert _stop(tcw, root, monkeypatch, at).code == 1
    left = sorted(p for p in (root / C).rglob("meta.yaml") if "resources" not in p.parts)[-1]
    left.write_text(left.read_text() + "# changed by hand\n")
    before = snapshot(root, times=False)
    done = tcw(["migrate"], root)
    assert done.code == 3, done.err
    assert any(line.startswith("  B17 ") and left.parent.relative_to(root).as_posix() in line
               for line in lines(done)), done.err
    assert snapshot(root, times=False) == before


def test_a_meta_yaml_waiting_for_deletion_changed_after_p7_is_b17(tcw, fake, tmp_path,
                                                                    monkeypatch):
    writes = _clean_writes(tcw, tmp_path, monkeypatch)
    at = _point(writes, "P7")
    waiting = root_rel = writes[at - 1][1][0]
    root = build_f_single(tmp_path / "app")
    assert _stop(tcw, root, monkeypatch, at).code == 1
    (root / waiting).write_text((root / waiting).read_text() + "# changed by hand\n")
    done = tcw(["migrate"], root)
    assert done.code == 3, done.err
    assert f"  B17 {root_rel}" in done.err
    assert (root / waiting).read_text().endswith("# changed by hand\n")


def test_a_move_across_filesystems_is_refused_then_finished_by_hand(tcw, fake, tmp_path,
                                                                     monkeypatch):
    expected = uninterrupted(tcw, tmp_path, monkeypatch)
    root = build_f_single(tmp_path / "app")
    old, new = f"{W}/APP-1-a/design.md", f"{W}/APP-1-a/resources/design.md"
    real = os.rename

    def rename(a, b, *rest, **kwargs):
        if str(a).endswith(old):
            raise OSError(errno.EXDEV, "Invalid cross-device link")
        return real(a, b, *rest, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(os, "rename", rename)
        done = tcw(["migrate"], root)
    assert done.code == 1, done.err
    assert f"{old} and {new} are on different filesystems" in done.err
    assert (root / old).is_file() and not (root / new).exists()
    (root / new).parent.mkdir(parents=True, exist_ok=True)
    real(root / old, root / new)
    again = tcw(["migrate"], root)
    assert again.code == 0, again.err
    assert tree(root) == expected


# ── criteria 14, 16, 17 ──────────────────────────────────────────────────────

def test_a_second_run_changes_nothing(tcw, fake, tmp_path):
    root = build_f_single(tmp_path / "app")
    assert tcw(["migrate"], root).code == 0
    before = snapshot(root)
    done = tcw(["migrate"], root)
    assert (done.code, lines(done)) == (0, ["nothing to migrate"])
    assert snapshot(root) == before


def test_only_3x_files_with_4_0_copies_and_moved_places_are_gone(tcw, fake, tmp_path):
    root = build_f_single(tmp_path / "app")
    before = tree(root)
    done = tcw(["migrate"], root)
    assert done.code == 0, done.err
    after = tree(root)
    moved = [line.split(" ")[1] for line in lines(done) if line.startswith("move ")]
    for path in sorted(set(before) - set(after)):
        if any(path == m or path.startswith(m + "/") for m in moved):
            continue
        name = path.rsplit("/", 1)[-1]
        folder = path.rpartition("/")[0]
        if name == "meta.yaml":
            assert any(f"{folder}/tcw-{kind}.yaml" in after for kind in ("taxonomy",
                                                                         "capability"))
        elif name == "item.yaml":
            assert f"{folder}/tcw-work-item.yaml" in after
        else:
            assert path in ("tcw-config.yaml", "tcw-config.local.yaml"), path
            assert f".tcw/{path}" in after
    record = (root / ".tcw/tcw-migration.yaml").read_text()
    assert record.startswith(version_line())
    held = yaml.safe_load(record)
    assert all(cap in json.dumps(held) and path in json.dumps(held)
               for path, cap in fixtures.CAPABILITY_IDS.items())


# ── criterion 51: TCW 4 reads the result ─────────────────────────────────────

def test_tcw_4_reads_the_result(tcw, fake, tmp_path):
    root = build_f_single(tmp_path / "app")
    done = tcw(["migrate"], root)
    assert done.code == 0, done.err
    a12 = [line for line in lines(done) if line.startswith("  A12 ")]
    assert a12 == [f"  A12 {where}: {text}" for where, text in fixtures.F_SINGLE_A12]
    found = tcw(["validate"], root)
    reported = [line for line in lines(done) if line.startswith(("  A1 ", "  A12 "))]
    assert len(found.out.splitlines()) == len(reported)
    listed = tcw(["work", "list", "--json"], root)
    assert listed.code == 0, listed.err
    ids = {item.get("full-id") or item.get("id") for item in json.loads(listed.out)["items"]}
    assert {"app.work/APP-1-a", "app.work/APP-2-b"} <= ids
    golden = json.loads(GOLDEN.read_text())["commands"]
    for axis, key in (("taxonomy", "terms"), ("capabilities", "capabilities")):
        three = {entry["path"] for entry in json.loads(golden[f"{axis} list --json"]["stdout"])[key]}
        three.discard("cli/v/resources")       # TCW 4 reads it as cli/v's resources
        four = json.loads(tcw([axis, "list", "--scope", "up", "--json"], root).out)[key]
        assert {e["full-id"].split("/", 1)[1] for e in four} == three
        assert {e["owner"] for e in four} == {"app"}


# ── criterion 4: git ─────────────────────────────────────────────────────────

def test_git_is_only_read_and_a_dirty_tree_changes_nothing(tcw, fake, tmp_path,
                                                           recorded_processes):
    inside = build_f_single(tmp_path / "git")
    (inside / "README.md").write_text("changed, not saved\n")
    outside = build_f_single(tmp_path / "plain", git=False)
    (outside / "README.md").write_text("changed, not saved\n")
    built = len(recorded_processes)
    assert tcw(["migrate"], inside).code == 0
    seed_tickets(fake)
    assert tcw(["migrate"], outside).code == 0
    a, b = tree(inside), tree(outside)
    assert {k: v for k, v in a.items() if k != ".tcw/.gitignore"} == \
        {k: v for k, v in b.items() if k != ".tcw/.gitignore"}
    for argv in recorded_processes[built:]:
        command, options = git_command(argv)
        if command is None:
            continue
        assert command in ("rev-parse", "ls-files", "status", "check-ignore"), argv
        if command == "status":
            assert "--no-optional-locks" in options, argv


# ── criterion 49: a linked worktree ──────────────────────────────────────────

def test_a_linked_worktree_changes_only_itself(tcw, fake, tmp_path):
    main = build_f_single(tmp_path / "main")
    subprocess.run(["git", "-C", str(main), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(main), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qm", "f-single"], check=True)
    (main / "tcw-config.local.yaml").write_text("user:\n  name: Only here\n")
    linked = tmp_path / "linked"
    subprocess.run(["git", "-C", str(main), "worktree", "add", "-q", str(linked)], check=True)
    (linked / "tcw-config.local.yaml").unlink(missing_ok=True)
    before = tree(main)
    done = tcw(["migrate"], linked)
    assert done.code == 0, done.err
    assert tree(main) == before
    assert (linked / ".tcw/tcw-config.yaml").is_file()
    a7 = [line for line in lines(done) if line.startswith("  A7 ")]
    assert a7 == [f"  A7 {main.resolve() / 'tcw-config.local.yaml'}: a 3.x personal file in "
                  f"the main checkout, which this run does not convert; run 'tcw migrate' "
                  f"there"]


# ── criteria 8 (part 1) and 9's interim form: blockers ───────────────────────

def _app(tmp_path, files: dict[str, str]) -> Path:
    root = tmp_path / "app"
    fixtures.write_files(root, {"tcw-config.yaml": "id: app\n", **files})
    fixtures.git_init(root)
    return root


CAP = f"{C}/cli/x/meta.yaml"
BLOCKERS = {
    "B1": {"tcw-config.yaml": "id: app\nwork:\n  stages:\n    spec:\n      Bad_Key: 1\n"},
    "B2": {"tcw-config.yaml": "id: app\nconnected-projects: []\n"},
    "B3": {"tcw-config.yaml": "id: app\nwork:\n  stages:\n    spec:\n      status: 5\n"},
    "B5": {"tcw-config.yaml": "id: app\nprojects:\n  upstream:\n    core: ../core\n"
                              "capabilities:\n  extends:\n  - core\n",
           CAP: "id: cap-1a2b3c\nname: X\nStatus: Supported\noverrides: core/cap-000000\n"},
    "B6": {"tcw-config.yaml": "id: app\ncapabilities:\n  path: /nowhere/in/a/project\n"},
    "B7": {"tcw-config.yaml": "id: app\ntaxonomy:\n  path: docs/x\ncapabilities:\n"
                              "  path: docs/x/y\n"},
    "B8": {f"{C}/cli/Bad Name/meta.yaml": "name: Bad\nStatus: Supported\n"},
    "B9": {CAP: "id: cap-1a2b3c\nname: X\nStatus: Supported\noverrides: cap-000000\n"},
    "B10": {f"{W}/2026-10-01-a/item.yaml": "title: A\nstage: inbox\n",
            f"{W}/2026-10-01-a/capabilities.yaml": "new:\n- cli/x\n"},
    "B11": {"tcw-config.yaml": "id: app\n", ".tcw/tcw-config.yaml": version_line() + "id: other\n"},
    "B14": {CAP: "name: [unclosed\n"},
    "B15": {"tcw-config.yaml": "work:\n  backend: filesystem\n"},
}


@pytest.mark.parametrize("code", sorted(BLOCKERS, key=lambda c: int(c[1:])))
def test_each_part_1_blocker_refuses_dry_and_real(tcw, tmp_path, code):
    root = _app(tmp_path, BLOCKERS[code])
    before = snapshot(root, times=False)
    for argv in (["migrate", "--dry-run"], ["migrate"]):
        done = tcw(argv, root)
        assert done.code == 3, (code, done.err)
        assert any(line.startswith(f"  {code} ") for line in lines(done)), (code, done.err)
    assert snapshot(root, times=False) == before


def test_b16_refuses_dry_and_real(tcw, fake, tmp_path):
    root = build_f_single(tmp_path / "app")
    fake.off_edit_screen.add(("Task", ITEM))
    before = snapshot(root, times=False)
    for argv in (["migrate", "--dry-run"], ["migrate"]):
        done = tcw(argv, root)
        assert done.code == 3 and "  B16 APP-1: " in done.err
    assert snapshot(root, times=False) == before
    assert not [m for m, _, _ in fake.log if m == "PUT"]


@pytest.mark.parametrize("which", ["write", "delete"])
def test_b17_in_both_forms_refuses_dry_and_real(tcw, fake, tmp_path, monkeypatch, which):
    writes = _clean_writes(tcw, tmp_path, monkeypatch)
    at = _point(writes, "P7" if which == "delete" else "P8")
    root = build_f_single(tmp_path / "app")
    assert _stop(tcw, root, monkeypatch, at).code == 1
    if which == "delete":
        target = root / writes[at - 1][1][0]
    else:
        target = sorted(p for p in (root / C).rglob("meta.yaml")
                        if "resources" not in p.parts)[-1]
    target.write_text(target.read_text() + "# by hand\n")
    before = snapshot(root, times=False)
    for argv in (["migrate", "--dry-run"], ["migrate"]):
        done = tcw(argv, root)
        assert done.code == 3 and "  B17 " in done.err, (argv, done.err)
    assert snapshot(root, times=False) == before


def test_three_blockers_in_one_run(tcw, tmp_path):
    """Criterion 9: B1, B8 and a pointer that names nothing (B9)."""
    root = _app(tmp_path, {**BLOCKERS["B1"], **BLOCKERS["B8"], **BLOCKERS["B9"]})
    done = tcw(["migrate"], root)
    assert done.code == 3
    found = {line.split()[0] for line in lines(done) if line.startswith("  B")}
    assert {"B1", "B8", "B9"} <= found
