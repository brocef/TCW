"""The `implement` stage must tell an author what to do about a *green* test.

`prompts/implement.md` step 3 has always said to write the failing test first and
watch it fail. It is correct and it produced nothing: "watch it fail" is a private
act, so when the test comes up green instead, the instruction is already satisfied
in the author's own account and there is no rule left to consult.

Across the store-provisioning epic that happened three times, and every
explanation for the green was locally true. What was missing is an action with a
visible result.
"""

from __future__ import annotations

import re

from tcw.work.resolve import load_builtins


def _implement_prompt() -> str:
    """What a user is actually served, not what is on disk — `tcw work stage`
    renders through the builtins, and that rendering is the surface under test."""
    return load_builtins().stage_prompts["implement"]


def test_the_implement_prompt_requires_falsifying_a_green_test():
    """The rule has to name the action, not the disposition.

    "Be suspicious of green tests" is what this drifts into if anyone shortens
    it, and it is worth nothing — the author in the epic *was* suspicious, wrote
    down why the green was fine, and was locally right each time. So the
    assertion is on the two halves that make it an instruction someone can carry
    out in thirty seconds: break the behaviour, and confirm the red.
    """
    prompt = _implement_prompt().lower()

    assert "passes on its first run" in prompt, prompt
    assert "break the behaviour it names" in prompt, prompt
    assert "goes red" in prompt, prompt


def test_the_implement_step_list_did_not_grow():
    """Rewritten into step 3, not appended as a tenth step.

    Two reasons, and the second is the item's whole subject. Steps 4-9 keep their
    numbers, so nothing that cites a step by number goes stale. And a list whose
    third entry went unfollowed does not get fixed by gaining a tenth entry —
    that is repeating the mistake in new words.
    """
    steps = re.findall(r"^(\d+)\.", _implement_prompt(), re.M)

    assert steps == [str(n) for n in range(1, 10)], steps


def test_the_original_rule_survives_the_rewrite():
    """The new sentence extends step 3; it does not replace what was already
    right. A test that has never been red still proves nothing."""
    prompt = _implement_prompt().lower()

    assert "watch it fail" in prompt, prompt
    assert "never been red proves nothing" in prompt, prompt
