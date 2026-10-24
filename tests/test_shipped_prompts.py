"""The stage prompts TCW ships, and the packaging that carries them (TCW-74
criteria 1-3).

Everything goes through `load_builtins()` rather than the source tree, so the
assertions hold in an installed tree as well as a checkout, and the wheel case
reads the built `.whl` itself, which is the only proof the files survive
packaging. Content is checked **after backend filtering**, for each backend,
because that is the text an agent is given.
"""

import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from tcw.store.base import PROCEDURE_IDS
from tcw.work.config import BACKENDS
from tcw.work.model import STAGES
from tcw.work.passages import filter_backend
from tcw.work.resolve import ResolveError, load_builtins

SHIPPED = {s.name for s in STAGES if s.prompt}
REPO = Path(__file__).resolve().parent.parent
PAIRS = [(sid, backend) for sid in sorted(SHIPPED) for backend in BACKENDS]
pairs = pytest.mark.parametrize("sid, backend", PAIRS, ids=lambda v: str(v))


PACKAGE = Path(__file__).resolve().parent.parent / "tcw"


def prompt(sid: str, backend: str) -> str:
    return filter_backend(load_builtins().stage_prompts[sid], backend)


# -- criterion 1: the set ---------------------------------------------------------

def test_the_prompts_are_exactly_the_stages_that_take_one():
    """Derived from the table's `prompt` column, never a hand-written list."""
    assert set(load_builtins().stage_prompts) == SHIPPED
    assert SHIPPED == {"inbox", "request", "spec", "plan", "implement", "review",
                       "qa", "postmortem"}


def test_verify_is_gone():
    assert not (REPO / "tcw" / "work" / "prompts" / "verify.md").exists()


def _with_prompts_folder(monkeypatch, tmp_path, change):
    """`load_builtins` reading a copy of the prompts folder, changed by
    `change(folder)`."""
    import tcw.work.resolve as resolve
    real = resolve.files("tcw.work")
    copy = tmp_path / "work"
    shutil.copytree(Path(str(real / "prompts")), copy / "prompts")
    shutil.copytree(Path(str(real / "procedures")), copy / "procedures")
    change(copy / "prompts")
    monkeypatch.setattr(resolve, "files", lambda _pkg: copy)
    resolve.load_builtins.cache_clear()


@pytest.mark.parametrize("sid", sorted(SHIPPED))
def test_a_missing_prompt_file_fails_loading_naming_it(sid, monkeypatch, tmp_path):
    import tcw.work.resolve as resolve
    _with_prompts_folder(monkeypatch, tmp_path,
                         lambda folder: (folder / f"{sid}.md").unlink())
    try:
        with pytest.raises(ResolveError) as error:
            resolve.load_builtins()
    finally:
        monkeypatch.undo()
        resolve.load_builtins.cache_clear()
    assert f"tcw/work/prompts/{sid}.md" in str(error.value)


@pytest.mark.parametrize("extra", ["completed.md", "verify.md"])
def test_a_prompt_file_for_no_such_stage_fails_loading(extra, monkeypatch, tmp_path):
    import tcw.work.resolve as resolve
    _with_prompts_folder(monkeypatch, tmp_path,
                         lambda folder: (folder / extra).write_text("text\n"))
    try:
        with pytest.raises(ResolveError) as error:
            resolve.load_builtins()
    finally:
        monkeypatch.undo()
        resolve.load_builtins.cache_clear()
    assert f"tcw/work/prompts/{extra}" in str(error.value)


def _pristine_checkout(tmp_path: Path) -> Path:
    """The tracked tree, copied out, with no build artifacts in it.

    Building from `REPO` itself reads whatever `build/` a developer happens to
    have, and `setuptools` reuses that staging directory, so a file deleted
    from the source long ago is still copied into the wheel. The listing
    rather than an archive of the last saved state: uncommitted edits, and new
    files not ignored, are part of what a packaging test should check.
    """
    names = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--cached", "--others",
         "--exclude-standard", "-z"],
        check=True, capture_output=True, text=True).stdout.split("\0")
    source = tmp_path / "source"
    for name in filter(None, names):
        if not (REPO / name).exists():
            continue                     # deleted in the working tree
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / name, target)
    return source


def test_the_wheel_carries_exactly_the_prompts_and_procedures(tmp_path):
    """Package data, not source-tree files. Reading the zip rather than
    installing it also proves the content survives a zipimport-style install."""
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps",
         "--no-build-isolation", "-w", str(tmp_path),
         str(_pristine_checkout(tmp_path))],
        check=True, capture_output=True)
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1, wheels
    with zipfile.ZipFile(wheels[0]) as z:
        members = {n for n in z.namelist()
                   if n.startswith("tcw/work/prompts/") and n.endswith(".md")}
        assert {Path(n).stem for n in members} == SHIPPED
        for name in members:
            assert z.read(name).decode("utf-8").strip()
        procedures = {Path(n).stem for n in z.namelist()
                      if n.startswith("tcw/work/procedures/") and n.endswith(".md")}
        assert procedures == set(PROCEDURE_IDS)


