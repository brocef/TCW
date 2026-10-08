"""`tcw work stage` — legality, stream discipline, and writing nothing."""

import hashlib
import re
import subprocess
from pathlib import Path

import yaml

from tcw.store.fs import init


def _node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    return root


def _configure(root: Path, lifecycle: dict) -> None:
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {})["lifecycle"] = lifecycle
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def _cli(root: Path, *args: str):
    """`tcw work stage gate …` — the verb that gates, which is what most of this
    module is about. It prints no instructions; `_prompt` is what does."""
    return subprocess.run(["tcw", "work", "stage", "gate", *args],
                          cwd=str(root), capture_output=True, text=True)


def _prompt(root: Path, *args: str):
    """`tcw work stage prompt …` — no legality check, no `pre` bindings."""
    return subprocess.run(["tcw", "work", "stage", "prompt", *args],
                          cwd=str(root), capture_output=True, text=True)


def _bare(root: Path, *args: str):
    """The form removed in 2.0.0, invoked to prove it is refused."""
    return subprocess.run(["tcw", "work", "stage", *args], cwd=str(root),
                          capture_output=True, text=True)


def _manifest(folder: Path) -> dict:
    """Names, sizes, and content hashes — the adapter-level "wrote nothing"."""
    return {str(p.relative_to(folder)): (p.stat().st_size,
                                         hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(folder.rglob("*")) if p.is_file()}


# ── the legality table ───────────────────────────────────────────────────────


def _shipped_verbs() -> set[str]:
    """Every command path the parser ships, such as `work stage gate`."""
    from tcw.cli import build_parser

    def verbs(parser, prefix=()):
        found = {" ".join(prefix)} if prefix else set()
        for action in parser._actions:
            choices = getattr(action, "choices", None) or {}
            if hasattr(choices, "items"):
                for name, sub in choices.items():
                    if hasattr(sub, "_actions"):
                        found |= verbs(sub, (*prefix, name))
        return found

    return {v for v in verbs(build_parser()) if v}


def _cited_commands(text: str) -> list[str]:
    return re.findall(r"`tcw ([a-z][a-z -]*?)(?: <|`)", text)


# ── the next step printed after a transition ─────────────────────────────────


def test_an_item_whose_artifacts_vanished_mid_read_counts_as_unreadable():
    """A store answers `[]` when the item's folder disappears while it reads,
    and a present item always lists every artifact, so an empty list means the
    artifacts could not be read. Reading it as "none written" would send `start`
    to `spec` and warn that spec and plan are missing; unreadable falls back to
    `implement` and warns about nothing."""
    from tcw.work.cli import _present_artifacts

    class VanishedStore:
        def artifacts(self, slug):
            return []

    assert _present_artifacts(VanishedStore(), "gone") is None


# ── streams ──────────────────────────────────────────────────────────────────


# ── writing nothing ──────────────────────────────────────────────────────────


# ── --no-exec ────────────────────────────────────────────────────────────────


# ── the built-in floor, end to end ───────────────────────────────────────────


# ── the reading verb ─────────────────────────────────────────────────────────


def test_the_removed_form_advises_inbox_without_a_reference(tmp_path):
    """`inbox` runs before an item exists and both verbs refuse a reference for
    it. The migration message handed every stage the same `<slug>` placeholder,
    so someone on the old spelling was advised a command that is itself refused
    — two wrong turns to reach the one that works.
    """
    root = _node(tmp_path)
    r = _bare(root, "inbox")
    assert r.returncode == 2
    assert "gate inbox`" in r.stderr and "prompt inbox`" in r.stderr, r.stderr
    assert "<slug>" not in r.stderr, r.stderr

    # Every other stage still gets one, since they do take a reference.
    other = _bare(root, "spec")
    assert "gate spec <slug>`" in other.stderr, other.stderr


def test_gate_inbox_runs_the_stages_pre_bindings(tmp_path):
    """`gate inbox` skips the *legality* check because there is no status to
    check, not the `pre` checks. Nothing else asserts this, and an inbox branch
    written as an early return would silently drop them."""
    root = _node(tmp_path)
    sentinel = (tmp_path / "INBOX-CHECK").resolve()
    _configure(root, {"stages": {"inbox": {
        "pre": [{"command": f"touch {sentinel}"}],
        "prompt": [{"blob": "triage it"}]}}})

    r = _cli(root, "inbox")
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""
    assert sentinel.exists()
    assert "triage it" in _prompt(root, "inbox").stdout


def test_prompt_reports_its_own_errors_on_stderr_alone(tmp_path):
    """Every failure originating in the verb's own handler: exit 1, nothing on
    stdout, the reason on stderr."""
    root = _node(tmp_path)
    for args, expected in (
            (("speck",), "unknown stage 'speck'"),
            (("complete",), "unknown stage 'complete'"),
            (("spec", "no-such-item"), "no such work item"),
    ):
        r = _prompt(root, *args)
        assert r.returncode == 1, args
        assert r.stdout == "", args
        assert expected in r.stderr, (args, r.stderr)


def test_an_unknown_stage_names_the_verb_it_was_reached_through(tmp_path):
    """The two verbs share `_stage_step`, so the message has to carry which one
    the reader typed or it names a command they did not run."""
    root = _node(tmp_path)
    assert "tcw work stage prompt: unknown stage" in _prompt(root, "speck").stderr
    assert "tcw work stage gate: unknown stage" in _cli(root, "speck", "x").stderr


# ── the form removed in 2.0.0 ────────────────────────────────────────────────


# ── the bookends ─────────────────────────────────────────────────────────────


