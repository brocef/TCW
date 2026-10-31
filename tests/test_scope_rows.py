"""TCW-113 Design 4.1-4.7, 4.10 (plan Step 8): the rows of a scope, from
plain data, with no file read. The objects are those of the family `F`
(`tests/families.py`), seen from `shared`."""

from __future__ import annotations

from tcw.ids import FullId
from tcw.store.base import ProjectView, ScopeObject, row_order, scope_rows, text_matches

DOWN = ["shared", "desktop", "server", "mobile"]
ALL = ["docs", "shared", "desktop", "server", "mobile"]


def cap(project: str, path: str) -> FullId:
    return FullId(project, "capabilities", path)


def term(project: str, path: str) -> FullId:
    return FullId(project, "taxonomy", path)


def entry(project, status, inherited, full_id):
    return {"project": project, "status": status, "inherited": inherited,
            "full-id": str(full_id)}


def test_ac12_ac13_one_row_for_an_object_and_its_overrides():
    shared, desktop, server = cap("shared", "abc"), cap("desktop", "abc"), cap("server", "abc")
    [row] = scope_rows("abc", order=DOWN, v=ScopeObject(shared),
                       own=[ScopeObject(desktop, shared), ScopeObject(server, shared)],
                       chain=[], views=[ProjectView("shared", shared, "Missing", True),
                                        ProjectView("desktop", desktop, "Supported", True),
                                        ProjectView("server", server, "Omitted", True)])
    assert row.shown == shared
    assert row.group == {shared, desktop, server}
    assert row.statuses == [entry("shared", "Missing", False, shared),
                            entry("desktop", "Supported", False, desktop),
                            entry("server", "Omitted", False, server)]
    assert row.overridden_by[shared] == [desktop, server]
    assert row.overridden_by[desktop] == [] and row.overridden_by[server] == []


def test_ac12_a_project_that_inherits_counts_with_the_status_it_inherits():
    shared = cap("shared", "ghi")
    [row] = scope_rows("ghi", order=DOWN, v=ScopeObject(shared), own=[], chain=[],
                       views=[ProjectView("shared", shared, "Missing", True),
                              ProjectView("desktop", shared, "Missing", False),
                              ProjectView("server", shared, "Missing", False)])
    assert row.statuses == [entry("shared", "Missing", False, shared),
                            entry("desktop", "Missing", True, shared),
                            entry("server", "Missing", True, shared)]


def test_ac12_a_descendants_new_object_is_its_own_row():
    desktop = cap("desktop", "def")
    [row] = scope_rows("def", order=DOWN, v=None, own=[ScopeObject(desktop)], chain=[],
                       views=[ProjectView("shared", None),
                              ProjectView("desktop", desktop, "Supported", True),
                              ProjectView("server", None)])
    assert row.shown == desktop
    assert row.statuses == [entry("desktop", "Supported", False, desktop)]


def test_ac15_an_override_that_sets_no_status_is_marked_inherited():
    shared, server = cap("shared", "abc"), cap("server", "abc")
    [row] = scope_rows("abc", order=DOWN, v=ScopeObject(shared),
                       own=[ScopeObject(server, shared)], chain=[],
                       views=[ProjectView("shared", shared, "Missing", True),
                              ProjectView("server", server, "Missing", False)])
    # The entry is marked inherited, and still names server's own object,
    # which its view comes from (review round 5, finding 1).
    assert row.statuses[-1] == entry("server", "Missing", True, server)


def test_ac18_two_new_objects_at_one_id_path_are_two_rows_in_scope_order():
    server, desktop = cap("server", "zz"), cap("desktop", "zz")
    rows = scope_rows("zz", order=DOWN, v=None,
                      own=[ScopeObject(server), ScopeObject(desktop)], chain=[],
                      views=[ProjectView("desktop", desktop, "Supported", True),
                             ProjectView("server", server, "Omitted", True)])
    assert [r.shown for r in rows] == [desktop, server]
    assert [r.statuses for r in rows] == [[entry("desktop", "Supported", False, desktop)],
                                          [entry("server", "Omitted", False, server)]]


