"""Change one key of a node's `tcw-config.yaml` without rewriting the file.

**Filesystem-adapter detail, not part of the storage-neutral model.** "Set a key
in the node's configuration" is an operation any store could offer; keeping a
text file's comments and layout while doing it means something only for a text
file. So this module is private to `fs.py`, and knows nothing about stores.

It used to be `yaml.safe_dump` of the whole mapping, which kept keys and values
but deleted every comment, reflowed long strings and re-indented the file — the
one TCW file people annotate by hand. Now the change is spliced into the
original text at the positions PyYAML reports for each node (`yaml.compose`),
and nothing else in the file is touched.

**Every edit is verified before it is returned, and refused rather than
rewritten.** The new text must parse to exactly the intended mapping *and* differ
from the original only inside the stretches the edit declared, with no anchor
and no comment it was not entitled to remove inside them. Meaning alone is not
enough: a lost comment, or a change at an anchor that other keys alias, can both
leave the parsed mapping looking right. A file that cannot be edited this way
gets `ConfigEditRefused`, telling the user what to change by hand. Only a
missing or empty file is written whole, because it has nothing to lose.

Position quirks this relies on, each measured against PyYAML rather than read
from its documentation, and each pinned by a test in `tests/test_config_edit.py`:

- A block collection's end mark lies at the start of the *next* token, after any
  comment lines that follow it, so the end of an entry is taken from its last
  scalar, never from the collection.
- A null written as nothing (`taxonomy:` or `extends: # note`) is a zero-width
  node right after the colon.
- A block scalar's end mark is the start of the following line.
- An alias node *is* the anchored node, so its marks point at the anchor.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


class ConfigEditRefused(ValueError):
    """The file cannot be changed without rewriting it; the message says what
    to change by hand. A `ValueError`, so every command already prints it as a
    one-line `tcw <cmd>: …` error."""


@dataclass(frozen=True)
class SetList:
    section: str
    key: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class SetScalar:
    section: str
    key: str
    value: str


@dataclass(frozen=True)
class Remove:
    """Remove `<section>.<key>`, and the section too when nothing is left in it."""
    section: str
    key: str


@dataclass(frozen=True)
class SetId:
    value: str


Edit = SetList | SetScalar | Remove | SetId


@dataclass(frozen=True)
class _Replacement:
    """Replace `original[start:end]` with `text`; `start == end` inserts."""
    start: int
    end: int
    text: str


class _Refuse(Exception):
    """Internal: why an edit cannot be made. Turned into `ConfigEditRefused`
    with the instruction for the edit that raised it."""


def read_text(path: Path) -> str | None:
    """The file's text exactly as stored — no line-ending translation, which
    `Path.read_text` would do — or None when it does not exist."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def intended(mapping: dict, edits: list[Edit]) -> dict:
    """`mapping` with `edits` applied — what the file must parse to afterwards."""
    out = dict(mapping)
    for edit in edits:
        if isinstance(edit, SetId):
            out["id"] = edit.value
            continue
        section = out.get(edit.section)
        section = dict(section) if isinstance(section, dict) else {}
        if isinstance(edit, Remove):
            section.pop(edit.key, None)
            if section:
                out[edit.section] = section
            else:
                out.pop(edit.section, None)
            continue
        section[edit.key] = (list(edit.values) if isinstance(edit, SetList)
                             else edit.value)
        out[edit.section] = section
    return out


