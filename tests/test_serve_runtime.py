from unittest.mock import Mock

import pytest

from tcw.serve.runtime import (
    MINIMUM_NODE, _supervise, find_compatible_node, parse_node_version,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("v22.12.0\n", MINIMUM_NODE), ("24.1.2", (24, 1, 2)), ("v22.12.0-rc.1", MINIMUM_NODE)],
)
def test_parse_node_version(raw, expected):
    assert parse_node_version(raw) == expected


def test_parse_node_version_rejects_noise():
    assert parse_node_version("node twenty-two") is None


def test_missing_node_is_actionable(monkeypatch):
    monkeypatch.setattr("tcw.serve.runtime.shutil.which", lambda _name: None)
    with pytest.raises(RuntimeError, match="Node.js 22.12"):
        find_compatible_node()


def test_old_node_is_actionable(monkeypatch):
    monkeypatch.setattr("tcw.serve.runtime.shutil.which", lambda _name: "/node")
    monkeypatch.setattr(
        "tcw.serve.runtime.subprocess.run",
        lambda *_args, **_kwargs: Mock(stdout="v22.11.0\n"),
    )
    with pytest.raises(RuntimeError, match="found 22.11.0"):
        find_compatible_node()


def test_current_node_is_accepted(monkeypatch):
    monkeypatch.setattr("tcw.serve.runtime.shutil.which", lambda _name: "/node")
    monkeypatch.setattr(
        "tcw.serve.runtime.subprocess.run",
        lambda *_args, **_kwargs: Mock(stdout="v24.0.0\n"),
    )
    assert find_compatible_node() == "/node"


def test_sidecar_token_validation():
    from tcw.serve import _valid_sidecar_token

    assert _valid_sidecar_token("secret", "secret") is True
    assert _valid_sidecar_token("wrong", "secret") is False
    assert _valid_sidecar_token("", None) is True


def test_supervisor_rejects_node_exit():
    process = Mock()
    process.poll.return_value = 7
    sidecar_thread = Mock()
    sidecar_thread.is_alive.return_value = True
    with pytest.raises(RuntimeError, match="status 7"):
        _supervise(process, sidecar_thread, poll_interval=0)


def test_supervisor_rejects_sidecar_exit():
    process = Mock()
    process.poll.return_value = None
    sidecar_thread = Mock()
    sidecar_thread.is_alive.return_value = False
    with pytest.raises(RuntimeError, match="sidecar exited"):
        _supervise(process, sidecar_thread, poll_interval=0)
