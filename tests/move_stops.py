"""Stop a move at every write in turn, and show that running it again
finishes it (TCW-114 Design 5.8; plan choice 10).

`every_stop(make, command)` first runs `command` once on a fresh fixture
with every write counted, and checks that each path and ticket that changed
is explained by a counted write. Then, for each write `k`, it builds a fresh
fixture, runs the command with write `k` failing, checks the stop, runs the
command again healthy, and compares the result with the clean run's, byte
for byte, tickets included.

What it counts: each `(path, content)` pair of `_atomic_write_all`, and
`Path.write_text`, `Path.write_bytes`, `os.replace`, `Path.replace`,
`os.rename`, `Path.rename`, `shutil.move`, `os.mkdir`, `Path.mkdir`,
`os.rmdir`, `Path.rmdir`, `os.remove`, `Path.unlink`, and each fake Jira
`PUT /issue/<key>`. Counting pauses inside a counted call, so the `os`
functions a `Path` method calls are not counted again.
"""

from __future__ import annotations

import errno
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import tcw.store.fs as store_fs
import tcw.work.fs_backend as fs_backend


@dataclass
class Fixture:
    """A fresh fixture: its folder (everything under it is compared) and
    the fake Jira serving it, or None."""
    root: Path
    fake: object = None


@dataclass
class Counter:
    fail_at: int | None = None
    writes: list[tuple[str, tuple[Path, ...]]] = field(default_factory=list)
    depth: int = 0

    def count(self, kind: str, *targets) -> None:
        """Count one write; raise when it is the one to fail."""
        self.writes.append((kind, tuple(Path(t) if not isinstance(t, str) or
                                        not t.startswith("ticket:") else t
                                        for t in targets)))
        if self.fail_at is not None and len(self.writes) == self.fail_at:
            raise OSError(errno.EIO, f"write {self.fail_at} made to fail ({kind})")


def _install(monkeypatch, counter: Counter, fake) -> None:
    def counted(kind: str, real: Callable, targets: Callable):
        def wrapper(*args, **kwargs):
            if counter.depth:
                return real(*args, **kwargs)
            counter.count(kind, *targets(*args, **kwargs))
            counter.depth += 1
            try:
                return real(*args, **kwargs)
            finally:
                counter.depth -= 1
        return wrapper

    real_atomic = store_fs._atomic_write_all

    def atomic(pairs):
        if counter.depth:
            return real_atomic(pairs)
        for path, content in pairs:
            counter.count("_atomic_write_all", path)
            counter.depth += 1
            try:
                real_atomic([(path, content)])
            finally:
                counter.depth -= 1
    monkeypatch.setattr(store_fs, "_atomic_write_all", atomic)
    monkeypatch.setattr(fs_backend, "_atomic_write_all", atomic)
    for name in ("write_text", "write_bytes", "mkdir", "rmdir", "unlink"):
        monkeypatch.setattr(Path, name, counted(f"Path.{name}", getattr(Path, name),
                                                lambda self, *a, **k: (self,)))
    for name in ("rename", "replace"):
        monkeypatch.setattr(Path, name, counted(f"Path.{name}", getattr(Path, name),
                                                lambda self, target, *a: (self, target)))
    for name in ("rename", "replace"):
        monkeypatch.setattr(os, name, counted(f"os.{name}", getattr(os, name),
                                              lambda a, b, *x, **k: (a, b)))
    for name in ("mkdir", "rmdir", "remove"):
        monkeypatch.setattr(os, name, counted(f"os.{name}", getattr(os, name),
                                              lambda a, *x, **k: (a,)))
    monkeypatch.setattr(shutil, "move", counted("shutil.move", shutil.move,
                                                lambda a, b, *x, **k: (a, b)))
    if fake is not None:
        real_answer = fake.answer

        def answer(client, method, path, body):
            if method == "PUT" and "/issue/" in path:
                key = path.split("?")[0].rsplit("/", 1)[1]
                try:
                    counter.count("PUT", f"ticket:{key}")
                except OSError as error:
                    from tcw.work.jira import client as jira
                    raise jira.TrackerUnavailable(str(error)) from None
            return real_answer(client, method, path, body)
        monkeypatch.setattr(fake, "answer", answer)