def test_ac19_under_down_each_override_of_an_inherited_object_is_its_own_row():
    docs = cap("docs", "xyz")
    desktop, server = cap("desktop", "xyz"), cap("server", "xyz")
    rows = scope_rows("xyz", order=DOWN, v=None,
                      own=[ScopeObject(desktop, docs), ScopeObject(server, docs)],
                      chain=[], views=None)
    assert [r.shown for r in rows] == [desktop, server]


def test_ac19_under_all_the_view_object_holds_its_chain_and_the_overrides():
    docs = cap("docs", "xyz")
    desktop, server = cap("desktop", "xyz"), cap("server", "xyz")
    [row] = scope_rows("xyz", order=ALL, v=ScopeObject(docs), chain=[docs],
                       own=[ScopeObject(desktop, docs), ScopeObject(server, docs)],
                       views=[ProjectView("docs", docs, "Supported", True),
                              ProjectView("shared", docs, "Supported", False),
                              ProjectView("desktop", desktop, "Missing", True),
                              ProjectView("server", server, "Omitted", True)])
    assert row.shown == docs
    assert [e["project"] for e in row.statuses] == ["docs", "shared", "desktop", "server"]
    assert row.statuses[1] == entry("shared", "Supported", True, docs)
    assert row.overridden_by[docs] == [desktop, server]


def test_under_all_an_override_of_a_chain_member_joins_the_view_objects_row():
    # `shared` overrides `docs`'s object; `desktop` overrides `docs`'s too,
    # not `shared`'s: the chain puts both in one row, shown as V(X).
    docs, shared, desktop = cap("docs", "q"), cap("shared", "q"), cap("desktop", "q")
    [row] = scope_rows("q", order=ALL, v=ScopeObject(shared, docs), chain=[shared, docs],
                       own=[ScopeObject(desktop, docs)], views=None)
    assert row.shown == shared and row.group == {docs, shared, desktop}
    assert row.overridden_by[docs] == [shared, desktop]


def test_a_group_held_by_overrides_alone_shows_the_object_overriding_nothing_in_it():
    desktop, server = cap("desktop", "n"), cap("server", "n")
    [row] = scope_rows("n", order=DOWN, v=None,
                       own=[ScopeObject(server, desktop), ScopeObject(desktop)],
                       chain=[], views=None)
    assert row.shown == desktop
    assert row.overridden_by[desktop] == [server]


def test_an_override_of_an_object_outside_the_scope_overrides_nothing_in_its_group():
    desktop, server = cap("desktop", "n"), cap("server", "n")
    [row] = scope_rows("n", order=DOWN, v=None,
                       own=[ScopeObject(server, desktop),
                            ScopeObject(desktop, cap("docs", "n"))],
                       chain=[], views=None)
    assert row.shown == desktop


def test_taxonomy_has_no_statuses_and_the_same_overridden_by():
    shared, desktop = term("shared", "t"), term("desktop", "t")
    [row] = scope_rows("t", order=DOWN, v=ScopeObject(shared),
                       own=[ScopeObject(desktop, shared)], chain=[], views=None)
    assert row.statuses is None
    assert row.overridden_by[shared] == [desktop]


def test_row_order_is_by_id_path_folder_by_folder_then_owner():
    rows = [cap("server", "event"), cap("shared", "event/log"), cap("desktop", "event"),
            cap("shared", "event-reporting")]
    ordered = row_order(rows, DOWN, shown=lambda f: f)
    assert ordered == [cap("desktop", "event"), cap("server", "event"),
                       cap("shared", "event/log"), cap("shared", "event-reporting")]


def test_text_matches_ignores_case_in_name_or_body():
    assert text_matches("Refund", "", "refu")
    assert text_matches("x", "Pays BACK", "back")
    assert not text_matches("x", "y", "z")


def test_under_all_the_chain_joins_what_no_overrides_link_reaches():
    # The view's chain holds `docs`'s object through `mid`'s, which is no
    # scope object, so only the chain puts `desktop`'s override of `docs`'s
    # object in V(X)'s row.
    docs, mid, shared = cap("docs", "w"), cap("mid", "w"), cap("shared", "w")
    desktop = cap("desktop", "w")
    [row] = scope_rows("w", order=["docs", "mid", *DOWN], v=ScopeObject(shared, mid),
                       chain=[shared, mid, docs], own=[ScopeObject(desktop, docs)],
                       views=None)
    assert row.shown == shared and row.group == {docs, mid, shared, desktop}
