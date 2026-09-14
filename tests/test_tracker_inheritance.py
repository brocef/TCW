"""`work.tracker` inherited from parent nodes, key by key.

The properties this file holds, beyond the merge itself:

- **Opt-in.** Only a node whose own block is a non-empty mapping inherits. A node
  that writes nothing has no tracker and no problems, whatever its parents hold.
- **A token never goes to a site its node did not choose.** `credentials` must
  come from the same file as `base-url`, or a nearer one.
- **A problem names the file that caused it**, matched on the exact key path, and
  a key nobody set is blamed on the node being checked.
"""

from __future__ import annotations

import copy

import pytest

from tcw.store.base import (
    attribute_tracker_problems,
    merge_tracker_blocks,
    parse_tracker_config,
    tracker_credentials_problem,
)

COMPLETE = {
    "provider": "jira-cloud",
    "base-url": "https://root.example.invalid",
    "candidate-query": "project = EX",
    "credentials": {"email-env": "ROOT_EMAIL", "token-env": "ROOT_TOKEN"},
    "transitions": {"claim": "Start"},
}

CREDENTIALS_MESSAGE_START = "work.tracker.credentials: inherited from a parent node"


# ── the pure merge ───────────────────────────────────────────────────────────


@pytest.fixture()
def empty_cwd(tmp_path, monkeypatch):
    """The pure functions read no file, so they run from a directory holding none."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_nested_mappings_merge_key_by_key_and_the_record_names_each_source(empty_cwd):
    """C18, with criterion 4's mappings."""
    root = {**COMPLETE, "credentials": {"email-env": "A", "token-env": "B"}}
    pkg = {"candidate-query": "component = api", "credentials": {"token-env": "C"}}
    merged, record, whole = merge_tracker_blocks([("pkg", pkg), ("root", root)])
    assert whole is None
    assert merged["credentials"] == {"email-env": "A", "token-env": "C"}
    assert merged["candidate-query"] == "component = api"
    assert merged["base-url"] == COMPLETE["base-url"]
    assert record[("credentials", "token-env")] == "pkg"
    assert record[("credentials", "email-env")] == "root"


def test_the_nearest_block_wins_a_scalar(empty_cwd):
    merged, record, _ = merge_tracker_blocks(
        [("pkg", {"base-url": "https://pkg"}), ("repo", {"base-url": "https://repo"}),
         ("root", COMPLETE)])
    assert merged["base-url"] == "https://pkg"
    assert record[("base-url",)] == "pkg"


def test_a_nearer_null_lets_the_farther_value_show_through(empty_cwd):
    """C6 at merge level. The record keeps naming the file that supplied the value."""
    merged, record, _ = merge_tracker_blocks(
        [("pkg", {"timeout-seconds": None}), ("root", {**COMPLETE, "timeout-seconds": 30})])
    assert merged["timeout-seconds"] == 30
    assert record[("timeout-seconds",)] == "root"


def test_a_null_with_nothing_farther_is_kept_for_the_parser_to_report(empty_cwd):
    """C7 at merge level."""
    merged, record, _ = merge_tracker_blocks([("pkg", {**COMPLETE, "timeout-seconds": None})])
    assert "timeout-seconds" in merged and merged["timeout-seconds"] is None
    assert record[("timeout-seconds",)] == "pkg"


def test_all_null_credentials_are_recorded_against_the_file_that_supplied_them(empty_cwd):
    """The merge half of C23. Recording the nulls' file here would silence the
    credentials rule and send root's token to pkg's site."""
    pkg = {"base-url": "https://pkg", "credentials": {"email-env": None, "token-env": None}}
    merged, record, _ = merge_tracker_blocks([("pkg", pkg), ("root", COMPLETE)])
    assert merged["credentials"] == COMPLETE["credentials"]
    assert record[("credentials", "email-env")] == "root"
    assert record[("credentials", "token-env")] == "root"


