"""A parser and evaluator for exactly the JQL shapes `tcw/work/jira/jql.py`
emits, for the fake Jira (TCW-71 Design 15.1).

Supported: `field = "v"`, `field IN ("a", ...)`, `field NOT IN (...)`,
`field IS EMPTY`, `field IS NOT EMPTY`, `AND`, `OR`, parentheses, and a final
`ORDER BY created ASC|DESC`. Fields are bare names or `cf[<digits>]`. Anything
else raises `JqlError`, so a new clause in `jql.py` cannot pass silently.

`IN` on `labels` matches a ticket carrying any of the listed labels, as Jira
does; labels compare exactly unless `ignore_label_case` is set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

TOKEN = re.compile(r"""
    \s*(?:
      (?P<string>"(?:[^"\\]|\\.)*")
    | (?P<cf>cf\[\d+\])
    | (?P<word>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<punct>[(),=])
    )""", re.VERBOSE)

Getter = Callable[[str], Any]      # field name or "customfield_<id>" -> value


class JqlError(ValueError):
    pass


@dataclass
class Query:
    predicate: Callable[[Getter, bool], bool]
    order: tuple[str, str] | None
    statuses: tuple[str, ...] = ()       # every value a status clause names


def _tokens(jql: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    jql = jql.rstrip()
    while pos < len(jql):
        match = TOKEN.match(jql, pos)
        if not match or match.end() == pos:
            raise JqlError(f"cannot read JQL at {jql[pos:]!r}")
        kind = match.lastgroup
        text = match.group(kind)
        if kind == "string":
            text = re.sub(r"\\(.)", r"\1", text[1:-1])
        elif kind == "cf":
            text = "customfield_" + text[3:-1]
        out.append((kind, text))
        pos = match.end()
    return out


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0
        self.statuses: list[str] = []

    def peek(self, offset=0):
        j = self.i + offset
        return self.tokens[j] if j < len(self.tokens) else (None, None)

    def word(self, *expected) -> bool:
        kind, text = self.peek()
        return kind == "word" and text.upper() in expected

    def take(self, kind=None, word=None):
        got = self.peek()
        if kind and got[0] != kind or word and (got[0] != "word"
                                                or got[1].upper() != word):
            raise JqlError(f"expected {word or kind}, got {got[1]!r}")
        self.i += 1
        return got[1]

    def expression(self):
        left = self.conjunction()
        while self.word("OR"):
            self.take(word="OR")
            right = self.conjunction()
            left = (lambda a, b: lambda get, ic: a(get, ic) or b(get, ic))(left, right)
        return left

    def conjunction(self):
        left = self.term()
        while self.word("AND"):
            self.take(word="AND")
            right = self.term()
            left = (lambda a, b: lambda get, ic: a(get, ic) and b(get, ic))(left, right)
        return left

    def term(self):
        if self.peek() == ("punct", "("):
            self.take("punct")
            inner = self.expression()
            if self.take("punct") != ")":
                raise JqlError("expected )")
            return inner
        return self.clause()

    def clause(self):
        kind, name = self.peek()
        if kind not in ("word", "cf"):
            raise JqlError(f"expected a field, got {name!r}")
        self.i += 1
        if self.peek() == ("punct", "="):
            self.take("punct")
            value = self.take("string")
            self._named(name, [value])
            return lambda get, ic: _matches(name, get(name), [value], ic)
        if self.word("IN"):
            self.take(word="IN")
            values = self.values()
            self._named(name, values)
            return lambda get, ic: _matches(name, get(name), values, ic)
        if self.word("NOT") and self.peek(1)[1] and self.peek(1)[1].upper() == "IN":
            self.take(word="NOT")
            self.take(word="IN")
            values = self.values()
            self._named(name, values)
            return lambda get, ic: not _matches(name, get(name), values, ic)
        if self.word("IS"):
            self.take(word="IS")
            negate = self.word("NOT")
            if negate:
                self.take(word="NOT")
            self.take(word="EMPTY")
            return lambda get, ic: _empty(get(name)) != negate
        raise JqlError(f"unsupported operator after {name!r}: {self.peek()[1]!r}")

    def _named(self, name: str, values: list[str]) -> None:
        if name.lower() == "status":
            self.statuses += values

    def values(self) -> list[str]:
        if self.take("punct") != "(":
            raise JqlError("expected (")
        out = [self.take("string")]
        while self.peek() == ("punct", ","):
            self.take("punct")
            out.append(self.take("string"))
        if self.take("punct") != ")":
            raise JqlError("expected )")
        return out


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == ()


def _matches(name: str, value: Any, wanted: list[str], ignore_case: bool) -> bool:
    if isinstance(value, (list, tuple)):
        fold = (lambda s: s.lower()) if ignore_case and name == "labels" else (lambda s: s)
        have = {fold(str(v)) for v in value}
        return any(fold(w) in have for w in wanted)
    return value is not None and str(value) in wanted


def parse(jql: str) -> Query:
    tokens = _tokens(jql)
    order = None
    for index in range(len(tokens) - 1):
        if tokens[index] == ("word", "ORDER") and tokens[index + 1][1].upper() == "BY":
            tail = tokens[index:]
            if len(tail) != 4 or tail[2] != ("word", "created") \
                    or tail[3][1].upper() not in ("ASC", "DESC"):
                raise JqlError(f"unsupported ORDER BY: {tail}")
            order = ("created", tail[3][1].upper())
            tokens = tokens[:index]
            break
    parser = _Parser(tokens)
    predicate = parser.expression()
    if parser.i != len(tokens):
        raise JqlError(f"unexpected {tokens[parser.i][1]!r}")
    return Query(predicate, order, tuple(parser.statuses))


def select(jql: str, tickets: list, getter: Callable[[Any, str], Any], *,
           ignore_label_case: bool = False, statuses=None) -> list:
    """The tickets the query selects, in its order. Like Jira's `search/jql`
    (the TCW-71 live check), a status value the site does not have matches
    nothing and is not an error; `statuses` is kept for callers that pass it."""
    query = parse(jql)
    found = [t for t in tickets
             if query.predicate(lambda name, t=t: getter(t, name), ignore_label_case)]
    if query.order:
        found.sort(key=lambda t: getter(t, "created") or "",
                   reverse=query.order[1] == "DESC")
    return found
