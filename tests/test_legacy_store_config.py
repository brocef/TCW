"""A leftover pre-2.5.0 store config file is reported, never read or touched.

Before 2.5.0 a tree store kept its `extends` in a file at its own root —
`config.yaml` for taxonomy, `.config.yaml` for capabilities. Since 2.5.0 that
list lives in the node's `tcw-config.yaml`, and the old file is not read. A
project that upgraded without moving it silently lost every inherited entry,
with nothing pointing at the cause. `check` (and `tcw validate`) now name the
file and the fix; nothing parses, rewrites or deletes it.
"""
import shutil
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore
from tcw.validate import ValidationTarget, validate

from nodeconfig import declare_extends, set_component_key
from test_validate import connect, node

LEFTOVER = {"taxonomy": "config.yaml", "capabilities": ".config.yaml"}
STORE = {"taxonomy": FsTaxonomyStore, "capabilities": FsCapabilitiesStore}
MARK = "no longer read"


def _write_term(root: Path, slug: str, *, tree: str = "docs/taxonomy") -> None:
    d = root / tree / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.yaml").write_text(yaml.safe_dump({"name": slug, "relatesTo": []}))
    (d / "description.md").write_text("")


def _write_cap(root: Path, path: str, cap_id: str, *,
               tree: str = "docs/capabilities") -> None:
    d = root / tree / path
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.yaml").write_text(yaml.safe_dump(
        {"id": cap_id, "name": path, "Status": "Supported"}, sort_keys=False))
    (d / "description.md").write_text("")


def _federated(tmp_path: Path) -> Path:
    """A consumer connected to `shared`, which has one term and one capability.

    `extends` is declared nowhere: the only place it is written is the
    leftover file each test adds, which is exactly the un-migrated project.
    """
    shared = node(tmp_path, "shared", "shared", ["taxonomy", "capabilities"])
    _write_term(shared, "Argument")
    _write_cap(shared, "auth", "cap-shared1")
    consumer = node(tmp_path, "consumer", "consumer", ["taxonomy", "capabilities"])
    connect(consumer, shared)
    _write_term(consumer, "Local")
    _write_cap(consumer, "local/thing", "cap-local1")
    return consumer


def _leftover_lines(problems: list[str]) -> list[str]:
    return [p for p in problems if MARK in p]


def _assert_one_leftover(problems: list[str], component: str, shown: str,
                         prefix: str = "") -> str:
    """Exactly one leftover line, naming the file, the key and the whole fix.

    `prefix` is what `tcw validate` puts in front of a component's problems
    (`taxonomy check: `, and `[<project>] ` when it recurses).
    """
    lines = [p for p in _leftover_lines(problems) if f"{component}.extends" in p]
    assert len(lines) == 1, problems
    line = lines[0]
    assert line.startswith(f"{prefix}{shown}: "), line
    assert f"{component}.extends" in line and "tcw-config.yaml" in line, line
    assert "then delete the file" in line, line
    assert "if already migrated, just delete it" in line, line
    return line


# ── the store reports its own leftover ───────────────────────────────────────

@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
def test_a_leftover_at_the_default_location_is_reported_by_check(
        tmp_path, monkeypatch, capsys, component):
    consumer = _federated(tmp_path)
    name = LEFTOVER[component]
    (consumer / "docs" / component / name).write_text("extends:\n  - shared\n")

    _assert_one_leftover(STORE[component].open(consumer).check(), component,
                         f"docs/{component}/{name}")

    monkeypatch.chdir(consumer)
    assert main([component, "check"]) == 1
    _assert_one_leftover(capsys.readouterr().err.splitlines(), component,
                         f"docs/{component}/{name}")


@pytest.mark.parametrize("component,moved", [
    ("taxonomy", "tax"), ("capabilities", "caps")])
def test_a_leftover_in_a_moved_store_is_reported_at_its_real_path(
        tmp_path, component, moved):
    consumer = _federated(tmp_path)
    shutil.move(str(consumer / "docs" / component), str(consumer / moved))
    set_component_key(consumer, component, "path", moved)
    (consumer / moved / LEFTOVER[component]).write_text("extends: [shared]\n")

    _assert_one_leftover(STORE[component].open(consumer).check(), component,
                         f"{moved}/{LEFTOVER[component]}")


@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
def test_a_leftover_outside_the_node_is_named_by_its_absolute_path(
        tmp_path, component):
    consumer = _federated(tmp_path)
    elsewhere = tmp_path / f"elsewhere-{component}"
    shutil.move(str(consumer / "docs" / component), str(elsewhere))
    set_component_key(consumer, component, "path", str(elsewhere))
    (elsewhere / LEFTOVER[component]).write_text("extends: [shared]\n")

    _assert_one_leftover(STORE[component].open(consumer).check(), component,
                         str((elsewhere / LEFTOVER[component]).resolve()))


