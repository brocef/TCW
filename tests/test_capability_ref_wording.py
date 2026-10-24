"""The exact wording of every capability cross-object ref problem.

**These are characterization tests, and the literals are the contract.** They
exist because `check` and the write path are about to share one renderer, and
a parity test between two consumers of the same renderer proves only that they
agree — it cannot catch the renderer changing both sides together.

The existing assertions in `tests/test_capabilities.py` are all substrings
(`any("Subject" in p and "ghost" in p …)`), so the suite would stay green
through a wording change. Copy the expected strings from the item's plan, not
from the source: a test that mirrors the code asserts nothing.

All fifteen rows of the plan's message table are covered. The four
ambiguous-*identifier* variants needed a federated fixture rather than a plain
one — capabilities are path-addressed, so "ambiguous" means the same path in two
extended stores, never a leaf-slug clash. An earlier revision of this file
claimed full coverage while omitting them; adversarial review caught the claim.

Since TCW-110 a stored reference is a full identifier (Design 5.1), so it can
no longer be ambiguous: the ambiguous wordings are now the write path's, for
an id-path given as input, and a stored value in a 3.x form is reported naming
`tcw migrate` (Design 5.2).
"""

import hashlib
import subprocess

import pytest
import yaml

from tcw.store.base import Term
from tcw.store.fs import FsCapabilitiesStore, write_sentinel
from tcw.errors import TcwError
from tests.fullids import fid
from tests.projectfiles import write_config, write_manifest
from tests.statefiles import write_state, CAPABILITY_STATE, TAXONOMY_STATE


def node(tmp_path, name="repo"):
    root = tmp_path / name
    (root / "docs" / "capabilities").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root, name)
    return root


def write_cap(root, path, body="", **meta):
    d = root / "docs" / "capabilities" / path
    d.mkdir(parents=True, exist_ok=True)
    m = {"id": "cap-" + hashlib.sha1(path.encode()).hexdigest()[:6],
         "name": path.rsplit("/", 1)[-1].replace("-", " ").title()}
    m.update(meta)
    write_state(d / CAPABILITY_STATE, yaml.safe_dump(m, sort_keys=False, allow_unicode=True))
    (d / "description.md").write_text(body)


def C(path: str) -> str:
    """A capability of the project `repo`, as a record stores it."""
    return fid("repo", "capabilities", path)


def T(slug: str) -> str:
    """A taxonomy entry of the project `repo`, as a record stores it."""
    return fid("repo", "taxonomy", slug)


class Tax:
    """A taxonomy stub for the project `repo`: `known` maps an id-path to
    its kind. It inherits from nothing."""

    project_id = "repo"

    def __init__(self, known=None):
        self.known = known or {}

    def _inherited(self):
        return {}

    def get_local(self, slug):
        kind = self.known.get(slug)
        return None if kind is None else Term(
            slug=slug, name=slug, description="", kind=kind,
            relates_to=[], vocabulary=[], attachments=[], origin="local",
            owner="repo")


def problems_for(tmp_path, taxonomy=None, **meta):
    """`check`'s problems for one capability, with the `<path>: ` prefix removed."""
    root = node(tmp_path)
    write_cap(root, "x", Status="Supported", **meta)
    out = FsCapabilitiesStore.open(root).check(taxonomy=taxonomy)
    assert all(p.where == "docs/capabilities/x" for p in out), out
    return [p.message for p in out]


# ── the fifteen strings ──────────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["Superseded by", "Blocked by"])
def test_dangling_identifier_wording(tmp_path, field):
    assert (f"{field} → dangling identifier '{C('routes/ghost')}'"
            in problems_for(tmp_path, **{field: C("routes/ghost")}))


@pytest.mark.parametrize("field", ["Roles", "When"])
def test_namespace_rule_wording_keeps_the_negation_marker(tmp_path, field):
    """The non-arrow variant. The token keeps its `!` here and loses it in the
    arrow messages — both shapes must survive the extraction."""
    token = f"!{C('nope')}"
    assert (f"{field} '{token}' must be a "
            f"{'roles' if field == 'Roles' else 'conditions'}/ slug"
            in problems_for(tmp_path, **{field: token}))


def test_roles_dangling_identifier_wording_strips_the_negation_marker(tmp_path):
    assert f"Roles → dangling identifier '{C('roles/ghost')}'" in problems_for(
        tmp_path, Roles=f"!{C('roles/ghost')}")


def test_when_dangling_identifier_wording(tmp_path):
    assert f"When → dangling identifier '{C('conditions/ghost')}'" in problems_for(
        tmp_path, When=C("conditions/ghost"))


