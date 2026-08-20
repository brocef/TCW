"""The exact wording of every capability cross-object ref problem.

**These are characterization tests, and the literals are the contract.** They
exist because `check` and the write path are about to share one renderer, and
a parity test between two consumers of the same renderer proves only that they
agree — it cannot catch the renderer changing both sides together.

The existing assertions in `tests/test_capabilities.py` are all substrings
(`any("Subject" in p and "ghost" in p …)`), so the suite would stay green
through a wording change. Copy the expected strings from the item's plan, not
from the source: a test that mirrors the code asserts nothing.
"""

import hashlib
import subprocess

import pytest
import yaml

from tcw.store.base import AmbiguousRef, Term
from tcw.store.fs import FsCapabilitiesStore, write_sentinel


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
    (d / "meta.yaml").write_text(yaml.safe_dump(m, sort_keys=False, allow_unicode=True))
    (d / "description.md").write_text(body)


class Tax:
    """A taxonomy stub: `known` maps ref → kind; `ambiguous` refs raise."""

    def __init__(self, known=None, ambiguous=()):
        self.known = known or {}
        self.ambiguous = set(ambiguous)

    def get(self, ref):
        if ref in self.ambiguous:
            raise AmbiguousRef(ref)
        kind = self.known.get(ref)
        return None if kind is None else Term(
            slug=ref, name=ref, description="", kind=kind,
            relates_to=[], vocabulary=[], attachments=[], origin="local")


def problems_for(tmp_path, taxonomy=None, **meta):
    """`check`'s problems for one capability, with the `<path>: ` prefix removed."""
    root = node(tmp_path)
    write_cap(root, "x", Status="Supported", **meta)
    out = FsCapabilitiesStore.open(root).check(taxonomy=taxonomy)
    return [p.removeprefix("x: ") for p in out]


# ── the fifteen strings ──────────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["Superseded by", "Blocked by"])
def test_dangling_identifier_wording(tmp_path, field):
    assert (f"{field} → dangling identifier 'routes/ghost'"
            in problems_for(tmp_path, **{field: "routes/ghost"}))


@pytest.mark.parametrize("field", ["Roles", "When"])
def test_namespace_rule_wording_keeps_the_negation_marker(tmp_path, field):
    """The non-arrow variant. The token keeps its `!` here and loses it in the
    arrow messages — both shapes must survive the extraction."""
    assert (f"{field} '!nope' must be a {'roles' if field == 'Roles' else 'conditions'}/ slug"
            in problems_for(tmp_path, **{field: "!nope"}))


def test_roles_dangling_identifier_wording_strips_the_negation_marker(tmp_path):
    assert "Roles → dangling identifier 'roles/ghost'" in problems_for(
        tmp_path, Roles="!roles/ghost")


def test_when_dangling_identifier_wording(tmp_path):
    assert "When → dangling identifier 'conditions/ghost'" in problems_for(
        tmp_path, When="conditions/ghost")


def test_subject_dangling_ref_wording(tmp_path):
    assert "Subject → dangling ref 'ghost'" in problems_for(
        tmp_path, Subject="ghost", taxonomy=Tax({"user": "Vocabulary"}))


def test_subject_ambiguous_ref_wording(tmp_path):
    assert "Subject → ambiguous ref 'dup'" in problems_for(
        tmp_path, Subject="dup", taxonomy=Tax(ambiguous=["dup"]))


def test_feature_dangling_ref_wording(tmp_path):
    assert "Feature → dangling ref 'ghost'" in problems_for(
        tmp_path, Feature="ghost", taxonomy=Tax({"real": "Feature"}))


def test_feature_ambiguous_ref_wording(tmp_path):
    assert "Feature → ambiguous ref 'dup'" in problems_for(
        tmp_path, Feature="dup", taxonomy=Tax(ambiguous=["dup"]))


def test_feature_wrong_kind_wording_is_one_line_with_a_single_space(tmp_path):
    """Written across two source lines; it must concatenate to exactly this."""
    assert "Feature → ref 'user' points to Vocabulary, expected Feature" in problems_for(
        tmp_path, Feature="user", taxonomy=Tax({"user": "Vocabulary"}))


def test_the_location_prefix_is_the_capability_path(tmp_path):
    """The prefix `_ref_problems` must NOT include — the caller adds it."""
    root = node(tmp_path)
    write_cap(root, "routes/login", Status="Supported", Subject="ghost")
    out = FsCapabilitiesStore.open(root).check(taxonomy=Tax({"user": "Vocabulary"}))
    assert "routes/login: Subject → dangling ref 'ghost'" in out


