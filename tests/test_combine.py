"""Combining an object over its sources (TCW-112 Design 2.1-2.6), with no
store around it: the chain, the fields laid key by key, the description, the
projects whose object is not used and whether each is warned about.

Declarations are plain data: a load order, each declaring project's
declaration at one id-path, and the "passes the axis to" relation from
TCW-108's `passing` over the same links."""

from __future__ import annotations

import random

import pytest

from tcw.store.base import (Declaration, ParentLink, clash_warning, combine,
                            load_order_of, passing)


def graph(**parents):
    """`aa=["bb"]`: each project's parents, in listing order; a value may be
    a `ParentLink`."""
    return {pid: [p if isinstance(p, ParentLink) else ParentLink(p) for p in ps]
            for pid, ps in parents.items()}


def relation(links, axis="capabilities"):
    """`passes(a, b)`: whether `a` passes `axis` to `b`, `a` not `b`."""
    def passes(a: str, b: str) -> bool:
        return a != b and a in passing(axis, b, links)
    return passes


def cap(description=None, **fields):
    return Declaration(fields=fields, description=description)


def combined(project, links, declared, axis="capabilities", unreadable=()):
    order = load_order_of(project, links).ids
    declarers = [(pid, declared[pid]) for pid in order if pid in declared]
    return combine(declarers, relation(links, axis), axis=axis,
                   unreadable=frozenset(unreadable))


# -- the chain (Design 2.1) ---------------------------------------------------

def test_an_override_over_its_original():
    links = graph(app=["core"])
    found = combined("app", links, {"core": cap("Core", name="X", Status="Missing"),
                                    "app": cap(Status="Supported")})
    assert found.chain == ("app", "core")
    assert found.overrides == "core"
    assert found.owner == "app"
    assert found.unused == ()


def test_ac9_only_a_declaring_project_replaces():
    links = graph(cc=["bb"], dd=["bb"], ee=["cc", "dd"])
    found = combined("ee", links, {"bb": cap(Status="Missing"),
                                   "cc": cap(Status="Supported")})
    assert found.chain == ("cc", "bb")
    assert found.overrides == "bb"
    assert found.fields == {"Status": "Supported"}
    assert found.unused == ()


def test_ac10_two_unrelated_projects():
    links = graph(ee=["cc", "dd"])
    found = combined("ee", links, {"cc": cap(name="C", Status="Supported", Priority="P1"),
                                   "dd": cap(name="D", Status="Missing")})
    assert found.chain == ("dd",)
    assert found.overrides is None
    assert found.fields == {"name": "D", "Status": "Missing"}
    assert [(u.project, u.winner, u.warned) for u in found.unused] == [("cc", "dd", True)]


def test_ac10_reversed_parents():
    links = graph(ee=["dd", "cc"])
    found = combined("ee", links, {"cc": cap(name="C"), "dd": cap(name="D")})
    assert found.chain == ("cc",)
    assert [(u.project, u.winner) for u in found.unused] == [("dd", "cc")]


def test_ac11_siblings_both_overriding_a_common_parent():
    links = graph(cc=["bb"], dd=["bb"], ee=["cc", "dd"])
    found = combined("ee", links, {"bb": cap(name="X", Status="Missing"),
                                   "cc": cap(Status="Supported"),
                                   "dd": cap(Priority="P2")})
    assert found.chain == ("dd", "bb")
    assert found.fields == {"name": "X", "Status": "Missing", "Priority": "P2"}
    assert [(u.project, u.winner, u.warned) for u in found.unused] == [("cc", "dd", True)]


def test_the_active_project_declaring_comes_first_and_is_never_unused():
    links = graph(ee=["cc", "dd"])
    found = combined("ee", links, {"cc": cap(name="C"), "dd": cap(name="D"),
                                   "ee": cap(Status="Supported")})
    assert found.chain == ("ee", "dd")
    assert [u.project for u in found.unused] == ["cc"]


def test_three_levels():
    links = graph(lib=["core"], app=["lib"])
    found = combined("app", links, {"core": cap(name="X"), "lib": cap(Priority="P1"),
                                    "app": cap(Status="Supported")})
    assert found.chain == ("app", "lib", "core")
    assert found.fields == {"name": "X", "Priority": "P1", "Status": "Supported"}


def test_a_link_that_does_not_pass_the_axis_breaks_the_chain():
    links = graph(lib=[ParentLink("core", frozenset({"taxonomy"}))], app=["lib"])
    found = combined("app", links, {"lib": cap(name="L")})
    assert found.chain == ("lib",)
    order = load_order_of("app", links).ids
    passes = relation(links)
    declarers = [(pid, {"core": cap(name="C"), "lib": cap(name="L")}[pid])
                 for pid in order if pid in ("core", "lib")]
    found = combine(declarers, passes, axis="capabilities")
    # `core` passes nothing to `lib`: the two are unrelated for this axis.
    assert found.chain == ("lib",)
    assert [u.project for u in found.unused] == ["core"]


