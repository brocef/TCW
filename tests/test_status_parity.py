"""The Python↔TypeScript work-status parity guard.

`web/client/src/model/types.ts` hand-mirrors `WORK_STATUSES` from
`tcw/store/base.py` and carries a comment saying so, but nothing has ever
enforced it. A status added on one side and forgotten on the other is exactly
the drift this exists to catch — and adding a status is precisely when it bites.

Deliberately a Python test rather than a TypeScript one: the failure mode being
guarded is a Python change that forgets the mirror, and a TS-side test only runs
when someone runs the web suite. This runs in the ordinary `pytest` sweep with
no Node.js toolchain involved.
"""
import re
from pathlib import Path

from tcw.store.base import WORK_STATUSES

TYPES_TS = Path(__file__).resolve().parents[1] / "web/client/src/model/types.ts"
TREE_TS = Path(__file__).resolve().parents[1] / "web/client/src/model/tree.ts"


def _ts_array(source: str, name: str) -> list[str]:
    """The string members of `export const <name> = [...]`.

    A regex over another language's source is coarse — it breaks if the
    declaration is reformatted across lines or switched to another shape. That
    is the accepted cost of not requiring Node.js here: the failure is loud and
    the fix is obvious. The explicit "declaration not found" below exists so a
    reformat reads as a broken test rather than silently matching nothing and
    passing.
    """
    m = re.search(rf"export const {name}\s*=\s*\[(.*?)\]", source, re.S)
    assert m, f"{name} declaration not found — was types.ts reformatted?"
    return re.findall(r'"([^"]+)"', m.group(1))


def _ts_map_keys(source: str, name: str) -> list[str]:
    m = re.search(rf"export const {name}\s*=\s*new Map\(\[(.*?)\]\)", source, re.S)
    assert m, f"{name} declaration not found — was tree.ts reformatted?"
    return re.findall(r'\[\s*"([^"]+)"', m.group(1))


def test_typescript_mirrors_the_python_work_statuses():
    ts = _ts_array(TYPES_TS.read_text(encoding="utf-8"), "WORK_STATUSES")
    assert set(ts) == set(WORK_STATUSES), (
        "web/client/src/model/types.ts has drifted from WORK_STATUSES in "
        f"tcw/store/base.py — python={sorted(WORK_STATUSES)} ts={sorted(ts)}"
    )


def test_the_typescript_mirror_preserves_order():
    """Not strictly required for correctness — the TS side sorts through
    WORK_STATUS_ORDER, not through this array — but a mirror that has drifted in
    order has usually drifted for a reason worth looking at."""
    ts = _ts_array(TYPES_TS.read_text(encoding="utf-8"), "WORK_STATUSES")
    assert ts == list(WORK_STATUSES)


def test_the_display_precedence_map_covers_every_status():
    """`tree.test.ts` asserts this from the TypeScript side too; asserting it
    here as well means a Python-side addition is caught without running the web
    suite."""
    keys = _ts_map_keys(TREE_TS.read_text(encoding="utf-8"), "WORK_STATUS_ORDER")
    assert set(keys) == set(WORK_STATUSES)
