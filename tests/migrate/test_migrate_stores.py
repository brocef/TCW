"""The stores' state files converted (TCW-116 Design 4.1, 4.2, 7: C9 to C12;
B7, B8, B11; A1, A2, D7; plan Step 6).

Most cases run `tcw migrate --no-jira` on F-single (`tests/migrate/fixtures.py`)
in both work backends; the blockers each use a small project of their own.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.project_files import version_line
from tests.migrate.fixtures import CAPABILITY_IDS, LONG_FOLDER, build_f_single
from tests.objectcli import tcw  # noqa: F401  (a fixture)

V = version_line()
T, C, W = "docs/taxonomy", "docs/capabilities", "docs/work"


def make(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    return root


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}


@pytest.fixture(params=["jira", "files"])
def migrated(request, tcw, tmp_path):
    root = build_f_single(tmp_path / "app", backend=request.param)
    before = tree(root)
    done = tcw(["migrate", "--no-jira"], root)
    assert done.code == 0, done.err
    return root, before, done


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


# ── C9 to C12 on F-single ─────────────────────────────────────────────────────

def test_each_state_file_is_renamed_with_only_the_listed_edits(migrated):
    root, before, done = migrated
    def old(rel):
        return before[rel].decode()
    # C9 and C10: the version first, the `cap-` id gone, the rest as it was.
    for path, capability_id in CAPABILITY_IDS.items():
        text = old(f"{C}/{path}/meta.yaml")
        assert text.startswith(f"id: {capability_id}\n")
        rest = text.split("\n", 1)[1]
        new = read(root, f"{C}/{path}/tcw-capability.yaml")
        if path == "cli/x/y":                       # C11
            assert new == V + "name: Do Y\nparent: app.capabilities/cli/x\nStatus: Supported\n"
        elif path == "cli/z":                       # C12
            assert new == V + rest + "name: Z\n"
        elif path == "cli/x":                       # C13 (Step 7), C16 (Step 8)
            assert new == V + rest.replace("- camera.md", "- resources/camera.md") \
                .replace("- invoice", "- app.taxonomy/invoice") \
                .replace("'!roles/admin'", "'!app.capabilities/roles/admin'") \
                .replace("- conditions/online", "- app.capabilities/conditions/online")
        else:
            assert new == V + rest, path
        assert not (root / C / path / "meta.yaml").exists()
    # Taxonomy: C11's parent after the name; an `id:` other than the folder's
    # name is left, and reported A1.
    assert read(root, f"{T}/invoice/tcw-taxonomy.yaml") == V + old(f"{T}/invoice/meta.yaml")
    assert read(root, f"{T}/invoice/line/tcw-taxonomy.yaml") == V + (
        "name: Line\nparent: app.taxonomy/invoice\nkind: Vocabulary\nrelatesTo:\n"
        "- app.taxonomy/invoice\n")
    assert read(root, f"{T}/order/tcw-taxonomy.yaml") == V + old(f"{T}/order/meta.yaml")
    assert "  A1 docs/taxonomy/order/tcw-taxonomy.yaml: id 'other' is not its folder's " \
           "name, 'order'" in done.err
    # Work items, in either backend: renamed, the version first.
    items = [rel for rel in before if rel.startswith(W) and rel.endswith("/item.yaml")]
    assert len(items) == 2
    for rel in items:
        new = rel.replace("/item.yaml", "/tcw-work-item.yaml")
        assert read(root, new).startswith(V)
        assert not (root / rel).exists()


def test_a_folder_alone_becomes_a_term_and_missing_descriptions_are_written(migrated):
    root, _, done = migrated
    assert read(root, f"{T}/customer/tcw-taxonomy.yaml") == V + "name: Customer\n"
    assert read(root, f"{T}/customer/description.md") == ""
    assert read(root, f"{C}/cli/z/description.md") == ""
    for where in (f"{T}/customer/tcw-taxonomy.yaml", f"{T}/customer/description.md",
                  f"{C}/cli/z/description.md"):
        assert f"  D7 {where}:" in done.err, where
    assert "write docs/taxonomy/customer/tcw-taxonomy.yaml: C11, C12" in done.err


def test_every_cap_id_is_recorded_with_its_id_path(migrated):
    root, _, _ = migrated
    text = read(root, ".tcw/tcw-migration.yaml")
    assert text.startswith(V)
    record = yaml.safe_load(text)
    assert record["capability-ids"] == {v: k for k, v in CAPABILITY_IDS.items()}
    assert set(record) == {"tcw-version", "capability-ids"}
    for path in CAPABILITY_IDS:
        assert "cap-" not in read(root, f"{C}/{path}/tcw-capability.yaml")


def test_a_state_file_under_resources_is_reported_and_left(migrated):
    root, before, done = migrated
    rel = f"{C}/cli/v/resources/meta.yaml"
    assert (root / rel).read_bytes() == before[rel]
    assert f"  A2 {rel}: " in done.err
    assert not (root / C / "cli/v/resources/tcw-capability.yaml").exists()


def test_no_folder_and_parent_warning_after_the_run(migrated, tcw):
    root, _, _ = migrated
    found = tcw(["validate"], root)
    assert "sits in the folder of" not in found.out + found.err


def test_the_record_is_written_first(tcw, tmp_path):
    root = build_f_single(tmp_path / "app")
    done = tcw(["migrate", "--no-jira", "--dry-run"], root)
    said = done.err.splitlines()
    assert said[:2] == ["would write .tcw/tcw-migration.yaml: C10",
                        "would write .tcw/.gitignore: C1"]


# ── objects in either form ───────────────────────────────────────────────────

def test_a_4_0_object_is_left_and_still_counts_as_an_enclosing_one(tcw, tmp_path):
    app = make(tmp_path / "app", {
        "tcw-config.yaml": "id: app\n",
        f"{C}/cli/tcw-capability.yaml": V + "name: Cli\nStatus: Supported\n",
        f"{C}/cli/description.md": "Cli.\n",
        f"{C}/cli/sub/meta.yaml": "id: cap-1a2b3c\nname: Sub\nStatus: Supported\n",
        f"{C}/cli/sub/description.md": "Sub.\n"})
    before = tree(app)
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    after = tree(app)
    assert after[f"{C}/cli/tcw-capability.yaml"] == before[f"{C}/cli/tcw-capability.yaml"]
    assert after[f"{C}/cli/sub/tcw-capability.yaml"].decode() == \
        V + "name: Sub\nparent: app.capabilities/cli\nStatus: Supported\n"


def test_an_equal_state_pair_keeps_the_4_0_file(tcw, tmp_path):
    four = V + "# kept\nname: Sub\nStatus: Supported\n"
    app = make(tmp_path / "app", {
        "tcw-config.yaml": "id: app\n",
        f"{C}/sub/meta.yaml": "id: cap-1a2b3c\nname: Sub\nStatus: Supported\n",
        f"{C}/sub/tcw-capability.yaml": four,
        f"{C}/sub/description.md": "Sub.\n"})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    files = tree(app)
    assert files[f"{C}/sub/tcw-capability.yaml"] == four.encode()
    assert f"{C}/sub/meta.yaml" not in files
    assert yaml.safe_load(files[".tcw/tcw-migration.yaml"])["capability-ids"] == \
        {"cap-1a2b3c": "sub"}


def test_a_differing_state_pair_is_b11(tcw, tmp_path):
    app = make(tmp_path / "app", {
        "tcw-config.yaml": "id: app\n",
        f"{C}/sub/meta.yaml": "id: cap-1a2b3c\nname: Sub\nStatus: Supported\n",
        f"{C}/sub/tcw-capability.yaml": V + "name: Other\nStatus: Supported\n",
        f"{C}/sub/description.md": "Sub.\n"})
    before = tree(app)
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert "B11 docs/capabilities/sub/meta.yaml: differs from " \
           "docs/capabilities/sub/tcw-capability.yaml at name" in done.err
    assert tree(app) == before


# ── B8 and B7, before anything is written ────────────────────────────────────

@pytest.mark.parametrize("files, said", [
    ({f"{T}/has.dot/meta.yaml": "name: Dot\n"},
     "B8 docs/taxonomy/has.dot: the id-part 'has.dot' breaks the rule"),
    ({f"{T}/resources/meta.yaml": "name: R\n"},
     "B8 docs/taxonomy/resources: 'resources' is reserved in the taxonomy store"),
    ({f"{W}/{LONG_FOLDER}/item.yaml": "title: Long\nstage: inbox\n"},
     f"B8 docs/work/{LONG_FOLDER}: app.work/{LONG_FOLDER} is 256 characters"),
])
def test_a_name_4_0_cannot_take_is_b8(tcw, tmp_path, files, said):
    app = make(tmp_path / "app", {"tcw-config.yaml": "id: app\n", **files})
    before = tree(app)
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert said in done.err
    assert tree(app) == before


def test_one_store_inside_another_is_b7(tcw, tmp_path):
    app = make(tmp_path / "app", {
        "tcw-config.yaml": "id: app\ntaxonomy:\n  path: docs/caps/terms\n"
                           "capabilities:\n  path: docs/caps\n",
        "docs/caps/terms/x/meta.yaml": "name: X\n"})
    before = tree(app)
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert "B7 docs/caps/terms: the taxonomy store is inside the capabilities store " \
           "docs/caps" in done.err
    assert tree(app) == before


def test_in_a_4_0_project_a_bare_taxonomy_folder_stays_an_organising_one(tcw, tmp_path):
    """A branch merged after the migration brings back one 3.x term inside
    an organising folder; the folder does not become a term."""
    app = make(tmp_path / "app", {
        ".tcw/tcw-config.yaml": V + "id: app\n",
        f"{T}/domain/x/meta.yaml": "name: X\nkind: Vocabulary\n",
        f"{T}/domain/x/description.md": "X.\n"})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    files = tree(app)
    assert files[f"{T}/domain/x/tcw-taxonomy.yaml"].decode() == \
        V + "name: X\nkind: Vocabulary\n"
    assert not any(rel.startswith(f"{T}/domain/") and rel.count("/") == 3 for rel in files)


# ── C13: loose entries into resources/ (plan Step 7) ─────────────────────────

def test_loose_entries_move_into_resources_with_their_bytes(migrated):
    root, before, done = migrated
    item = sorted(rel.split("/")[2] for rel in before if rel.startswith(W) and
                  rel.endswith("/design.md"))[0]
    moved = {f"{W}/{item}/design.md": f"{W}/{item}/resources/design.md",
             f"{C}/cli/x/camera.md": f"{C}/cli/x/resources/camera.md"}
    if item == "APP-1-a":
        moved[f"{W}/APP-1-a/notes/one.md"] = f"{W}/APP-1-a/resources/notes/one.md"
    for old, new in moved.items():
        assert not (root / old).exists()
        assert (root / new).read_bytes() == before[old]
    assert f"move {W}/{item}/design.md -> {W}/{item}/resources/design.md: C13" in done.err
    # Fixed folders and files stay where they are.
    assert all((root / rel).exists() for rel in before
               if rel.startswith(W) and ("/spec/" in rel or "/request/" in rel))


def test_a_prepended_document_is_found_in_resources(migrated, tcw):
    import json
    root, _, done = migrated
    text = read(root, f"{C}/cli/x/tcw-capability.yaml")
    assert "prependedDocs:\n- resources/camera.md\n" in text
    assert f"write {C}/cli/x/tcw-capability.yaml: C9, C10, C13, C16" in done.err
    shown = tcw(["capabilities", "show", "cli/x", "--json"], root)
    assert shown.code == 0, shown.err
    assert json.loads(shown.out)["capability"]["body"].startswith("The camera is on.")


def test_exact_mentions_are_rewritten_and_shortened_ones_reported(tcw, tmp_path):
    root = build_f_single(tmp_path / "app")
    readme = (root / "README.md").read_bytes()
    done = tcw(["migrate", "--no-jira"], root)
    assert done.code == 0, done.err
    spec = read(root, f"{W}/APP-2-b/spec/spec.md")
    assert "The design is in docs/work/APP-1-a/resources/design.md, and" in spec
    assert "Shortened, it is APP-1-…/design.md or APP-1-.../design.md." in spec
    a3 = [line for line in done.err.splitlines() if line.startswith("  A3")]
    assert a3 == [
        f"  A3 {W}/APP-2-b/spec/spec.md:4: names APP-1-…/design.md, which moved to "
        f"{W}/APP-1-a/resources/design.md; only the path in full is rewritten",
        f"  A3 {W}/APP-2-b/spec/spec.md:4: names APP-1-.../design.md, which moved to "
        f"{W}/APP-1-a/resources/design.md; only the path in full is rewritten"]
    assert f"write {W}/APP-2-b/spec/spec.md: C13, C16" in done.err
    assert (root / "README.md").read_bytes() == readme


def test_a_relative_link_beside_the_moved_file_is_rewritten(tcw, tmp_path):
    app = make(tmp_path / "app", {
        "tcw-config.yaml": "id: app\n",
        f"{C}/x/meta.yaml": "id: cap-1a2b3c\nname: X\nStatus: Supported\n"
                            "appendedDocs: [./notes.md, resources/kept.md]\n",
        f"{C}/x/description.md": "See [the notes](notes.md) and [kept](resources/kept.md).\n",
        f"{C}/x/notes.md": "Notes.\n",
        f"{C}/x/resources/kept.md": "Kept.\n"})
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert read(app, f"{C}/x/description.md") == \
        "See [the notes](resources/notes.md) and [kept](resources/kept.md).\n"
    assert "appendedDocs: [resources/notes.md, resources/kept.md]\n" in \
        read(app, f"{C}/x/tcw-capability.yaml")
    assert read(app, f"{C}/x/resources/notes.md") == "Notes.\n"
