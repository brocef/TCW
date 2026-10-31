"""The table of keys TCW knows and the names of the override variables
(TCW-109 Design 1.1, 4.1, 4.3, AC 26), on the functions alone."""

from __future__ import annotations

import pytest

from tcw.config import INHERITED_KEYS
from tcw.config_keys import (BOOLEAN, LIST, MAPPING, NUMBER, TEXT, decode_key,
                             key_part, known_keys, override_name)
from tcw.store.base import PROCEDURE_IDS
from tcw.work.config import SIDE_STAGE_KEYS
from tcw.work.model import PRIORITIES, SIDE, STAGES


def test_the_inherited_keys_in_their_order():
    assert INHERITED_KEYS == ("work.tags", "work.jira")


def test_ac26_one_name_per_key_and_back():
    table = known_keys()
    for row in STAGES:
        assert ("work", "stages", row.name) in table
    for name in PROCEDURE_IDS:
        assert ("work", "procedures", name) in table
    for priority in PRIORITIES:
        assert ("work", "jira", "priorities", priority) in table
    names = [override_name(path, "p") for path in table]
    assert len(set(names)) == len(names) == len(table)
    for path in table:
        assert decode_key(key_part(path)) == path


def test_the_side_stage_has_only_enabled_and_prompt():
    side = next(s.name for s in STAGES if s.kind == SIDE)
    under = {path[3] for path in known_keys()
             if path[:3] == ("work", "stages", side) and len(path) == 4}
    assert under == set(SIDE_STAGE_KEYS) == {"enabled", "prompt"}


def test_design_4_1_the_name():
    assert override_name(("work", "jira", "credentials", "email-env"), "my-proj") \
        == "TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__MY_PROJ"
    assert override_name(("user", "name"), "tcw") == "TCW_USER_NAME__TCW"


@pytest.mark.parametrize("part", ["WORK_STAGES_SPEC_PROMPTS", "TCW_VERSION",
                                  "WORK_STAGES_DESIGN_PROMPT",
                                  "WORK_STAGES_SPEC_PROMPT_BLOB"])
def test_ac20_parts_that_name_no_key(part):
    assert decode_key(part) is None


@pytest.mark.parametrize("path, kind", [
    (("work",), MAPPING), (("work", "stages", "spec"), MAPPING),
    (("work", "jira", "credentials"), MAPPING),
    (("user", "name"), TEXT), (("work", "jira", "credentials", "email-env"), TEXT),
    (("work", "jira", "credentials", "token-env"), TEXT),
    (("work", "stages", "spec", "prompt"), LIST), (("work", "stages", "spec", "pre"), LIST),
    (("work", "stages", "spec", "post"), LIST),
    (("work", "procedures", "documentation-sync"), LIST),
    (("work", "hooks", "timeout"), NUMBER), (("work", "jira", "timeout"), NUMBER),
    (("work", "stages", "spec", "enabled"), BOOLEAN),
])
def test_each_kind(path, kind):
    assert known_keys()[path] == kind


def test_no_version_and_no_key_inside_a_list_entry():
    assert not any("tcw-version" in path for path in known_keys())
    assert not any(part in ("blob", "file", "when", "command") for path in known_keys()
                   for part in path[3:] if path[:2] == ("work", "stages"))
