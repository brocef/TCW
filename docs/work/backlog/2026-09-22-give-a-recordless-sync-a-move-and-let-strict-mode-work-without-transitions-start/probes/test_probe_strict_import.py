from __future__ import annotations

from test_tracker_sync import (STATUSES, KEY, TICKET_ID, A, B, cli, fake,  # noqa: F401
                               make_node, record, status)
from test_tracker_strict import set_tracker_key


def test_strict_without_transitions_start_cannot_import(tmp_path, fake):
    # `transitions=None` leaves work.tracker.transitions out entirely: legal since C6.
    root = make_node(tmp_path, statuses=STATUSES, transitions=None)
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
    set_tracker_key(root, "strict", True)
    code, out, err = cli(root, "validate")
    print("$ tcw validate ->", code)
    print(out.strip()[-600:], err.strip()[-600:])
    for argv in (("work", "tracker", "import", KEY),
                 ("work", "new", "Some work"),
                 ("work", "tracker", "link", "nope", KEY)):
        code, out, err = cli(root, *argv)
        print("\n$ tcw", " ".join(argv), "->", code)
        print("  OUT:", out.strip())
        print("  ERR:", err.strip())


def test_strict_without_transitions_start_can_start_and_finish(tmp_path, fake):
    """The same configuration, with the item created before strict was turned on."""
    root = make_node(tmp_path, statuses=STATUSES, transitions=None)
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
    code, out, err = cli(root, "work", "tracker", "import", KEY)
    print("import ->", code, out.strip(), err.strip())