def test_a_null_credentials_mapping_is_recorded_against_the_farther_file(empty_cwd):
    merged, record, _ = merge_tracker_blocks(
        [("pkg", {"credentials": None}), ("root", COMPLETE)])
    assert merged["credentials"] == COMPLETE["credentials"]
    assert record[("credentials", "token-env")] == "root"


def test_a_list_replaces_rather_than_concatenating(empty_cwd):
    merged, _, _ = merge_tracker_blocks([("pkg", {"extra": [3]}), ("root", {"extra": [1, 2]})])
    assert merged["extra"] == [3]


def test_a_value_replacing_a_mapping_drops_the_mappings_record_entries(empty_cwd):
    merged, record, _ = merge_tracker_blocks([("pkg", {"credentials": "x"}), ("root", COMPLETE)])
    assert merged["credentials"] == "x"
    assert record[("credentials",)] == "pkg"
    assert not [p for p in record if len(p) > 1 and p[0] == "credentials"]


def test_a_mapping_replacing_a_value_records_its_own_keys(empty_cwd):
    merged, record, _ = merge_tracker_blocks(
        [("pkg", {"credentials": {"token-env": "C"}}), ("root", {"credentials": "x"})])
    assert merged["credentials"] == {"token-env": "C"}
    assert record[("credentials", "token-env")] == "pkg"


def test_an_ancestor_that_is_not_a_mapping_stops_the_merge_and_owns_the_problem(empty_cwd):
    merged, record, whole = merge_tracker_blocks([("pkg", COMPLETE), ("root", "off")])
    assert merged == "off"
    assert record == {}
    assert whole == "root"


def test_empty_ancestors_contribute_nothing(empty_cwd):
    merged, _, whole = merge_tracker_blocks([("pkg", COMPLETE), ("repo", None), ("root", {})])
    assert merged == COMPLETE
    assert whole is None


def test_the_merge_does_not_change_its_inputs(empty_cwd):
    root = copy.deepcopy(COMPLETE)
    pkg = {"credentials": {"token-env": "C", "email-env": None}, "timeout-seconds": None}
    before = copy.deepcopy((pkg, root))
    merged, _, _ = merge_tracker_blocks([("pkg", pkg), ("root", root)])
    merged["credentials"]["email-env"] = "changed"
    assert (pkg, root) == before


# ── credentials stay with their site ─────────────────────────────────────────


def _credentials_problem(blocks):
    _merged, record, _ = merge_tracker_blocks(blocks)
    return tracker_credentials_problem(record, [label for label, _ in blocks])


def test_a_nearer_base_url_with_inherited_credentials_is_a_problem(empty_cwd):
    problem = _credentials_problem([("pkg", {"base-url": "https://pkg"}), ("root", COMPLETE)])
    assert problem is not None and problem.startswith(CREDENTIALS_MESSAGE_START)
    assert "in pkg;" in problem


def test_nearer_credentials_on_the_same_site_are_allowed(empty_cwd):
    assert _credentials_problem(
        [("pkg", {"credentials": {"email-env": "E", "token-env": "T"}}), ("root", COMPLETE)]) is None


def test_base_url_and_credentials_from_one_file_are_allowed(empty_cwd):
    assert _credentials_problem([("pkg", {"candidate-query": "q"}), ("root", COMPLETE)]) is None


def test_partly_inherited_credentials_count_by_their_farthest_key(empty_cwd):
    problem = _credentials_problem(
        [("pkg", {"base-url": "https://pkg", "credentials": {"token-env": "T"}}),
         ("root", COMPLETE)])
    assert problem is not None and problem.startswith(CREDENTIALS_MESSAGE_START)


def test_all_null_credentials_beside_a_nearer_base_url_are_a_problem(empty_cwd):
    """C23 at merge level."""
    problem = _credentials_problem(
        [("pkg", {"base-url": "https://pkg",
                  "credentials": {"email-env": None, "token-env": None}}),
         ("root", COMPLETE)])
    assert problem is not None and problem.startswith(CREDENTIALS_MESSAGE_START)