def test_a_clean_capability_reports_nothing(tmp_path):
    """The control: every assertion above is about a string being present."""
    assert problems_for(
        tmp_path, Subject="user", Feature="real",
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

    def get(self, ref):
        self.calls.append(ref)
        return super().get(ref)


def test_check_without_a_taxonomy_resolves_against_the_nodes_own(tmp_path):
    """Today this silently skips Subject/Feature entirely, so the two write
    surfaces and `check` could disagree about *whether* a ref is checked."""
    root = node(tmp_path)
    (root / "docs" / "taxonomy").mkdir(parents=True)
    write_cap(root, "x", Status="Supported", Subject="ghost")
    problems = FsCapabilitiesStore.open(root).check()
    assert any("Subject → dangling ref 'ghost'" in p for p in problems)


def test_an_explicitly_passed_falsey_taxonomy_still_wins(tmp_path):
    root = node(tmp_path)
    (root / "docs" / "taxonomy").mkdir(parents=True)
    write_cap(root, "x", Status="Supported", Subject="user")
    stub = RecordingTax({"user": "Vocabulary"})
    problems = FsCapabilitiesStore.open(root).check(taxonomy=stub)
    assert stub.calls == ["user"], "the injected stub was not consulted"
    assert problems == []


def test_a_node_without_a_taxonomy_component_still_skips_subject(tmp_path):
    """No `docs/taxonomy/` means nothing to resolve against — the existing
    degradation, not a new one."""
    root = node(tmp_path)
    write_cap(root, "x", Status="Supported", Subject="ghost")
    assert FsCapabilitiesStore.open(root).check() == []


# ── the write path refuses what check would report ───────────────────────────

def _node_with_taxonomy(tmp_path):
    """A node whose taxonomy holds `thing` (Vocabulary) and `real-feature`."""
    root = node(tmp_path)
    tax = root / "docs" / "taxonomy"
    for slug, kind in (("thing", "Vocabulary"), ("real-feature", "Feature")):
        d = tax / slug
        d.mkdir(parents=True)
        (d / "meta.yaml").write_text(f"name: {slug}\nkind: {kind}\nrelatesTo: []\n")
        (d / "description.md").write_text("x")
    write_cap(root, "web/editing", Status="Supported")
    return root


@pytest.mark.parametrize("field,value,expected", [
    ("Subject", "no-such-term", "Subject → dangling ref 'no-such-term'"),
    ("Feature", "also-bogus", "Feature → dangling ref 'also-bogus'"),
    ("Feature", "thing", "Feature → ref 'thing' points to Vocabulary, expected Feature"),
    ("Superseded by", "nope", "Superseded by → dangling identifier 'nope'"),
    ("Blocked by", "nope2", "Blocked by → dangling identifier 'nope2'"),
    ("Roles", "roles/admin", "Roles → dangling identifier 'roles/admin'"),
    ("When", "conditions/offline", "When → dangling identifier 'conditions/offline'"),
])
def test_set_refuses_an_unresolvable_ref_and_writes_nothing(
        tmp_path, field, value, expected):
    root = _node_with_taxonomy(tmp_path)
    meta = root / "docs" / "capabilities" / "web" / "editing" / "meta.yaml"
    before = meta.read_bytes()
    store = FsCapabilitiesStore.open(root)
    with pytest.raises(ValueError) as e:
        store.set("web/editing", {field: value})
    assert expected in str(e.value)
    assert meta.read_bytes() == before, "a refused write must write nothing"


def test_set_reports_every_bad_ref_not_just_the_first(tmp_path):
    root = _node_with_taxonomy(tmp_path)
    store = FsCapabilitiesStore.open(root)
    with pytest.raises(ValueError) as e:
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
    with pytest.raises(ValueError) as e:
        store.set("web/editing", {"Subject": "no-such-term"})
    write_cap(root, "mirror", Status="Supported", Subject="no-such-term")
    from_check = [p.removeprefix("mirror: ")
                  for p in FsCapabilitiesStore.open(root).check()
                  if p.startswith("mirror: ")]
    assert str(e.value) in from_check


def test_a_taxonomy_less_node_still_accepts_subject_but_refuses_blocked_by(tmp_path):
    """Goal 1's stated qualification: with nothing to resolve against,
    Subject/Feature pass. The other four resolve against the store itself and
    are validated regardless."""
    root = node(tmp_path)
    write_cap(root, "x", Status="Supported")
    store = FsCapabilitiesStore.open(root)
    store.set("x", {"Subject": "anything"})
    with pytest.raises(ValueError, match="Blocked by"):
        store.set("x", {"Blocked by": "nope"})