def edit_text(path: Path, text: str | None, edits: list[Edit]) -> str | None:
    """The new file text, or None when the edits change nothing.

    `path` only names the file in a refusal. `text` is what `read_text` returned.
    """
    if text is None or not text.lstrip("\ufeff").strip():
        target = intended({}, edits)
        if not target:
            return None
        return yaml.safe_dump(target, sort_keys=False, allow_unicode=True)
    mapping = _load(text)
    if not isinstance(mapping, dict):
        mapping = {}
    target = intended(mapping, edits)
    if target == mapping:
        return None
    doc = _Document(text)
    replacements: list[_Replacement] = []
    allowed: set[int] = set()
    for edit in edits:
        if intended(mapping, [edit]) == mapping:
            continue                       # this one changes nothing
        try:
            made, ok = doc.plan(edit, mapping)
        except _Refuse as why:
            raise ConfigEditRefused(_message(path, edit, doc, mapping, str(why))) from None
        replacements += made
        allowed |= ok
    replacements.sort(key=lambda r: (r.start, r.end))
    for before, after in zip(replacements, replacements[1:]):
        if after.start < before.end:
            raise ConfigEditRefused(_message(path, edits[0], doc, mapping,
                                             "two changes overlap"))
    new = _assemble(text, replacements)
    _verify(path, text, new, replacements, allowed, target,
            instruction="; and ".join(_instruction(e, doc, mapping) for e in edits))
    return new


# ── reading ─────────────────────────────────────────────────────────────────

def _load(text: str):
    from tcw.store.fs import _UniqueKeyLoader    # fs.py imports this module
    return yaml.load(text, Loader=_UniqueKeyLoader)


def _assemble(text: str, replacements: list[_Replacement]) -> str:
    out, cursor = [], 0
    for r in replacements:
        out += [text[cursor:r.start], r.text]
        cursor = r.end
    return "".join(out) + text[cursor:]


