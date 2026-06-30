import subprocess
from pathlib import Path

import pytest

from tcw.store.base import AmbiguousRef, RefError, Term
from tcw.store.fs import FsCapabilitiesStore, heading_slug, write_sentinel


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    (root / "docs" / "capabilities").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root)                # mark it a node for CLI (find_node) tests
    return root


def write_cap(root: Path, relpath: str, text: str) -> None:
    p = root / "docs" / "capabilities" / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


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


class AmbiguousFeatureTax(FeatureTax):
    def get(self, ref):
        if ref == "user-authentication":
            raise AmbiguousRef(ref)
        return super().get(ref)


# ── add (flat + folder) + collision ──────────────────────────────────────────

def test_add_flat_and_folder(tmp_path):
    root = node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    cf = st.add("routes/login", name="Sign in")
    assert cf.identifier == "routes/login"
    assert (root / "docs/capabilities/routes/login.md").is_file()
    cf2 = st.add("api/auth/login", name="Login", folder=True)
    assert cf2.identifier == "api/auth/login"
    assert (root / "docs/capabilities/api/auth/login/capabilities.md").is_file()
    # default status seeded
    assert st.get("routes/login").capabilities[0].status == "Missing"


def test_add_refuses_flat_folder_collision(tmp_path):
    root = node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("components/footer")
    with pytest.raises(ValueError):
        st.add("components/footer", folder=True)


# ── identifier resolution (flat / folder-entry / [state] / #heading) ─────────

def small_tree(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/login.md",
              "# Login — capabilities\n\n## Sign in\n**Status:** Supported\n\nUser signs in.\n")
    write_cap(root, "api/auth/login/capabilities.md",
              "# Login API — capabilities\n\n## POST login\n**Status:** Supported\n\nAuth endpoint.\n")
    write_cap(root, "components/button/capabilities.md",
              "# Button — capabilities\n\n## Click\n**Status:** Supported\n\nCommon.\n")
    write_cap(root, "components/button/with-icon.md",
              "# Button (icon) — capabilities\n\n## Click with icon\n**Status:** Supported\n\nIcon.\n")
    return root


def test_resolution_forms(tmp_path):
    st = FsCapabilitiesStore.open(small_tree(tmp_path))
    assert st.get("routes/login").identifier == "routes/login"            # flat
    assert st.get("api/auth/login").identifier == "api/auth/login"        # folder-entry
    variant = st.get("components/button[icon]")                           # [state]
    assert variant.capabilities[0].name == "Click with icon"
    assert st._ref_error("routes/login#sign-in") is None                 # #heading
    assert st._ref_error("routes/login#nope") is not None


def test_list_search_show(tmp_path):
    st = FsCapabilitiesStore.open(small_tree(tmp_path))
    ids = {c.file_id for c in st.list()}
    assert {"routes/login", "api/auth/login", "components/button"} <= ids
    assert st.list(namespace="routes") and all(
        c.file_id.startswith("routes") for c in st.list(namespace="routes"))
    assert any(c.file_id == "routes/login" for c in st.search("signs in"))


def test_heading_slug():
    assert heading_slug("Sign in with Google") == "sign-in-with-google"
    assert heading_slug("401: Invalid credentials") == "401-invalid-credentials"


# ── check: each failure class ────────────────────────────────────────────────

def test_check_clean(tmp_path):
    root = small_tree(tmp_path)
    write_cap(root, "roles/admin.md", "# Admin — capabilities\n\n## Admin role\n**Status:** Supported\n")
    write_cap(root, "routes/profile.md",
              "# Profile — capabilities\n\n## View\n**Status:** Supported\n"
              "**Subject:** user\n**Roles:** roles/admin\n\nProfile.\n")
    assert FsCapabilitiesStore.open(root).check(taxonomy=StubTax("user")) == []


def test_check_dangling_identifier(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/old.md",
              "# Old — capabilities\n\n## Legacy\n**Status:** Supported\n"
              "**Lifecycle:** Deprecated\n**Superseded by:** routes/ghost\n")
    assert any("Superseded by" in p for p in FsCapabilitiesStore.open(root).check())


def test_check_bad_subject_ref(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x.md",
              "# X — capabilities\n\n## Do x\n**Status:** Supported\n**Subject:** nope/missing\n")
    problems = FsCapabilitiesStore.open(root).check(taxonomy=StubTax("user"))
    assert any("Subject" in p and "dangling" in p for p in problems)


def test_check_feature_ref(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x.md",
              "# X — capabilities\n\n## Do x\n**Status:** Supported\n"
              "**Feature:** user-authentication\n")
    assert FsCapabilitiesStore.open(root).check(taxonomy=FeatureTax()) == []


def test_check_bad_feature_ref(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x.md",
              "# X — capabilities\n\n## Do x\n**Status:** Supported\n"
              "**Feature:** user\n")
    problems = FsCapabilitiesStore.open(root).check(taxonomy=FeatureTax())
    assert any("Feature" in p and "expected Feature" in p for p in problems)


