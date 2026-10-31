"""The load order (TCW-108 Design 4), computed from parent links alone.

The design's examples are criteria AC 10-14, and a property test compares
the implementation on generated graphs against Python's own C3 (the method
resolution order of classes whose bases are each project's parents,
reversed) and against a transcription of the fallback rules of Design 4.4
and 4.5 written here."""

from __future__ import annotations

import random

import pytest

from tcw.store.base import AXES, ParentLink, find_loop, load_order_of, loop_message, passing


def graph(**parents):
    """`aa=["bb"]` and the like: each project's parents, in listing order,
    every link passing everything; a value may be a `ParentLink`."""
    return {pid: [p if isinstance(p, ParentLink) else ParentLink(p) for p in ps]
            for pid, ps in parents.items()}


def order(project_id, links, missing=(), unreadable=()):
    return load_order_of(project_id, links, missing=set(missing),
                         unreadable=set(unreadable))


def ids(text: str) -> tuple:
    return tuple(part.strip() for part in text.split(","))


# AC 10-12: the design's C3 examples.

def test_ac10_several_levels():
    links = graph(cc=["aa", "bb"], ff=["dd", "ee"], gg=["cc", "ff"])
    found = order("gg", links)
    assert found.ids == ids("aa, bb, cc, dd, ee, ff, gg")
    assert found.warning is None


def test_ac11_reached_twice_placed_once():
    links = graph(bb=["aa"], cc=["bb"], dd=["bb"], ee=["cc", "dd"])
    found = order("ee", links)
    assert found.ids == ids("aa, bb, cc, dd, ee")
    assert found.warning is None


def test_ac12_c3_not_depth_first():
    links = graph(xx=["bb"], yy=["aa", "bb"], zz=["xx", "yy"])
    found = order("zz", links)
    assert found.ids == ids("aa, bb, xx, yy, zz")
    assert found.warning is None


# AC 13-14: the fallback and its warning.

def test_ac13_parents_that_disagree():
    links = graph(xx=["aa", "bb"], yy=["bb", "aa"], zz=["xx", "yy"])
    found = order("zz", links)
    assert found.ids == ids("aa, bb, xx, yy, zz")
    assert found.warning == (
        "load order: no order keeps every project's own order of parents (at 'zz': "
        "'aa', 'bb' cannot be placed); using depth-first order aa, bb, xx, yy, zz; "
        "the order of each project's parents: list sets the load order, and listing "
        "the parents of 'yy' as aa, bb instead gives an order that keeps every other "
        "project's own order; to choose a configuration value yourself, set the value "
        "in 'zz' itself, which loads last and wins")


def test_the_warning_names_the_order_of_the_failing_project_itself():
    # A parent listed before an upstream that parent itself inherits.
    links = graph(aa=["core"], bb=["aa", "core"])
    found = order("bb", links)
    assert ("the order of each project's parents: list sets the load order, and listing "
            "the parents of 'bb' as core, aa instead gives an order") in found.warning


def test_with_no_one_list_to_reorder_the_warning_says_to_reorder_those_that_disagree():
    links = graph(xx=["aa", "bb"], yy=["bb", "aa"], uu=["cc", "dd"], vv=["dd", "cc"],
                  zz=["xx", "yy", "uu", "vv"])
    found = order("zz", links)
    assert ("using depth-first order aa, bb, xx, yy, cc, dd, uu, vv, zz; the order of "
            "each project's parents: list sets the load order: reorder the lists that "
            "disagree; to choose a configuration value yourself, set the value in 'zz' "
            "itself, which loads last and wins") in found.warning


def test_ac14_a_child_listed_before_its_own_parent():
    links = graph(dd=["cc"], ee=["dd", "cc"])
    found = order("ee", links)
    assert found.ids == ids("cc, dd, ee")
    assert "(at 'ee': 'cc', 'dd' cannot be placed)" in found.warning
    assert found.warning.count("'cc'") == 1


@pytest.mark.parametrize("pp, at", [(["ee", "ii"], "(at 'ee': 'cc', 'dd' cannot be placed)"),
                                    (["ii", "ee"], "(at 'ii': 'gg', 'hh' cannot be placed)")])
def test_ac14_the_first_merge_to_fail_is_named(pp, at):
    links = graph(dd=["cc"], ee=["dd", "cc"], hh=["gg"], ii=["hh", "gg"], pp=pp)
    assert at in order("pp", links).warning


