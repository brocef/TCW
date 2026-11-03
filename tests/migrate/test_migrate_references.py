"""References within the project rewritten to full identifiers (TCW-116
Design 4.1, C16; B10; criteria 41 and 62; plan Steps 8 and 22).

One small project per row of TCW-110 Design 5.1's table, each run with
`tcw migrate`; then F-single, whose references all name its own objects.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.project_files import version_line
from tests.migrate.fixtures import build_f_single
from tests.objectcli import tcw  # noqa: F401  (a fixture)

V = version_line()
T, C, W = "docs/taxonomy", "docs/capabilities", "docs/work"
FILES = "id: app\nwork:\n  backend: filesystem\n"


def make(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    return root


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


BASE = {
    f"{T}/invoice/meta.yaml": "name: Invoice\nkind: Vocabulary\n",
    f"{T}/invoice/description.md": "An invoice.\n",
    f"{C}/roles/admin/meta.yaml": "id: cap-6f7081\nname: Admin\nStatus: Supported\n",
    f"{C}/roles/admin/description.md": "Admin.\n",
    f"{C}/conditions/online/meta.yaml": "id: cap-708192\nname: Online\nStatus: Supported\n",
    f"{C}/conditions/online/description.md": "Online.\n",
    f"{C}/cli/old/meta.yaml": "id: cap-1a2b3c\nname: Old\nStatus: Supported\n",
    f"{C}/cli/old/description.md": "Old.\n",
    f"{W}/2026-10-01-a/item.yaml": "title: A\nstage: inbox\n",
}


@pytest.mark.parametrize("rel, text, expected", [
    # A work item's parent and blocked-by (files backend).
    (f"{W}/2026-10-02-b/item.yaml",
     "title: B\nstage: inbox\nparent: app/2026-10-01-a\nblocked-by:\n- app/2026-10-01-a\n",
     "title: B\nstage: inbox\nparent: app.work/2026-10-01-a\nblocked-by:\n"
     "- app.work/2026-10-01-a\n"),
    # A term's relatesTo and vocabulary.
    (f"{T}/line/meta.yaml",
     "name: Line\nkind: Vocabulary\nrelatesTo: [invoice]\nvocabulary:\n- invoice\n",
     "name: Line\nkind: Vocabulary\nrelatesTo: [app.taxonomy/invoice]\nvocabulary:\n"
     "- app.taxonomy/invoice\n"),
    # A capability's six fields, `!` and the roles/ and conditions/ paths kept.
    (f"{C}/cli/x/meta.yaml",
     "name: X\nStatus: Supported\nSubject: invoice, invoice\nFeature: invoice\n"
     "Superseded by: cli/old\nBlocked by: 'cli/old'\nRoles:\n- '!roles/admin'\n"
     "When: [conditions/online, '!conditions/online']\n",
     "name: X\nStatus: Supported\nSubject: app.taxonomy/invoice, app.taxonomy/invoice\n"
     "Feature: app.taxonomy/invoice\nSuperseded by: app.capabilities/cli/old\n"
     "Blocked by: 'app.capabilities/cli/old'\nRoles:\n- '!app.capabilities/roles/admin'\n"
     "When: [app.capabilities/conditions/online, '!app.capabilities/conditions/online']\n"),
])
def test_each_field_of_a_state_file(tcw, tmp_path, rel, text, expected):
    app = make(tmp_path / "app", {"tcw-config.yaml": FILES, **BASE, rel: text})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    new = rel.replace("meta.yaml", "tcw-taxonomy.yaml" if rel.startswith(T)
                      else "tcw-capability.yaml").replace("item.yaml", "tcw-work-item.yaml")
    assert read(app, new) == V + expected
    assert "C16" in next(line for line in done.err.splitlines()
                         if line.startswith(f"write {new}"))


def test_each_entry_of_an_items_capabilities_file(tcw, tmp_path):
    rel = f"{W}/2026-10-01-a/capabilities.yaml"
    text = ("new:\n- cli/not-yet\nchanged: [cli/old]\nremoved:\n- cli/old\n"
            "taxonomy:\n  new:\n  - invoice\n  changed: []\n")
    app = make(tmp_path / "app", {"tcw-config.yaml": FILES, **BASE, rel: text})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert read(app, rel) == (
        "new:\n- app.capabilities/cli/not-yet\nchanged: [app.capabilities/cli/old]\n"
        "removed:\n- app.capabilities/cli/old\ntaxonomy:\n  new:\n"
        "  - app.taxonomy/invoice\n  changed: []\n")
    assert f"write {rel}: C16" in done.err.splitlines()


def test_a_link_outside_code_is_rewritten_and_one_inside_is_not(tcw, tmp_path):
    rel = f"{C}/cli/old/description.md"
    text = ("See [x](tcw://C/cli/old), [t](tcw://T/invoice), [w](tcw://W/2026-10-01-a)\n"
            "and [w2](tcw://W/app/2026-10-01-a) and [done](tcw://app.capabilities/cli/old).\n"
            "In code: `[x](tcw://C/cli/old)`.\n\n```\n[x](tcw://C/cli/old)\n```\n")
    app = make(tmp_path / "app", {"tcw-config.yaml": FILES, **BASE, rel: text})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert read(app, rel) == (
        "See [x](tcw://app.capabilities/cli/old), [t](tcw://app.taxonomy/invoice), "
        "[w](tcw://app.work/2026-10-01-a)\n"
        "and [w2](tcw://app.work/2026-10-01-a) and [done](tcw://app.capabilities/cli/old).\n"
        "In code: `[x](tcw://C/cli/old)`.\n\n```\n[x](tcw://C/cli/old)\n```\n")
    assert f"write {rel}: C16" in done.err.splitlines()


def test_f_single_names_its_own_objects(tcw, tmp_path):
    root = build_f_single(tmp_path / "app")
    done = tcw(["migrate", "--no-jira"], root)
    assert done.code == 0, done.err
    x = yaml.safe_load(read(root, f"{C}/cli/x/tcw-capability.yaml"))
    assert x["Subject"] == ["app.taxonomy/invoice"]
    assert x["Roles"] == ["!app.capabilities/roles/admin"]
    assert x["When"] == ["app.capabilities/conditions/online"]
    assert yaml.safe_load(read(root, f"{T}/invoice/line/tcw-taxonomy.yaml"))["relatesTo"] \
        == ["app.taxonomy/invoice"]
    assert yaml.safe_load(read(root, f"{W}/APP-1-a/capabilities.yaml")) == {
        "new": ["app.capabilities/cli/new-thing"], "changed": ["app.capabilities/cli/x"],
        "taxonomy": {"new": ["app.taxonomy/invoice"]}}
    spec = read(root, f"{W}/APP-2-b/spec/spec.md")
    assert "[the capability](tcw://app.capabilities/cli/x)" in spec
    assert "`[the capability](tcw://C/cli/x)`" in spec
    assert f"write {W}/APP-2-b/spec/spec.md: C13, C16" in done.err.splitlines()


def test_files_backend_f_single_converts_its_parent_and_blocked_by(tcw, tmp_path):
    root = build_f_single(tmp_path / "app", backend="files")
    done = tcw(["migrate"], root)
    assert done.code == 0, done.err
    item = yaml.safe_load(read(root, f"{W}/2026-10-02-b/tcw-work-item.yaml"))
    assert item["parent"] == "app.work/2026-10-01-a"
    assert item["blocked-by"] == ["app.work/2026-10-01-a"]


# ── criterion 62: a branch brings 3.x files back ─────────────────────────────

def test_only_the_3x_files_a_branch_brought_back_convert(tcw, tmp_path):
    app = make(tmp_path / "app", {
        ".tcw/tcw-config.yaml": V + FILES,
        f"{T}/invoice/tcw-taxonomy.yaml": V + "name: Invoice\n",
        f"{T}/invoice/description.md": "An invoice.\n",
        f"{W}/2026-10-01-a/tcw-work-item.yaml": V + "title: A\nstage: inbox\n",
        f"{C}/cli/back/meta.yaml": "id: cap-1a2b3c\nname: Back\nStatus: Supported\n"
                                   "Subject: [invoice]\n",
        f"{C}/cli/back/description.md": "Back.\n",
        f"{W}/2026-10-02-b/item.yaml": "title: B\nstage: inbox\nblocked-by:\n"
                                       "- app/2026-10-01-a\n"})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    changed = sorted(line for line in done.err.splitlines() if line.startswith("write"))
    assert changed == [
        "write .tcw/.gitignore: C1",
        "write .tcw/tcw-migration.yaml: C10",
        f"write {C}/cli/back/tcw-capability.yaml: C9, C10, C16",
        f"write {W}/2026-10-02-b/tcw-work-item.yaml: C9, C16"]
    assert yaml.safe_load(read(app, f"{C}/cli/back/tcw-capability.yaml"))["Subject"] == \
        ["app.taxonomy/invoice"]
    assert yaml.safe_load(read(app, f"{W}/2026-10-02-b/tcw-work-item.yaml"))[
        "blocked-by"] == ["app.work/2026-10-01-a"]


# ── what one project cannot convert yet, or at all ───────────────────────────

def test_a_capabilities_entry_with_no_ledger_is_b10(tcw, tmp_path):
    app = make(tmp_path / "app", {
        "tcw-config.yaml": FILES,
        f"{W}/2026-10-01-a/item.yaml": "title: A\nstage: inbox\n",
        f"{W}/2026-10-01-a/capabilities.yaml": "new:\n- cli/x\n"})
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert ("B10 docs/work/2026-10-01-a/capabilities.yaml: cli/x: this project ('app') "
            "keeps no capabilities ledger; qualify the path with a child project id "
            "(it declares no child projects)") in done.err


# ── references owned by another project (plan Step 22) ──────────────────────

CORE = {"tcw-config.yaml": "id: core\n",
        f"{T}/auth/meta.yaml": "name: Auth\nkind: Vocabulary\n",
        f"{C}/auth/login/meta.yaml": "id: cap-aaa111\nname: Login\nStatus: Supported\n"}
EXTENDS = ("id: app\nwork:\n  backend: filesystem\nprojects:\n  upstream:\n"
           "    core: ../core\ntaxonomy:\n  extends:\n  - core\ncapabilities:\n"
           "  extends:\n  - core\n")


def migrated(tcw, root: Path):
    done = tcw(["migrate", "--no-jira"], root)
    assert done.code == 0, done.err
    return done


def own_state(root: Path, rel: str) -> dict:
    return yaml.safe_load(read(root, rel))


def test_bare_and_prefixed_paths_name_the_source_that_has_them(tcw, tmp_path):
    make(tmp_path / "core", CORE)
    app = make(tmp_path / "app", {
        "tcw-config.yaml": EXTENDS,
        f"{C}/cli/x/meta.yaml": "name: X\nStatus: Supported\nSubject:\n- core/auth\n"
                                 "- billing\nBlocked by: auth/login\n",
        f"{C}/cli/x/description.md": "See [login](tcw://C/auth/login) and "
                                      "[auth](tcw://T/auth).\n",
        f"{T}/billing/meta.yaml": "name: Billing\nkind: Vocabulary\n"})
    migrated(tcw, app)
    data = own_state(app, f"{C}/cli/x/tcw-capability.yaml")
    assert data["Subject"] == ["core.taxonomy/auth", "app.taxonomy/billing"]
    assert data["Blocked by"] == "core.capabilities/auth/login"
    assert read(app, f"{C}/cli/x/description.md") == (
        "See [login](tcw://core.capabilities/auth/login) and "
        "[auth](tcw://core.taxonomy/auth).\n")


def test_a_capabilities_yaml_entry_is_routed_as_3_x_routed_it(tcw, tmp_path):
    make(tmp_path / "core", CORE)
    make(tmp_path / "kid", {"tcw-config.yaml": "id: kid\n"})
    app = make(tmp_path / "app", {
        "tcw-config.yaml": EXTENDS.replace("  upstream:", "  children:\n    kid: ../kid\n"
                                                         "  upstream:"),
        f"{C}/cli/x/meta.yaml": "name: X\nStatus: Supported\n",
        f"{W}/2026-10-01-a/item.yaml": "title: A\nstage: inbox\n",
        f"{W}/2026-10-01-a/capabilities.yaml": "new:\n- cli/y\nchanged:\n- kid/cli/z\n"
                                                "- core/auth/login\n- cli/x\n"
                                                "taxonomy:\n  changed:\n  - auth\n"
                                                "  new:\n  - fresh\n"})
    migrated(tcw, app)
    data = own_state(app, f"{W}/2026-10-01-a/capabilities.yaml")
    assert data == {"new": ["app.capabilities/cli/y"],
                    "changed": ["kid.capabilities/cli/z", "core.capabilities/auth/login",
                                "app.capabilities/cli/x"],
                    "taxonomy": {"changed": ["core.taxonomy/auth"],
                                 "new": ["app.taxonomy/fresh"]}}


# ── a taxonomy: entry prefixed with a child (TCW-119) ───────────────────────

A_CONFIG = "id: a\nwork:\n  backend: filesystem\nprojects:\n  children:\n    b: ../B\n"
A_ITEM = f"{W}/2026-10-01-a/capabilities.yaml"
A_ITEM_TEXT = ("changed:\n- b/cli/x\ntaxonomy:\n  changed:\n  - b/turn\n  new:\n"
               "  - b/never\n")
B_ITEM = f"{W}/2026-10-02-b/capabilities.yaml"


def family(tmp_path: Path, a_extra: dict[str, str], a_config: str) -> tuple[Path, Path]:
    """The spec's Reproduction: a parent `A` (3.x) listing a child `b` at
    `../B`, with an unfinished item declaring `b/…` entries and a completed
    one; and `B`, which has the term `turn` and the capability `cli/x`.
    `a_config` is `A`'s whole configuration, never defaulted, since what it
    lists (children, sources) is what the routing branches on."""
    a = make(tmp_path / "A", {
        "tcw-config.yaml": a_config,
        f"{W}/2026-10-01-a/item.yaml": "title: A\nstage: inbox\n",
        A_ITEM: A_ITEM_TEXT,
        f"{W}/2026-10-02-b/item.yaml": "title: B\nstage: completed\n",
        B_ITEM: "taxonomy:\n  removed:\n  - b/turn\n",
        **a_extra})
    b = make(tmp_path / "B", {
        "tcw-config.yaml": "id: b\nprojects:\n  parent:\n    a: ../A\n",
        f"{T}/turn/meta.yaml": "name: Turn\nkind: Vocabulary\n",
        f"{T}/turn/description.md": "A turn.\n",
        f"{C}/cli/x/meta.yaml": "id: cap-123abc\nname: X\nStatus: Supported\n",
        f"{C}/cli/x/description.md": "X.\n"})
    return a, b


def _assert_refused_unwritten(done, a: Path, line: str) -> None:
    """The run is B10 with exactly `line`, and wrote nothing."""
    assert done.code == 3, (done.out, done.err)
    assert line in done.err
    assert (a / "tcw-config.yaml").is_file()
    assert not (a / ".tcw").exists()
    assert read(a, A_ITEM) == A_ITEM_TEXT


def test_a_taxonomy_entry_prefixed_with_a_child_names_the_child_s_term(tcw, tmp_path):
    a, b = family(tmp_path, {}, A_CONFIG)
    done = tcw(["migrate"], a)
    assert done.code == 0, done.err
    assert "write docs/work/2026-10-01-a/capabilities.yaml: C16" in done.err.splitlines()
    assert "a.taxonomy/b/" not in read(a, A_ITEM) + read(a, B_ITEM)
    assert own_state(a, A_ITEM) == {"changed": ["b.capabilities/cli/x"],
                                    "taxonomy": {"changed": ["b.taxonomy/turn"],
                                                 "new": ["b.taxonomy/never"]}}
    assert own_state(a, B_ITEM) == {"taxonomy": {"removed": ["b.taxonomy/turn"]}}
    assert tcw(["migrate"], b).code == 0
    found = tcw(["validate"], a)
    assert found.code == 0, (found.out, found.err)
    assert not [line for line in (found.out + found.err).splitlines()
                if "capabilities.yaml" in line]


def test_a_taxonomy_entry_the_parent_s_own_taxonomy_holds_keeps_3x_reading(tcw, tmp_path):
    # Only the held entry: `b/never` beside it is not held, and `b` is now a
    # folder of A's taxonomy, so it would be B10 (the case below).
    a, _ = family(tmp_path, {f"{T}/b/turn/meta.yaml": "name: Turn\nkind: Vocabulary\n",
                             f"{T}/b/turn/description.md": "A turn.\n",
                             A_ITEM: "taxonomy:\n  changed:\n  - b/turn\n"}, A_CONFIG)
    migrated(tcw, a)
    assert own_state(a, A_ITEM)["taxonomy"]["changed"] == ["a.taxonomy/b/turn"]


def test_a_taxonomy_entry_whose_child_is_also_a_taxonomy_folder_is_b10(tcw, tmp_path):
    a, _ = family(tmp_path, {f"{T}/b/other/meta.yaml": "name: Other\nkind: Vocabulary\n",
                             f"{T}/b/other/description.md": "Other.\n"}, A_CONFIG)
    _assert_refused_unwritten(
        tcw(["migrate"], a), a,
        "B10 docs/work/2026-10-01-a/capabilities.yaml: b/turn: ambiguous — 'b' is both "
        "a child project of this project and a namespace in this project's taxonomy; "
        "write it as 'b.taxonomy/turn' or 'a.taxonomy/b/turn', then run 'tcw migrate' "
        "again")


def test_a_taxonomy_entry_whose_child_is_a_folder_of_an_inherited_taxonomy_is_b10(
        tcw, tmp_path):
    make(tmp_path / "lib", {"tcw-config.yaml": "id: lib\n",
                            f"{T}/b/other/meta.yaml": "name: Other\nkind: Vocabulary\n",
                            f"{T}/b/other/description.md": "Other.\n"})
    a, _ = family(tmp_path, {}, A_CONFIG + "  upstream:\n    lib: ../lib\n"
                                           "taxonomy:\n  extends:\n  - lib\n")
    done = tcw(["migrate"], a)
    _assert_refused_unwritten(
        done, a,
        "B10 docs/work/2026-10-01-a/capabilities.yaml: b/turn: ambiguous — 'b' is both "
        "a child project of this project and a namespace in the taxonomy it inherits "
        "from 'lib'; write it as 'b.taxonomy/turn' or 'lib.taxonomy/b/turn', then run "
        "'tcw migrate' again")
    assert "'a.taxonomy/b/turn'" not in done.err


def test_a_capability_subject_prefixed_with_a_child_is_not_routed(tcw, tmp_path):
    a, _ = family(tmp_path, {f"{C}/cli/y/meta.yaml": "name: Y\nStatus: Supported\n"
                                                     "Subject: [b/turn]\n",
                             f"{C}/cli/y/description.md": "Y.\n"}, A_CONFIG)
    migrated(tcw, a)
    assert own_state(a, f"{C}/cli/y/tcw-capability.yaml")["Subject"] == \
        ["a.taxonomy/b/turn"]


def test_a_cross_project_blocked_by_names_that_project_s_item(tcw, tmp_path):
    """3.x's `--blocks` wrote `<project>/<folder>` for another project's item."""
    app = make(tmp_path / "app", {
        "tcw-config.yaml": FILES,
        f"{W}/2026-10-02-b/item.yaml": "title: B\nstage: inbox\nblocked-by:\n"
                                       "- other/2026-10-01-x\n",
        f"{W}/2026-10-02-b/notes.md": "After [x](tcw://W/other/2026-10-01-x).\n"})
    migrated(tcw, app)
    assert own_state(app, f"{W}/2026-10-02-b/tcw-work-item.yaml")["blocked-by"] == \
        ["other.work/2026-10-01-x"]
    assert read(app, f"{W}/2026-10-02-b/resources/notes.md") == \
        "After [x](tcw://other.work/2026-10-01-x).\n"


def test_a_reference_to_an_override_a_source_moved_names_its_new_path(tcw, tmp_path):
    make(tmp_path / "lib", {"tcw-config.yaml": "id: lib\n",
                            f"{C}/auth/login/meta.yaml": "id: cap-aaa111\nname: Login\n"
                                                          "Status: Supported\n"})
    core = make(tmp_path / "core", {
        "tcw-config.yaml": "id: core\nprojects:\n  upstream:\n    lib: ../lib\n"
                           "capabilities:\n  extends:\n  - lib\n",
        f"{C}/ov/login/meta.yaml": "Status: Experimental\noverrides: cap-aaa111\n"})
    migrated(tcw, core)
    app = make(tmp_path / "app", {
        "tcw-config.yaml": EXTENDS,
        f"{C}/cli/x/meta.yaml": "name: X\nStatus: Supported\nBlocked by: core/ov/login\n"})
    make(tmp_path / "core", {f"{T}/auth/meta.yaml": "name: Auth\nkind: Vocabulary\n"})
    migrated(tcw, app)
    assert own_state(app, f"{C}/cli/x/tcw-capability.yaml")["Blocked by"] == \
        "core.capabilities/auth/login"


def test_a_bare_reference_two_sources_have_is_b10(tcw, tmp_path):
    make(tmp_path / "core", CORE)
    make(tmp_path / "lib", {**CORE, "tcw-config.yaml": "id: lib\n"})
    app = make(tmp_path / "app", {
        "tcw-config.yaml": EXTENDS.replace("    core: ../core\n",
                                           "    core: ../core\n    lib: ../lib\n")
                                  .replace("  - core\n", "  - core\n  - lib\n"),
        f"{C}/cli/x/meta.yaml": "name: X\nStatus: Supported\nBlocked by: auth/login\n"})
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 3
    assert (f"  B10 {C}/cli/x/meta.yaml: Blocked by: auth/login is in more than one "
            f"project this one inherits from (core, lib), and TCW 3 refused it") in done.err


# ── A prefix 3.x resolved through a source's own taxonomy extends ───────────

def term(name: str) -> dict[str, str]:
    return {f"{T}/{name}/meta.yaml": f"name: {name}\nkind: Vocabulary\n"}


def chain_family(base: Path, depth: int) -> dict[str, Path]:
    """A root `r` with nothing of its own; a library `l`; `depth` projects
    `m1`, ..., each the next one's parent, `m1` extending `l` and each other
    the one above it; and `kid`, extending the last, which reaches `l`'s
    terms through `depth` taxonomy `extends`. Each project but `r` has one
    term of its own."""
    roots = {"r": make(base, {"tcw-config.yaml": "id: r\nprojects:\n  children:\n"
                                                 "    l: l\n    m1: m1\n"})}
    roots["l"] = make(base / "l", {"tcw-config.yaml": "id: l\nprojects:\n  parent:\n"
                                                       "    r: ..\n",
                                   **term("lib-term")})
    above, folder = "r", base
    for n in range(1, depth + 1):
        pid, nxt = f"m{n}", (f"m{n - 1}" if n > 1 else "l")
        folder = folder / pid
        child = f"m{n + 1}" if n < depth else "kid"
        roots[pid] = make(folder, {
            "tcw-config.yaml": f"id: {pid}\nprojects:\n  parent:\n    {above}: ..\n"
                               f"  children:\n    {child}: {child}\n"
                               f"taxonomy:\n  extends:\n  - {nxt}\n",
            **term(f"term-{n}")})
        above = pid
    roots["kid"] = make(folder / "kid", {
        "tcw-config.yaml": f"id: kid\nprojects:\n  parent:\n    {above}: ..\n"
                           f"taxonomy:\n  extends:\n  - {above}\n",
        **term("own-term"),
        f"{T}/check/meta.yaml": (
            "name: Check\nkind: Feature\n"
            f"vocabulary:\n- {above}/term-{depth}\n- own-term\n"
            "- l/lib-term\n"
            f"relatesTo:\n- {above}/term-{depth}\n- own-term\n"
            "- l/lib-term\n")})
    return roots


@pytest.mark.parametrize("depth", [1, 3])
@pytest.mark.parametrize("migrated_first", [False, True])
def test_a_prefix_3_x_reached_through_a_source_s_extends_names_that_project(
        tcw, tmp_path, depth, migrated_first):
    """3.x's taxonomy `get` took a first folder naming any project its
    `extends` reached, through each source's own (`_inherited_stores`), as
    that project's; so does C16, whether those projects are still 3.x or
    already migrated."""
    fam = chain_family(tmp_path / "r", depth)
    if migrated_first:
        for pid in ("r", "l", *[f"m{n}" for n in range(1, depth + 1)]):
            migrated(tcw, fam[pid])
    migrated(tcw, fam["kid"])
    data = own_state(fam["kid"], f"{T}/check/tcw-taxonomy.yaml")
    above = f"m{depth}"
    expected = [f"{above}.taxonomy/term-{depth}", "kid.taxonomy/own-term",
                "l.taxonomy/lib-term"]
    assert data["vocabulary"] == expected
    assert data["relatesTo"] == expected
    if migrated_first:
        found = tcw(["validate"], fam["kid"])
        assert found.code == 0, (found.out, found.err)
