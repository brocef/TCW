"""Top-level `tcw` CLI: dispatches `validate | serve | migrate | taxonomy |
capabilities | work | project`.

Built component groups register their own subparsers; the rest stub to "not yet
implemented" until their phase lands (capabilities = Phase 3, work = Phase 5).
"""

import argparse
import os
import re
import sys
from pathlib import Path

from tcw.cli_suggest import SuggestingParser, attach_index
from tcw.errors import ConfigError, TcwError
from tcw import __version__
from tcw import project_cli
from tcw.capabilities import cli as capabilities_cli
from tcw.migrate import cli as migrate_cli
from tcw.serve import DEFAULT_PORT, serve
from tcw.store.fs import (
    COMPONENTS, SENTINEL, STORE_CLASSES, FsStoreProvisioner,
    LOCAL_CONFIG, LOCAL_MANIFEST, declared_repository, find_project_root, git_root,
    ignore_personal_files, init, load_config, refuse_legacy_project,
    refuse_retired_config,
)
from tcw.store.base import MultipleMatch
from tcw.store.project import FsProjectRegistry
import yaml
from tcw.taxonomy import cli as taxonomy_cli
from tcw.work import cli as work_cli


# Every component the provisioning verb can serve. This was narrowed to `work`
# while only the work store had an adapter — a taxonomy declaration was cloned
# and then refused for missing work statuses — and widens here together with the
# adapters that make the other two values honest, never ahead of them.
PROVISION_COMPONENTS = COMPONENTS

# Component CLI modules (each exposes NAME and
# add_subparser). All three components are now built.
_BUILT = [taxonomy_cli, capabilities_cli, work_cli]
_STUBBED = [c for c in COMPONENTS if c not in {m.NAME for m in _BUILT}]


def run_init(components: list[str], project_id: str | None = None,
             work_path: str | None = None,
             paths: dict[str, str] | None = None) -> int:
    """Scaffold the named stores under the current directory and mark it a
    project. Prints nothing on stdout; names each file written and folder
    created on stderr (TCW-73 Design 1.7)."""
    from tcw.errors import BackendError, UsageError
    from tcw.output import changed
    root = Path.cwd()
    unknown = [c for c in components if c not in COMPONENTS]
    if unknown:
        raise UsageError(f"unknown axis {', '.join(repr(c) for c in unknown)}; "
                         f"choose from {', '.join(COMPONENTS)}")
    # Checked on the text: as a `Path`, `tcw://` collapses to `tcw:/` and
    # would be scaffolded as a plain folder of that name. Resolving the
    # address needs the project to exist already, which here it may not.
    # The scheme is matched in any case, as URL schemes are: `TCW://` would
    # otherwise become a folder named `TCW:`.
    given = {**(paths or {}), **({"work": work_path} if work_path is not None else {})}
    for c, text in given.items():
        if text.casefold().startswith("tcw:"):
            raise UsageError(
                f"--{c}-path {text!r}: `tcw project new` takes a path relative to the "
                f"project; a store location given as a tcw:// address is written "
                f"into {SENTINEL} by hand once the project exists")
    sentinel = root / SENTINEL
    if project_id is None:
        configured = load_config(sentinel) if sentinel.exists() else {}
        if not isinstance(configured, dict) or not configured.get("id"):
            raise UsageError("a new project needs `--id <project-id>`; IDs are not "
                             "inferred")
    from tcw.config import store_location_problem
    for c, text in given.items():
        problem = store_location_problem(f"{c}.path", text, address=False)
        if problem:
            raise UsageError(problem)
    try:
        written = init(
            components, root, project_id,
            Path(work_path).expanduser() if work_path is not None else None,
            {c: Path(p).expanduser() for c, p in (paths or {}).items()})
    # `RuntimeError` too: `Path.expanduser()` raises it for a `~name` naming no
    # user, whether that came from `--path` or from `work.path` in the config.
    except (ValueError, OSError, RuntimeError) as error:
        raise BackendError(str(error)) from None
    # The personal file is kept out of version control from the start
    # (TCW-72 Design 10.2). Outside a repository there is no ignore file to
    # write, so the person is told to do it themselves.
    if git_root(root) is not None:
        written += ignore_personal_files(root)
        changed(written)
    else:
        changed(written)
        print(f"note: not inside a repository, so no ignore rule was written; "
              f"keep {LOCAL_CONFIG} and {LOCAL_MANIFEST} out of version control "
              f"yourself", file=sys.stderr)
    return 0