def _snapshot(fixture: Fixture) -> tuple[dict, dict]:
    root = fixture.root
    files = {}
    for path in sorted(root.rglob("*")):
        if ".git" in path.relative_to(root).parts:
            continue
        rel = str(path.relative_to(root))
        files[rel] = path.read_bytes() if path.is_file() else "<folder>"
    tickets = {}
    if fixture.fake is not None:
        for key, ticket in fixture.fake.tickets.items():
            tickets[key] = (dict(ticket.custom), ticket.summary, ticket.status,
                            ticket.parent)
    return files, tickets


def _unexplained(before, after, writes, root: Path) -> list[str]:
    files0, tickets0 = before
    files1, tickets1 = after
    changed = {p for p in set(files0) | set(files1) if files0.get(p) != files1.get(p)}
    targets: set[str] = set()
    renamed: list[tuple[str, str]] = []
    for kind, paths in writes:
        rel = []
        for p in paths:
            if isinstance(p, str):
                targets.add(p)
                continue
            try:
                rel.append(str(Path(p).resolve().relative_to(root.resolve())))
            except ValueError:
                continue
        targets.update(rel)
        if kind in ("os.rename", "Path.rename", "shutil.move") and len(rel) == 2:
            renamed.append((rel[0], rel[1]))
    out = []
    for path in sorted(changed):
        if path in targets:
            continue
        if any(path.startswith(a + "/") or path.startswith(b + "/") for a, b in renamed):
            continue
        out.append(path)
    for key in set(tickets0) | set(tickets1):
        if tickets0.get(key) != tickets1.get(key) and f"ticket:{key}" not in targets:
            out.append(f"ticket {key}")
    return out


#: What a move's stopped run says (TCW-114 Design 5.8).
MOVE_STOPPED = ("run the same command again", "the folder is still at")


def every_stop(monkeypatch_factory, make: Callable[[], Fixture],
               command: Callable[[Fixture], object], *,
               stopped_says: tuple[str, ...] = MOVE_STOPPED) -> int:
    """Run the clean run, then a stop at each write in turn and its re-run;
    returns how many writes the clean run made. `monkeypatch_factory()`
    gives a fresh `MonkeyPatch`, undone after each run. `command` is any
    callable that performs one run on a fixture and returns its `code`,
    `out` and `err`; a stopped run's `err` must hold each of `stopped_says`
    (a move's two lines by default; `tcw migrate` gives its own)."""
    clean = make()
    before = _snapshot(clean)
    counter = Counter()
    with monkeypatch_factory() as patch:
        _install(patch, counter, clean.fake)
        result = command(clean)
    assert result.code == 0, result.err
    expected = _snapshot(clean)
    unexplained = _unexplained(before, expected, counter.writes, clean.root)
    assert not unexplained, f"changed with no counted write: {unexplained}"
    old_values = {}
    if clean.fake is not None:
        old_values = {k: v[0] for k, v in before[1].items()}
    total = len(counter.writes)
    assert total > 0
    for k in range(1, total + 1):
        fixture = make()
        failing = Counter(fail_at=k)
        with monkeypatch_factory() as patch:
            _install(patch, failing, fixture.fake)
            stopped = command(fixture)
        kind = failing.writes[k - 1][0]
        if stopped.code == 0:
            # Only the tidy step may fail and still succeed, with a warning.
            assert kind in ("os.rmdir", "Path.rmdir"), (k, kind, stopped.err)
            assert "warning:" in stopped.err, (k, stopped.err)
        else:
            assert stopped.out == "", (k, kind, stopped.out)
            for words in stopped_says:
                assert words in stopped.err, (k, kind, stopped.err)
            again = command(fixture)
            assert again.code == 0, (k, kind, again.err)
        got = _snapshot(fixture)
        if stopped.code == 0:
            # The tidy step's empty folder is left; everything else matches.
            files = {p: v for p, v in got[0].items()
                     if not (v == "<folder>" and p not in expected[0])}
            assert (files, got[1]) == expected, (k, kind)
        else:
            assert got == expected, (k, kind)
        if fixture.fake is not None:
            # No ticket is ever set back to an old value.
            for m, p, b in fixture.fake.log:
                if m == "PUT" and isinstance(b, dict):
                    key = p.split("?")[0].rsplit("/", 1)[1]
                    for field_id, value in (b.get("fields") or {}).items():
                        old = old_values.get(key, {}).get(field_id)
                        new = expected[1].get(key, ({},))[0].get(field_id)
                        assert value == new or old == new, (k, key, value)
    return total