class _Document:
    """The original text, its composed tree, and the position arithmetic."""

    def __init__(self, text: str):
        self.text = text
        self.root = yaml.compose(text)
        first_break = text.find("\n")
        self.nl = "\r\n" if first_break > 0 and text[first_break - 1] == "\r" else "\n"
        self.bom = 1 if text.startswith("\ufeff") else 0
        tokens = list(yaml.scan(text))
        self.anchors = [t.start_mark.index for t in tokens
                        if isinstance(t, yaml.AnchorToken)]
        scalars = [(t.start_mark.index, t.end_mark.index) for t in tokens
                   if isinstance(t, yaml.ScalarToken)]
        self.comments = [m.start() for m in re.finditer("#", text)
                         if (m.start() == self.bom or text[m.start() - 1] in " \t\r\n")
                         and not any(s <= m.start() < e for s, e in scalars)]

    # -- lines --

    def line_start(self, i: int) -> int:
        return max(self.text.rfind("\n", 0, i) + 1, self.bom)

    def line_end(self, i: int) -> int:
        """Where the line holding position `i` ends, before its line break."""
        j = self.text.find("\n", i)
        if j == -1:
            return len(self.text)
        return j - 1 if j > 0 and self.text[j - 1] == "\r" else j

    def next_line(self, i: int) -> int:
        """The start of the line after the one holding `i` (or the end of text)."""
        j = self.text.find("\n", i)
        return len(self.text) if j == -1 else j + 1

    def column(self, i: int) -> int:
        return i - self.line_start(i)

    def comments_in(self, start: int, end: int) -> list[int]:
        return [c for c in self.comments if start <= c < end]

    def end_of(self, node, seen=None) -> int:
        """The position just after the last character that belongs to `node`.

        Not `node.end_mark` for a block collection, which runs past the comment
        lines that follow it. The maximum over the whole subtree, so an alias
        inside it (whose marks point back at its anchor) cannot pull it short.
        """
        seen = seen if seen is not None else set()
        if id(node) in seen:
            return 0
        seen.add(id(node))
        if isinstance(node, yaml.ScalarNode) or node.flow_style:
            return node.end_mark.index
        children = (node.value if isinstance(node, yaml.SequenceNode)
                    else [n for pair in node.value for n in pair])
        return max([node.start_mark.index] + [self.end_of(c, seen) for c in children])

    def document_end(self) -> tuple[int, str]:
        """Where to append, and the line break to put in front of the new lines."""
        lines = self.text.splitlines(keepends=True)
        if lines and lines[-1].strip() == "...":
            return len(self.text) - len(lines[-1]), ""
        if self.text.endswith("\n"):
            return len(self.text), ""
        return len(self.text), self.nl

    # -- finding --

    def pairs(self):
        if self.root is None:
            return []
        if not isinstance(self.root, yaml.MappingNode) or self.root.flow_style:
            raise _Refuse("the file is not a block mapping")
        return self.root.value

    @staticmethod
    def find(pairs, name):
        for k, v in pairs:
            if isinstance(k, yaml.ScalarNode) and k.value == name:
                return k, v
        return None

    def unit(self, section_pair=None) -> int:
        """Spaces per indentation level: the section's own, then the file's."""
        candidates = [section_pair] if section_pair else []
        candidates += list(self.pairs())
        for pair in candidates:
            if pair is None:
                continue
            k, v = pair
            if isinstance(v, yaml.MappingNode) and not v.flow_style and v.value:
                gap = self.column(v.value[0][0].start_mark.index) - self.column(k.start_mark.index)
                if gap > 0:
                    return gap
        return 2

    # -- rendering --

    @staticmethod
    def scalar(value: str, flow: bool = False) -> str:
        plain = value and not (flow and any(c in value for c in ",[]{}"))
        if plain:
            try:
                plain = yaml.safe_load(value) == value and "\n" not in value
            except yaml.YAMLError:
                plain = False
        return value if plain else json.dumps(value, ensure_ascii=False)

    @staticmethod
    def flow_list(values) -> str:
        return "[" + ", ".join(_Document.scalar(v, flow=True) for v in values) + "]"

    def block_value(self, edit, key_column: int, unit: int) -> list[str]:
        """The lines of `key: value` for `edit`, the key at `key_column`."""
        pad = " " * key_column
        if isinstance(edit, SetScalar):
            return [f"{pad}{edit.key}: {self.scalar(edit.value)}"]
        if not edit.values:
            return [f"{pad}{edit.key}: []"]
        dash = " " * (key_column + unit)
        return [f"{pad}{edit.key}:"] + [f"{dash}- {self.scalar(v)}" for v in edit.values]

    # -- planning one edit --

    def plan(self, edit: Edit, mapping: dict) -> tuple[list[_Replacement], set[int]]:
        pairs = self.pairs()
        if isinstance(edit, SetId):
            return self.plan_id(edit, pairs), set()
        found = self.find(pairs, edit.section)
        if found is None:
            if isinstance(edit, Remove):
                raise _Refuse(f"`{edit.section}.{edit.key}` is not written in the file")
            unit = self.unit()
            at, lead = self.document_end()
            lines = [f"{edit.section}:"] + self.block_value(edit, unit, unit)
            return [_Replacement(at, at, lead + self.nl.join(lines) + self.nl)], set()
        sk, sv = found
        if self.is_null(sv):
            if isinstance(edit, Remove):
                raise _Refuse(f"`{edit.section}.{edit.key}` is not written in the file")
            unit = self.unit()
            key_column = self.column(sk.start_mark.index) + unit
            lines = self.block_value(edit, key_column, unit)
            return self.fill_null(sk, sv, self.nl + self.nl.join(lines)), set()
        if not isinstance(sv, yaml.MappingNode):
            raise _Refuse(f"`{edit.section}` is not a mapping")
        if self.is_alias(sk, sv):
            raise _Refuse(f"`{edit.section}` is an alias")
        entry = self.find(sv.value, edit.key)
        if entry is None:
            if isinstance(edit, Remove):
                raise _Refuse(f"`{edit.section}.{edit.key}` is not written in the file")
            if sv.flow_style:
                raise _Refuse(f"`{edit.section}` is written inside braces")
            unit = self.unit(found)
            key_column = self.column(sv.value[0][0].start_mark.index)
            last_k, last_v = sv.value[-1]
            at = self.line_end(max(self.end_of(last_v), last_k.end_mark.index) - 1)
            lines = self.block_value(edit, key_column, unit)
            return [_Replacement(at, at, self.nl + self.nl.join(lines))], set()
        k, v = entry
        if self.is_alias(k, v):
            raise _Refuse(f"`{edit.section}.{edit.key}` is an alias")
        if isinstance(edit, Remove):
            if sv.flow_style:
                raise _Refuse(f"`{edit.section}` is written inside braces")
            return self.plan_remove(sk, sv, k, v)
        if self.is_null(v):
            if isinstance(edit, SetScalar):
                lead = " " if v.start_mark.index == v.end_mark.index else ""
                return self.fill_null(k, v, lead + self.scalar(edit.value), inline=True), set()
            unit = self.unit(found)
            lines = self.block_value(edit, self.column(k.start_mark.index), unit)[1:]
            if not lines:
                lead = " " if v.start_mark.index == v.end_mark.index else ""
                return self.fill_null(k, v, lead + "[]", inline=True), set()
            return self.fill_null(k, v, self.nl + self.nl.join(lines)), set()
        if isinstance(edit, SetScalar):
            if not isinstance(v, yaml.ScalarNode):
                raise _Refuse(f"`{edit.section}.{edit.key}` is not a single value")
            if v.style in ("|", ">") or v.start_mark.line != v.end_mark.line:
                raise _Refuse(f"`{edit.section}.{edit.key}` spans more than one line")
            return [_Replacement(v.start_mark.index, v.end_mark.index,
                                 self.scalar(edit.value))], set()
        if not isinstance(v, yaml.SequenceNode):
            raise _Refuse(f"`{edit.section}.{edit.key}` is not a list")
        return self.plan_list(k, v, list(edit.values))

    @staticmethod
    def is_null(node) -> bool:
        return isinstance(node, yaml.ScalarNode) and node.tag == "tag:yaml.org,2002:null"

    @staticmethod
    def is_alias(key, value) -> bool:
        return value.start_mark.index < key.end_mark.index

    def fill_null(self, key, value, text: str, inline: bool = False) -> list[_Replacement]:
        """Replace a null with `text`.

        A null written as nothing is filled at the end of the key's line, so a
        comment there stays on it (`inline` puts a scalar right after the colon
        instead, which keeps the comment after the value). An explicit `null` or
        `~` is removed and the new lines follow its line in the same way.
        """
        start, end = value.start_mark.index, value.end_mark.index
        if inline:
            return [_Replacement(start, end, text)]
        at = self.line_end(start)
        if start == end:
            return [_Replacement(at, at, text)]
        return [_Replacement(start, end, ""), _Replacement(at, at, text)]

    def plan_id(self, edit: SetId, pairs) -> list[_Replacement]:
        found = self.find(pairs, "id")
        if found is not None:
            k, v = found
            if not self.is_null(v):
                raise _Refuse("the file already has an `id`")
            if v.start_mark.index == v.end_mark.index:
                return [_Replacement(v.start_mark.index, v.end_mark.index,
                                     " " + self.scalar(edit.value))]
            return [_Replacement(v.start_mark.index, v.end_mark.index,
                                 self.scalar(edit.value))]
        line = f"id: {self.scalar(edit.value)}"
        if pairs:
            at = self.line_start(pairs[0][0].start_mark.index)
            return [_Replacement(at, at, line + self.nl)]
        at, lead = self.document_end()
        return [_Replacement(at, at, lead + line + self.nl)]

    def plan_remove(self, sk, sv, k, v) -> tuple[list[_Replacement], set[int]]:
        """Delete the key's lines, and the section's line when it is left empty.
        The comments this may take are the ones on those lines themselves."""
        start = self.line_start(k.start_mark.index)
        last = max(self.end_of(v), k.end_mark.index) - 1
        end = self.next_line(last)
        allowed = set(self.comments_in(start, self.next_line(k.start_mark.index)))
        if isinstance(v, yaml.SequenceNode) and not v.flow_style:
            for item in v.value:
                allowed |= set(self.comments_in(item.start_mark.index,
                                                self.next_line(item.start_mark.index)))
        made = [_Replacement(start, end, "")]
        if len(sv.value) == 1:
            s_start = self.line_start(sk.start_mark.index)
            s_end = self.next_line(sk.start_mark.index)
            allowed |= set(self.comments_in(s_start, s_end))
            made.insert(0, _Replacement(s_start, s_end, ""))
        return made, allowed

    def plan_list(self, k, v, new: list[str]) -> tuple[list[_Replacement], set[int]]:
        items = v.value
        if any(not isinstance(i, yaml.ScalarNode) for i in items):
            raise _Refuse("the list holds something other than plain values")
        old = [i.value for i in items]
        shared_old = [x for x in old if x in new]
        shared_new = [x for x in new if x in old]
        incremental = (len(set(old)) == len(old) and len(set(new)) == len(new)
                       and shared_old == shared_new)
        start, end = v.start_mark.index, self.end_of(v)
        if v.flow_style:
            if v.start_mark.line != v.end_mark.line:
                if self.comments_in(start, end):
                    raise _Refuse("the list spans several lines and holds comments")
                return [_Replacement(start, end, self.flow_list(new))], set()
            return [self.replace_flow(v, new)], set()
        if any(i.start_mark.line != i.end_mark.line for i in items):
            raise _Refuse("an item of the list spans more than one line")
        prefixes = [self.text[self.line_start(i.start_mark.index):i.start_mark.index]
                    for i in items]
        if any(not re.fullmatch(r"[ \t]*-[ \t]+", p) for p in prefixes):
            raise _Refuse("the list is not one item per line")
        if not new:
            colon = self.text.index(":", k.end_mark.index)
            span_end = self.line_end(items[-1].start_mark.index)
            allowed = {c for i in items
                       for c in self.comments_in(i.start_mark.index,
                                                 self.next_line(i.start_mark.index))}
            return [_Replacement(colon + 1, span_end, " []")], allowed
        dash = prefixes[0]
        if not incremental:
            first = self.line_start(items[0].start_mark.index)
            last = self.line_end(items[-1].start_mark.index)
            if self.comments_in(first, last):
                raise _Refuse("the list is being reordered and holds comments")
            body = self.nl.join(dash + self.scalar(x) for x in new)
            return [_Replacement(first, last, body)], set()
        made, allowed = [], set()
        by_value = dict(zip(old, items))
        for item in items:
            if item.value not in new:
                s = self.line_start(item.start_mark.index)
                e = self.next_line(item.start_mark.index)
                made.append(_Replacement(s, e, ""))
                allowed |= set(self.comments_in(s, e))
        survivors = [by_value[x] for x in shared_new]
        after = None
        for x in new:
            if x in by_value:
                after = by_value[x]
                continue
            line = dash + self.scalar(x)
            if after is None:
                target = survivors[0] if survivors else items[0]
                at = self.line_start(target.start_mark.index)
                made.append(_Replacement(at, at, line + self.nl))
            else:
                at = self.next_line(after.start_mark.index)
                if at == len(self.text) and not self.text.endswith("\n"):
                    made.append(_Replacement(at, at, self.nl + line))
                else:
                    made.append(_Replacement(at, at, line + self.nl))
        return made, allowed

    def replace_flow(self, v, new: list[str]) -> _Replacement:
        """A one-line flow list, keeping each surviving item's own spelling and
        the list's own spacing."""
        start, end = v.start_mark.index, v.end_mark.index
        items = v.value
        if not new:
            return _Replacement(start, end, "[]")
        spelled = {i.value: self.text[i.start_mark.index:i.end_mark.index] for i in items}
        if items:
            head = self.text[start:items[0].start_mark.index]
            tail = self.text[items[-1].end_mark.index:end]
            sep = (self.text[items[0].end_mark.index:items[1].start_mark.index]
                   if len(items) > 1 else ", ")
        else:
            head, tail, sep = "[", "]", ", "
        body = sep.join(spelled.get(x) or self.scalar(x, flow=True) for x in new)
        return _Replacement(start, end, head + body + tail)