def run_provision(components: list[str], *, dry_run: bool = False,
                  prefix: str = "tcw project provision", project_id: str | None = None,
                  projects: bool = True) -> int:
    """Make this project's declared component stores usable here.

    The only command in `tcw` that clones a repository, and it does so only
    because it was asked to. (The Jira backend's commands also reach the
    network: the configured `work.jira.site`, and wherever that site
    redirects a request, but the credentials are sent to the site alone.)
    That is the whole
    security posture of the feature: a repository's config can name a URL, so
    nothing may act on that URL without an explicit instruction from the
    person holding the checkout. The remote is
    printed before it is contacted, for the same reason. Everything it says
    goes to stderr, `--dry-run` included: it has no product (TCW-73 Design
    1.7). A store already here is never fetched into (Design 8.4).

    Then, unless `projects` is false (the `--component` form), the projects
    the family names that are not here (`tcw.provision`, TCW-115 Design 7).
    With `project_id`, that project and its load order, and no store.
    """
    project_root = find_project_root()
    if project_root is None:
        from tcw.errors import NO_PROJECT, BackendError
        raise BackendError(NO_PROJECT)

    # The readers below treat a config too broken to read as declaring
    # nothing, which would end in "Nothing to provision" and success.
    try:
        load_config(project_root / SENTINEL)
    except ValueError as error:
        print(f"{prefix}: {error}", file=sys.stderr)
        return 1

    # An override that is present and wrong refuses here too, and it has to be
    # said here rather than left to the registry. Every other command reaches a
    # broken override through `check()`, but this one reads declarations straight
    # from the configs — so without this gate the registry refused the override
    # while provisioning went and cloned a second copy of the very project the
    # override was pointing at. That is the bug the whole feature exists to stop.
    #
    # Deliberately only overrides, not graph problems at large: a graph with a
    # project not on this machine is routine here. An override is a declaration
    # the environment made, and a declaration that is present and wrong refuses
    # — the same rule the block below applies to the ones written in files. It
    # still matters with no project fetched: a store whose repository is a
    # project the variable places resolves inside it (TCW-107 plan, choice 6).
    try:
        failed_overrides = [o for o in FsProjectRegistry.open(project_root).overrides()
                            if o.problem is not None]
    except Exception:
        failed_overrides = []
    if failed_overrides:
        for override in failed_overrides:
            print(f"{prefix}: {override.problem}", file=sys.stderr)
        return 1

    # A graph problem refuses before anything is contacted (TCW-115 Design
    # 7.14); the `--component` form keeps exactly the checks it had.
    if projects:
        try:
            FsProjectRegistry.open(project_root).require_valid(fetching=True)
        except ValueError as error:
            print(f"{prefix}: {error}", file=sys.stderr)
            return 1
    if project_id is not None:
        from tcw.provision import provision_projects
        return provision_projects(project_root, project_id, dry_run=dry_run, prefix=prefix)

    declared: list[tuple[str, object]] = []
    problems: list[str] = []
    for component in components:
        declaration, component_problems = declared_repository(project_root, component)
        problems += [f"{SENTINEL}: {p}" for p in component_problems]
        if declaration is not None:
            declared.append((component, declaration))

    # A malformed declaration refuses rather than reading as "nothing declared".
    # Silently doing nothing here would be the worst outcome: the user asked for
    # a store and would be told everything is fine.
    if problems:
        for problem in problems:
            print(f"{prefix}: {problem}", file=sys.stderr)
        return 1

    if not declared:
        print(f"Nothing to provision: no component declares a home repository in "
              f"{SENTINEL}.", file=sys.stderr)

    # A store that fails does not stop the run: the projects pass follows,
    # and the last line counts both (TCW-115 Design 7.2, 7.13).
    fetched = failed = 0
    for component, declaration in declared:
        provisioner = FsStoreProvisioner(project_root, component, declaration)
        declared_available = provisioner.is_available()
        if not declared_available:
            try:
                # *This* component's store. Asking the work store here was
                # correct only while the loop had one component to run: with
                # more, a taxonomy declaration was measured against whether the
                # work store resolved, and would be cloned because it did not.
                resolved = STORE_CLASSES[component].open(project_root)
            except ValueError:
                pass
            else:
                print(f"  {component}: already available at {resolved.root}", file=sys.stderr)
                continue
        if not declared_available:
            print(f"→ {provisioner.describe()}", file=sys.stderr)      # says what it will contact
        try:
            result = provisioner.ensure_available(dry_run=dry_run)
        except (ValueError, OSError) as error:
            print(f"{prefix}: {error}", file=sys.stderr)
            failed += 1
            continue
        print(f"  {result.detail}", file=sys.stderr)
        fetched += result.action == "obtained"
    if not projects:
        return 1 if failed else 0
    from tcw.provision import provision_projects
    return provision_projects(project_root, dry_run=dry_run, prefix=prefix,
                              stores=(fetched, failed))


