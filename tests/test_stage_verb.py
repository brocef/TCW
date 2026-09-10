"""`tcw work stage` — legality, stream discipline, and writing nothing."""

import hashlib
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import (
    LIFECYCLE_STEPS, STAGE_IDS, STAGE_NEXT_STEPS, STAGE_STATUSES, WORK_STATUSES,
    Artifact, WorkStore,
)
from tcw.store.fs import FsWorkStore, init
from tcw.work.resolve import (
    bookend, load_builtins, substitute_body, substitute_documentation)


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


def test_the_table_covers_every_stage_and_only_real_statuses():
    assert set(STAGE_STATUSES) == set(STAGE_IDS)
    for stage, statuses in STAGE_STATUSES.items():
        assert set(statuses) <= set(WORK_STATUSES), stage


def test_each_row_is_what_the_lifecycle_contract_says():
    """Written out rather than derived, because the two non-obvious rows are
    exactly where a table written from the happy path goes wrong."""
    assert STAGE_STATUSES == {
        # Empty means "no work-item status applies", which is a true statement
        # about a stage that runs before an item exists — not "refused". The
        # `inbox` branch in `_stage` is chosen by stage id; nothing reads this
        # emptiness as a rejection.
        "inbox": (),
        "request": ("backlog",),
        "spec": ("backlog",),
        "plan": ("backlog",),
        "implement": ("active",),
        # `complete` moves from `review | active`, so an item can be verified
        # without ever having been submitted.
        "verify": ("active", "review"),
        # Not `discarded`: `completed` means shipped and `discarded` means closed
        # without shipping, and a post-mortem on work nobody did is not this.
        "postmortem": ("review", "completed"),
    }


def test_the_next_step_table_covers_every_stage():
    """Its sibling `STAGE_STATUSES` has exactly this check. A stage missing from
    here raises `KeyError` inside the footer, which surfaces as a stage whose
    instructions cannot be printed at all."""
    assert set(STAGE_NEXT_STEPS) == set(STAGE_IDS)


def test_every_next_step_names_a_command_that_exists():
    """The footer is the one place TCW tells a reader what to run next, and it is
    prose in a table — nothing resolves it against the parser. A verb renamed
    without touching this table would send every reader of every stage to a
    command that exits 2."""
    import re
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

    shipped = {v for v in verbs(build_parser()) if v}
    for stage_id, text in STAGE_NEXT_STEPS.items():
        for cited in re.findall(r"`tcw ([a-z][a-z -]*?)(?: <|`)", text):
            words = cited.split()
            # Longest shipped prefix, so `work stage gate request` is read as the
            # verb `work stage gate` applied to the stage `request` — and the
            # stage id is checked too, not skipped as leftovers.
            verb = next((" ".join(words[:n]) for n in range(len(words), 0, -1)
                         if " ".join(words[:n]) in shipped), None)
            assert verb, (f"{stage_id}'s next step names `tcw {cited}`, whose "
                          f"leading words are not a command")
            rest = words[len(verb.split()):]
            assert all(w in STAGE_IDS for w in rest), (
                f"{stage_id}'s next step names `tcw {cited}`, and {rest} is not "
                f"a stage id")


def test_a_stage_producing_two_artifacts_names_a_branch_for_each():
    """Derived from `LifecycleStep.produces`, not from a list naming `verify`.

    A stage that can end two ways has a footer that is the last line its reader
    sees. If it names only one branch, the reader who took the other is told to
    run a command for a verdict they did not reach. `verify` shipped that way:
    the footer named `tcw work complete` alone, contradicting the stage's own
    step 6, and `tcw work complete` does not refuse an item carrying `rework.md`.

    One command per outcome is the floor. It does not check that the commands
    are the *right* ones — nothing derives that — but a footer that lost a
    branch fails here.
    """
    for step in LIFECYCLE_STEPS:
        if step.kind != "stage" or len(step.produces) < 2:
            continue
        text = STAGE_NEXT_STEPS[step.id]
        commands = set(re.findall(r"`(tcw work [a-z-]+)", text))
        assert len(commands) >= len(step.produces), (
            f"{step.id} produces {len(step.produces)} artifacts "
            f"({', '.join(step.produces)}) but its next step names "
            f"{len(commands)} command(s): {sorted(commands) or 'none'}")


