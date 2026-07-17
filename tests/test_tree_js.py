"""Run the tree.js node --test suite from pytest.

The web UI's pure tree model (tcw/serve/static/tree.js) is tested with Node's
built-in test runner (tests/tree.test.mjs, zero JS dependencies). This wrapper
makes `python -m pytest` cover it; skipped when node isn't installed.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_tree_js_suite_passes():
    result = subprocess.run(
        ["node", "--test", str(REPO / "tests" / "tree.test.mjs")],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (
        f"node --test failed:\n{result.stdout}\n{result.stderr}"
    )