def _cmd_provision(args: argparse.Namespace) -> int:
    # The error lines name the command as it was typed (TCW-115 plan, choice 23).
    from tcw.errors import UsageError
    from tcw.project_files import validate_project_id
    project_id = getattr(args, "id", None)
    if project_id is not None:
        if args.component:
            raise UsageError("name a project or --component, not both: a project is "
                             "fetched with its load order and no store")
        try:
            validate_project_id(project_id)
        except ValueError as error:
            raise UsageError(str(error)) from None
        return run_provision([], dry_run=args.dry_run, prefix=args._command,
                             project_id=project_id)
    return run_provision(args.component or list(PROVISION_COMPONENTS),
                         dry_run=args.dry_run, prefix=args._command,
                         projects=not args.component)


def _cmd_init(args: argparse.Namespace) -> int:
    return run_init(
        args.components or list(COMPONENTS), args.id, args.work_path,
        {c: getattr(args, f"{c}_path") for c in ("taxonomy", "capabilities")
         if getattr(args, f"{c}_path", None) is not None})


def _not_yet(name: str):
    def run(args: argparse.Namespace) -> int:
        print(f"tcw {name}: not yet implemented.", file=sys.stderr)
        return 1
    return run


def collect_findings(project_root: Path, *, notes: list[str] | None = None,
                     work: bool = True) -> list:
    """Every finding of an offline `tcw validate` of the project, unprinted,
    with the lines about the run itself appended to `notes`. `work=False`
    leaves out the work-store checks (`validate`'s section e). Called by
    `_cmd_validate` and by `tcw migrate`'s check after its run (TCW-116
    Design 2.1)."""
    from tcw.findings import Finding
    from tcw.validate import config_findings, validate
    notes = [] if notes is None else notes
    registry = FsProjectRegistry.open(project_root)
    graph = registry.check()
    if graph:
        # `validate` is not reached, so the configuration findings it would
        # have led with are added here.
        return [*config_findings(project_root), *graph]
    # A project of the family that is not available here, one finding each
    # (TCW-108 Design 6.5); one that this project's own manifests place is
    # reported once, by `manifest_findings` (TCW-107 Design 5.1).
    unavailable: list = []
    checked = validate(project_root, notes=notes, unavailable=unavailable, work=work)
    # Where a store check stopped at a project it inherits from (Design 6.5
    # row c), said in that project's one finding.
    inherited = [(e.project, e.axis) for e in unavailable]
    # A gap that left a key of the configuration undecided, after any store
    # check's (TCW-109 Design 3.6).
    from tcw.config import effective
    inherited += [(gap, "configuration")
                  for gap in effective(project_root).gaps_withholding]
    findings: list[Finding] = registry.availability_findings(inherited)
    findings += registry.manifest_findings(inherited)
    findings += registry.warning_findings()
    # Design 4.5: the fallback order is said here and in `projects list
    # --json`, and by no other command.
    warning = registry.load_order().warning
    if warning is not None:
        findings.append(Finding("warning", str(project_root / SENTINEL), warning))
    return findings + checked