def test_a_project_with_no_parents_is_alone():
    found = order("app", {})
    assert found.ids == ("app",) and found.complete and found.warning is None


# Design 6.4: missing and unreadable projects.

def test_a_missing_grandparent_is_placed_with_no_parents():
    links = graph(app=["lib"], lib=["core"])
    found = order("app", links, missing={"core"})
    assert found.ids == ids("core, lib, app")
    assert found.missing == ("core",) and not found.complete


def test_an_unreadable_project_has_no_parents():
    # Whatever links were recorded for it are not used: its file is wrong.
    links = graph(app=["lib"], lib=["core"])
    found = order("app", links, unreadable={"lib"})
    assert found.ids == ids("lib, app")
    assert found.unreadable == ("lib",)


# AC 17: which projects pass an axis.

def test_ac17_passing():
    links = graph(gg=[ParentLink("ww", frozenset()), ParentLink("ll", frozenset({"taxonomy"}))],
                  ll=["kk"], ww=["vv"])
    assert order("gg", links).ids == ids("vv, ww, kk, ll, gg")
    assert passing("taxonomy", "gg", links) == {"kk", "ll", "gg"}
    assert passing("config", "gg", links) == {"gg"}
    assert passing("capabilities", "gg", links) == {"gg"}
    links["ll"] = [ParentLink("kk", frozenset({"config"}))]
    assert passing("taxonomy", "gg", links) == {"ll", "gg"}
    assert passing("config", "gg", links) == {"gg"}


# Design 4.7: loops.

def test_a_two_project_loop():
    links = graph(aa=["bb"], bb=["aa"])
    assert loop_message(find_loop(links, ["aa", "bb"])) == "loop in parents: aa -> bb -> aa"
    assert loop_message(find_loop(links, ["bb", "aa"])) == "loop in parents: bb -> aa -> bb"


def test_a_project_its_own_parent():
    assert loop_message(find_loop(graph(aa=["aa"]), ["aa"])) == "loop in parents: aa -> aa"


def test_ac15_a_loop_among_descendants():
    links = graph(cc=["ws", "ee"], dd=["cc"], ee=["dd"])
    loop = find_loop(links, ["ws", "cc", "dd", "ee"])
    assert loop_message(loop) == "loop in parents: cc -> ee -> dd -> cc"


def test_no_loop():
    assert find_loop(graph(bb=["aa"], cc=["aa", "bb"]), ["cc", "bb", "aa"]) is None


def test_a_loop_is_refused_rather_than_followed():
    with pytest.raises(ValueError):
        order("aa", graph(aa=["bb"], bb=["aa"]))


# The property test (spec Risks, "C3 is subtle").

GRAPHS = 2000
NAMES = [f"p{i}" for i in range(8)]


def _generate(rng: random.Random):
    """A parent graph with no loop over at most eight projects: each project
    takes parents only among those generated before it, so no loop can
    form; some projects are missing or unreadable."""
    count = rng.randint(2, len(NAMES))
    names = NAMES[:count]
    links: dict[str, list[ParentLink]] = {}
    for index, name in enumerate(names):
        earlier = names[:index]
        chosen = rng.sample(earlier, rng.randint(0, min(3, len(earlier))))
        links[name] = [ParentLink(p) for p in chosen]
    missing, unreadable = set(), set()
    for name in names[:-1]:
        roll = rng.random()
        if roll < 0.06:
            missing.add(name)
        elif roll < 0.12:
            unreadable.add(name)
    for name in names:
        listed = [link.id for link in links[name]]
        assert len(listed) == len(set(listed))       # Python refuses a repeated base
    return names, links, missing, unreadable


def _effective(links, missing, unreadable):
    return {pid: ([] if pid in missing or pid in unreadable else ps)
            for pid, ps in links.items()}


def _python_c3(project_id, links):
    """The MRO Python gives the project, farthest first, or None when it
    cannot make one; built afresh from the project's own ancestors only."""
    built: dict[str, type] = {}

    def make(pid):
        if pid not in built:
            bases = tuple(make(link.id) for link in reversed(links.get(pid, [])))
            built[pid] = type(pid, bases or (object,), {})
        return built[pid]

    try:
        cls = make(project_id)
    except TypeError:
        return None
    return tuple(reversed([c.__name__ for c in cls.__mro__ if c is not object]))


def _depth_first(project_id, links):
    placed: list[str] = []

    def place(pid):
        for link in links.get(pid, []):
            if link.id not in placed:
                place(link.id)
        if pid not in placed:
            placed.append(pid)

    place(project_id)
    return tuple(placed)


