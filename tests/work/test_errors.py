"""Each error carries the exit code the spec gives it (TCW-69, Design 5.5).

TCW-73's exit-code table is not in the repository yet, so the numbers are
pinned here as the spec states them.
"""

import pytest

from tcw import exit as codes
from tcw.errors import (
    BackendError, MovedWithoutNote, NotFound, Refused, TcwError, Unreachable,
    UsageError,
)


def test_the_exit_codes_are_the_spec_s_numbers():
    assert (codes.OK, codes.ERROR, codes.USAGE, codes.REFUSED, codes.NOT_FOUND,
            codes.UNREACHABLE, codes.MOVED_WITH_PROBLEM) == (0, 1, 2, 3, 4, 5, 6)


@pytest.mark.parametrize("cls, code", [
    (BackendError, codes.ERROR),
    (UsageError, codes.USAGE),
    (Refused, codes.REFUSED),
    (NotFound, codes.NOT_FOUND),
    (Unreachable, codes.UNREACHABLE),
    (MovedWithoutNote, codes.MOVED_WITH_PROBLEM),
])
def test_each_error_carries_its_code(cls, code):
    error = cls("message")
    assert isinstance(error, TcwError)
    assert error.code == code
    assert str(error) == "message"


def test_a_refusal_can_name_the_record_the_backend_already_made():
    assert Refused("stopped").name is None
    assert Refused("stopped", name="TCW-12").name == "TCW-12"
