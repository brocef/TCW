from __future__ import annotations

from test_tracker_sync import (STATUSES, KEY, TICKET_ID, A, B, cli, fake,  # noqa: F401
                               make_node, bound_item, record, status)
from test_tracker_strict import set_tracker_key


def test_reopened_ticket_on_a_completed_item_under_an_exclusive_workflow(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
    slug = bound_item(root)
    for argv in (("work", "start", slug), ("work", "submit", slug),
                 ("work", "complete", slug, "--resolution", "done", "--confirm")):
        code, out, err = cli(root, *argv)
        assert code == 0, (argv, err)
    t = fake.tickets[TICKET_ID]
    print("after complete:", t.status, t.assignee)
    t.status, t.assignee = "In Progress", None        # reopened, unassigned
    for argv in (("work", "tracker", "sync", slug),
                 ("work", "tracker", "claim", slug),
                 ("work", "tracker", "claim", slug, "--take-over"),
                 ("work", "tracker", "sync", slug)):
        code, out, err = cli(root, *argv)
        print("\n$ tcw", " ".join(argv), "->", code)
        print("  OUT:", out.strip())
        print("  ERR:", err.strip())
        print("  ticket:", fake.tickets[TICKET_ID].status,
              fake.tickets[TICKET_ID].assignee)
