import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, FsWorkStore, init
from tcw.validate import ValidationTarget, validate


def _node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["taxonomy", "capabilities", "work"], root, "repo")
    return root


def test_rejects_path_and_target_together(tmp_path):
    root = _node(tmp_path)
    with pytest.raises(ValueError, match="mutually exclusive"):
        validate(root, root / "docs", target=ValidationTarget("work", "missing"))


@pytest.mark.parametrize("axis", ["taxonomy", "capabilities", "work"])
def test_missing_target_is_explicit(tmp_path, axis):
    root = _node(tmp_path)
    assert validate(root, target=ValidationTarget(axis, "missing")) == [
        f"{axis} target: no such object 'missing'"
    ]


def test_graph_problems_precede_target_resolution(tmp_path):
    root = _node(tmp_path)
    broken = tmp_path / "broken-node"
    broken.mkdir()
    (broken / "tcw-config.yaml").write_text("id: broken-node\nid: dupe\n")
    config = yaml.safe_load((root / "tcw-config.yaml").read_text())
    config["connected-projects"] = {"children": {"broken-node": str(broken)}}
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    problems = validate(root, target=ValidationTarget("work", "missing"))
    assert problems and all(problem.startswith("project graph:") for problem in problems)


def test_an_absent_connected_project_does_not_block_target_resolution(tmp_path):
    """The case above used to be spelled with a target that is simply not here.

    That is no longer a graph problem — a locator naming nothing on this machine
    is a fact about the checkout — so validation proceeds to the target instead
    of refusing before it.
    """
    root = _node(tmp_path)
    config = yaml.safe_load((root / "tcw-config.yaml").read_text())
    config["connected-projects"] = {"children": {"missing": "missing-node"}}
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    assert validate(root, target=ValidationTarget("work", "missing")) == [
        "work target: no such object 'missing'"
    ]


def test_target_scans_only_selected_yaml_and_links(tmp_path):
    root = _node(tmp_path)
    taxonomy = FsTaxonomyStore.open(root)
    taxonomy.add("Good", slug="good")
    taxonomy.add("Broken", slug="broken")
    (root / "docs/taxonomy/good/description.md").write_text("[bad](tcw://T/missing)\n")
    (root / "docs/taxonomy/broken/meta.yaml").write_text("name: [\n")
    targeted = validate(root, target=ValidationTarget("taxonomy", "good"))
    full = validate(root)
    assert any("tcw://" in problem for problem in targeted)
    assert not any("broken/meta.yaml" in problem for problem in targeted)
    assert any("broken/meta.yaml" in problem for problem in full)


def test_target_reports_its_own_malformed_yaml(tmp_path):
    root = _node(tmp_path)
    FsCapabilitiesStore.open(root).add("broken")
    (root / "docs/capabilities/broken/meta.yaml").write_text("name: [\n")
    problems = validate(root, target=ValidationTarget("capabilities", "broken"))
    assert any("broken/meta.yaml" in problem for problem in problems)
    assert any("component checks skipped" in problem for problem in problems)


def test_axis_semantics_are_object_local(tmp_path):
    root = _node(tmp_path)
    # Features carrying no vocabulary ref: `add` refuses them now, so write the
    # nodes directly — the point here is that `check` reports only the target.
    for slug in ("feature", "other"):
        d = root / "docs" / "taxonomy" / slug
        d.mkdir(parents=True)
        (d / "meta.yaml").write_text(f"name: {slug}\nkind: Feature\nrelatesTo: []\n")
        (d / "description.md").write_text("")
    capability = FsCapabilitiesStore.open(root)
    capability.add("bad", status="Partial")
    capability.add("other", status="Blocked")
    work = FsWorkStore.open(root)
    item = work.create_work("Tagged")
    work.set_field(item.item.slug, "tags", ["stale"])
    assert any("Feature requires" in problem for problem in validate(root, target=ValidationTarget("taxonomy", "feature")))
    assert not any("other" in problem for problem in validate(root, target=ValidationTarget("taxonomy", "feature")))
    cap_problems = validate(root, target=ValidationTarget("capabilities", "bad"))
    assert any("Partial requires Gaps" in problem for problem in cap_problems)
    assert not any("other" in problem for problem in cap_problems)
    assert any("unregistered tag" in problem for problem in validate(root, target=ValidationTarget("work", item.item.slug)))


def test_work_target_reports_an_item_that_vanishes_mid_check(tmp_path, monkeypatch):
    """`check` resolves the item again after reading its plan stages; losing it in
    between used to be `None / "plan.md"` → `TypeError`. It is now absorbed by the
    enclosing `except ValueError` and reported as a validation problem — a
    spurious line when the item merely moved, which beats a traceback."""
    root = _node(tmp_path)
    work = FsWorkStore.open(root)
    detail = work.create_work("Vanishing")
    work.write_artifact(detail.item.slug, "plan",
                        "---\nstages: [{id: model, title: Build, depends_on: []}]\n---\n")

    real_stages = FsWorkStore._declared_plan_stages

    def vanish_after_stages(self, slug):
        stages = real_stages(self, slug)
        monkeypatch.setattr(FsWorkStore, "_find", lambda self, slug: None)
        return stages

    monkeypatch.setattr(FsWorkStore, "_declared_plan_stages", vanish_after_stages)
    problems = validate(root, target=ValidationTarget("work", detail.item.slug))
    assert any("no such work item" in problem for problem in problems)


def test_work_target_includes_bounded_resources(tmp_path):
    root = _node(tmp_path)
    work = FsWorkStore.open(root)
    detail = work.create_work("Resources")
    work.write_artifact(detail.item.slug, "spec", "[bad](tcw://C/missing)\n")
    (work.path(detail.item.slug) / "capabilities.yaml").write_text("changed: [\n")
    problems = validate(root, target=ValidationTarget("work", detail.item.slug))
    assert any("tcw://" in problem for problem in problems)
    assert any("capabilities.yaml" in problem for problem in problems)