def _cmd_validate(args: argparse.Namespace) -> int:
    """Findings on stdout, one per line; overrides in effect, what was skipped
    and the closing count on stderr (TCW-73 Design 6). Exit 1 with any error,
    5 when `--remote` could not reach Jira, else 0."""
    from tcw.errors import NO_PROJECT, BackendError, UsageError
    project_root = find_project_root()
    if project_root is None:
        raise BackendError(NO_PROJECT)
    if args.remote and _not_jira_mode(project_root):
        raise UsageError("--remote checks a Jira-mode project, and this project's "
                         "work.backend is not jira")
    # An override is set in an environment rather than in any file this
    # checkout holds, so a graph that resolves because of one resolves for a
    # reason no reader can grep. Narration, never a finding: an override is a
    # statement about this machine, not a defect. Said first, because a graph
    # problem below ends the run.
    registry = FsProjectRegistry.open(project_root)
    for override in registry.overrides():
        print(f"connected project '{override.id}' is overridden by "
              f"{override.source} to {override.locator}", file=sys.stderr)
        if override.warning:
            print(f"warning: {override.warning}", file=sys.stderr)
    notes: list[str] = []
    findings = collect_findings(project_root, notes=notes)
    if registry.check():
        # A graph problem ends the run here, before any note or remote check.
        return _report(findings, project_root)
    for note in notes:
        print(note, file=sys.stderr)
    if args.remote:
        remote, unreachable = _validate_remote(project_root)
        findings += remote
        code = _report(findings, project_root)
        return 5 if unreachable else code
    return _report(findings, project_root)


def _located(finding, project_root: Path):
    """`finding` with its `where` relative to the project when it is a path
    inside it, absolute otherwise, so every finding names a file one way. The
    message loses a leading copy of that path, which some checks repeat."""
    from dataclasses import replace
    where, line = finding.where, ""
    if not where.startswith("/"):
        return finding
    if (m := re.fullmatch(r"(.+?)(:\d+)", where)):
        where, line = m.group(1), m.group(2)
    message = finding.message
    for spelling in (where, str(Path(where).resolve())):
        if message.startswith(spelling + ": "):
            message = message[len(spelling) + 2:]
    for root in (project_root, project_root.resolve()):
        try:
            where = str(Path(where).relative_to(root))
            break
        except ValueError:
            continue
    return replace(finding, where=where + line, message=message)


def _report(findings, project_root: Path) -> int:
    """Print each finding on stdout and the closing count on stderr; 1 when
    any is an error."""
    counts = {"error": 0, "warning": 0, "unresolved": 0}
    for finding in findings:
        print(_located(finding, project_root))
        counts[finding.severity] += 1
    plural = {"error": "errors", "warning": "warnings", "unresolved": "unresolved"}
    print(", ".join(f"{n} {name if n == 1 else plural[name]}"
                    for name, n in counts.items()), file=sys.stderr)
    return 1 if counts["error"] else 0


def _not_jira_mode(project_root: Path) -> bool:
    """Whether this project's `work.backend` is plainly something other than
    `jira`. Read from the raw value, so a Jira-mode project whose work config
    has some other problem is still Jira mode; a config that does not parse
    answers False, and the config finding `validate` reports explains it."""
    from tcw.store.fs import load_config
    try:
        raw = load_config(project_root / SENTINEL)
    except (ValueError, OSError):
        return False
    work = raw.get("work") if isinstance(raw, dict) else None
    backend = work.get("backend", "filesystem") if isinstance(work, dict) else "filesystem"
    return backend != "jira"


def _validate_remote(root: Path):
    """The remote checks of this Jira-mode project (TCW-71 Design 9.2; TCW-73
    Design 6.1): its findings, and whether Jira could not be reached. What
    passed or was skipped goes to stderr."""
    from tcw.errors import TcwError
    from tcw.work.gates import project_reader
    from tcw.work.jira.backend import JiraBackend
    from tcw.work.jira.remote import remote_findings
    from tcw.work.open import open_backend, reference_resolver
    try:
        backend = open_backend(root)
    except TcwError:
        return [], False             # the offline checks have reported it
    if not isinstance(backend, JiraBackend):
        return [], False
    reader = project_reader(root, FsProjectRegistry.open(root))
    findings, narration = remote_findings(backend, backend.layout, reader,
                                          reference_resolver(root))
    for line in narration:
        print(line, file=sys.stderr)
    # `remote_findings` reports Jira out of reach as one `unresolved` finding
    # located at the project itself; every other finding names a slug or a key.
    unreachable = any(f.severity == "unresolved" and f.where == backend.project
                      for f in findings)
    return findings, unreachable


