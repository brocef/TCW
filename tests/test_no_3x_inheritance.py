"""TCW 3.x inheritance stays removed (TCW-112 plan Step 20; AC 30).

A static test, read from the files: the federation checks' messages, the
functions TCW 4.0 removed, and the fixture forms that set up 3.x inheritance
(`extends` under a store's section, an `overrides:` pointer in a state file,
an opaque `id: cap-…`) appear nowhere they should not. A fixture that keeps
one of those forms makes a test pass for the wrong reason, or exercise code
that no longer exists, so each file that may write one is named here with
the refusal it tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import tcw

CODE = Path(tcw.__file__).resolve().parent
TESTS = Path(__file__).resolve().parent

#: Messages of the checks TCW 4.0 removed (AC 30).
REMOVED_MESSAGES = ("cycle in taxonomy federation", "cycle in capability federation",
                    "collides with local top-level")

#: Functions TCW 4.0 removed; none is defined or called in the code.
REMOVED_NAMES = ("_mint_cap_id", "get_by_id", "_apply_override", "extends_add",
                 "extends_remove")

#: The fixture forms, each a pattern over a test file's text.
FIXTURE_FORMS = {
    "extends": re.compile(
        # The section by name or as an f-string's field, then a real
        # newline or `\n` written in a string literal.
        r"(?:taxonomy|capabilities|\{[a-z_]+\}):[ \t]*(?:\n|\\n)\s*extends:"
        r"|(?:taxonomy|capabilities)\.extends:"
        r"|set_component_key\([^)]*\"extends\""
        r"|declare_extends\("),
    # A 3.x pointer is an opaque id or `<project>/<id>`; a 4.0 full
    # identifier (`core.capabilities/cli/x`, as `show` prints it) never
    # matches, since its project is followed by a dot.
    "overrides": re.compile(
        r"overrides:\s+(?:cap-|[a-z0-9-]+/)"
        r"|overrides=\""
        r"|\"overrides\":\s*\"(?:cap-|[a-z0-9-]+/)"),
    "cap-id": re.compile(r"id: cap-|id=\"cap-|\"id\": \"cap-|'id': 'cap-"),
}

#: The test files that may write a form, and why: each tests its refusal,
#: or writes a 3.x file on purpose.
ALLOWED = {
    "extends": {
        "test_no_extends.py": "AC 15: the key is refused, and ignored in a parent",
        "test_capabilities_federation.py": "Design 1.5, refused here, ignored in a parent",
        "test_taxonomy.py": "Design 1.5, the taxonomy key refused and ignored",
        "test_validate_moved_stores.py": "Design 1.5, reported without a local tree",
        "test_store_provisioning.py": "Design 1.5, a store that will not open",
        "test_legacy_store_config.py": "Design 6.8, a pre-2.5.0 store file",
        "test_config_edit.py": "the generic line editor, any key",
        "nodeconfig.py": "the helper the refusal tests write the key with",
    },
    "overrides": {
        "test_overrides_by_path.py": "AC 29: the key is an error at its file",
        "test_capabilities_federation.py": "Design 6.4, the same error",
        "test_no_3x_inheritance.py": "this guard's own samples",
    },
    "cap-id": {
        "test_overrides_by_path.py": "AC 28: an opaque id fails row k",
        "test_capabilities.py": "Design 5.3, the same error",
        "test_object_folder_shape.py": "a 3.x meta.yaml left in a store",
        "test_object_walk.py": "a 3.x meta.yaml left in a store",
        "test_no_3x_inheritance.py": "this guard's own samples",
    },
}

#: Code and tests that a later item (TCW-116, `tcw migrate`) adds, which read
#: and rewrite the 3.x forms on purpose. Empty until then.
MIGRATION_CODE: tuple[str, ...] = ()
MIGRATION_TESTS: tuple[str, ...] = ()


def code_files(root: Path = CODE) -> list[Path]:
    return sorted(p for p in root.rglob("*.py")
                  if str(p.relative_to(root)) not in MIGRATION_CODE)


def test_no_removed_check_message_is_left_in_the_code():
    found = [f"{p.relative_to(CODE)}: {message}" for p in code_files()
             for message in REMOVED_MESSAGES if message in p.read_text(encoding="utf-8")]
    assert found == []


def removed_names(text: str) -> list[str]:
    return [name for name in REMOVED_NAMES if re.search(rf"\b{name}\b", text)]


def test_no_removed_function_is_defined_or_called_in_the_code():
    found = [f"{p.relative_to(CODE)}: {name}" for p in code_files()
             for name in removed_names(p.read_text(encoding="utf-8"))]
    assert found == []


def offenders(root: Path = TESTS) -> list[str]:
    found = []
    for path in sorted(root.rglob("*.py")):
        if path.name in MIGRATION_TESTS:
            continue
        text = path.read_text(encoding="utf-8")
        for form, pattern in FIXTURE_FORMS.items():
            if pattern.search(text) and path.name not in ALLOWED[form]:
                found.append(f"{path.relative_to(root)}: {form}")
    return found


def test_no_fixture_sets_up_3x_inheritance():
    assert offenders() == []


def test_every_allowed_file_still_needs_it():
    """An entry left here after its file stopped writing the form would let
    a new one back in unseen."""
    stale = [f"{name}: {form}" for form, names in ALLOWED.items() for name in names
             if not any(FIXTURE_FORMS[form].search(p.read_text(encoding="utf-8"))
                        for p in TESTS.rglob(name))]
    assert stale == []


def test_each_form_is_seen(tmp_path):
    """The guard itself: each form, written in a file not allowed it, is
    reported once (the mutation check, kept)."""
    samples = {
        "extends": 'TEXT = "capabilities:\\n  extends:\\n    - base\\n"\n',
        "overrides": 'write_cap(root, "ov/x", overrides="cap-aaa111")\n',
        "cap-id": 'write_cap(root, "x", id="cap-x00001")\n',
    }
    for form, text in samples.items():
        (tmp_path / f"test_sample_{form.replace('-', '_')}.py").write_text(text)
    assert sorted(offenders(tmp_path)) == sorted(
        f"test_sample_{form.replace('-', '_')}.py: {form}" for form in samples)


def test_a_4x_overrides_line_is_not_a_pointer(tmp_path):
    (tmp_path / "test_show.py").write_text(
        'assert "overrides: core.capabilities/cli/x" in out\n')
    assert offenders(tmp_path) == []


def test_a_removed_name_and_message_are_seen():
    assert removed_names("def get_by_id(self):\n") == ["get_by_id"]
    assert removed_names("store.extends_add('x')\n") == ["extends_add"]
    assert removed_names("def get_by_identifier(self):\n") == []
