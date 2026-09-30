"""The web app on a slug two folders hold: the board still lists, and the item's
own route refuses with a message naming both folders instead of a server error
(spec: 2026-09-30-refuse-instead-of-crashing-when-a-slug-is-held-by-two-folders)."""

import shutil
import subprocess
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from tcw.store.fs import FsWorkStore

from test_serve_write import _get_json, _node, _start_server


@pytest.fixture
def served(tmp_path):
    root = _node(tmp_path)
    work = FsWorkStore.open(root)
    twice, other = work.create("Twice").slug, work.create("Other").slug
    waiting = work.create("Waiting").slug
    work.add_blocker(waiting, twice)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    (root / "docs/work/active").mkdir(exist_ok=True)
    shutil.copytree(root / "docs/work/backlog" / twice, root / "docs/work/active" / twice)
    httpd, base = _start_server(root)
    yield base, twice, other, waiting
    httpd.shutdown()


def test_the_board_still_lists(served):
    base, twice, other, waiting = served
    body = _get_json(base, "/api/work")
    text = str(body)
    assert other in text and waiting in text, text


def test_the_item_route_refuses_without_a_server_error(served):
    base, twice, _, _ = served
    with pytest.raises(HTTPError) as caught:
        urlopen(f"{base}/api/work/{twice}")
    error = caught.value
    message = error.read().decode("utf-8")
    assert error.code != 500, message
    assert "held by 2 folders" in message and "server error" not in message, message
