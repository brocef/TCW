from __future__ import annotations

from test_tracker_sync import (STATUSES, KEY, TICKET_ID, A, B, cli, fake,  # noqa: F401
                               make_node, bound_item, record, status)


def test_recovery_without_an_exclusive_transition(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    for argv in (("work", "start", slug), ("work", "submit", slug),
                 ("work", "complete", slug, "--resolution", "done", "--confirm")):
        assert cli(root, *argv)[0] == 0
    t = fake.tickets[TICKET_ID]
    t.status, t.assignee = "In Progress", B      # reopened and handed to Bob
    for argv in (("work", "tracker", "sync", slug),
                 ("work", "tracker", "claim", slug),
                 ("work", "tracker", "claim", slug, "--take-over"),
                 ("work", "tracker", "sync", slug)):
        code, out, err = cli(root, *argv)
        print("\n$ tcw", " ".join(argv), "->", code)
        print("   OUT:", out.strip(), "| ERR:", err.strip())
        print("   ticket:", fake.tickets[TICKET_ID].status,
              fake.tickets[TICKET_ID].assignee, "| record:", record(root, slug))
