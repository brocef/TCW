"""TCW-113 plan choice 10: the state one command, or one `tcw serve`
request, keeps for itself, thread by thread."""

from __future__ import annotations

import threading

from tcw.config import begin_command, command_span, command_state, end_command


def test_none_outside_a_command():
    assert command_state() is None


def test_a_dictionary_inside_a_command():
    begin_command()
    try:
        assert command_state() == {}
    finally:
        end_command()
    assert command_state() is None


def test_each_threads_span_is_its_own():
    entered, release = threading.Barrier(2), threading.Event()
    seen: dict[str, object] = {}

    def first():
        with command_span() as state:
            state["who"] = "first"
            entered.wait()
            release.wait()
            seen["first"] = command_state()

    def second():
        with command_span() as state:
            state["who"] = "second"
            entered.wait()
        # Leaving its span drops only its own state.
        seen["second-after"] = command_state()
        release.set()

    threads = [threading.Thread(target=first), threading.Thread(target=second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
    assert seen == {"first": {"who": "first"}, "second-after": None}


def test_a_span_inside_a_command_leaves_the_command_state():
    begin_command()
    try:
        outer = command_state()
        outer["kept"] = 1
        with command_span() as inner:
            assert inner == {} and inner is not outer
        assert command_state() is outer
    finally:
        end_command()


def test_a_span_inside_a_span_leaves_the_outer_one():
    with command_span() as outer:
        outer["kept"] = 1
        with command_span() as inner:
            assert inner == {}
        assert command_state() is outer
    assert command_state() is None
