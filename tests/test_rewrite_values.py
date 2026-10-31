"""`rewrite_yaml` given a function rather than pairs (TCW-116 plan Step 4,
Decided 9): the function is asked for each reference at a field the rows
name, and what it returns replaces the value in place."""

from __future__ import annotations

from tcw.ids import parse_full_id
from tcw.reference_fields import fields_of
from tcw.rewrite import rewrite_yaml

CAPABILITY = fields_of("capability")

TEXT = """\
name: X
Subject: [invoice, 'order']
Roles:
- '!roles/admin'
- roles/user
Feature: cli
"""


def replace(row, value):
    return {"invoice": "app.taxonomy/invoice", "order": "app.taxonomy/order",
            "roles/admin": "app.capabilities/roles/admin"}.get(value)


def test_flow_and_block_entries_are_replaced_keeping_quotes_and_the_bang():
    new, changed, done = rewrite_yaml(TEXT, CAPABILITY, replace)
    assert new == TEXT.replace("[invoice, 'order']",
                               "[app.taxonomy/invoice, 'app.taxonomy/order']") \
        .replace("'!roles/admin'", "'!app.capabilities/roles/admin'")
    assert changed == ["Subject invoice -> app.taxonomy/invoice",
                       "Subject order -> app.taxonomy/order",
                       "Roles !roles/admin -> !app.capabilities/roles/admin"]
    assert done == []


def test_a_value_the_function_leaves_is_left_byte_for_byte():
    assert rewrite_yaml(TEXT, CAPABILITY, lambda row, value: None) == (TEXT, [], [])


def test_the_function_is_told_which_field():
    asked = []
    rewrite_yaml(TEXT, CAPABILITY, lambda row, value: asked.append((row.name, value)))
    assert asked == [("Subject", "invoice"), ("Subject", "order"),
                     ("Roles", "roles/admin"), ("Roles", "roles/user"), ("Feature", "cli")]


def test_the_pair_form_gives_what_it_gave():
    pairs = [(parse_full_id("app.taxonomy/invoice"), parse_full_id("app.taxonomy/bill"))]
    text = "Subject:\n- app.taxonomy/invoice\n- app.taxonomy/bill\n"
    assert rewrite_yaml(text, CAPABILITY, pairs) == (
        "Subject:\n- app.taxonomy/bill\n- app.taxonomy/bill\n",
        ["Subject app.taxonomy/invoice -> app.taxonomy/bill"],
        ["Subject app.taxonomy/bill"])
