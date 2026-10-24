"""Record TCW 3.0.2's own answers about each migration fixture (TCW-116 plan,
Decided 3). A script run by hand, never by the suite: pytest collects only
`test_*.py` files, and nothing imports this one.

The answers are what `tcw migrate`'s copied 3.x readers are checked against,
and after TCW-118 no 3.x `tcw` is left on this machine to give them, so they
are recorded once and committed, as `tests/migrate/golden/<fixture>.json`.
`tests/migrate/test_goldens_current.py` fails when a fixture changes after
its golden was recorded, naming this script.

    python tests/migrate/record_3x_listings.py            # installs tcw-cli 3.0.2
    python tests/migrate/record_3x_listings.py --tcw PATH  # uses a 3.0.2 already here

Without `--tcw` it needs network access: it first checks that PyPI answers,
and stops with exit 1 if not, having made nothing, so pip is never run
behind a proxy that points nowhere. It then installs `tcw-cli==3.0.2` into a
throwaway virtual environment. Either way it checks that the `tcw` it runs
prints exactly `tcw 3.0.2`, runs only that one by its full path, and runs it
only in fixture folders it made in a new temporary folder outside every
project, with `HOME`, `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` inside that
folder, every `TCW_*` variable removed, and the HTTPS proxy set to an
address nothing listens on.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from tests.migrate.fixtures import (FIXTURE_PROJECTS, FIXTURES,  # noqa: E402
                                    build_fixture, fixture_digest_of)

VERSION = "tcw 3.0.2"
PYPI = "https://pypi.org/pypi/tcw-cli/3.0.2/json"
DEAD_PROXY = "http://127.0.0.1:9"


def fail(message: str) -> None:
    print(f"record_3x_listings: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_network() -> None:
    try:
        with urllib.request.urlopen(PYPI, timeout=10) as answer:
            answer.read(1)
    except Exception as error:      # any failure means: do not run pip
        fail(f"cannot reach PyPI ({error}); run it with network access and with "
             f"no proxy that points nowhere")


def install(folder: Path) -> tuple[Path, list[str]]:
    venv = folder / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    subprocess.run([str(venv / "bin" / "pip"), "install", "-q", "tcw-cli==3.0.2"],
                   check=True)
    return venv / "bin" / "tcw", freeze(venv / "bin" / "python")


def freeze(python: Path) -> list[str]:
    done = subprocess.run([str(python), "-m", "pip", "freeze"], capture_output=True,
                          text=True, check=True)
    return [line for line in done.stdout.splitlines()
            if line.lower().startswith(("pyyaml", "tcw")) or "tcw_cli" in line]


def environment(folder: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("TCW_")}
    env.update({"HOME": str(folder / "home"), "XDG_CONFIG_HOME": str(folder / "config"),
                "XDG_CACHE_HOME": str(folder / "cache"), "https_proxy": DEAD_PROXY,
                "HTTPS_PROXY": DEAD_PROXY})
    return env


def nearest_config(start: Path) -> Path | None:
    for folder in (start, *start.parents):
        if (folder / "tcw-config.yaml").is_file():
            return folder
    return None


def placeheld(text: str, folder: Path) -> str:
    for path, name in ((folder / "fixture", "<fixture>"), (folder / "config", "<config>"),
                       (folder / "cache", "<cache>"), (folder / "home", "<home>")):
        for spelling in {str(path), str(path.resolve())}:
            text = text.replace(spelling, name)
    return text


def answers(tcw: Path, root: Path, env: dict, folder: Path) -> dict:
    """3.0.2's answers in the project at `root`."""
    def run(*argv: str) -> dict:
        done = subprocess.run([str(tcw), *argv], cwd=root, env=env,
                              capture_output=True, text=True, timeout=120)
        return {"exit": done.returncode, "stdout": placeheld(done.stdout, folder),
                "stderr": placeheld(done.stderr, folder)}

    commands = {"taxonomy list --json": run("taxonomy", "list", "--json"),
                "capabilities list --json": run("capabilities", "list", "--json")}
    listed = json.loads(commands["capabilities list --json"]["stdout"])
    for row in listed["capabilities"]:
        commands[f"capabilities show {row['path']} --json"] = run(
            "capabilities", "show", row["path"], "--json")
    commands["validate"] = run("validate")
    return commands


def record(name: str, tcw: Path, frozen: list[str], out: Path) -> None:
    folder = Path(tempfile.mkdtemp(prefix=f"tcw116-{name}-"))
    try:
        for sub in ("home", "cache"):
            (folder / sub).mkdir()
        root = build_fixture(name, folder / "fixture", config_home=folder / "config",
                             cache_home=folder / "cache")
        projects = FIXTURE_PROJECTS.get(name)
        places = {key: root / rel for key, rel in (projects or {None: "."}).items()}
        for place in places.values():
            if nearest_config(place) != place:
                fail(f"{place} holds no project of its own; not running tcw there")
        if nearest_config(folder) is not None:
            fail(f"{folder} is inside another project; not running tcw there")
        env = environment(folder)
        golden = {"tcw-version": subprocess.run(
                      [str(tcw), "--version"], cwd=folder, env=env, capture_output=True,
                      text=True, timeout=120).stdout.strip(),
                  "pip-freeze": frozen,
                  "date": datetime.date.today().isoformat(),
                  "fixture-digest": fixture_digest_of(name, folder / "fixture",
                                                      folder / "config",
                                                      folder / "cache")}
        if projects is None:
            golden["commands"] = answers(tcw, root, env, folder)
        else:
            golden["projects"] = {key: answers(tcw, place, env, folder)
                                  for key, place in places.items()}
        out.write_text(json.dumps(golden, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tcw", type=Path, help="a tcw 3.0.2 already installed")
    parser.add_argument("--only", nargs="+", choices=sorted(FIXTURES),
                        help="record only these fixtures' goldens")
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix="tcw116-record-"))
    try:
        if args.tcw is None:
            check_network()
            tcw, frozen = install(work)
        else:
            tcw = args.tcw.resolve()
            frozen = freeze(Path(os.path.realpath(tcw)).parent / "python")
        version = subprocess.run([str(tcw), "--version"], capture_output=True,
                                 text=True, env=environment(work)).stdout.strip()
        if version != VERSION:
            fail(f"{tcw} prints {version!r}, not {VERSION!r}")
        (HERE / "golden").mkdir(exist_ok=True)
        names = args.only or list(FIXTURES)
        for name in names:
            record(name, tcw, frozen, HERE / "golden" / f"{name}.json")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
