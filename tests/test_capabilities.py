import hashlib
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import AmbiguousRef, RefError, Term
from tcw.store.fs import FsCapabilitiesStore, heading_slug, write_sentinel


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    (root / "docs" / "capabilities").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root, name)          # mark it a node for CLI (find_node) tests
    return root


def connect(parent: Path, child: Path) -> None:
    (parent / "tcw-config.yaml").write_text(
        f"id: {parent.name}\nconnected-projects:\n  children:\n"
        f"    {child.name}: ../{child.name}\n"
    )
    (child / "tcw-config.yaml").write_text(
        f"id: {child.name}\nconnected-projects:\n  parent:\n"
        f"    {parent.name}: ../{parent.name}\n"
    )


def write_cap(root: Path, path: str, body: str = "", **meta) -> None:
    """Write a folder-model capability node (meta.yaml + description.md)."""
    d = root / "docs" / "capabilities" / path
    d.mkdir(parents=True, exist_ok=True)
    m = {"id": "cap-" + hashlib.sha1(path.encode()).hexdigest()[:6],
         "name": path.rsplit("/", 1)[-1].replace("-", " ").title()}
    m.update(meta)
    (d / "meta.yaml").write_text(yaml.safe_dump(m, sort_keys=False, allow_unicode=True))
    (d / "description.md").write_text(body)


class StubTax:
    """Minimal TaxonomyStore for the cross-component Subject check."""
    def __init__(self, *known):
        self.known = set(known)

    def get(self, ref):
        return object() if ref in self.known else None


class FeatureTax:
    def __init__(self):
        self.terms = {
            "user": Term("user", "User", kind="Vocabulary"),
            "user-authentication": Term("user-authentication", "User Authentication",
                                        kind="Feature", vocabulary=["user"]),
        }

    def get(self, ref):
        return self.terms.get(ref)


def test_cli_path_prints_resolved_store_root_and_reserves_command(tmp_path, monkeypatch,
                                                                  capsys):
    from tcw.cli import main
    root = node(tmp_path)
    write_cap(root, "path", name="Path capability", Status="Supported")
    monkeypatch.chdir(root)

    assert main(["capabilities", "path"]) == 0
    output = capsys.readouterr()
    assert output.out == f"{(root / 'docs/capabilities').resolve()}\n"
    assert output.err == ""

    assert main(["capabilities", "show", "path"]) == 0
    assert "Path capability" in capsys.readouterr().out