# ── naming the file a problem came from ──────────────────────────────────────


def _attributed(blocks):
    merged, record, whole = merge_tracker_blocks(blocks)
    _config, problems = parse_tracker_config(merged)
    return attribute_tracker_problems(problems, record, blocks[0][0], whole)


def test_an_unknown_top_level_key_names_the_file_that_wrote_it(empty_cwd):
    assert "root: work.tracker.colour: unknown key" in _attributed(
        [("pkg", {"candidate-query": "q"}), ("root", {**COMPLETE, "colour": "red"})])


def test_an_unknown_nested_key_names_the_file_that_wrote_it(empty_cwd):
    root = {**COMPLETE, "credentials": {**COMPLETE["credentials"], "x": 1}}
    assert "root: work.tracker.credentials.x: unknown key" in _attributed(
        [("pkg", {"candidate-query": "q"}), ("root", root)])


def test_a_wrong_type_names_the_file_that_wrote_it(empty_cwd):
    assert ("root: work.tracker.base-url: expected a non-empty string, got int"
            in _attributed([("pkg", {"candidate-query": "q"}), ("root", {**COMPLETE, "base-url": 42})]))


def test_an_unsupported_provider_names_the_file_that_wrote_it(empty_cwd):
    problems = _attributed([("pkg", {"candidate-query": "q"}),
                            ("root", {**COMPLETE, "provider": "github"})])
    assert [p for p in problems if p.startswith("root: work.tracker.provider: 'github'")]


def test_a_missing_top_level_key_is_blamed_on_the_node_being_checked(empty_cwd):
    root = {k: v for k, v in COMPLETE.items() if k != "candidate-query"}
    assert "pkg: work.tracker.candidate-query: required" in _attributed(
        [("pkg", {"timeout-seconds": 5}), ("root", root)])


def test_a_missing_nested_key_under_an_ancestors_mapping_is_blamed_on_the_node(empty_cwd):
    """C22 at merge level. Root supplied `transitions`, but nobody set `claim`."""
    problems = _attributed([("pkg", {"candidate-query": "q"}),
                            ("root", {**COMPLETE, "transitions": {}})])
    assert "pkg: work.tracker.transitions.claim: required" in problems
    assert not [p for p in problems if p.startswith("root:")]


def test_a_key_whose_name_contains_a_dot_is_one_key(empty_cwd):
    """C24 at merge level."""
    assert "root: work.tracker.a.b: unknown key" in _attributed(
        [("pkg", {"candidate-query": "q"}), ("root", {**COMPLETE, "a.b": 1})])


def test_a_whole_block_that_is_not_a_mapping_names_the_ancestor(empty_cwd):
    assert _attributed([("pkg", COMPLETE), ("root", "off")]) == [
        "root: work.tracker: expected a mapping, got str"]


def test_a_node_whose_own_block_is_not_a_mapping_is_named_itself(empty_cwd):
    assert _attributed([("pkg", "none")]) == ["pkg: work.tracker: expected a mapping, got str"]


# ── the parser no longer raises on mixed key types ───────────────────────────


def test_mixed_key_types_at_the_top_level_are_reported_not_raised():
    """C26."""
    config, problems = parse_tracker_config({**COMPLETE, 5: 1, "z": 2})
    assert config is None
    assert "work.tracker.5: unknown key" in problems
    assert "work.tracker.z: unknown key" in problems


def test_mixed_key_types_inside_a_nested_mapping_are_reported_not_raised():
    """C26."""
    config, problems = parse_tracker_config(
        {**COMPLETE, "credentials": {**COMPLETE["credentials"], 5: 1, "z": 2}})
    assert config is None
    assert "work.tracker.credentials.5: unknown key" in problems
    assert "work.tracker.credentials.z: unknown key" in problems