def _first_failure(project_id, links):
    """Design 4.5's `<Q>` and its heads, by a transcription of Design 4.1 and
    4.5: each project's merge after all its parents', parents in listing
    order."""
    done: dict[str, list[str]] = {}

    def resolve(pid):
        if pid in done:
            return None
        for link in links.get(pid, []):
            failed = resolve(link.id)
            if failed is not None:
                return failed
        parents = [link.id for link in links.get(pid, [])]
        lists = [list(done[p]) for p in reversed(parents)] + [list(reversed(parents))]
        result = [pid]
        while any(lists):
            for candidate in (lst[0] for lst in lists if lst):
                if not any(candidate in lst[1:] for lst in lists):
                    break
            else:
                heads: list[str] = []
                for lst in lists:
                    if lst and lst[0] not in heads:
                        heads.append(lst[0])
                return pid, heads
            result.append(candidate)
            lists = [[x for x in lst if x != candidate] for lst in lists]
        done[pid] = result
        return None

    return resolve(project_id)


def _single_reorders(project_id, links):
    """Each `(project, its parents in a new order)` that, alone, lets Python
    make an MRO for `project_id`."""
    from itertools import permutations
    found = set()
    for pid, parents in links.items():
        for perm in permutations(parents):
            if list(perm) == list(parents):
                continue
            trial = dict(links, **{pid: list(perm)})
            if _python_c3(project_id, trial) is not None:
                found.add((pid, tuple(link.id for link in perm)))
    return found


def test_property_against_python_c3_and_the_fallback_rules():
    rng = random.Random(108)
    fell_back = with_absent = checked = suggested = 0
    for _ in range(GRAPHS):
        names, links, missing, unreadable = _generate(rng)
        effective = _effective(links, missing, unreadable)
        with_absent += bool(missing or unreadable)
        for pid in names:
            if pid in missing:
                continue
            found = load_order_of(pid, links, missing=missing, unreadable=unreadable)
            checked += 1
            expected = _python_c3(pid, effective)
            # Rules that hold for any graph.
            assert len(set(found.ids)) == len(found.ids)
            assert found.ids[-1] == pid
            position = {p: i for i, p in enumerate(found.ids)}
            for member in found.ids:
                for link in effective.get(member, []):
                    assert position[link.id] < position[member], (pid, links)
            assert set(found.missing) == missing & set(found.ids)
            assert set(found.unreadable) == unreadable & set(found.ids)
            if expected is not None:
                assert found.ids == expected, (pid, links, missing, unreadable)
                assert found.warning is None
                for member in found.ids:
                    listed = [position[link.id] for link in effective.get(member, [])]
                    assert listed == sorted(listed)
            else:
                fell_back += 1
                assert found.ids == _depth_first(pid, effective)
                where, heads = _first_failure(pid, effective)
                named = ", ".join(f"'{h}'" for h in heads)
                head = (f"load order: no order keeps every project's own order of "
                        f"parents (at '{where}': {named} cannot be placed); using "
                        f"depth-first order {', '.join(found.ids)}; the order of each "
                        f"project's parents: list sets the load order")
                tail = (f"; to choose a configuration value yourself, set the value in "
                        f"'{pid}' itself, which loads last and wins")
                assert found.warning.startswith(head) and found.warning.endswith(tail), \
                    (pid, links)
                middle = found.warning[len(head):-len(tail)]
                fixes = _single_reorders(pid, effective)
                if middle == ": reorder the lists that disagree":
                    assert not fixes, (pid, links, fixes)
                else:
                    assert middle.startswith(", and listing the parents of '"), middle
                    assert middle.endswith(" instead gives an order that keeps every "
                                           "other project's own order"), middle
                    named_pid, listed = middle[len(", and listing the parents of '"):
                                               ].split(" instead")[0].split("' as ")
                    assert (named_pid, tuple(listed.split(", "))) in fixes, \
                        (pid, links, middle)
                    suggested += 1
    # The suggestion is checked, so a run that never makes one would pass quietly.
    assert suggested >= fell_back * 0.10, (suggested, fell_back)
    # A generator that stopped producing hard cases would pass quietly.
    assert fell_back >= checked * 0.10, (fell_back, checked)
    assert with_absent >= GRAPHS * 0.10, with_absent


def test_axes_are_the_three():
    assert AXES == ("taxonomy", "capabilities", "config")