def test_a_next_step_names_a_transition_only_where_one_is_needed():
    """Derived from `STAGE_STATUSES`, because the footer is prose asserting a
    lifecycle fact and prose does not check itself.

    A footer sending the reader straight to the next stage is claiming that stage
    is legal where they already are. A footer naming a transition first is
    claiming it is not. Both directions are wrong to get wrong: an unnecessary
    `tcw work submit` moves an item to `review` for no reason, and a missing
    `tcw work start` sends the reader to a stage that refuses them.

    `implement` was the one this caught. It named `tcw work submit` before
    `verify`, which is legal from `active` too — so the transition was optional
    and the `verify` instructions already own that decision.
    """
    for stage_id, text in STAGE_NEXT_STEPS.items():
        m = re.search(r"`tcw work stage gate (\w+)", text)
        if not m:                     # `verify` ends in a transition; `postmortem` in nothing
            continue
        nxt = m.group(1)
        here, there = set(STAGE_STATUSES[stage_id]), set(STAGE_STATUSES[nxt])
        if not here:                  # `inbox` runs before an item has a status
            continue
        names_transition = "tcw work " in text.split("`tcw work stage gate")[0]
        if names_transition:
            assert not (here & there), (
                f"{stage_id} names a transition before {nxt}, but {nxt} is "
                f"already legal in {sorted(here & there)}")
        else:
            assert here & there, (
                f"{stage_id} sends the reader straight to {nxt}, which is legal "
                f"only in {sorted(there)} — a transition is needed first")


@pytest.fixture
def one_of_each(tmp_path):
    """An item in every status, in one node, so the matrix can be swept."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    slugs = {}
    for status in WORK_STATUSES:
        item = st.create(f"Item {status}", body="req\n")
        if status in ("active", "review", "completed", "discarded"):
            st.start(item.slug)
        if status in ("review",):
            st.submit(item.slug)
        if status == "completed":
            st.complete(item.slug, "done", dod_ack=list(st.dod_checklist()),
                        force=True)
        if status == "discarded":
            st.complete(item.slug, "wontfix", dod_ack=[], force=True)
        slugs[status] = item.slug
    return root, slugs


def test_every_illegal_pair_is_rejected_and_every_legal_one_accepted(one_of_each):
    """The whole Cartesian product, driven from the table.

    Special-casing the two illegal pairs someone thought to test is precisely
    what this closes — and if it ever finds a combination users need, the table
    is wrong rather than the test.
    """
    root, slugs = one_of_each
    for stage in STAGE_IDS:
        for status in WORK_STATUSES:
            r = _cli(root, stage, slugs[status])
            legal = status in STAGE_STATUSES[stage]
            assert (r.returncode == 0) is legal, (
                f"{stage} in {status}: expected "
                f"{'accept' if legal else 'reject'}, got rc={r.returncode} "
                f"{r.stderr}")
            if not legal:
                assert r.stdout == ""


def test_postmortem_is_rejected_on_a_discarded_item(one_of_each):
    """Named separately because it is the row the first draft of the spec got
    wrong, and a matrix test that itself derives from the table would agree with
    a wrong table."""
    root, slugs = one_of_each
    r = _cli(root, "postmortem", slugs["discarded"])
    assert r.returncode == 1
    assert "not legal" in r.stderr


def test_inbox_refuses_a_work_item_argument(one_of_each):
    """There is no item at this point, so a reference is a mistake to report,
    never something to interpret.

    The refusal must be its own: `inbox` has an empty legality row, so a branch
    that fell through to the status check would report "not legal for an item in
    'backlog'" — true of nothing and misleading about why.
    """
    root, slugs = one_of_each
    r = _cli(root, "inbox", slugs["backlog"])
    assert r.returncode == 1
    assert r.stdout == ""
    assert "takes no work item" in r.stderr
    assert "not legal" not in r.stderr


def test_an_unknown_stage_names_the_legal_ids(one_of_each):
    root, slugs = one_of_each
    r = _cli(root, "speck", slugs["backlog"])
    assert r.returncode == 1 and r.stdout == ""
    assert "unknown stage 'speck'" in r.stderr and "spec" in r.stderr


def test_a_transition_id_is_not_a_stage(one_of_each):
    root, slugs = one_of_each
    assert _cli(root, "complete", slugs["backlog"]).returncode == 1


# ── streams ──────────────────────────────────────────────────────────────────


def test_the_gate_prints_nothing_on_stdout(tmp_path):
    """The verb's contract: an exit code, and everything else on stderr. A check
    that writes to stdout must not reach the caller's, or a pipeline reading
    `prompt` elsewhere cannot trust that this one is silent."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    _configure(root, {"stages": {"spec": {
        "pre": [{"command": "printf 'check-out'; printf 'check-err' >&2"}],
        "prompt": [{"blob": "THE PROMPT"}]}}})

    r = _cli(root, "spec", item.slug)
    assert r.returncode == 0
    assert r.stdout == ""
    assert "THE PROMPT" not in r.stderr        # the gate resolves no prompt
    assert "check-out" in r.stderr and "check-err" in r.stderr
    assert "tcw work stage prompt spec" in r.stderr