# -- criterion 2: the ceiling -----------------------------------------------------

@pairs
def test_each_prompt_is_at_most_60_lines_for_each_backend(sid, backend):
    """Text an agent reads at every stage; a ceiling that is only a convention
    erodes. Raised from 50 by TCW-74 for the request template and the backend
    passages."""
    assert len(prompt(sid, backend).splitlines()) <= 60


@pairs
def test_each_prompt_keeps_its_shape(sid, backend):
    text = prompt(sid, backend)
    for part in ("**Purpose.**", "**Inputs.**", "**Produce**", "## Steps",
                 "## Exit badly"):
        assert part in text, f"{sid} ({backend}) has no {part}"


# -- criterion 3: content ---------------------------------------------------------

TWO_X = ("intake.md", "initial-request.md", "outcome.md", "refined-outcome.md",
         "rework.md", "post-mortem.md", "state.yaml")


@pairs
def test_no_prompt_names_a_2x_item_file(sid, backend):
    text = prompt(sid, backend)
    assert [name for name in TWO_X if name in text] == []


EXTERNAL_IN_JIRA = {"request", "qa"}


@pairs
def test_every_prompt_but_inbox_names_its_handoff(sid, backend):
    text = prompt(sid, backend)
    if sid == "inbox":
        assert "handoff" not in text.lower()
    elif backend == "jira" and sid in EXTERNAL_IN_JIRA:
        assert "Handoff" in text and "tcw work comment" in text
        assert "--handoff" not in text
    else:
        assert "--handoff" in text


@pytest.mark.parametrize("backend", BACKENDS)
def test_spec_declares_and_posts_the_qa_plan(backend):
    text = prompt("spec", backend)
    for words in ("QA plan", "tcw work comment", "capabilities.yaml"):
        assert words in text
    exit_badly = text.split("## Exit badly", 1)[1]
    assert "tcw work comment" in exit_badly


@pytest.mark.parametrize("backend", BACKENDS)
def test_plan_covers_a_disabled_spec(backend):
    text = prompt("plan", backend)
    assert "capabilities.yaml" in text and "QA plan" in text


@pytest.mark.parametrize("backend", BACKENDS)
def test_implement_writes_one_round_naming_five_things(backend):
    text = prompt("implement", backend)
    assert "tcw work path <slug> implement --next" in text
    for words in ("what\nwas done", "the test result", "what the\nplan or spec got wrong",
                  "which records changed", "which rejections it answers"):
        assert " ".join(words.split()) in " ".join(text.split()), words
    assert "**Write the round once, at the end**" in text
    assert "`judges`" in text


def test_only_jira_implement_reads_the_qa_move_comment():
    move = "recording a move from qa to implement"
    assert move in " ".join(prompt("implement", "jira").split())
    assert move not in " ".join(prompt("implement", "filesystem").split())


@pytest.mark.parametrize("sid", ["review", "qa"])
def test_review_and_filesystem_qa_carry_the_front_matter(sid):
    text = prompt(sid, "filesystem")
    assert "verdict:" in text and "judges:" in text


@pytest.mark.parametrize("backend", BACKENDS)
def test_review_writes_the_next_round(backend):
    assert "tcw work path <slug> review --next" in prompt("review", backend)


@pytest.mark.parametrize("backend", BACKENDS)
def test_request_carries_the_template(backend):
    text = prompt("request", backend)
    for section in ("What and why", "Product changes", "Out of scope",
                    "Constraints", "References"):
        assert f"**{section}**" in text


def test_jira_request_comments_instead_of_writing():
    text = prompt("request", "jira")
    assert "tcw work comment" in text
    assert "tcw work path <slug> request" not in text


def test_jira_inbox_triages_tickets():
    text = prompt("inbox", "jira")
    for words in ("tcw work tickets adopt", "tcw work tickets list --json",
                  "description", "tcw work comment", "close"):
        assert words in text, words
    assert "--stage inbox" not in text and "tcw work discard" not in text


def test_filesystem_inbox_accepts_by_advancing():
    text = prompt("inbox", "filesystem")
    assert "tcw work advance" in text and "tickets" not in text


def _paragraph_with(text: str, words: str) -> str:
    """The blank-line paragraph or list item holding `words`."""
    flat = text.replace("\n   ", " ").replace("\n  ", " ")
    blocks = re.split(r"\n\s*\n|\n(?=\d+\. |- )", flat)
    found = [b for b in blocks if words in " ".join(b.split())]
    assert len(found) == 1, (words, found)
    return " ".join(found[0].split())