@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
@pytest.mark.parametrize("content,migrated", [
    ("", False),
    ("extends: []\n", False),
    ("extends: [shared]\n", True),         # already copied into tcw-config.yaml
    ("extends: [unclosed\n", False),       # not YAML at all: never parsed
])
def test_the_leftover_is_reported_whatever_it_holds(
        tmp_path, component, content, migrated):
    consumer = _federated(tmp_path)
    if migrated:
        declare_extends(consumer, component, "extends: [shared]\n")
    (consumer / "docs" / component / LEFTOVER[component]).write_text(content)

    _assert_one_leftover(STORE[component].open(consumer).check(), component,
                         f"docs/{component}/{LEFTOVER[component]}")


def test_only_a_file_at_the_store_root_is_a_leftover(tmp_path):
    consumer = _federated(tmp_path)
    tax, caps = consumer / "docs" / "taxonomy", consumer / "docs" / "capabilities"
    # Inside a folder node: an ordinary file of that node.
    (tax / "Local" / "config.yaml").write_text("extends: [shared]\n")
    (caps / "local" / "thing" / ".config.yaml").write_text("extends: [shared]\n")
    (caps / "local" / "thing" / "config.yaml").write_text("extends: [shared]\n")
    # The other component's name at each root: never a file this store kept.
    (tax / ".config.yaml").write_text("extends: [shared]\n")
    (caps / "config.yaml").write_text("extends: [shared]\n")

    assert _leftover_lines(FsTaxonomyStore.open(consumer).check()) == []
    assert _leftover_lines(FsCapabilitiesStore.open(consumer).check()) == []


def test_a_directory_with_the_legacy_name_is_not_a_leftover(tmp_path):
    consumer = _federated(tmp_path)
    (consumer / "docs" / "taxonomy" / "config.yaml").mkdir()

    assert _leftover_lines(FsTaxonomyStore.open(consumer).check()) == []


@pytest.mark.parametrize("component,ident", [
    ("taxonomy", "Local"), ("capabilities", "local/thing")])
def test_a_check_scoped_to_one_object_leaves_the_leftover_out(
        tmp_path, component, ident):
    consumer = _federated(tmp_path)
    (consumer / "docs" / component / LEFTOVER[component]).write_text("extends: [shared]\n")
    st = STORE[component].open(consumer)

    assert _leftover_lines(st.check(identifier=ident)) == []
    assert len(_leftover_lines(st.check())) == 1        # the file is there


@pytest.mark.parametrize("component,inherited", [
    ("taxonomy", "shared/Argument"), ("capabilities", "shared/auth")])
def test_following_the_message_makes_check_clean(tmp_path, component, inherited):
    consumer = _federated(tmp_path)
    leftover = consumer / "docs" / component / LEFTOVER[component]
    leftover.write_text("extends:\n  - shared\n")
    assert STORE[component].open(consumer).check() != []

    declare_extends(consumer, component, leftover.read_text())
    leftover.unlink()

    st = STORE[component].open(consumer)
    assert st.check() == []
    assert inherited in {entry.qualified for entry in st.list_all()}


def test_a_node_reached_through_a_symlink_still_gets_a_relative_path(tmp_path):
    """The store root is resolved when it opens, and so is the node root
    (`resolve_store`), so the two compare. Were only one resolved, a node
    opened through a symlinked ancestor would see its own file named by an
    absolute path."""
    consumer = _federated(tmp_path)
    (consumer / "docs" / "taxonomy" / "config.yaml").write_text("extends: [shared]\n")
    link = tmp_path / "via-link"
    link.symlink_to(tmp_path, target_is_directory=True)

    _assert_one_leftover(FsTaxonomyStore.open(link / "consumer").check(), "taxonomy",
                         "docs/taxonomy/config.yaml")


# ── `tcw validate` reports each leftover once per store ──────────────────────

def _check_prefix(component: str) -> str:
    return f"{component} check: "


def test_validate_reports_both_leftovers_once_each(tmp_path):
    consumer = _federated(tmp_path)
    for component, name in LEFTOVER.items():
        (consumer / "docs" / component / name).write_text("extends: [shared]\n")

    problems = validate(consumer)

    assert len(_leftover_lines(problems)) == 2, problems
    for component, name in LEFTOVER.items():
        _assert_one_leftover(problems, component, f"docs/{component}/{name}",
                             _check_prefix(component))


@pytest.mark.parametrize("keep_default_dir", [False, True])
def test_validate_reports_a_moved_stores_leftover_once(tmp_path, keep_default_dir):
    """Without `docs/taxonomy`, `validate` never runs the taxonomy check, so the
    leftover has to be reported directly. With an empty `docs/taxonomy` left
    behind, the check does run — on the moved store — and the direct report
    must then stay out of the way."""
    consumer = _federated(tmp_path)
    shutil.move(str(consumer / "docs" / "taxonomy"), str(consumer / "tax"))
    if keep_default_dir:
        (consumer / "docs" / "taxonomy").mkdir()
    set_component_key(consumer, "taxonomy", "path", "tax")
    (consumer / "tax" / "config.yaml").write_text("extends: [shared]\n")

    _assert_one_leftover(validate(consumer), "taxonomy", "tax/config.yaml",
                         _check_prefix("taxonomy"))


