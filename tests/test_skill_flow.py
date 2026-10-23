"""The product flow the work and capabilities skills prescribe, end to end
through the CLI (TCW-74 acceptance criterion 13).

A capability the item declares new is written into the ledger with the status
it really has, in the same change as the code, and the move out of implement
checks that it was. Nothing flips a status at completion.
"""

import io
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore


@pytest.fixture
def item(tmp_path, monkeypatch, capsys):
    """A filesystem project, spec, plan and review enabled (the defaults), with
    one item at implement that declares `billing/refund` new."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", "1")
    root = tmp_path / "shop"
    root.mkdir()
    monkeypatch.chdir(root)
    assert main(["init", "--id", "shop", "work", "capabilities"]) == 0
    monkeypatch.setattr("sys.stdin", io.StringIO("Refund a captured payment.\n"))
    assert main(["work", "new", "Refund a payment"]) == 0
    slug = capsys.readouterr().out.strip().splitlines()[-1]

    assert _advance(slug, capsys) == (0, "spec")
    _path(slug, capsys).joinpath("capabilities.yaml").write_text(
        "new:\n  - shop.capabilities/billing/refund\n", encoding="utf-8")
    assert _advance(slug, capsys) == (0, "plan")
    assert _advance(slug, capsys) == (0, "implement")
    round_one = _path(slug, capsys, "implement", "--next")
    round_one.parent.mkdir(parents=True, exist_ok=True)
    round_one.write_text("Refunds a captured payment.\n", encoding="utf-8")
    return root, slug


def _advance(slug, capsys):
    capsys.readouterr()
    code = main(["work", "advance", slug])
    return code, capsys.readouterr().out.strip()


def _path(slug, capsys, *args) -> Path:
    capsys.readouterr()
    assert main(["work", "path", slug, *args]) == 0
    return Path(capsys.readouterr().out.strip())


def test_a_record_written_with_its_real_status_lets_the_item_reach_review(
        item, capsys, monkeypatch):
    root, slug = item
    monkeypatch.setattr("sys.stdin", io.StringIO("Refund a payment.\n"))
    assert main(["capabilities", "add", "billing/refund", "Refund a payment",
                 "--status", "Supported"]) == 0
    assert FsCapabilitiesStore.open(root).get_view("billing/refund").status == "Supported"
    assert _advance(slug, capsys) == (0, "review")


def test_a_record_left_at_its_default_status_is_refused(item, capsys, monkeypatch):
    root, slug = item
    monkeypatch.setattr("sys.stdin", io.StringIO("Refund a payment.\n"))
    assert main(["capabilities", "add", "billing/refund", "Refund a payment"]) == 0
    assert FsCapabilitiesStore.open(root).get_view("billing/refund").status == "Missing"
    capsys.readouterr()
    assert main(["work", "advance", slug]) == 3
    assert "billing/refund" in capsys.readouterr().err
