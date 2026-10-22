"""This repository's two configurations hold the same settings (TCW-106 plan
step 5a).

Until `tcw migrate` exists (TCW-116), this repository keeps both: the root
`tcw-config.yaml`, which the released 3.x CLI driving its lifecycle reads, and
`.tcw/tcw-config.yaml`, which the code under test reads. They differ in exactly
two ways, the version line and the key `not_tags` written `not-tags`, so a 3.x
change merged into the root file cannot leave the 4.0 copy behind unnoticed.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tcw.project_files import (LEGACY_SENTINEL, SENTINEL, VERSION_KEY,
                               version_problem, without_version)

ROOT = Path(__file__).resolve().parent.parent


def _as_3x_keys(value):
    """`value` with every `not-tags` key spelled the 3.x way."""
    if isinstance(value, dict):
        return {("not_tags" if k == "not-tags" else k): _as_3x_keys(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [_as_3x_keys(v) for v in value]
    return value


def test_the_4_0_configuration_is_the_3_x_one_with_a_version_line():
    old = yaml.safe_load((ROOT / LEGACY_SENTINEL).read_text(encoding="utf-8"))
    new_text = (ROOT / SENTINEL).read_text(encoding="utf-8")
    new = yaml.safe_load(new_text)
    assert new_text.startswith(f"{VERSION_KEY}: "), "the version is the first line"
    assert version_problem(new) is None
    assert "not_tags" not in new_text, "the 4.0 copy uses the 4.0 key"
    assert _as_3x_keys(without_version(new)) == old


def test_the_personal_file_is_ignored_inside_the_tcw_folder():
    lines = (ROOT / ".tcw" / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/tcw-config.local.yaml" in lines
