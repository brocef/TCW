"""Plugin manifests parse, and the version is in lockstep across all 5 files.

The single automated guard against *authoring* drift (runtime cache-vs-installed
drift is the setup skill's job, not this test's).
"""
import json
import os
import subprocess
import tomllib

import yaml
from pathlib import Path

import pytest

import tcw

REPO = Path(__file__).resolve().parent.parent

CLAUDE_PLUGIN = REPO / ".claude-plugin" / "plugin.json"
CLAUDE_MARKET = REPO / ".claude-plugin" / "marketplace.json"
CODEX_PLUGIN = REPO / ".codex-plugin" / "plugin.json"
AGENTS_MARKET = REPO / ".agents" / "plugins" / "marketplace.json"

ALL_MANIFESTS = [CLAUDE_PLUGIN, CLAUDE_MARKET, CODEX_PLUGIN, AGENTS_MARKET]


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_all_manifests_exist_and_parse():
    for m in ALL_MANIFESTS:
        assert m.is_file(), f"missing manifest: {m}"
        _load(m)  # raises on malformed JSON


def test_five_version_fields_agree():
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    versions = {
        "pyproject.toml": pyproject["project"]["version"],
        "tcw/__init__.py": tcw.__version__,
        ".claude-plugin/plugin.json": _load(CLAUDE_PLUGIN)["version"],
        ".claude-plugin/marketplace.json": _load(CLAUDE_MARKET)["plugins"][0]["version"],
        ".codex-plugin/plugin.json": _load(CODEX_PLUGIN)["version"],
    }
    assert len(set(versions.values())) == 1, f"version drift: {versions}"


def test_agents_marketplace_carries_no_version():
    """Deliberately version-free (per spec) — keep it that way so it never
    becomes a 6th drift source."""
    data = _load(AGENTS_MARKET)
    assert "version" not in data
    assert all("version" not in p for p in data.get("plugins", []))


def test_claude_agents_key_is_md_files_not_a_directory():
    """Claude's schema accepts only `.md` file paths for `agents` (unlike
    `skills`/`commands`, which take directories). A directory there fails
    install with "agents: Invalid input"; omitting the key auto-loads agents/."""
    agents = _load(CLAUDE_PLUGIN).get("agents")
    paths = [agents] if isinstance(agents, str) else (agents or [])
    assert all(p.endswith(".md") for p in paths), f"agents must be .md files: {agents}"


NUMBER_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
    13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen",
    17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
}


def _names_missing_from(blob: str, names) -> list[str]:
    """Which of `names` the description does not mention, matching each only as
    a **backticked name** rather than as a bare substring or bare word.

    The distinction is load-bearing. `work` is a substring of `work-stage` and
    `work-create`, and without the plugin-id prefix several names are also
    ordinary words: "work" sits inside "framework" and "work item", and
    "taxonomy" and "capabilities" in the manifest's keywords. Any looser match
    finds the name somewhere else and reports it present when the enumeration
    never names it, so the guard for that skill would be dead — its name could
    be deleted from the description with the suite green.
    """
    return [n for n in names if f"`{n}`" not in blob]


def test_the_codex_description_counts_the_skills_it_ships():
    """The Codex manifest describes the plugin in prose and enumerates every
    skill by name. Prose does not check itself: it said "eight skills" and named
    eight while nine shipped, so the newest one was undiscoverable to anyone
    reading the description — which is the whole audience for it.

    Both halves are checked, because either can rot alone: a skill added without
    touching the sentence leaves the count wrong, and a count bumped without
    naming the skill leaves the list short.
    """
    import json
    desc = json.loads((REPO / ".codex-plugin" / "plugin.json").read_text())
    blob = desc["interface"]["longDescription"]
    names = sorted(p.parent.name for p in (REPO / "skills").glob("*/SKILL.md"))
    word = NUMBER_WORDS[len(names)]
    assert f"{word} skills" in blob, (
        f"the Codex description does not say '{word} skills' for the "
        f"{len(names)} that ship: {', '.join(names)}")
    missing = _names_missing_from(blob, names)
    assert not missing, f"shipped but unnamed in the description: {missing}"