def test_the_gate_resolves_no_prompt_at_all(tmp_path):
    """Not "resolves and discards": a `generate:` binding must not run a script
    for output nobody reads. Paired with the `prompt` half so that a generator
    which never worked cannot pass the first assertion on its own."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    sentinel = (tmp_path / "GENERATED").resolve()
    _configure(root, {"stages": {"spec": {
        "prompt": [{"generate": f"touch {sentinel}; printf 'x'"}]}}})

    assert _cli(root, "spec", item.slug).returncode == 0
    assert not sentinel.exists(), "the gate resolved the stage's prompt"

    assert _prompt(root, "spec", item.slug).returncode == 0
    assert sentinel.exists(), "the generator never ran, so the check above proves nothing"


def test_a_failing_check_stops_before_the_prompt_would_have_run(tmp_path):
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    sentinel = (tmp_path / "GENERATED").resolve()
    _configure(root, {"stages": {"spec": {
        "pre": [{"command": "exit 7"}],
        "prompt": [{"generate": f"touch {sentinel}; printf 'x'"}]}}})

    r = _cli(root, "spec", item.slug)
    assert r.returncode == 1
    assert r.stdout == ""
    assert "exit 7" in r.stderr
    assert not sentinel.exists()


def test_a_late_generator_failure_leaves_stdout_empty(tmp_path):
    """The text is buffered and emitted once, after everything that can fail has
    succeeded — so an earlier binding that resolved fine still prints nothing."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    _configure(root, {"stages": {"spec": {"prompt": [
        {"blob": "resolved first"},
        {"generate": "exit 5"}]}}})

    r = _prompt(root, "spec", item.slug)
    assert r.returncode == 1
    assert r.stdout == ""
    assert "resolved first" not in r.stdout


# ── writing nothing ──────────────────────────────────────────────────────────


def test_no_mutating_store_method_is_called(tmp_path, monkeypatch):
    """The portable half: a Jira-backed adapter has no item folder, so the
    property is "no mutator ran", not "no file changed"."""
    from tcw.cli import main
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    _configure(root, {"stages": {"spec": {"prompt": [{"blob": "text"}]}}})

    mutators = [name for name in dir(WorkStore)
                if name.startswith(("create", "update", "write", "delete",
                                    "set_", "start", "submit", "rework",
                                    "complete", "drop", "inbox_accept",
                                    "record"))
                and callable(getattr(WorkStore, name, None))]
    assert mutators, "found no mutating methods to guard — the guard is vacuous"
    called = []
    for name in mutators:
        original = getattr(FsWorkStore, name, None)
        if original is None:
            continue
        monkeypatch.setattr(FsWorkStore, name,
                            (lambda n: lambda *a, **k: called.append(n))(name))

    monkeypatch.chdir(root)
    assert main(["work", "stage", "gate", "spec", item.slug]) == 0
    assert called == [], f"`gate` called mutators: {called}"

    # `prompt` skips the gate, so it reaches resolution by a different path and
    # needs its own guard — the property is the same and the route is not.
    assert main(["work", "stage", "prompt", "spec", item.slug]) == 0
    assert called == [], f"`prompt` called mutators: {called}"
    assert main(["work", "stage", "prompt", "spec"]) == 0
    assert called == [], f"itemless `prompt` called mutators: {called}"


