from __future__ import annotations

from test_tracker_sync import (STATUSES, KEY, TICKET_ID, A, B, cli, fake,  # noqa: F401
                               make_node, bound_item, record, status)
from test_tracker_strict import set_tracker_key


def test_a_sync_during_an_outage_blocks_the_next_strict_move(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    assert cli(root, "work", "submit", slug)[0] == 0
    set_tracker_key(root, "strict", True)
    t = fake.tickets[TICKET_ID]
    print("healthy state:", t.status, t.assignee, "| item:", status(root, slug),
          "| record:", record(root, slug))
    fake.down = True
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    print("\n$ sync (tracker down) ->", code, "|", out.strip())
    print("  record:", record(root, slug))
    fake.down = False
    code, out, err = cli(root, "work", "complete", slug, "--resolution", "done",
                         "--confirm")
    print("\n$ complete (tracker back) ->", code)
    print("  ERR:", err.strip())
    print("  item:", status(root, slug))
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    print("\n$ sync again ->", code, "|", out.strip(), "| record:", record(root, slug))
    code, out, err = cli(root, "work", "complete", slug, "--resolution", "done",
                         "--confirm")
    print("\n$ complete ->", code, "| item:", status(root, slug),
          "| ticket:", fake.tickets[TICKET_ID].status)