def test_check_ambiguous_feature_ref(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x.md",
              "# X — capabilities\n\n## Do x\n**Status:** Supported\n"
              "**Feature:** user-authentication\n")
    problems = FsCapabilitiesStore.open(root).check(taxonomy=AmbiguousFeatureTax())
    assert any("Feature" in p and "ambiguous" in p for p in problems)


def test_check_unknown_field(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x.md", "# X — capabilities\n\n## Do x\n**Status:** Supported\n**Bogus:** y\n")
    assert any("unknown field" in p for p in FsCapabilitiesStore.open(root).check())


def test_check_missing_required_when_field(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x.md", "# X — capabilities\n\n## Do x\n**Status:** Partial\n")
    assert any("Partial requires Gaps" in p for p in FsCapabilitiesStore.open(root).check())


def test_check_unresolved_role_slug(tmp_path):
    root = node(tmp_path)
    write_cap(root, "routes/x.md",
              "# X — capabilities\n\n## Do x\n**Status:** Supported\n**Roles:** roles/ghost\n")
    assert any("Roles" in p for p in FsCapabilitiesStore.open(root).check())


def test_check_flat_folder_collision(tmp_path):
    root = node(tmp_path)
    write_cap(root, "components/footer.md", "# Footer — capabilities\n\n## Show\n**Status:** Supported\n")
    write_cap(root, "components/footer/capabilities.md",
              "# Footer — capabilities\n\n## Show2\n**Status:** Supported\n")
    assert any("collision" in p for p in FsCapabilitiesStore.open(root).check())


# ── CLI smoke ────────────────────────────────────────────────────────────────

def test_cli_check_with_taxonomy(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    (root / "docs" / "taxonomy" / "user").mkdir(parents=True)
    (root / "docs" / "taxonomy" / "user" / "meta.yaml").write_text("name: User\n")
    write_cap(root, "routes/x.md",
              "# X — capabilities\n\n## Do x\n**Status:** Supported\n**Subject:** user\n")
    monkeypatch.chdir(root)
    assert main(["capabilities", "check"]) == 0
    assert "capabilities OK" in capsys.readouterr().out


# ── set (the ledger-flip affordance) ──────────────────────────────────────────

_MULTI = (
    "# Auth — capabilities\n\n"
    "## Sign in with Google\n**Status:** Missing\n\nUser clicks the Google button.\n\n"
    "## Sign out\n**Status:** Supported\n**Priority:** P1\n\nUser ends the session.\n"
)


def test_set_updates_status_preserving_siblings(tmp_path):
    root = node(tmp_path)
    write_cap(root, "auth.md", _MULTI)
    st = FsCapabilitiesStore.open(root)
    cap = st.set("auth#sign-in-with-google", {"Status": "Supported"})
    assert cap.status == "Supported"
    sign_out = next(c for c in st.get("auth").capabilities if c.name == "Sign out")
    assert sign_out.status == "Supported" and sign_out.fields.get("Priority") == "P1"
    assert "User clicks the Google button." in (root / "docs/capabilities/auth.md").read_text()


def test_set_inserts_new_field_into_metadata_run(tmp_path):
    root = node(tmp_path)
    write_cap(root, "auth.md", _MULTI)
    st = FsCapabilitiesStore.open(root)
    st.set("auth#sign-in-with-google", {"Planning doc": "2026-01-01-google-sso"})
    cap = next(c for c in st.get("auth").capabilities if c.name == "Sign in with Google")
    assert cap.fields.get("Planning doc") == "2026-01-01-google-sso"
    assert cap.body.startswith("User clicks")


def test_set_requires_heading_for_multicap(tmp_path):
    root = node(tmp_path)
    write_cap(root, "auth.md", _MULTI)
    with pytest.raises(RefError):
        FsCapabilitiesStore.open(root).set("auth", {"Status": "Supported"})


def test_set_bare_id_on_single_cap(tmp_path):
    root = node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    cap = st.set("routes/login", {"Status": "Supported"})
    assert cap.status == "Supported"


def test_set_rejects_invalid_status_and_unknown_field(tmp_path):
    root = node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    with pytest.raises(ValueError):
        st.set("routes/login", {"Status": "Broken"})
    with pytest.raises(ValueError):
        st.set("routes/login", {"Frobnicate": "x"})


def test_set_dangling_id_errors(tmp_path):
    root = node(tmp_path)
    with pytest.raises((ValueError, RefError)):
        FsCapabilitiesStore.open(root).set("routes/nope", {"Status": "Supported"})


def test_cli_set_not_rewritten_to_show(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    from tcw.cli import main
    FsCapabilitiesStore.open(root).add("routes/login", name="Sign in")
    assert main(["capabilities", "set", "routes/login", "--status", "Supported"]) == 0
    assert "Set" in capsys.readouterr().out
    assert FsCapabilitiesStore.open(root).get("routes/login").capabilities[0].status == "Supported"


def test_cli_capabilities_init_mirrors_top_level(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = tmp_path / "fresh"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    monkeypatch.chdir(root)
    assert main(["capabilities", "init"]) == 0
    comp_out = capsys.readouterr().out
    assert (root / "docs" / "capabilities" / ".gitkeep").is_file()
    assert main(["init", "capabilities"]) == 0
    assert comp_out == capsys.readouterr().out