def test_the_item_folder_is_byte_identical_after_every_legal_stage(tmp_path):
    """The adapter half: catches anything that writes without going through the
    store at all."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    st.write_artifact(item.slug, "spec", "# Spec\n")
    # `inbox` is excluded deliberately, not left over: this test walks an
    # *item* folder, and `inbox` neither takes an item nor appears in the loop
    # below (its legality row is empty). Configuring it would add a binding no
    # assertion here exercises.
    _configure(root, {"stages": {sid: {"prompt": [{"blob": f"{sid} text"}]}
                                 for sid in STAGE_IDS if sid != "inbox"}})

    folder = st.path(item.slug)
    for stage in STAGE_IDS:
        if "backlog" not in STAGE_STATUSES[stage]:
            continue
        before = _manifest(folder)
        assert _cli(root, stage, item.slug).returncode == 0
        assert _manifest(folder) == before, f"`stage {stage}` wrote something"


# ── --no-exec ────────────────────────────────────────────────────────────────


def test_no_exec_runs_nothing_and_names_what_it_skipped(tmp_path):
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    check_sentinel = (tmp_path / "CHECK").resolve()
    gen_sentinel = (tmp_path / "GEN").resolve()
    (root / "guide.md").write_text("from a file\n")
    _configure(root, {"stages": {"spec": {
        "pre": [{"command": f"touch {check_sentinel}"}],
        "prompt": [{"blob": "static text"},
                   {"file": "guide.md"},
                   {"generate": f"touch {gen_sentinel}; printf 'gen'"}]}}})

    # Each verb reports its own half and nothing else, and neither prints on
    # stdout: a dry run that emitted partial text could be mistaken for the
    # instructions, which is the whole reason the plan goes to stderr.
    g = _cli(root, "spec", item.slug, "--no-exec")
    assert g.returncode == 0 and g.stdout == ""
    assert "pre check would run" in g.stderr
    assert "prompt file" not in g.stderr       # the prompt is not the gate's business

    r = _prompt(root, "spec", item.slug, "--no-exec")
    assert r.returncode == 0 and r.stdout == ""
    assert "prompt file" in r.stderr
    assert f"touch {gen_sentinel}" in r.stderr
    assert "pre check would run" not in r.stderr

    assert not check_sentinel.exists() and not gen_sentinel.exists()


def test_without_no_exec_the_same_stage_runs_everything(tmp_path):
    """The other side of the previous test: if this failed the same way, that
    one would prove nothing."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    check_sentinel = (tmp_path / "CHECK").resolve()
    (root / "guide.md").write_text("from a file\n")
    _configure(root, {"stages": {"spec": {
        "pre": [{"command": f"touch {check_sentinel}"}],
        "prompt": [{"blob": "static text"}, {"file": "guide.md"},
                   {"generate": "printf 'gen'"}]}}})

    g = _cli(root, "spec", item.slug)
    assert g.returncode == 0
    assert check_sentinel.exists()

    r = _prompt(root, "spec", item.slug)
    assert r.returncode == 0
    assert "static text\n\nfrom a file\n\ngen" in r.stdout


