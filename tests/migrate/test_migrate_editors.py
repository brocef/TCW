"""The editor on 3.x text (TCW-116 plan Step 4).

Here, not in `tests/test_config_edit.py`, because these hold the 3.x forms
TCW-112's test-file rule keeps out of every test outside the migration's
own (Decided 24): a capability state file's `id: cap-…`, and `overrides`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tcw.migrate.editors import convert_text
from tcw.project_files import version_line
from tcw.reference_fields import fields_of
from tcw.store.config_edit import ConfigEditRefused, RemoveTop, SetTop, edit_text

PATH = Path("docs/capabilities/x/meta.yaml")


def test_a_capabilitys_own_3x_id_is_removed_and_nothing_else():
    text = "# the camera\nid: cap-1a2b3c\nname: Camera\nStatus: Supported\n"
    assert edit_text(PATH, text, [RemoveTop("id")]) == \
        "# the camera\nname: Camera\nStatus: Supported\n"


def test_an_override_pointer_is_removed_with_its_comment_reported():
    text = ("name: Login\n"
            "overrides: cap-2b3c4d   # the parent's login\n"
            "Status: Supported\n")
    dropped: list[str] = []
    after = edit_text(PATH, text, [RemoveTop("overrides")], dropped=dropped)
    assert after == "name: Login\nStatus: Supported\n"
    assert dropped == ["# the parent's login"]


def test_one_file_converted_in_the_fixed_order():
    text = "id: cap-1a2b3c\nname: Camera\nSubject: [invoice]\n"
    done = convert_text(PATH, text,
                        [RemoveTop("id"), SetTop("parent", "app.capabilities/cli", after="name")],
                        fields=fields_of("capability"),
                        replace=lambda row, value: f"app.taxonomy/{value}"
                        if row.name == "Subject" else None,
                        expect={"tcw-version": version_line().split()[1], "name": "Camera",
                                "parent": "app.capabilities/cli",
                                "Subject": ["app.taxonomy/invoice"]})
    assert done.text == (version_line() + "name: Camera\nparent: app.capabilities/cli\n"
                         "Subject: [app.taxonomy/invoice]\n")
    assert done.changed == ["Subject invoice -> app.taxonomy/invoice"]


def test_a_value_rewritten_after_the_structural_edit_is_caught_by_the_final_check():
    """The structural edit sets `parent`; the reference rewrite then changes
    it again. The final parse is compared with what the plan intends."""
    text = "id: cap-1a2b3c\nname: Camera\n"
    with pytest.raises(ConfigEditRefused, match="would not mean what was intended"):
        convert_text(PATH, text, [RemoveTop("id"), SetTop("parent", "app.capabilities/cli")],
                     fields=fields_of("capability"),
                     replace=lambda row, value: "other.capabilities/cli"
                     if row.name == "parent" else None,
                     expect={"tcw-version": version_line().split()[1], "name": "Camera",
                             "parent": "app.capabilities/cli"})


def test_a_converted_text_without_a_4_0_version_is_refused():
    text = "tcw-version: 3.0.2\nname: Camera\n"
    with pytest.raises(ConfigEditRefused, match="format of TCW 3.0"):
        convert_text(PATH, text, [])
    assert yaml.safe_load(convert_text(PATH, "name: Camera\n", []).text)["name"] == "Camera"


def test_a_3x_projects_block_is_removed_whole():
    text = ("id: app\n"
            "# who we read from\n"
            "projects:\n"
            "  # the parent\n"
            "  parent:\n"
            "    core: ../core\n"
            "work:\n"
            "  backend: filesystem\n")
    dropped: list[str] = []
    after = edit_text(Path("tcw-config.yaml"), text, [RemoveTop("projects")], dropped=dropped)
    assert after == "id: app\n# who we read from\nwork:\n  backend: filesystem\n"
    assert dropped == ["# the parent"]