# ── through the filesystem store ─────────────────────────────────────────────
#
# Nodes are siblings under `tmp_path`, never nested, so deleting one (C13, C14)
# leaves the others on disk.

import shutil
from pathlib import Path

import yaml

from tcw.store.fs import SENTINEL, FsWorkStore, init, write_sentinel
from tcw.store.project import FsProjectRegistry

ABSENT = object()


def _node(path: Path, project_id: str, *, board: bool) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if board:
        init(["work"], path, project_id)
    else:
        write_sentinel(path, project_id)
    return path.resolve()


def _connect(parent: Path, child: Path, parent_id: str, child_id: str) -> None:
    """Copied from `tests/test_store_nodes.py`. It replaces the child's whole
    `connected-projects`, so a chain must be connected top-down."""
    parent_cfg = yaml.safe_load((parent / SENTINEL).read_text()) or {}
    parent_cfg.setdefault("connected-projects", {}).setdefault("children", {})[
        child_id] = str(child)
    (parent / SENTINEL).write_text(yaml.safe_dump(parent_cfg, sort_keys=False))
    child_cfg = yaml.safe_load((child / SENTINEL).read_text()) or {}
    child_cfg["connected-projects"] = {"parent": {parent_id: str(parent)}}
    (child / SENTINEL).write_text(yaml.safe_dump(child_cfg, sort_keys=False))


def _set_tracker(node: Path, tracker) -> None:
    if tracker is ABSENT:
        return
    cfg = yaml.safe_load((node / SENTINEL).read_text()) or {}
    work = cfg.get("work") if isinstance(cfg.get("work"), dict) else {}
    cfg["work"] = {**work, "tracker": tracker}
    (node / SENTINEL).write_text(yaml.safe_dump(cfg, sort_keys=False))


def _chain(tmp_path: Path, *, root_board: bool, root, repo, pkg) -> dict[str, Path]:
    """root → repo → pkg. Every axis the store branches on is an explicit argument:
    whether root has a board, and each node's tracker block (`ABSENT` for none).
    Repo and pkg always have boards. The graph is checked before it is used, since
    a broken one makes the store quietly fall back to the node's own block."""
    nodes = {
        "root": _node(tmp_path / "root", "root", board=root_board),
        "repo": _node(tmp_path / "repo", "repo", board=True),
        "pkg": _node(tmp_path / "pkg", "pkg", board=True),
    }
    _connect(nodes["root"], nodes["repo"], "root", "repo")
    _connect(nodes["repo"], nodes["pkg"], "repo", "pkg")
    for name, tracker in (("root", root), ("repo", repo), ("pkg", pkg)):
        _set_tracker(nodes[name], tracker)
    for node in nodes.values():
        assert FsProjectRegistry.open(node).check() == []
    return nodes


def _store(node: Path) -> FsWorkStore:
    return FsWorkStore.open(node)


def _label(node: Path, project_id: str) -> str:
    return f"{node / SENTINEL} (project '{project_id}')"


QUERY_ONLY = {"candidate-query": "component = api"}


def test_a_query_only_child_inherits_everything_else(tmp_path):
    """C1."""
    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT, pkg=QUERY_ONLY)
    expected, _ = parse_tracker_config({**COMPLETE, **QUERY_ONLY})
    assert _store(nodes["pkg"]).tracker_config() == expected
    assert _store(nodes["pkg"]).tracker_problems() == []


def test_a_node_that_writes_no_block_does_not_inherit(tmp_path):
    """C2."""
    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT, pkg=QUERY_ONLY)
    assert _store(nodes["repo"]).tracker_config() is None
    assert _store(nodes["repo"]).tracker_problems() == []


