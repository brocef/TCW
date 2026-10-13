"""Which file a problem is blamed on, and `file:` confinement at load time
(TCW-72 Design 5.1, 5.2, 6.1; AC 10's first half)."""

from __future__ import annotations

from tcw.config import load_config
from tests.config.conftest import problem_lines


def test_a_bad_binding_in_a_personal_file_is_blamed_on_that_file(personal):
    personal.user({"work": {"stages": {"spec": {"prompt": [{"nonsense": 1}]}}}})
    lines = problem_lines(load_config(personal.root))
    assert len(lines) == 1, lines
    assert lines[0].startswith(f"{personal.user_file}: work.stages.spec.prompt[0]: ")


def test_a_bad_when_is_blamed_on_the_entry_that_holds_it(personal):
    personal.local({"work": {"stages": {"spec": {"prompt": [
        {"blob": "x", "when": {"type": "bug"}}]}}}})
    lines = problem_lines(load_config(personal.root))
    assert len(lines) == 1 and lines[0].startswith("tcw-config.local.yaml: "), lines


def test_an_unknown_stage_in_a_personal_file_is_blamed_on_it(personal):
    personal.local({"work": {"stages": {"nonsense": {"prompt": [{"blob": "x"}]}}}})
    lines = problem_lines(load_config(personal.root))
    assert lines and all(l.startswith("tcw-config.local.yaml: ") for l in lines), lines


def test_a_project_problem_is_blamed_on_the_project_file(personal):
    personal.project({"work": {"hooks": {"timeout": -1}}})
    assert problem_lines(load_config(personal.root)) == [
        "tcw-config.yaml: work.hooks.timeout: must be a positive number of "
        "seconds, got -1"]


def test_a_built_in_entry_is_never_blamed_on_a_file(personal):
    config = load_config(personal.root)
    assert all(b.origin.file is None for b in config.work.stage("spec").prompt)


def test_a_user_file_reads_prompt_files_from_its_own_folder(personal):
    (personal.user_file.parent / "prompts").mkdir(parents=True)
    (personal.user_file.parent / "prompts" / "spec.md").write_text("mine\n")
    personal.user({"work": {"stages": {"spec": {"prompt": [{"file": "prompts/spec.md"}]}}}})
    config = load_config(personal.root)
    assert config.problems == []
    binding = config.work.stage("spec").prompt[0]
    assert binding.origin.folder / binding.value == \
        personal.xdg / "tcw" / "prompts" / "spec.md"


def test_a_file_leaving_its_folder_is_a_problem_whether_or_not_it_exists(personal):
    (personal.xdg / "x.md").parent.mkdir(parents=True, exist_ok=True)
    for exists in (False, True):
        if exists:
            (personal.xdg / "x.md").write_text("x\n")
        personal.user({"work": {"stages": {"spec": {"prompt": [{"file": "../x.md"}]}}}})
        lines = problem_lines(load_config(personal.root))
        assert len(lines) == 1, (exists, lines)
        assert lines[0].startswith(f"{personal.user_file}: work.stages.spec.prompt[0]: ")


def test_a_project_file_leaving_the_project_is_a_problem(personal):
    personal.project({"work": {"stages": {"spec": {"prompt": [{"file": "../x.md"}]}}}})
    lines = problem_lines(load_config(personal.root))
    assert len(lines) == 1 and lines[0].startswith("tcw-config.yaml: "), lines


def test_a_key_path_is_written_with_dots_and_brackets(personal):
    personal.project({"work": {"stages": {"spec": {"prompt": [{"blob": "a"},
                                                              {"bogus": 1}]}}}})
    lines = problem_lines(load_config(personal.root))
    assert lines[0].startswith("tcw-config.yaml: work.stages.spec.prompt[1]: "), lines


def test_an_unreadable_project_file_is_one_problem(personal):
    personal.project_file.write_text("id: [unclosed\n")
    config = load_config(personal.root)
    assert config.unreadable and len(config.problems) == 1


# -- A file that is not UTF-8 (review finding L4) --------------------------------------


def test_a_local_file_that_is_not_utf8_is_a_problem_naming_it(personal):
    personal.local_file.write_bytes(b"user:\n  name: Ren\xe9\n")
    config = load_config(personal.root)
    assert problem_lines(config) == [
        "tcw-config.local.yaml: is not valid UTF-8 text (byte 0xe9 at position 17)"]


def test_a_project_file_that_is_not_utf8_is_unreadable(personal):
    personal.project_file.write_bytes(b"id: p\xff\n")
    config = load_config(personal.root)
    assert config.unreadable
    assert problem_lines(config) == [
        "tcw-config.yaml: is not valid UTF-8 text (byte 0xff at position 5)"]


def test_config_show_origin_names_a_file_that_is_not_utf8(personal):
    from tests.config.conftest import tcw
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.user_file.parent.mkdir(parents=True)
    personal.user_file.write_bytes(b"\xff\xfe")
    result = tcw(personal.root, "config", "show", "--origin")
    assert result.code == 1, result
    assert "builtin: true" in result.out
    assert result.err == f"tcw config show: {personal.user_file}: is not valid UTF-8 " \
                         f"text (byte 0xff at position 0)\n"


# -- Several problems, one line each (review finding L6) -------------------------------


def test_every_problem_is_its_own_prefixed_line(personal):
    from tests.config.conftest import tcw
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.project({"work": {"hooks": {"timeout": -1, "output-cap": -1}}})
    personal.local({"id": "other"})
    result = tcw(personal.root, "work", "list")
    assert result.code == 1, result
    lines = result.err.splitlines()
    assert len(lines) == 3, lines
    assert all(line.startswith("tcw work list: ") for line in lines), lines