def test_nothing_declared_is_none():
    assert combine([], relation({}), axis="capabilities") is None


# -- combining the fields (Design 2.2) -----------------------------------------

def test_a_value_replaces_and_an_absent_key_leaves():
    links = graph(app=["core"])
    found = combined("app", links, {"core": cap(Status="Missing", Priority="P1"),
                                    "app": cap(Status="Supported")})
    assert found.fields == {"Status": "Supported", "Priority": "P1"}


def test_null_removes_the_value_below():
    links = graph(app=["core"])
    found = combined("app", links, {"core": cap(Status="Missing", Priority="P1"),
                                    "app": cap(Priority=None)})
    assert found.fields == {"Status": "Missing"}
    assert "Priority" not in found.declared_by


@pytest.mark.parametrize("key", ["Subject", "relatesTo", "vocabulary", "prependedDocs",
                                 "appendedDocs"])
def test_a_list_is_replaced_whole(key):
    links = graph(app=["core"])
    found = combined("app", links, {
        "core": cap(**{key: ["core.taxonomy/invoice", "core.taxonomy/payment"]}),
        "app": cap(**{key: ["app.taxonomy/money"]})})
    assert found.fields[key] == ["app.taxonomy/money"]
    assert found.declared_by[key] == "app"


@pytest.mark.parametrize("key", ["parent", "name", "kind"])
def test_structural_keys_combine_the_same_way(key):
    links = graph(app=["core"])
    found = combined("app", links, {"core": cap(**{key: "core-value"}),
                                    "app": cap(**{key: "app-value"})})
    assert found.fields[key] == "app-value"
    found = combined("app", links, {"core": cap(**{key: "core-value"}), "app": cap()})
    assert found.fields[key] == "core-value"


def test_the_file_keys_never_combine():
    links = graph(app=["core"])
    found = combined("app", links, {"core": cap(**{"id": "x", "tcw-version": "4.0.0"}),
                                    "app": cap(Status="Supported")})
    assert found.fields == {"Status": "Supported"}


def test_declared_by_names_the_member_that_supplied_each_list():
    links = graph(app=["core"])
    found = combined("app", links, {"core": cap(prependedDocs=["resources/a.md"]),
                                    "app": cap(appendedDocs=["resources/b.md"])})
    assert found.declared_by["prependedDocs"] == "core"
    assert found.declared_by["appendedDocs"] == "app"


# -- the description (Design 2.3) ----------------------------------------------

def test_the_nearest_description_with_text():
    links = graph(app=["core"])
    found = combined("app", links, {"core": cap("Core body"), "app": cap("App body")})
    assert (found.description, found.declared_by["description"]) == ("App body", "app")


@pytest.mark.parametrize("own", [None, "", "  \n"])
def test_an_empty_or_undeclared_description_falls_through(own):
    links = graph(app=["core"])
    found = combined("app", links, {"core": cap("Core body"), "app": cap(own)})
    assert (found.description, found.declared_by["description"]) == ("Core body", "core")


def test_no_description_anywhere_is_none():
    links = graph(app=["core"])
    found = combined("app", links, {"core": cap(""), "app": cap(None)})
    assert found.description is None
    assert "description" not in found.declared_by


# -- the warning (Design 2.5) --------------------------------------------------

def test_the_warning_for_a_capability():
    assert clash_warning("capabilities", "X", "cc", "dd", "ee") == (
        "capabilities X: 'cc' and 'dd' each have an object at this path, and neither "
        "inherits it from the other; 'ee' uses the one from 'dd', which comes later in "
        "its load order, and nothing from 'cc''s; to choose for yourself, give 'ee' a "
        "complete object of its own at X (a name, a Status and a description), "
        "holding every field you want")


def test_the_warning_for_a_term():
    assert clash_warning("taxonomy", "t", "cc", "dd", "ee").endswith(
        "give 'ee' a complete object of its own at t (a name and a description), "
        "holding every field you want")


@pytest.mark.parametrize("description", ["E body", ""])
def test_ac43_a_complete_object_in_a_project_inheriting_from_both_silences_it(description):
    links = graph(ee=["cc", "dd"])
    found = combined("ee", links, {
        "cc": cap(name="C", Status="Supported"), "dd": cap(name="D", Status="Missing"),
        "ee": cap(description, name="E", Status="Supported")})
    assert found.chain == ("ee", "dd")
    assert [(u.project, u.warned) for u in found.unused] == [("cc", False)]


@pytest.mark.parametrize("own", [cap(Status="Supported"),
                                 cap(name="E", Status="Supported"),
                                 cap("E body", Status="Supported"),
                                 cap("E body", name="E")])