# ── verification ────────────────────────────────────────────────────────────

def _verify(path: Path, original: str, new: str, replacements: list[_Replacement],
            allowed: set[int], target: dict, *, instruction: str) -> None:
    """Refuse unless `new` means `target` and differs from `original` only
    inside `replacements`, whose spans hold no anchor and no comment outside
    `allowed`. Checked against `new` itself, not against how it was built."""
    def refuse(why: str):
        raise ConfigEditRefused(
            f"{path}: cannot make this change without rewriting the file, which would "
            f"lose its comments and formatting ({why}); {instruction}")

    cursor_old = cursor_new = 0
    for r in sorted(replacements, key=lambda r: (r.start, r.end)):
        kept = original[cursor_old:r.start]
        if new[cursor_new:cursor_new + len(kept)] != kept:
            refuse("text outside the change would differ")
        cursor_new += len(kept) + len(r.text)
        cursor_old = r.end
    if new[cursor_new:] != original[cursor_old:]:
        refuse("text outside the change would differ")
    doc = _Document(original)
    for r in replacements:
        if any(r.start <= a < r.end for a in doc.anchors):
            refuse("the change would edit an anchor that other keys may refer to")
        if [c for c in doc.comments_in(r.start, r.end) if c not in allowed]:
            refuse("the change would delete a comment")
    try:
        result = _load(new)
    except yaml.YAMLError:
        refuse("the result would not parse")
    if result != target:
        refuse("the result would not mean what was intended")


