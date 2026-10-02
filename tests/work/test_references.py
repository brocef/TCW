"""Reference and stage-ahead checks for `tcw validate` (TCW-69 Design 9; AC 17)."""

from datetime import date

from tcw.work.layout import Layout
from tcw.work.model import STAGES, Item, Slug
from tcw.work.references import reference_problems, stage_problems

ALL = frozenset(s.name for s in STAGES)


def item(folder, stage="spec", *, project="tcw", parent=None, blocked_by=()):
    return Item(slug=Slug(project, folder), title=folder, stage=stage,
                created=date(2026, 10, 1), priority="medium", effort=None,
                complexity=None, tags=(), assignee=None, parent=parent,
                blocked_by=tuple(blocked_by))


def never(slug):
    raise AssertionError(f"asked to resolve {slug}")


def test_a_missing_same_project_blocker_is_a_warning():
    a = item("a", blocked_by=[Slug("tcw", "gone")])
    [problem] = reference_problems([a], "tcw", never)
    assert (problem.level, problem.slug) == ("warning", a.slug)
    assert "missing item" in problem.message and "tcw/gone" in problem.message


def test_a_missing_parent_is_a_warning():
    a = item("a", parent=Slug("tcw", "gone"))
    assert [p.level for p in reference_problems([a], "tcw", never)] == ["warning"]


def test_a_completed_blocker_is_not_a_warning():
    done = item("done", "completed")
    a = item("a", blocked_by=[done.slug])
    assert reference_problems([a, done], "tcw", never) == []


def test_cross_project_references_go_through_resolve():
    answers = {Slug("far", "x"): "unresolved", Slug("near", "y"): "missing",
               Slug("near", "z"): "found"}
    a = item("a", blocked_by=list(answers))
    problems = reference_problems([a], "tcw", answers.__getitem__)
    assert sorted(p.level for p in problems) == ["unresolved", "warning"]
    unresolved = next(p for p in problems if p.level == "unresolved")
    assert "far/x" in unresolved.message


def write(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x")


def test_an_item_ahead_of_its_artifacts_is_warned(tmp_path):
    layout = Layout(tmp_path, ALL, frozenset())
    a = item("a", "plan")
    write(layout.document(a.slug, "request"))
    [problem] = stage_problems([a], layout)
    assert problem.level == "warning"
    assert "spec" in problem.message and "forced" in problem.message


def test_a_disabled_stage_needs_no_artifact(tmp_path):
    layout = Layout(tmp_path, ALL - {"spec"}, frozenset())
    a = item("a", "plan")
    write(layout.document(a.slug, "request"))
    assert stage_problems([a], layout) == []


def test_rounds_count_and_external_stages_are_skipped(tmp_path):
    layout = Layout(tmp_path, ALL - {"spec", "plan"}, frozenset({"request"}))
    a = item("a", "review")
    assert len(stage_problems([a], layout)) == 1          # no implement round
    write(layout.stage_dir(a.slug, "implement") / "round-1.md")
    assert stage_problems([a], layout) == []


def test_finished_and_stageless_items_are_skipped(tmp_path):
    layout = Layout(tmp_path, ALL, frozenset())
    assert stage_problems([item("a", "discarded"), item("b", "completed"),
                           item("c", None)], layout) == []
