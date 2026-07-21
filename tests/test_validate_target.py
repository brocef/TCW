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
    config = yaml.safe_load((root / "tcw-config.yaml").read_text())
    config["connected-projects"] = {"children": {"missing": "missing-node"}}
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    problems = validate(root, target=ValidationTarget("work", "missing"))
    assert problems and all(problem.startswith("project graph:") for problem in problems)


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
    taxonomy = FsTaxonomyStore.open(root)
    taxonomy.add("Feature", slug="feature", kind="Feature")
    taxonomy.add("Other feature", slug="other", kind="Feature")
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


def test_work_target_includes_bounded_resources(tmp_path):
    root = _node(tmp_path)
    work = FsWorkStore.open(root)
    detail = work.create_work("Resources")
    work.write_artifact(detail.item.slug, "spec", "[bad](tcw://C/missing)\n")
    (work.path(detail.item.slug) / "capabilities.yaml").write_text("changed: [\n")
    problems = validate(root, target=ValidationTarget("work", detail.item.slug))
    assert any("tcw://" in problem for problem in problems)
    assert any("capabilities.yaml" in problem for problem in problems)