def test_shared_settings_without_a_query_leave_non_tracking_nodes_green(tmp_path, monkeypatch):
    """C3."""
    shared = {k: v for k, v in COMPLETE.items() if k != "candidate-query"}
    nodes = _chain(tmp_path, root_board=False, root=shared, repo=ABSENT, pkg=QUERY_ONLY)
    expected, _ = parse_tracker_config({**shared, **QUERY_ONLY})
    assert _store(nodes["pkg"]).tracker_config() == expected
    assert _store(nodes["pkg"]).tracker_problems() == []
    assert _store(nodes["repo"]).tracker_config() is None
    assert _store(nodes["repo"]).tracker_problems() == []
    monkeypatch.chdir(nodes["root"])
    code, out, err = _run(["validate"])
    assert (code, out.strip()) == (0, "validate OK"), err


def test_nested_credentials_merge_through_the_store(tmp_path):
    """C4."""
    root = {**COMPLETE, "credentials": {"email-env": "A", "token-env": "B"}}
    pkg = {**QUERY_ONLY, "credentials": {"token-env": "C"}}
    nodes = _chain(tmp_path, root_board=False, root=root, repo=ABSENT, pkg=pkg)
    config = _store(nodes["pkg"]).tracker_config()
    assert (config.email_env, config.token_env) == ("A", "C")


def test_each_node_gets_its_own_nearest_base_url(tmp_path):
    """C5."""
    repo = {**COMPLETE, "base-url": "https://repo.example.invalid"}
    pkg = {**QUERY_ONLY, "base-url": "https://pkg.example.invalid",
           "credentials": {"email-env": "PKG_EMAIL", "token-env": "PKG_TOKEN"}}
    nodes = _chain(tmp_path, root_board=True, root=COMPLETE, repo=repo, pkg=pkg)
    assert _store(nodes["pkg"]).tracker_config().base_url == "https://pkg.example.invalid"
    assert _store(nodes["repo"]).tracker_config().base_url == "https://repo.example.invalid"
    assert _store(nodes["root"]).tracker_config().base_url == "https://root.example.invalid"


def test_a_child_null_takes_the_parents_value(tmp_path):
    """C6."""
    nodes = _chain(tmp_path, root_board=False, root={**COMPLETE, "timeout-seconds": 30},
                   repo=ABSENT, pkg={**QUERY_ONLY, "timeout-seconds": None})
    assert _store(nodes["pkg"]).tracker_config().timeout_seconds == 30


def test_a_lone_null_is_still_reported(tmp_path):
    """C7."""
    node = _node(tmp_path / "solo", "solo", board=True)
    _set_tracker(node, {**COMPLETE, "timeout-seconds": None})
    assert _store(node).tracker_config() is None
    assert [p for p in _store(node).tracker_problems()
            if p.startswith("tcw-config.yaml: work.tracker.timeout-seconds: ")]


def test_tracker_none_is_not_an_opt_out(tmp_path):
    """C8."""
    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT, pkg="none")
    assert _store(nodes["pkg"]).tracker_config() is None
    assert _store(nodes["pkg"]).tracker_problems() == [
        "tcw-config.yaml: work.tracker: expected a mapping, got str"]


def test_a_wrong_type_in_a_parent_names_the_parents_file(tmp_path):
    """C9."""
    nodes = _chain(tmp_path, root_board=False, root={**COMPLETE, "base-url": 42},
                   repo=ABSENT, pkg=QUERY_ONLY)
    assert _store(nodes["pkg"]).tracker_config() is None
    assert (f"{_label(nodes['root'], 'root')}: work.tracker.base-url: expected a "
            f"non-empty string, got int") in _store(nodes["pkg"]).tracker_problems()


def test_an_unknown_key_in_a_parent_names_the_parents_file(tmp_path):
    """C10."""
    nodes = _chain(tmp_path, root_board=False, root={**COMPLETE, "colour": "red"},
                   repo=ABSENT, pkg=QUERY_ONLY)
    assert (f"{_label(nodes['root'], 'root')}: work.tracker.colour: unknown key"
            in _store(nodes["pkg"]).tracker_problems())