def test_each_no_exec_header_names_the_verb_that_printed_it(tmp_path):
    """Both verbs take the flag, so the header has to say which one ran or a
    reader copying it out of a log runs the wrong command. Neither may name the
    bare form, which is not a command at all."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    _configure(root, {"stages": {"spec": {"prompt": [{"blob": "text"}]}}})

    g = _cli(root, "spec", item.slug, "--no-exec")
    assert g.returncode == 0
    assert "tcw work stage gate spec: --no-exec" in g.stderr

    r = _prompt(root, "spec", item.slug, "--no-exec")
    assert r.returncode == 0
    assert "tcw work stage prompt spec: --no-exec" in r.stderr

    for out in (g.stderr, r.stderr):
        assert "tcw work stage spec:" not in out


def test_no_exec_reports_a_condition_that_did_not_match(tmp_path):
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug"])
    item = st.create("Thing", body="req\n")
    _configure(root, {"stages": {"spec": {"prompt": [
        {"blob": "for bugs", "when": {"tags": ["bug"]}},
        {"blob": "for all"}]}}})

    r = _prompt(root, "spec", item.slug, "--no-exec")
    assert "skipped (condition)" in r.stderr
    assert r.stdout == ""


# ── the built-in floor, end to end ───────────────────────────────────────────


def test_an_unconfigured_node_prints_tcws_own_instructions(one_of_each):
    """The demonstration. A node with no `work.lifecycle` key at all — which is
    the state every node starts in — gets TCW's instructions for the stage
    rather than exit 0 and silence.

    The shipped prompt is a *template*: `plan` and `implement` wrap their
    documentation instruction in `{{tcw:documentation}}…{{/tcw:documentation}}`,
    and `spec` and `plan` name their input through `{{tcw:body}}…{{/tcw:body}}`.
    With nothing configured the documentation span resolves to its own inner
    text; the body span resolves against the item, and `one_of_each` builds every
    item with a `body=`, so it resolves to the request. The comparison is against
    the resolved source rather than the raw file. The bytes an unconfigured node
    actually receives are pinned independently, against a fixture captured before
    any of this existed, in `test_prompt_fallback.py`.
    """
    root, slugs = one_of_each
    shipped = load_builtins().stage_prompts
    has_request = [Artifact("initial-request", True)]
    for stage in sorted(set(STAGE_IDS) - {"inbox"}):
        status = STAGE_STATUSES[stage][0]
        slug = slugs[status]
        r = _prompt(root, stage, slug)
        assert r.returncode == 0, r.stderr
        resolved = substitute_body(
            substitute_documentation(shipped[stage], ()), has_request)
        assert r.stdout == bookend(resolved, stage, slug) + "\n"


def test_inbox_prints_its_prompt_with_no_item(one_of_each):
    """The stage that runs before an item exists, invoked the only way it can
    be: with no reference at all.

    Asserting the replaced message is absent, not just that the new one is
    present — the refusal this supersedes said "runs before an item exists",
    and a branch that still printed it while somehow exiting 0 would satisfy a
    presence-only check.
    """
    root, _ = one_of_each
    r = _prompt(root, "inbox")
    assert r.returncode == 0, r.stderr
    assert r.stdout == bookend(
        load_builtins().stage_prompts["inbox"], "inbox", "<slug>") + "\n"
    assert r.stderr == ""
    assert "runs before an item exists" not in r.stderr


# ── the reading verb ─────────────────────────────────────────────────────────


def test_prompt_prints_the_built_in_for_every_stage_unconfigured(one_of_each):
    """`prompt` reaches all seven stages on a node that configured nothing.

    `inbox` is included and is the one that takes no reference, which is why the
    loop cannot simply pass a slug to each.
    """
    root, slugs = one_of_each
    shipped = load_builtins().stage_prompts
    for stage in STAGE_IDS:
        r = _prompt(root, stage) if stage == "inbox" else _prompt(
            root, stage, slugs["backlog"])
        assert r.returncode == 0, f"{stage}: {r.stderr}"
        assert shipped[stage].strip().splitlines()[0] in r.stdout


def test_prompt_answers_for_an_item_in_any_status(one_of_each):
    """The whole point: `gate` refuses most of this matrix, and `prompt` is how
    you ask anyway. Swept over the same product as the legality test, so the two
    disagree by design rather than by omission."""
    root, slugs = one_of_each
    for stage in sorted(set(STAGE_IDS) - {"inbox"}):
        for status in WORK_STATUSES:
            r = _prompt(root, stage, slugs[status])
            assert r.returncode == 0, (
                f"{stage} in {status}: rc={r.returncode} {r.stderr}")
            assert r.stdout != ""


def test_prompt_says_so_on_stderr_when_the_stage_is_not_legal(one_of_each):
    """Exit 0 and a note, not an error. stdout carries the instructions alone,
    so a caller piping it gets the whole text and nothing else."""
    root, slugs = one_of_each
    r = _prompt(root, "implement", slugs["backlog"])
    assert r.returncode == 0
    assert r.stdout != "" and "not legal" not in r.stdout
    assert "not legal" in r.stderr and "backlog" in r.stderr


def test_the_two_verbs_no_longer_print_the_same_bytes(tmp_path):
    """They did, and that was the defect. Any view composing a stage out of both
    showed the instructions twice, and every wording around it was an apology for
    the repetition. `gate` now prints none of it."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    (root / "guide.md").write_text("from a file\n")
    _configure(root, {"stages": {"spec": {
        "prompt": [{"blob": "static text"}, {"file": "guide.md"}]}}})

    gated = _cli(root, "spec", item.slug)
    read = _prompt(root, "spec", item.slug)
    assert gated.returncode == 0 and read.returncode == 0, gated.stderr
    assert gated.stdout == ""
    assert "static text" in read.stdout and "from a file" in read.stdout


