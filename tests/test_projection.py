"""The work item JSON projection.

Every value shape here is produced by running real YAML through
`yaml.safe_load`, not by building the Python object directly. That is the point:
`WorkItem.capabilities` is filled from a YAML file, so the question is what the
loader hands over, and a test that constructs its own `datetime.date` could drift
from that without anyone noticing.
"""

import base64
import datetime
import json
import math
from dataclasses import fields

import pytest
import yaml

from tcw.store.base import WORK_ARTIFACTS, Artifact, WorkItem
from tcw.work.projection import (
    CIRCULAR, SCHEMA_VERSION, WORK_ITEM_SCHEMA, _json_safe, work_item_json,
)


def _loaded(text: str):
    """The value `capabilities` would actually hold, loaded the way TCW loads it."""
    return yaml.safe_load(text)["x"]


# ── the walker, shape by shape ────────────────────────────────────────────────


def test_scalars_pass_through_unchanged():
    assert _json_safe(_loaded("x: null")) is None
    assert _json_safe(_loaded("x: true")) is True
    assert _json_safe(_loaded("x: 7")) == 7
    assert _json_safe(_loaded("x: 1.5")) == 1.5
    assert _json_safe(_loaded("x: hello")) == "hello"


def test_a_yaml_date_and_datetime_render_iso():
    # A bare `2026-01-01` in YAML is a date object, not a string.
    assert isinstance(_loaded("x: 2026-01-01"), datetime.date)
    assert _json_safe(_loaded("x: 2026-01-01")) == "2026-01-01"
    assert _json_safe(_loaded("x: 2026-01-01 12:30:00")) == "2026-01-01 12:30:00"


def test_binary_becomes_base64_not_a_python_repr():
    raw = _loaded("x: !!binary aGk=")
    assert raw == b"hi"                      # what the loader produces
    projected = _json_safe(raw)
    assert projected == base64.b64encode(b"hi").decode()
    assert base64.b64decode(projected) == b"hi"
    assert "b'" not in projected             # str(bytes) would have given "b'hi'"


def test_a_yaml_set_becomes_a_sorted_array_deterministically():
    raw = _loaded("x: !!set {b: null, a: null, 2: null}")
    assert isinstance(raw, set)
    first = _json_safe(raw)
    assert first == _json_safe(_loaded("x: !!set {2: null, a: null, b: null}"))
    assert first == [2, "a", "b"]            # key=str never compares elements


@pytest.mark.parametrize("literal, rendered", [
    (".nan", "nan"), (".inf", "inf"), ("-.inf", "-inf"),
])
def test_non_finite_floats_become_strings(literal, rendered):
    raw = _loaded(f"x: {literal}")
    assert isinstance(raw, float) and not math.isfinite(raw)
    assert _json_safe(raw) == rendered
    # The reason this branch exists: json.dumps never consults default= for a
    # float, so the old projection emitted this unparseable document.
    assert json.dumps(raw) in ("NaN", "Infinity", "-Infinity")


def test_a_yaml_anchor_cycle_renders_a_marker_instead_of_recursing():
    raw = yaml.safe_load("a: &x\n  b: *x\n")
    with pytest.raises(ValueError, match="Circular reference"):
        json.dumps(raw)
    assert _json_safe(raw) == {"a": {"b": CIRCULAR}}


def test_the_same_object_twice_is_not_a_cycle():
    # A DAG is not a loop: both positions render in full.
    raw = yaml.safe_load("shared: &s [1, 2]\na: *s\nb: *s\n")
    assert _json_safe(raw) == {"shared": [1, 2], "a": [1, 2], "b": [1, 2]}


def test_colliding_stringified_keys_raise_and_name_both():
    raw = yaml.safe_load('1: "a"\n"1": "b"\n')
    assert set(raw) == {1, "1"}              # the loader really keeps both
    with pytest.raises(ValueError) as e:
        _json_safe(raw)
    assert "'1'" in str(e.value) and "1" in str(e.value)
    assert "would be lost" in str(e.value)