def test_a_parent_block_that_is_not_a_mapping_disables_the_child(tmp_path):
    """C11."""
    nodes = _chain(tmp_path, root_board=False, root="off", repo=ABSENT, pkg=COMPLETE)
    assert _store(nodes["pkg"]).tracker_config() is None
    assert _store(nodes["pkg"]).tracker_problems() == [
        f"{_label(nodes['root'], 'root')}: work.tracker: expected a mapping, got str"]


def test_a_missing_grandparent_is_named_when_settings_are_incomplete(tmp_path):
    """C13."""
    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT, pkg=QUERY_ONLY)
    shutil.rmtree(nodes["root"])
    problems = _store(nodes["pkg"]).tracker_problems()
    assert "tcw-config.yaml: work.tracker.base-url: required" in problems
    assert ("tcw-config.yaml: work.tracker: declared parent 'root' is not available in "
            "this checkout, so any tracker settings it holds were not read (run tcw "
            "provision)") in problems


def test_a_missing_direct_parent_is_named_when_settings_are_incomplete(tmp_path):
    """C14."""
    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT, pkg=QUERY_ONLY)
    shutil.rmtree(nodes["repo"])
    problems = _store(nodes["pkg"]).tracker_problems()
    assert [p for p in problems if "declared parent 'repo' is not available" in p]
    assert not [p for p in problems if "declared parent 'root'" in p]


def test_a_missing_parent_adds_nothing_when_settings_are_complete(tmp_path):
    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT, pkg=COMPLETE)
    shutil.rmtree(nodes["root"])
    assert _store(nodes["pkg"]).tracker_problems() == []


def test_changing_the_site_without_credentials_is_refused(tmp_path):
    """C15."""
    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT,
                   pkg={**QUERY_ONLY, "base-url": "https://elsewhere.example.invalid"})
    assert _store(nodes["pkg"]).tracker_config() is None
    assert _store(nodes["pkg"]).tracker_problems() == [
        "tcw-config.yaml: work.tracker.credentials: inherited from a parent node, but "
        "base-url is set nearer, in tcw-config.yaml; set credentials in the same file "
        "as base-url"]


def test_repeating_the_parents_base_url_still_needs_credentials(tmp_path):
    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT,
                   pkg={**QUERY_ONLY, "base-url": COMPLETE["base-url"]})
    assert _store(nodes["pkg"]).tracker_config() is None
    problems = _store(nodes["pkg"]).tracker_problems()
    assert [p for p in problems if p.startswith(f"tcw-config.yaml: {CREDENTIALS_MESSAGE_START}")]
    assert not [p for p in problems if p.endswith(": required")]


def test_no_tracker_anywhere_means_no_tracker_and_no_problems(tmp_path):
    """C16."""
    nodes = _chain(tmp_path, root_board=True, root=ABSENT, repo=ABSENT, pkg=ABSENT)
    for node in nodes.values():
        assert _store(node).tracker_config() is None
        assert _store(node).tracker_problems() == []


def test_a_nested_required_key_nobody_set_is_blamed_on_the_child(tmp_path):
    """C22."""
    nodes = _chain(tmp_path, root_board=False, root={**COMPLETE, "transitions": {}},
                   repo=ABSENT, pkg=QUERY_ONLY)
    problems = _store(nodes["pkg"]).tracker_problems()
    assert "tcw-config.yaml: work.tracker.transitions.claim: required" in problems
    assert not [p for p in problems if str(nodes["root"]) in p]
    # Root's settings were inherited: only the key nobody set is missing.
    assert "tcw-config.yaml: work.tracker.transitions: required" not in problems
    assert not [p for p in problems if "base-url" in p or "provider" in p]


def test_all_null_credentials_do_not_hide_a_site_change(tmp_path):
    """C23."""
    pkg = {**QUERY_ONLY, "base-url": "https://elsewhere.example.invalid",
           "credentials": {"email-env": None, "token-env": None}}
    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT, pkg=pkg)
    assert _store(nodes["pkg"]).tracker_config() is None
    assert [p for p in _store(nodes["pkg"]).tracker_problems()
            if p.startswith(f"tcw-config.yaml: {CREDENTIALS_MESSAGE_START}")]