def test_prompt_runs_no_gate_and_the_gate_verb_does(tmp_path):
    """The paired assertion. A `pre` binding that leaves a trace is the only way
    to observe non-execution: without the `gate` half, the `prompt` half passes
    just as well when the gate is broken and never runs at all.

    A throwaway sentinel command rather than this repository's
    `require_artifact.py`, which writes nothing and so can evidence nothing.
    """
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")     # backlog: `plan` is legal…
    sentinel = (tmp_path / "GATE-RAN").resolve()
    _configure(root, {"stages": {"plan": {
        "pre": [{"command": f"touch {sentinel}; exit 1"}],
        "prompt": [{"blob": "plan instructions"}]}}})

    read = _prompt(root, "plan", item.slug)
    assert read.returncode == 0, read.stderr
    assert "plan instructions" in read.stdout
    assert not sentinel.exists(), "prompt ran the stage's pre binding"

    gated = _cli(root, "plan", item.slug)
    assert gated.returncode == 1
    assert gated.stdout == ""
    assert sentinel.exists(), "the gate never ran, so the check above proves nothing"


def test_a_condition_matches_only_when_an_item_is_named(tmp_path):
    """What makes the optional reference worth having rather than cosmetic: the
    two invocations resolve different text on purpose."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug"])
    item = st.create("Thing", body="req\n")
    st.update_work(item.slug, tags=["bug"])
    _configure(root, {"stages": {"spec": {"prompt": [
        {"blob": "for bugs", "when": {"tags": ["bug"]}},
        {"blob": "for all"}]}}})

    generic = _prompt(root, "spec")
    assert generic.returncode == 0, generic.stderr
    assert "for all" in generic.stdout and "for bugs" not in generic.stdout

    for_item = _prompt(root, "spec", item.slug)
    assert for_item.returncode == 0, for_item.stderr
    assert "for bugs\n\nfor all" in for_item.stdout


def test_a_qualified_reference_reads_the_owning_nodes_bindings(tmp_path):
    """`prompt <stage> <project-id>/<slug>` answers with the *other* node's
    configuration. Both nodes bind the stage, to different text, so a resolution
    that quietly stayed in the anchor node would still print something."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"],
                   check=True)
    anchor, child = tmp_path / "anchor", tmp_path / "child"
    for path, name in ((anchor, "anchor"), (child, "child")):
        path.mkdir()
        init(["work"], path, name)
    (anchor / "tcw-config.yaml").write_text(
        "id: anchor\nconnected-projects:\n  children:\n    child: ../child\n")
    (child / "tcw-config.yaml").write_text(
        "id: child\nconnected-projects:\n  parent:\n    anchor: ../anchor\n")
    _configure(anchor, {"stages": {"spec": {"prompt": [{"blob": "ANCHOR TEXT"}]}}})
    _configure(child, {"stages": {"spec": {"prompt": [{"blob": "CHILD TEXT"}]}}})
    item = FsWorkStore.open(child).create("Thing", body="req\n")

    r = _prompt(anchor, "spec", f"child/{item.slug}")
    assert r.returncode == 0, r.stderr
    assert "CHILD TEXT" in r.stdout and "ANCHOR TEXT" not in r.stdout