def test_every_walker_output_survives_a_strict_encoder():
    raw = yaml.safe_load(
        "d: 2026-01-01\n"
        "s: !!set {a: null}\n"
        "b: !!binary aGk=\n"
        "n: .nan\n"
        "nested: {deep: [1, {inner: 2026-01-01}]}\n"
    )
    json.dumps(_json_safe(raw), allow_nan=False)   # raises if anything slipped


# ── the schema ────────────────────────────────────────────────────────────────


def test_the_schema_declares_exactly_the_model_plus_two():
    """Criterion 3, and the reason it exists.

    A closed schema that every emitted document validates against proves the
    schema and the projection agree — not that they agree about the right
    document. Drop `started` from both and every other assertion still passes.
    Only the model can settle it.
    """
    declared = set(WORK_ITEM_SCHEMA["properties"])
    expected = {f.name for f in fields(WorkItem)} | {"schema", "artifacts"}
    assert declared == expected, (
        f"undeclared WorkItem fields: {sorted(expected - declared)}; "
        f"declared but not on WorkItem: {sorted(declared - expected)}. "
        "Add the field to WORK_ITEM_SCHEMA with its JSON type, or remove it.")


def test_the_schema_is_closed_and_fully_required():
    assert WORK_ITEM_SCHEMA["additionalProperties"] is False
    assert set(WORK_ITEM_SCHEMA["required"]) == set(WORK_ITEM_SCHEMA["properties"])


def test_the_artifacts_map_is_pinned_to_the_registry():
    art = WORK_ITEM_SCHEMA["properties"]["artifacts"]
    assert set(art["properties"]) == set(WORK_ARTIFACTS)
    assert set(art["required"]) == set(WORK_ARTIFACTS)
    assert art["additionalProperties"] is False


# ── the document ──────────────────────────────────────────────────────────────


def _item(**kw) -> WorkItem:
    base = dict(slug="s", title="T", status="backlog")
    base.update(kw)
    return WorkItem(**base)


def test_the_document_validates_against_the_schema():
    jsonschema = pytest.importorskip("jsonschema")
    doc = work_item_json(_item(), [Artifact(n, False) for n in WORK_ARTIFACTS])
    jsonschema.validate(doc, WORK_ITEM_SCHEMA)
    assert doc["schema"] == SCHEMA_VERSION


def test_the_artifacts_map_reports_presence_for_every_registered_name():
    arts = [Artifact(n, n in {"spec", "intake"}) for n in WORK_ARTIFACTS]
    doc = work_item_json(_item(), arts)
    assert set(doc["artifacts"]) == set(WORK_ARTIFACTS)
    assert doc["artifacts"]["spec"] is True
    assert doc["artifacts"]["intake"] is True
    assert doc["artifacts"]["plan"] is False


def test_both_blocker_shapes_validate():
    jsonschema = pytest.importorskip("jsonschema")
    doc = work_item_json(
        _item(blocked_by=[{"slug": "other"}, {"external": "https://x/1"}]),
        [Artifact(n, False) for n in WORK_ARTIFACTS])
    jsonschema.validate(doc, WORK_ITEM_SCHEMA)


def test_a_hostile_capabilities_blob_still_emits_valid_json():
    jsonschema = pytest.importorskip("jsonschema")
    blob = yaml.safe_load(
        "when: 2026-01-01\nraw: !!binary aGk=\nvals: !!set {a: null}\nn: .nan\n")
    doc = work_item_json(_item(capabilities=blob),
                         [Artifact(n, False) for n in WORK_ARTIFACTS])
    jsonschema.validate(doc, WORK_ITEM_SCHEMA)
    # allow_nan=False and no default=: the document is JSON-native already.
    json.dumps(doc, allow_nan=False)