def test_subject_dangling_ref_wording(tmp_path):
    assert f"Subject → dangling ref '{T('ghost')}'" in problems_for(
        tmp_path, Subject=T("ghost"), taxonomy=Tax({"user": "Vocabulary"}))


def test_feature_dangling_ref_wording(tmp_path):
    assert f"Feature → dangling ref '{T('ghost')}'" in problems_for(
        tmp_path, Feature=T("ghost"), taxonomy=Tax({"real": "Feature"}))


def test_feature_wrong_kind_wording_is_one_line_with_a_single_space(tmp_path):
    """Written across two source lines; it must concatenate to exactly this."""
    assert (f"Feature → ref '{T('user')}' points to Vocabulary, expected Feature"
            in problems_for(tmp_path, Feature=T("user"),
                            taxonomy=Tax({"user": "Vocabulary"})))


@pytest.mark.parametrize("field, value, namespace", [
    ("Subject", "ghost", "taxonomy"),
    ("Feature", "ghost", "taxonomy"),
    ("Superseded by", "routes/ghost", "capabilities"),
    ("Blocked by", "routes/ghost", "capabilities"),
    ("Roles", "!roles/ghost", "capabilities"),
    ("When", "conditions/ghost", "capabilities"),
])
def test_a_3x_value_is_reported_naming_the_field_and_tcw_migrate(
        tmp_path, field, value, namespace):
    """TCW-110 AC 11: a stored value in a 3.x form, with no `.` before its
    first `/`, is reported where it is read."""
    bare = value.lstrip("!")
    assert (f"{field} → '{bare}' is a TCW 3.x reference; TCW 4 writes "
            f"<project>.{namespace}/<id-path> (run 'tcw migrate' in this project)"
            in problems_for(tmp_path, taxonomy=Tax(), **{field: value}))


def test_the_location_prefix_is_the_capability_path(tmp_path):
    """The location `_ref_problems` must NOT include — the caller adds it, as
    the finding's `where`."""
    root = node(tmp_path)
    write_cap(root, "routes/login", Status="Supported", Subject=T("ghost"))
    out = FsCapabilitiesStore.open(root).check(taxonomy=Tax({"user": "Vocabulary"}))
    assert ("docs/capabilities/routes/login", f"Subject → dangling ref '{T('ghost')}'") \
        in [(p.where, p.message) for p in out]


def test_a_clean_capability_reports_nothing(tmp_path):
    """The control: every assertion above is about a string being present."""
    assert problems_for(
        tmp_path, Subject=T("user"), Feature=T("real"),
        taxonomy=Tax({"user": "Vocabulary", "real": "Feature"})) == []


# ── check's taxonomy fallback ────────────────────────────────────────────────