def test_validate_reports_a_leftover_outside_the_node_once(tmp_path):
    consumer = _federated(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    shutil.move(str(consumer / "docs" / "capabilities"), str(elsewhere))
    set_component_key(consumer, "capabilities", "path", str(elsewhere))
    (elsewhere / ".config.yaml").write_text("extends: [shared]\n")

    _assert_one_leftover(validate(consumer), "capabilities",
                         str((elsewhere / ".config.yaml").resolve()),
                         _check_prefix("capabilities"))


def test_an_unparseable_leftover_gets_both_its_parse_error_and_the_report(tmp_path):
    consumer = _federated(tmp_path)
    (consumer / "docs" / "taxonomy" / "config.yaml").write_text("extends: [unclosed\n")

    problems = validate(consumer)

    assert "(component checks skipped: YAML problem above)" in problems, problems
    assert [p for p in problems if p.startswith("docs/taxonomy/config.yaml: ")
            and MARK not in p], problems
    _assert_one_leftover(problems, "taxonomy", "docs/taxonomy/config.yaml",
                         _check_prefix("taxonomy"))


def test_a_yaml_error_elsewhere_does_not_hide_the_leftover(tmp_path):
    consumer = _federated(tmp_path)
    (consumer / "docs" / "taxonomy" / "Local" / "meta.yaml").write_text("name: [unclosed\n")
    (consumer / "docs" / "capabilities" / ".config.yaml").write_text("extends: [shared]\n")

    problems = validate(consumer)

    assert "(component checks skipped: YAML problem above)" in problems, problems
    _assert_one_leftover(problems, "capabilities", "docs/capabilities/.config.yaml",
                         _check_prefix("capabilities"))


def test_validate_names_the_descendant_that_holds_the_leftover(
        tmp_path, monkeypatch, capsys):
    consumer = _federated(tmp_path)
    shared = tmp_path / "shared"
    (shared / "docs" / "taxonomy" / "config.yaml").write_text("extends: []\n")

    monkeypatch.chdir(consumer)
    assert main(["validate"]) == 1
    _assert_one_leftover(capsys.readouterr().err.splitlines(), "taxonomy",
                         "docs/taxonomy/config.yaml",
                         f"[shared] {_check_prefix('taxonomy')}")


def test_a_moved_store_that_cannot_open_is_reported_once_instead(
        tmp_path, monkeypatch, capsys):
    """Opening resolves federation first, so a bad `extends` stops the store
    before any leftover could be looked for. `validate` did not run this
    store's check (no `docs/taxonomy`), so the open failure is its to report —
    once — and the leftover waits until that is fixed."""
    consumer = _federated(tmp_path)
    shutil.move(str(consumer / "docs" / "taxonomy"), str(consumer / "tax"))
    set_component_key(consumer, "taxonomy", "path", "tax")
    declare_extends(consumer, "taxonomy", "extends: [ghost]\n")
    (consumer / "tax" / "config.yaml").write_text("extends: [shared]\n")

    problems = validate(consumer)
    failures = [p for p in problems if p.startswith(_check_prefix("taxonomy"))]
    assert len(failures) == 1, problems
    assert "ghost" in failures[0] and "taxonomy.extends" in failures[0], failures
    assert _leftover_lines(problems) == [], problems

    # The check command refuses too, and says nothing about the leftover. What
    # it does say is not this item's: `find_node` turns any open failure other
    # than a provisioning one into "no tcw taxonomy node here", a separate
    # defect recorded in this item's outcome.
    monkeypatch.chdir(consumer)
    assert main(["taxonomy", "check"]) == 1
    assert MARK not in capsys.readouterr().err


@pytest.mark.parametrize("component,ident", [
    ("taxonomy", "Local"), ("capabilities", "local/thing")])
def test_validating_one_object_leaves_the_leftover_out(tmp_path, component, ident):
    """Both leftovers, so neither the target's own component nor the other one
    can slip in through `validate`'s direct report."""
    consumer = _federated(tmp_path)
    for other, name in LEFTOVER.items():
        (consumer / "docs" / other / name).write_text("extends: [shared]\n")

    assert _leftover_lines(validate(
        consumer, target=ValidationTarget(component, ident))) == []


def test_no_command_touches_the_leftover(tmp_path, monkeypatch, capsys):
    consumer = _federated(tmp_path)
    before = {}
    for component, name in LEFTOVER.items():
        path = consumer / "docs" / component / name
        path.write_bytes(b"# kept by hand\nextends:\n  - shared\n")
        before[path] = path.read_bytes()

    monkeypatch.chdir(consumer)
    for argv in (["taxonomy", "check"], ["capabilities", "check"], ["validate"]):
        assert main(argv) == 1
    capsys.readouterr()

    assert {path: path.read_bytes() for path in before} == before