def test_a_qualified_reference_survives_into_the_advised_commands(tmp_path):
    """Both verbs quote a command back at the reader — the bookend header names
    the gate, the gate's success line names the prompt. `_resolve` returns a
    **bare** slug by contract, so displaying that drops the `<project-id>/`
    qualifier and advises a command that resolves against the anchor node.

    Slugs are date-prefixed and derived from titles, so two nodes filing the same
    request on one day produce the same slug. The advised command then silently
    gates the wrong node's item and runs the wrong node's `pre` bindings, which
    is why this is worth a test rather than a cosmetic note. Both nodes here hold
    an item of the same slug, so a stripped qualifier resolves rather than
    erroring.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"],
                   check=True)
    anchor, child = tmp_path / "anchor", tmp_path / "child"
    for path, name in ((anchor, "anchor"), (child, "child")):
        path.mkdir()
        init(["work"], path, name)
    (anchor / "tcw-config.yaml").write_text(
        "id: anchor\nconnected-projects:\n  children:\n    child: ../child\n")
    (child / "tcw-config.yaml").write_text(
        "id: child\nconnected-projects:\n  parent:\n    anchor: ../anchor\n")
    mine = FsWorkStore.open(anchor).create("Same Title", body="req\n")
    theirs = FsWorkStore.open(child).create("Same Title", body="req\n")
    assert mine.slug == theirs.slug, "the collision this test needs did not happen"
    ref = f"child/{theirs.slug}"

    r = _prompt(anchor, "spec", ref)
    assert r.returncode == 0, r.stderr
    assert f"tcw work stage gate spec {ref}" in r.stdout, (
        "the bookend dropped the project qualifier, so it advises gating the "
        f"anchor node's own {theirs.slug}")

    g = _cli(anchor, "spec", ref)
    assert g.returncode == 0, g.stderr
    assert f"tcw work stage prompt spec {ref}" in g.stderr, (
        "the gate's success line dropped the project qualifier")


def test_prompt_refuses_a_work_item_for_inbox(one_of_each):
    """Same rule as `gate`, and for the same reason: there is no item yet, so a
    reference is a mistake to report rather than something to interpret."""
    root, slugs = one_of_each
    r = _prompt(root, "inbox", slugs["backlog"])
    assert r.returncode == 1
    assert r.stdout == ""
    assert "takes no work item" in r.stderr

    ok = _prompt(root, "inbox")
    assert ok.returncode == 0, ok.stderr
    assert ok.stdout == bookend(
        load_builtins().stage_prompts["inbox"], "inbox", "<slug>") + "\n"


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


def test_prompt_accepts_no_exec_and_prints_no_text(tmp_path):
    """It used to refuse the flag, because suppressing `file:` and `generate:`
    would leave incomplete *instructions* on stdout. It leaves none there at all:
    the plan goes to stderr. Refusing now would drop the conditioned
    matched/skipped diagnostic from the CLI, since `gate` reports only its own
    bindings."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    (root / "guide.md").write_text("from a file\n")
    _configure(root, {"stages": {"spec": {
        "prompt": [{"blob": "text"}, {"file": "guide.md"}]}}})

    r = _prompt(root, "spec", item.slug, "--no-exec")
    assert r.returncode == 0
    assert r.stdout == ""
    assert "from a file" not in r.stderr        # the file is not read either
    assert "prompt file — matched: guide.md" in r.stderr


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


def test_the_bare_form_is_a_usage_error_naming_both_verbs(one_of_each):
    """Exit 2, argparse's code for a command line that is not a command — not 1,
    which would say the stage was attempted and failed."""
    root, slugs = one_of_each
    r = _bare(root, "spec", slugs["backlog"])
    assert r.returncode == 2
    assert r.stdout == ""
    assert f"tcw work stage gate spec {slugs['backlog']}" in r.stderr
    assert f"tcw work stage prompt spec {slugs['backlog']}" in r.stderr


