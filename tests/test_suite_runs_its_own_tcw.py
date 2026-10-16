"""The suite's `tcw` subprocesses run this interpreter's `tcw` (pre-freeze
clean-up, C6): `tests/conftest.py` puts the interpreter's folder first on
`PATH` when it holds one."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import tcw

HERE = Path(sys.executable).parent


@pytest.mark.skipif(not shutil.which("tcw", path=str(HERE)),
                    reason="no tcw is installed beside this interpreter")
def test_the_first_tcw_on_path_is_this_interpreters():
    assert Path(shutil.which("tcw")).parent == HERE
    ran = subprocess.run(["tcw", "--version"], capture_output=True, text=True,
                         stdin=subprocess.DEVNULL)
    assert ran.returncode == 0, ran.stderr
    assert ran.stdout.split() == ["tcw", tcw.__version__], ran.stdout
