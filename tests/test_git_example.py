"""The opt-in git example works (TCW-75 spec, acceptance criterion 5).

`docs/guide/examples/commit-item-after-move.sh` is the `post` hook a project
can copy to commit a work item's folder after TCW moves it. TCW itself never
changes git state; this script is the project's own. Each case runs it the
way the example binds it, `sh <script>`, with the three variables `advance`
sets, in repositories built under `tmp_path`. The configuration guide shows
the script byte for byte, and its configuration loads and keeps TCW's own
instructions after the pull instruction.
"""

import os
import re
import subprocess
from pathlib import Path

import yaml

from tcw.config import load_config

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "docs/guide/examples/commit-item-after-move.sh"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def _repository(path: Path) -> Path:
    """A repository with one commit and its own identity, so no setting of
    the machine running the tests decides the outcome."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    _git(path, "config", "user.name", "Test")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "commit.gpgsign", "false")
    (path / "README.md").write_text("start\n")
    (path / "docs/work/x").mkdir(parents=True)
    (path / "docs/work/x/item.yaml").write_text("title: x\n")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "start")
    return path


def _run(item: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "TCW_ITEM_PATH": str(item), "TCW_SLUG": "demo/x",
           "TCW_STAGE": "plan"}
    return subprocess.run(["sh", str(SCRIPT)], env=env, cwd=item.parent,
                          capture_output=True, text=True)


def _commits(repo: Path) -> int:
    return int(_git(repo, "rev-list", "--count", "HEAD"))


def _last_commit_paths(repo: Path) -> list[str]:
    return _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r",
                "HEAD").split()


def _status(repo: Path) -> list[str]:
    return _git(repo, "status", "--porcelain").splitlines()


def test_the_script_is_executable():
    assert os.access(SCRIPT, os.X_OK)


def test_a_change_in_the_item_folder_makes_one_commit_of_the_item_only(tmp_path):
    repo = _repository(tmp_path / "project")
    item = repo / "docs/work/x"
    (item / "plan").mkdir()
    (item / "plan/plan.md").write_text("the plan\n")
    (item / "item.yaml").write_text("title: x\nstage: plan\n")
    before = _commits(repo)
    result = _run(item)
    assert result.returncode == 0, result.stderr
    assert _commits(repo) == before + 1
    paths = _last_commit_paths(repo)
    assert paths and all(p.startswith("docs/work/x/") for p in paths), paths
    assert _git(repo, "log", "-1", "--format=%s").strip() == "Move demo/x to plan"
    assert _status(repo) == []


def test_other_changes_staged_or_not_are_left_as_they_were(tmp_path):
    repo = _repository(tmp_path / "project")
    item = repo / "docs/work/x"
    (item / "item.yaml").write_text("title: x\nstage: plan\n")
    (repo / "staged.txt").write_text("staged\n")
    _git(repo, "add", "staged.txt")
    (repo / "README.md").write_text("changed, not staged\n")
    result = _run(item)
    assert result.returncode == 0, result.stderr
    assert _last_commit_paths(repo) == ["docs/work/x/item.yaml"]
    status = _status(repo)
    assert "A  staged.txt" in status, status
    assert " M README.md" in status, status
    assert len(status) == 2, status


def test_no_change_makes_no_commit_and_succeeds(tmp_path):
    repo = _repository(tmp_path / "project")
    (repo / "README.md").write_text("changed elsewhere\n")
    before = _commits(repo)
    result = _run(repo / "docs/work/x")
    assert result.returncode == 0, result.stderr
    assert _commits(repo) == before
    assert _status(repo) == [" M README.md"]


def test_an_item_in_a_nested_repository_is_committed_there(tmp_path):
    outer = _repository(tmp_path / "planning")
    inner = _repository(outer / "store")
    (outer / ".gitignore").write_text("store/\n")
    _git(outer, "add", ".gitignore")
    _git(outer, "commit", "-q", "-m", "ignore the store")
    item = inner / "docs/work/x"
    (item / "item.yaml").write_text("title: x\nstage: plan\n")
    (outer / "README.md").write_text("changed in the outer repository\n")
    outer_before, inner_before = _commits(outer), _commits(inner)
    result = _run(item)
    assert result.returncode == 0, result.stderr
    assert _commits(inner) == inner_before + 1
    assert _last_commit_paths(inner) == ["docs/work/x/item.yaml"]
    assert _commits(outer) == outer_before
    assert _status(outer) == [" M README.md"]


# ── the guide shows the script and a configuration that works ────────────────

GUIDE = REPO / "docs/guide/configuration.md"
HEADING = ("## Example: keeping git in step with each stage change "
           "(something your project adds)")


def _example_section() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    _, found, rest = text.partition("\n" + HEADING + "\n")
    assert found, f"{GUIDE.name} has no heading {HEADING!r}"
    return re.split(r"^## ", rest, maxsplit=1, flags=re.M)[0]


def _first_block(language: str) -> str:
    """The first fenced block of `language` in the example, as its text."""
    m = re.search(rf"^```{language}\n(.*?)^```$", _example_section(), re.M | re.S)
    assert m, f"no ```{language} block under the example heading"
    return m.group(1)


def test_the_guide_shows_the_script_byte_for_byte():
    assert _first_block("sh") == SCRIPT.read_text(encoding="utf-8")


def _example_config(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", "1")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "tcw-config.yaml").write_text("id: x\n" + _first_block("yaml"),
                                              encoding="utf-8")
    return load_config(tmp_path)


def test_the_example_configuration_loads_with_no_problems(tmp_path, monkeypatch):
    config = _example_config(tmp_path, monkeypatch)
    assert [str(p) for p in config.problems] == []


def test_every_example_prompt_is_the_pull_text_then_tcws_own(tmp_path, monkeypatch):
    """`- inherit: true` keeps TCW's own instructions after the pull text; a
    writer who drops it fails here."""
    raw = yaml.safe_load(_first_block("yaml"))["work"]["stages"]
    work = _example_config(tmp_path, monkeypatch).work
    prompted = [stage for stage, block in raw.items() if "prompt" in block]
    assert prompted
    for stage in prompted:
        kinds = [b.kind for b in work.stage(stage).prompt]
        assert kinds == ["blob", "builtin"], (stage, kinds)
        assert "git -C" in work.stage(stage).prompt[0].value


def test_the_example_binds_no_pre_hook():
    raw = yaml.safe_load(_first_block("yaml"))["work"]["stages"]
    assert not [stage for stage, block in raw.items() if "pre" in block]
