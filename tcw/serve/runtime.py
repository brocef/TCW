"""Process supervision for the Fastify frontend and private Python API."""

from __future__ import annotations

import json
import os
import queue
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import webbrowser
from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path
from typing import TextIO

from tcw.store.fs import find_node_root

HOST = "127.0.0.1"
MINIMUM_NODE = (22, 12, 0)
READINESS_TIMEOUT_SECONDS = 15.0
_NODE_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def parse_node_version(value: str) -> tuple[int, int, int] | None:
    """Parse the stable numeric portion of `node --version` output."""
    match = _NODE_VERSION.match(value.strip())
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def find_compatible_node() -> str:
    """Return a Node executable that satisfies TCW's serve runtime floor."""
    executable = shutil.which("node")
    if executable is None:
        raise RuntimeError(
            "Node.js 22.12 or newer is required for `tcw serve`; install Node and retry."
        )
    try:
        result = subprocess.run(
            [executable, "--version"], check=True, capture_output=True, text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(f"could not run `{executable} --version`: {error}") from error
    version = parse_node_version(result.stdout)
    if version is None:
        raise RuntimeError(f"could not parse Node.js version: {result.stdout.strip()!r}")
    if version < MINIMUM_NODE:
        found = ".".join(str(part) for part in version)
        raise RuntimeError(
            f"Node.js 22.12 or newer is required for `tcw serve`; found {found}."
        )
    return executable


def _read_first_line(stream: TextIO, output: queue.Queue[str | None]) -> None:
    try:
        output.put(stream.readline(16_385))
    except Exception:
        output.put(None)


def _await_readiness(process: subprocess.Popen[str]) -> int:
    if process.stdout is None:
        raise RuntimeError("Node child did not expose a readiness stream")
    output: queue.Queue[str | None] = queue.Queue(maxsize=1)
    threading.Thread(
        target=_read_first_line, args=(process.stdout, output), daemon=True
    ).start()
    try:
        line = output.get(timeout=READINESS_TIMEOUT_SECONDS)
    except queue.Empty as error:
        raise RuntimeError("Node child did not become ready within 15 seconds") from error
    if line is None or not line or len(line) > 16_384:
        raise RuntimeError("Node child exited or emitted an invalid readiness message")
    try:
        message = json.loads(line)
    except json.JSONDecodeError as error:
        raise RuntimeError("Node child emitted malformed readiness output") from error
    port = message.get("port") if isinstance(message, dict) else None
    if message.get("type") != "ready" or not isinstance(port, int):
        raise RuntimeError("Node child emitted an invalid readiness message")
    return port


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_server(*, port: int, open_browser: bool, node_root: Path | None,
               include_descendants: bool) -> int:
    """Run the authenticated sidecar and packaged Fastify server together."""
    root = node_root or find_node_root()
    if root is None:
        print("tcw serve: no tcw node here — run `tcw init` in the project folder.",
              file=sys.stderr)
        return 1
    try:
        node = find_compatible_node()
    except RuntimeError as error:
        print(f"tcw serve: {error}", file=sys.stderr)
        return 1

    # Imported lazily to avoid a circular import while tcw.serve exports serve().
    from tcw.serve import TcwServer

    token = secrets.token_urlsafe(32)
    try:
        sidecar = TcwServer((HOST, 0), root, include_descendants,
                            token=token, api_only=True)
    except OSError as error:
        print(f"tcw serve: cannot start private API sidecar: {error}", file=sys.stderr)
        return 1
    sidecar_thread = threading.Thread(target=sidecar.serve_forever, daemon=True)
    sidecar_thread.start()
    process: subprocess.Popen[str] | None = None
    install_signal_handler = threading.current_thread() is threading.main_thread()
    previous_sigterm = signal.getsignal(signal.SIGTERM) if install_signal_handler else None

    def stop_on_sigterm(_signum, _frame) -> None:
        raise KeyboardInterrupt

    if install_signal_handler:
        signal.signal(signal.SIGTERM, stop_on_sigterm)
    try:
        with ExitStack() as stack:
            distribution = files("tcw.serve").joinpath("dist")
            dist_path = stack.enter_context(as_file(distribution))
            server_entry = dist_path.joinpath("server.cjs")
            asset_directory = dist_path.joinpath("client")
            if not server_entry.is_file() or not asset_directory.is_dir():
                raise RuntimeError("packaged web assets are missing; reinstall TCW")
            environment = os.environ.copy()
            environment.update({
                "TCW_SERVE_ASSET_DIR": str(asset_directory),
                "TCW_SERVE_PORT": str(port),
                "TCW_SERVE_SIDECAR_ORIGIN": f"http://{HOST}:{sidecar.server_port}",
                "TCW_SERVE_SIDECAR_TOKEN": token,
            })
            process = subprocess.Popen(
                [node, str(server_entry)], env=environment, stdout=subprocess.PIPE,
                text=True,
            )
            public_port = _await_readiness(process)
            url = f"http://{HOST}:{public_port}/"
            print(f"Serving TCW at {url}")
            if open_browser:
                threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
            return_code = process.wait()
            if return_code != 0:
                print(f"tcw serve: Node child exited with status {return_code}", file=sys.stderr)
                return 1
            return 0
    except KeyboardInterrupt:
        print("\ntcw serve: stopped", file=sys.stderr)
        return 0
    except (OSError, RuntimeError) as error:
        print(f"tcw serve: {error}", file=sys.stderr)
        return 1
    finally:
        if install_signal_handler and previous_sigterm is not None:
            signal.signal(signal.SIGTERM, previous_sigterm)
        if process is not None:
            _stop_process(process)
        sidecar.shutdown()
        sidecar.server_close()
        sidecar_thread.join(timeout=5)
