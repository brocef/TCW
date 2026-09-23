from __future__ import annotations

from test_tracker_sync import (STATUSES, KEY, TICKET_ID, A, B, cli, fake,  # noqa: F401
                               make_node, bound_item, record, status, binding_text)
from test_tracker_strict import set_tracker_key


def test_a_failed_diagnostic_sync_wedges_a_strict_item(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    set_tracker_key(root, "strict", True)
    t = fake.tickets[TICKET_ID]
    print("state:", t.status, t.assignee, "record:", record(root, slug))
    # Somebody in the tracker sends the ticket back to the backlog and drops it.
    t.status, t.assignee = "To Do", None
    for argv in (("work", "submit", slug),
                 ("work", "tracker", "sync", slug),
                 ("work", "submit", slug),
                 ("work", "complete", slug, "--resolution", "done", "--confirm")):
        code, out, err = cli(root, *argv)
        print("\n$ tcw", " ".join(argv), "->", code)
        print("  OUT:", out.strip())
        print("  ERR:", err.strip())
        print("  record:", record(root, slug), "| item:", status(root, slug))