def test_ac43_an_incomplete_object_does_not_silence_it(own):
    links = graph(ee=["cc", "dd"])
    found = combined("ee", links, {"cc": cap(name="C"), "dd": cap(name="D"), "ee": own})
    assert [(u.project, u.warned) for u in found.unused] == [("cc", True)]


def test_a_term_is_complete_without_a_status():
    links = graph(ee=["cc", "dd"])
    found = combined("ee", links, {"cc": cap(name="C"), "dd": cap(name="D"),
                                   "ee": cap("", name="E")}, axis="taxonomy")
    assert [(u.project, u.warned) for u in found.unused] == [("cc", False)]


def test_ac43_a_complete_object_the_unused_project_does_not_pass_to_does_not_silence():
    links = graph(cc=["bb"], dd=["bb"], ee=["cc", "dd"])
    found = combined("ee", links, {"bb": cap(name="X"), "cc": cap(Status="Supported"),
                                   "dd": cap("D body", name="D", Status="Missing")})
    assert [(u.project, u.winner, u.warned) for u in found.unused] == [("cc", "dd", True)]


def test_unused_projects_are_in_load_order():
    links = graph(ee=["aa", "bb", "cc"])
    found = combined("ee", links, {"aa": cap(), "bb": cap(), "cc": cap()})
    assert [(u.project, u.winner) for u in found.unused] == [("aa", "cc"), ("bb", "cc")]


# -- an unreadable member (Design 1.3) ------------------------------------------

def test_an_unreadable_chain_member_makes_the_path_unreadable():
    links = graph(app=["core"])
    found = combined("app", links, {"core": cap(), "app": cap(Status="Supported")},
                     unreadable={"core"})
    assert found.unreadable == "core"
    assert found.chain == ("app", "core")


def test_an_unreadable_unused_declarer_changes_only_the_warning():
    links = graph(ee=["cc", "dd"])
    found = combined("ee", links, {"cc": cap(), "dd": cap(name="D")}, unreadable={"cc"})
    assert found.unreadable is None
    assert found.fields == {"name": "D"}
    assert [u.project for u in found.unused] == ["cc"]


# -- a property test, as TCW-108's ------------------------------------------------

def _family(rng: random.Random):
    """At most seven projects, each with random parents among those before it
    and random `inherit`, declaring at one id-path at random. The last is the
    active project."""
    size = rng.randint(2, 7)
    names = [f"p{n}" for n in range(size)]
    links = {}
    for i, pid in enumerate(names):
        chosen = rng.sample(names[:i], rng.randint(0, min(3, i)))
        links[pid] = [ParentLink(p, frozenset({"capabilities"}) if rng.random() < 0.8
                                 else frozenset({"taxonomy"})) for p in chosen]
    declared = {}
    for pid in names:
        if rng.random() < 0.6:
            declared[pid] = cap(**{f"k{rng.randint(0, 3)}": pid, "who": pid})
    return names[-1], links, declared


def test_the_chain_rules_hold_for_generated_families():
    rng = random.Random(112)
    with_unused = checked = 0
    for _ in range(2000):
        active, links, declared = _family(rng)
        try:
            order = load_order_of(active, links).ids
        except ValueError:
            continue
        sources = passing("capabilities", active, links)
        declared = {pid: d for pid, d in declared.items() if pid in sources}
        if not declared:
            continue
        passes = relation(links)
        declarers = [(pid, declared[pid]) for pid in order if pid in declared]
        found = combine(declarers, passes, axis="capabilities")
        checked += 1
        position = {pid: i for i, pid in enumerate(order)}
        chain = list(found.chain)
        # The chain's members are declarers, in reverse load order.
        assert all(pid in declared for pid in chain)
        assert [position[p] for p in chain] == sorted((position[p] for p in chain),
                                                      reverse=True)
        # The first member is the last declarer; each member passes the axis to
        # the one before it; and none is skipped: no declarer between two
        # members passes the axis to the nearer one.
        assert chain[0] == declarers[-1][0]
        for near, far in zip(chain, chain[1:]):
            assert passes(far, near)
            between = [pid for pid, _ in declarers
                       if position[far] < position[pid] < position[near]]
            assert not any(passes(pid, near) for pid in between)
        # The last member has no declarer before it that passes it the axis.
        assert not any(passes(pid, chain[-1]) for pid, _ in declarers
                       if position[pid] < position[chain[-1]])
        # Every declarer is in the chain or unused, never both.
        unused = [u.project for u in found.unused]
        assert sorted(chain + unused) == sorted(declared)
        assert not set(chain) & set(unused)
        # The active project, when it declares, is first and never unused.
        if active in declared:
            assert chain[0] == active and active not in unused
        # The fields are the chain's own fields folded in load order.
        folded = {}
        for pid in reversed(chain):
            folded.update(declared[pid].fields)
        assert found.fields == folded
        with_unused += bool(unused)
    assert checked > 1000
    assert with_unused >= checked // 10, (with_unused, checked)