def test_the_bare_form_resolves_nothing_and_runs_nothing(tmp_path):
    """It reports the command to run; it does not quietly run it. An alias is
    the thing this release decided against, and a bare form that resolved the
    prompt would be one in all but name."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    sentinel = (tmp_path / "RAN").resolve()
    _configure(root, {"stages": {"spec": {
        "pre": [{"command": f"touch {sentinel}"}],
        "prompt": [{"blob": "THE PROMPT"}]}}})

    r = _bare(root, "spec", item.slug)
    assert r.returncode == 2
    assert "THE PROMPT" not in r.stdout + r.stderr
    assert not sentinel.exists()


# ── the bookends ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("stage_id", STAGE_IDS)
def test_every_stage_is_bookended_with_its_own_gate_and_next_step(stage_id,
                                                                  one_of_each):
    """The header is the replacement for a guarantee this release gave up.
    `prompt` gates nothing, so wanting the instructions no longer makes anyone
    run `gate` — the reminder has to ride with the text, where every reader sees
    it under either harness rather than only through the Claude-only skill."""
    root, slugs = one_of_each
    if stage_id == "inbox":
        # Resolved without a reference, so the commands keep the placeholder —
        # and `inbox`'s own gate invocation takes none at all.
        r, ref, gate = _prompt(root, "inbox"), "<slug>", "tcw work stage gate inbox"
    else:
        ref = slugs[STAGE_STATUSES[stage_id][0]]
        r = _prompt(root, stage_id, ref)
        gate = f"tcw work stage gate {stage_id} {ref}"
    assert r.returncode == 0, r.stderr

    assert r.stdout.startswith("> **This text ran no checks.**")
    assert gate in r.stdout.splitlines()[0]
    assert "## When this stage's output is written" in r.stdout
    nxt = STAGE_NEXT_STEPS[stage_id].replace("<slug>", ref)
    expected = (nxt[0].upper() + nxt[1:] + "." if nxt else
                "Nothing follows. This stage runs out of band and moves no item.")
    assert r.stdout.rstrip().endswith(expected)


def test_postmortem_says_nothing_follows_rather_than_omitting_the_section(
        one_of_each):
    """A missing section reads as a footer that failed to resolve. `postmortem`
    is the one stage nothing follows, so it says so."""
    root, slugs = one_of_each
    r = _prompt(root, "postmortem", slugs["review"])
    assert r.returncode == 0, r.stderr
    assert "## When this stage's output is written" in r.stdout
    assert "Nothing follows" in r.stdout
    assert "tcw work stage gate " in r.stdout.splitlines()[0]   # header only


def test_the_bookends_wrap_a_projects_own_bindings_too(tmp_path):
    """Overriding what a stage *says* is not overriding where the lifecycle goes
    next, and a reader of the overridden text needs the gate reminder just as
    much. A wrapper applied only to the built-in floor would give the reminder
    to exactly the projects that configured nothing."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    _configure(root, {"stages": {"spec": {"prompt": [{"blob": "OURS ALONE"}]}}})

    r = _prompt(root, "spec", item.slug)
    assert r.returncode == 0, r.stderr
    assert "OURS ALONE" in r.stdout
    assert r.stdout.startswith("> **This text ran no checks.**")
    assert f"tcw work stage gate plan {item.slug}" in r.stdout


def test_a_stage_that_resolves_to_nothing_is_not_bookended(tmp_path):
    """`resolve_prompts` promises that a stage whose only binding does not match
    resolves to nothing. Wrapping that nothing would turn silence into a header
    and a footer around an empty middle, which reads as a stage that failed to
    resolve rather than one the project deliberately silenced."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug"])
    item = st.create("Thing", body="req\n")          # no tags
    _configure(root, {"stages": {"spec": {"prompt": [
        {"blob": "only for bugs", "when": {"tags": ["bug"]}}]}}})

    r = _prompt(root, "spec", item.slug)
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""
