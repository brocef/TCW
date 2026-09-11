"""Tags on work items: per-node registry + apply/filter/validate (spec:
2026-07-17-add-tags-to-work-items-for-filtering)."""

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.base import normalize_tag
from tcw.store.fs import FsWorkStore, init
from tcw.validate import validate


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root)
    return root


# ── normalize ────────────────────────────────────────────────────────────────

def test_normalize_tag_slugifies():
    assert normalize_tag("Bug") == "bug"
    assert normalize_tag("  Tech Debt ") == "tech-debt"


def test_normalize_tag_rejects_empty():
    with pytest.raises(ValueError):
        normalize_tag("  ")


# ── registry round-trip ──────────────────────────────────────────────────────

def test_registered_tags_empty_by_default(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    assert st.registered_tags() == []


def test_register_normalizes_dedups_sorts_and_persists(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    assert st.register_tags(["Bug", "tech-debt", "bug"]) == ["bug", "tech-debt"]
    # persisted: a fresh store sees them
    assert FsWorkStore.open(root).registered_tags() == ["bug", "tech-debt"]
    # idempotent
    assert st.register_tags(["bug"]) == ["bug", "tech-debt"]


def test_registered_tags_tolerates_non_dict_work_config(tmp_path):
    root = node(tmp_path)
    (root / "tcw-config.yaml").write_text("work: enabled\n")   # hand-edited to a scalar
    assert FsWorkStore.open(root).registered_tags() == []      # no crash


def test_malformed_config_raises_clear_error(tmp_path):
    root = node(tmp_path)
    (root / "tcw-config.yaml").write_text("- just\n- a\n- list\n")  # valid YAML, wrong shape
    with pytest.raises(ValueError, match="malformed"):
        FsWorkStore.open(root).registered_tags()


def test_unregister(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    st.register_tags(["bug", "tech-debt"])
    assert st.unregister_tags(["bug"]) == ["tech-debt"]
    assert st.registered_tags() == ["tech-debt"]


# ── apply on create / update ─────────────────────────────────────────────────

def test_create_with_registered_tag(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    st.register_tags(["bug"])
    detail = st.create_work("X", created="2026-01-01", tags=["Bug"])
    assert detail.item.tags == ["bug"]
    assert st.get(detail.item.slug).tags == ["bug"]


def test_create_with_unregistered_tag_rejected_and_creates_nothing(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    with pytest.raises(ValueError):
        st.create_work("Y", created="2026-01-01", tags=["nope"])
    assert st.query() == []


def test_update_add_and_remove_tags(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    st.register_tags(["bug", "urgent"])
    slug = st.create_work("Z", created="2026-01-01", tags=["bug"]).item.slug
    st.update_work(slug, tags=["urgent"])
    assert st.get(slug).tags == ["urgent"]


def test_update_unregistered_tag_rejected(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    slug = st.create_work("Z", created="2026-01-01").item.slug
    with pytest.raises(ValueError):
        st.update_work(slug, tags=["nope"])


def test_tagless_item_omits_tags_key(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    slug = st.create_work("plain", created="2026-01-01").item.slug
    state = (st.path(slug) / "state.yaml").read_text()
    assert "tags" not in state
    assert st.get(slug).tags == []


# ── validation ───────────────────────────────────────────────────────────────

def test_check_flags_stale_tag(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug"])
    slug = st.create_work("stale", created="2026-01-01", tags=["bug"]).item.slug
    st.unregister_tags(["bug"])            # tag now stale on the item
    problems = st.check()
    assert any(slug in p and "bug" in p for p in problems)
    # surfaced through the aggregate validate() pass too
    assert any("work check" in p and slug in p for p in validate(root))


def test_validate_reports_malformed_config_without_crashing(tmp_path):
    root = node(tmp_path)
    (root / "tcw-config.yaml").write_text("- not\n- a\n- mapping\n")
    problems = validate(root)                          # must not raise
    assert any("project graph" in p and "config must be a mapping" in p for p in problems)


# ── CLI end-to-end ───────────────────────────────────────────────────────────

def test_cli_register_apply_list_filter(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tags", "add", "bug"]) == 0
    capsys.readouterr()
    assert main(["work", "new", "Boom", "--tag", "bug"]) == 0
    slug = capsys.readouterr().out.strip().splitlines()[0]
    state = (FsWorkStore.open(root).path(slug) / "state.yaml").read_text()
    assert "tags:" in state and "bug" in state

    assert main(["work", "list", "--tag", "bug"]) == 0
    assert slug in capsys.readouterr().out
    assert main(["work", "list", "--tag", "other"]) == 0
    assert slug not in capsys.readouterr().out


def test_cli_new_unregistered_tag_fails(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "new", "Nope", "--tag", "ghost"]) == 1
    assert "unregistered tag" in capsys.readouterr().err
    assert FsWorkStore.open(root).query() == []


def test_cli_edit_tag_and_untag(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug", "urgent"])
    slug = st.create_work("E", created="2026-01-01", tags=["bug"]).item.slug
    monkeypatch.chdir(root)
    assert main(["work", "edit", slug, "--tag", "urgent", "--untag", "bug"]) == 0
    assert FsWorkStore.open(root).get(slug).tags == ["urgent"]
    capsys.readouterr()
    assert main(["work", "show", slug]) == 0
    assert "tags: urgent" in capsys.readouterr().out


def test_cli_tags_rm_warns_about_stale_items(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug"])
    slug = st.create_work("S", created="2026-01-01", tags=["bug"]).item.slug
    monkeypatch.chdir(root)
    assert main(["work", "tags", "rm", "bug"]) == 0
    assert slug in capsys.readouterr().err


# ── comma-separated tags (spec: 2026-08-11-accept-comma-separated-tags-on-tcw-work-new)

def _tagged_node(tmp_path, monkeypatch, *tags):
    root = node(tmp_path)
    FsWorkStore.open(root).register_tags(list(tags))
    monkeypatch.chdir(root)
    return root


def _new(capsys, *argv):
    """Run `tcw work new` and return the created slug."""
    assert main(["work", "new", *argv]) == 0
    return capsys.readouterr().out.strip().splitlines()[0]


def test_cli_tags_option_splits_on_commas(tmp_path, monkeypatch, capsys):
    root = _tagged_node(tmp_path, monkeypatch, "cli", "docs")
    slug = _new(capsys, "X", "--tags", "cli,docs")
    assert FsWorkStore.open(root).get(slug).tags == ["cli", "docs"]


def test_cli_singular_tag_also_splits_on_commas(tmp_path, monkeypatch, capsys):
    """The reported papercut is --tags; this is the defect underneath it. Before
    the fix `cli,docs` normalized to the single tag `cli-docs`."""
    root = _tagged_node(tmp_path, monkeypatch, "cli", "docs")
    slug = _new(capsys, "X", "--tag", "cli,docs")
    assert FsWorkStore.open(root).get(slug).tags == ["cli", "docs"]


def test_cli_tag_spellings_compose_in_either_order(tmp_path, monkeypatch, capsys):
    root = _tagged_node(tmp_path, monkeypatch, "cli", "docs")
    a = _new(capsys, "A", "--tag", "cli", "--tags", "docs")
    b = _new(capsys, "B", "--tags", "docs", "--tag", "cli")
    st = FsWorkStore.open(root)
    # Order is insertion order all the way down, so the spellings do not
    # reorder anything — b really is docs-then-cli, not sorted.
    assert st.get(a).tags == ["cli", "docs"]
    assert st.get(b).tags == ["docs", "cli"]


def test_cli_duplicate_tags_collapse(tmp_path, monkeypatch, capsys):
    root = _tagged_node(tmp_path, monkeypatch, "cli")
    a = _new(capsys, "A", "--tags", "cli,cli")
    b = _new(capsys, "B", "--tag", "cli", "--tags", "cli")
    st = FsWorkStore.open(root)
    assert st.get(a).tags == ["cli"]
    assert st.get(b).tags == ["cli"]


def test_cli_tags_tolerates_blank_segments_and_spacing(tmp_path, monkeypatch, capsys):
    root = _tagged_node(tmp_path, monkeypatch, "cli", "docs")
    a = _new(capsys, "A", "--tags", "cli,,docs")
    b = _new(capsys, "B", "--tags", "cli, docs")
    st = FsWorkStore.open(root)
    assert st.get(a).tags == ["cli", "docs"]
    assert st.get(b).tags == ["cli", "docs"]


@pytest.mark.parametrize("value", ["", ",,"])
def test_cli_tags_refuses_a_value_that_yields_nothing(tmp_path, monkeypatch, capsys, value):
    """Blank segments are ignored, but an occurrence must yield at least one tag.
    The message echoes the value as typed, so ',,' is not reported as ''."""
    root = _tagged_node(tmp_path, monkeypatch, "cli")
    with pytest.raises(SystemExit):
        main(["work", "new", "X", "--tags", value])
    assert f"invalid tag {value!r}" in capsys.readouterr().err
    assert FsWorkStore.open(root).query() == []


def test_cli_tags_refuses_an_unregistered_token_and_creates_nothing(tmp_path, monkeypatch, capsys):
    root = _tagged_node(tmp_path, monkeypatch, "cli")
    assert main(["work", "new", "X", "--tags", "cli,nope"]) == 1
    assert "unregistered tag 'nope'" in capsys.readouterr().err
    assert FsWorkStore.open(root).query() == []


def test_cli_tags_refuses_a_nonblank_invalid_token(tmp_path, monkeypatch, capsys):
    """`!!!` normalizes to nothing. It is refused, not silently discarded."""
    root = _tagged_node(tmp_path, monkeypatch, "cli")
    with pytest.raises(SystemExit):
        main(["work", "new", "X", "--tags", "cli,!!!"])
    # Name the token, not just the words: this must be distinguishable from
    # rejecting the whole value.
    assert "'!!!'" in capsys.readouterr().err
    assert FsWorkStore.open(root).query() == []


def test_cli_edit_tags_and_untags(tmp_path, monkeypatch, capsys):
    root = _tagged_node(tmp_path, monkeypatch, "cli", "docs", "web")
    slug = _new(capsys, "E", "--tags", "cli,docs")
    assert main(["work", "edit", slug, "--tags", "web"]) == 0
    assert FsWorkStore.open(root).get(slug).tags == ["cli", "docs", "web"]
    assert main(["work", "edit", slug, "--untags", "cli,docs"]) == 0
    assert FsWorkStore.open(root).get(slug).tags == ["web"]


def test_cli_edit_add_still_wins_over_remove(tmp_path, monkeypatch, capsys):
    """Pre-existing behaviour: the same tag added and removed stays applied."""
    root = _tagged_node(tmp_path, monkeypatch, "cli")
    slug = _new(capsys, "E", "--tags", "cli")
    assert main(["work", "edit", slug, "--tag", "cli", "--untag", "cli"]) == 0
    assert FsWorkStore.open(root).get(slug).tags == ["cli"]


def test_cli_untags_ignores_a_tag_the_item_does_not_carry(tmp_path, monkeypatch, capsys):
    """Removal does not check the registry, and never has: `--untag nope`
    succeeds as a no-op today. The asymmetry with `--tag` is deliberate —
    applying an unregistered tag writes bad data, removing one cannot — so a
    comma list inherits it rather than tightening it."""
    root = _tagged_node(tmp_path, monkeypatch, "cli", "docs")
    slug = _new(capsys, "E", "--tags", "cli,docs")
    assert main(["work", "edit", slug, "--untags", "cli,nope"]) == 0
    assert FsWorkStore.open(root).get(slug).tags == ["docs"]


def test_cli_list_filter_splits_on_commas(tmp_path, monkeypatch, capsys):
    """Four fixtures, so an AND filter cannot pass this."""
    _tagged_node(tmp_path, monkeypatch, "cli", "docs")
    only_cli = _new(capsys, "OnlyCli", "--tags", "cli")
    only_docs = _new(capsys, "OnlyDocs", "--tags", "docs")
    both = _new(capsys, "Both", "--tags", "cli,docs")
    neither = _new(capsys, "Neither")
    assert main(["work", "list", "--tags", "cli,docs"]) == 0
    out = capsys.readouterr().out
    assert only_cli in out and only_docs in out and both in out
    assert neither not in out
    # Parity is the criterion's actual words: the comma spelling must mean the
    # same thing as the repeated flag, not merely filter with OR.
    assert main(["work", "list", "--tag", "cli", "--tag", "docs"]) == 0
    assert capsys.readouterr().out == out


def test_cli_tags_add_splits_on_commas(tmp_path, monkeypatch, capsys):
    """The corruption path. Before the fix this registered the single tag
    `cli-docs`, `tcw validate` reported OK, and every later `--tag cli,docs`
    silently applied it."""
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tags", "add", "cli,docs"]) == 0
    assert FsWorkStore.open(root).registered_tags() == ["cli", "docs"]


def test_cli_tags_add_splits_across_several_positionals(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tags", "add", "cli,docs", "web"]) == 0
    assert FsWorkStore.open(root).registered_tags() == ["cli", "docs", "web"]


def test_cli_tags_rm_splits_on_commas(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    FsWorkStore.open(root).register_tags(["cli", "docs", "web"])
    monkeypatch.chdir(root)
    assert main(["work", "tags", "rm", "cli,docs"]) == 0
    assert FsWorkStore.open(root).registered_tags() == ["web"]


def test_cli_tags_rm_no_longer_targets_a_joined_tag(tmp_path, monkeypatch, capsys):
    """A node poisoned before the fix keeps its joined tag. `tags rm cli,docs`
    now means the two tags, so it does not remove `cli-docs` by accident."""
    root = node(tmp_path)
    FsWorkStore.open(root).register_tags(["cli-docs"])
    monkeypatch.chdir(root)
    assert main(["work", "tags", "rm", "cli,docs"]) == 0
    assert FsWorkStore.open(root).registered_tags() == ["cli-docs"]


@pytest.mark.parametrize("value", ["", ",,"])
def test_cli_tags_add_refuses_a_value_that_yields_nothing(tmp_path, monkeypatch, capsys, value):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tags", "add", value]) != 0
    # Echo the value as typed, so ',,' is not reported as ''. Without this the
    # test passes unchanged against the pre-fix code.
    assert f"invalid tag {value!r}" in capsys.readouterr().err
    assert FsWorkStore.open(root).registered_tags() == []


def test_cli_new_blocked_by_keeps_a_comma_in_free_text(tmp_path, monkeypatch, capsys):
    """The non-goal, pinned. `--blocked-by` takes a slug or free prose, so a
    comma there is a character and not a separator."""
    root = node(tmp_path)
    monkeypatch.chdir(root)
    slug = _new(capsys, "B", "--blocked-by", "external: waiting on Acme, Inc.")
    blockers = FsWorkStore.open(root).get(slug).blocked_by
    assert len(blockers) == 1, "the comma must not have split this into two"
    assert "Acme, Inc." in str(blockers[0])


def test_cli_tags_add_is_all_or_nothing_across_positionals(tmp_path, monkeypatch, capsys):
    """`_tag_args` is a comprehension, so a bad value raises before
    `register_tags` is reached. Nothing else makes this true."""
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tags", "add", "cli", ""]) != 0
    assert FsWorkStore.open(root).registered_tags() == []


def test_cli_list_include_descendants_splits_the_tag_filter(tmp_path, monkeypatch, capsys):
    """`-i` passes the tag list positionally, on a different code path from the
    plain board."""
    _tagged_node(tmp_path, monkeypatch, "cli", "docs")
    tagged = _new(capsys, "Tagged", "--tags", "cli")
    untagged = _new(capsys, "Untagged")
    assert main(["work", "list", "-i", "--tags", "cli,docs"]) == 0
    out = capsys.readouterr().out
    assert tagged in out and untagged not in out


def test_cli_edit_tags_unregistered_token_leaves_the_item_untouched(tmp_path, monkeypatch, capsys):
    root = _tagged_node(tmp_path, monkeypatch, "cli", "docs", "web")
    slug = _new(capsys, "E", "--tags", "cli")
    assert main(["work", "edit", slug, "--tags", "web,nope"]) != 0
    assert FsWorkStore.open(root).get(slug).tags == ["cli"]