# ── messages ────────────────────────────────────────────────────────────────

def _flow(edit) -> str:
    if isinstance(edit, SetList):
        return _Document.flow_list(edit.values)
    return _Document.scalar(edit.value, flow=True)


def _section_shape(doc: _Document, section: str) -> str:
    """'absent', 'braces', 'block' or 'other' — what the file holds for `section`."""
    try:
        found = doc.find(doc.pairs(), section)
    except _Refuse:
        return "other"
    if found is None:
        return "absent"
    value = found[1]
    if isinstance(value, yaml.MappingNode):
        return "braces" if value.flow_style else "block"
    return "block" if doc.is_null(value) else "other"


def _instruction(edit: Edit, doc: _Document, mapping: dict) -> str:
    if isinstance(edit, SetId):
        return f"edit it by hand so it has the top-level key `id: {_Document.scalar(edit.value)}`"
    shape = _section_shape(doc, edit.section)
    section = mapping.get(edit.section)
    if isinstance(edit, Remove):
        others = isinstance(section, dict) and len(section) > 1
        text = (f"edit it by hand: delete the `{edit.key}` key and its value from the "
                f"`{edit.section}` section, leaving its other keys")
        return text if others else text + f", then the now-empty `{edit.section}` line"
    line = f"{edit.key}: {_flow(edit)}"
    if shape == "braces":
        present = isinstance(section, dict) and edit.key in section
        if present:
            return (f"edit it by hand: inside the braces of `{edit.section}: {{…}}`, "
                    f"change `{edit.key}` to `{_flow(edit)}`")
        return (f"edit it by hand: inside the braces of `{edit.section}: {{…}}`, "
                f"add `, {line}`")
    if shape == "absent":
        return (f"edit it by hand: add this at the end of the file:\n"
                f"{edit.section}:\n  {line}")
    return (f"edit it by hand: under the existing `{edit.section}` section "
            f"(do not add a second one), set `{line}`")


def _message(path: Path, edit: Edit, doc: _Document, mapping: dict, why: str) -> str:
    if isinstance(edit, SetId):
        what, verb = "id", "set"
    else:
        what = f"{edit.section}.{edit.key}"
        section = mapping.get(edit.section)
        present = isinstance(section, dict) and edit.key in section
        verb = "remove" if isinstance(edit, Remove) else ("change" if present else "add")
    return (f"{path}: cannot {verb} {what} without rewriting the file, which would "
            f"lose its comments and formatting ({why}); "
            f"{_instruction(edit, doc, mapping)}")
