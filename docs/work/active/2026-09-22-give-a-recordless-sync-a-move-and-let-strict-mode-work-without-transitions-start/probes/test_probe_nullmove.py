from __future__ import annotations

from test_tracker_sync import (STATUSES, KEY, TICKET_ID, A, B, cli, fake,  # noqa: F401
                               make_node, bound_item, record, binding_text, status)


def test_recordless_sync_during_an_outage_writes_an_unreadable_record(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    print("after start:", fake.tickets[TICKET_ID].status, fake.tickets[TICKET_ID].assignee,
          "record:", record(root, slug))
    fake.down = True
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    print("sync exit", code, "OUT:", out, "ERR:", err)
    print("binding file:\n", binding_text(root, slug))
    print("record now:", record(root, slug))
    fake.down = False
    code, out, err = cli(root, "work", "show", slug)
    print("show:", out, err)
    # And the strict-mode gate
    code, out, err = cli(root, "work", "submit", slug)
    print("submit exit", code, "OUT:", out, "ERR:", err)
    print("record after submit:", record(root, slug))
