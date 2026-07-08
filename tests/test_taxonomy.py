import subprocess
from pathlib import Path

import pytest

from tcw.store.base import AmbiguousRef
from tcw.store.fs import FsTaxonomyStore, write_sentinel


def node(tmp_path: Path, name: str) -> Path:
    """A repo root with docs/taxonomy/ (git-inited so add/rm can stage)."""
    root = tmp_path / name
    (root / "docs" / "taxonomy").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root)                # mark it a node for CLI (find_node) tests
    return root


def write_term(root: Path, slug: str, name=None, relates_to=None, description="",
               kind=None, vocabulary=None):
    d = root / "docs" / "taxonomy" / slug
    d.mkdir(parents=True, exist_ok=True)
    import yaml
    meta = {"name": name or slug, "relatesTo": relates_to or []}
    if kind:
        meta["kind"] = kind
    if vocabulary:
        meta["vocabulary"] = vocabulary
    (d / "meta.yaml").write_text(yaml.safe_dump(meta))
    (d / "description.md").write_text(description)


def write_config(root: Path, text: str):
    (root / "docs" / "taxonomy" / "config.yaml").write_text(text)


# ── add / identity ──────────────────────────────────────────────────────────

def test_add_nesting_and_slug_is_path(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    perm = st.add("Permission", parent="admin")
    assert perm.slug == "admin/permission"
    assert (root / "docs/taxonomy/admin/permission/meta.yaml").exists()
    assert st.get("admin/permission").name == "Permission"
    # same leaf under different parents are distinct terms
    st.add("Object")
    st.add("Permission", parent="object")
    assert st.get("object/permission").slug == "object/permission"


def test_add_feature_with_vocabulary_refs(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    st.add("User")
    feature = st.add("User Authentication", kind="Feature", vocabulary=["user"])
    assert feature.kind == "Feature"
    assert feature.vocabulary == ["user"]
    assert st.check() == []


def test_missing_kind_defaults_to_vocabulary(tmp_path):
    root = node(tmp_path, "repo")
    write_term(root, "user", name="User")
    term = FsTaxonomyStore.open(root).get("user")
    assert term.kind == "Vocabulary"


def test_add_refuses_collision(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    with pytest.raises(ValueError):
        st.add("Admin")


# ── extends: list/show/origin + the three resolution branches ───────────────

def consumer_with_shared(tmp_path, alias="shared", local_dup=False):
    shared = node(tmp_path, "shared")
    write_term(shared, "Argument", name="Argument")
    cons = node(tmp_path, "consumer")
    write_config(cons, f"extends:\n  {alias}: ../shared\n")
    if local_dup:
        write_term(cons, "Argument", name="Local Argument")
    return cons, shared


def test_list_flags_inherited_origin(tmp_path):
    cons, _ = consumer_with_shared(tmp_path)
    st = FsTaxonomyStore.open(cons)
    by_slug = {t.slug: t for t in st.list_all()}
    assert by_slug["Argument"].origin == "shared"
    assert st.get("shared/Argument").qualified == "shared/Argument"
    assert FsTaxonomyStore.open(cons).list_all(local_only=True) == []


def test_resolution_unique_extended(tmp_path):
    cons, _ = consumer_with_shared(tmp_path)
    st = FsTaxonomyStore.open(cons)
    assert st.get("Argument").origin == "shared"          # bare, one extend


def test_resolution_local_wins_bare(tmp_path):
    cons, _ = consumer_with_shared(tmp_path, local_dup=True)
    st = FsTaxonomyStore.open(cons)
    assert st.get("Argument").origin == "local"           # local shadows extend


def test_resolution_ambiguous_errors(tmp_path):
    a = node(tmp_path, "a"); write_term(a, "Term", name="A")
    b = node(tmp_path, "b"); write_term(b, "Term", name="B")
    cons = node(tmp_path, "consumer")
    write_config(cons, "extends:\n  a: ../a\n  b: ../b\n")
    st = FsTaxonomyStore.open(cons)
    with pytest.raises(AmbiguousRef):
        st.get("Term")
    assert st.get("a/Term").origin == "a"                 # qualified is unambiguous


def test_get_term_detail_of_inherited_term(tmp_path):
    # Regression: get_term_detail read files under the extending store's root,
    # not the source store's, so an inherited term raised FileNotFoundError (→ 500
    # in the web viewer). Detail must resolve against the owning store.
    cons, _ = consumer_with_shared(tmp_path)
    st = FsTaxonomyStore.open(cons)
    detail = st.get_term_detail("shared/Argument")
    assert detail is not None
    assert detail.term.name == "Argument"
    assert detail.term.origin == "shared"                 # origin preserved
    assert detail.term.qualified == "shared/Argument"
    assert detail.core_revision                            # non-empty revision
    # bare ref (unique extend) resolves the same way
    assert st.get_term_detail("Argument").term.origin == "shared"


# ── rm ──────────────────────────────────────────────────────────────────────

def test_rm_local(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    st.remove("admin")
    assert not (root / "docs/taxonomy/admin").exists()


def test_rm_refuses_inherited(tmp_path):
    cons, _ = consumer_with_shared(tmp_path)
    st = FsTaxonomyStore.open(cons)
    with pytest.raises(ValueError):
        st.remove("shared/Argument")


# ── check ───────────────────────────────────────────────────────────────────

def test_check_clean(tmp_path):
    cons, _ = consumer_with_shared(tmp_path)
    assert FsTaxonomyStore.open(cons).check() == []


def test_check_dangling_relatesto(tmp_path):
    root = node(tmp_path, "repo")
    write_term(root, "thing", name="Thing", relates_to=["nope/missing"])
    problems = FsTaxonomyStore.open(root).check()
    assert any("dangling" in p for p in problems)


def test_check_feature_vocabulary_refs(tmp_path):
    root = node(tmp_path, "repo")
    write_term(root, "user", name="User")
    write_term(root, "user-authentication", name="User Authentication",
               kind="Feature", vocabulary=["user"])
    write_term(root, "password-reset", name="Password Reset",
               kind="Feature", vocabulary=["user-authentication"])
    write_term(root, "ghost-feature", name="Ghost Feature",
               kind="Feature", vocabulary=["ghost"])
    problems = FsTaxonomyStore.open(root).check()
    assert any("password-reset" in p and "expected Vocabulary" in p for p in problems)
    assert any("ghost-feature" in p and "dangling vocabulary" in p for p in problems)


def test_check_feature_requires_vocabulary_refs(tmp_path):
    root = node(tmp_path, "repo")
    write_term(root, "user-authentication", name="User Authentication", kind="Feature")
    problems = FsTaxonomyStore.open(root).check()
    assert any("Feature requires at least one vocabulary ref" in p for p in problems)


def test_check_ambiguous_relatesto(tmp_path):
    a = node(tmp_path, "a"); write_term(a, "Term")
    b = node(tmp_path, "b"); write_term(b, "Term")
    cons = node(tmp_path, "consumer")
    write_config(cons, "extends:\n  a: ../a\n  b: ../b\n")
    write_term(cons, "host", relates_to=["Term"])
    problems = FsTaxonomyStore.open(cons).check()
    assert any("ambiguous" in p for p in problems)


def test_check_duplicate_alias(tmp_path):
    cons = node(tmp_path, "consumer")
    other = node(tmp_path, "other")
    write_config(cons, "extends:\n  shared: ../other\n  shared: ../other\n")
    problems = FsTaxonomyStore.open(cons).check()
    assert any("config.yaml" in p for p in problems)


def test_check_alias_collides_with_local_top_level(tmp_path):
    cons, _ = consumer_with_shared(tmp_path, alias="shared")
    write_term(cons, "shared", name="Shared (local)")
    problems = FsTaxonomyStore.open(cons).check()
    assert any("collides" in p for p in problems)


def test_check_cycle(tmp_path):
    a = node(tmp_path, "a")
    b = node(tmp_path, "b")
    write_config(a, "extends:\n  b: ../b\n")
    write_config(b, "extends:\n  a: ../a\n")
    problems = FsTaxonomyStore.open(a).check()
    assert any("cycle" in p for p in problems)


def test_check_missing_extends_path(tmp_path):
    cons = node(tmp_path, "consumer")
    write_config(cons, "extends:\n  ghost: ../does-not-exist\n")
    problems = FsTaxonomyStore.open(cons).check()
    assert any("does not exist" in p for p in problems)


# ── CLI smoke (bare-path sugar) ─────────────────────────────────────────────

def test_cli_bare_path_is_show(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path, "repo")
    monkeypatch.chdir(root)
    main(["taxonomy", "add", "Admin"])
    assert main(["taxonomy", "admin"]) == 0          # bare path → show
    assert "Admin" in capsys.readouterr().out


def test_cli_add_feature_lists_and_shows_kind(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path, "repo")
    monkeypatch.chdir(root)
    assert main(["taxonomy", "add", "User"]) == 0
    capsys.readouterr()
    assert main(["taxonomy", "add", "Password", "--slug", "password"]) == 0
    capsys.readouterr()
    assert main(["taxonomy", "add", "User Authentication", "--kind", "feature",
                 "--vocab", "user", "--vocab", "password"]) == 0
    capsys.readouterr()
    assert main(["taxonomy", "list"]) == 0
    out = capsys.readouterr().out
    assert "user  [V]" in out
    assert "user-authentication  [F]" in out
    assert main(["taxonomy", "show", "user-authentication"]) == 0
    out = capsys.readouterr().out
    assert "kind: Feature" in out
    assert "vocabulary: user, password" in out


def test_cli_list_unknown_kind_uses_unknown_marker(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path, "repo")
    write_term(root, "mystery", name="Mystery", kind="Mystery")
    monkeypatch.chdir(root)
    assert main(["taxonomy", "list"]) == 0
    assert "mystery  [?]" in capsys.readouterr().out


def test_cli_taxonomy_init_mirrors_top_level(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = tmp_path / "fresh"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    monkeypatch.chdir(root)
    assert main(["taxonomy", "init"]) == 0
    comp_out = capsys.readouterr().out
    assert (root / "docs" / "taxonomy" / ".gitkeep").is_file()
    assert main(["init", "taxonomy"]) == 0          # idempotent; same report
    assert comp_out == capsys.readouterr().out


# ── extends (federation) write path ───────────────────────────────────────────

def test_extends_add_writes_map_and_resolves(tmp_path):
    base = node(tmp_path, "base")
    write_term(base, "widget", name="Widget")
    consumer = node(tmp_path, "consumer")
    FsTaxonomyStore.open(consumer).extends_add("shared", "../base")
    st = FsTaxonomyStore.open(consumer)            # reopen to load the new federation
    assert "shared/widget" in {t.qualified for t in st.list_all()}
    assert st.get("shared/widget").name == "Widget"


def test_extends_add_refuses(tmp_path):
    node(tmp_path, "base")
    consumer = node(tmp_path, "consumer")
    FsTaxonomyStore.open(consumer).extends_add("shared", "../base")
    st = FsTaxonomyStore.open(consumer)
    with pytest.raises(ValueError):               # duplicate alias
        st.extends_add("shared", "../base")
    with pytest.raises(ValueError):               # missing target repo
        st.extends_add("nope", "../does-not-exist")
    with pytest.raises(ValueError):               # self-reference
        st.extends_add("self", ".")


def test_extends_remove(tmp_path):
    node(tmp_path, "base")
    consumer = node(tmp_path, "consumer")
    FsTaxonomyStore.open(consumer).extends_add("shared", "../base")
    st = FsTaxonomyStore.open(consumer)
    st.extends_remove("shared")
    assert "shared" not in (FsTaxonomyStore.open(consumer).config.get("extends") or {})
    with pytest.raises(ValueError):               # absent alias
        FsTaxonomyStore.open(consumer).extends_remove("shared")


def test_cli_extends_add_and_rm(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    node(tmp_path, "base")
    consumer = node(tmp_path, "consumer")
    monkeypatch.chdir(consumer)
    assert main(["taxonomy", "extends", "add", "shared", "../base"]) == 0
    capsys.readouterr()
    assert (consumer / "docs/taxonomy/config.yaml").exists()
    assert main(["taxonomy", "extends", "add", "shared", "../base"]) == 1   # duplicate → error exit
    assert "already exists" in capsys.readouterr().err
    assert main(["taxonomy", "extends", "rm", "shared"]) == 0


def test_cli_extends_is_not_treated_as_a_term_path(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path, "repo")
    monkeypatch.chdir(root)
    # "extends" must dispatch to the subcommand, not the `taxonomy <path>` show-sugar
    assert main(["taxonomy", "extends", "rm", "ghost"]) == 1   # absent alias → handled error, not "no such term"
    assert "no such term" not in capsys.readouterr().err