class RecordingTax(Tax):
    """A stub that records being consulted — and is falsey.

    Both halves matter. Asserting only the output cannot tell "the injected
    stub was used" from "the default store happened to agree", and `or` would
    silently discard a falsey store where `is not None` keeps it.
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.calls = []

    def __bool__(self):
        return False

    def get_local(self, slug):
        self.calls.append(slug)
        return super().get_local(slug)


def test_check_without_a_taxonomy_resolves_against_the_nodes_own(tmp_path):
    """Today this silently skips Subject/Feature entirely, so the two write
    surfaces and `check` could disagree about *whether* a ref is checked."""
    root = node(tmp_path)
    (root / "docs" / "taxonomy").mkdir(parents=True)
    write_cap(root, "x", Status="Supported", Subject=T("ghost"))
    problems = FsCapabilitiesStore.open(root).check()
    assert any(f"Subject → dangling ref '{T('ghost')}'" in p.message for p in problems)


def test_an_explicitly_passed_falsey_taxonomy_still_wins(tmp_path):
    root = node(tmp_path)
    (root / "docs" / "taxonomy").mkdir(parents=True)
    write_cap(root, "x", Status="Supported", Subject=T("user"))
    stub = RecordingTax({"user": "Vocabulary"})
    problems = FsCapabilitiesStore.open(root).check(taxonomy=stub)
    assert stub.calls == ["user"], "the injected stub was not consulted"
    assert problems == []


def test_a_node_without_a_taxonomy_component_still_skips_subject(tmp_path):
    """No `docs/taxonomy/` means nothing to resolve against — the existing
    degradation, not a new one."""
    root = node(tmp_path)
    write_cap(root, "x", Status="Supported", Subject=T("ghost"))
    assert FsCapabilitiesStore.open(root).check() == []


# ── the write path refuses what check would report ───────────────────────────

def _node_with_taxonomy(tmp_path):
    """A node whose taxonomy holds `thing` (Vocabulary) and `real-feature`."""
    root = node(tmp_path)
    tax = root / "docs" / "taxonomy"
    for slug, kind in (("thing", "Vocabulary"), ("real-feature", "Feature")):
        d = tax / slug
        d.mkdir(parents=True)
        write_state(d / TAXONOMY_STATE, f"name: {slug}\nkind: {kind}\nrelatesTo: []\n")
        (d / "description.md").write_text("x")
    write_cap(root, "web/editing", Status="Supported")
    return root


@pytest.mark.parametrize("field,value,expected", [
    ("Subject", "no-such-term", "Subject → dangling ref 'no-such-term'"),
    ("Feature", "also-bogus", "Feature → dangling ref 'also-bogus'"),
    ("Feature", "thing",
     "Feature → ref 'repo.taxonomy/thing' points to Vocabulary, expected Feature"),
    ("Superseded by", "nope", "Superseded by → dangling identifier 'nope'"),
    ("Blocked by", "nope2", "Blocked by → dangling identifier 'nope2'"),
    ("Roles", "roles/admin", "Roles → dangling identifier 'roles/admin'"),
    ("When", "conditions/offline", "When → dangling identifier 'conditions/offline'"),
])
def test_set_refuses_an_unresolvable_ref_and_writes_nothing(
        tmp_path, field, value, expected):
    root = _node_with_taxonomy(tmp_path)
    meta = root / "docs" / "capabilities" / "web" / "editing" / CAPABILITY_STATE
    before = meta.read_bytes()
    store = FsCapabilitiesStore.open(root)
    with pytest.raises(TcwError) as e:
        store.set("web/editing", {field: value})
    assert expected in str(e.value)
    assert meta.read_bytes() == before, "a refused write must write nothing"


def test_set_reports_every_bad_ref_not_just_the_first(tmp_path):
    root = _node_with_taxonomy(tmp_path)
    store = FsCapabilitiesStore.open(root)
    with pytest.raises(TcwError) as e:
        store.set("web/editing", {"Subject": "no-such-term", "Feature": "also-bogus"})
    parts = set(str(e.value).split("; "))
    assert parts == {"Subject → dangling ref 'no-such-term'",
                     "Feature → dangling ref 'also-bogus'"}


def test_set_accepts_refs_that_resolve(tmp_path):
    root = _node_with_taxonomy(tmp_path)
    store = FsCapabilitiesStore.open(root)
    store.set("web/editing", {"Subject": "thing", "Feature": "real-feature"})
    assert FsCapabilitiesStore.open(root).check() == []


def test_a_capability_with_a_stored_bad_ref_stays_repairable(tmp_path):
    """The route `tcw work complete` recommends. Validating the merged node
    instead of the supplied fields would make bad data unrepairable through the
    CLI that exists to repair it."""
    root = _node_with_taxonomy(tmp_path)
    write_cap(root, "broken", Status="Supported", Subject="ghost")
    store = FsCapabilitiesStore.open(root)
    store.set("broken", {"Status": "Omitted"})
    assert store.get_local("broken").fields["Status"] == "Omitted"


def test_the_refusal_and_check_agree_word_for_word(tmp_path):
    """One renderer, checked behaviourally across both consumers."""
    root = _node_with_taxonomy(tmp_path)
    store = FsCapabilitiesStore.open(root)
    with pytest.raises(TcwError) as e:
        store.set("web/editing", {"Subject": T("no-such-term")})
    write_cap(root, "mirror", Status="Supported", Subject=T("no-such-term"))
    from_check = [p.message for p in FsCapabilitiesStore.open(root).check()
                  if p.where == "docs/capabilities/mirror"]
    assert str(e.value) in from_check


def test_a_taxonomy_less_node_still_accepts_subject_but_refuses_blocked_by(tmp_path):
    """Goal 1's stated qualification: with nothing to resolve against,
    Subject/Feature pass. The other four resolve against the store itself and
    are validated regardless."""
    root = node(tmp_path)
    write_cap(root, "x", Status="Supported")
    store = FsCapabilitiesStore.open(root)
    store.set("x", {"Subject": "anything"})
    with pytest.raises(TcwError, match="Blocked by"):
        store.set("x", {"Blocked by": "nope"})


# ── a rejected create writes nothing ─────────────────────────────────────────

@pytest.mark.parametrize("fields,status", [
    ({"Feature": "also-bogus"}, "Missing"),
    ({"NotAField": "x"}, "Missing"),
    ({}, "InvalidStatus"),
])
def test_add_with_bad_fields_creates_no_folder(tmp_path, fields, status):
    """One write, so validation happens before anything is created. Fixes the
    class — bad ref, unknown field and invalid Status alike — not one input."""
    root = _node_with_taxonomy(tmp_path)
    store = FsCapabilitiesStore.open(root)
    with pytest.raises(TcwError):
        store.add("new/thing", name="Thing", status=status, fields=fields)
    assert not (root / "docs" / "capabilities" / "new" / "thing").exists()


def test_add_with_valid_fields_writes_them(tmp_path):
    root = _node_with_taxonomy(tmp_path)
    store = FsCapabilitiesStore.open(root)
    store.add("new/thing", name="Thing", status="Supported",
              fields={"Feature": "real-feature"})
    cap = FsCapabilitiesStore.open(root).get_local("new/thing")
    assert cap is not None and cap.fields.get("Feature") == T("real-feature")


def test_add_without_fields_is_unchanged(tmp_path):
    """The control: every existing caller omits the new keyword."""
    root = _node_with_taxonomy(tmp_path)
    store = FsCapabilitiesStore.open(root)
    store.add("plain/thing", name="Plain", status="Supported")
    assert FsCapabilitiesStore.open(root).get_local("plain/thing") is not None


# ── the four ambiguous-identifier variants ───────────────────────────────────
#
# These four resolve against the capability store itself, and capabilities are
# path-addressed — so "ambiguous" here is not a leaf-slug clash. It means the
# same path exists in more than one *extended* store, which is why this needs a
# child federating two bases rather than a plain fixture.

def _two_bases(tmp_path):
    """A child extending two projects that both hold the same capability path.

    The child names both bases as parents passing their capabilities, and the
    bases name nothing.
    """
    bases = []
    for name in ("alpha", "beta"):
        base = node(tmp_path, name)
        for path in ("dup", "roles/dup", "conditions/dup"):
            write_cap(base, path, Status="Supported")
        bases.append(base)
    child = node(tmp_path, "child")
    parents = "".join(f"- id: {b.name}\n  inherit: [capabilities]\n" for b in bases)
    write_config(child, f"id: child\nparents:\n{parents}")
    write_manifest(child, {b.name: f"../{b.name}" for b in bases})
    for name in ("alpha", "beta"):
        FsCapabilitiesStore.open(child).extends_add(name)
    return child


@pytest.mark.parametrize("field,value,expected", [
    ("Superseded by", "dup", "Superseded by \u2192 ambiguous identifier 'dup'"),
    ("Blocked by", "dup", "Blocked by \u2192 ambiguous identifier 'dup'"),
    ("Roles", "roles/dup", "Roles \u2192 ambiguous identifier 'roles/dup'"),
    ("When", "conditions/dup", "When \u2192 ambiguous identifier 'conditions/dup'"),
])
def test_ambiguous_identifier_wording(tmp_path, field, value, expected):
    """An id-path given to a write that two extended projects both hold."""
    child = _two_bases(tmp_path)
    write_cap(child, "x", Status="Supported")
    with pytest.raises(TcwError) as e:
        FsCapabilitiesStore.open(child).set("x", {field: value})
    assert expected in str(e.value)


# ── field values that are not strings ────────────────────────────────────────

def test_a_non_string_ref_is_refused_rather_than_crashing(tmp_path):
    """`Feature: 1` used to reach the resolver untouched and escape as
    AttributeError — an HTTP 500 rather than the documented 422 refusal."""
    root = _node_with_taxonomy(tmp_path)
    store = FsCapabilitiesStore.open(root)
    with pytest.raises(TcwError) as e:
        store.set("web/editing", {"Feature": 1})
    assert "Feature → dangling ref '1'" in str(e.value)


def test_a_non_string_subject_is_refused_rather_than_crashing(tmp_path):
    root = _node_with_taxonomy(tmp_path)
    store = FsCapabilitiesStore.open(root)
    with pytest.raises(TcwError) as e:
        store.set("web/editing", {"Subject": [1, 2]})
    assert "Subject → dangling ref '1'" in str(e.value)


def test_add_with_a_null_field_clears_it_as_add_then_set_did(tmp_path):
    """`fields={"Status": None}` must pop the Status seeded by the `status`
    argument. Skipping the sentinel would keep a value the caller asked to
    clear, which the create-then-set sequence this replaced did not."""
    root = _node_with_taxonomy(tmp_path)
    store = FsCapabilitiesStore.open(root)
    store.add("new/thing", name="Thing", status="Supported", fields={"Status": None})
    meta = yaml.safe_load(
        (root / "docs" / "capabilities" / "new" / "thing" / CAPABILITY_STATE).read_text())
    assert "Status" not in meta