def _cmd_serve(args: argparse.Namespace) -> int:
    project_root = find_project_root()
    if project_root is None:
        from tcw.errors import NO_PROJECT, BackendError
        raise BackendError(NO_PROJECT)
    FsProjectRegistry.open(project_root).require_valid()
    # The server outlives the start-up, and each request must see the files as
    # they are then, so the once-per-command read of the configuration ends
    # here (TCW-72 Design 2.3).
    from tcw import config as layered
    layered.end_command()
    return serve(project_root, port=args.port, open_browser=not args.no_open)


def build_parser() -> argparse.ArgumentParser:
    from tcw.cli_help import EXIT_CODES, command
    parser = SuggestingParser(prog="tcw", description="Taxonomy · Capabilities · Work.",
                              epilog=EXIT_CODES,
                              formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"tcw {__version__}")
    parser.add_argument(
        "-C", dest="chdir", action="append", default=[],
        metavar="<folder or tcw://<id>.path/>",
        help="run as if tcw had been started in this folder; repeat it to go "
             "further, each one read from the folder the one before chose")
    sub = parser.add_subparsers(dest="group", required=True)

    p_validate = command(
        sub, "validate", help="check this project's files, stores and work items",
        prints="one finding per line, `<severity>: <where>: <message>`; nothing "
        "when clean", writes="nothing",
        examples=["validate", "validate --remote"])
    p_validate.add_argument(
        "--remote", action="store_true",
        help="also check this Jira-mode project against Jira itself (reads only)",
    )
    p_validate.set_defaults(own_config=True, func=_cmd_validate)

    p_serve = command(sub, "serve", help="serve a local web viewer",
                      prints="the URL", writes="what the viewer saves",
                      examples=["serve", "serve --port 8123 --no-open"])
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT,
                         help=f"loopback port to listen on; 0 picks a free one "
                         f"(default: {DEFAULT_PORT})")
    p_serve.add_argument("--no-open", action="store_true",
                         help="do not open a browser")
    p_serve.set_defaults(func=_cmd_serve)

    migrate_cli.add_subparser(sub)

    for mod in _BUILT:
        mod.add_subparser(sub)
    # After `work`: the suggester names commands in the order the groups are
    # registered (TCW-115 Design 1.1, 1.3).
    project_cli.add_subparser(sub)
    for name in _STUBBED:
        p = sub.add_parser(name, help=f"{name} commands (not yet implemented)")
        p.set_defaults(func=_not_yet(name))

    attach_index(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    command = getattr(args, "_command", "tcw")
    # `tcw -C` changes the current folder; a caller in the same process
    # (the suite, the eval harness) gets its own back (TCW-114 Design 4.5).
    start = os.getcwd()
    try:
        code = _dispatch(args, command)
        # Flushed here, inside the `try`, so a reader that closed the pipe
        # before reading a short output is met by the handler below rather
        # than by the interpreter's own flush at exit, which prints
        # "Exception ignored ..." and exits 120. This covers what a failure
        # printed too: the name a failed create still prints on stdout.
        sys.stdout.flush()
        return code
    except BrokenPipeError:
        # Whoever read stdout stopped reading (`tcw work list | head -1`).
        # Nothing to say about it: point stdout at the null device so the
        # interpreter's own flush at exit cannot fail a second time, and exit
        # 1 as Python's documentation on SIGPIPE recommends.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass                       # stdout is not a file descriptor here
        return 1
    finally:
        os.chdir(start)


def _check_here(args: argparse.Namespace) -> None:
    """The checks every command makes of the project in the current folder
    before it runs."""
    from tcw import config as layered
    # Before anything else, for every command: a TCW 3.x project is refused,
    # naming `tcw migrate` (TCW-106 Design 4.1).
    refuse_legacy_project()
    # One place for every command: a config still holding the 2.x key is
    # refused before anything reads it (Design 9.3). `validate` reports it
    # as one of its findings instead.
    if args.group != "validate":
        refuse_retired_config()
    # And the project's configuration, every layer of it, is read and
    # checked once before the command runs (TCW-72 Design 2.3). The few
    # commands that must run with problems present read it themselves.
    if not getattr(args, "own_config", False):
        root = find_project_root()
        if root is not None and layered.effective(root).problems:
            raise ConfigError(layered.effective(root).problems)


def _enter(target: str, args: argparse.Namespace) -> None:
    """Change the current folder to the one `tcw -C <target>` names (TCW-114
    Design 4.2-4.4): a path, from the current folder; or a folder address,
    found from the project active in the current folder, after which the
    project active there must be the one the address names. Reads only
    folders on this machine."""
    from tcw.errors import UsageError
    from tcw.ids import FolderAddress, has_scheme, parse_address
    if not has_scheme(target):
        folder = Path(target)
    else:
        found = parse_address(target)
        if not isinstance(found, FolderAddress):
            raise UsageError(
                f"{target} names an object, not a folder; tcw -C takes a folder "
                f"address, tcw://<project>[.<namespace>].path/<folder>")
        _check_here(args)
        here = find_project_root()
        if here is None:
            raise TcwError(f"tcw -C {target} needs a TCW project here to find "
                           f"'{found.project}' from; give the folder's path instead")
        from tcw.locate import Locator, resolve_folder_address
        folder = resolve_folder_address(found, Locator.of(here), here)
    if not folder.is_dir():
        raise UsageError(f"cannot run in {target}: no such folder")
    os.chdir(folder)
    if has_scheme(target):
        _runs_as(found, target, folder)


def _runs_as(address, target: str, folder: Path) -> None:
    """Refuse an address whose folder is not in the project it names: the
    command would run as another project (TCW-114 Design 4.4)."""
    from tcw.errors import UsageError
    from tcw.locate import Locator
    root = find_project_root()
    to_run = f"give tcw://{address.project}.path/ to run as '{address.project}'"
    if root is None:
        raise UsageError(f"{target} is {folder.resolve()}, which is in no TCW project; "
                         f"{to_run}")
    active = Locator.of(root).project_id
    if active != address.project:
        raise UsageError(f"{target} is a folder of project '{active}', so the command "
                         f"would run as '{active}', not '{address.project}'; {to_run}")


def _dispatch(args: argparse.Namespace, command: str) -> int:
    """Run the command and turn every expected failure into one line on
    stderr and its exit code. A closed stdout is left to `main`."""
    from tcw import config as layered
    layered.begin_command()
    try:
        # `tcw -C`: the folder the command runs in, chosen before anything of
        # the command reads the current one (TCW-114 Design 4.5).
        for target in getattr(args, "chdir", None) or ():
            _enter(target, args)
        # `tcw migrate` reads the files these checks would refuse, so it
        # makes none of them (TCW-116 Design 1.2).
        if not getattr(args, "skips_checks", False):
            _check_here(args)
        return args.func(args)
    except TcwError as error:
        # A failure after something was created still names it, on stdout
        # exactly as success would (Design 1.8).
        if error.name:
            print(error.name)
        # Several configuration problems are several errors: one line each,
        # each with the command's prefix (TCW-73's one-line form).
        lines = ([str(p) for p in error.problems] if isinstance(error, ConfigError)
                 else [str(error)])
        for line in lines:
            print(f"{command}: {line}", file=sys.stderr)
        return error.code
    except (ValueError, MultipleMatch) as error:
        # A fault that reached here unclassified, not an answer: exit 1.
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    except yaml.YAMLError as error:
        # A malformed YAML file is the user's, not a bug in TCW, so it reads as
        # a message rather than a traceback. The loader's message names the
        # file (`tcw.store.yaml_source.load`).
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        raise                          # an OSError, but `main` handles it
    except OSError as error:
        # A file TCW could not read or write — permissions, a full disk, a
        # path that vanished — is reported in one line, not as a traceback.
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    finally:
        layered.end_command()

if __name__ == "__main__":
    sys.exit(main())
