import os
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
    write_sentinel(root, name)          # mark it a node for CLI (find_node) tests
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


def connect_sources(consumer: Path, *sources: Path) -> None:
    children = "".join(f"    {source.name}: ../{source.name}\n" for source in sources)
    (consumer / "tcw-config.yaml").write_text(
        f"id: {consumer.name}\nconnected-projects:\n  children:\n{children}"
    )
    for source in sources:
        (source / "tcw-config.yaml").write_text(
            f"id: {source.name}\nconnected-projects:\n  parent:\n"
            f"    {consumer.name}: ../{consumer.name}\n"
        )


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


def test_modified_timestamp_uses_bounded_taxonomy_resources(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    st.add("User")
    folder = root / "docs/taxonomy/user"
    os.utime(folder / "meta.yaml", (100, 100))
    os.utime(folder / "description.md", (200, 200))
    attachment = folder / "notes.txt"
    attachment.write_text("not a core taxonomy resource\n")
    os.utime(attachment, (300, 300))

    assert st.get("user").modified == "1970-01-01T00:03:20Z"


def test_add_feature_with_vocabulary_refs(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    st.add("User")
    feature = st.add("User Authentication", kind="Feature", vocabulary=["user"])
    assert feature.kind == "Feature"
    assert feature.vocabulary == ["user"]
    assert st.check() == []


def test_add_refuses_unresolvable_vocab_ref(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    with pytest.raises(ValueError, match="'this-does-not-exist' does not resolve"):
        st.add("F", kind="Feature", vocabulary=["this-does-not-exist"])
    assert not (root / "docs/taxonomy/f").exists()      # no partial folder


def test_add_requires_a_vocabulary_ref_on_a_feature(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    with pytest.raises(ValueError, match="Feature requires at least one vocabulary ref"):
        st.add("F", kind="Feature")
    assert not (root / "docs/taxonomy/f").exists()


def test_add_refuses_vocab_ref_pointing_at_a_feature(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    st.add("User")
    st.add("User Authentication", kind="Feature", vocabulary=["user"])
    with pytest.raises(ValueError, match="expected Vocabulary"):
        st.add("Password Reset", kind="Feature", vocabulary=["user-authentication"])
    assert not (root / "docs/taxonomy/password-reset").exists()


def test_add_resolves_a_unique_leaf_slug_to_its_path(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    st.add("Alpha")
    st.add("Zeta", parent="alpha")
    feature = st.add("F", kind="Feature", vocabulary=["zeta"])
    assert feature.vocabulary == ["alpha/zeta"]        # the path, not the leaf
    assert st.check() == []                            # what add wrote, check accepts


def test_add_ambiguous_leaf_slug_names_both_candidates(tmp_path):
    root = node(tmp_path, "repo")
    st = FsTaxonomyStore.open(root)
    for parent in ("alpha", "beta"):
        st.add(parent.title())
        st.add("Zeta", parent=parent)
    with pytest.raises(ValueError) as excinfo:
        st.add("F", kind="Feature", vocabulary=["zeta"])
    message = str(excinfo.value)
    assert "ambiguous" in message
    assert "alpha/zeta" in message and "beta/zeta" in message
    assert not (root / "docs/taxonomy/f").exists()


def test_add_stores_a_resolving_ref_verbatim(tmp_path):
    # A ref that already resolves is never rewritten — not a full local path,
    # and not an inherited term reached through an extends alias.
    cons, _ = consumer_with_shared(tmp_path)
    st = FsTaxonomyStore.open(cons)
    st.add("Alpha")
    st.add("Zeta", parent="alpha")
    assert st.add("F", kind="Feature",
                  vocabulary=["alpha/zeta"]).vocabulary == ["alpha/zeta"]
    assert st.add("G", kind="Feature",
                  vocabulary=["Argument"]).vocabulary == ["Argument"]
    assert st.add("H", kind="Feature",
                  vocabulary=["shared/Argument"]).vocabulary == ["shared/Argument"]


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
    connect_sources(cons, shared)
    write_config(cons, "extends:\n  - shared\n")
    if local_dup:
        write_term(cons, "Argument", name="Local Argument")
    return cons, shared


def transitive_taxonomy(tmp_path):
    a = node(tmp_path, "alpha")
    b = node(tmp_path, "bravo")
    c = node(tmp_path, "charlie")
    (a / "tcw-config.yaml").write_text(
        "id: alpha\nconnected-projects:\n  children:\n    bravo: ../bravo\n"
    )
    (b / "tcw-config.yaml").write_text(
        "id: bravo\nconnected-projects:\n  parent:\n    alpha: ../alpha\n"
        "  children:\n    charlie: ../charlie\n"
    )
    (c / "tcw-config.yaml").write_text(
        "id: charlie\nconnected-projects:\n  parent:\n    bravo: ../bravo\n"
    )
    write_config(a, "extends:\n  - bravo\n")
    write_config(b, "extends:\n  - charlie\n")
    write_term(b, "shared", name="B Shared", description="from project b")
    write_term(c, "shared", name="C Shared", description="from project c")
    write_term(c, "deep", name="Deep", description="transitive needle")
    return a, b, c


def test_list_flags_inherited_origin(tmp_path):
    cons, _ = consumer_with_shared(tmp_path)
    st = FsTaxonomyStore.open(cons)
    by_slug = {t.slug: t for t in st.list_all()}
    assert by_slug["Argument"].origin == "shared"
    assert st.get("shared/Argument").qualified == "shared/Argument"
    assert FsTaxonomyStore.open(cons).list_all(local_only=True) == []


def test_transitive_extends_flattens_terms_by_owning_project(tmp_path):
    a, _, c = transitive_taxonomy(tmp_path)
    st = FsTaxonomyStore.open(a)

    assert {(term.qualified, term.origin) for term in st.list_all()} == {
        ("bravo/shared", "bravo"),
        ("charlie/deep", "charlie"),
        ("charlie/shared", "charlie"),
    }
    assert st.get("charlie/deep").qualified == "charlie/deep"
    assert st.get("deep").origin == "charlie"
    assert [term.qualified for term in st.search("transitive needle")] == ["charlie/deep"]

    detail = st.get_term_detail("charlie/deep")
    assert detail is not None
    assert detail.term.origin == "charlie"
    assert st._validation_resources("charlie/deep") == [
        c / "docs/taxonomy/deep/meta.yaml",
        c / "docs/taxonomy/deep/description.md",
    ]


def test_transitive_extends_preserves_shadowing_and_ambiguity(tmp_path):
    a, _, _ = transitive_taxonomy(tmp_path)
    st = FsTaxonomyStore.open(a)
    with pytest.raises(AmbiguousRef):
        st.get("shared")

    write_term(a, "shared", name="A Shared")
    assert FsTaxonomyStore.open(a).get("shared").origin == "local"


def test_transitive_extends_deduplicates_a_diamond_by_project_id(tmp_path):
    a, _, c = transitive_taxonomy(tmp_path)
    d = node(tmp_path, "delta")
    (a / "tcw-config.yaml").write_text(
        "id: alpha\nconnected-projects:\n  children:\n"
        "    bravo: ../bravo\n    delta: ../delta\n"
    )
    (d / "tcw-config.yaml").write_text(
        "id: delta\nconnected-projects:\n  parent:\n    alpha: ../alpha\n"
    )
    (c / "tcw-config.yaml").write_text(
        "id: charlie\nconnected-projects:\n  parent:\n    bravo: ../bravo\n"
    )
    write_config(a, "extends:\n  - bravo\n  - delta\n")
    write_config(d, "extends:\n  - charlie\n")

    qualified = [term.qualified for term in FsTaxonomyStore.open(a).list_all()]
    assert qualified.count("charlie/deep") == 1
    assert qualified.count("charlie/shared") == 1


def test_transitive_extends_crosses_a_second_hop_through_a_moved_tree(tmp_path):
    """`bravo` keeps its taxonomy somewhere other than `docs/taxonomy`.

    Resolving a sibling's *store* is what let `alpha` reach it at all; rebuilding
    that store from its root then broke the hop past it, because `FsTreeStore`
    falls back to `root.parent.parent` for the node root — correct only for the
    `docs/<component>` shape this resolution exists to stop assuming. `bravo`
    got a node root above its own repo, so its `extends: charlie` resolved
    against the wrong graph and `charlie` vanished from `alpha`'s view.
    """
    a, b, c = transitive_taxonomy(tmp_path)
    (b / "ledger").mkdir()
    for entry in (b / "docs" / "taxonomy").iterdir():
        entry.rename(b / "ledger" / entry.name)
    (b / "tcw-config.yaml").write_text(
        "id: bravo\ntaxonomy:\n  path: ledger\nconnected-projects:\n"
        "  parent:\n    alpha: ../alpha\n  children:\n    charlie: ../charlie\n"
    )

    st = FsTaxonomyStore.open(a)
    assert {(term.qualified, term.origin) for term in st.list_all()} == {
        ("bravo/shared", "bravo"),
        ("charlie/deep", "charlie"),
        ("charlie/shared", "charlie"),
    }
    assert st.check() == []
    assert st._validation_resources("charlie/deep") == [
        c / "docs/taxonomy/deep/meta.yaml",
        c / "docs/taxonomy/deep/description.md",
    ]


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
    connect_sources(cons, a, b)
    write_config(cons, "extends:\n  - a\n  - b\n")
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


def test_rm_refuses_ref_escaping_the_store(tmp_path):
    # Regression: `rm ../capabilities/thing` resolved through get_local's
    # unguarded root-join and DELETED the folder outside docs/taxonomy/.
    root = node(tmp_path, "repo")
    outside = root / "docs" / "capabilities" / "thing"
    outside.mkdir(parents=True)
    (outside / "meta.yaml").write_text("name: Thing\n")
    st = FsTaxonomyStore.open(root)
    assert st.get("../capabilities/thing") is None
    with pytest.raises(ValueError, match="no such term"):
        st.remove("../capabilities/thing")
    assert outside.is_dir()


def test_check_reports_escaping_ref_as_dangling(tmp_path):
    # A `..` ref already stored in a meta.yaml must be reported, not raised.
    root = node(tmp_path, "repo")
    write_term(root, "user", name="User")
    write_term(root, "feature", name="Feature", kind="Feature",
               vocabulary=["../../capabilities/thing"])
    problems = FsTaxonomyStore.open(root).check()
    assert any("dangling vocabulary" in p for p in problems)


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
    connect_sources(cons, a, b)
    write_config(cons, "extends:\n  - a\n  - b\n")
    write_term(cons, "host", relates_to=["Term"])
    problems = FsTaxonomyStore.open(cons).check()
    assert any("ambiguous" in p for p in problems)


def test_check_duplicate_project_id(tmp_path):
    cons = node(tmp_path, "consumer")
    other = node(tmp_path, "other")
    connect_sources(cons, other)
    write_config(cons, "extends:\n  - other\n  - other\n")
    with pytest.raises(ValueError, match="duplicate project IDs"):
        FsTaxonomyStore.open(cons)


def test_check_alias_collides_with_local_top_level(tmp_path):
    cons, _ = consumer_with_shared(tmp_path, alias="shared")
    write_term(cons, "shared", name="Shared (local)")
    problems = FsTaxonomyStore.open(cons).check()
    assert any("collides" in p for p in problems)


def test_check_cycle(tmp_path):
    a = node(tmp_path, "a")
    b = node(tmp_path, "b")
    connect_sources(a, b)
    write_config(a, "extends:\n  - b\n")
    write_config(b, "extends:\n  - a\n")
    problems = FsTaxonomyStore.open(a).check()
    assert any("cycle" in p for p in problems)


def test_check_unknown_extends_project(tmp_path):
    cons = node(tmp_path, "consumer")
    write_config(cons, "extends:\n  - ghost\n")
    with pytest.raises(ValueError, match="not reachable"):
        FsTaxonomyStore.open(cons)


# ── CLI smoke (bare-path sugar) ─────────────────────────────────────────────

def test_cli_bare_path_is_show(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path, "repo")
    monkeypatch.chdir(root)
    main(["taxonomy", "add", "Admin"])
    assert main(["taxonomy", "admin"]) == 0          # bare path → show
    assert "Admin" in capsys.readouterr().out


def test_cli_path_prints_resolved_store_root_and_reserves_command(tmp_path, monkeypatch,
                                                                  capsys):
    from tcw.cli import main
    root = node(tmp_path, "repo")
    write_term(root, "path", name="Path term")
    monkeypatch.chdir(root)

    assert main(["taxonomy", "path"]) == 0
    output = capsys.readouterr()
    assert output.out == f"{(root / 'docs/taxonomy').resolve()}\n"
    assert output.err == ""

    assert main(["taxonomy", "show", "path"]) == 0
    assert "Path term" in capsys.readouterr().out


def test_cli_path_outside_taxonomy_node_prints_no_path(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    monkeypatch.chdir(tmp_path)

    assert main(["taxonomy", "path"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "no tcw taxonomy node here" in output.err


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


def test_cli_list_does_not_interleave_hyphen_sibling_with_subtree(tmp_path, monkeypatch, capsys):
    """A hyphen-extended root slug must not capture another root's children.

    `-` (0x2D) sorts before `/` (0x2F), so keying the sort on the joined path put
    `event-reporting` between `event` and `event/log-batch` while indentation was
    derived independently from the segment count — rendering `event`'s children
    as though they belonged to `event-reporting`. The full ordered output is
    asserted, not mere membership: this was an ordering defect, so a membership
    assertion passes against the broken code.
    """
    from tcw.cli import main
    root = node(tmp_path, "repo")
    write_term(root, "event", name="Event")
    write_term(root, "event/log-batch", name="Log Batch")
    write_term(root, "event/stat", name="Stat")
    write_term(root, "event-reporting", name="Event Reporting", kind="Feature")
    monkeypatch.chdir(root)
    assert main(["taxonomy", "list"]) == 0
    assert capsys.readouterr().out == (
        "event  [V] (local)\n"
        "  log-batch  [V] (local)\n"
        "  stat  [V] (local)\n"
        "event-reporting  [F] (local)\n"
    )


def test_cli_list_is_depth_first_preorder_at_three_levels(tmp_path, monkeypatch, capsys):
    """Every term renders immediately after its parent, before the parent's next
    sibling, at any depth — and siblings stay alphabetical within a level."""
    from tcw.cli import main
    root = node(tmp_path, "repo")
    for slug in ("a", "a/b", "a/b/c", "a/b/c2", "a/d", "a-sibling"):
        write_term(root, slug, name=slug)
    monkeypatch.chdir(root)
    assert main(["taxonomy", "list"]) == 0
    assert capsys.readouterr().out == (
        "a  [V] (local)\n"
        "  b  [V] (local)\n"
        "    c  [V] (local)\n"
        "    c2  [V] (local)\n"
        "  d  [V] (local)\n"
        "a-sibling  [V] (local)\n"
    )


def test_cli_list_never_splices_an_inherited_tree_into_the_local_one(tmp_path, monkeypatch, capsys):
    """Each `extends` alias is a separate store with its own slug namespace, so
    an inherited tree groups after the local one rather than sorting into it."""
    from tcw.cli import main
    cons, shared = consumer_with_shared(tmp_path)
    write_term(shared, "Argument/nested", name="Nested")
    write_term(cons, "argument-local", name="Argument Local")
    monkeypatch.chdir(cons)
    assert main(["taxonomy", "list"]) == 0
    out = capsys.readouterr().out
    assert out == (
        "argument-local  [V] (local)\n"
        "Argument  [V] (shared)\n"
        "  nested  [V] (shared)\n"
    )


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
    assert main(["taxonomy", "init", "--id", "fresh"]) == 0
    comp_out = capsys.readouterr().out
    assert (root / "docs" / "taxonomy" / ".gitkeep").is_file()
    assert main(["init", "taxonomy"]) == 0          # idempotent; same report
    assert comp_out == capsys.readouterr().out


# ── extends (federation) write path ───────────────────────────────────────────

def test_extends_add_writes_map_and_resolves(tmp_path):
    base = node(tmp_path, "base")
    write_term(base, "widget", name="Widget")
    consumer = node(tmp_path, "consumer")
    connect_sources(consumer, base)
    FsTaxonomyStore.open(consumer).extends_add("base")
    st = FsTaxonomyStore.open(consumer)            # reopen to load the new federation
    assert "base/widget" in {t.qualified for t in st.list_all()}
    assert st.get("base/widget").name == "Widget"


def test_extends_add_refuses(tmp_path):
    base = node(tmp_path, "base")
    consumer = node(tmp_path, "consumer")
    connect_sources(consumer, base)
    FsTaxonomyStore.open(consumer).extends_add("base")
    st = FsTaxonomyStore.open(consumer)
    with pytest.raises(ValueError):               # duplicate alias
        st.extends_add("base")
    with pytest.raises(ValueError):               # missing target repo
        st.extends_add("nope")
    with pytest.raises(ValueError):               # self-reference
        st.extends_add("consumer")


def test_extends_remove(tmp_path):
    base = node(tmp_path, "base")
    consumer = node(tmp_path, "consumer")
    connect_sources(consumer, base)
    FsTaxonomyStore.open(consumer).extends_add("base")
    st = FsTaxonomyStore.open(consumer)
    st.extends_remove("base")
    assert "base" not in (FsTaxonomyStore.open(consumer).config.get("extends") or [])
    with pytest.raises(ValueError):               # absent alias
        FsTaxonomyStore.open(consumer).extends_remove("base")


def test_cli_extends_add_and_rm(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    base = node(tmp_path, "base")
    consumer = node(tmp_path, "consumer")
    connect_sources(consumer, base)
    monkeypatch.chdir(consumer)
    assert main(["taxonomy", "extends", "add", "base"]) == 0
    capsys.readouterr()
    assert (consumer / "docs/taxonomy/config.yaml").exists()
    assert main(["taxonomy", "extends", "add", "base"]) == 1
    assert "already exists" in capsys.readouterr().err
    assert main(["taxonomy", "extends", "rm", "base"]) == 0


def test_cli_extends_is_not_treated_as_a_term_path(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path, "repo")
    monkeypatch.chdir(root)
    # "extends" must dispatch to the subcommand, not the `taxonomy <path>` show-sugar
    assert main(["taxonomy", "extends", "rm", "ghost"]) == 1   # absent alias → handled error, not "no such term"
    assert "no such term" not in capsys.readouterr().err


# ── the extended store is resolved, not composed ─────────────────────────────

def test_a_sibling_that_moved_its_tree_can_still_be_extended(tmp_path):
    """`taxonomy.path` is exactly what `tcw init --taxonomy-path` writes.

    The extended project's store used to be composed as `docs/taxonomy` under
    its root, so a project that had moved its tree became unextendable and the
    error blamed a path nobody had written. Resolution is component-generic, so
    this is the taxonomy half of a fix whose capabilities half is already
    covered — and the half that would go unnoticed if the two ever diverged.
    """
    import shutil
    base = node(tmp_path, "base")
    elsewhere = base / "vocabulary"
    elsewhere.mkdir(parents=True)
    write_term(base, "argument", name="Argument", description="A claim with support.")
    shutil.move(str(base / "docs" / "taxonomy" / "argument"),
                str(elsewhere / "argument"))
    shutil.rmtree(base / "docs" / "taxonomy")
    (base / "tcw-config.yaml").write_text(
        "id: base\ntaxonomy:\n  path: vocabulary\n"
        "connected-projects:\n  children:\n    consumer: ../consumer\n"
    )

    cons = node(tmp_path, "consumer")
    (cons / "tcw-config.yaml").write_text(
        "id: consumer\nconnected-projects:\n  parent:\n    base: ../base\n"
    )
    write_config(cons, "extends:\n  - base\n")

    st = FsTaxonomyStore.open(cons)
    assert {term.qualified for term in st.list_all()} == {"base/argument"}
    assert st.get("base/argument").name == "Argument"
    assert st.get("argument").origin == "base"