def test_filesystem_qa_writes_a_round_and_can_hand_the_verdict_to_a_person():
    text = prompt("qa", "filesystem")
    assert "tcw work path <slug> qa --next" in text and "QA plan" in text
    paragraph = _paragraph_with(text, "a person decides")
    assert "decided-by" in paragraph and "qa --next" in paragraph


def test_jira_qa_records_no_verdict():
    text = prompt("qa", "jira")
    assert "tcw work path <slug> qa" not in text and "verdict:" not in text


def test_jira_qa_moves_the_ticket_when_the_person_gives_the_verdict():
    """TCW-100: the person decides; once they give the verdict in the
    conversation, the agent records it with `advance`, and otherwise stops."""
    paragraph = _paragraph_with(prompt("qa", "jira"), "gives you the verdict")
    assert "--to completed --reason" in paragraph
    assert "--to implement --reason" in paragraph
    assert "after they have seen your findings" in paragraph
    assert "stop at qa" in paragraph


def test_jira_request_writes_adopted_wording_before_moving():
    """TCW-100: adopted wording goes into the description, is read back, and
    only then is the item moved, with a reason naming who said to move it."""
    paragraph = _paragraph_with(prompt("request", "jira"), "tell you to move")
    for words in ("description", "paste", "read it back",
                  "tcw work advance <slug> --reason"):
        assert words in paragraph, words
    assert paragraph.index("read it back") < paragraph.index("tcw work advance")


@pytest.mark.parametrize("sid", sorted(SHIPPED))
def test_no_prompt_tells_the_agent_to_ask_what_it_is_reading(sid):
    """`tcw work lifecycle --stage <id>` inside the text that command reports
    is circular."""
    assert "tcw work lifecycle --stage" not in load_builtins().stage_prompts[sid]


@pytest.mark.parametrize("sid", sorted(SHIPPED))
def test_no_prompt_dispatches_an_agent_by_name(sid):
    """An agent is Claude packaging; a prompt naming one leaves Codex and Pi
    users a reference to nothing. The one skill a prompt names,
    `documentation-sync`, is named with the condition that the plugin is
    installed (Design 12)."""
    text = load_builtins().stage_prompts[sid]
    for name in ("verifier", "reviewer agent", "backlog-auditor", "work-stage"):
        assert name not in text


def test_the_self_review_pass_appears_in_exactly_three_prompts():
    """A pass earns its place only where it checks the document against a
    source outside itself. Set equality, so copying it into every prompt fails."""
    prompts = load_builtins().stage_prompts
    found = {sid for sid, text in prompts.items() if "self-review" in text.lower()}
    assert found == {"spec", "plan", "implement"}


def test_jira_request_keeps_what_the_requester_did_not_change():
    """TCW-101: adopted wording changes only what was adopted."""
    paragraph = _paragraph_with(prompt("request", "jira"), "tell you to move")
    assert "keep everything else in the description" in paragraph


@pytest.mark.parametrize("backend", BACKENDS)
def test_spec_says_what_to_do_when_the_requester_revises_the_request(backend):
    """TCW-101: the item stays at spec, and the change is recorded where the
    request lives, in either backend's form."""
    paragraph = _paragraph_with(prompt("spec", backend), "The requester revises")
    for words in ("stays at spec", "amendment", "## Added", "`Added` comment"):
        assert words in paragraph, words


def test_plan_says_how_to_file_a_part_into_another_project():
    """TCW-114 Design 2.1, 9.2: a part for another project is made in that
    project, with `tcw -C` and `--parent`; the removed `--project` is not
    named, and neither is anything it needed afterwards."""
    paragraph = _paragraph_with(prompt("plan", "filesystem"), "Too large for one item")
    flat = " ".join(paragraph.split())
    order = [flat.index(s) for s in (
        "--parent <slug> --nest` per part",
        'tcw -C tcw://<id>.path/ work new "<title>" --parent <slug> --nest',
        "set `--blocked-by` the same way",
        "TCW records it in the part's folder")]
    assert order == sorted(order)
    for gone in ("--project", "ticket key printed", "version control", "uncommitted",
                 "only a ticket on its own site"):
        assert gone not in flat, gone


def test_no_shipped_procedure_or_prompt_names_project_filing():
    assert "--project" not in prompt("plan", "filesystem")
    assert "--project" not in (PACKAGE / "work" / "procedures" /
                               "audit-backlog.md").read_text(encoding="utf-8")


def test_plan_nests_each_part_in_its_parent():
    """TCW-111 AC 19: each part is made with --nest, which puts its folder
    inside the parent's; --parent is what makes it a part."""
    for backend in ("filesystem", "jira"):
        paragraph = _paragraph_with(prompt("plan", backend), "Too large for one item")
        flat = " ".join(paragraph.split())
        assert "--parent <slug> --nest" in flat, paragraph
        assert "puts the part's folder inside the parent's folder" in flat
        assert "`--parent`, not the folder, is what makes it a part" in flat