def test_a_shared_name_or_plain_word_cannot_stand_in_for_a_skill_name():
    """The guard above, guarded. `work` is a prefix of `work-stage` and an
    ordinary word, so under a looser match dropping the `work` skill from the
    description was invisible: its name was still found, inside a longer name
    or in the surrounding prose.

    Asserting on the real description would not catch a revert — it names every
    skill, so every matcher agrees on it. This asserts the discrimination
    directly, on a blob that names only the longer skill and uses the word.
    """
    blob = "a framework for tracking work; among them `work-stage`"
    assert _names_missing_from(blob, ["work-stage"]) == []
    assert _names_missing_from(blob, ["work"]) == ["work"]


SHIPPED_SKILLS = sorted((REPO / "skills").glob("*/SKILL.md"))
SHIPPED_AGENTS = sorted((REPO / "agents").glob("*.md"))


def _frontmatter(path: Path) -> dict:
    """The `---`-delimited YAML frontmatter of a SKILL.md or an agent file.

    Parsed as YAML, not scanned line by line. A plain scalar containing ": "
    is a YAML error, and every one of the five per-stage skills shipped with
    one on first write — a `when_to_use` reading "runs no gate: `tcw work
    stage gate` is what refuses". A line-based scan sees the keys and passes;
    Codex, which actually parses this, refuses to load the skill.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0] == "---", f"{path} is missing YAML frontmatter"
    end = lines.index("---", 1)
    front = yaml.safe_load("\n".join(lines[1:end]))
    assert isinstance(front, dict), f"{path} frontmatter is not a YAML mapping"
    return front


@pytest.mark.parametrize("skill", SHIPPED_SKILLS, ids=lambda p: p.parent.name)
def test_every_skill_has_name_and_description_frontmatter(skill):
    """Codex refuses to load a skill whose SKILL.md lacks `---` frontmatter with
    a name and description; Claude silently tolerates it, so only a test catches
    the drop."""
    assert {"name", "description"} <= set(_frontmatter(skill)), (
        f"{skill} frontmatter lacks name/description")


@pytest.mark.parametrize("skill", SHIPPED_SKILLS, ids=lambda p: p.parent.name)
def test_skill_frontmatter_name_matches_its_directory(skill):
    """A skill's declared `name` is the directory it sits in.

    The test above checks `name` is *present*, never that it agrees with the
    path — which is exactly what lets a directory rename land half-done. Move
    `skills/<old>/` to `skills/<new>/` and leave `name: <old>` behind and the
    whole suite stays green, while the two harnesses disagree about what the
    skill is called.
    """
    front = _frontmatter(skill)
    assert front["name"] == skill.parent.name, (
        f"{skill} declares name={front['name']!r} but sits in "
        f"{skill.parent.name!r} — a rename left the frontmatter behind")


def test_no_shipped_name_repeats_the_plugin_id():
    """A skill or agent name does not repeat the namespace that already qualifies
    it. Claude invokes a skill as `/<plugin>:<skill>` and Codex as
    `$<plugin>:<skill>`, so a `tcw-` prefix on the skill's own name produced
    `/tcw:tcw-work` — four characters and a stutter distinguishing nothing.

    Stated as the general rule, read from the manifest rather than hardcoded, so
    it keeps holding if the plugin is ever renamed and it refuses the prefix
    creeping back one skill at a time.
    """
    plugin_id = _load(CLAUDE_PLUGIN)["name"]
    stutter = f"{plugin_id}-"
    offenders = sorted(
        [s.parent.name for s in SHIPPED_SKILLS if s.parent.name.startswith(stutter)]
        + [a.stem for a in SHIPPED_AGENTS if a.stem.startswith(stutter)])
    assert not offenders, (
        f"these repeat the plugin id {plugin_id!r}, which the namespace already "
        f"supplies: {offenders}")


@pytest.mark.parametrize("agent", SHIPPED_AGENTS, ids=lambda p: p.stem)
def test_agent_frontmatter_name_matches_its_file(agent):
    """The same agreement, for the subagents. `agents/` carries no manifest —
    Claude auto-loads the directory — so the filename and the declared name are
    the only two statements of an agent's identity, and nothing else compares
    them."""
    front = _frontmatter(agent)
    assert front["name"] == agent.stem, (
        f"{agent} declares name={front['name']!r} but is filed as "
        f"{agent.stem!r} — a rename left the frontmatter behind")


def test_hooks_manifest_wires_one_executable_session_start_script():
    """The SessionStart install hook. Claude loads `hooks/hooks.json` by
    convention and rejects the plugin if the manifest names it again; nothing
    outside this test catches that, nor the script losing its executable bit —
    a hook that cannot run fails silently."""
    assert "hooks" not in _load(CLAUDE_PLUGIN), (
        "hooks/hooks.json is loaded by convention; naming it in the manifest is a "
        "duplicate-hooks load error"
    )
    hooks_file = REPO / "hooks" / "hooks.json"
    assert hooks_file.is_file(), f"missing hooks file: {hooks_file}"
    entries = _load(hooks_file)["hooks"]["SessionStart"]
    commands = [h["command"] for e in entries for h in e["hooks"]]
    assert len(commands) == 1, f"expected exactly one SessionStart hook: {commands}"
    script = REPO / commands[0].replace('"${CLAUDE_PLUGIN_ROOT}"/', "")
    assert script.is_file(), f"hook command is not a file: {script}"
    assert os.access(script, os.X_OK), f"hook command is not executable: {script}"


def test_claude_marketplace_carries_publishable_metadata():
    """The server-side marketplace validator behind claude.ai and the desktop
    app is stricter than `claude plugin validate`, and reports every rejection
    as one generic "sync failed" string. Marketplaces that sync carry these
    fields; the ones that failed did not."""
    data = _load(CLAUDE_MARKET)
    assert data.get("description"), "marketplace needs a top-level description"
    owner = data.get("owner", {})
    assert owner.get("name") and owner.get("email"), f"owner needs name + email: {owner}"
    entry = data["plugins"][0]
    assert entry.get("author", {}).get("name"), f"plugin entry needs an author: {entry}"


def test_claude_and_codex_plugin_manifests_agree():
    """Two manifests describing one artifact. Version lockstep is covered above;
    these are the fields that silently drift apart instead."""
    claude, codex = _load(CLAUDE_PLUGIN), _load(CODEX_PLUGIN)
    for field in ("homepage", "repository", "license"):
        assert claude.get(field), f".claude-plugin/plugin.json lacks {field}"
        assert claude[field] == codex.get(field), (
            f"{field} disagrees: claude={claude.get(field)!r} codex={codex.get(field)!r}"
        )


def test_agents_marketplace_source_path_resolves():
    """Codex addresses the plugin by a path relative to the marketplace root.
    Layout-agnostic on purpose: it held for the old `./plugins/tcw` symlink and
    holds for the root-relative `.` that replaced it."""
    path = _load(AGENTS_MARKET)["plugins"][0]["source"]["path"]
    assert (REPO / path).is_dir(), f"agents marketplace source path is not a directory: {path}"


def test_no_tracked_symlink_resolves_to_its_own_ancestor():
    """`plugins/tcw -> ..` used to make the plugin root contain itself. Every
    tree walker that follows symlinks recurses forever on that, and a
    server-side one cannot be configured around the way pytest and setuptools
    were. Asserting the class, not the instance, so it cannot come back under
    another name."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-s", "-z"],
        capture_output=True, text=True, check=True,
    ).stdout
    links = [
        REPO / entry.split("\t", 1)[1]
        for entry in out.split("\0")
        if entry and entry.split(" ", 1)[0] == "120000"
    ]
    for link in links:
        target = link.resolve()
        assert target not in link.parents, (
            f"{link.relative_to(REPO)} resolves to its own ancestor {target} — "
            "a self-containing tree that breaks any walker following symlinks"
        )