def test_a_dotted_key_in_a_parent_names_the_parents_file(tmp_path):
    """C24."""
    nodes = _chain(tmp_path, root_board=False, root={**COMPLETE, "a.b": 1},
                   repo=ABSENT, pkg=QUERY_ONLY)
    assert (f"{_label(nodes['root'], 'root')}: work.tracker.a.b: unknown key"
            in _store(nodes["pkg"]).tracker_problems())


def test_a_childs_own_bad_value_keeps_the_own_file_prefix_through_the_merge(tmp_path):
    """C25."""
    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT,
                   pkg={**QUERY_ONLY, "base-url": 42})
    problems = _store(nodes["pkg"]).tracker_problems()
    assert "tcw-config.yaml: work.tracker.base-url: expected a non-empty string, got int" in problems
    assert not [p for p in problems if p.endswith(": required")]


def test_a_broken_graph_falls_back_to_the_nodes_own_block_without_raising(tmp_path):
    aa = _node(tmp_path / "aa", "aa", board=True)
    bb = _node(tmp_path / "bb", "bb", board=True)
    _connect(aa, bb, "aa", "bb")
    _connect(bb, aa, "bb", "aa")
    _set_tracker(aa, QUERY_ONLY)
    _set_tracker(bb, COMPLETE)
    assert FsProjectRegistry.open(aa).check() != []
    store = _store(aa)
    assert store.tracker_config() is None
    problems = store.tracker_problems()
    assert problems and all(p.startswith("tcw-config.yaml: ") for p in problems)


def _run(argv):
    """Run the CLI in-process, as `tests/test_tracker_cli.py` does."""
    import contextlib
    import io

    from tcw.cli import main
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exit_:
            code = exit_.code or 0
    return code, out.getvalue(), err.getvalue()


# ── the commands ─────────────────────────────────────────────────────────────


def test_tracker_list_sends_the_childs_query_to_the_inherited_site(tmp_path, monkeypatch):
    """C17. No CLI code changed; this proves `tcw work tracker list` reads the merge."""
    import json

    from tcw.tracker import jira

    nodes = _chain(tmp_path, root_board=False, root=COMPLETE, repo=ABSENT, pkg=QUERY_ONLY)
    monkeypatch.chdir(nodes["pkg"])
    monkeypatch.setenv("ROOT_EMAIL", "probe@example.test")
    monkeypatch.setenv("ROOT_TOKEN", "probe-token")
    calls = []

    def fake(self, method, path, body=None, *, timeout=None):
        calls.append((self.config.base_url, path, body))
        return (200, {}, json.dumps({"isLast": True, "issues": []}).encode())

    monkeypatch.setattr(jira.JiraClient, "_request", fake)
    code, out, err = _run(["work", "tracker", "list"])
    assert code == 0, err
    assert "no tracker is configured" not in err
    assert len(calls) == 1
    base_url, path, body = calls[0]
    assert base_url == COMPLETE["base-url"]
    assert path.startswith("/rest/api/3/search/jql")
    sent = json.loads(body) if isinstance(body, (bytes, str)) else body
    assert sent["jql"] == QUERY_ONLY["candidate-query"]


def test_validate_reports_a_parents_bad_value_under_each_child_that_inherits_it(
        tmp_path, monkeypatch):
    nodes = _chain(tmp_path, root_board=False, root={**COMPLETE, "base-url": 42},
                   repo=ABSENT, pkg=QUERY_ONLY)
    monkeypatch.chdir(nodes["root"])
    code, out, err = _run(["validate"])
    assert code == 1
    assert "validate OK" not in out
    assert (f"[pkg] {_label(nodes['root'], 'root')}: work.tracker.base-url: expected a "
            f"non-empty string, got int") in err
    # Repo writes no block, so it inherits nothing and reports nothing.
    assert "[repo]" not in err
