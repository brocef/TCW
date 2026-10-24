"""The repository's references rewritten after a move, and the mentions
listed (TCW-114 Design 6; plan Step 16)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tcw.ids import FullId
from tcw.reference_fields import fields_of
from tcw.rewrite import (RewriteStopped, field_problems, mentions, rewrite_references,
                         rewrite_yaml, unreadable_records)
from tests.objectcli import obj, project
from tests.statefiles import write_state

OLD = "2026-10-22-old"


def fid(text: str) -> FullId:
    project_id, rest = text.split(".", 1)
    namespace, _, id_path = rest.partition("/")
    return FullId(project_id, namespace, id_path)


def pairs(*texts: tuple[str, str]):
    return [(fid(a), fid(b)) for a, b in texts]


INVOICE = pairs(("demo.taxonomy/invoice", "demo.taxonomy/bill"))
ADMIN = pairs(("demo.capabilities/roles/admin", "demo.capabilities/roles/staff/admin"))
WORK = pairs((f"demo.work/{OLD}", "demo.work/2026-10-22-new"))


# -- rewrite_yaml on its own -------------------------------------------------------------


def test_each_scalar_style_keeps_its_quoting():
    rows = fields_of("capability")
    text = ("Status: Supported\n"
            "Subject: [demo.taxonomy/invoice, demo.taxonomy/other]\n"
            "Feature: 'demo.taxonomy/invoice'\n"
            "Superseded by: \"demo.capabilities/roles/admin\"\n"
            "Roles: demo.capabilities/roles/admin, '!demo.capabilities/roles/admin'\n")
    new, changed, _ = rewrite_yaml(text, rows, [*INVOICE, *ADMIN])
    assert new == ("Status: Supported\n"
                   "Subject: [demo.taxonomy/bill, demo.taxonomy/other]\n"
                   "Feature: 'demo.taxonomy/bill'\n"
                   "Superseded by: \"demo.capabilities/roles/staff/admin\"\n"
                   "Roles: demo.capabilities/roles/staff/admin, "
                   "'!demo.capabilities/roles/admin'\n")
    assert len(changed) == 4


def test_a_negated_list_item_keeps_its_mark():
    text = "Roles:\n- '!demo.capabilities/roles/admin'\n- demo.capabilities/roles/x\n"
    new, changed, _ = rewrite_yaml(text, fields_of("capability"), ADMIN)
    assert new == ("Roles:\n- '!demo.capabilities/roles/staff/admin'\n"
                   "- demo.capabilities/roles/x\n")
    assert changed == ["Roles !demo.capabilities/roles/admin -> "
                       "!demo.capabilities/roles/staff/admin"]


def test_a_comma_list_keeps_a_negated_value_and_its_spacing():
    text = "When: demo.capabilities/c/x,  !demo.capabilities/roles/admin\n"
    rows = [r for r in fields_of("capability") if r.name == "When"]
    # `When` names conditions; the parse is by namespace, so the value matches.
    new, _, _ = rewrite_yaml(text, rows, ADMIN)
    assert new == "When: demo.capabilities/c/x,  !demo.capabilities/roles/staff/admin\n"


def test_a_block_sequence_and_a_nested_key():
    text = ("new:\n  - demo.capabilities/roles/admin\n"
            "taxonomy: {changed: [demo.taxonomy/invoice]}\n"
            "notes: demo.taxonomy/invoice\n")
    new, changed, _ = rewrite_yaml(text, fields_of("capabilities-yaml"),
                                   [*INVOICE, *ADMIN])
    assert new == ("new:\n  - demo.capabilities/roles/staff/admin\n"
                   "taxonomy: {changed: [demo.taxonomy/bill]}\n"
                   "notes: demo.taxonomy/invoice\n")
    assert len(changed) == 2


def test_a_value_under_another_key_is_never_changed():
    text = "name: demo.taxonomy/invoice\nrelatesTo: [demo.taxonomy/invoice]\n"
    new, _, _ = rewrite_yaml(text, fields_of("term"), INVOICE)
    assert new == "name: demo.taxonomy/invoice\nrelatesTo: [demo.taxonomy/bill]\n"


def test_a_longer_identifier_is_not_matched():
    text = f"parent: demo.work/{OLD}-two\n"
    new, changed, _ = rewrite_yaml(text, fields_of("work-item"), WORK)
    assert new == text and changed == []


def test_a_value_already_new_is_counted_as_done():
    text = "Feature: demo.taxonomy/bill\n"
    new, changed, done = rewrite_yaml(text, fields_of("capability"), INVOICE)
    assert (new, changed, done) == (text, [], ["Feature demo.taxonomy/bill"])


# -- rewrite_references over a project -----------------------------------------------------


@pytest.fixture
def demo(tmp_path):
    root = project(tmp_path, "demo", work={})
    obj(root, "taxonomy", "vocab", name="Vocab", kind="Vocabulary")
    write_state(root / "docs/taxonomy/invoice/tcw-taxonomy.yaml",
                "name: Invoice\nkind: Feature\nvocabulary: [demo.taxonomy/vocab]\n")
    write_state(root / "docs/taxonomy/payment/tcw-taxonomy.yaml",
                "name: Payment\nkind: Feature\nvocabulary: [demo.taxonomy/vocab]\n"
                "relatesTo: [demo.taxonomy/invoice]\n"
                "note: see demo.taxonomy/invoice\n")
    write_state(root / "docs/capabilities/roles/admin/tcw-capability.yaml",
                "name: Admin\nStatus: Supported\n")
    write_state(root / "docs/capabilities/cli/y/tcw-capability.yaml",
                "name: demo.capabilities/cli/x\nStatus: Supported\n"
                "Feature: demo.taxonomy/invoice\n"
                "Roles: '!demo.capabilities/roles/admin'\n")
    item_dir = root / "docs/work" / OLD
    write_state(item_dir / "tcw-work-item.yaml",
                "title: Old\nstage: request\n")
    write_state(root / "docs/work/2026-10-22-r/tcw-work-item.yaml",
                f"title: R\nstage: request\nparent: demo.work/{OLD}\n")
    (root / "docs/work/2026-10-22-r/capabilities.yaml").write_text(
        "changed:\n- demo.capabilities/roles/admin\n"
        "taxonomy:\n  changed: [demo.taxonomy/invoice]\n"
        "notes: demo.capabilities/roles/admin\n")
    spec = root / "docs/work/2026-10-22-r/spec/spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(f"See [the old one](tcw://demo.work/{OLD}) now.\n"
                    f"Not [this](tcw://demo.work/{OLD}-two).\n"
                    f"In code: `[x](tcw://demo.work/{OLD})`\n"
                    "```\n"
                    f"[y](tcw://demo.work/{OLD})\n"
                    "```\n"
                    f"Prose names demo.work/{OLD} plainly.\n"
                    f"Another epic's part is other-epic/{OLD}x.\n")
    (root / "docs/capabilities/cli/y/description.md").write_text(
        "Uses [invoices](tcw://demo.taxonomy/invoice).\n")
    return root


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}


def test_every_field_is_rewritten_and_nothing_else(demo):
    before = snapshot(demo)
    results = rewrite_references(demo, [*INVOICE, *ADMIN, *WORK])
    after = snapshot(demo)
    changed = {k for k in after if after[k] != before[k]}
    assert changed == {
        "docs/taxonomy/payment/tcw-taxonomy.yaml",
        "docs/capabilities/cli/y/tcw-capability.yaml",
        "docs/capabilities/cli/y/description.md",
        "docs/work/2026-10-22-r/capabilities.yaml",
        "docs/work/2026-10-22-r/spec/spec.md"}
    assert after["docs/taxonomy/payment/tcw-taxonomy.yaml"] == before[
        "docs/taxonomy/payment/tcw-taxonomy.yaml"].replace(
        b"relatesTo: [demo.taxonomy/invoice]", b"relatesTo: [demo.taxonomy/bill]")
    assert after["docs/capabilities/cli/y/tcw-capability.yaml"] == before[
        "docs/capabilities/cli/y/tcw-capability.yaml"].replace(
        b"Feature: demo.taxonomy/invoice", b"Feature: demo.taxonomy/bill").replace(
        b"'!demo.capabilities/roles/admin'", b"'!demo.capabilities/roles/staff/admin'")
    assert after["docs/work/2026-10-22-r/capabilities.yaml"] == (
        b"changed:\n- demo.capabilities/roles/staff/admin\n"
        b"taxonomy:\n  changed: [demo.taxonomy/bill]\n"
        b"notes: demo.capabilities/roles/admin\n")
    assert after["docs/work/2026-10-22-r/spec/spec.md"].decode() == (
        "See [the old one](tcw://demo.work/2026-10-22-new) now.\n"
        f"Not [this](tcw://demo.work/{OLD}-two).\n"
        f"In code: `[x](tcw://demo.work/{OLD})`\n"
        "```\n"
        f"[y](tcw://demo.work/{OLD})\n"
        "```\n"
        f"Prose names demo.work/{OLD} plainly.\n"
        f"Another epic's part is other-epic/{OLD}x.\n")
    # The work item's state file is the backend's: left byte for byte.
    assert after["docs/work/2026-10-22-r/tcw-work-item.yaml"] == before[
        "docs/work/2026-10-22-r/tcw-work-item.yaml"]
    assert all("tcw-work-item.yaml" not in str(r.path) for r in results)


def test_by_field_not_by_value_the_rest_are_mentions(demo):
    rewrite_references(demo, [*INVOICE, *ADMIN, *WORK])
    said = mentions(demo, [*INVOICE, *ADMIN, *WORK])
    text = "\n".join(said)
    assert "payment/tcw-taxonomy.yaml:6: names demo.taxonomy/invoice, not rewritten" in text
    assert ("cli/y/tcw-capability.yaml:2: names demo.capabilities/cli/x"
            not in text)           # not a changed identifier
    assert ("2026-10-22-r/capabilities.yaml:5: names demo.capabilities/roles/admin, "
            "not rewritten") in text
    spec = [line for line in said if "spec.md" in line]
    assert spec == [
        f"{demo / 'docs/work/2026-10-22-r/spec/spec.md'}:3: names demo.work/{OLD}, "
        "not rewritten",
        f"{demo / 'docs/work/2026-10-22-r/spec/spec.md'}:5: names demo.work/{OLD}, "
        "not rewritten",
        f"{demo / 'docs/work/2026-10-22-r/spec/spec.md'}:7: names demo.work/{OLD}, "
        "not rewritten"]


def test_a_capability_name_equal_to_an_old_identifier_is_a_mention(demo):
    moved = pairs(("demo.capabilities/cli/x", "demo.capabilities/cli/z"))
    before = snapshot(demo)
    rewrite_references(demo, moved)
    assert snapshot(demo) == before
    assert any("cli/y/tcw-capability.yaml:2: names demo.capabilities/cli/x, not "
               "rewritten" in line for line in mentions(demo, moved))


def test_a_second_run_changes_nothing_and_reports_it_done(demo):
    changes = [*INVOICE, *ADMIN, *WORK]
    first = rewrite_references(demo, changes)
    after_first = snapshot(demo)
    second = rewrite_references(demo, changes)
    assert snapshot(demo) == after_first
    assert all(r.changed == [] for r in second)
    assert sum(len(r.done) for r in second) == sum(len(r.changed) for r in first)


def test_a_file_that_cannot_be_written_carries_the_files_before_it(demo, monkeypatch):
    import tcw.store.fs as fs
    real = fs._atomic_write_all
    calls = []

    def failing(pairs_):
        calls.append(pairs_[0][0])
        if len(calls) == 2:
            raise PermissionError(13, "Permission denied")
        return real(pairs_)
    monkeypatch.setattr(fs, "_atomic_write_all", failing)
    with pytest.raises(RewriteStopped) as stop:
        rewrite_references(demo, [*INVOICE, *ADMIN, *WORK])
    assert [r.path for r in stop.value.results if r.changed] == [calls[0]]
    assert stop.value.path == calls[1]


def test_a_failed_promote_leaves_the_file_whole_and_no_temporary(demo, monkeypatch):
    """Each file is replaced in one step (Design 6.6)."""
    real_replace = Path.replace
    seen = []

    def replace(self, target):
        seen.append(target)
        if len(seen) == 2:
            raise OSError(5, "Input/output error")
        return real_replace(self, target)
    monkeypatch.setattr(Path, "replace", replace)
    before = snapshot(demo)
    with pytest.raises(RewriteStopped):
        rewrite_references(demo, [*INVOICE, *ADMIN, *WORK])
    after = snapshot(demo)
    first, second = (str(Path(p).relative_to(demo)) for p in seen)
    assert after[first] != before[first]
    assert after[second] == before[second]
    assert not [k for k in after if k.endswith(".tmp")]


# -- the checks before a move ----------------------------------------------------------


def test_field_problems_names_the_field_and_the_record(demo):
    problems = field_problems(demo, pairs(("demo.capabilities/roles/admin",
                                           "demo.capabilities/cli/owner")))
    assert len(problems) == 1
    assert "Roles" in problems[0] and "cli/y" in problems[0]
    assert field_problems(demo, ADMIN) == []


def test_unreadable_records_are_named(demo):
    (demo / "docs/capabilities/cli/y/tcw-capability.yaml").write_text(
        "tcw-version: banana\nname: Y\n")
    (demo / "docs/work/2026-10-22-r/capabilities.yaml").write_text("new: [unclosed\n")
    found = "\n".join(unreadable_records(demo))
    assert "cli/y/tcw-capability.yaml" in found
    assert "2026-10-22-r/capabilities.yaml" in found


def test_mentions_skip_a_file_that_is_not_utf8(demo):
    (demo / "docs/work/2026-10-22-r/spec/notes.md").write_bytes(
        b"\xff\xfe demo.work/" + OLD.encode())
    assert not [m for m in mentions(demo, WORK) if "notes.md" in m]


def test_a_nested_part_is_named_by_its_whole_path(demo):
    nested = pairs((f"demo.work/{OLD}/p", "demo.work/2026-10-22-new/p"))
    (demo / "docs/work/2026-10-22-r/spec/more.md").write_text(
        f"Part demo.work/{OLD}/p here.\nAnd other-epic/p there.\n")
    said = [m for m in mentions(demo, nested) if "more.md" in m]
    assert said == [f"{demo / 'docs/work/2026-10-22-r/spec/more.md'}:1: names "
                    f"demo.work/{OLD}/p, not rewritten"]