def test_cli_path_outside_capabilities_node_prints_no_path(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    monkeypatch.chdir(tmp_path)

    assert main(["capabilities", "path"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "no tcw capabilities node here" in output.err


class AmbiguousFeatureTax(FeatureTax):
    def get(self, ref):
        if ref == "user-authentication":
            raise AmbiguousRef(ref)
        return super().get(ref)


# ── add + collision ──────────────────────────────────────────────────────────

def test_add_creates_folder_with_id(tmp_path):
    root = node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    cap = st.add("routes/login", name="Sign in")
    assert cap.path == "routes/login"
    assert cap.id.startswith("cap-")
    assert (root / "docs/capabilities/routes/login/meta.yaml").is_file()
    assert (root / "docs/capabilities/routes/login/description.md").is_file()
    assert st.get("routes/login").status == "Missing"        # default status


def test_modified_timestamp_includes_declared_capability_docs(tmp_path):
    root = node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    folder = root / "docs/capabilities/routes/login"
    meta_path = folder / "meta.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["appendedDocs"] = ["guide.md"]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False))
    guide = folder / "guide.md"
    guide.write_text("Extra context\n")
    os.utime(meta_path, (100, 100))
    os.utime(folder / "description.md", (200, 200))
    os.utime(guide, (300, 300))

    assert st.get("routes/login").modified == "1970-01-01T00:05:00Z"


def test_add_mints_unique_ids(tmp_path):
    st = FsCapabilitiesStore.open(node(tmp_path))
    a = st.add("a")
    b = st.add("b")
    assert a.id and b.id and a.id != b.id


def test_add_refuses_duplicate(tmp_path):
    st = FsCapabilitiesStore.open(node(tmp_path))
    st.add("components/footer")
    with pytest.raises(ValueError):
        st.add("components/footer")


# ── path resolution + list/search ────────────────────────────────────────────

def small_tree(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/login", "User signs in.", Status="Supported")
    write_cap(root, "api/auth/login", "Auth endpoint.", Status="Supported")
    write_cap(root, "components/button", "Common.", Status="Supported")
    return root


def test_resolution_by_path(tmp_path):
    st = FsCapabilitiesStore.open(small_tree(tmp_path))
    assert st.get("routes/login").path == "routes/login"
    assert st.get("api/auth/login").path == "api/auth/login"     # nested
    assert st.get("routes/nope") is None


def test_list_search(tmp_path):
    st = FsCapabilitiesStore.open(small_tree(tmp_path))
    paths = {c.path for c in st.list_all()}
    assert {"routes/login", "api/auth/login", "components/button"} <= paths
    routes = st.list_all(namespace="routes")
    assert routes and all(c.path.startswith("routes") for c in routes)
    assert any(c.path == "routes/login" for c in st.search("signs in"))


def test_grouping_dir_is_not_a_capability(tmp_path):
    # `api/` is a pure grouping parent (no meta.yaml); only `api/auth/login` is a cap.
    st = FsCapabilitiesStore.open(small_tree(tmp_path))
    paths = {c.path for c in st.list_all()}
    assert "api" not in paths and "api/auth" not in paths


def test_capability_can_also_be_a_grouping_parent(tmp_path):
    root = node(tmp_path)
    write_cap(root, "web", "Browse.", Status="Supported")
    write_cap(root, "web/editing", "Edit.", Status="Supported")
    st = FsCapabilitiesStore.open(root)
    paths = {c.path for c in st.list_all()}
    assert {"web", "web/editing"} <= paths


def test_heading_slug():
    assert heading_slug("Sign in with Google") == "sign-in-with-google"
    assert heading_slug("401: Invalid credentials") == "401-invalid-credentials"


# ── multi-valued Subject ─────────────────────────────────────────────────────

def test_subject_multivalued(tmp_path):
    root = node(tmp_path)
    write_cap(root, "x", Status="Supported", Subject=["a", "b"])
    cap = FsCapabilitiesStore.open(root).get("x")
    assert cap.fields["Subject"] == ["a", "b"]


def test_set_subject_comma_replaces(tmp_path):
    st = FsCapabilitiesStore.open(node(tmp_path))
    st.add("x")
    cap = st.set("x", {"Subject": "a,b,c"})
    assert cap.fields["Subject"] == ["a", "b", "c"]


def test_check_resolves_each_subject(tmp_path):
    root = node(tmp_path)
    write_cap(root, "x", Status="Supported", Subject=["user", "ghost"])
    problems = FsCapabilitiesStore.open(root).check(taxonomy=StubTax("user"))
    assert any("Subject" in p and "ghost" in p for p in problems)
    assert not any("Subject" in p and "'user'" in p for p in problems)


# ── check: each failure class ────────────────────────────────────────────────

def test_check_clean(tmp_path):
    root = small_tree(tmp_path)
    write_cap(root, "roles/admin", Status="Supported")
    write_cap(root, "routes/profile", "Profile.", Status="Supported",
              Subject="user", Roles="roles/admin")
    assert FsCapabilitiesStore.open(root).check(taxonomy=StubTax("user")) == []


def test_check_dangling_superseded(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/old", Status="Supported",
              Lifecycle="Deprecated", **{"Superseded by": "routes/ghost"})
    assert any("Superseded by" in p for p in FsCapabilitiesStore.open(root).check())


def test_check_bad_subject_ref(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x", Status="Supported", Subject="nope/missing")
    problems = FsCapabilitiesStore.open(root).check(taxonomy=StubTax("user"))
    assert any("Subject" in p and "dangling" in p for p in problems)


def test_check_feature_ref_ok(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x", Status="Supported", Feature="user-authentication")
    assert FsCapabilitiesStore.open(root).check(taxonomy=FeatureTax()) == []


def test_check_bad_feature_ref(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x", Status="Supported", Feature="user")
    problems = FsCapabilitiesStore.open(root).check(taxonomy=FeatureTax())
    assert any("Feature" in p and "expected Feature" in p for p in problems)


def test_check_ambiguous_feature_ref(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x", Status="Supported", Feature="user-authentication")
    problems = FsCapabilitiesStore.open(root).check(taxonomy=AmbiguousFeatureTax())
    assert any("Feature" in p and "ambiguous" in p for p in problems)


def test_check_unknown_field(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x", Status="Supported", Bogus="y")
    assert any("unknown field" in p for p in FsCapabilitiesStore.open(root).check())


def test_check_missing_required_when_field(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x", Status="Partial")
    assert any("Partial requires Gaps" in p for p in FsCapabilitiesStore.open(root).check())


def test_check_unresolved_role_slug(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x", Status="Supported", Roles="roles/ghost")
    assert any("Roles" in p for p in FsCapabilitiesStore.open(root).check())


def test_check_missing_id(tmp_path):
    root = node(tmp_path)
    d = root / "docs/capabilities/x"
    d.mkdir(parents=True)
    (d / "meta.yaml").write_text("name: X\nStatus: Supported\n")
    (d / "description.md").write_text("")
    assert any("missing id" in p for p in FsCapabilitiesStore.open(root).check())


def test_check_duplicate_id(tmp_path):
    root = node(tmp_path)
    write_cap(root, "a", Status="Supported")
    write_cap(root, "b", Status="Supported")
    # Force a duplicate id on b.
    mb = root / "docs/capabilities/b/meta.yaml"
    m = yaml.safe_load(mb.read_text())
    m["id"] = yaml.safe_load((root / "docs/capabilities/a/meta.yaml").read_text())["id"]
    mb.write_text(yaml.safe_dump(m))
    assert any("duplicate id" in p for p in FsCapabilitiesStore.open(root).check())


def test_cli_check_with_taxonomy(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    (root / "docs" / "taxonomy" / "user").mkdir(parents=True)
    (root / "docs" / "taxonomy" / "user" / "meta.yaml").write_text("name: User\n")
    write_cap(root, "routes/x", Status="Supported", Subject="user")
    monkeypatch.chdir(root)
    assert main(["capabilities", "check"]) == 0
    assert "capabilities OK" in capsys.readouterr().out


# ── drift (unreviewed inherited + shipped-but-Missing) ───────────────────────

def test_cli_drift_flags_unreviewed_inherited(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    base = node(tmp_path, "base")
    write_cap(base, "auth/login", Status="Supported")
    child = node(tmp_path, "child")
    connect(base, child)
    FsCapabilitiesStore.open(child).extends_add("base")
    monkeypatch.chdir(child)
    assert main(["capabilities", "drift"]) == 1
    out = capsys.readouterr().out
    assert "unreviewed" in out and "base/auth/login" in out


def test_cli_drift_clean_after_override(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    base = node(tmp_path, "base")
    write_cap(base, "auth/login", Status="Supported")
    child = node(tmp_path, "child")
    connect(base, child)
    FsCapabilitiesStore.open(child).extends_add("base")
    FsCapabilitiesStore.open(child).set("auth/login", {"Status": "Omitted"})
    monkeypatch.chdir(child)
    assert main(["capabilities", "drift"]) == 0
    assert "no capability drift" in capsys.readouterr().out


def test_cli_drift_flags_shipped_but_missing(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.store.fs import FsWorkStore, init
    root = node(tmp_path)
    init(["work"], root)
    write_cap(root, "auth/login", Status="Missing")
    FsCapabilitiesStore.open(root).set("auth/login",
                                       {"Planning doc": "2026-01-01-ship-login"})
    st = FsWorkStore.open(root)
    slug = st.create("Ship login", created="2026-01-01").slug
    # Rename the item to the referenced slug is overkill; point Planning doc at it.
    FsCapabilitiesStore.open(root).set("auth/login", {"Planning doc": slug})
    st.start(slug)
    st.complete(slug, "done", dod_ack=[], force=True)
    monkeypatch.chdir(root)
    assert main(["capabilities", "drift"]) == 1
    assert "shipped-missing" in capsys.readouterr().out


def _external_completed_planning_item(tmp_path: Path) -> tuple[Path, str]:
    """A capabilities node whose work store lives in a *second* git repository,
    with a completed item wired to a still-Missing capability."""
    from tcw.store.fs import FsWorkStore, init
    root = node(tmp_path)
    store_repo = node(tmp_path, "store-repo")
    init(["work"], root, "repo", work_path=store_repo / "work")
    write_cap(root, "auth/login", Status="Missing")
    st = FsWorkStore.open(root)
    slug = st.create("Ship login", created="2026-01-01").slug
    FsCapabilitiesStore.open(root).set("auth/login", {"Planning doc": slug})
    st.start(slug)
    st.complete(slug, "done", dod_ack=[], force=True)
    return root, slug


@pytest.mark.parametrize("with_decoy", [False, True])
def test_cli_drift_reads_completed_item_from_external_store(
        tmp_path, monkeypatch, capsys, with_decoy):
    from tcw.cli import main
    root, slug = _external_completed_planning_item(tmp_path)
    if with_decoy:
        (root / "docs" / "work").mkdir(parents=True)
    monkeypatch.chdir(root)

    assert main(["capabilities", "drift"]) == 1
    output = capsys.readouterr().out
    assert "shipped-missing" in output
    assert slug in output


def test_cli_drift_ignores_a_discarded_planning_doc(tmp_path, monkeypatch, capsys):
    """`shipped-missing` asks "did it ship?", not "is it closed?". A discarded
    item's capability is *supposed* to stay Missing — flagging it was a false
    positive before `discarded` existed, when every closure landed in completed/."""
    from tcw.cli import main
    from tcw.store.fs import FsWorkStore, init
    root = node(tmp_path)
    init(["work"], root)
    write_cap(root, "auth/login", Status="Missing")
    st = FsWorkStore.open(root)
    slug = st.create("Ship login", created="2026-01-01").slug
    FsCapabilitiesStore.open(root).set("auth/login", {"Planning doc": slug})
    st.complete(slug, "wontfix", dod_ack=[], force=True)
    assert FsWorkStore.open(root).get(slug).status == "discarded"
    monkeypatch.chdir(root)
    assert main(["capabilities", "drift"]) == 0
    assert "no capability drift" in capsys.readouterr().out


def test_cli_drift_active_planning_doc_not_flagged(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.store.fs import FsWorkStore, init
    root = node(tmp_path)
    init(["work"], root)
    write_cap(root, "auth/login", Status="Missing")
    st = FsWorkStore.open(root)
    slug = st.create("Ship login", created="2026-01-01").slug
    FsCapabilitiesStore.open(root).set("auth/login", {"Planning doc": slug})
    st.start(slug)                                   # active, not completed
    monkeypatch.chdir(root)
    assert main(["capabilities", "drift"]) == 0


# ── drift does not depend on which machine is asking ──────────────────────────
#
# `completed/` and `discarded/` are gitignored, and resolving an item *moves* its
# folder there rather than deleting it — so the folder is present for whoever ran
# the transition and reaches no other clone. Answering "did this ship?" from
# `get()` therefore answered differently depending on who asked, and the silent
# direction was under-reporting: `drift` exited 0 with "no capability drift" in
# CI and in every colleague's clone. The tombstone is the same answer from a
# source that travels.


def _shipped_capability(tmp_path: Path, resolution: str = "done") -> tuple[Path, str]:
    """A Missing capability whose `Planning doc` names an item resolved as
    `resolution`, with the item's resolved folder still on disk."""
    from tcw.store.fs import FsWorkStore, init
    root = node(tmp_path)
    init(["work"], root)
    write_cap(root, "auth/login", Status="Missing")
    st = FsWorkStore.open(root)
    slug = st.create("Ship login", created="2026-01-01").slug
    FsCapabilitiesStore.open(root).set("auth/login", {"Planning doc": slug})
    if resolution == "done":
        # `(backlog, completed)` is not a legal transition for a plain item —
        # only a discard may close straight from backlog.
        st.start(slug)
    st.complete(slug, resolution, dod_ack=[], force=True)
    return root, slug


def _make_it_a_fresh_clone(root: Path, slug: str) -> None:
    """Remove the resolved item's folder, which is what every other checkout
    sees: the folder is gitignored, so it never arrived there at all."""
    import shutil
    from tcw.store.fs import FsWorkStore
    st = FsWorkStore.open(root)
    for status in ("completed", "discarded"):
        target = st.root / status / slug
        if target.exists():
            shutil.rmtree(target)
            return
    raise AssertionError(f"{slug} is in no resolved folder; the fixture is wrong")


def test_cli_drift_reports_a_shipped_item_whose_folder_is_gone(
        tmp_path, monkeypatch, capsys):
    """Spec criterion 1. The capability's work shipped; the only thing missing is
    the folder, which was never going to be here."""
    from tcw.cli import main
    root, slug = _shipped_capability(tmp_path)
    _make_it_a_fresh_clone(root, slug)
    monkeypatch.chdir(root)

    assert main(["capabilities", "drift"]) == 1
    out = capsys.readouterr().out
    assert "shipped-missing" in out and "auth/login" in out


def test_cli_drift_gives_the_same_verdict_either_side_of_the_ignore_rule(
        tmp_path, monkeypatch, capsys):
    """Spec criterion 2, and the criterion this whole item exists for.

    Asserts the two runs are *equal* rather than re-asserting the value: the
    defect was never a wrong answer, it was two different answers to the same
    question at the same commit, and equality is what says so.
    """
    from tcw.cli import main
    root, slug = _shipped_capability(tmp_path)
    monkeypatch.chdir(root)

    here_code = main(["capabilities", "drift"])
    here_out = capsys.readouterr().out

    _make_it_a_fresh_clone(root, slug)

    clone_code = main(["capabilities", "drift"])
    clone_out = capsys.readouterr().out

    assert (here_code, here_out) == (clone_code, clone_out)


def test_cli_drift_still_ignores_a_discarded_item_whose_folder_is_gone(
        tmp_path, monkeypatch, capsys):
    """Spec criterion 3. The distinction `drift` makes on purpose — "did it
    ship?", not "is it closed?" — has to survive being answered from the record
    rather than from the folder, or this fix trades a false negative for the
    false positive the command was already careful to avoid."""
    from tcw.cli import main
    root, slug = _shipped_capability(tmp_path, resolution="wontfix")
    _make_it_a_fresh_clone(root, slug)
    monkeypatch.chdir(root)

    assert main(["capabilities", "drift"]) == 0
    assert "no capability drift" in capsys.readouterr().out


def test_cli_drift_is_silent_when_the_record_kept_no_resolution(
        tmp_path, monkeypatch, capsys):
    """Spec criterion 4. A backfilled record often has no resolution, because
    whoever backfilled it did not know one. Reporting on that would mean guessing
    that unknown means shipped, and the requester chose silence over ever calling
    abandoned work shipped."""
    from tcw.cli import main
    from tcw.store.fs import init
    root = node(tmp_path)
    init(["work"], root)
    write_cap(root, "auth/login", Status="Missing")
    FsCapabilitiesStore.open(root).set("auth/login",
                                       {"Planning doc": "2026-01-01-long-gone"})
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", "2026-01-01-long-gone"]) == 0
    capsys.readouterr()

    assert main(["capabilities", "drift"]) == 0
    assert "no capability drift" in capsys.readouterr().out


def test_cli_drift_ignores_a_planning_doc_naming_a_slug_that_never_existed(
        tmp_path, monkeypatch, capsys):
    """Spec criterion 5, and a regression guard rather than a defect test — it
    passes before and after. It is the case that separates "resolved" from
    "typo", which is the distinction the whole tombstone mechanism exists to
    draw, so it is worth pinning where the drift lookup can see it."""
    from tcw.cli import main
    from tcw.store.fs import init
    root = node(tmp_path)
    init(["work"], root)
    write_cap(root, "auth/login", Status="Missing")
    FsCapabilitiesStore.open(root).set("auth/login",
                                       {"Planning doc": "2026-01-01-never-was"})
    monkeypatch.chdir(root)

    assert main(["capabilities", "drift"]) == 0
    assert "no capability drift" in capsys.readouterr().out


def test_cli_drift_no_work_node_no_error(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)                             # capabilities only, no work
    write_cap(root, "auth/login", Status="Missing", **{"Planning doc": "whatever"})
    monkeypatch.chdir(root)
    assert main(["capabilities", "drift"]) == 0       # degrades to silence


def test_cli_drift_does_not_affect_check(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    base = node(tmp_path, "base")
    write_cap(base, "auth/login", Status="Supported")
    child = node(tmp_path, "child")
    connect(base, child)
    FsCapabilitiesStore.open(child).extends_add("base")
    monkeypatch.chdir(child)
    assert main(["capabilities", "check"]) == 0        # unreviewed ≠ structural fault


# ── set (the ledger-flip affordance) ──────────────────────────────────────────

def test_set_updates_status(tmp_path):
    root = node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("auth/google", name="Sign in with Google", body="User clicks the Google button.")
    cap = st.set("auth/google", {"Status": "Supported"})
    assert cap.status == "Supported"
    assert "User clicks the Google button." in (
        root / "docs/capabilities/auth/google/description.md").read_text()


def test_set_inserts_new_field(tmp_path):
    st = FsCapabilitiesStore.open(node(tmp_path))
    st.add("auth/google", name="Sign in with Google", body="User clicks.")
    st.set("auth/google", {"Planning doc": "2026-01-01-google-sso"})
    cap = st.get("auth/google")
    assert cap.fields.get("Planning doc") == "2026-01-01-google-sso"
    assert cap.body.startswith("User clicks")


def test_set_clears_field_with_none(tmp_path):
    st = FsCapabilitiesStore.open(node(tmp_path))
    st.add("x")
    st.set("x", {"Priority": "P1"})
    assert st.get("x").fields.get("Priority") == "P1"
    st.set("x", {"Priority": None})
    assert "Priority" not in st.get("x").fields


def test_set_rejects_invalid_status_and_unknown_field(tmp_path):
    st = FsCapabilitiesStore.open(node(tmp_path))
    st.add("routes/login", name="Sign in")
    with pytest.raises(ValueError):
        st.set("routes/login", {"Status": "Broken"})
    with pytest.raises(ValueError):
        st.set("routes/login", {"Frobnicate": "x"})


def test_set_dangling_path_errors(tmp_path):
    root = node(tmp_path)
    with pytest.raises((ValueError, RefError)):
        FsCapabilitiesStore.open(root).set("routes/nope", {"Status": "Supported"})


def test_remove(tmp_path):
    st = FsCapabilitiesStore.open(node(tmp_path))
    st.add("x")
    st.remove("x")
    assert st.get("x") is None


def test_cli_set_not_rewritten_to_show(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    from tcw.cli import main
    FsCapabilitiesStore.open(root).add("routes/login", name="Sign in")
    assert main(["capabilities", "set", "routes/login", "--status", "Supported"]) == 0
    assert "Set" in capsys.readouterr().out
    assert FsCapabilitiesStore.open(root).get("routes/login").status == "Supported"


def test_cli_set_inherited_path(tmp_path, monkeypatch, capsys):
    """The reporter's transcript (issue #3): `set` must accept every path
    `show` accepts, materializing the override itself."""
    base = node(tmp_path, "base")
    FsCapabilitiesStore.open(base).add("moderation/report-content",
                                       name="Report content", status="Supported")
    child = node(tmp_path, "child")
    connect(base, child)
    FsCapabilitiesStore.open(child).extends_add("base")
    monkeypatch.chdir(child)
    from tcw.cli import main

    assert main(["capabilities", "set", "base/moderation/report-content",
                 "--status", "Missing"]) == 0
    assert "Set" in capsys.readouterr().out
    assert FsCapabilitiesStore.open(child).get(
        "moderation/report-content").status == "Missing"
    assert FsCapabilitiesStore.open(base).get(
        "moderation/report-content").status == "Supported"


def test_cli_set_ambiguous_ref_reports_ambiguity(tmp_path, monkeypatch, capsys):
    for name in ("one", "two"):
        FsCapabilitiesStore.open(node(tmp_path, name)).add("x/thing", name="Thing")
    child = node(tmp_path, "child")
    st = FsCapabilitiesStore.open(child)
    (child / "tcw-config.yaml").write_text(
        "id: child\nconnected-projects:\n  children:\n"
        "    one: ../one\n    two: ../two\n"
    )
    for name in ("one", "two"):
        (tmp_path / name / "tcw-config.yaml").write_text(
            f"id: {name}\nconnected-projects:\n  parent:\n    child: ../child\n"
        )
    st = FsCapabilitiesStore.open(child)
    st.extends_add("one")
    st.extends_add("two")
    monkeypatch.chdir(child)
    from tcw.cli import main

    assert main(["capabilities", "set", "x/thing", "--status", "Missing"]) == 1
    err = capsys.readouterr().err
    assert "ambiguous" in err and "x/thing" in err     # not a bare, unexplained path
    assert main(["capabilities", "set", "one/x/thing", "--status", "Missing"]) == 0


def test_cli_capabilities_init_mirrors_top_level(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = tmp_path / "fresh"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    monkeypatch.chdir(root)
    assert main(["capabilities", "init", "--id", "fresh"]) == 0
    comp_out = capsys.readouterr().out
    assert (root / "docs" / "capabilities" / ".gitkeep").is_file()
    assert main(["init", "capabilities"]) == 0
    assert comp_out == capsys.readouterr().out
